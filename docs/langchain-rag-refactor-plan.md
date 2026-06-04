# LangChain 与 RAG 长期记忆改造方案

## 结论

当前项目后端已经有轻量的 `ModelProvider` / `ModelRegistry` 抽象，适合继续承载多供应商模型调用、TTS、音色设计、分镜规划、脚本润色等能力。后续要做小说和脚本的长期记忆时，建议引入 LangChain，但引入位置应放在 **RAG 与 AI 编排层**，而不是替换现有 provider 层。

推荐方向：

- 保留现有 `server/services/model_provider_base.py` 和 `server/services/model_registry.py`。
- 新增 `server/services/memory/` 作为长期记忆、向量检索、RAG 编排层。
- 小说续写、脚本生成、热点分析等需要长期上下文的模块逐步接入 RAG。
- TTS、音色复刻、视频渲染等非 RAG 能力继续走现有服务。

这样可以让 LangChain 用在最需要它的地方，同时避免把整个后端模型调用体系一次性改重。

## 为什么需要引入 LangChain

小说和脚本长期记忆不是简单的 prompt 拼接。随着章节、人物、事件、世界观和伏笔越来越多，系统需要解决这些问题：

- 长上下文无法全部塞进一次 LLM 请求。
- 不同章节需要检索不同人物、地点、事件、伏笔和前文摘要。
- 用户修改设定后，需要让后续生成优先使用最新事实。
- AI 生成章节后，需要把新事实写回长期记忆。
- 生成前需要检查设定冲突、人设漂移、事件因果断裂。
- 后续可能需要多步骤工作流：检索、计划、生成、审稿、抽取、确认、写回。

LangChain 的价值在这里主要是：

- 统一 document loader、text splitter、embedding、retriever、vector store。
- 把 RAG 检索、prompt、LLM、结构化输出解析串成可测试链路。
- 后续可引入 LangGraph 做更复杂的多步骤生成与审核工作流。
- 可以把不同记忆来源组合成 retriever，而不是手写大量一次性查询逻辑。

## 不建议整体替换现有 provider 层

当前项目的 AI 能力不是单一聊天模型：

- MiMo TTS 音色设计、音色复刻、预置音色。
- OpenAI TTS。
- DeepSeek / OpenAI-compatible 文本模型。
- 分镜规划、脚本润色、音色提示词润色。
- 视频生成、配音工作流、内容发现等业务链路。

LangChain 更适合 LLM 编排和 RAG，不适合接管所有 TTS 和媒体处理逻辑。现有 provider 层已经把能力拆成 `llm_text`、`tts_plain`、`tts_voice_design`、`scene_planning` 等 capability，应该继续作为项目内部模型边界。

建议边界：

```text
Flask routes
  -> business services
    -> memory/RAG services with LangChain
      -> existing ModelProvider for LLM calls, or LangChain chat model adapter
    -> existing TTS/video/discovery services
```

## 目标架构

```text
server/services/
  model_provider_base.py
  model_registry.py
  providers/
    mimo_provider.py
    openai_provider.py
    openai_compatible_provider.py

  memory/
    __init__.py
    document_types.py
    chunker.py
    embeddings.py
    vector_store.py
    retriever.py
    rag_chain.py
    memory_writer.py
    conflict_detector.py

  novel/
    context_builder.py
    chapter_generator.py
    graph_extractor.py
```

新增 memory 层职责：

| 模块 | 职责 |
| --- | --- |
| `document_types.py` | 定义长期记忆文档类型和元数据 |
| `chunker.py` | 将章节、设定、人物卡、事件摘要切片 |
| `embeddings.py` | 统一 embedding 模型调用 |
| `vector_store.py` | 封装 Chroma / FAISS / pgvector 等向量库 |
| `retriever.py` | 根据项目、章节、人物、事件、关键词检索相关记忆 |
| `rag_chain.py` | 使用 LangChain 编排检索、prompt、LLM、输出解析 |
| `memory_writer.py` | AI 生成或用户确认后写入长期记忆 |
| `conflict_detector.py` | 检查设定冲突、人设漂移、时间线矛盾 |

## 依赖建议

LangChain Python 当前采用核心包和集成包拆分。建议先引入最小组合：

```toml
dependencies = [
    "langchain",
    "langchain-openai",
    "langchain-community",
    "chromadb",
]
```

说明：

- `langchain`：核心 chain、prompt、retriever 等能力。
- `langchain-openai`：OpenAI chat model 和 embeddings 集成。
- `langchain-community`：社区 vector store、loader 等集成。
- `chromadb`：第一阶段本地向量库，适合开发验证。

安装前应以官方安装文档和当前 Python 版本为准。当前项目要求 Python 3.13，新增依赖后必须跑完整测试和启动验证。

可选后续依赖：

```toml
dependencies = [
    "faiss-cpu",
    "pgvector",
    "langgraph",
]
```

后续选择：

- 本地开发优先 Chroma。
- 单机轻量部署可考虑 FAISS。
- 多用户、生产化、需要 SQL 过滤和备份时考虑 PostgreSQL + pgvector。
- 多步骤 agent / 审稿 / 写回流程复杂后再引入 LangGraph。

## 数据模型设计

### 1. 长期记忆表

建议新增 `NovelMemory`，存结构化长期记忆元数据。向量库只存检索索引，数据库仍是事实主存储。

```python
class NovelMemory(db.Model):
    __tablename__ = 'novel_memories'

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(db.String(36), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    source_id = db.Column(db.String(36), nullable=True)
    memory_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=3)
    status = db.Column(db.String(20), nullable=False, default='active')
    vector_status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
```

字段建议：

| 字段 | 说明 |
| --- | --- |
| `source_type` | `project`, `chapter`, `outline`, `entity`, `event`, `manual_note`, `script` |
| `source_id` | 来源对象 ID |
| `memory_type` | `world_rule`, `character`, `relationship`, `event`, `foreshadowing`, `style`, `summary` |
| `importance` | 1-5，越高越优先进入上下文 |
| `status` | `active`, `archived`, `superseded` |
| `vector_status` | `pending`, `indexed`, `failed` |

### 2. 记忆变更日志

长期记忆要可追踪、可回滚，建议新增 `NovelMemoryChange`：

```python
class NovelMemoryChange(db.Model):
    __tablename__ = 'novel_memory_changes'

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(db.String(36), nullable=False, index=True)
    memory_id = db.Column(db.String(36), nullable=True, index=True)
    change_type = db.Column(db.String(30), nullable=False)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
```

用途：

- AI 自动抽取后先进入 `pending`。
- 用户确认后写入 `NovelMemory` 并更新向量索引。
- 用户发现错误时可以回滚。

### 3. 向量库元数据

向量库每个 chunk 建议包含：

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

必须支持按 `project_id` 过滤，避免不同小说工程的记忆串库。

## RAG 检索策略

### 检索输入

章节生成时，retriever 输入不应只有用户一句话，还应包含：

- 当前小说项目 ID。
- 当前章节 ID。
- 当前章节大纲。
- 前一章摘要。
- 当前出场人物。
- 当前事件目标。
- 用户临时指令。
- 需要回收或推进的伏笔。

### 多路检索

建议使用多路召回，再做排序压缩：

| 检索来源 | 目的 |
| --- | --- |
| 人物记忆 | 防止人设漂移 |
| 世界观规则 | 防止设定冲突 |
| 事件和时间线 | 保持因果连续 |
| 伏笔 | 提醒埋设和回收 |
| 文风样例 | 保持风格一致 |
| 前文摘要 | 保持章节衔接 |

示例：

```text
query = 当前章节大纲 + 用户指令 + 当前出场人物 + 事件目标

retrieved_context =
  character_memories +
  world_rules +
  recent_events +
  unresolved_foreshadowing +
  style_examples
```

### 上下文预算

建议把 RAG 上下文分成固定预算：

| 上下文块 | 建议占比 |
| --- | --- |
| 当前章节大纲 | 15% |
| 前文摘要 | 15% |
| 人物和关系 | 20% |
| 世界观规则 | 15% |
| 事件时间线 | 20% |
| 伏笔和用户指令 | 15% |

不要把向量检索结果无脑塞进 prompt。需要按重要性、相似度、最近更新时间、章节距离做排序和压缩。

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
  -> context_builder.py 构建基础上下文
  -> memory.retriever 检索长期记忆
  -> memory.rag_chain 组装 prompt 并生成
  -> 保存章节版本
  -> graph_extractor.py 抽取实体/事件变化
  -> memory_writer.py 生成记忆变更
  -> 用户确认或自动写回
```

第一阶段可只在 `chapter_generator.py` 接入 RAG，不改动所有小说服务。

## Prompt 结构

章节生成 prompt 建议固定为：

```text
你是长篇小说创作助手。你必须遵守长期记忆和当前大纲，不得随意改变已确认设定。

【项目设定】
...

【当前章节目标】
...

【长期记忆】
1. 人物设定
2. 世界观规则
3. 事件时间线
4. 未回收伏笔
5. 风格要求

【前文摘要】
...

【用户指令】
...

【输出要求】
- 只输出正文 Markdown。
- 不要解释。
- 不要改写已确认事实。
- 如果信息不足，用合理留白，不要创造冲突设定。
```

结构化抽取 prompt 建议输出 JSON，用于记忆写回：

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

### 记忆列表

```http
GET /api/novels/projects/{project_id}/memories
```

查询参数：

- `memory_type`
- `source_type`
- `status`
- `keyword`

### 新增手动记忆

```http
POST /api/novels/projects/{project_id}/memories
```

### 更新记忆

```http
PATCH /api/novels/projects/{project_id}/memories/{memory_id}
```

### 重建向量索引

```http
POST /api/novels/projects/{project_id}/memories/reindex
```

### 检索预览

```http
POST /api/novels/projects/{project_id}/memories/search
```

用途：

- 让用户和开发者看到某次生成会召回哪些记忆。
- 调试 RAG 质量。
- 避免“AI 为什么这么写”不可解释。

### 记忆变更确认

```http
GET /api/novels/projects/{project_id}/memory-changes
POST /api/novels/projects/{project_id}/memory-changes/{change_id}/confirm
POST /api/novels/projects/{project_id}/memory-changes/{change_id}/reject
```

## 前端改造

小说模块建议新增“长期记忆”入口：

- 记忆列表：按人物、事件、世界观、伏笔、风格筛选。
- 记忆详情：查看内容、来源、重要性、最近更新时间。
- 检索预览：输入章节目标，查看 RAG 召回结果。
- 待确认变更：AI 从章节中抽取的新事实，用户逐条确认。
- 索引状态：显示 pending / indexed / failed。

在章节生成页增加：

- “启用长期记忆”开关。
- “检索预览”按钮。
- “记忆强度”选项：保守、均衡、发散。
- 生成结果旁显示“引用的记忆片段”。

## 分阶段落地计划

### P0：最小可用 RAG

目标：章节生成可以检索项目长期记忆。

改造：

1. 增加 LangChain 和 Chroma 依赖。
2. 新增 `NovelMemory` 和 `NovelMemoryChange` 模型。
3. 新增 `server/services/memory/` 基础模块。
4. 支持手动新增记忆并写入向量库。
5. 在 `chapter_generator.py` 中检索相关记忆并拼入 prompt。
6. 增加 `/memories/search` 调试接口。

验收：

- 同一个项目下的记忆能被检索。
- 不同项目之间不会互相召回。
- 章节生成结果会遵守手动记忆。
- Redis、TTS、视频生成等现有功能不受影响。

### P1：章节确认后自动抽取记忆

目标：用户确认章节后，AI 自动提取新增事实和变更。

改造：

1. 在章节确认流程后调用结构化抽取。
2. 生成 `NovelMemoryChange` 待确认记录。
3. 前端增加“待确认记忆变更”面板。
4. 用户确认后写入 `NovelMemory` 并更新向量库。

验收：

- 章节中新出现的人物、地点、事件能被抽取。
- 用户可以确认或拒绝。
- 被确认的记忆能影响下一章生成。

### P2：冲突检测与记忆压缩

目标：减少长篇创作中的设定冲突和上下文膨胀。

改造：

1. 新增 `conflict_detector.py`。
2. 生成前检查当前章节目标与长期记忆是否冲突。
3. 对旧章节正文做摘要压缩。
4. 为高频记忆设置 `importance` 自动调整。

验收：

- 修改人物设定后，系统能发现生成目标中的明显冲突。
- 长篇章节数量增加后，RAG 上下文仍可控。
- 检索结果不会被大量低价值旧文本淹没。

### P3：多步骤工作流

目标：把章节生成升级成可观察、可重试的 AI 工作流。

可选方案：

- 继续用 LangChain Runnable 组合。
- 或引入 LangGraph 管理节点状态。

节点示例：

```text
retrieve_memory
  -> plan_chapter
  -> draft_chapter
  -> review_consistency
  -> revise_draft
  -> extract_memory_changes
  -> persist_version
```

## 关键风险

### 1. 依赖漂移

LangChain 生态更新较快，包拆分和导入路径可能变化。应避免在业务代码里散落大量 LangChain import，集中封装在 `server/services/memory/`。

### 2. 召回污染

如果向量库没有严格按 `project_id` 过滤，不同小说工程的设定可能串库。这是 P0 必须防住的问题。

### 3. 长期记忆写错

AI 抽取的事实可能错误。默认应采用“AI 提取后人工确认”，不要一开始就全自动写回。

### 4. 成本和延迟

RAG 会增加 embedding、检索、rerank、LLM 调用成本。第一阶段先不做 rerank，优先验证产品价值。

### 5. 过度依赖向量检索

人物当前状态、章节顺序、事件因果这类强结构信息不应该只靠向量检索。应继续保留 SQL 结构化查询，RAG 负责补充语义相关内容。

## 测试计划

### 单元测试

- `chunker` 切片稳定性。
- `vector_store` project 过滤。
- `retriever` 召回排序。
- `memory_writer` 写入和状态转换。

### 集成测试

- 新增记忆后能被 `/memories/search` 检索。
- A 项目的记忆不会被 B 项目召回。
- 章节生成启用 RAG 后 prompt 包含相关记忆。
- 章节确认后生成待确认记忆变更。

### 回归测试

- `uv run pytest server/tests/ -q`
- `uv run pytest tests/ -q`
- `cd web && pnpm run build`

如果修改前端页面，还需要用浏览器验证：

- 记忆列表加载。
- 检索预览结果显示。
- 待确认变更可以确认和拒绝。
- 章节生成页能展示引用记忆。

## 推荐实施顺序

1. 先做后端最小 RAG 骨架，不动 UI 大结构。
2. 加手动记忆 API 和检索预览 API。
3. 把 `chapter_generator.py` 接入检索结果。
4. 再补前端长期记忆管理页。
5. 最后做章节确认后的 AI 自动抽取和写回。

这个顺序能最快验证“长期记忆确实改善生成质量”，同时控制改造范围。

## 外部参考

- LangChain Python 安装文档：https://docs.langchain.com/oss/python/langchain/install
- LangChain Python 概览：https://docs.langchain.com/oss/python
- LangChain Python 集成包说明：https://docs.langchain.com/oss/python/integrations/providers
