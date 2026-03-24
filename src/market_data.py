from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .fxcm_source import FXCMSource


def history_start_for_bars(timeframe: str, bars: int) -> datetime:
    now = datetime.now(timezone.utc)
    tf = timeframe.lower()
    if tf == "m30":
        return now - timedelta(minutes=30 * (bars + 200))
    if tf == "d1":
        return now - timedelta(days=bars + 50)
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "")


def download_symbol_histories(source: FXCMSource, symbol: str, settings: dict) -> dict[str, Path]:
    raw_dir = Path(settings["storage"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    for timeframe in settings["history"]["download_timeframes"]:
        bars = int(settings["history"]["bars"][timeframe])
        date_from = history_start_for_bars(timeframe, bars)
        df = source.get_history(symbol, timeframe, date_from=date_from, date_to=None, quotes_count=bars)
        out_path = raw_dir / f"{safe_symbol(symbol)}_{timeframe}.parquet"
        source.save_history(df, out_path)
        outputs[timeframe] = out_path
    return outputs


def load_symbol_history(symbol: str, timeframe: str, settings: dict) -> pd.DataFrame:
    raw_dir = Path(settings["storage"]["raw_dir"])
    path = raw_dir / f"{safe_symbol(symbol)}_{timeframe.lower()}.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)


def get_last_price(symbol: str, settings: dict) -> float:
    m30 = load_symbol_history(symbol, "m30", settings)
    return float(m30["close"].iloc[-1])
