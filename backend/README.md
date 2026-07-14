# Orenda Backend

FastAPI backend for Orenda.

## Endpoints
- `GET /health`
- `GET /api/history?q=...&mood=...` — SQLite-backed journal history (search + mood filter)
- `POST /api/reflect/stream` — SSE streaming reflection (plain-text labeled blocks); persists entry after stream completes

When the sibling `frontend/` directory is present, the app also serves the static UI at `/`.

## Environment
Create `backend/.env`:
- `ANTHROPIC_API_KEY` — Claude API key (omit or leave placeholder to use dev mock stream)
- `ANTHROPIC_MODEL` — optional, defaults to `claude-3-5-sonnet-latest`
- `ORENDA_DB_PATH` — SQLite file path (legacy alias: `ORIENTA_DB_PATH`)
- `CORS_ORIGINS` — comma-separated allowed origins (tighten for production)

## Run locally
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` for the integrated UI, or open `frontend/*.html` directly (API defaults to `http://localhost:8000`).

## Docker (project root)
```bash
docker compose up --build
```

SQLite is persisted in the `orenda_data` Docker volume at `/data/orenda.sqlite3`.

## Production checklist
- Set `CORS_ORIGINS` to your deployed frontend origin(s) only
- Provide a real `ANTHROPIC_API_KEY`
- Mount a persistent volume for `ORENDA_DB_PATH`
- Terminate TLS at a reverse proxy / load balancer in front of uvicorn
