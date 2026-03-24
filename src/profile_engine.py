from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from .utils import bucket_size_for_symbol


@dataclass
class ProfileResult:
    period_code: str
    profile_id: str
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    poc_price: float
    vah: float
    val: float
    profile_high: float
    profile_low: float
    profile_close: float
    profile_volume: float
    bars_in_profile: int


def _iso_week_key(ts: pd.Series) -> pd.Series:
    iso = ts.dt.isocalendar()
    return iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)


def _completed_previous_group(df: pd.DataFrame, period_code: str) -> tuple[str, pd.DataFrame]:
    work = df.copy()
    ts = pd.to_datetime(work["timestamp"], utc=True)

    if period_code == "W":
        work["group_key"] = _iso_week_key(ts)
    elif period_code == "M":
        work["group_key"] = ts.dt.strftime("%Y-%m")
    elif period_code == "Y":
        work["group_key"] = ts.dt.strftime("%Y")
    else:
        raise ValueError(f"Unsupported period_code: {period_code}")

    keys = work["group_key"].drop_duplicates().tolist()
    if len(keys) < 2:
        raise ValueError(f"Not enough completed groups for {period_code}")

    last_complete_key = keys[-2]
    group = work.loc[work["group_key"] == last_complete_key].copy()
    return last_complete_key, group


def _distribute_bar_volume(low: float, high: float, volume: float, bucket_edges: np.ndarray) -> np.ndarray:
    if pd.isna(low) or pd.isna(high) or pd.isna(volume):
        return np.zeros(len(bucket_edges) - 1)
    if high < low:
        low, high = high, low
    arr = np.zeros(len(bucket_edges) - 1)
    if high == low:
        idx = np.searchsorted(bucket_edges, low, side="right") - 1
        if 0 <= idx < len(arr):
            arr[idx] = float(volume)
        return arr
    touched = (bucket_edges[:-1] < high) & (bucket_edges[1:] > low)
    n = int(touched.sum())
    if n > 0:
        arr[touched] = float(volume) / n
    return arr


def _build_profile(group: pd.DataFrame, symbol: str, settings: dict) -> tuple[np.ndarray, np.ndarray]:
    bucket_size = bucket_size_for_symbol(symbol, settings)
    price_min = float(group["low"].min())
    price_max = float(group["high"].max())
    start = np.floor(price_min / bucket_size) * bucket_size
    end = np.ceil(price_max / bucket_size) * bucket_size + bucket_size
    edges = np.arange(start, end + bucket_size, bucket_size)
    volumes = np.zeros(len(edges) - 1)

    for _, row in group.iterrows():
        volumes += _distribute_bar_volume(float(row["low"]), float(row["high"]), float(row["volume"]), edges)
    return edges, volumes


def _compute_value_area(edges: np.ndarray, volumes: np.ndarray, value_area_pct: float) -> tuple[float, float, float]:
    centers = (edges[:-1] + edges[1:]) / 2.0
    poc_idx = int(np.argmax(volumes))
    poc = float(centers[poc_idx])

    target = float(volumes.sum()) * value_area_pct
    included = {poc_idx}
    current = float(volumes[poc_idx])
    left = poc_idx - 1
    right = poc_idx + 1
    while current < target and (left >= 0 or right < len(volumes)):
        left_vol = float(volumes[left]) if left >= 0 else -1.0
        right_vol = float(volumes[right]) if right < len(volumes) else -1.0
        if right_vol >= left_vol:
            if right < len(volumes):
                included.add(right)
                current += float(volumes[right])
                right += 1
            elif left >= 0:
                included.add(left)
                current += float(volumes[left])
                left -= 1
        else:
            if left >= 0:
                included.add(left)
                current += float(volumes[left])
                left -= 1
            elif right < len(volumes):
                included.add(right)
                current += float(volumes[right])
                right += 1

    idxs = sorted(included)
    vah = float(centers[max(idxs)])
    val = float(centers[min(idxs)])
    return poc, vah, val


def calculate_active_poc(df_m30: pd.DataFrame, symbol: str, period_code: str, settings: dict) -> ProfileResult:
    profile_id, group = _completed_previous_group(df_m30, period_code)
    if len(group) < int(settings["poc"]["min_bars_per_profile"]):
        raise ValueError(f"Not enough bars for {symbol} {period_code} profile")
    edges, volumes = _build_profile(group, symbol, settings)
    poc, vah, val = _compute_value_area(edges, volumes, float(settings["poc"]["value_area_pct"]))
    return ProfileResult(
        period_code=period_code,
        profile_id=profile_id,
        start_time=pd.Timestamp(group["timestamp"].min()),
        end_time=pd.Timestamp(group["timestamp"].max()),
        poc_price=poc,
        vah=vah,
        val=val,
        profile_high=float(group["high"].max()),
        profile_low=float(group["low"].min()),
        profile_close=float(group["close"].iloc[-1]),
        profile_volume=float(group["volume"].sum()),
        bars_in_profile=int(len(group)),
    )
