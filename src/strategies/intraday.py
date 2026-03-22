from __future__ import annotations

import pandas as pd

from src.level_builder import LevelBuilder
from src.level_ranker import LevelRanker
from src.zone_detector import ZoneDetector


class IntradayStrategy:
    def __init__(self, config: dict):
        self.config = config
        self.zone_detector = ZoneDetector()
        self.level_builder = LevelBuilder()
        self.level_ranker = LevelRanker()

    def build_levels(self, instrument: str, df_m30: pd.DataFrame):
        zones = self.zone_detector.detect_cumulation_zones(
            instrument=instrument,
            timeframe="M30",
            df=df_m30,
            window_size=20,
        )

        levels = self.level_builder.build_levels_from_zones(
            strategy="intraday",
            build_tf="M30",
            trigger_tf="M1",
            zones=zones,
        )

        ranked = self.level_ranker.rank_levels(levels)
        return ranked
