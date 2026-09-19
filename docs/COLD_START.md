# Price Pantry — Full Cold-Start Manual

Bring the entire application up from nothing (fresh machine or after deleting all
Docker containers/images). Everything runs **natively from the terminal**; only
PostgreSQL optionally uses a small Docker container.

**Result:** API at http://localhost:8000 · App at http://localhost:3000
**Ports:** 3000 (frontend), 8000 (backend), 5432 (Postgres)

---

## Fast path (one command)

From the project root in PowerShell:

```powershell
.\bootstrap.ps1
```

This starts Postgres (Docker), sets up the backend (venv → deps → migrate →
seed), and installs frontend deps. Then start the two servers:

```powershell
# Terminal 1
cd backend; .\dev.ps1
# Terminal 2
cd frontend; npm run dev
```

Prefer no Docker at all? Install Postgres first (Step 2, Option B) then run
`.\bootstrap.ps1 -NoDocker`.

The rest of this document explains every step manually.

---

## 0. Prerequisites

Verify these are installed (all already present on this machine):

```powershell
node --version      # v18+ (have v24)
npm --version
python --version    # 3.11.x   (use `python`, not `py -3.11`)
git --version
```

Plus **one** database option:
- **Docker Desktop** (for the Postgres container), or
- **PostgreSQL 16** installed natively.

> **Docker not on PATH?** This machine installed Docker to a non-standard path.
> Add it permanently (run once, then reopen the terminal):
> ```powershell
> [Environment]::SetEnvironmentVariable("PATH", [Environment]::GetEnvironmentVariable("PATH","User") + ";C:\Users\HP\AppData\Local\Programs\DockerDesktop\resources\bin", "User")
> ```

---

## 1. Environment files

The repo ships an example. Create the real files if missing:

```powershell
# from project root
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path frontend\.env.local)) {
  "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -Encoding utf8 frontend\.env.local
}
```

- Root `.env` → used by Docker Compose (Postgres credentials).
- `frontend/.env.local` → tells the browser where the API is.

---

## 2. Database

### Option A — Postgres via Docker (recommended, smallest effort)

```powershell
docker compose up -d db
```

Pulls `postgres:16-alpine` (~420 MB) if needed and starts it on `localhost:5432`,
persisting data in the `price-pantry_db_data` volume. Check it's healthy:

```powershell
docker compose ps
```

### Option B — Native PostgreSQL (zero Docker)

1. Install **PostgreSQL 16** (EDB installer) and start the service.
2. Create the role + database (via `psql -U postgres`):
   ```sql
   CREATE ROLE pricepantry LOGIN PASSWORD 'pricepantry';
   CREATE DATABASE pricepantry OWNER pricepantry;
   ```
3. Confirm it listens on `localhost:5432` (default).

Either option ends with an empty Postgres at
`postgresql://pricepantry:pricepantry@localhost:5432/pricepantry`.

---

## 3. Backend (FastAPI)

```powershell
cd backend

# Create the venv if it doesn't exist yet
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Point at the local DB (only needed if you didn't use dev.ps1)
$env:DATABASE_URL = "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"

# Create tables, load demo data, run the API
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Or just: **`.\dev.ps1`** (does all of the above).

Verify:
```powershell
curl http://localhost:8000/health      # {"status":"ok","database":"ok"}
```
Interactive docs: http://localhost:8000/docs

> The backend reads the root `.env` only when launched from the repo root. Run it
> from `backend/` (or set `$env:DATABASE_URL`) so it targets `localhost`, not the
> Docker-internal `db` host.

---

## 4. Frontend (Next.js)

In a second terminal:

```powershell
cd frontend
npm install        # first time only
npm run dev
```

Open http://localhost:3000. You should see the seeded products, working search,
pagination, and product pages.

---

## 5. (Optional) Load real Tesco data

The seed gives 8 demo items so the app works immediately. For **real** data,
run the scraper. Tesco is behind Akamai Bot Manager, so this must run **headful
with your installed Chrome** (headless is blocked with HTTP 403).

```powershell
cd scrapers

# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium

# Scrape (a Chrome window opens and browses Tesco — let it run)
.\scrape_tesco.ps1 milk bread eggs cheese chicken
```

`scrape_tesco.ps1` sets `PW_CHANNEL=chrome`, a persistent profile, and the DB
URL for you. Each run appends fresh `prices` rows (building history) and
de-dupes products by `external_id`. ~25–30 products per category per page.

---

## 6. Verify the whole stack

| Check | Expected |
|-------|----------|
| `curl http://localhost:8000/health` | `{"status":"ok","database":"ok"}` |
| `curl "http://localhost:8000/products?page_size=1"` | JSON with `total` ≥ 8 |
| http://localhost:3000 | Product grid renders |
| http://localhost:3000/search?q=milk | Milk results |
| Re-run scraper, open a product page | Price-history chart shows ≥2 points |

---

## 7. Stop / restart / teardown

```powershell
# Stop the servers: Ctrl+C in each terminal.

# Stop Postgres (keeps data):
docker compose stop db

# Start it again later:
docker compose up -d db

# Full teardown INCLUDING data (deletes the volume):
docker compose down -v
```

After a full teardown, repeat Steps 2→4 (migrations + seed recreate everything).

---

## 8. One-click alternative (VS Code)

`.vscode/tasks.json` is included. **Terminal → Run Task…**:
- **Start All (DB + Backend + Frontend)** — all three in parallel
- **Frontend: install** — run once before the first start
- **Scrape Tesco (real Chrome)**

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker` not recognised | Add Docker to PATH (Prerequisites note), reopen terminal. |
| Docker daemon errors | Start **Docker Desktop** and wait for it to say "running". |
| `.ps1` scripts blocked | `powershell -ExecutionPolicy Bypass -File <script>.ps1`. |
| Backend: `could not translate host name "db"` | You're loading the root `.env`. Run from `backend/` or set `$env:DATABASE_URL` to the `localhost` URL. |
| Backend: connection refused on 5432 | Postgres isn't up. `docker compose up -d db` (or start native Postgres). |
| Port 8000/3000 in use | `Get-NetTCPConnection -LocalPort 8000 \| Select OwningProcess`, then `Stop-Process -Id <pid>`. |
| Frontend: "Couldn't load products" | Backend not running, or `NEXT_PUBLIC_API_URL` wrong. Check http://localhost:8000/products. |
| Scraper returns 0 products / 403 | Must be headful + `PW_CHANNEL=chrome` (use `scrape_tesco.ps1`). Ensure Chrome is installed. |
| `playwright` browser missing | `.\.venv\Scripts\python.exe -m playwright install chromium` in `scrapers/`. |

---

## Appendix — full cold start, copy-paste

```powershell
# From the project root, with Docker Desktop running:
.\bootstrap.ps1
# then, in two terminals:
cd backend;  .\dev.ps1
cd frontend; npm run dev
# optional real data:
cd scrapers; .\scrape_tesco.ps1 milk bread eggs
```
