# 修仙短视频热点采集与视频生成联动方案

## 背景

当前项目已经具备较完整的“文本 -> 字幕/TTS -> 静态图视频 -> MP4/剪映素材包”生产链路：

- `splitter.py` / `srt.py` 负责字幕切分和 SRT 生成。
- `server/routes/video.py` 提供视频模板、图片上传、异步视频任务和下载接口。
- `server/services/video_job.py` 负责后台生成视频、合成语音、构建字幕时间轴和打包剪映素材。
- `web/src/components/video/VideoGenerateModal.vue` 已经是模板、画面、音色、音频、预览、生成的多步向导。
- `server/models.py` 已有 `Text`、`Tag`、`Folder`、`VideoJob`、`VideoAsset` 等模型，适合承接“采集结果 -> 文本库 -> 视频生成”的联动。

新增功能的核心目标不是搬运别人视频，而是把热门平台上“单图 + 字幕 + 语音”的修仙小说短视频作为选题、结构、标题和节奏参考，辅助生成原创脚本，并把脚本和素材参数送入现有视频生成流程。

## 合规边界

这个功能建议明确命名为“热点采集/灵感分析”，不要命名为“搬运/下载/复刻”。默认规则：

1. 优先使用官方开放平台、用户授权接口或用户手动提供的链接。
2. 默认只保存元数据：平台、URL、标题、作者、封面、发布时间、播放/点赞/评论等公开指标、关键词、标签、摘要和分析结果。
3. 不默认下载原视频、原音频、原字幕，也不把他人作品直接导入生成链路。
4. 如果用户拥有授权素材，可以通过“手动上传视频/图片/字幕”进入更深度分析。
5. LLM 只做原创改写、结构抽象和选题拓展，避免逐句复制原文。
6. 所有采集任务必须有限速、缓存、失败退避、来源记录和可删除机制。

外部平台能力会变化，接入前需要再次核对官方文档和服务条款。当前可参考：

- [抖音开放平台概述](https://developer.open-douyin.com/docs/resource/zh-CN/developer/introduction/overview)说明其能力开放包含视频数据、用户数据和榜单等能力；[抖音搜索能力](https://developer.open-douyin.com/docs/resource/zh-CN/dop/ability/search-management/item-search)文档同时说明“实验能力，现不对外开放”，并限制爬取、缓存、下载等行为。
- [YouTube Data API `search.list`](https://developers.google.com/youtube/v3/docs/search/list) 提供官方搜索接口，可按关键词、发布时间、区域、排序等参数获取视频结果，但每次搜索调用有 quota 成本。
- [B 站开放平台](https://openhome.bilibili.com/doc)公开入口包含 OPEN API、视频稿件发布/删除/查询和数据开放等能力，但通用全站搜索/热榜类能力需要以官方可申请能力为准。
- [快手开放平台](https://open.kuaishou.com/platform/openApi)页面需要 JavaScript 渲染，具体可用接口需要在接入时通过官方控制台确认。

## 目标

构建一个“热门修仙短视频采集 -> 热点分析 -> 原创脚本生成 -> 现有视频生成”的闭环：

```text
平台关键词/榜单/手动链接
-> 采集候选视频元数据
-> 识别单图字幕语音类内容
-> 分析标题、开头钩子、剧情结构、字幕节奏、热度指标
-> 生成原创选题和脚本草稿
-> 导入 Text 文本库并打标签
-> 预填 VideoGenerateModal 参数
-> 生成 MP4 + 剪映素材包
```

## 非目标

1. 不做绕过登录、验证码、反爬或平台风控的强爬虫。
2. 不承诺下载第三方平台视频源文件。
3. 不做批量搬运或自动洗稿。
4. 不在第一阶段做完整视频画面理解模型。
5. 不把采集服务做成公开 SaaS，只面向本地创作辅助流程。

## 三种可行路线

### 路线 A：官方 API / 授权接口优先

特点：稳定性和合规性最好，适合长期使用。

适用平台：

- YouTube：可用官方 Data API 搜索关键词，如 `修仙小说`、`仙帝重生`、`玄幻有声小说` 等。
- 抖音：优先接入开放平台已开放的视频数据、用户授权数据、榜单能力；通用视频搜索如不可开放，则不作为第一阶段依赖。
- B 站：优先确认开放平台账号下可申请的视频数据/搜索/稿件数据能力。
- 快手：以开放平台控制台实际可申请能力为准。

优点：

- 最容易做限流、缓存、错误处理和测试。
- 结果结构化，适合入库和后续分析。
- 后续可扩展成定时监控。

缺点：

- 平台申请门槛、配额和可用字段受限制。
- 国内短视频平台的通用搜索/热榜能力未必对外开放。

### 路线 B：手动 URL + 半自动分析

特点：第一阶段最推荐。用户从平台复制链接，本系统只解析链接、保存来源、抓取可合规展示的公开元数据；如需要深度分析，由用户上传其拥有授权的视频或截图。

优点：

- 快速落地，不依赖各平台审批。
- 风险低，功能可控。
- 适合创作者日常把看到的爆款样本收进“灵感库”。

缺点：

- 不是真正自动化热榜抓取。
- 热点发现仍依赖用户自己找样本。

### 路线 C：浏览器自动化爬取

特点：技术上可做，但不建议作为默认方案。

优点：

- 覆盖面广，能模拟搜索、滚动和页面采集。

缺点：

- 容易触碰平台服务条款和反爬策略。
- 页面结构经常变化，维护成本高。
- 账号、验证码、IP、风控问题会不断出现。

结论：浏览器自动化只适合作为“内部、低频、人工触发、可关闭”的补充工具，不作为核心架构。

## 推荐方案

采用“路线 B 起步，路线 A 扩展，路线 C 谨慎可插拔”的方案。

第一阶段先做一个本地“热点采集台”：

1. 用户输入关键词或粘贴视频链接。
2. 系统通过平台 Connector 获取可用元数据。
3. 对候选视频做“修仙短视频小说”相关性评分。
4. 对“单图 + 字幕 + 语音”形态做轻量识别。
5. 生成原创标题、开头钩子、剧情大纲、分段脚本。
6. 一键导入 `Text`，自动加标签，如 `修仙`、`热点参考`、`单图视频`、平台名。
7. 一键进入现有 `VideoGenerateModal`，预填模板、音色、字幕长度、场景图建议和来源上下文。

## 功能模块

### 1. 热点采集台

前端新增页面或入口：`web/src/views/Discovery.vue`。

主要能力：

- 平台选择：抖音、快手、B 站、YouTube、手动链接。
- 关键词管理：修仙、玄幻、仙帝、重生、废柴逆袭、炼气、筑基、女帝、宗门、天劫、系统流。
- 结果列表：标题、平台、作者、封面、发布时间、播放量、点赞量、评论量、相关性评分、形态评分。
- 操作：收藏、分析、生成原创脚本、导入文本、进入视频生成。

### 2. Connector 抽象层

新增目录：

```text
server/services/discovery/
  __init__.py
  models.py
  registry.py
  base.py
  manual_url.py
  youtube.py
  douyin.py
  bilibili.py
  kuaishou.py
  scoring.py
  analyzer.py
  script_adapter.py
```

核心接口：

```python
class DiscoveryConnector:
    platform_key: str

    def search(self, query: str, limit: int, cursor: str | None = None) -> DiscoveryPage:
        raise NotImplementedError

    def resolve_url(self, url: str) -> DiscoveryItem:
        raise NotImplementedError
```

`DiscoveryItem` 建议字段：

```json
{
  "platform": "douyin",
  "source_url": "https://www.douyin.com/video/1234567890",
  "source_id": "平台视频ID",
  "title": "标题",
  "author_name": "作者",
  "cover_url": "封面URL",
  "published_at": "2026-05-27T12:00:00+08:00",
  "duration": 68.2,
  "stats": {
    "views": 120000,
    "likes": 8000,
    "comments": 300,
    "shares": 1200
  },
  "tags": ["修仙", "重生"],
  "raw": {}
}
```

### 3. 数据模型

建议新增模型：

```text
DiscoverySource
DiscoveryQuery
DiscoveryItem
DiscoveryAnalysis
```

职责：

| 模型 | 职责 |
|------|------|
| `DiscoverySource` | 平台配置、是否启用、鉴权方式、限流策略 |
| `DiscoveryQuery` | 用户发起的关键词/链接采集任务 |
| `DiscoveryItem` | 单条候选视频元数据和热度指标 |
| `DiscoveryAnalysis` | 相关性评分、形态识别、脚本分析和原创改写结果 |

第一阶段可以只落 SQLite，跟现有 `Text`、`Tag`、`Folder` 共用数据库。后续若采集量变大，再拆到单独表和定期清理任务。

### 4. 相关性评分

用于判断“是不是修仙短视频小说”。

基础规则：

- 标题/标签命中：修仙、玄幻、仙帝、仙尊、重生、渡劫、炼气、筑基、金丹、元婴、宗门、师尊、女帝、系统、逆袭。
- 标题结构命中：“开局”、“我竟然”、“一口气看完”、“穿越成”、“被逐出宗门”、“三千年后归来”。
- 时长区间：30 秒到 8 分钟优先。
- 互动指标：播放、点赞、评论、收藏/分享按平台归一化。
- 发布时间：近 7 天权重更高，近 30 天可作为趋势样本。

输出：

```json
{
  "xianxia_score": 0.86,
  "hot_score": 0.72,
  "reason": ["标题命中仙帝/重生", "近7天高互动", "时长符合短视频小说"]
}
```

### 5. 单图字幕语音形态识别

第一阶段使用轻量规则，不依赖下载原视频：

- 标题/简介含“一张图”、“有声小说”、“小说推文”、“书荒推荐”、“一口气看完”等关键词。
- 封面是人物/场景图 + 大字标题的概率。
- 平台标签和作者历史内容偏小说推文。

如果用户上传授权视频，启用更准确的检测：

1. 用 ffmpeg 抽取每 3-5 秒一帧。
2. 计算相邻帧差异，画面变化长期低于阈值时判定为单图/近静态。
3. 用 OCR 检查底部字幕区域是否持续出现文本。
4. 用音频能量/ASR 检查是否有人声旁白。

输出：

```json
{
  "format_score": 0.81,
  "is_static_image_style": true,
  "has_subtitle_like_text": true,
  "has_narration": true,
  "confidence": "medium"
}
```

### 6. 热点分析与原创脚本生成

分析目标不是复制内容，而是提取可复用结构：

- 标题套路：爽点、冲突、身份反转。
- 开头钩子：前 3 秒要抛出的危机或反差。
- 剧情骨架：主角身份、压迫者、金手指、第一次反击、悬念。
- 字幕节奏：每句 12-20 字，短句优先。
- 视频参数建议：模板、声线、BGM 氛围、字幕密度。

输出到现有 `Text`：

```json
{
  "title": "原创标题",
  "content": "原创脚本正文",
  "tags": ["修仙", "热点参考", "原创改写"],
  "source_context": {
    "discovery_item_id": 123,
    "platform": "bilibili",
    "source_url": "https://www.bilibili.com/video/BV1xx411c7mD"
  }
}
```

### 7. 与现有视频生成联动

联动点：

1. `DiscoveryItem -> Text`
   - 点击“生成原创脚本”后创建或更新 `Text`。
   - 使用已有 `textsApi.create` / 后端 `server/routes/texts.py`。

2. `DiscoveryAnalysis -> VideoGenerateModal`
   - 推荐 `template_key`，例如 `xianxia_narration`。
   - 推荐字幕 `max_chars`，默认 16-20。
   - 推荐声线描述，例如“沉稳、有故事感的男声”或“清冷女声”。
   - 推荐场景图关键词，用户可上传自己的图。

3. `source_context -> VideoJob`
   - 在 `video_job.request_json` 里记录参考来源。
   - 在剪映素材包 manifest 里写入 `inspiration_sources`，方便用户追溯。

4. `VideoAsset`
   - 只保存用户自己上传或有授权的图片/音频/视频素材。
   - 平台封面默认作为远程引用，不复制入素材包，除非用户明确保存并确认授权。

## API 设计

新增蓝图：`server/routes/discovery.py`。

### GET /api/discovery/sources

返回平台启用状态和配置需求。

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

响应：

```json
{
  "query_id": 1,
  "items": [],
  "next_cursor": null
}
```

### POST /api/discovery/resolve-url

请求：

```json
{
  "url": "https://www.youtube.com/watch?v=abc123xyz00"
}
```

响应：单个 `DiscoveryItem`。

### POST /api/discovery/items/:id/analyze

生成相关性评分、形态评分和脚本分析。

### POST /api/discovery/items/:id/create-text

把分析结果转为原创文本库条目。

请求：

```json
{
  "mode": "original_script",
  "folder_id": 2,
  "tag_names": ["修仙", "热点参考"]
}
```

响应：

```json
{
  "text_id": 88,
  "title": "开局被逐出宗门，我在后山觉醒万古剑骨"
}
```

### POST /api/discovery/items/:id/create-video-job

可选能力：跳过文本编辑页，直接基于原创脚本创建视频任务。第一阶段不建议默认开放，优先让用户先看脚本。

## 前端流程

新增菜单入口：“热点采集”。

页面结构：

```text
顶部筛选区：平台 / 关键词 / 时间范围 / 时长 / 排序
左侧：关键词包和历史查询
中间：候选视频列表
右侧：分析面板
底部操作：收藏 / 生成原创脚本 / 导入文本 / 生成视频
```

和现有页面的关系：

- `TextList.vue` 可增加“来自热点采集”的筛选标签。
- `TextEdit.vue` 可显示来源参考信息。
- `VideoGenerateModal.vue` 接收可选 `prefill` 参数，自动填入模板、音色和场景建议。

## 后台任务

采集和分析可能耗时，建议使用现有 `VideoJob` 的思路新增轻量任务表，或者先用同步 API + 前端 loading。

第一阶段：

- 手动 URL 解析：同步。
- YouTube 搜索：同步，限制 `limit <= 20`。
- LLM 分析：同步或短任务。

第二阶段：

- 批量关键词监控：后台任务。
- 多平台搜索：后台任务。
- 授权视频抽帧/OCR/ASR：后台任务。

## 推荐实施阶段

### Phase 1：灵感库 MVP

目标：不用等待平台审批，也能把用户看到的爆款样本收进系统。

交付：

- `DiscoveryItem` / `DiscoveryAnalysis` 模型。
- 手动 URL 导入。
- YouTube 官方 API Connector。
- 关键词相关性评分。
- LLM 生成原创脚本。
- 一键创建 `Text`。
- 前端“热点采集”页面。

### Phase 2：平台 Connector 扩展

目标：按官方开放能力逐个平台接入。

交付：

- 抖音开放平台授权配置位。
- B 站开放平台配置位。
- 快手开放平台配置位。
- Connector 健康检查和限流配置。
- 统一错误提示：无权限、配额不足、平台能力未开放。

### Phase 3：授权素材深度分析

目标：对用户有权使用的视频/截图做形态识别。

交付：

- 上传授权视频。
- ffmpeg 抽帧。
- 静态画面检测。
- 字幕区域 OCR。
- ASR 或音频人声检测。
- 生成更准确的字幕节奏和视频参数建议。

### Phase 4：热点监控和批量生产

目标：把采集变成持续选题雷达。

交付：

- 关键词定时监控。
- 热度趋势图。
- 爆款标题模式统计。
- 批量生成原创选题。
- 批量导入文本库。

## 风险与控制

| 风险 | 控制方案 |
|------|----------|
| 平台接口不可用 | Connector 可插拔，手动 URL 和 YouTube 作为基础可用路径 |
| 版权风险 | 默认只存元数据和原创分析，不下载原视频/音频/字幕 |
| 平台条款变化 | 每个平台配置页显示“需确认官方授权和条款” |
| 热点质量低 | 相关性评分 + 人工收藏 + 黑名单关键词 |
| 生成内容同质化 | LLM 提示词要求换人物、换冲突、换世界观、换表达 |
| 采集任务过慢 | 限制单次数量，缓存结果，后台任务处理 |
| 数据膨胀 | 设置保留周期，支持批量删除历史采集结果 |

## 测试策略

后端：

- Connector 基类和 registry 单元测试。
- 手动 URL 平台识别测试。
- YouTube Connector 使用 mocked HTTP 响应测试。
- 相关性评分测试：命中修仙关键词、非相关内容、边界时长。
- `create-text` 路由测试：生成 `Text`、写入标签、保留来源上下文。
- 限流和错误映射测试。

前端：

- 热点采集页面空状态、加载态、错误态。
- 搜索结果列表展示。
- 分析面板展示。
- 创建文本成功后跳转到 `TextEdit`。
- `VideoGenerateModal` prefill 参数不破坏现有生成流程。

回归：

```bash
uv run pytest
cd web && pnpm run build
```

## 结论

这个功能可行，但建议定位为“热点采集 + 原创生产辅助”，不要做“自动爬取并复刻视频”。最稳的产品路线是：

1. 先做手动链接和 YouTube 官方 API，跑通灵感库闭环。
2. 用统一 Connector 抽象预留抖音、快手、B 站能力。
3. 把采集结果导入现有 `Text`，再复用现有视频生成向导和异步 `VideoJob`。
4. 后续再做授权素材抽帧、OCR、ASR 和趋势监控。

这样可以最大化复用当前代码资产，同时把合规风险、平台不确定性和维护成本压到最低。
