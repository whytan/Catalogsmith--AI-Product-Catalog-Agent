# Repair a broken local venv (corrupted pip metadata / partial uninstall).
# Usage: .\scripts\repair-venv.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Pip = Join-Path $Root ".venv\Scripts\pip.exe"
$SitePackages = Join-Path $Root ".venv\Lib\site-packages"

if (-not (Test-Path $Python)) {
    Write-Error "No .venv found. Run: python -m venv .venv"
}

Write-Host "Removing corrupted pip metadata from site-packages..."
Get-ChildItem $SitePackages -Force | Where-Object { $_.Name -match '^~' } | ForEach-Object {
    Write-Host "  deleting $($_.Name)"
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Reinstalling catalogsmith in editable mode..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Pip install -e ".[dev]" 2>&1 | Out-Null
$pipOk = $LASTEXITCODE -eq 0
if (-not $pipOk) {
    Write-Host "pip install blocked - writing src path hook..."
    $pthPath = Join-Path $SitePackages "catalogsmith-dev.pth"
    Set-Content -Path $pthPath -Value (Join-Path $Root "src") -Encoding Ascii
    & $Pip install -e ".[dev]" --no-deps 2>&1 | Out-Null
}
$ErrorActionPreference = $prevEap

$pthPath = Join-Path $SitePackages "catalogsmith-dev.pth"
Set-Content -Path $pthPath -Value (Join-Path $Root "src") -Encoding Ascii

Write-Host "Verifying import..."
& $Python -c "import sys; sys.path.insert(0, r'$Root\src'); import agent.main; print('OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Import check failed after reinstall."
}

Write-Host "Venv repaired. Start with: python run.py"
