# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**墨 · 影 字幕工坊** — a Chinese subtitle generation tool that takes Chinese text, splits it by punctuation into segments, and produces SRT subtitle files. Two interfaces: a CLI (`main.py`) and a web application (Flask backend + Vue 3 frontend).

## Commands

### Run all tests
```bash
uv run pytest
```

### Run a single test file
```bash
uv run pytest tests/test_splitter.py
uv run pytest server/tests/test_texts.py
```

### Start/stop both servers (Flask + Vue dev server)
```bash
./start.sh start    # Flask on :5002, Vue dev on :3000
./start.sh stop
./start.sh status
```

### Run Flask backend only
```bash
uv run python -m server.app
```

### Run Vue frontend only
```bash
cd web && pnpm run dev
```

### Build Vue frontend (outputs to server/static/)
```bash
cd web && pnpm run build
```

### CLI usage
```bash
uv run python main.py input.txt --speed 5 --max-chars 20 -o output.srt
```

## Architecture

### Core library (root directory)
- **splitter.py** — Chinese text segmentation by punctuation (sentence-ending `。？！…` first, then comma-level `，、；：` for long segments). Handles forced splitting when no punctuation exists.
- **srt.py** — Converts segment list to SRT format with calculated timestamps based on characters-per-second speed.
- **main.py** — CLI wrapper combining splitter + srt.

### Flask backend (`server/`)
- **app.py** — Factory pattern (`create_app`). SQLite DB at `data.db` in project root. Registers three blueprints. Port 5002.
- **models.py** — Three models: `Text` (content with title, folder, tags), `Folder` (hierarchical via self-referencing `parent_id`), `Tag` (many-to-many with Text via `text_tags` join table).
- **routes/texts.py** — CRUD + `.txt` import + SRT export endpoint (`/api/texts/<id>/srt`). Imports `splitter` and `srt` from root.
- **routes/folders.py** — CRUD for hierarchical folders.
- **routes/tags.py** — List and create tags.

### Vue frontend (`web/`)
- **Vite** with dev proxy: `/api` → `localhost:5002`. Build output goes to `server/static/` so Flask can serve the SPA.
- **Stack**: Vue 3, Pinia (stores: `texts.js`, `folders.js`, `tags.js`), Vue Router, Ant Design Vue 4, Axios.
- **Routes**: `/` (TextList), `/edit/:id?` (TextEdit), `/import` (Import).
- **Components**: `FolderTree.vue` (drag-and-drop folder hierarchy), `TagSelector.vue`.
- **API layer**: `src/api/index.js` — axios instance with `/api` base URL, exports `textsApi`, `foldersApi`, `tagsApi`.
- **Theme**: Cinematic ink & shadow aesthetic via CSS custom properties in `styles/theme.css`.

### Test structure
- `tests/` — Root-level tests for `splitter.py` and `srt.py` (pure Python, no Flask).
- `server/tests/` — Flask integration tests using in-memory SQLite via `conftest.py` fixtures (`app`, `client`, `db`).
- pytest config in `pyproject.toml`: `pythonpath = [".", "server"]`, `testpaths = ["tests", "server/tests"]`.

## Key Patterns

- The Flask server imports `splitter` and `srt` from the project root via `sys.path` manipulation in `routes/texts.py`.
- Vue dev server proxies `/api/*` to Flask, so frontend uses relative URLs (`/api/texts`).
- Production: build Vue (`pnpm build`) → outputs to `server/static/` → Flask serves the SPA at `/`.
- `data.db` is SQLite and committed to the repo (small, local-only project).
- UI text and API error messages are in Chinese.
