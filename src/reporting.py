from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_table(df: pd.DataFrame, output_dir: str | Path, name: str) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{name}.csv"
    parquet_path = out_dir / f"{name}.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    return csv_path, parquet_path


def save_master_levels(df: pd.DataFrame, output_dir: str | Path) -> tuple[Path, Path]:
    return save_table(df, output_dir, "all_levels")
