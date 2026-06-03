# Script

中文 SRT 字幕生成与短视频生产工具。除了核心的中文文本智能分句与 SRT 字幕生成外，还提供 TTS 语音合成、视频模板渲染、语音工作流编排、内容发现、多模型供应商管理、小说续写与长期记忆等能力，并附带一个 Vue 3 + Flask 的 Web 工作台。

## 功能特性

- **智能 SRT 字幕生成**：根据中文标点（。？！… → ，、；：）进行两级分段，可配置语速、段长上限；支持中英双语字幕
- **多供应商 TTS 合成**：内置 MiMo（语音设计 / 克隆 / 内置音色）与 OpenAI TTS 适配器，可插拔扩展
- **多模型 LLM 能力**：内置 mimo / deepseek / openai / minimax 预设，支持场景规划、文案润色、语音提示词生成等
- **视频生成流水线**：场景规划 → TTS 合成 → BGM / 环境音混音 → 视频渲染 → 剪映 / CapCut 草稿导出
- **语音工作流**：基于 `@vue-flow/core` 的节点画布，按片段配置情感、强度、语速、音量、停顿等参数
- **内容发现**：可插拔连接器（YouTube / 手动 URL），结合 LLM 自动分析与脚本改写
- **小说续写工作台**：大纲管理、Markdown 编辑器、AI 多版本生成、人物关系图 / 事件因果图、一致性审稿
- **RAG 长期记忆**：基于 LangChain + ChromaDB 的向量检索，自动抽取章节事实、冲突检测、多步骤 LangGraph 工作流
- **内容管理**：文字、文件夹、标签、语音档案、视频模板的统一管理（SQLite + 可选 MySQL）
- **Web 工作台**：Vue 3 + Vite + Pinia + Ant Design Vue，前后端分离开发

## 项目结构

```
.
├── main.py                # CLI 入口：从文件/标准输入读取中文文本，生成 SRT
├── splitter.py            # 中文文本智能分句（标点两级分段）
├── srt.py                 # SRT 格式生成器（含双语支持）
│
├── server/                # Flask 后端
│   ├── app.py             # 应用工厂：注册蓝图、初始化数据库、播种视频模板
│   ├── models/            # SQLAlchemy 模型
│   │   ├── text.py / folder.py / video.py / provider.py / discovery.py / voice_workflow.py
│   │   └── novel/         # 小说模块模型（project / outline / chapter / entity / event / graph_change / memory）
│   ├── routes/            # REST 蓝图
│   │   ├── texts / folders / tags / tts / video / voice_profiles / models / discovery / voice_workflows
│   │   └── novels/        # 小说路由（projects / outline / chapters / entities / events / graph / memories）
│   └── services/          # 业务逻辑
│       ├── model_provider_base.py / model_registry.py / providers/   # 可插拔模型供应商
│       ├── tts_adapters/                                              # TTS 适配器层
│       ├── video_job.py / video_scene_planner.py / video_renderer.py # 视频生成流水线
│       ├── audio_mixer.py / audio_postprocess.py / audio_package.py  # 音频处理
│       ├── voice_workflow_service.py / emotion_planner.py            # 语音工作流
│       ├── discovery/                                                 # 内容发现连接器
│       ├── novel/           # 小说生成服务（context_builder / chapter_generator / prompt_templates / generation_runner）
│       ├── memory/          # RAG 长期记忆（retriever / rag_chain / vector_store / memory_writer / conflict_detector / workflow）
│       ├── jianying_draft.py / capcut_package.py                      # 剪映/CapCut 导出
│       └── ...
│
├── web/                   # Vue 3 前端
│   └── src/
│       ├── views/         # TextList / TextEdit / Import / QuickGenerate / Discovery / VoiceWorkflowList / VoiceWorkflowView / NovelProjectList / NovelWorkspace
│       ├── components/    # video/ settings/ voice-workflow/ discovery/ novel/ (MemoryPanel / CharacterGraph / EventGraph / ...)
│       ├── stores/        # Pinia: texts / folders / tags / settings / modelSettings / discovery / voiceWorkflows / novels
│       ├── utils/         # memoryTypes 等共享工具
│       └── api/           # Axios API 封装（含 novelsApi 60+ 端点）
│
├── tests/                 # 核心模块测试（splitter、srt）
├── server/tests/          # 后端测试
├── docs/                  # 迁移与最佳实践文档
├── data.db                # SQLite 数据库
├── start.sh               # 启停脚本（Flask :5002 + Vue :3000）
└── pyproject.toml
```

## 环境要求

- Python 3.13（见 `.python-version`）
- [uv](https://docs.astral.sh/uv/)（推荐）
- Node.js + pnpm（前端）
- 可选：MySQL（用于语音档案功能，通过 `.env` 配置）

## 安装

```bash
uv sync
cd web && pnpm install
```

按需复制 `.env` 用于 MySQL 语音档案功能；核心 SRT / CLI 流程无需任何环境变量。

## 快速开始

### CLI：生成 SRT 字幕

```bash
uv run main.py input.txt -o output.srt
echo "你好吗？我很好。" | uv run main.py -o output.srt
```

可选项：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--speed` | 语速（字/秒） | 5 |
| `--max-chars` | 每段最大字数 | 20 |
| `-o` | 输出文件路径 | `output.srt` |

### Web 工作台

```bash
./start.sh start       # Flask :5002 + Vue :3000
./start.sh status
./start.sh stop
```

日志：`/tmp/flask.log`、`/tmp/vue.log`

仅启动 Flask：

```bash
uv run python -m server.app
# 或：uv run subtitle-web
```

前端开发模式：

```bash
cd web && pnpm run dev     # :3000，/api/* 反代到 :5002
cd web && pnpm run build   # 生产构建，输出到 server/static/
```

## 核心库使用示例

```python
from splitter import split_text
from srt import generate_srt, generate_bilingual_srt

segments = split_text("你好吗？我很好。今天天气不错，我们去公园散步吧。")
srt = generate_srt(segments, chars_per_second=5)
# 双语字幕
srt_bi = generate_bilingual_srt(segments, ["How are you?", "I'm fine.", ...])
```

## 架构要点

### 文本到视频流水线

```
文字输入 → 分句（splitter）→ 场景规划（LLM, video_scene_planner）
       → 语音合成（TTS, tts_provider / tts_adapters）
       → 音频混音（audio_mixer: BGM + 环境音 + 人声）
       → 视频渲染（moviepy, video_renderer）
       → 导出（剪映 jianying_draft / CapCut capcut_package）
```

视频任务以后台守护线程运行，前端通过 REST 轮询任务状态。

### 可插拔模型供应商

`server/services/model_provider_base.py` 定义 `ModelProvider` 抽象基类与能力枚举（`llm_text` / `tts_builtin_voice` / `tts_voice_design` / `tts_voice_clone` / `scene_planning` / `script_polish` 等）。`model_registry.py` 工厂预置 4 个供应商：

- `mimo`：MiMo TTS（语音设计 / 克隆 / 内置）+ LLM
- `openai`：OpenAI LLM + TTS + 场景规划
- `openai_compatible`：通用 OpenAI 兼容协议（DeepSeek、MiniMax 等）
- `deepseek` / `minimax`：便捷预设

新增供应商只需实现对应 capability。

### 内容发现

`server/services/discovery/` 提供可插拔连接器：

- `youtube.py`：YouTube 视频与字幕抽取
- `manual_url.py`：手动 URL 提交
- `analyzer.py`：LLM 内容分析
- `scoring.py`：相关性打分
- `script_adapter.py`：转换为视频脚本

### 语音工作流

- 数据模型支持按片段配置情感、强度、语速、音量、停顿、过渡
- 节点画布前端（`@vue-flow/core`）
- 音频指纹与清单生成
- 导出到 剪映 / CapCut 草稿

### 小说续写与 RAG 长期记忆

`server/services/novel/` 提供小说续写核心服务：

- `context_builder.py`：预算控制的上下文组装（大纲 / 前文摘要 / 人物 / 事件 / 世界观 / 伏笔）
- `chapter_generator.py`：单章节版本生成，集成 RAG 记忆检索
- `prompt_templates.py`：9 种小说体裁模板 + 6 种版本方向修饰符
- `blueprint_generator.py`：从一句话前提生成全书蓝图（大纲树 + 人物 + 世界观）
- `graph_extractor.py`：从已确认章节自动抽取人物关系和事件因果
- `consistency_reviewer.py`：9 维一致性审稿（人物 / 世界观 / 时间线 / 因果 / 伏笔 / ...）
- `generation_runner.py`：后台线程异步执行 + SSE 实时进度推送

`server/services/memory/` 提供 RAG 长期记忆：

- `retriever.py`：多路向量检索，余弦距离归一化 + 重要性 + 类型权重排序
- `rag_chain.py`：检索 → prompt 组装 → LLM 生成 → 冲突警告注入
- `vector_store.py`：ChromaDB 封装，按项目隔离 collection，线程安全缓存
- `memory_writer.py`：记忆 CRUD + 向量索引 + 章节确认后自动抽取（结构化 JSON）
- `conflict_detector.py`：生成前检测章节目标与已有设定的冲突
- `workflow.py`：LangGraph 7 节点工作流（检索 → 冲突检测 → 起草 → 审稿 → 修改 → 抽取 → 持久化）
- `chunker.py`：按中文标点边界切片，支持重叠窗口

前端工作台（`NovelWorkspace.vue`）支持 4 种模式：

- **写作**：三栏布局（大纲树 / Markdown 编辑器 / 生成面板 + 版本管理 + 上下文预览）
- **图谱**：`@vue-flow/core` 画布，人物关系图 / 事件因果图，节点可拖拽布局
- **审稿**：一致性评分 + 问题列表 + 修改建议
- **记忆**：长期记忆管理 / RAG 检索预览 / 待确认 AI 抽取变更

### 双数据库

- **SQLite**（`data.db`）：文字、文件夹、标签、视频模板、视频任务、视频资产、发现数据、自定义供应商
- **MySQL**（远程，可选）：语音档案与试听记录

## 测试

```bash
uv run pytest                                      # 全部测试
uv run pytest tests/test_splitter.py -v            # 单个文件
uv run pytest server/tests/ -v                     # 仅后端测试
```

测试目录：

- `tests/`：核心库（splitter、srt）
- `server/tests/`：后端路由与服务

## 主要依赖

**Python**：Flask、Flask-SQLAlchemy、Flask-CORS、requests、deep-translator、moviepy、PyMySQL、python-dotenv、LangChain、ChromaDB、LangGraph

**前端**：Vue 3、Vite、Pinia、Vue Router、Ant Design Vue、Axios、`@vue-flow/core`

## 外部服务

- **MiMo**：`api.xiaomimimo.com`（TTS 语音设计 / 克隆 / 内置）
- **MiMo Token Plan**：`token-plan-cn.xiaomimimo.com/anthropic`（LLM）
- **Google Translate**（`deep-translator`）：双语字幕翻译
- 视频模板 / BGM / 字体等素材由后端种子数据初始化

## 常用脚本

```bash
./start.sh start|stop|restart|status
uv run python scripts/migrate_sqlite_to_mysql.py   # 数据迁移
```

## 文档

- `CLAUDE.md`：项目级 AI 协作指南（命令、架构、模式）
- `docs/tts-migration-guide.md`：TTS 智能分块同步包 API 迁移
- `docs/voice-workflow-*.md`：语音工作流优化与最佳实践
- `FRONTEND_IMPROVEMENT_PLAN.md`：前端改进计划
- `UI_THEME_GUIDE.md`：UI 主题指南
