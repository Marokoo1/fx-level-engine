# Config Center

This project can now be controlled from one main file:

- `config/settings.yaml`

## What To Edit

### Instruments

Edit:

- `instruments.symbols`

This list decides which symbols are used by the default one-click flow:

- market data download
- level calculation
- HTML and CSV report export
- calendar status and event reports

If this list is empty, the app falls back to:

- `input/symbols.csv`

### Market Data Download

Edit:

- `history.download_timeframes`
- `history.bars`

This controls which timeframes are downloaded and how much history is fetched for each configured instrument.

### POC Calculation

Edit:

- `poc.source_timeframe`
- `poc.bucket_mode`
- `poc.bucket_size_pips`
- `poc.value_area_pct`
- `poc.min_bars_per_profile`

### IB Calculation

Edit:

- `ib.weekly_anchor`
- `ib.monthly_anchor`
- `ib.yearly_anchor`
- `ib.multipliers`
- `ib.periods.W`
- `ib.periods.M`
- `ib.periods.Y`

### Report Types

Edit:

- `tables.intraday`
- `tables.swing`
- `tables.invest`
- `matrix_tables.poc_matrix`
- `matrix_tables.ib_matrix`
- `matrix_tables.swing_poc_matrix`
- `matrix_tables.swing_ib_matrix`
- `matrix_tables.invest_poc_matrix`
- `matrix_tables.invest_ib_matrix`

### Economic Calendar

Edit:

- `economic_calendar.enabled`
- `economic_calendar.sources`
- `economic_calendar.cache_ttl_hours`
- `economic_calendar.trading_restrictions.quiet_minutes`
- `economic_calendar.trading_restrictions.importance_threshold`
- `economic_calendar.monitor_symbols`

## Important Behavior

- No calendar-based filtering happens before market data download.
- Data should stay fresh for every configured instrument, whether it is tradeable right now or not.
- Calendar status is used for `open`, `watch`, and `blocked` reporting in the exported views.

## One-Click Flow

The simplest refresh flow is:

- double-click `RUN_AND_OPEN_REPORTS.cmd`

That flow now does this:

1. Reads symbols from `config/settings.yaml`
2. Downloads fresh market history for those symbols
3. Rebuilds all reports
4. Refreshes calendar status in the exported views
5. Opens the main HTML reports

## Recommended Files

- `config/settings.yaml`
- `SESSION_HANDOFF.md`
- `REPORT_HUB.html`
