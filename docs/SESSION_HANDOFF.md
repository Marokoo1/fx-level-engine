# Session Handoff

Date: 2026-03-28

## What Is Done

- `intraday` view now prioritizes `current_price`, IB, POC, and distances.
- HTML report is fully self-contained and works offline.
- `preview.md` exists as the clean VS Code entry point.
- Two matrix views were added:
  - `poc_matrix`
  - `ib_matrix`
- Matrix views use the same dark/offline dashboard styling.
- Matrix config is stored in `config/settings.yaml`.

## Current State

- `ib_matrix` is working and fills `Res1/Res2/Sup1/Sup2` nicely.
- `poc_matrix` currently looks sparse because there are not many fresh POC candidates in the current data.
- Confluence badges are wired in the matrix layer, but no strong hits are showing yet.

## Important Files

- `src/matrix_builder.py`
- `src/pipeline.py`
- `src/html_report.py`
- `config/settings.yaml`
- `preview.md`

## Re-run Command

```powershell
& 'C:\Users\User\AppData\Local\Programs\Python\Python311\python.exe' -m src.main --mode export-all --symbols EUR/USD USD/JPY
```

## Next Best Steps

1. Add more POC calculations so `poc_matrix` has more usable fresh candidates.
2. Tune the matrix selection rules and labels to match the reference table more closely.
3. If needed, make confluence a separate view later.

## Note

If you come back tomorrow, start from this file and `preview.md`. The workspace already contains the changes, so nothing special is needed beyond reopening the repo.
