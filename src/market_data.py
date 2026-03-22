from __future__ import annotations

from pathlib import Path
import pandas as pd


class MarketDataStore:
    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, timeframe: str) -> Path:
        return self.raw_dir / f"{symbol}_{timeframe}.parquet"

    def save_bars(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Path:
        path = self._path(symbol, timeframe)
        df.to_parquet(path, index=False)
        return path

    def load_bars(self, symbol: str, timeframe: str) -> pd.DataFrame:
        path = self._path(symbol, timeframe)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        return pd.read_parquet(path)
