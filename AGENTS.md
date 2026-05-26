# AGENTS.md

SRT subtitle generator for Chinese video editors (CapCut/剪映). Two interfaces: CLI (`main.py`) and web app (Flask + Vue).

## Commands

```bash
# Run all tests (pytest covers both tests/ and server/tests/)
uv run pytest

# Run a single test file
uv run pytest tests/test_splitter.py -v

# CLI: generate SRT from text file
uv run main.py input.txt -o output.srt

# Start/stop web servers (Flask on :5002, Vue on :3000)
./start.sh start|stop|restart|status

# Build frontend (outputs to server/static/)
cd web && pnpm run build
```

## Architecture

- `splitter.py` / `srt.py` — core modules (punctuation-based segmentation, SRT generation)
- `main.py` — CLI entrypoint
- `server/` — Flask backend (app factory in `server/app.py`, port 5002)
- `web/` — Vue 3 + Vite + Pinia + Ant Design Vue frontend (port 3000)
- `data.db` — SQLite (texts, folders, tags)
- MySQL — voice profiles (configured via `.env`)

## Key facts

- Python 3.13 required (`.python-version`). Use `uv run` for all Python commands.
- Frontend build output goes to `server/static/` — Flask serves it as static files. Rebuild after frontend changes.
- Vue dev server proxies `/api/*` to Flask at `:5002`.
- No lint, typecheck, or CI config exists — run `uv run pytest` before finishing.
- `.env` is gitignored. Create it for MySQL voice profile features; not needed for core SRT/CLI.
- pytest `pythonpath = [".", "server"]` — imports resolve from both root and server/.
- Tests use fixtures in `server/tests/conftest.py` for Flask app context.
