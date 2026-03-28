$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$reports = @(
    "data\tables\calendar_status.html",
    "data\tables\calendar_events.html",
    "data\tables\intraday_view.html",
    "data\tables\swing_view.html",
    "data\tables\invest_view.html",
    "data\tables\poc_matrix_view.html",
    "data\tables\ib_matrix_view.html",
    "data\tables\swing_poc_matrix_view.html",
    "data\tables\swing_ib_matrix_view.html",
    "data\tables\invest_poc_matrix_view.html",
    "data\tables\invest_ib_matrix_view.html"
)

foreach ($relativePath in $reports) {
    $fullPath = Join-Path $repoRoot $relativePath
    if (Test-Path $fullPath) {
        Start-Process $fullPath
    }
}
