# To-Do App

A minimal to-do list app: a FastAPI + SQLite backend, and a single-file React
frontend (loaded via CDN script tags, no build step required).

- **Backend:** FastAPI, SQLAlchemy, SQLite. API-key-protected REST endpoints
  for creating, listing, editing, completing, and deleting tasks. Deployed
  on [Render](https://render.com).
- **Frontend:** Plain `index.html` using React from a CDN and Babel's
  in-browser JSX transform — no `npm install` or build step. Deployed on
  [Vercel](https://vercel.com).

## Live demo

- Frontend: https://to-do-list-steel-five-36.vercel.app
- Backend: https://to-do-list-fzlx.onrender.com

Note: the backend is on Render's free tier, which spins down after periods
of inactivity. The first request after idling can take 30–50 seconds to
wake it back up — that's expected, not a bug.

## Project structure

```
todo-app/
├── README.md
├── DEPLOYMENT.md
├── .gitignore
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

Set locally in `backend/.env` (never committed), and as dashboard environment
variables on Render:

| Variable | Description | Required |
|---|---|---|
| `API_KEY` | Shared secret clients must send as `X-API-Key` | yes |
| `DB_PATH` | SQLite file path | no (defaults to `todos.db`) |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins for CORS (e.g. the Vercel URL, no trailing slash) | no (defaults to `*`) |

## API

All endpoints require header `X-API-Key: <API_KEY>`.

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check — returns `{"status": "ok"}` |
| GET | `/tasks` | List all tasks |
| POST | `/tasks` | Create a task — body `{"text": "..."}` |
| PATCH | `/tasks/{id}` | Toggle a task's done state |
| PUT | `/tasks/{id}` | Edit a task's text — body `{"text": "..."}` |
| DELETE | `/tasks/{id}` | Delete a task |

## Deployment

This app is deployed with:

- **Backend → Render:** Web Service, Docker environment, root directory
  `backend`, environment variables `API_KEY`, `DB_PATH`, and
  `ALLOWED_ORIGINS` set in the Render dashboard.
- **Frontend → Vercel:** static project, root directory `frontend`,
  framework preset "Other" (no build step).

See `DEPLOYMENT.md` for the full step-by-step walkthrough, including how to
redeploy or point this at a different Render/Vercel project.
