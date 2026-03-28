from __future__ import annotations

import pandas as pd


def _pick_first(df: pd.DataFrame):
    if df.empty:
        return None
    return df.sort_values(["status_order", "distance_pips_abs", "rank"]).iloc[0]


def _price_decimals(symbol: str) -> int:
    return 3 if "JPY" in str(symbol).upper() else 5


def _round_price(value, decimals: int):
    if value is None or pd.isna(value):
        return value
    try:
        return round(float(value), decimals)
    except Exception:
        return value


def _cell(row, col, default=None):
    if row is None:
        return default
    return row.get(col, default)


def _compose_signal_summary(symbol: str, nearest_support, nearest_resistance, nearest_poc, nearest_ib) -> str:
    def _fmt(row, label: str) -> str:
        if row is None:
            return f"{label} -"
        price = _round_price(_cell(row, "level_price"), symbol)
        status = _cell(row, "status")
        status_part = f" ({status})" if status else ""
        distance = _cell(row, "distance_pips")
        distance_part = f" [{float(distance):.2f} pips]" if distance is not None and not pd.isna(distance) else ""
        return f"{label} {_cell(row, 'level_name')}{status_part} @ {price}{distance_part}"

    return " | ".join([
        _fmt(nearest_support, "Support"),
        _fmt(nearest_resistance, "Resistance"),
        _fmt(nearest_poc, "POC"),
        _fmt(nearest_ib, "IB"),
    ])


def build_view_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    status_order = {"fresh": 0, "tested": 1, "crossed": 2}
    work["status_order"] = work["status"].map(status_order).fillna(9)

    rows = []

    for symbol, group in work.groupby("symbol", sort=True):
        group = group.copy()
        last_price = float(group["last_price"].iloc[0])
        asof_time = group["asof_time"].iloc[0]
        price_decimals = _price_decimals(symbol)

        nearest_support = _pick_first(group[group["direction"] == "long"])
        nearest_resistance = _pick_first(group[group["direction"] == "short"])
        nearest_fresh_support = _pick_first(
            group[(group["direction"] == "long") & (group["status"] == "fresh")]
        )
        nearest_fresh_resistance = _pick_first(
            group[(group["direction"] == "short") & (group["status"] == "fresh")]
        )
        nearest_poc = _pick_first(group[group["level_family"] == "POC"])
        nearest_ib = _pick_first(group[group["level_family"] == "IB"])

        row = {
            "asof_time": asof_time,
            "table_type": table_name,
            "symbol": symbol,
            "current_price": _round_price(last_price, symbol),
            "last_price": _round_price(last_price, symbol),
            "signal_summary": _compose_signal_summary(symbol, nearest_support, nearest_resistance, nearest_poc, nearest_ib),

            "nearest_support": _cell(nearest_support, "level_name"),
            "nearest_support_price": _round_price(_cell(nearest_support, "level_price"), symbol),
            "nearest_support_pips": _cell(nearest_support, "distance_pips"),
            "nearest_support_status": _cell(nearest_support, "status"),

            "nearest_resistance": _cell(nearest_resistance, "level_name"),
            "nearest_resistance_price": _round_price(_cell(nearest_resistance, "level_price"), symbol),
            "nearest_resistance_pips": _cell(nearest_resistance, "distance_pips"),
            "nearest_resistance_status": _cell(nearest_resistance, "status"),

            "nearest_fresh_support": _cell(nearest_fresh_support, "level_name"),
            "nearest_fresh_support_price": _round_price(_cell(nearest_fresh_support, "level_price"), symbol),
            "nearest_fresh_support_pips": _cell(nearest_fresh_support, "distance_pips"),

            "nearest_fresh_resistance": _cell(nearest_fresh_resistance, "level_name"),
            "nearest_fresh_resistance_price": _round_price(_cell(nearest_fresh_resistance, "level_price"), symbol),
            "nearest_fresh_resistance_pips": _cell(nearest_fresh_resistance, "distance_pips"),

            "nearest_poc": _cell(nearest_poc, "level_name"),
            "nearest_poc_price": _round_price(_cell(nearest_poc, "level_price"), symbol),
            "nearest_poc_pips": _cell(nearest_poc, "distance_pips"),
            "nearest_poc_status": _cell(nearest_poc, "status"),

            "nearest_ib": _cell(nearest_ib, "level_name"),
            "nearest_ib_price": _round_price(_cell(nearest_ib, "level_price"), symbol),
            "nearest_ib_pips": _cell(nearest_ib, "distance_pips"),
            "nearest_ib_status": _cell(nearest_ib, "status"),

            "fresh_levels": int((group["status"] == "fresh").sum()),
            "tested_levels": int((group["status"] == "tested").sum()),
            "crossed_levels": int((group["status"] == "crossed").sum()),
            "total_levels": int(len(group)),
        }

        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    pip_cols = [
        "nearest_support_pips",
        "nearest_resistance_pips",
        "nearest_fresh_support_pips",
        "nearest_fresh_resistance_pips",
        "nearest_poc_pips",
        "nearest_ib_pips",
    ]
    for col in pip_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    preferred_cols = [
        "asof_time",
        "table_type",
        "symbol",
        "current_price",
        "nearest_ib",
        "nearest_ib_price",
        "nearest_ib_pips",
        "nearest_ib_status",
        "nearest_poc",
        "nearest_poc_price",
        "nearest_poc_pips",
        "nearest_poc_status",
        "nearest_support",
        "nearest_support_price",
        "nearest_support_pips",
        "nearest_support_status",
        "nearest_resistance",
        "nearest_resistance_price",
        "nearest_resistance_pips",
        "nearest_resistance_status",
        "signal_summary",
        "last_price",
        "nearest_fresh_support",
        "nearest_fresh_support_price",
        "nearest_fresh_support_pips",
        "nearest_fresh_resistance",
        "nearest_fresh_resistance_price",
        "nearest_fresh_resistance_pips",
        "fresh_levels",
        "tested_levels",
        "crossed_levels",
        "total_levels",
    ]

    return out[preferred_cols].sort_values("symbol").reset_index(drop=True)
