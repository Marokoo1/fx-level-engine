from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from src.models import Level, Zone


class LevelBuilder:
    """
    První jednoduchá verze:
    z jedné zóny vytvoří long a short kandidátní level na POC.
    """

    def build_levels_from_zones(
        self,
        strategy: str,
        build_tf: str,
        trigger_tf: str,
        zones: list[Zone],
    ) -> list[Level]:
        levels: list[Level] = []

        for zone in zones:
            if zone.poc is None:
                continue

            levels.append(
                Level(
                    level_id=str(uuid4()),
                    instrument=zone.instrument,
                    strategy=strategy,
                    build_timeframe=build_tf,
                    trigger_timeframe=trigger_tf,
                    direction="long",
                    rank=1,
                    price=zone.poc,
                    zone_low=zone.zone_low,
                    zone_high=zone.zone_high,
                    source_setup_type=zone.zone_type,
                    created_at=datetime.utcnow(),
                    status="new",
                    strength_score=zone.strength_score,
                )
            )

            levels.append(
                Level(
                    level_id=str(uuid4()),
                    instrument=zone.instrument,
                    strategy=strategy,
                    build_timeframe=build_tf,
                    trigger_timeframe=trigger_tf,
                    direction="short",
                    rank=1,
                    price=zone.poc,
                    zone_low=zone.zone_low,
                    zone_high=zone.zone_high,
                    source_setup_type=zone.zone_type,
                    created_at=datetime.utcnow(),
                    status="new",
                    strength_score=zone.strength_score,
                )
            )

        return levels
