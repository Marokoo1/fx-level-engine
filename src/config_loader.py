from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_settings(path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_symbols(path: str | Path = "input/symbols.csv") -> list[str]:
    df = pd.read_csv(path)
    if "symbol" not in df.columns:
        raise ValueError("symbols.csv must contain a 'symbol' column")
    return df["symbol"].dropna().astype(str).tolist()
