from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_settings(path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize_symbols(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [str(value).strip() for value in values if str(value).strip()]


def load_symbols(
    path: str | Path = "input/symbols.csv",
    settings_path: str | Path = "config/settings.yaml",
) -> list[str]:
    settings_file = Path(settings_path)
    if settings_file.exists():
        settings = load_settings(settings_file)
        configured_symbols = _normalize_symbols(((settings.get("instruments") or {}).get("symbols")))
        if configured_symbols:
            return configured_symbols

    df = pd.read_csv(path)
    if "symbol" not in df.columns:
        raise ValueError("symbols.csv must contain a 'symbol' column")
    return df["symbol"].dropna().astype(str).tolist()
