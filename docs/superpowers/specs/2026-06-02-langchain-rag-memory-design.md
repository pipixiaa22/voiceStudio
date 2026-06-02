# LangChain RAG 长期记忆系统设计

## 概述

为小说续写模块引入 LangChain RAG 长期记忆系统，解决长篇创作中的上下文膨胀、设定冲突、人设漂移等问题。保留现有 ModelProvider/ModelRegistry 抽象，新增 `server/services/memory/` 作为 RAG 编排层。

**目标**：
- 章节生成可以检索项目长期记忆
- 章节确认后自动抽取新事实
- 检测设定冲突和人设漂移
- 多步骤可观察、可重试的 AI 工作流

**范围**：P0-P3 全部四个阶段

## 架构

### 整体分层

```text
Flask routes (novels/memories.py)
  -> business services (novel/)
    -> memory/RAG services (memory/)
      -> existing ModelProvider for LLM calls, OR LangChain chat model adapter
    -> existing TTS/video/discovery services (untouched)
```

### 新增文件结构

```text
server/services/memory/
  __init__.py
  document_types.py      # 长期记忆文档类型定义
  chunker.py             # 章节/设定切片
  embeddings.py          # 统一 embedding 调用
  vector_store.py        # Chroma 封装
  retriever.py           # 多路检索 + 排序压缩
  rag_chain.py           # LangChain 编排：检索 -> prompt -> LLM -> 输出解析
  memory_writer.py       # AI 生成或用户确认后写入长期记忆
  conflict_detector.py   # 设定冲突/人设漂移检测

server/models/novel/memory.py     # NovelMemory + NovelMemoryChange
server/routes/novels/memories.py  # 记忆 CRUD + 检索预览 + 变更确认
```

### 依赖

```toml
dependencies = [
    "langchain",
    "langchain-openai",
    "langchain-community",
    "chromadb",
    "langgraph",  # P3 阶段
]
```

### Embedding 模型选择

使用 OpenAI-compatible embedding API，复用现有 provider 配置：
- 优先使用 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` 对应的 embedding 模型
- Chroma 本地持久化路径：`data/chromadb/`（与 `data.db` 同级）
- 测试时使用 Chroma in-memory 模式

## 数据模型

### NovelMemory

结构化长期记忆元数据。数据库为主存储，向量库只存检索索引。

```python
class NovelMemory(db.Model):
    __tablename__ = 'novel_memories'

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(db.String(36), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    # project, chapter, outline, entity, event, manual_note
    source_id = db.Column(db.String(36), nullable=True)
    memory_type = db.Column(db.String(40), nullable=False)
    # world_rule, character, relationship, event, foreshadowing, style, summary
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=3)  # 1-5
    status = db.Column(db.String(20), nullable=False, default='active')
    # active, archived, superseded
    vector_status = db.Column(db.String(20), nullable=False, default='pending')
    # pending, indexed, failed
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
```

### NovelMemoryChange

AI 抽取待确认记录，复用现有 GraphChange 的 accept/reject 模式。

```python
class NovelMemoryChange(db.Model):
    __tablename__ = 'novel_memory_changes'

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(db.String(36), nullable=False, index=True)
    memory_id = db.Column(db.String(36), nullable=True, index=True)
    change_type = db.Column(db.String(30), nullable=False)
    # add, modify, archive
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False)
    # ai_extract, user_manual
    status = db.Column(db.String(20), nullable=False, default='pending')
    # pending, confirmed, rejected
    created_at = db.Column(db.DateTime, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
```

### 向量库元数据（Chroma）

每个 chunk 包含：

```json
{
  "project_id": "project-id",
  "memory_id": "memory-id",
  "source_type": "chapter",
  "source_id": "chapter-id",
  "memory_type": "event",
  "chapter_index": 12,
  "entity_ids": ["character-id"],
  "event_ids": ["event-id"],
  "importance": 4,
  "updated_at": "2026-06-02T12:00:00+08:00"
}
```

必须按 `project_id` 过滤，避免不同小说工程的记忆串库。

## RAG 检索策略

### 检索输入

章节生成时，retriever 输入包含：
- 当前小说项目 ID
- 当前章节 ID
- 当前章节大纲
- 前一章摘要
- 当前出场人物
- 当前事件目标
- 用户临时指令
- 需要回收或推进的伏笔

### 多路检索

按记忆类型分别召回，再排序压缩：

| 检索来源 | 目的 |
|---|---|
| 人物记忆 | 防止人设漂移 |
| 世界观规则 | 防止设定冲突 |
| 事件时间线 | 保持因果连续 |
| 伏笔 | 提醒埋设和回收 |
| 文风样例 | 保持风格一致 |
| 前文摘要 | 保持章节衔接 |

### 上下文预算

与现有 `context_builder.py` 的 `_truncate` 模式一致，按优先级分配：

| 上下文块 | 建议占比 |
|---|---|
| 当前章节大纲 | 15% |
| 前文摘要 | 15% |
| 人物和关系 | 20% |
| 世界观规则 | 15% |
| 事件时间线 | 20% |
| 伏笔和用户指令 | 15% |

### 与现有 context_builder 的关系

- `context_builder.py` 继续负责结构化数据查询（SQL）
- `memory/retriever.py` 负责语义检索（向量）
- `memory/rag_chain.py` 合并两者结果后组装最终 prompt

## 生成链路改造

### 当前链路

```text
chapter_generator.py
  -> context_builder.py
  -> get_llm_provider()
  -> provider.complete()
  -> 保存章节版本
```

### 改造后链路

```text
chapter_generator.py
  -> context_builder.py 构建基础上下文（SQL 结构化数据）
  -> memory/retriever.py 检索长期记忆（向量语义数据）
  -> memory/rag_chain.py 合并上下文 + 组装 prompt + 调用 LLM
  -> 保存章节版本
  -> graph_extractor.py 抽取实体/事件变化（已有）
  -> memory_writer.py 生成记忆变更（新增）
  -> 用户确认或自动写回
```

关键改动：`chapter_generator.py` 中的 `generate_single_version()` 函数，在构建 context 后、调用 LLM 前，插入 RAG 检索步骤。`rag_chain.py` 提供一个 `generate_with_memory()` 函数替代直接的 `provider.complete()` 调用。

## Prompt 结构

章节生成 prompt 固定为：

```text
你是长篇小说创作助手。你必须遵守长期记忆和当前大纲，不得随意改变已确认设定。

【项目设定】...

【当前章节目标】...

【长期记忆】
1. 人物设定
2. 世界观规则
3. 事件时间线
4. 未回收伏笔
5. 风格要求

【前文摘要】...

【用户指令】...

【输出要求】
- 只输出正文 Markdown。
- 不要解释。
- 不要改写已确认事实。
- 如果信息不足，用合理留白，不要创造冲突设定。
```

结构化抽取 prompt 输出 JSON：

```json
{
  "new_memories": [],
  "updates": [],
  "conflicts": [],
  "foreshadowing": [],
  "events": []
}
```

## API 设计

新增路由模块 `server/routes/novels/memories.py`：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/novels/<pid>/memories` | 记忆列表（支持 memory_type/source_type/status/keyword 筛选） |
| POST | `/api/novels/<pid>/memories` | 新增手动记忆 |
| PATCH | `/api/novels/<pid>/memories/<mid>` | 更新记忆 |
| DELETE | `/api/novels/<pid>/memories/<mid>` | 删除记忆 |
| POST | `/api/novels/<pid>/memories/reindex` | 重建向量索引 |
| POST | `/api/novels/<pid>/memories/search` | 检索预览（调试 RAG 质量） |
| GET | `/api/novels/<pid>/memory-changes` | 待确认变更列表 |
| POST | `/api/novels/<pid>/memory-changes/<cid>/confirm` | 确认变更 |
| POST | `/api/novels/<pid>/memory-changes/<cid>/reject` | 拒绝变更 |

所有路由遵循现有模式：
- 验证 project 存在：`NovelProject.query.get_or_404(project_id)`
- 验证子资源属于同一项目
- 中文错误消息
- REST 标准状态码（201/200/204/400/404）

## 前端改造

### 新增组件

- `NovelMemoryPanel.vue` — 长期记忆管理（列表、筛选、CRUD）
- `NovelMemorySearch.vue` — 检索预览面板
- `NovelMemoryChangeReview.vue` — 待确认记忆变更面板（类似现有 NovelExtractionReviewModal）

### 修改组件

- `NovelWorkspace.vue` — 新增"记忆"模式（activeMode: 'memory'），在 top-center 的 segmented 中增加选项
- `NovelGenerationPanel.vue` — 增加"启用长期记忆"开关、"检索预览"按钮
- `NovelContextPanel.vue` — 显示引用的记忆片段

### Store 新增

```javascript
// 新增 state
memories: [],
memoryChanges: [],
memorySearchResults: [],
memoryLoading: false,

// 新增 actions
fetchMemories(pid, params)
createMemory(pid, data)
updateMemory(pid, mid, data)
deleteMemory(pid, mid)
searchMemories(pid, query)
fetchMemoryChanges(pid)
confirmMemoryChange(pid, cid)
rejectMemoryChange(pid, cid)
reindexMemories(pid)
```

### API 层新增

```javascript
// novelsApi 新增
listMemories: (pid, params) => api.get(`/novels/${pid}/memories`, { params }),
createMemory: (pid, data) => api.post(`/novels/${pid}/memories`, data),
updateMemory: (pid, mid, data) => api.patch(`/novels/${pid}/memories/${mid}`, data),
deleteMemory: (pid, mid) => api.delete(`/novels/${pid}/memories/${mid}`),
searchMemories: (pid, data) => api.post(`/novels/${pid}/memories/search`, data),
reindexMemories: (pid) => api.post(`/novels/${pid}/memories/reindex`),
listMemoryChanges: (pid) => api.get(`/novels/${pid}/memory-changes`),
confirmMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/confirm`),
rejectMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/reject`),
```

## P3 多步骤工作流（LangGraph）

将章节生成升级为可观察、可重试的 AI 工作流：

```text
retrieve_memory -> plan_chapter -> draft_chapter -> review_consistency -> revise_draft -> extract_memory_changes -> persist_version
```

使用 LangGraph 的 `StateGraph` 管理节点状态，每个节点可以独立重试，支持中途人工干预。

## 分阶段实施

### P0：最小可用 RAG

1. 增加 LangChain 和 Chroma 依赖
2. 新增 NovelMemory 和 NovelMemoryChange 模型
3. 新增 `server/services/memory/` 基础模块
4. 支持手动新增记忆并写入向量库
5. 在 chapter_generator.py 中检索相关记忆并拼入 prompt
6. 增加 `/memories/search` 调试接口
7. 前端：记忆管理面板 + 检索预览

### P1：章节确认后自动抽取记忆

1. 在章节确认流程后调用结构化抽取
2. 生成 NovelMemoryChange 待确认记录
3. 前端增加"待确认记忆变更"面板
4. 用户确认后写入 NovelMemory 并更新向量库

### P2：冲突检测与记忆压缩

1. 新增 conflict_detector.py
2. 生成前检查当前章节目标与长期记忆是否冲突
3. 对旧章节正文做摘要压缩
4. 为高频记忆设置 importance 自动调整

### P3：多步骤工作流

1. 引入 LangGraph
2. 实现 retrieve_memory -> plan_chapter -> draft_chapter -> review_consistency -> revise_draft -> extract_memory_changes -> persist_version 节点
3. 支持节点独立重试和人工干预

## 关键风险

1. **依赖漂移** — LangChain 生态更新快，集中在 memory/ 封装
2. **召回污染** — 必须严格按 project_id 过滤
3. **长期记忆写错** — 默认 AI 提取后人工确认，不自动写回
4. **成本和延迟** — 第一阶段不做 rerank，优先验证价值
5. **过度依赖向量检索** — 结构化数据继续走 SQL，RAG 负责语义补充

## 测试计划

### 单元测试
- chunker 切片稳定性
- vector_store project 过滤
- retriever 召回排序
- memory_writer 写入和状态转换
- conflict_detector 冲突检测

### 集成测试
- 新增记忆后能被 /memories/search 检索
- A 项目的记忆不会被 B 项目召回
- 章节生成启用 RAG 后 prompt 包含相关记忆
- 章节确认后生成待确认记忆变更

### 回归测试
- `uv run pytest server/tests/ -q`
- `cd web && pnpm run build`
