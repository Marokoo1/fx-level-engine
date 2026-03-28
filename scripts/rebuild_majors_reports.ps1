param(
    [switch]$OpenReports
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".python37-embed\python.exe"

if (-not (Test-Path $python)) {
    throw "Embedded Python runtime not found at $python"
}

Write-Host "Downloading fresh market data for configured instruments..." -ForegroundColor Cyan
Write-Host "Source of symbols: config/settings.yaml -> instruments.symbols" -ForegroundColor DarkCyan
& $python -m src.main --mode download
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Download failed." -ForegroundColor Red
    Write-Host "Check FXCM connectivity, credentials, and network access, then rerun the script." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Rebuilding reports with the latest market data and calendar..." -ForegroundColor Cyan
& $python -m src.main --mode export-all
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Export failed." -ForegroundColor Red
    Write-Host "If the error mentions PermissionError on data/tables/*.csv, close any open CSV/HTML previews and rerun the script." -ForegroundColor Yellow
    Write-Host "If the error mentions Trading Economics network access, the cached calendar can still be inspected in data/state/economic_events.json." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Reports updated under data/tables" -ForegroundColor Green

if ($OpenReports) {
    & (Join-Path $PSScriptRoot "open_latest_reports.ps1")
}
