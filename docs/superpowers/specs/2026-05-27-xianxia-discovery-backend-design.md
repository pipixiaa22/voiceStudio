# 修仙短视频热点采集 - 后端实现设计（Phase 1 MVP）

## 范围

Phase 1 灵感库 MVP：手动 URL 导入 + YouTube API Connector + 关键词评分 + LLM 原创脚本生成 + 一键创建 Text。

不包含：抖音/B站/快手 Connector 实现、授权视频抽帧/OCR/ASR、热点监控和批量生产。

## 目录结构变更

将 `server/models.py` 重构为 `server/models/` 目录，新增 `server/routes/discovery.py` 和 `server/services/discovery/` 目录。

```
server/
├── models/                        # 从 models.py 重构为目录
│   ├── __init__.py                # 统一导出 db + 所有模型
│   ├── base.py                    # db = SQLAlchemy() 实例
│   ├── text.py                    # Text, Tag, text_tags
│   ├── folder.py                  # Folder
│   ├── video.py                   # VideoTemplate, VideoJob, VideoAsset
│   ├── provider.py                # CustomProvider
│   └── discovery.py               # DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis
├── routes/
│   ├── ...（现有 7 个路由文件不变）
│   └── discovery.py               # 新增 discovery_bp
├── services/
│   ├── ...（现有服务文件不变）
│   └── discovery/                 # 新增服务目录
│       ├── __init__.py
│       ├── base.py                # DiscoveryConnector ABC
│       ├── registry.py            # ConnectorRegistry
│       ├── manual_url.py          # ManualUrlConnector
│       ├── youtube.py             # YoutubeConnector
│       ├── scoring.py             # 相关性评分
│       ├── analyzer.py            # LLM 分析 + 原创脚本生成
│       └── script_adapter.py      # DiscoveryItem → Text 转换
```

### 重构约束

- `server/models/base.py` 只放 `db = SQLAlchemy()` 实例
- `server/models/__init__.py` 统一导出 `db` 和所有模型类
- 所有现有 import 路径 `from server.models import db, Text, ...` 保持不变
- 现有路由文件和 service 文件无需修改 import 语句

## 数据模型

### DiscoverySource

平台配置。

```python
class DiscoverySource(db.Model):
    __tablename__ = 'discovery_sources'

    id            # Integer, PK
    platform_key  # String(50), unique, not null  -- youtube/douyin/bilibili/kuaishou/manual
    display_name  # String(100), not null
    is_enabled    # Boolean, default True
    config_json   # Text, default '{}'            -- API key、限流参数等
    created_at    # DateTime, utcnow
    updated_at    # DateTime, utcnow, onupdate
```

### DiscoveryQuery

用户发起的采集任务。

```python
class DiscoveryQuery(db.Model):
    __tablename__ = 'discovery_queries'

    id            # Integer, PK
    query_type    # String(20), not null           -- 'keyword' | 'url'
    platform_key  # String(50), not null
    query_text    # String(500), not null           -- 关键词或 URL
    filters_json  # Text, default '{}'             -- 时间范围、时长、排序
    status        # String(20), default 'pending'  -- pending/running/completed/failed
    item_count    # Integer, default 0
    error_message # Text, nullable
    created_at    # DateTime, utcnow
```

### DiscoveryItem

单条候选视频元数据。

```python
class DiscoveryItem(db.Model):
    __tablename__ = 'discovery_items'

    id            # Integer, PK
    query_id      # Integer, FK → discovery_queries.id, nullable
    platform_key  # String(50), not null
    source_url    # String(1000), not null
    source_id     # String(200), nullable           -- 平台视频 ID
    title         # String(500), nullable
    author_name   # String(200), nullable
    cover_url     # String(1000), nullable
    published_at  # DateTime, nullable
    duration      # Float, nullable                 -- 秒
    stats_json    # Text, default '{}'              -- {"views":0,"likes":0,"comments":0,"shares":0}
    tags_json     # Text, default '[]'              -- ["修仙","重生"]
    raw_json      # Text, default '{}'              -- 平台原始返回
    is_favorited  # Boolean, default False
    created_at    # DateTime, utcnow
```

### DiscoveryAnalysis

分析结果。

```python
class DiscoveryAnalysis(db.Model):
    __tablename__ = 'discovery_analyses'

    id                    # Integer, PK
    item_id               # Integer, FK → discovery_items.id, unique, not null
    xianxia_score         # Float, default 0.0       -- 0-1 修仙相关性
    hot_score             # Float, default 0.0       -- 0-1 热度评分
    format_score          # Float, default 0.0       -- 0-1 单图字幕语音形态
    is_static_image_style # Boolean, default False
    score_reasons_json    # Text, default '[]'       -- 评分理由列表
    analysis_json         # Text, default '{}'       -- LLM 分析结果
    generated_title       # String(500), nullable    -- 原创标题
    generated_content     # Text, nullable           -- 原创脚本
    recommended_template  # String(50), nullable     -- 推荐模板 key
    recommended_voice_desc # String(200), nullable   -- 推荐声线描述
    recommended_max_chars # Integer, nullable        -- 推荐字幕长度
    created_at            # DateTime, utcnow
```

### Text 模型扩展

在现有 `Text` 模型新增可选字段：

```python
source_context_json = db.Column(db.Text, nullable=True)
```

存储结构：

```json
{
  "discovery_item_id": 123,
  "platform": "bilibili",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "generated_from": "discovery_analysis"
}
```

## 启动初始化

在 `app.py` 的 `create_app()` 中新增 `seed_discovery_sources()`，与 `seed_builtin_templates()` 同级调用。

内置平台：

| platform_key | display_name | is_enabled |
|--------------|-------------|------------|
| manual       | 手动链接     | True       |
| youtube      | YouTube     | True       |
| douyin       | 抖音        | False      |
| bilibili     | B站         | False      |
| kuaishou     | 快手        | False      |

抖音/B站/快手默认禁用，Phase 2 开放。按 `platform_key` 幂等插入，与 `seed_builtin_templates()` 模式一致。

## Connector 架构

### 基类

```python
# server/services/discovery/base.py

class DiscoveryConnector(ABC):
    platform_key: str
    display_name: str

    @abstractmethod
    def search(self, query: str, limit: int, filters: dict | None = None) -> list[dict]:
        """关键词搜索，返回 DiscoveryItem 字典列表"""
        ...

    @abstractmethod
    def resolve_url(self, url: str) -> dict:
        """解析单个 URL，返回 DiscoveryItem 字典"""
        ...

    def is_available(self) -> bool:
        """检查平台是否可用"""
        return True
```

### Registry

```python
# server/services/discovery/registry.py

class ConnectorRegistry:
    _connectors: dict[str, DiscoveryConnector] = {}

    @classmethod
    def register(cls, connector: DiscoveryConnector): ...

    @classmethod
    def get(cls, platform_key: str) -> DiscoveryConnector | None: ...

    @classmethod
    def get_all(cls) -> dict[str, DiscoveryConnector]: ...
```

在 `__init__.py` 中注册所有 connector 实例。

### ManualUrlConnector

解析用户粘贴的 URL，识别平台和视频 ID。

URL 匹配规则：

```python
URL_PATTERNS = {
    'douyin':   r'douyin\.com/video/(\d+)',
    'bilibili': r'bilibili\.com/video/(BV\w+)',
    'youtube':  r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)',
    'kuaishou': r'kuaishou\.com/short-video/(\w+)',
}
```

- `resolve_url()`: 正则匹配 → 提取平台+ID → 通过 oEmbed 或 HTTP GET 页面 meta 获取标题/封面
- `search()`: 不支持，抛出 `NotImplementedError`

元数据获取策略（按优先级）：

1. YouTube：oEmbed API (`https://www.youtube.com/oembed?url=...&format=json`)
2. 其他平台：HTTP GET 页面，解析 `<title>` 和 `og:title`/`og:image` meta 标签
3. 获取失败：只保存 URL 和平台信息，其他字段留空

### YoutubeConnector

调用 YouTube Data API v3。

- `search()`:
  - 端点：`https://www.googleapis.com/youtube/v3/search`
  - 参数：`part=snippet`, `q`, `type=video`, `maxResults`, `order=date`/`viewCount`, `publishedAfter`, `videoDuration=short`/`medium`
  - 返回结果用 `videos.list` 补充 `statistics` 和 `contentDetails`
- `resolve_url()`: 提取 video ID，调用 `videos.list` 获取详情
- `is_available()`: 检查 `DiscoverySource.config_json` 中是否有 API key

YouTube API key 从 `DiscoverySource.config_json` 读取，支持前端配置。

## 评分服务

```python
# server/services/discovery/scoring.py

def score_item(item: dict) -> dict:
    """
    返回 {
        "xianxia_score": 0-1,
        "hot_score": 0-1,
        "format_score": 0-1,
        "reasons": ["标题命中仙帝/重生", "近7天高互动", ...]
    }
    """
```

### xianxia_score 评分规则

关键词匹配（标题 + 标签）：

- 一级词（权重 0.3/个）：修仙、玄幻、仙帝、仙尊、重生、渡劫
- 二级词（权重 0.15/个）：炼气、筑基、金丹、元婴、宗门、师尊、女帝、系统、逆袭
- 结构词（权重 0.2/个）：开局、我竟然、一口气看完、穿越成、被逐出宗门、三千年后归来

上限 1.0。

### hot_score 评分规则

- 播放量归一化：按平台设基准（YouTube 10万=1.0，其他平台 50万=1.0）
- 互动率：(点赞 + 评论 + 分享) / 播放量，上限 0.3
- 时间衰减：7天内 ×1.0，30天内 ×0.7，更早 ×0.4

### format_score 评分规则

- 标题含"有声小说"/"小说推文"/"一张图"/"书荒推荐"：+0.4
- 时长 30s-8min：+0.3
- 标题含"一口气看完"/"完整版"/"全集"：+0.3

## LLM 分析服务

```python
# server/services/discovery/analyzer.py

def analyze_item(item: dict, score_result: dict) -> dict:
    """调用 LLM 生成分析结果和原创脚本"""
```

通过现有 `model_registry` 获取 LLM provider，调用 `provider.complete()`。

Prompt 结构：

```
你是一个修仙短视频小说的选题分析师。根据以下热门视频的元数据，分析其成功要素，并生成一个原创脚本。

## 视频信息
- 标题：{title}
- 平台：{platform}
- 时长：{duration}秒
- 播放量：{views}
- 标签：{tags}

## 要求
1. 分析标题套路（爽点/冲突/身份反转）
2. 分析开头钩子（前3秒要抛出的危机或反差）
3. 提取剧情骨架（主角身份、压迫者、金手指、第一次反击、悬念）
4. 建议字幕节奏（每句12-20字，短句优先）
5. 生成一个原创标题（不要复制原标题，要换人物/换冲突/换世界观）
6. 生成原创脚本正文（分段，每段对应一个字幕时间段）
7. 推荐视频参数

以 JSON 格式输出。
```

LLM 输出 JSON 结构：

```json
{
  "title_pattern": "身份反转 + 废柴逆袭",
  "hook": "被逐出宗门的少年，眼神冰冷",
  "plot_skeleton": "主角身份 → 压迫者 → 金手指觉醒 → 第一次反击 → 悬念",
  "subtitle_rhythm": "每句15字左右，短句为主",
  "generated_title": "开局被逐出宗门，我在后山觉醒万古剑骨",
  "generated_content": "第一段...\n第二段...\n...",
  "recommended_template": "xianxia_narration",
  "recommended_voice_desc": "沉稳、有故事感的男声",
  "recommended_max_chars": 16
}
```

## 脚本适配服务

```python
# server/services/discovery/script_adapter.py

def create_text_from_analysis(
    item: dict,
    analysis: dict,
    folder_id: int | None,
    tag_names: list[str]
) -> Text:
    """将分析结果转为 Text 模型实例"""
```

- 创建或复用 Tag（按 name 查找，不存在则创建）
- 设置 `source_context_json` 记录来源
- 返回 Text 实例，由调用方 commit

## API 路由

新增 `server/routes/discovery.py`，蓝图 `discovery_bp`。

### GET /api/discovery/sources

返回平台启用状态。

响应：

```json
[
  {"platform_key": "manual", "display_name": "手动链接", "is_enabled": true, "needs_api_key": false},
  {"platform_key": "youtube", "display_name": "YouTube", "is_enabled": true, "needs_api_key": true},
  {"platform_key": "douyin", "display_name": "抖音", "is_enabled": false, "needs_api_key": true}
]
```

### POST /api/discovery/search

请求：

```json
{
  "platform": "youtube",
  "query": "修仙小说 一张图",
  "limit": 20,
  "filters": {
    "published_days": 30,
    "duration_min": 30,
    "duration_max": 480
  }
}
```

流程：

1. 验证平台存在且启用
2. 创建 `DiscoveryQuery`（status=running）
3. 调用 `ConnectorRegistry.get(platform).search()`
4. 对每个结果调用 `scoring.score_item()`
5. 批量创建 `DiscoveryItem` + `DiscoveryAnalysis`（仅评分）
6. 更新 query status=completed, item_count
7. 返回 items 列表

响应：

```json
{
  "query_id": 1,
  "items": [
    {
      "id": 1,
      "platform_key": "youtube",
      "title": "...",
      "xianxia_score": 0.86,
      "hot_score": 0.72,
      "format_score": 0.5
    }
  ],
  "total": 20
}
```

### POST /api/discovery/resolve-url

请求：

```json
{
  "url": "https://www.youtube.com/watch?v=abc123xyz00"
}
```

流程：

1. 创建 `DiscoveryQuery`（query_type=url）
2. 调用 `ManualUrlConnector.resolve_url()`
3. 调用 `scoring.score_item()`
4. 创建 `DiscoveryItem` + `DiscoveryAnalysis`
5. 返回单个 item

### GET /api/discovery/items

支持筛选参数：`platform`、`min_score`、`favorited`、`page`、`per_page`

### GET /api/discovery/items/:id

返回 `DiscoveryItem` 完整信息。如果有 `DiscoveryAnalysis`，嵌套在 `analysis` 字段中返回：

```json
{
  "id": 1,
  "platform_key": "youtube",
  "title": "...",
  "source_url": "...",
  "stats": {"views": 120000, "likes": 8000},
  "tags": ["修仙", "重生"],
  "is_favorited": false,
  "analysis": {
    "xianxia_score": 0.86,
    "hot_score": 0.72,
    "format_score": 0.5,
    "generated_title": "...",
    "generated_content": "..."
  }
}
```

### POST /api/discovery/items/:id/analyze

触发 LLM 分析。

流程：

1. 获取 `DiscoveryItem`
2. 调用 `analyzer.analyze_item()`
3. 创建或更新 `DiscoveryAnalysis`
4. 返回完整分析结果

### POST /api/discovery/items/:id/create-text

创建原创文本。

请求：

```json
{
  "folder_id": 2,
  "tag_names": ["修仙", "热点参考"]
}
```

流程：

1. 获取 `DiscoveryItem` + `DiscoveryAnalysis`
2. 如果没有 `DiscoveryAnalysis` 或没有 `generated_content`，返回 400
3. 调用 `script_adapter.create_text_from_analysis()`
4. 创建 Text + 关联 Tag
5. 返回 text_id

响应：

```json
{
  "text_id": 88,
  "title": "开局被逐出宗门，我在后山觉醒万古剑骨"
}
```

### PUT /api/discovery/items/:id/favorite

切换收藏状态。

### GET /api/discovery/queries

返回历史查询列表，按 created_at 降序。

### DELETE /api/discovery/items/:id

删除采集记录及关联分析。

### 错误处理

遵循现有模式：

- 中文错误消息
- 400：参数校验失败（含平台未启用、缺少 API key、缺少分析结果等）
- 404：资源不存在
- 409：冲突（重复）
- 502：上游 API 调用失败（YouTube API 错误、URL 解析失败等）

## 测试策略

| 测试文件 | 覆盖内容 |
|----------|----------|
| `server/tests/test_discovery_models.py` | 模型 CRUD、外键关系、JSON 字段序列化 |
| `server/tests/test_discovery_scoring.py` | 评分规则：命中修仙关键词、非相关内容、边界时长、热度归一化 |
| `server/tests/test_discovery_connector.py` | Connector registry、ManualUrl URL 解析、mock YouTube API |
| `server/tests/test_discovery_routes.py` | 全部 10 个端点的请求/响应、错误处理 |
| `server/tests/test_discovery_analyzer.py` | LLM mock 分析流程、create-text 端到端 |

回归验证：

```bash
uv run pytest
cd web && pnpm run build
```

## 不在范围内

- 抖音/B站/快手 Connector 实现（Phase 2）
- 授权视频抽帧/OCR/ASR（Phase 3）
- 关键词定时监控和批量生产（Phase 4）
- 后台异步任务（Phase 1 使用同步 API + 前端 loading）
