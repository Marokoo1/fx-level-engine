# Session Handoff

Date: 2026-03-28

## Current State

- Economic calendar integration is live and uses Trading Economics by default.
- Configured symbols now live in `config/settings.yaml` under `instruments.symbols`.
- The pipeline generates dedicated calendar reports:
  - `data/tables/calendar_status.html`
  - `data/tables/calendar_events.html`
- `REPORT_HUB.html` is now the browser entry point and opens reports in new tabs.
- Matrix reports are now split by horizon:
  - `intraday` matrix uses weekly sources
  - `swing` matrix uses monthly sources
  - `invest` matrix uses yearly sources
- Weekly IB is disabled. Monthly and yearly IB now use human-readable labels like:
  - `M IB 150`
  - `M IB -200`
  - `Y IB HIGH`
- POC matrix reports now include `POC`, `VAH`, and `VAL` in compact `Above / Below` columns.
- HTML matrix tables no longer show `asof_time` inside the grid; hub stats still show update time.
- Market data download currently refreshes the full configured rolling window each run and then recalculates all levels from scratch.

## Last Verified Run

Verified successfully:

```powershell
& .\.python37-embed\python.exe -m py_compile src\level_builder.py src\matrix_builder.py src\pipeline.py src\html_report.py src\reporting.py
& .\.python37-embed\python.exe -c "from src.config_loader import load_settings, load_symbols; from src.pipeline import build_all_levels, export_tables; settings = load_settings(); symbols = load_symbols(); df = build_all_levels(settings, symbols); export_tables(df, settings, table_names=['poc_matrix','swing_poc_matrix','invest_poc_matrix','ib_matrix','swing_ib_matrix','invest_ib_matrix'], symbols=symbols)"
```

Current matrix snapshot after the last targeted export:

- `poc_matrix`: `11` selected fresh levels
- `swing_poc_matrix`: `13`
- `invest_poc_matrix`: `20`
- `ib_matrix`: weekly-only and therefore currently empty because weekly IB is disabled
- `swing_ib_matrix`: monthly-only and populated
- `invest_ib_matrix`: yearly-only and populated

Still blocked:

- full `export-all` currently fails on a Windows file lock:
  - `data/tables/swing_signals.csv`
- this is not a code crash; it is an external file lock from another process or preview window

## Fast Resume

Refresh data and rebuild reports for all configured instruments:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_majors_reports.ps1
```

Double-click launchers in the repo root:

- `OPEN_REPORT_HUB.cmd`
- `RUN_AND_OPEN_REPORTS.cmd`
- Main config file: `config/settings.yaml`
- Config overview: `CONFIG_CENTER.md`
- Session handoff: `SESSION_HANDOFF.md`

Rebuild and open the main reports:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_majors_reports.ps1 -OpenReports
```

Open the latest reports without rebuilding:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_latest_reports.ps1
```

## Main Files To Continue In

- `src/economic_calendar.py`
- `src/market_monitor.py`
- `src/pipeline.py`
- `src/html_report.py`
- `src/matrix_builder.py`
- `src/level_builder.py`
- `src/main.py`
- `config/settings.yaml`

## Main Outputs To Inspect

- `data/tables/calendar_status.html`
- `data/tables/calendar_events.html`
- `data/tables/poc_matrix_view.html`
- `data/tables/swing_poc_matrix_view.html`
- `data/tables/invest_poc_matrix_view.html`
- `data/tables/ib_matrix_view.html`
- `data/tables/swing_ib_matrix_view.html`
- `data/tables/invest_ib_matrix_view.html`
- `data/state/economic_events.json`

## Suggested Next Steps

1. Close the process that is locking `data/tables/swing_signals.csv` and rerun full `export-all` or `RUN_AND_OPEN_REPORTS.cmd`.
2. Decide whether `intraday IB` should stay empty with weekly-only logic, or whether weekly IB should be re-enabled later.
3. If more untouched POC levels are needed, extend the POC engine to calculate multiple historical completed profiles, not just the latest completed one.
4. Consider converting market data refresh from full-window redownload to incremental append.

## Notes

- The repo currently contains generated outputs and history files.
- Local Python runtime folders are now ignored in `.gitignore`.
- If a rebuild fails with `PermissionError` on `data/tables/*.csv`, close open file previews or the owning app and rerun the helper script.
- If Trading Economics is temporarily unreachable, the last cached events remain in `data/state/economic_events.json`.
- Calendar status does not filter symbols before market data download; all configured instruments should still be refreshed.
