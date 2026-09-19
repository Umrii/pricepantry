# Run the backend locally (no Docker): migrate -> seed -> serve with autoreload.
# Requires a Postgres reachable at localhost:5432 (see docs/LOCAL_DEV.md).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# One-time venv setup if missing.
if (-not (Test-Path ".venv")) {
    Write-Host "[setup] creating venv + installing deps..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
}

# Talk to Postgres on localhost (native run), unless already overridden.
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"
}

Write-Host "[db]  applying migrations..."
.\.venv\Scripts\python.exe -m alembic upgrade head
Write-Host "[db]  seeding demo data..."
.\.venv\Scripts\python.exe -m app.seed
Write-Host "[api] starting uvicorn on http://localhost:8000 ..."
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
