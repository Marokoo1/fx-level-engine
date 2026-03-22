from __future__ import annotations

from src.models import Level


class LevelRanker:
    def rank_levels(self, levels: list[Level]) -> list[Level]:
        long_levels = [lvl for lvl in levels if lvl.direction == "long"]
        short_levels = [lvl for lvl in levels if lvl.direction == "short"]

        long_levels = sorted(long_levels, key=lambda x: x.strength_score, reverse=True)
        short_levels = sorted(short_levels, key=lambda x: x.strength_score, reverse=True)

        for i, lvl in enumerate(long_levels[:2], start=1):
            lvl.rank = i

        for i, lvl in enumerate(short_levels[:2], start=1):
            lvl.rank = i

        return long_levels[:2] + short_levels[:2]
