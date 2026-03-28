from __future__ import annotations

import pandas as pd


def _pick_first(df: pd.DataFrame):
    if df.empty:
        return None
    return df.sort_values(["distance_pips_abs", "rank"]).iloc[0]


def _price_decimals(symbol: str) -> int:
    return 3 if "JPY" in str(symbol).upper() else 5


def _round_price(value, decimals: int):
    if value is None or pd.isna(value):
        return value
    try:
        return round(float(value), decimals)
    except Exception:
        return value


def _round_pips(value):
    if value is None or pd.isna(value):
        return value
    try:
        return round(float(value), 2)
    except Exception:
        return value


def _extract_level_fields(row, prefix: str) -> dict:
    if row is None:
        return {
            f"{prefix}_level_name": None,
            f"{prefix}_direction": None,
            f"{prefix}_level_family": None,
            f"{prefix}_level_period": None,
            f"{prefix}_level_price": None,
            f"{prefix}_distance_pips": None,
            f"{prefix}_status": None,
            f"{prefix}_notes": None,
        }

    symbol = str(row.get("symbol", ""))
    price_decimals = _price_decimals(symbol)

    return {
        f"{prefix}_level_name": row["level_name"],
        f"{prefix}_direction": row["direction"],
        f"{prefix}_level_family": row["level_family"],
        f"{prefix}_level_period": row["level_period"],
        f"{prefix}_level_price": _round_price(row["level_price"], price_decimals),
        f"{prefix}_distance_pips": _round_pips(row["distance_pips"]),
        f"{prefix}_status": row["status"],
        f"{prefix}_notes": row["notes"],
    }


def _compose_signal_summary(symbol: str, nearest_long, nearest_short, nearest_poc, nearest_ib) -> str:
    def _fmt(row, label: str) -> str:
        if row is None:
            return f"{label} -"
        price = _round_price(row["level_price"], _price_decimals(symbol))
        status = row.get("status")
        status_part = f" ({status})" if status else ""
        distance = _round_pips(row.get("distance_pips"))
        distance_part = f" [{distance:.2f} pips]" if distance is not None and not pd.isna(distance) else ""
        return f"{label} {row['level_name']}{status_part} @ {price}{distance_part}"

    return " | ".join([
        _fmt(nearest_long, "Support"),
        _fmt(nearest_short, "Resistance"),
        _fmt(nearest_poc, "POC"),
        _fmt(nearest_ib, "IB"),
    ])


def build_summary_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    rows = []

    for symbol, group in df.groupby("symbol", sort=True):
        group = group.sort_values(["distance_pips_abs", "rank"]).copy()
        last_price = float(group["last_price"].iloc[0])
        asof_time = group["asof_time"].iloc[0]

        nearest_long = _pick_first(group[group["direction"] == "long"])
        nearest_short = _pick_first(group[group["direction"] == "short"])

        nearest_fresh_long = _pick_first(
            group[(group["direction"] == "long") & (group["status"] == "fresh")]
        )
        nearest_fresh_short = _pick_first(
            group[(group["direction"] == "short") & (group["status"] == "fresh")]
        )

        nearest_poc = _pick_first(group[group["level_family"] == "POC"])
        nearest_ib = _pick_first(group[group["level_family"] == "IB"])

        row = {
            "asof_time": asof_time,
            "symbol": symbol,
            "table_type": table_name,
            "current_price": last_price,
            "last_price": last_price,
            "signal_summary": _compose_signal_summary(symbol, nearest_long, nearest_short, nearest_poc, nearest_ib),
            "total_levels": int(len(group)),
            "fresh_levels": int((group["status"] == "fresh").sum()),
            "tested_levels": int((group["status"] == "tested").sum()),
            "crossed_levels": int((group["status"] == "crossed").sum()),
        }

        row.update(_extract_level_fields(nearest_long, "nearest_long"))
        row.update(_extract_level_fields(nearest_short, "nearest_short"))
        row.update(_extract_level_fields(nearest_fresh_long, "nearest_fresh_long"))
        row.update(_extract_level_fields(nearest_fresh_short, "nearest_fresh_short"))
        row.update(_extract_level_fields(nearest_poc, "nearest_poc"))
        row.update(_extract_level_fields(nearest_ib, "nearest_ib"))

        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    price_cols = [
        "current_price",
        "last_price",
        "nearest_long_level_price",
        "nearest_short_level_price",
        "nearest_fresh_long_level_price",
        "nearest_fresh_short_level_price",
        "nearest_poc_level_price",
        "nearest_ib_level_price",
    ]
    pip_cols = [
        "nearest_long_distance_pips",
        "nearest_short_distance_pips",
        "nearest_fresh_long_distance_pips",
        "nearest_fresh_short_distance_pips",
        "nearest_poc_distance_pips",
        "nearest_ib_distance_pips",
    ]

    for idx, row in out.iterrows():
        symbol = str(row["symbol"])
        for col in price_cols:
            if col in out.columns:
                out.at[idx, col] = _round_price(row[col], _price_decimals(symbol))
        for col in pip_cols:
            if col in out.columns:
                out.at[idx, col] = _round_pips(row[col])

    preferred_cols = [
        "asof_time",
        "symbol",
        "table_type",
        "current_price",
        "last_price",
        "nearest_ib_level_name",
        "nearest_ib_level_price",
        "nearest_ib_distance_pips",
        "nearest_ib_status",
        "nearest_poc_level_name",
        "nearest_poc_level_price",
        "nearest_poc_distance_pips",
        "nearest_poc_status",
        "nearest_long_level_name",
        "nearest_long_level_price",
        "nearest_long_distance_pips",
        "nearest_long_status",
        "nearest_short_level_name",
        "nearest_short_level_price",
        "nearest_short_distance_pips",
        "nearest_short_status",
        "nearest_fresh_long_level_name",
        "nearest_fresh_long_level_price",
        "nearest_fresh_long_distance_pips",
        "nearest_fresh_short_level_name",
        "nearest_fresh_short_level_price",
        "nearest_fresh_short_distance_pips",
        "fresh_levels",
        "tested_levels",
        "crossed_levels",
        "total_levels",
        "signal_summary",
    ]

    existing_cols = [c for c in preferred_cols if c in out.columns]
    return out[existing_cols].sort_values("symbol").reset_index(drop=True)
