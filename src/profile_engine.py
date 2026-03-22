from __future__ import annotations

import pandas as pd


class ProfileEngine:
    """
    První jednoduchá verze.
    Zatím nepočítá plný market profile, ale základní metriky
    nad M30 oknem, které použijeme pro první kandidátní zóny.
    """

    def compute_basic_profile_metrics(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {
                "poc": None,
                "high": None,
                "low": None,
                "total_volume": 0.0,
                "range": 0.0,
            }

        volume_idx = df["volume"].idxmax()
        poc_price = float(df.loc[volume_idx, "close"])

        high = float(df["high"].max())
        low = float(df["low"].min())

        return {
            "poc": poc_price,
            "high": high,
            "low": low,
            "total_volume": float(df["volume"].sum()),
            "range": high - low,
        }
