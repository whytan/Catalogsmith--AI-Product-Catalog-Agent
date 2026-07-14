# Run Catalogsmith locally (offline demo mode).
# Usage: .\scripts\run.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Serve = Join-Path $Root ".venv\Scripts\catalogsmith-serve.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual env not found. Run: python -m venv .venv; .\.venv\Scripts\Activate.ps1; .\scripts\repair-venv.ps1"
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

# Always works — does not depend on pip console scripts or uvicorn CLI.
# LLM_MOCK / CHROMA_EPHEMERAL come from .env unless already set in the shell.
& $Python run.py
