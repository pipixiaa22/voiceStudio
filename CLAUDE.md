# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRT subtitle generator for video editors (primarily CapCut/剪映). Converts Chinese text into timed SRT subtitle files with intelligent punctuation-based segmentation.

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
```

### Development
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_splitter.py -v

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
- `routes/` — REST API blueprints: texts, folders, tags, tts

### Vue Frontend (`web/`)
- Vue 3 + Vite + Pinia + Ant Design Vue
- `src/stores/` — Pinia state management for texts, folders, tags
- `src/api/` — Axios wrapper calling Flask API
- Vite dev server proxies `/api/*` to Flask on port 5002

### Core Modules (Root)
- `splitter.py` — Chinese text segmentation by punctuation (。？！…then，、；：)
- `srt.py` — SRT format generator with timestamp calculation

## Key Design Decisions

1. **Punctuation splitting**: Sentences split by 。？！… first, then by ，、；：if too long, then force-split
2. **Trailing punctuation**: 。and，are stripped from segment endings; ？and！are preserved
3. **SRT filenames**: Use RFC 5987 encoding (`filename*=UTF-8''...`) for Chinese filenames
4. **Port config**: Flask uses port 5002 (5000/5001 often occupied on macOS), Vue on 3000

## Database

SQLite stored at `data.db` in project root. Tables: `texts`, `folders`, `tags`, `text_tags` (association).

## Testing

Tests in `tests/` (core modules) and `server/tests/` (API endpoints). Pytest configured in `pyproject.toml` with `pythonpath = [".", "server"]`.
