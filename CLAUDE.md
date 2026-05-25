# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRT subtitle generator for video editors (primarily CapCut/剪映). Converts Chinese text into timed SRT subtitle files with intelligent punctuation-based segmentation. Also supports TTS voice synthesis, static image video generation, and voice profile management.

## Commands

### CLI Usage
```bash
# Generate SRT from file
uv run main.py input.txt -o output.srt

# Generate SRT from stdin
echo "你好吗？我很好。" | uv run main.py -o output.srt

# Options: --speed (chars/sec, default 5), --max-chars (default 20)
```

### Web Server
```bash
# Start both Flask backend and Vue frontend
./start.sh start

# Stop servers
./start.sh stop

# Check status
./start.sh status

# Restart servers
./start.sh restart
```

### Development
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_splitter.py -v

# Run backend tests only
uv run pytest server/tests/ -v

# Build frontend for production
cd web && pnpm run build
```

## Architecture

### Two Interfaces, Shared Core
- **CLI** (`main.py`): Direct command-line tool using `splitter.py` and `srt.py`
- **Web** (`server/` + `web/`): Flask API + Vue 3 SPA, same core modules

### Python Backend (`server/`)
- `app.py` — Flask app factory with SQLite, runs on port 5002
- `models.py` — SQLAlchemy models: Text, Folder (self-referential hierarchy), Tag (many-to-many)
- `routes/` — REST API blueprints:
  - `texts.py` — Text CRUD, import/export, SRT generation
  - `folders.py` — Folder CRUD
  - `tags.py` — Tag CRUD
  - `tts.py` — TTS voice synthesis (MiMo API), includes sync-package-v2 with smart chunking
  - `video.py` — Static image video generation (moviepy)
  - `voice_profiles.py` — Voice profile CRUD, audition API
- `services/` — Business logic layer:
  - `tts_provider.py` — MiMo TTS API wrapper
  - `tts_planner.py` — Merges subtitle segments into speech chunks (80-300 chars)
  - `audio_package.py` — WAV reading, concatenation, SRT generation, ZIP packaging
  - `subtitle_timeline.py` — Generates subtitle timestamps from chunk durations
  - `mysql.py` — MySQL connection for voice profiles
  - `voice_profile_repository.py` — Voice profile database operations

### Vue Frontend (`web/`)
- Vue 3 + Vite + Pinia + Ant Design Vue
- `src/stores/` — Pinia state management for texts, folders, tags
- `src/api/` — Axios wrapper calling Flask API
- `src/views/` — Page components: TextList, TextEdit, Import, QuickGenerate
- `src/components/` — Reusable components including VoiceSynthModal, VoiceProfileSelector, VoiceProfileDrawer
- Vite dev server proxies `/api/*` to Flask on port 5002

### Core Modules (Root)
- `splitter.py` — Chinese text segmentation by punctuation (。？！…then，、；：)
- `srt.py` — SRT format generator with timestamp calculation

## Key Design Decisions

1. **Punctuation splitting**: Sentences split by 。？！… first, then by ，、；：if too long, then force-split
2. **Trailing punctuation**: 。and，are stripped from segment endings; ？and！are preserved
3. **SRT filenames**: Use RFC 5987 encoding (`filename*=UTF-8''...`) for Chinese filenames
4. **Port config**: Flask uses port 5002 (5000/5001 often occupied on macOS), Vue on 3000
5. **Video generation**: Uses moviepy (pure Python) instead of ffmpeg for video synthesis
6. **TTS smart chunking**: Subtitle segments merged into 80-300 char speech chunks to reduce voice fragmentation
7. **Voice profiles**: Stored in MySQL (separate from SQLite), support system presets and user-created profiles

## Databases

- **SQLite** (`data.db`): Texts, folders, tags, text_tags
- **MySQL** (remote): Voice profiles, audition records

MySQL connection configured via `.env` file (see `.env.example`).

## Dependencies

### Python
- Flask, Flask-SQLAlchemy, Flask-CORS
- requests (for TTS API calls)
- moviepy (for video generation)
- pymysql (for MySQL voice profiles)
- python-dotenv (for .env loading)

### Frontend
- Vue 3, Vite, Pinia, Vue Router
- Ant Design Vue
- axios

## Testing

Tests in `tests/` (core modules) and `server/tests/` (API endpoints). Pytest configured in `pyproject.toml` with `pythonpath = [".", "server"]`.
