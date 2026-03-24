from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LevelRecord:
    asof_time: datetime
    symbol: str
    table_type: str
    level_family: str
    level_period: str
    level_name: str
    direction: str
    level_price: float
    zone_low: float
    zone_high: float
    last_price: float
    distance_pips: float
    distance_pips_abs: float
    is_above_price: bool
    is_below_price: bool
    status: str
    touch_count: int
    first_touch_time: str | None
    first_cross_time: str | None
    source_data: str
    build_timeframe: str
    entry_timeframe: str
    notes: str
