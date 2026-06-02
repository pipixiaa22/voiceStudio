# Redis 优化改造方案

本文档基于当前项目代码梳理 Redis 可落地的优化点。结论先说：Redis 不建议替代现有 SQLite/MySQL 主存储，而应作为 **任务状态与事件总线、热点缓存、分布式锁、限流与幂等层** 接入。这样可以在不重写业务模型的前提下，提升视频生成、配音工作流、内容发现和外部模型调用的稳定性与响应速度。

## 当前现状

- Flask 后端在 `server/app.py` 初始化 SQLAlchemy，默认 SQLite，支持 `DATABASE_URL` 切到 MySQL。
- 视频任务在 `server/services/video_job.py` 使用后台 daemon thread 执行，任务状态写入 `VideoJob` 表。
- 视频任务 SSE 使用进程内 `_sse_subscribers: dict[str, list[queue.Queue]]` 广播，重启或多进程部署后订阅不可共享。
- 语音工作流音频缓存位于 `outputs/voice_workflow_cache`，通过音频指纹复用本地 WAV 文件。
- 多处接口会调用外部服务：TTS、LLM、Google Translate、YouTube/oEmbed/页面抓取。
- 前端视频进度组件 `web/src/components/video/VideoJobProgress.vue` 已使用 SSE，并在失败时回退为单次 REST 查询。

## 改造优先级

| 优先级 | 场景 | 价值 | 涉及文件 |
| --- | --- | --- | --- |
| P0 | 视频任务状态缓存 + Redis Pub/Sub SSE | 跨进程可见、重启后更快恢复、减少 DB 查询 | `server/services/video_job.py`, `server/routes/video.py` |
| P0 | 语音/TTS 片段分布式锁 | 防止同一音频指纹并发重复合成，节省云端 TTS 费用 | `server/services/voice_workflow_audio.py`, `server/services/video_job.py` |
| P1 | 外部 API 响应缓存 | 降低 YouTube/页面解析/翻译/LLM 分析重复请求 | `server/routes/texts.py`, `server/routes/discovery.py`, `server/services/discovery/*` |
| P1 | 任务队列化 | 控制视频渲染并发，避免多个 moviepy/TTS 任务压垮本机 | `server/services/video_job.py` |
| P1 | 限流与幂等 | 防误点、保护云端 API key、降低重复任务 | `server/routes/tts.py`, `server/routes/models.py`, `server/routes/video.py` |
| P2 | 热点列表短缓存 | 加快模板、模型列表、发现列表、文本列表查询 | `server/routes/models.py`, `server/routes/discovery.py`, `server/routes/texts.py` |
| P2 | 缓存健康检查与运维面板 | 便于判断 Redis 是否在线、缓存命中率和队列积压 | `server/routes/system.py` |

## Redis 基础接入

### 依赖与配置

建议新增依赖：

```toml
dependencies = [
    "redis>=5.0.0",
]
```

建议新增环境变量：

```bash
REDIS_URL=redis://:password@host:6379/0
REDIS_KEY_PREFIX=video-script
REDIS_CACHE_ENABLED=true
REDIS_TASK_QUEUE_ENABLED=false
```

### 新增服务模块

建议新增 `server/services/redis_client.py`：

```python
import os
import redis

_client = None

def get_redis():
    global _client
    if _client is not None:
        return _client
    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    _client = redis.Redis.from_url(url, decode_responses=False)
    return _client

def redis_key(*parts):
    prefix = os.environ.get('REDIS_KEY_PREFIX', 'video-script')
    clean = ':'.join(str(p).strip(':') for p in parts)
    return f'{prefix}:{clean}'
```

说明：

- `decode_responses=False` 更适合同时存 JSON 和二进制音频元数据；业务层自行 encode/decode。
- 所有调用都要允许 Redis 不可用时降级到当前逻辑，避免云端 Redis 故障导致核心功能完全不可用。

## P0：视频任务状态与 SSE 事件总线

### 当前问题

`server/services/video_job.py` 的 `_sse_subscribers` 是进程内内存：

- Flask debug reload、多 worker、重启后订阅全部丢失。
- 如果未来用 gunicorn 多进程，同一个 job 的更新可能发生在 A 进程，但浏览器 SSE 连到 B 进程，B 进程收不到事件。
- `GET /api/video/jobs/<job_id>` 每次都查 DB；高频进度请求会产生不必要 DB 压力。

### Redis 方案

保留 `VideoJob` 表作为最终状态，Redis 存实时快照和事件：

| Key | 类型 | TTL | 用途 |
| --- | --- | --- | --- |
| `video-script:video:job:{job_id}` | String(JSON) | 7 天 | 任务实时状态快照 |
| `video-script:video:job:{job_id}:events` | Stream | 7 天 | 任务进度事件，支持断线续读 |
| `video-script:video:jobs:latest` | ZSET | 7 天 | 最近任务列表，score 为时间戳 |
| `video-script:video:job:{job_id}:lock` | String | 任务运行期 | 防重复启动同一任务 |

### 改造步骤

1. 在 `create_job()` 创建 DB 记录后，将 `job.to_dict()` 写入 Redis。
2. 在 `update_job_progress()` / `update_job_completed()` / `update_job_failed()` 中：
   - 继续写 DB，保证最终一致。
   - 同步写 `video:job:{job_id}` 快照。
   - `XADD video:job:{job_id}:events` 写入进度事件。
3. 在 `get_job()` 中优先读 Redis 快照；Redis miss 再读 DB，并回填 Redis。
4. 将 `subscribe_sse()` / `_sse_broadcast()` 改造成 Redis Stream 读取：
   - SSE 连接时先返回当前快照。
   - 然后使用 `XREAD BLOCK 15000` 监听新事件。
   - 没有新事件时发送 heartbeat。
5. 保留当前内存队列作为 `REDIS_URL` 未配置时的降级路径。

### 预期收益

- 前端进度在多进程部署下仍可靠。
- 任务详情接口可减少 DB 查询。
- 浏览器断线重连后可以从 Stream 读取最近进度，不只拿到最后状态。

## P0：配音片段合成分布式锁

### 当前问题

`server/services/voice_workflow_audio.py` 已经用 `build_audio_fingerprint()` 和本地 WAV 文件做缓存，但有两个短板：

- 两个请求同时合成同一 workflow/segment/fingerprint 时，都会判断缓存不存在，然后同时请求云端 TTS。
- `audition-path` 使用 `persist_cache=False`，但重复试听同一路径也可能短时间内重复消耗 TTS。

### Redis 方案

围绕音频指纹加锁：

| Key | 类型 | TTL | 用途 |
| --- | --- | --- | --- |
| `video-script:tts:fingerprint:{sha}` | String(JSON) | 30 天 | 音频元数据缓存，记录 path/duration/model |
| `video-script:tts:fingerprint:{sha}:lock` | String | 120 秒 | 防重复合成同一片段 |
| `video-script:tts:audition:{hash}` | String(base64 或 path) | 10-30 分钟 | 短期试听缓存 |

### 改造步骤

1. 在 `synthesize_or_cache_segment()` 计算 `expected_fingerprint` 后，先读 Redis 元数据。
2. 如果 Redis 指向的本地文件存在，直接返回缓存。
3. 如果缓存不存在，用 `SET lock_key request_id NX EX 120` 获取锁。
4. 获取锁成功的请求执行 TTS，写本地文件和 Redis 元数据后释放锁。
5. 获取锁失败的请求短暂轮询缓存，最多等待 15-30 秒；仍无结果再返回“语音正在生成，请稍后重试”。
6. 对 `persist_cache=False` 的试听路径，可使用短 TTL Redis 缓存，避免用户连续点试听反复计费。

### 预期收益

- 明显减少重复 TTS 调用。
- 视频生成、导出、补齐缺失音频并发触发时更稳定。
- 云端 Redis 可跨 Flask 进程共享锁。

## P1：外部 API 响应缓存

### 1. 双语字幕翻译缓存

当前 `server/routes/texts.py` 的 `/api/texts/generate-bilingual-srt` 对每个字幕段逐个调用 Google Translate。

建议缓存：

| Key | TTL | Value |
| --- | --- | --- |
| `video-script:translate:zh-CN:en:{sha256(text)}` | 30 天 | 翻译文本 |

改造方式：

- 对每个 segment 先读 Redis。
- miss 时调用 `GoogleTranslator.translate()`，成功后写入缓存。
- 失败时不要缓存空字符串，避免临时故障污染结果。

### 2. 内容发现搜索与 URL 解析缓存

当前 `server/services/discovery/youtube.py` 和 `manual_url.py` 每次都会请求 YouTube API、oEmbed 或目标页面。

建议缓存：

| Key | TTL | Value |
| --- | --- | --- |
| `video-script:discovery:search:{platform}:{hash(query+filters+limit)}` | 10-30 分钟 | 搜索结果列表 |
| `video-script:discovery:url:{sha256(url)}` | 1-7 天 | URL 解析结果 |
| `video-script:discovery:video:{platform}:{source_id}` | 1-7 天 | 单视频详情 |

注意：

- 搜索结果热度变化较快，TTL 不宜过长。
- URL 元数据较稳定，可以缓存更久。
- 仍然要把最终发现记录写入数据库，Redis 只减少外部请求。

### 3. LLM 分析结果缓存

当前 `/api/discovery/items/<item_id>/analyze` 每次都会调用 LLM，随后覆盖 `DiscoveryAnalysis`。

建议缓存：

| Key | TTL | Value |
| --- | --- | --- |
| `video-script:llm:analysis:{item_hash}:{prompt_version}:{model}` | 7-30 天 | LLM JSON 结果 |
| `video-script:llm:polish:{hash(input+options)}` | 7 天 | 文案/音色提示词润色结果 |

关键点：

- 必须包含 `prompt_version`，否则 prompt 调整后会误用旧结果。
- 必须包含 provider/model，否则不同模型结果会混在一起。
- 对用户明确要求“重新分析”的动作应支持 `force_refresh=true` 跳过缓存。

## P1：视频任务队列化

### 当前问题

`start_job_processing()` 直接创建 daemon thread：

- 没有全局并发控制。
- 任务多时会同时跑 TTS、moviepy、文件打包，容易拖垮机器。
- 进程退出时 daemon thread 可能被中断。

### 轻量 Redis 队列方案

不引入 Celery 的情况下，可以先用 Redis List/Stream：

| Key | 类型 | 用途 |
| --- | --- | --- |
| `video-script:queue:video_jobs` | List 或 Stream | 待处理任务 |
| `video-script:queue:video_jobs:processing` | ZSET | 正在处理任务和心跳时间 |
| `video-script:video:worker:{worker_id}` | String | worker 心跳 |

改造步骤：

1. `create_video_job()` 只创建任务并 `LPUSH`/`XADD` 到队列。
2. 新增 worker 启动入口，例如 `uv run python -m server.workers.video_worker`。
3. worker 使用 `BRPOP` 或 `XREADGROUP` 拉取任务。
4. 用环境变量控制并发：`VIDEO_WORKER_CONCURRENCY=1`。
5. 开发环境可以保留 `REDIS_TASK_QUEUE_ENABLED=false`，继续用当前线程模式。

### 后续可选

如果任务量继续增大，再升级为 RQ/Celery/Dramatiq。当前项目依赖较轻，第一阶段不建议一上来引入完整任务框架。

## P1：限流与幂等

### 限流场景

建议对以下接口加 Redis 滑动窗口或固定窗口限流：

- `/api/tts/synthesize`
- `/api/tts/batch-synthesize`
- `/api/models/tts/synthesize`
- `/api/models/llm/complete`
- `/api/model-providers/test`
- `/api/video/jobs`
- `/api/discovery/items/<item_id>/analyze`

示例策略：

| 接口类型 | 限制 |
| --- | --- |
| TTS 单次试听 | 每 IP 每分钟 20 次 |
| 批量 TTS/导出 | 每 IP 每分钟 3 次 |
| LLM 分析 | 每 IP 每分钟 10 次 |
| 视频任务创建 | 每 IP 每 5 分钟 3 次 |
| 供应商连接测试 | 每 IP 每分钟 10 次 |

### 幂等场景

视频任务创建接口 `/api/video/jobs` 可引入请求 hash：

| Key | TTL | Value |
| --- | --- | --- |
| `video-script:idempotency:video:{request_hash}` | 10 分钟 | `job_id` |

同一标题、文本、模板、音色、场景配置在短时间重复提交时，直接返回已有 `job_id`，避免前端重复点击创建多个任务。

## P2：热点列表缓存

适合短 TTL 缓存的接口：

- `GET /api/video/templates`
- `GET /api/model-providers/presets`
- `GET /api/models`
- `GET /api/discovery/sources`
- `GET /api/discovery/items`
- `GET /api/texts`
- `GET /api/voice-workflows`

建议：

- 模板、模型预设：TTL 5-30 分钟。
- 文本/发现/工作流列表：TTL 10-60 秒。
- 写操作后删除相关列表缓存，而不是等待 TTL。

注意：`/api/texts`、`/api/discovery/items` 有查询参数，缓存 key 必须包含 query string。

## 不建议使用 Redis 的地方

- 不建议把 `Text`、`Folder`、`Tag`、`VoiceWorkflow` 等主业务数据迁到 Redis；这些仍应由 SQLAlchemy 数据库负责。
- 不建议把大 MP4/ZIP 文件直接存 Redis；继续存 `outputs/video_jobs`，Redis 只存路径、状态和元数据。
- 不建议把长期语音 WAV 全部放 Redis；当前文件缓存更合适。Redis 可存索引、锁、短期试听结果。
- 不建议缓存 API Key 明文；现有 API Key 多来自请求或数据库配置，Redis 中只保存派生 hash、状态或非敏感元数据。

## 推荐实施路线

### Phase 1：基础设施与任务状态

1. 增加 `redis` Python 依赖。
2. 新增 `server/services/redis_client.py`。
3. 给 `/api/system` 增加 Redis 健康检查。
4. 改造 `video_job.py`：任务快照写 Redis、SSE 事件写 Redis Stream。
5. 保留无 Redis 降级路径。
6. 增加单元测试：Redis mock/关闭 Redis 时逻辑可正常降级。

### Phase 2：TTS 锁与缓存元数据

1. 改造 `voice_workflow_audio.synthesize_or_cache_segment()`。
2. 给 `build_voice_track_from_text()` 中普通文本 TTS 也加入按文本+音色+模型的缓存锁。
3. 补充测试：并发请求同一 fingerprint 只触发一次 provider。

### Phase 3：外部 API 缓存与限流

1. 翻译缓存。
2. YouTube/oEmbed/页面元数据缓存。
3. LLM 分析缓存，加入 `prompt_version`。
4. TTS/LLM/视频任务接口限流。
5. 视频任务创建幂等。

### Phase 4：队列 worker

1. 新增 Redis 队列 worker。
2. `start_job_processing()` 根据 `REDIS_TASK_QUEUE_ENABLED` 选择线程或入队。
3. 增加 worker 心跳、失败重试、卡住任务恢复。
4. 更新 `start.sh`，支持启动 worker。

## 配置示例

`.env` 示例：

```bash
REDIS_URL=redis://:your-password@your-redis-host:6379/0
REDIS_KEY_PREFIX=video-script-dev
REDIS_CACHE_ENABLED=true
REDIS_TASK_QUEUE_ENABLED=false
VIDEO_WORKER_CONCURRENCY=1
```

生产环境建议：

- Redis 开启密码和 TLS（如果云厂商支持）。
- 使用独立 DB 或清晰 prefix 区分 dev/prod。
- 给缓存 key 设置 TTL，避免长期膨胀。
- 大对象不要进入 Redis，特别是 MP4/ZIP。

## 验证清单

- 未配置 `REDIS_URL` 时，现有功能仍可运行。
- Redis 正常时，视频任务创建后能看到 `video:job:{job_id}` 快照。
- 视频任务 SSE 在 Flask 重启/浏览器重连后能恢复最新状态。
- 同一语音片段并发生成时，provider 只被调用一次。
- 双语字幕重复生成时，第二次明显减少翻译请求。
- YouTube 搜索同一关键词短时间内命中缓存。
- 限流触发时返回明确的 429 响应和剩余等待时间。

## 需要注意的风险

- Redis Stream 事件和 DB 状态可能短暂不一致，最终状态仍以 DB 为准。
- 分布式锁必须设置 TTL，避免任务异常退出后永久锁死。
- 释放锁时要校验 request_id，避免误删其他请求持有的锁。
- LLM/TTS 缓存 key 需要包含模型、音色、参数、prompt 版本，否则会出现错误复用。
- 云端 Redis 网络延迟会影响高频接口，因此读写 Redis 应设置短超时并允许降级。

