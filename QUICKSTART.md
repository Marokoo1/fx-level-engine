# QUICK START

## Main Idea

Everything important is now controlled from one main file:

- `config/settings.yaml`

Edit there:

- `instruments.symbols`
- `history.download_timeframes`
- `history.bars`
- `poc.*`
- `ib.*`
- `tables.*`
- `matrix_tables.*`
- `economic_calendar.*`

Config overview:

- `CONFIG_CENTER.md`

## Simplest Start

### Just open the latest reports

Double-click:

- `OPEN_REPORT_HUB.cmd`

### Download fresh data and rebuild everything

Double-click:

- `RUN_AND_OPEN_REPORTS.cmd`

That flow does this:

1. Reads symbols from `config/settings.yaml`
2. Downloads fresh market data for all configured instruments
3. Rebuilds reports
4. Refreshes economic calendar status in the outputs
5. Opens the main HTML reports

## Main Reports

- `data/tables/calendar_status.html`
- `data/tables/calendar_events.html`
- `data/tables/intraday_view.html`
- `data/tables/swing_view.html`
- `data/tables/invest_view.html`
- `data/tables/poc_matrix_view.html`
- `data/tables/ib_matrix_view.html`
- `data/tables/swing_poc_matrix_view.html`
- `data/tables/swing_ib_matrix_view.html`
- `data/tables/invest_poc_matrix_view.html`
- `data/tables/invest_ib_matrix_view.html`

## Command Line Alternative

Refresh data and rebuild reports:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_majors_reports.ps1 -OpenReports
```

Download only:

```powershell
& .\.python37-embed\python.exe -m src.main --mode download
```

Export only:

```powershell
& .\.python37-embed\python.exe -m src.main --mode export-all
```

Run the combined pipeline:

```powershell
& .\.python37-embed\python.exe -m src.main --mode run-all
```

## Important Behavior

- No calendar-based filtering happens before market data download.
- Data should stay fresh for every configured instrument, whether it is tradeable right now or not.
- Economic calendar status is used for reporting:
  - `open`
  - `watch`
  - `blocked`

## Where To Add Instruments

Edit:

- `config/settings.yaml`

Section:

```yaml
instruments:
  symbols:
    - EUR/USD
    - GBP/USD
    - USD/JPY
```

If you add more instruments there, the one-click launcher uses them automatically for:

- download
- calculation
- export

## Troubleshooting

If rebuild fails with `PermissionError` on `data/tables/*.csv`:

- close open CSV/HTML preview windows
- run `RUN_AND_OPEN_REPORTS.cmd` again

If calendar refresh is temporarily unavailable:

- reports can still use the last cached events from `data/state/economic_events.json`

## Useful Files

- `preview.md`
- `SESSION_HANDOFF.md`
- `CONFIG_CENTER.md`
- `REPORT_HUB.html`
