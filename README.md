# To-Do App

A minimal to-do list app: a FastAPI + SQLite backend, and a single-file React
frontend (loaded via CDN script tags, no build step required).

- **Backend:** FastAPI, SQLAlchemy, SQLite. API-key-protected REST endpoints
  for creating, listing, editing, completing, and deleting tasks.
- **Frontend:** Plain `index.html` using React from a CDN and Babel's in-browser
  JSX transform — open it in a browser, no `npm install` needed.

## Project structure

```
todo-app/
├── backend/
│   ├── main.py            # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .env.example       # copy to .env and fill in
└── frontend/
    ├── index.html
    └── todo.css
```

## Running locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # then edit .env and set your own API_KEY

uvicorn main:app --reload
```

The API is now at `http://127.0.0.1:8000`. Every request except `/` (a health
check) must include header `X-API-Key: <your key>`.

### Frontend

The frontend is just static files. Open `frontend/index.html` directly in a
browser, or serve the folder with any static server, e.g.:

```bash
cd frontend
python -m http.server 5500
```

Before running, make sure `API_BASE` and `API_KEY` in `index.html` match your
backend's URL and `.env` value.

### Running the backend with Docker

```bash
cd backend
docker build -t todo-backend .
docker run -p 8000:8000 --env-file .env todo-backend
```

## Environment variables (backend)

| Variable | Description | Required |
|---|---|---|
| `API_KEY` | Shared secret clients must send as `X-API-Key` | yes |
| `DB_PATH` | SQLite file path | no (defaults to `todos.db`) |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins for CORS | no (defaults to `*`) |

## API

All endpoints require header `X-API-Key: <API_KEY>`.

| Method | Path | Description |
|---|---|---|
| GET | `/tasks` | List all tasks |
| POST | `/tasks` | Create a task — body `{"text": "..."}` |
| PATCH | `/tasks/{id}` | Toggle a task's done state |
| PUT | `/tasks/{id}` | Edit a task's text — body `{"text": "..."}` |
| DELETE | `/tasks/{id}` | Delete a task |

## Deployment

See `DEPLOYMENT.md` for step-by-step instructions for deploying the backend
(Render/Railway) and frontend (Vercel/Netlify).

## Security note

This is a demo-grade auth setup: a single static API key shipped in the
frontend's JS source, visible to anyone who views the page source or the
network tab. That's fine for a personal/learning project, but don't reuse
this pattern for anything with real user data — you'd want per-user auth
(e.g. OAuth or signed tokens) instead of one shared key baked into public
client code.
