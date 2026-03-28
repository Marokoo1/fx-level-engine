# FX Level Engine Preview

This is the quick entry point for the current project snapshot.

## Simplest way to open everything

- Double-click `OPEN_REPORT_HUB.cmd` to open a simple browser hub.
- Double-click `RUN_AND_OPEN_REPORTS.cmd` to download fresh data for all configured instruments, rebuild reports, and open the latest results.
- Edit `config/settings.yaml` to control symbols, download depth, calculations, and calendar rules in one place.

## 🤖 NEW: Economic Calendar Agent

The project now includes an autonomous **Economic Calendar Agent** that:
- Automatically downloads a live forex economic calendar from Trading Economics
- Optionally uses the official Trading Economics API when an API key is configured
- Blocks trading on currency pairs during economic news announcements
- Integrates seamlessly with the trading pipeline
- Caches data for 4 hours
- Adds tradeability status to reports when you run `run_daily()` or `run_all()`

**Quick start:**
1. Agent is enabled by default in `config/settings.yaml`
2. When you run `python -m src.main --mode run-daily`, it automatically:
   - Refreshes the economic calendar
   - Keeps market data fresh for all configured instruments
   - Reports blocked pairs in the output

**Learn more:** See [AGENT_SETUP.md](AGENT_SETUP.md) and [docs/ECONOMIC_CALENDAR_AGENT.md](docs/ECONOMIC_CALENDAR_AGENT.md)

## Open these files

- [Config center](CONFIG_CENTER.md)
- [Report hub](REPORT_HUB.html)
- [Session handoff](SESSION_HANDOFF.md)
- [Economic calendar status](data/tables/calendar_status.html)
- [Economic calendar events](data/tables/calendar_events.html)
- [Interactive dashboard](data/tables/intraday_view.html)
- [POC matrix dashboard](data/tables/poc_matrix_view.html)
- [IB matrix dashboard](data/tables/ib_matrix_view.html)
- [Swing POC matrix dashboard](data/tables/swing_poc_matrix_view.html)
- [Swing IB matrix dashboard](data/tables/swing_ib_matrix_view.html)
- [Invest POC matrix dashboard](data/tables/invest_poc_matrix_view.html)
- [Invest IB matrix dashboard](data/tables/invest_ib_matrix_view.html)
- [Intraday summary](data/tables/intraday_summary.csv)
- [POC matrix](data/tables/poc_matrix_view.csv)
- [IB matrix](data/tables/ib_matrix_view.csv)
- [Intraday signals](data/tables/intraday_signals.csv)
- [All levels](data/levels/all_levels.csv)
- [README](README.md)
- **[Agent Setup Guide](AGENT_SETUP.md)** ←  NEW
- **[Agent Documentation](docs/ECONOMIC_CALENDAR_AGENT.md)** ←  NEW

## What this project does

- downloads FX candle history from FXCM
- builds POC and IB levels for intraday, swing, and invest
- exports matrix views for fresh POC and IB levels
- ranks levels and exports CSV, Parquet, and HTML snapshots
- keeps the HTML report fully offline and self-contained
- **[NEW]** monitors economic calendar and blocks trading during high-impact events
- **[NEW]** enriches intraday/swing/invest HTML views with trade-status and next-event context

## Recommended sample run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_majors_reports.ps1 -OpenReports
```

This flow downloads fresh market data for every configured instrument and then rebuilds the reports.

## Resume next time

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_majors_reports.ps1 -OpenReports
```

## Notes

- Open this file in VS Code Markdown Preview for a clean landing page.
- The dashboard does not need internet access.
- If the output changes, rerun the sample command above.
- **[NEW]** The Economic Calendar Agent requires internet for the first fetch, then caches data locally.
