# 系统配置保存后热更新优化方案

## 背景

当前系统配置面板保存后会提示“配置已保存，需要重启服务生效”，并提供“立即重启服务”按钮。

现有链路：

- 前端：`web/src/components/settings/SystemConfigPanel.vue`
- API：`web/src/api/index.js` 的 `systemApi`
- 后端：`server/routes/system.py`
- 启动加载：`server/app.py` 显式 `load_dotenv(.env, override=True)`

当前 `PUT /api/system/config` 已经做了两件事：

1. 写入项目根目录 `.env`。
2. 同步更新当前进程的 `os.environ`。

但这不等于完整热更新。原因是很多运行时对象已经被创建并缓存：

- Flask-SQLAlchemy engine / session / connection pool。
- Redis client：`server/services/redis_client.py` 的 `_client`。
- Embedding client：`server/services/memory/embeddings.py` 的 `_embeddings`。
- Vector store：`server/services/memory/vector_store.py` 的 `_stores`。
- 可能正在运行的后台生成任务、视频任务、SSE 任务。

所以现在“一律要求重启”是保守方案，但产品体验偏重。

## 改造目标

保存配置后按风险级别精确生效：

- 能安全热更新的配置，保存后立即生效。
- 需要重建 client 的配置，保存后自动刷新对应 runtime 对象。
- 高风险配置不强行热更新，明确提示“需重启生效”。
- 前端不再一刀切显示“重启后生效”，而是展示每项配置的生效状态。

目标体验：

```text
保存配置
  -> API 返回：
     - OPENAI_API_KEY：已热更新
     - REDIS_KEY_PREFIX：已热更新
     - REDIS_URL：已重建 Redis 连接
     - DATABASE_URL：已保存，需重启切换数据库
```

## 非目标

第一阶段不建议实现数据库连接热切换。

原因：

- `DATABASE_URL` 影响 Flask-SQLAlchemy 的 engine、session 和连接池。
- 后台线程可能正在读写旧数据库。
- SSE / 生成任务可能持有旧 session。
- 从 SQLite 切 MySQL/PostgreSQL 还涉及表结构、数据迁移和任务一致性。

数据库配置可以保存、测试、建表，但真正切换运行数据库仍建议重启。

## 配置分类

### A 类：可直接热更新

这些配置只依赖 `os.environ` 或下一次调用时读取，无需重启。

- `REDIS_KEY_PREFIX`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `DASHSCOPE_API_KEY`

注意：

- 如果相关服务已经缓存 client，需要同时清理缓存。
- Embedding API key 虽然是环境变量，但当前 `_embeddings` 会缓存实例，因此需要调用 reset。

### B 类：可热更新，但需要重建 runtime client

- `REDIS_URL`
- Embedding key 相关配置：
  - `DASHSCOPE_API_KEY`
  - `OPENAI_API_KEY`
  - `DEEPSEEK_API_KEY`

需要处理：

- Redis：关闭旧 client，清空 `_client` 和 backoff 状态。
- Embedding：调用 `reset_embeddings()`。
- Vector store：清空 `_stores`，让下次访问用新的 embedding / backend 创建。

### C 类：谨慎热更新，可选实现

- `CHROMADB_PERSIST_DIR`

原因：

- 当前 `get_vector_store(project_id)` 会缓存每个项目的 Chroma / pgvector store。
- 目录变更后，旧 store 仍指向旧目录。
- 直接清空 `_stores` 可以让新访问走新目录，但正在运行的索引/检索任务可能还持有旧对象。

建议：

- 第一阶段保存后标记“需重新加载向量库”。
- 若没有进行中的 RAG 任务，可自动清空 vector store cache。
- 如果有进行中任务，则提示“已保存，等待任务结束后自动刷新”或“需重启”。

### D 类：不建议热更新

- `DATABASE_URL`
- 数据库 driver / host / port / user / database。

处理策略：

- 保存到 `.env`。
- 更新前端状态为“已保存，需重启切换数据库”。
- 保留“测试连接”和“创建表结构”能力。
- 不在当前进程中替换 Flask app 的 SQLAlchemy engine。

## 后端设计

### 1. 新增配置 runtime 管理模块

新增文件：

- `server/services/runtime_config.py`

职责：

- 判断每个配置 key 的生效策略。
- 写入 env 后执行对应热更新 hook。
- 返回前端可展示的生效结果。

建议结构：

```python
# server/services/runtime_config.py

HOT_ENV_KEYS = {
    'REDIS_KEY_PREFIX',
    'OPENAI_API_KEY',
    'DEEPSEEK_API_KEY',
    'DASHSCOPE_API_KEY',
}

RELOADABLE_KEYS = {
    'REDIS_URL',
    'CHROMADB_PERSIST_DIR',
}

RESTART_REQUIRED_KEYS = {
    'DATABASE_URL',
}


def apply_runtime_updates(updates):
    results = []

    if 'REDIS_URL' in updates:
        reset_redis_client()
        results.append({
            'key': 'REDIS_URL',
            'status': 'reloaded',
            'message': 'Redis 连接已重建',
        })

    if any(k in updates for k in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY')):
        reset_embeddings()
        reset_vector_stores()
        results.append({
            'key': 'EMBEDDINGS',
            'status': 'reloaded',
            'message': 'Embedding 与向量检索客户端将在下次请求重建',
        })

    if 'CHROMADB_PERSIST_DIR' in updates:
        reset_vector_stores()
        results.append({
            'key': 'CHROMADB_PERSIST_DIR',
            'status': 'reloaded',
            'message': '向量库缓存已清空，下次访问使用新目录',
        })

    if 'DATABASE_URL' in updates:
        results.append({
            'key': 'DATABASE_URL',
            'status': 'restart_required',
            'message': '数据库连接已保存，需重启后切换当前运行数据库',
        })

    for key in HOT_ENV_KEYS.intersection(updates):
        if key not in {r['key'] for r in results}:
            results.append({
                'key': key,
                'status': 'hot_applied',
                'message': '已更新当前进程环境变量',
            })

    return results
```

### 2. Redis 增加 reset hook

修改：

- `server/services/redis_client.py`

新增：

```python
def reset_redis_client():
    global _client, _unavailable_until
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _unavailable_until = 0.0
```

保存 `REDIS_URL` 后调用该 hook。

好处：

- 下次 `get_redis()` 会读取新的 `os.environ['REDIS_URL']`。
- 不需要重启即可测试新的 Redis。
- 失败 backoff 会被清空，不会因为旧连接失败继续等待 60 秒。

### 3. Embedding 和向量库增加 reset hook

当前已有：

- `server/services/memory/embeddings.py::reset_embeddings`

建议补充：

- `server/services/memory/vector_store.py::reset_vector_stores`

实现：

```python
def reset_vector_stores():
    with _stores_lock:
        _stores.clear()
```

保存以下 key 后调用：

- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `CHROMADB_PERSIST_DIR`

### 4. 配置保存接口返回生效结果

修改：

- `server/routes/system.py::update_config`

当前返回：

```json
{
  "message": "配置已保存，需要重启服务生效",
  "updated": ["DATABASE_URL", "REDIS_URL"]
}
```

建议返回：

```json
{
  "message": "配置已保存",
  "updated": ["DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY"],
  "effects": [
    {
      "key": "DATABASE_URL",
      "status": "restart_required",
      "message": "数据库连接已保存，需重启后切换当前运行数据库"
    },
    {
      "key": "REDIS_URL",
      "status": "reloaded",
      "message": "Redis 连接已重建"
    },
    {
      "key": "EMBEDDINGS",
      "status": "reloaded",
      "message": "Embedding 与向量检索客户端将在下次请求重建"
    }
  ],
  "restart_required": true
}
```

后端逻辑：

```python
_write_env(updates)
effects = apply_runtime_updates(updates)
restart_required = any(e['status'] == 'restart_required' for e in effects)
return jsonify({
    'message': '配置已保存',
    'updated': list(updates.keys()),
    'effects': effects,
    'restart_required': restart_required,
})
```

### 5. 增加运行时配置状态接口

新增：

```http
GET /api/system/config/effects
```

用途：

- 前端切换到系统配置页时，可以知道当前是否有待重启配置。
- 保存后刷新状态。

返回：

```json
{
  "restart_required": true,
  "pending_restart_keys": ["DATABASE_URL"],
  "hot_reloadable_keys": [
    "REDIS_URL",
    "REDIS_KEY_PREFIX",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "CHROMADB_PERSIST_DIR"
  ]
}
```

第一阶段可以不做持久化 pending 状态，只根据“本次保存返回”展示。第二阶段再落地到 `.env.state` 或内存变量。

## 前端设计

### 1. 保存后展示分项生效结果

修改：

- `web/src/components/settings/SystemConfigPanel.vue`

新增状态：

```js
const configEffects = ref([])
const restartRequired = ref(false)
```

保存后：

```js
const { data } = await systemApi.updateConfig(payload)
configEffects.value = data.effects || []
restartRequired.value = !!data.restart_required
saved.value = true

if (restartRequired.value) {
  message.warning('部分配置已保存，需重启后生效')
} else {
  message.success('配置已保存并已热更新')
}
```

### 2. 替换“一律重启”提示

当前：

```vue
<a-button v-if="saved" type="primary" danger @click="handleRestart">
  立即重启服务
</a-button>
<span v-if="saved && !restarting" class="hint">配置已保存，重启后生效</span>
```

建议改为：

```vue
<a-alert
  v-if="configEffects.length"
  type="info"
  show-icon
  message="配置保存结果"
>
  <template #description>
    <div v-for="effect in configEffects" :key="effect.key">
      <a-tag :color="effect.status === 'restart_required' ? 'orange' : 'green'">
        {{ effect.status === 'restart_required' ? '需重启' : '已生效' }}
      </a-tag>
      {{ effect.key }}：{{ effect.message }}
    </div>
  </template>
</a-alert>

<a-button
  v-if="restartRequired"
  type="primary"
  danger
  @click="handleRestart"
  :loading="restarting"
>
  重启以应用剩余配置
</a-button>
```

### 3. 不同配置区域展示不同提示

数据库区域：

```text
数据库连接影响主数据源。保存后会写入配置，但当前运行数据库需重启后切换。
```

Redis 区域：

```text
Redis 连接支持热更新。保存后会重建 Redis client。
```

RAG 区域：

```text
Embedding Key 支持热更新。ChromaDB 目录保存后会清空向量库缓存，下次检索重建连接。
```

### 4. 保存 payload 粒度优化

当前前端保存时会尽量发送 database / redis / rag。建议进一步区分 dirty 字段：

- 只发送用户改过的区域。
- 避免用户只改 RAG API key，却因为数据库字段为空而触发 `DATABASE_URL=''`。
- 保存按钮旁显示“将更新：Redis、RAG”。

建议新增：

```js
const dirtySections = reactive({
  database: false,
  redis: false,
  rag: false,
})
```

各输入项 `@change` 标记对应 section dirty。

第一阶段可以先不做，第二阶段补。

## 推荐实施阶段

### 阶段一：最小热更新

目标：保存 Redis 和 RAG key 不再要求重启。

后端：

- 新增 `reset_redis_client()`。
- 新增 `reset_vector_stores()`。
- 复用已有 `reset_embeddings()`。
- 新增 `runtime_config.apply_runtime_updates()`。
- `PUT /api/system/config` 返回 `effects` 和 `restart_required`。

前端：

- 保存后展示分项结果。
- 只有 `restart_required=true` 才展示重启按钮。

验收：

- 修改 `REDIS_URL` 后，不重启即可 `GET /api/system/health` 看到新连接状态。
- 修改 `REDIS_KEY_PREFIX` 后，新生成的 Redis key 使用新 prefix。
- 修改 `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` 后，下一次 RAG indexing 使用新 embedding client。
- 只保存 RAG key 时，不再显示“重启后生效”。

### 阶段二：向量库目录与任务安全

目标：更安全地处理 `CHROMADB_PERSIST_DIR`。

后端：

- 引入轻量 runtime task registry，记录正在运行的 RAG indexing / search。
- 如果没有进行中任务，保存后清空 vector store cache。
- 如果有任务，返回 `pending_reload`。

返回示例：

```json
{
  "key": "CHROMADB_PERSIST_DIR",
  "status": "pending_reload",
  "message": "当前有 RAG 任务运行，任务结束后刷新向量库；必要时可重启"
}
```

### 阶段三：数据库切换体验优化

目标：数据库仍需重启，但体验更清楚。

后端：

- 保存 `DATABASE_URL` 后返回 `restart_required`。
- `GET /api/system/config` 返回：
  - `configured_database`
  - `running_database`
  - `database_pending_restart`

前端：

- 如果配置文件中的数据库和当前运行数据库不同，显示：

```text
已保存新的数据库连接，但当前服务仍运行在 SQLite。重启后切换到 MySQL。
```

这比“配置已保存，重启后生效”更具体。

### 阶段四：可选数据库热切换

不推荐作为近期目标。若将来确实要做，需要满足：

- 暂停后台任务。
- 关闭 SSE / 生成队列或等待 drain。
- `db.session.remove()`。
- dispose 旧 engine。
- 重配 Flask app SQLAlchemy URI。
- 新 engine 建表检查。
- 失败时回滚到旧 engine。

这部分风险高，收益低，除非系统要变成长期运行的服务端平台，否则重启更稳。

## 后端测试方案

新增测试：

- `server/tests/test_system_config_hot_reload.py`

测试点：

1. 保存 `REDIS_KEY_PREFIX`：
   - `.env` 写入。
   - `os.environ` 更新。
   - response `restart_required=false`。

2. 保存 `REDIS_URL`：
   - 调用 `reset_redis_client`。
   - response status 为 `reloaded`。

3. 保存 embedding key：
   - 调用 `reset_embeddings`。
   - 调用 `reset_vector_stores`。
   - response status 为 `reloaded`。

4. 保存 `DATABASE_URL`：
   - response `restart_required=true`。
   - status 为 `restart_required`。
   - 不尝试替换 SQLAlchemy engine。

5. 混合保存：
   - `DATABASE_URL + REDIS_URL` 同时保存时，Redis 热更新，数据库提示重启。

运行：

```bash
uv run pytest server/tests/test_system_config_hot_reload.py -v
```

回归：

```bash
uv run pytest server/tests/test_novel_graph.py server/tests/test_novel_chapter.py server/tests/test_novel_outline.py -q
cd web && pnpm run build
```

## 前端验证方案

手工验证：

1. 只修改 Redis prefix。
   - 保存后不出现重启按钮。
   - 显示“已热更新”。

2. 只修改 RAG API key。
   - 保存后不出现重启按钮。
   - 下次记忆索引重建 embedding client。

3. 修改数据库 host/database。
   - 保存后出现重启按钮。
   - 显示“数据库需重启后切换”。

4. 同时修改 Redis 和数据库。
   - Redis 显示已热更新。
   - 数据库显示需重启。
   - 只有一个“重启以应用剩余配置”按钮。

## 风险与处理

### 风险一：热更新 Redis 时旧任务仍持有旧 client

处理：

- `reset_redis_client()` 只影响后续 `get_redis()`。
- 已经拿到旧 client 的短请求可以自然结束。
- 后台长任务尽量每次操作时重新 `get_redis()`，避免长期持有。

### 风险二：Embedding key 切换后旧 vector store 仍使用旧 embeddings

处理：

- 保存 embedding key 后同时 `reset_embeddings()` 和 `reset_vector_stores()`。
- 下次 `get_vector_store(project_id)` 会重新创建 store。

### 风险三：前端误以为数据库已经热切

处理：

- API 明确返回 `restart_required=true`。
- 前端数据库区域显示“当前运行数据库”和“已保存数据库”。
- 不使用“已生效”描述数据库配置。

### 风险四：`.env` 与 `os.environ` 优先级混乱

处理：

- 保存时继续 `_write_env` 同步 `.env` 和 `os.environ`。
- `GET /api/system/config` 可以继续用 `_effective_env()` 展示配置文件 + 当前进程环境。
- 但数据库区域额外返回 running status，避免误判。

## 最终建议

近期最优方案不是“所有配置都热更新”，而是：

- Redis 和 RAG 相关配置热更新。
- 数据库配置保存后仍要求重启。
- 前端展示分项生效结果。
- 后端统一 runtime reload hooks，避免每个路由自己处理 client 生命周期。

这样可以显著减少不必要的后端重启，同时不把数据库连接池和后台任务一致性问题变成隐藏风险。

