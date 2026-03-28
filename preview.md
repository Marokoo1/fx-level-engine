# FX Level Engine Preview

This is the quick entry point for the current project snapshot.

## Open these files

- [Interactive dashboard](data/tables/intraday_view.html)
- [POC matrix dashboard](data/tables/poc_matrix_view.html)
- [IB matrix dashboard](data/tables/ib_matrix_view.html)
- [Intraday summary](data/tables/intraday_summary.csv)
- [POC matrix](data/tables/poc_matrix_view.csv)
- [IB matrix](data/tables/ib_matrix_view.csv)
- [Intraday signals](data/tables/intraday_signals.csv)
- [All levels](data/levels/all_levels.csv)
- [README](README.md)

## What this project does

- downloads FX candle history from FXCM
- builds POC and IB levels for intraday, swing, and invest
- exports matrix views for fresh POC and IB levels
- ranks levels and exports CSV, Parquet, and HTML snapshots
- keeps the HTML report fully offline and self-contained

## Recommended sample run

```powershell
& 'C:\Users\User\AppData\Local\Programs\Python\Python311\python.exe' -m src.main --mode export-all --symbols EUR/USD USD/JPY
```

## Notes

- Open this file in VS Code Markdown Preview for a clean landing page.
- The dashboard does not need internet access.
- If the output changes, rerun the sample command above.
