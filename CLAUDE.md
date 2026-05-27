# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRT subtitle generator and video production tool for Chinese text. Converts Chinese text into timed SRT subtitle files with intelligent punctuation-based segmentation. Also supports TTS voice synthesis, video generation with templates/BGM/effects, voice profile management, and a pluggable multi-provider model system.

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
./start.sh status
```

### Development
```bash
uv run pytest                              # All tests
uv run pytest tests/test_splitter.py -v    # Single test file
uv run pytest server/tests/ -v             # Backend tests only

cd web && pnpm run dev     # Vue dev server only
cd web && pnpm run build   # Production build → server/static/
```

## Architecture

### Core Library (root)
- `splitter.py` — Chinese text segmentation by punctuation (。？！…then，、；：)
- `srt.py` — SRT format generator with configurable gap between segments (default 1s). Also `generate_bilingual_srt()` for Chinese+English.
- `main.py` — CLI wrapper

### Flask Backend (`server/`)
- `app.py` — Factory pattern, SQLite (`data.db`), registers 7 blueprints, seeds video templates on startup
- `models.py` — 6 SQLAlchemy models: Text, Folder, Tag, VideoTemplate, VideoJob, VideoAsset
- `routes/` — 7 blueprints: texts, folders, tags, tts, video, voice_profiles, models

**Key backend patterns:**
- TTS uses MiMo API (`api.xiaomimimo.com`). LLM uses MiMo Token Plan (`token-plan-cn.xiaomimimo.com/anthropic`).
- Video jobs run in background daemon threads (`video_job.py`), polled via REST (not WebSocket).
- Video templates are JSON configs stored in DB, seeded as built-in on startup (`video_template.py`).
- `deep-translator` (Google Translate) used for bilingual subtitle translation in `routes/texts.py`.

### Pluggable Model Provider System (`server/services/`)
- `model_provider_base.py` — Abstract `ModelProvider` base class with capability enum
- `model_registry.py` — Factory with 4 built-in presets: mimo, deepseek, openai, minimax
- `providers/mimo_provider.py` — MiMo TTS (voice design/clone/builtin) + LLM
- `providers/openai_provider.py` — OpenAI LLM + TTS + scene planning
- `providers/openai_compatible_provider.py` — Generic for DeepSeek, MiniMax, etc.
- Capabilities: `llm_text`, `llm_voice_prompt_polish`, `tts_builtin_voice`, `tts_voice_design`, `tts_voice_clone`, `tts_plain`, `scene_planning`, `script_polish`

### Video Generation Pipeline
`video.py` route → `video_job.py` (async thread) → `video_scene_planner.py` (LLM scene planning) → `tts_provider.py` (voice synthesis) → `audio_mixer.py` (BGM + ambient + voice mixing) → `video_renderer.py` (moviepy rendering) → `capcut_package.py` (剪映-friendly export)

Video templates define: aspect ratio, resolution, fps, visual effects (zoom/pan/shake/flash), audio mixing ratios, transitions, export settings.

### Vue Frontend (`web/`)
- Vue 3 + Vite 8 + Pinia 3 + Ant Design Vue 4 + Axios
- Dev server proxies `/api/*` to Flask on port 5002. Build output → `server/static/`.
- **Views:** TextList, TextEdit, Import, QuickGenerate
- **Component subdirectories:** `video/` (7-step wizard), `settings/` (model provider config)
- **Stores:** texts, folders, tags, settings, modelSettings
- **API layer:** `web/src/api/index.js` — 7 modules (textsApi, foldersApi, tagsApi, ttsApi, voiceProfilesApi, videoApi, modelProvidersApi)

### Dual Database
- **SQLite** (`data.db`): Texts, folders, tags, video templates, video jobs, video assets
- **MySQL** (remote, optional): Voice profiles, audition records. Configured via `.env`.

### SRT Segment Gap
`generate_srt()` and `generate_bilingual_srt()` in `srt.py` accept a `gap` parameter (default 1.0 second) that adds silence between subtitle segments for readability.

## Testing

- `tests/` — Core module tests (splitter, srt)
- `server/tests/` — 25 test files covering routes and services
- Pytest configured in `pyproject.toml`: `pythonpath = [".", "server"]`, `testpaths = ["tests", "server/tests"]`

## Key Dependencies

**Python:** Flask, Flask-SQLAlchemy, Flask-CORS, requests, deep-translator, moviepy, pymysql, python-dotenv
**Frontend:** Vue 3, Vite, Pinia, Vue Router, Ant Design Vue, axios
