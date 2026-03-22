from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

Direction = Literal["long", "short"]
ZoneType = Literal["cumulation", "aggressive_initiation", "strong_rejection"]
LevelStatus = Literal["new", "active", "tested", "consumed", "invalid"]


@dataclass
class Zone:
    zone_id: str
    instrument: str
    timeframe: str
    zone_type: ZoneType
    direction_bias: Optional[Direction]
    zone_low: float
    zone_high: float
    poc: Optional[float]
    created_at: datetime
    strength_score: float = 0.0


@dataclass
class Level:
    level_id: str
    instrument: str
    strategy: str
    build_timeframe: str
    trigger_timeframe: str
    direction: Direction
    rank: int
    price: float
    zone_low: float
    zone_high: float
    source_setup_type: ZoneType
    created_at: datetime
    status: LevelStatus = "new"
    touch_count: int = 0
    strength_score: float = 0.0
