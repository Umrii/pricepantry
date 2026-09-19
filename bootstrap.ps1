# ============================================================================
# Price Pantry - cold-start bootstrap (one-shot setup)
#
# Provisions everything needed to run the app, then leaves you to start the
# backend and frontend servers in their own terminals.
#
#   Database:  starts the Postgres container (docker compose up -d db)
#   Backend:   creates venv, installs deps, runs migrations, seeds demo data
#   Frontend:  installs npm dependencies
#
# Usage:   .\bootstrap.ps1              # full setup (Docker Postgres)
#          .\bootstrap.ps1 -NoDocker    # skip DB; you provide Postgres yourself
# ============================================================================
param([switch]$NoDocker)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$dbUrl = "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"

function Section($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

# --- 0. Put Docker on PATH for this session ---------------------------------
$dockerBin = "C:\Users\HP\AppData\Local\Programs\DockerDesktop\resources\bin"
if (Test-Path $dockerBin) { $env:PATH = "$dockerBin;$env:PATH" }

# --- 1. Database (Postgres) -------------------------------------------------
if (-not $NoDocker) {
    Section "Database (Postgres via Docker)"
    try { docker info *> $null } catch {
        Write-Host "Docker daemon not reachable. Start Docker Desktop and re-run," -ForegroundColor Yellow
        Write-Host "or use -NoDocker with a native Postgres on localhost:5432." -ForegroundColor Yellow
        exit 1
    }
    Set-Location $root
    docker compose up -d db

    Write-Host "Waiting for Postgres to be ready..." -NoNewline
    for ($i = 0; $i -lt 30; $i++) {
        try {
            docker compose exec -T db pg_isready -U pricepantry -d pricepantry *> $null
            if ($LASTEXITCODE -eq 0) { break }
        } catch {}
        Start-Sleep -Seconds 1; Write-Host "." -NoNewline
    }
    Write-Host " ready."
} else {
    Section "Database (native - skipping Docker)"
    Write-Host "Ensure PostgreSQL is running on localhost:5432 with role/db 'pricepantry'."
}

# --- 2. Backend -------------------------------------------------------------
Section "Backend (FastAPI)"
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating venv + installing dependencies..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
}
$env:DATABASE_URL = $dbUrl
Write-Host "Applying migrations..."
.\.venv\Scripts\python.exe -m alembic upgrade head
Write-Host "Seeding demo data..."
.\.venv\Scripts\python.exe -m app.seed

# --- 3. Frontend ------------------------------------------------------------
Section "Frontend (Next.js)"
Set-Location "$root\frontend"
if (-not (Test-Path ".env.local")) {
    "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -Encoding utf8 ".env.local"
}
Write-Host "Installing npm dependencies (this can take a minute)..."
npm install

# --- Done -------------------------------------------------------------------
Set-Location $root
Section "Setup complete - start the servers in two terminals"
Write-Host "  Terminal 1:  cd backend;  .\dev.ps1        # API  -> http://localhost:8000"
Write-Host "  Terminal 2:  cd frontend; npm run dev      # App  -> http://localhost:3000"
Write-Host "`n  (Optional) real Tesco data:  cd scrapers; .\scrape_tesco.ps1 milk bread eggs`n"
