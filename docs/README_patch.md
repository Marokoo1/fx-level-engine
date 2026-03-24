This patch adds an FXCM-only pipeline for:
- downloading FXCM candle history via ForexConnect
- computing active W/M/Y POC levels
- computing active W/M/Y IB levels and multipliers
- exporting human-readable signal tables: intraday, swing, invest
- automatic refresh logic: daily / weekly / biweekly

Run manually each day:
    python -m src.main --mode run-daily

Recommended automation:
- Linux cron: run once daily after FXCM data is available
- Windows Task Scheduler: run once daily at a fixed server time

Environment variables required:
- FXCM_USER
- FXCM_PASSWORD
- FXCM_URL (usually http://www.fxcorporate.com/Hosts.jsp)
- FXCM_CONNECTION (Demo or Real)
- FXCM_SESSION_ID (optional)
- FXCM_PIN (optional)
