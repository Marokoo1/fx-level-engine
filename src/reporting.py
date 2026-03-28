from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_table(df: pd.DataFrame, output_dir: str | Path, name: str) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{name}.csv"
    parquet_path = out_dir / f"{name}.parquet"
    try:
        df.to_csv(csv_path, index=False)
    except PermissionError as exc:
        raise PermissionError(
            f"Cannot write {csv_path}. The file is likely open in VS Code, Excel, or another preview window. "
            "Close that file and run the export again."
        ) from exc

    try:
        df.to_parquet(parquet_path, index=False)
    except PermissionError as exc:
        raise PermissionError(
            f"Cannot write {parquet_path}. The file is likely open in another app or preview window. "
            "Close that file and run the export again."
        ) from exc
    return csv_path, parquet_path


def save_master_levels(df: pd.DataFrame, output_dir: str | Path) -> tuple[Path, Path]:
    return save_table(df, output_dir, "all_levels")
