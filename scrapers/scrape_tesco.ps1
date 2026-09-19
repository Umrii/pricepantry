# Scrape real Tesco data using the host's real Chrome (beats Akamai).
# Usage:  .\scrape_tesco.ps1                 # default categories
#         .\scrape_tesco.ps1 milk bread      # custom categories
#         .\scrape_tesco.ps1 -DryRun milk    # don't write to the DB
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Categories,
    [switch]$DryRun,
    [int]$MaxPages = 1
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# One-time setup if the venv is missing.
if (-not (Test-Path ".venv")) {
    Write-Host "[setup] creating venv + installing Playwright Chromium..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    .\.venv\Scripts\python.exe -m playwright install chromium
}

$env:PW_CHANNEL = "chrome"
$env:PW_USER_DATA_DIR = "$env:TEMP\pp-chrome-profile"
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"
}

$pyArgs = @("-m", "run", "--headful", "--max-pages", "$MaxPages")
if ($DryRun) { $pyArgs += "--dry-run" }
if ($Categories -and $Categories.Count -gt 0) {
    $pyArgs += "--categories"
    $pyArgs += $Categories
}

.\.venv\Scripts\python.exe @pyArgs
