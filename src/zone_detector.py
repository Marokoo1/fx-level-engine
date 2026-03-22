from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pandas as pd

from src.models import Zone
from src.profile_engine import ProfileEngine


class ZoneDetector:
    """
    První jednoduchý detector cumulation zóny na M30.
    Zatím bere poslední okno barů a z něj vytvoří kandidátní oblast.
    """

    def __init__(self) -> None:
        self.profile_engine = ProfileEngine()

    def detect_cumulation_zones(
        self,
        instrument: str,
        timeframe: str,
        df: pd.DataFrame,
        window_size: int = 20,
    ) -> list[Zone]:
        if df.empty:
            return []

        last_n = min(len(df), window_size)
        window = df.tail(last_n).copy()

        metrics = self.profile_engine.compute_basic_profile_metrics(window)
        if metrics["poc"] is None:
            return []

        zone = Zone(
            zone_id=str(uuid4()),
            instrument=instrument,
            timeframe=timeframe,
            zone_type="cumulation",
            direction_bias=None,
            zone_low=float(window["low"].min()),
            zone_high=float(window["high"].max()),
            poc=float(metrics["poc"]),
            created_at=datetime.utcnow(),
            strength_score=0.0,
        )
        return [zone]
