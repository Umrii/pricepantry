# Running Price Pantry locally (from the VS Code terminal, no Docker Compose)

This runs each service natively so you can develop with hot-reload. The only
piece that still benefits from Docker is **PostgreSQL** (tiny image); a fully
local Postgres alternative is covered at the bottom.

> Ports used: **3000** (frontend), **8000** (backend), **5432** (Postgres).

---

## 0. One-time: move Docker's disk image to another drive

Do this in the Docker Desktop UI (safest — it migrates existing data/volumes,
so your scraped products survive):

1. **Docker Desktop → Settings (gear) → Resources → Advanced.**
2. Find **"Disk image location"** and click **Browse…**.
3. Pick a folder on the drive with more space (e.g. `D:\DockerData`).
4. **Apply & Restart.** Docker moves the WSL2 virtual disk there.

After it restarts, confirm the DB volume is still present:

```powershell
& "C:\Users\HP\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe" volume ls
```

You should see `price-pantry_db_data`. (If it's gone, no problem — the backend
recreates the schema + demo data on start, and you can re-scrape.)

---

## 1. One-time: put `docker` on your PATH

Docker Desktop here installed to a non-standard path, so `docker` isn't found in
the terminal. Add it to your **user PATH** permanently (run once, then reopen the
terminal):

```powershell
[Environment]::SetEnvironmentVariable(
  "PATH",
  [Environment]::GetEnvironmentVariable("PATH","User") + ";C:\Users\HP\AppData\Local\Programs\DockerDesktop\resources\bin",
  "User")
```

Reopen VS Code (or the terminal) afterwards. Verify: `docker --version`.

---

## 2. Start Postgres

```powershell
docker compose up -d db
```

That's the only container you need. It listens on `localhost:5432` and persists
data in the `db_data` volume.

---

## 3. Backend — FastAPI (terminal #1)

The venv already exists (`backend/.venv`). Easiest path — one script does
migrate → seed → serve:

```powershell
cd backend
.\dev.ps1
```

<details>
<summary>…or run the steps manually</summary>

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```
</details>

- API:  http://localhost:8000
- Docs: http://localhost:8000/docs

> The backend defaults to `localhost:5432` when run from the `backend/` folder
> (it does **not** read the root `.env`, which targets the Docker network).

---

## 4. Frontend — Next.js (terminal #2)

```powershell
cd frontend
npm install        # one-time (node_modules isn't committed)
npm run dev
```

- App: http://localhost:3000  (talks to the API via `frontend/.env.local`)

---

## 5. Scrape real Tesco data (optional, terminal #3)

Real Tesco data needs your installed **Chrome** headful (Akamai blocks headless).
The scraper venv + Chromium are already set up.

```powershell
cd scrapers
.\scrape_tesco.ps1 milk bread eggs cheese
```

Re-run anytime to append fresh prices (builds price history). See the main
README for details on the Akamai bypass.

---

## One-click in VS Code

`.vscode/tasks.json` defines tasks. Open **Terminal → Run Task…** and pick:

- **Start All (DB + Backend + Frontend)** — runs all three in parallel
- or individually: *DB: Postgres (Docker)*, *Backend: dev*, *Frontend: dev*,
  *Frontend: install*, *Scrape Tesco (real Chrome)*

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker` not recognised | Do step 1 (add to PATH), reopen terminal. |
| Port 8000/3000 already in use | Stop the old process: `Get-NetTCPConnection -LocalPort 8000 \| Select OwningProcess`, then `Stop-Process -Id <pid>`. Or change the port. |
| Backend can't connect to `db` host | You're picking up the root `.env`. Run from `backend/`, or set `$env:DATABASE_URL="postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"`. |
| `dev.ps1` blocked (execution policy) | Run `powershell -ExecutionPolicy Bypass -File dev.ps1`. |
| Frontend shows "Couldn't load products" | Backend isn't up, or `NEXT_PUBLIC_API_URL` is wrong. Confirm http://localhost:8000/products returns JSON. |

---

## Fully Docker-free database (alternative)

If you'd rather not use Docker at all:

1. Install **PostgreSQL 16** for Windows (EDB installer) and start the service.
2. Create the role + database:
   ```sql
   CREATE ROLE pricepantry LOGIN PASSWORD 'pricepantry';
   CREATE DATABASE pricepantry OWNER pricepantry;
   ```
3. Ensure it listens on `localhost:5432` (default). Then run the backend as in
   step 3 — the default `DATABASE_URL` already matches these credentials.
