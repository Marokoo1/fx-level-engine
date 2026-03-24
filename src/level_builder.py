from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from .ib_engine import IBResult
from .models import LevelRecord
from .profile_engine import ProfileResult
from .utils import pip_size, utc_now


def _level_status(level_price: float, post_df: pd.DataFrame) -> tuple[str, int, str | None, str | None]:
    if post_df.empty:
        return "fresh", 0, None, None

    touched = post_df[(post_df["low"] <= level_price) & (post_df["high"] >= level_price)].copy()
    crosses = post_df[
        ((post_df["close"].shift(1) < level_price) & (post_df["close"] > level_price)) |
        ((post_df["close"].shift(1) > level_price) & (post_df["close"] < level_price))
    ].copy()

    touch_count = int(len(touched))
    first_touch = touched["timestamp"].iloc[0].isoformat() if not touched.empty else None
    first_cross = crosses["timestamp"].iloc[0].isoformat() if not crosses.empty else None

    if first_cross:
        status = "crossed"
    elif touch_count > 0:
        status = "tested"
    else:
        status = "fresh"
    return status, touch_count, first_touch, first_cross


def _direction(level_price: float, last_price: float) -> str:
    return "long" if level_price <= last_price else "short"


def _make_record(
    *,
    table_type: str,
    symbol: str,
    level_family: str,
    level_period: str,
    level_name: str,
    level_price: float,
    zone_low: float,
    zone_high: float,
    last_price: float,
    post_df: pd.DataFrame,
    build_timeframe: str,
    entry_timeframe: str,
    source_data: str,
    notes: str,
) -> dict:
    signed_pips = (level_price - last_price) / pip_size(symbol)
    status, touch_count, first_touch, first_cross = _level_status(level_price, post_df)
    rec = LevelRecord(
        asof_time=utc_now(),
        symbol=symbol,
        table_type=table_type,
        level_family=level_family,
        level_period=level_period,
        level_name=level_name,
        direction=_direction(level_price, last_price),
        level_price=float(level_price),
        zone_low=float(zone_low),
        zone_high=float(zone_high),
        last_price=float(last_price),
        distance_pips=float(signed_pips),
        distance_pips_abs=float(abs(signed_pips)),
        is_above_price=bool(level_price > last_price),
        is_below_price=bool(level_price < last_price),
        status=status,
        touch_count=touch_count,
        first_touch_time=first_touch,
        first_cross_time=first_cross,
        source_data=source_data,
        build_timeframe=build_timeframe,
        entry_timeframe=entry_timeframe,
        notes=notes,
    )
    return asdict(rec)


def build_poc_rows(symbol: str, poc: ProfileResult, last_price: float, post_df: pd.DataFrame, table_type: str, build_timeframe: str, entry_timeframe: str) -> list[dict]:
    rows = []
    base_name = f"{poc.period_code}_POC"
    rows.append(_make_record(
        table_type=table_type,
        symbol=symbol,
        level_family="POC",
        level_period=poc.period_code,
        level_name=base_name,
        level_price=poc.poc_price,
        zone_low=poc.val,
        zone_high=poc.vah,
        last_price=last_price,
        post_df=post_df,
        build_timeframe=build_timeframe,
        entry_timeframe=entry_timeframe,
        source_data="fxcm_m30",
        notes=f"Profile {poc.profile_id} | close {poc.profile_close:.5f}",
    ))
    return rows


def build_ib_rows(symbol: str, ib: IBResult, last_price: float, post_df: pd.DataFrame, table_type: str, build_timeframe: str, entry_timeframe: str) -> list[dict]:
    rows = []
    for level_name, level_price in ib.levels.items():
        rows.append(_make_record(
            table_type=table_type,
            symbol=symbol,
            level_family="IB",
            level_period=ib.period_code,
            level_name=level_name,
            level_price=level_price,
            zone_low=level_price,
            zone_high=level_price,
            last_price=last_price,
            post_df=post_df,
            build_timeframe=build_timeframe,
            entry_timeframe=entry_timeframe,
            source_data="fxcm_m30/d1",
            notes=f"Anchor {ib.anchor_id} | range {ib.ib_range:.5f}",
        ))
    return rows
