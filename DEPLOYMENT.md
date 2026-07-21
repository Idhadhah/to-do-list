# Deployment guide

These steps require an account and a browser, so you'll need to do them
yourself — nothing here can be done from inside a chat session.

## Part A — Push the code to GitHub

1. Create a new empty repo on GitHub (no README/license, so there's no merge
   conflict with your local files).
2. From the `todo-app/` folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: FastAPI backend + React frontend"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
3. **Before you push**, double check `.env` is NOT staged:
   ```bash
   git status
   ```
   You should see `backend/.env.example` listed but not `backend/.env`. If
   `.env` shows up, the `.gitignore` isn't being picked up — run
   `git rm --cached backend/.env` first.

## Part B — Deploy the backend (Render, free tier)

1. Go to render.com and sign up / log in (GitHub login is easiest).
2. Dashboard → **New** → **Web Service**.
3. Connect your GitHub account and select the repo you just pushed.
4. Configure:
   - **Root Directory:** `backend`
   - **Environment:** Docker (Render will detect the `Dockerfile` automatically)
   - **Instance Type:** Free
5. Under **Environment Variables**, add:
   - `API_KEY` = a long random string you choose (don't reuse
     `mysecretkey123` — generate one, e.g. `openssl rand -hex 32`)
   - `DB_PATH` = `todos.db`
   - `ALLOWED_ORIGINS` = leave blank for now; you'll fill this in after Part C
     with your Vercel/Netlify URL
6. Click **Create Web Service**. Render will build the Docker image and
   deploy it — this takes a few minutes on first deploy.
7. Once live, note the URL Render gives you, something like
   `https://todo-backend-xxxx.onrender.com`.
8. Sanity check in your own browser: visit `https://YOUR-URL.onrender.com/` —
   you should see `{"status":"ok"}`.

   Note: on Render's free tier, the service spins down after inactivity and
   the first request after that can take ~30-50 seconds to wake back up.
   That's expected, not a bug.

**Railway alternative:** same idea — New Project → Deploy from GitHub repo →
set Root Directory to `backend` → Railway also auto-detects the Dockerfile →
add the same environment variables in the Variables tab → deploy → copy the
generated public URL.

## Part C — Point the frontend at the live backend, then deploy it

1. In `frontend/index.html`, replace the placeholder:
   ```js
   const API_BASE = "https://YOUR-BACKEND-URL.onrender.com";
   const API_KEY = "the-same-random-string-you-set-as-API_KEY-on-render";
   ```
2. Commit and push that change.
3. Deploy on Vercel:
   - vercel.com → sign up/log in → **Add New** → **Project** → import your
     GitHub repo.
   - **Root Directory:** `frontend`
   - Framework preset: **Other** (it's static HTML, no build step).
   - Deploy.
4. Vercel gives you a URL like `https://your-app.vercel.app`.

**Netlify alternative:** New site from Git → pick the repo → set **Base
directory** to `frontend`, leave build command empty, publish directory
`frontend` (or `.` relative to base) → deploy.

5. Go back to Render (or Railway) and set `ALLOWED_ORIGINS` to your new
   frontend URL, e.g. `https://your-app.vercel.app`, then redeploy/restart the
   backend so CORS allows it. This is what lets th e browser actually call
   the API instead of getting blocked by CORS.

## Part D — End-to-end test on the live URLs

Open your Vercel/Netlify URL (not localhost) in a browser and, using only
that page:

1. **Add** a task, confirm it appears in the list.
2. **Check it done** (click the checkbox), confirm the strikethrough style
   applies.
3. **Edit** it, save, confirm the new text persists after a page refresh.
4. **Delete** it, confirm it disappears and stays gone after a refresh.
5. Open browser DevTools → Network tab while doing the above, and confirm
   every request is going to your `onrender.com`/`railway.app` URL, not
   `127.0.0.1`.

If step 1 fails with a CORS error in the console, it's almost always
`ALLOWED_ORIGINS` on the backend not matching your frontend's exact URL
(including `https://`, no trailing slash). If it fails with a 401, the
`API_KEY` values on frontend and backend don't match.

## Part E — Final repo cleanup

- Confirm `README.md` and this `DEPLOYMENT.md` are committed.
- Confirm `backend/.env` was never committed (`git log --all --full-history -- backend/.env` should return nothing).
- Squash or leave your commit history as-is, but make sure commit messages
  describe what changed (e.g. "Add Docker support", "Load secrets from
  .env", "Point frontend at deployed backend") rather than "wip" / "fix".
- Add a short repo description and topics (e.g. `fastapi`, `react`,
  `todo-app`) on the GitHub repo page for discoverability.
