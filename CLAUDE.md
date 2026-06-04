# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRT subtitle generator and video production tool for Chinese text. Converts Chinese text into timed SRT subtitle files with intelligent punctuation-based segmentation. Also supports TTS voice synthesis, video generation with templates/BGM/effects, voice profile management, content discovery, a pluggable multi-provider model system, a novel continuation/authoring workbench with RAG long-term memory (LangChain + ChromaDB + LangGraph), and a node-based voice workflow editor.

## Commands

### CLI Usage
```bash
uv run main.py input.txt -o output.srt
echo "你好吗？我很好。" | uv run main.py -o output.srt
# Options: --speed (chars/sec, default 5), --max-chars (default 20)
```

### Web Server
```bash
./start.sh start       # Flask backend (:5002) + Vue frontend (:3000)
./start.sh stop
./start.sh restart
./start.sh status
# Logs: /tmp/flask.log, /tmp/vue.log
```

### Flask Standalone
```bash
uv run python -m server.app    # Flask only, debug mode on :5002
# or: uv run subtitle-web      (same, via pyproject.toml script entry)
```

### Video Worker (Redis queue mode)
```bash
REDIS_TASK_QUEUE_ENABLED=true uv run python -m server.workers.video_worker
# Requires REDIS_URL in .env. Without it, video jobs run in daemon threads.
```

### Development
```bash
uv run pytest                                    # All tests
uv run pytest tests/test_splitter.py -v          # Single test file
uv run pytest tests/test_splitter.py::test_fn -v # Single test function
uv run pytest server/tests/ -v                   # Backend tests only

cd web && pnpm run dev     # Vue dev server on :3000, proxies /api/* → Flask :5002
cd web && pnpm run build   # Production build → server/static/
```

## Architecture

### Core Library (root)
- `splitter.py` — Chinese text segmentation by punctuation (。？！…then，、；：)
- `srt.py` — SRT format generator with configurable gap between segments (default 1s). Also `generate_bilingual_srt()` for Chinese+English.
- `main.py` — CLI wrapper

### Flask Backend (`server/`)
- `app.py` — Factory pattern, SQLite (`data.db`), registers blueprints, seeds video templates on startup
- `models/` — SQLAlchemy models split by domain: `text.py` (Text, Tag), `folder.py` (Folder), `video.py` (VideoTemplate, VideoJob, VideoAsset), `provider.py` (CustomProvider), `discovery.py` (DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis), `voice_workflow.py` (VoiceWorkflow, VoiceSegment), `novel/` (Project, Outline, Chapter, Entity, Event, GraphChange, Memory)
- `routes/` — Blueprints: texts, folders, tags, tts, video, voice_profiles, models, discovery, voice_workflows, `novels/` (projects, outline, chapters, entities, events, graph, memories)

**Key backend patterns:**
- TTS uses MiMo API (`api.xiaomimimo.com`). LLM uses MiMo Token Plan (`token-plan-cn.xiaomimimo.com/anthropic`).
- Video jobs run in background daemon threads (`video_job.py`), with SSE progress via `GET /api/video/jobs/<id>/stream`. Redis Pub/Sub used when available, in-memory queues as fallback.
- Video templates are JSON configs stored in DB, seeded as built-in on startup (`video_template.py`).
- `deep-translator` (Google Translate) used for bilingual subtitle translation in `routes/texts.py`.
- **Redis (optional):** Caching, SSE pub/sub, distributed TTS locks, rate limiting, task queue. All features degrade gracefully when `REDIS_URL` is not set. Config via `REDIS_URL`, `REDIS_KEY_PREFIX`, `REDIS_TASK_QUEUE_ENABLED`.

### Pluggable Model Provider System (`server/services/`)
- `model_provider_base.py` — Abstract `ModelProvider` base class with capability enum
- `model_registry.py` — Factory with 4 built-in presets: mimo, deepseek, openai, minimax
- `providers/mimo_provider.py` — MiMo TTS (voice design/clone/builtin) + LLM
- `providers/openai_provider.py` — OpenAI LLM + TTS + scene planning
- `providers/openai_compatible_provider.py` — Generic for DeepSeek, MiniMax, etc.
- Capabilities: `llm_text`, `llm_voice_prompt_polish`, `tts_builtin_voice`, `tts_voice_design`, `tts_voice_clone`, `tts_plain`, `scene_planning`, `script_polish`

### Content Discovery System (`server/services/discovery/`)
- Pluggable connector architecture: `base.py` defines abstract connector, `registry.py` manages connectors
- Built-in connectors: `youtube.py` (YouTube video/transcript extraction), `manual_url.py` (direct URL submission)
- `analyzer.py` — LLM-powered content analysis and script generation
- `scoring.py` — Relevance scoring for discovered items
- `script_adapter.py` — Adapts discovered content into video scripts

### Video Generation Pipeline
`video.py` route → `video_job.py` (async thread) → `video_scene_planner.py` (LLM scene planning) → `tts_provider.py` (voice synthesis) → `audio_mixer.py` (BGM + ambient + voice mixing) → `video_renderer.py` (moviepy rendering) → `capcut_package.py` (剪映-friendly export)

Video templates define: aspect ratio, resolution, fps, visual effects (zoom/pan/shake/flash), audio mixing ratios, transitions, export settings.

### Voice Workflow System
- **Model:** `models/voice_workflow.py` — segments with emotion/intensity/rate/pitch/volume/pause/transition settings
- **Service:** `services/voice_workflow_service.py` — CRUD, linear path resolution, audio fingerprinting, manifest generation
- **Route:** `routes/voice_workflows.py` — REST API for workflow CRUD, audition, export
- **Frontend:** `VoiceWorkflowList.vue`, `VoiceWorkflowView.vue` (node-based canvas using `@vue-flow/core`)
- **Store:** `stores/voiceWorkflows.js`
- Emotion planning: `emotion_planner.py` (LLM-based), `emotional_tts.py` (segment-level emotional voice control)
- Audio pipeline: `audio_postprocess.py`, `audio_package.py`, `subtitle_timeline.py`
- Export: `jianying_draft.py` (剪映 draft format), `capcut_package.py` (CapCut package)

### Novel Continuation Workbench (`server/services/novel/`)
Full novel authoring system with outline management, multi-version chapter generation, character/event graphs, and consistency review:
- `context_builder.py` — Budget-controlled context assembly (outline, prior summaries, characters, events, world-building, foreshadowing)
- `chapter_generator.py` — Single-chapter version generation with RAG memory retrieval
- `prompt_templates.py` — 9 genre templates + 6 version direction modifiers
- `blueprint_generator.py` — Generate full-book blueprint from a one-line premise (outline tree + characters + world)
- `graph_extractor.py` — Auto-extract character relationships and event causality from confirmed chapters
- `consistency_reviewer.py` — 9-dimension consistency review (character, world, timeline, causality, foreshadowing, etc.)
- `generation_runner.py` — Background thread async execution + SSE real-time progress
- Routes: `routes/novels/` — projects, outline, chapters, entities, events, graph, memories
- Frontend: `NovelProjectList.vue`, `NovelWorkspace.vue` (4 modes: writing, graphs, review, memory)
- Components: `novel/` — CharacterGraph, EventGraph, MemoryPanel, ConsistencyPanel, etc.
- Store: `stores/novels.js`

### RAG Long-Term Memory (`server/services/memory/`)
LangChain + ChromaDB vector store with LangGraph workflow for persistent novel memory:
- `vector_store.py` — ChromaDB wrapper, per-project collection isolation, thread-safe caching
- `retriever.py` — Multi-path vector retrieval with cosine distance normalization + importance + type weighting
- `rag_chain.py` — Retrieval → prompt assembly → LLM generation → conflict warning injection
- `memory_writer.py` — Memory CRUD + vector indexing + auto-extraction from confirmed chapters (structured JSON)
- `conflict_detector.py` — Detect conflicts between chapter goals and existing settings before generation
- `workflow.py` — LangGraph 7-node pipeline: retrieve → conflict detect → draft → review → revise → extract → persist
- `chunker.py` — Chinese punctuation boundary splitting with overlap windows
- `embeddings.py` — Embedding model abstraction
- `document_types.py` — Memory document type definitions

### TTS Adapters (`server/services/tts_adapters/`)
Abstraction layer separating TTS provider logic from route code:
- `base.py` — abstract adapter interface
- `mimo.py` — MiMo TTS adapter (voice design/clone/builtin)
- `openai.py` — OpenAI TTS adapter
- `voice_prompt.py` — LLM-powered voice prompt generation and polish

### Vue Frontend (`web/`)
- Vue 3 + Vite 8 + Pinia 3 + Ant Design Vue 4 + Axios
- `@vue-flow/core` for node-based visual editors (voice workflow canvas)
- Dev server proxies `/api/*` to Flask on port 5002. Build output → `server/static/`.
- **Views:** TextList, TextEdit, Import, QuickGenerate, Discovery, VoiceWorkflowList, VoiceWorkflowView, NovelProjectList, NovelWorkspace
- **Component subdirectories:** `video/` (7-step wizard), `settings/` (model provider config), `voice-workflow/`, `discovery/`, `novel/` (CharacterGraph, EventGraph, MemoryPanel, ConsistencyPanel, etc.)
- **Stores:** texts, folders, tags, settings, modelSettings, discovery, voiceWorkflows, novels
- **API layer:** `web/src/api/index.js` — modules: textsApi, foldersApi, tagsApi, ttsApi, voiceProfilesApi, videoApi, modelProvidersApi, customProvidersApi, discoveryApi, voiceWorkflowsApi, novelsApi (60+ endpoints)

### Dual Database
- **SQLite** (`data.db`): Texts, folders, tags, video templates, video jobs, video assets, discovery data, custom providers
- **MySQL** (remote, optional): Voice profiles, audition records. Configured via `.env`.

## Testing

- `tests/` — Core module tests (splitter, srt)
- `server/tests/` — Test files covering routes and services
- Pytest configured in `pyproject.toml`: `pythonpath = [".", "server"]`, `testpaths = ["tests", "server/tests"]`
- Tests use fixtures in `server/tests/conftest.py` for Flask app context

## Key Dependencies

**Python:** Flask, Flask-SQLAlchemy, Flask-CORS, requests, deep-translator, moviepy, pymysql, python-dotenv, redis, langchain, langchain-openai, langchain-community, chromadb, langgraph
**Frontend:** Vue 3, Vite, Pinia, Vue Router, Ant Design Vue, axios

## Environment

- Python 3.13 required (`.python-version`). Use `uv run` for all Python commands.
- `.env` is gitignored. Create it for MySQL voice profile features; not needed for core SRT/CLI.
- Optional Redis: set `REDIS_URL` in `.env` for caching, SSE, distributed locks, rate limiting, and task queue.
- No lint, typecheck, or CI config exists — run `uv run pytest` before finishing.
