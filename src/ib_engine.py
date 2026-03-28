from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class IBResult:
    period_code: str
    anchor_id: str
    anchor_start: pd.Timestamp
    anchor_end: pd.Timestamp
    ib_high: float
    ib_low: float
    ib_range: float
    levels: dict[str, float]


def _iso_week_key(ts: pd.Series) -> pd.Series:
    iso = ts.dt.isocalendar()
    return iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)


def _current_week_group(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    ts = pd.to_datetime(df["timestamp"], utc=True)
    work = df.copy()
    work["week_key"] = _iso_week_key(ts)
    key = work["week_key"].iloc[-1]
    return key, work.loc[work["week_key"] == key].copy()


def _current_month_group(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    ts = pd.to_datetime(df["timestamp"], utc=True)
    work = df.copy()
    work["month_key"] = ts.dt.strftime("%Y-%m")
    key = work["month_key"].iloc[-1]
    return key, work.loc[work["month_key"] == key].copy()


def _current_year_group(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    ts = pd.to_datetime(df["timestamp"], utc=True)
    work = df.copy()
    work["year_key"] = ts.dt.strftime("%Y")
    key = work["year_key"].iloc[-1]
    return key, work.loc[work["year_key"] == key].copy()


def _first_day_of_week(df_m30: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    ts = pd.to_datetime(df_m30["timestamp"], utc=True)
    work = df_m30.copy()
    work["day"] = ts.dt.floor("D")
    first_day = work["day"].min()
    anchor = work.loc[work["day"] == first_day].copy()
    return pd.Timestamp(anchor["timestamp"].min()), pd.Timestamp(anchor["timestamp"].max()), anchor


def _first_week_of_month(df_m30: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    ts = pd.to_datetime(df_m30["timestamp"], utc=True)
    work = df_m30.copy()
    work["day"] = ts.dt.floor("D")
    days = sorted(work["day"].drop_duplicates().tolist())
    first_days = days[:5]
    anchor = work.loc[work["day"].isin(first_days)].copy()
    return pd.Timestamp(anchor["timestamp"].min()), pd.Timestamp(anchor["timestamp"].max()), anchor


def _first_two_months_of_year(df_d1: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    ts = pd.to_datetime(df_d1["timestamp"], utc=True)
    work = df_d1.copy()
    work["month_num"] = ts.dt.month
    anchor = work.loc[work["month_num"].isin([1, 2])].copy()
    return pd.Timestamp(anchor["timestamp"].min()), pd.Timestamp(anchor["timestamp"].max()), anchor


def _ib_period_config(settings: dict, period_code: str) -> dict:
    ib_settings = settings.get("ib", {}) or {}
    period_settings = (ib_settings.get("periods") or {}).get(period_code, {}) or {}
    fallback_multipliers = [float(x) for x in ib_settings.get("multipliers", [1.0, 1.5, 2.0, 3.0])]
    multipliers = [float(x) for x in period_settings.get("multipliers", fallback_multipliers)]
    return {
        "enabled": bool(period_settings.get("enabled", True)),
        "include_low_high": bool(period_settings.get("include_low_high", True)),
        "include_mid": bool(period_settings.get("include_mid", True)),
        "multipliers": multipliers,
    }


def enabled_ib_periods(settings: dict) -> list[str]:
    return [period for period in ["W", "M", "Y"] if _ib_period_config(settings, period).get("enabled", True)]


def _multiplier_label(mult: float) -> str:
    value = float(mult) * 100.0
    if value.is_integer():
        return str(int(value))
    return str(round(value, 2)).replace(".0", "")


def _project_levels(period_code: str, ib_high: float, ib_low: float, period_config: dict) -> dict[str, float]:
    width = ib_high - ib_low
    midpoint = (ib_high + ib_low) / 2.0
    levels: dict[str, float] = {}

    if period_config.get("include_low_high", True):
        levels[f"{period_code} IB HIGH"] = ib_high
        levels[f"{period_code} IB LOW"] = ib_low

    if period_config.get("include_mid", True):
        levels[f"{period_code} IB MID"] = midpoint

    for mult in period_config.get("multipliers", []):
        tag = _multiplier_label(mult)
        levels[f"{period_code} IB {tag}"] = ib_high + width * float(mult)
        levels[f"{period_code} IB -{tag}"] = ib_low - width * float(mult)

    return levels


def calculate_active_ib(df_m30: pd.DataFrame, df_d1: pd.DataFrame, period_code: str, settings: dict) -> IBResult:
    period_config = _ib_period_config(settings, period_code)
    if not period_config.get("enabled", True):
        raise ValueError(f"IB period {period_code} is disabled in settings")

    if period_code == "W":
        key, week_df = _current_week_group(df_m30)
        anchor_start, anchor_end, anchor = _first_day_of_week(week_df)
    elif period_code == "M":
        key, month_df = _current_month_group(df_m30)
        anchor_start, anchor_end, anchor = _first_week_of_month(month_df)
    elif period_code == "Y":
        key, year_df = _current_year_group(df_d1)
        anchor_start, anchor_end, anchor = _first_two_months_of_year(year_df)
    else:
        raise ValueError(f"Unsupported period_code: {period_code}")

    if anchor.empty:
        raise ValueError(f"No anchor bars available for {period_code} IB")

    ib_high = float(anchor["high"].max())
    ib_low = float(anchor["low"].min())
    levels = _project_levels(period_code, ib_high, ib_low, period_config)

    return IBResult(
        period_code=period_code,
        anchor_id=key,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_range=ib_high - ib_low,
        levels=levels,
    )
