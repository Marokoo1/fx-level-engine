from __future__ import annotations

import pandas as pd

from .utils import pip_size


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


def _config_number(value, symbol: str) -> float | None:
    if value is None:
        return None

    if isinstance(value, dict):
        symbol_upper = str(symbol).upper()
        if "JPY" in symbol_upper and "JPY" in value:
            try:
                return float(value["JPY"])
            except Exception:
                return None
        if "default" in value:
            try:
                return float(value["default"])
            except Exception:
                return None

    try:
        return float(value)
    except Exception:
        return None


def _slot_prefix(side: str, index: int) -> str:
    return f"res{index}" if side == "short" else f"sup{index}"


def _empty_slot(prefix: str) -> dict:
    return {
        f"{prefix}_name": None,
        f"{prefix}_price": None,
        f"{prefix}_pips": None,
        f"{prefix}_family": None,
        f"{prefix}_period": None,
        f"{prefix}_status": None,
        f"{prefix}_conf": None,
        f"{prefix}_conf_name": None,
        f"{prefix}_conf_pips": None,
    }


def _slot_summary(prefix: str, row, symbol: str, conf: dict | None) -> str:
    label = prefix.replace("res", "Res").replace("sup", "Sup")
    if row is None:
        return f"{label} -"

    price = _round_price(row["level_price"], _price_decimals(symbol))
    distance = _round_pips(row.get("distance_pips"))
    status = row.get("status")
    status_part = f" ({status})" if status else ""
    distance_part = f" [{distance:.2f} pips]" if distance is not None and not pd.isna(distance) else ""
    conf_part = f" +{conf['conf']}" if conf and conf.get("conf") else ""
    return f"{label} {row['level_name']}{status_part} @ {price}{distance_part}{conf_part}"


def _matches_confluence(row, other_group: pd.DataFrame, symbol: str, tolerance_pips: float | None) -> dict | None:
    if row is None or other_group.empty or tolerance_pips is None or tolerance_pips <= 0:
        return None

    delta = (other_group["level_price"].astype(float) - float(row["level_price"])) / pip_size(symbol)
    matched = other_group.loc[delta.abs() <= tolerance_pips].copy()
    if matched.empty:
        return None

    matched["conf_distance_pips"] = delta.loc[matched.index].abs()
    best = matched.sort_values(["conf_distance_pips", "distance_pips_abs", "rank"]).iloc[0]
    return {
        "conf": str(best["level_family"]),
        "conf_name": str(best["level_name"]),
        "conf_pips": _round_pips((float(best["level_price"]) - float(row["level_price"])) / pip_size(symbol)),
    }


def _pick_side_levels(
    group: pd.DataFrame,
    side: str,
    max_levels: int,
    symbol: str,
    min_separation_pips: float | None = None,
) -> list[pd.Series]:
    side_group = group[group["direction"] == side].copy()
    if side_group.empty:
        return []

    side_group = side_group.sort_values(["distance_pips_abs", "rank"]).reset_index(drop=True)
    selected: list[pd.Series] = []
    min_separation = float(min_separation_pips or 0.0)

    for _, row in side_group.iterrows():
        if min_separation > 0 and selected:
            too_close = False
            for picked in selected:
                delta_pips = abs(float(row["level_price"]) - float(picked["level_price"])) / pip_size(symbol)
                if delta_pips < min_separation:
                    too_close = True
                    break
            if too_close:
                continue

        selected.append(row)
        if len(selected) >= max_levels:
            break

    return selected


def build_matrix_table(df: pd.DataFrame, table_name: str, spec: dict) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    source_table_type = str(spec.get("source_table_type", "")).strip() or None
    source_families = [str(x) for x in spec.get("source_families", []) if str(x).strip()]
    source_periods = [str(x) for x in spec.get("source_periods", []) if str(x).strip()]
    fresh_only = bool(spec.get("fresh_only", True))
    max_levels_per_side = int(spec.get("max_levels_per_side", 2))
    max_distance_cfg = spec.get("max_distance_pips")
    min_separation_cfg = spec.get("min_side_separation_pips")
    confluence_cfg = spec.get("confluence", {}) or {}
    confluence_family = str(confluence_cfg.get("family", "")).strip() or None
    confluence_enabled = bool(confluence_cfg.get("enabled", bool(confluence_family)))
    confluence_tolerance_cfg = confluence_cfg.get("tolerance_pips")

    scope = df.copy()

    if source_table_type and "table_type" in scope.columns:
        scope = scope.loc[scope["table_type"] == source_table_type].copy()

    if source_periods and "level_period" in scope.columns:
        scope = scope.loc[scope["level_period"].isin(source_periods)].copy()

    if scope.empty:
        return pd.DataFrame()

    source_candidates = scope.copy()
    if fresh_only and "status" in source_candidates.columns:
        source_candidates = source_candidates.loc[source_candidates["status"] == "fresh"].copy()
    if source_families:
        source_candidates = source_candidates.loc[source_candidates["level_family"].isin(source_families)].copy()

    confluence_candidates = scope.copy()
    if fresh_only and "status" in confluence_candidates.columns:
        confluence_candidates = confluence_candidates.loc[confluence_candidates["status"] == "fresh"].copy()
    if confluence_enabled and confluence_family:
        confluence_candidates = confluence_candidates.loc[confluence_candidates["level_family"] == confluence_family].copy()
    else:
        confluence_candidates = pd.DataFrame(columns=scope.columns)

    rows: list[dict] = []

    for symbol, symbol_group in scope.groupby("symbol", sort=True):
        symbol_group = symbol_group.sort_values(["distance_pips_abs", "rank"]).copy()
        source_group = source_candidates.loc[source_candidates["symbol"] == symbol].copy()
        confluence_group = confluence_candidates.loc[confluence_candidates["symbol"] == symbol].copy()

        max_distance_pips = _config_number(max_distance_cfg, symbol)
        if max_distance_pips is not None:
            source_group = source_group.loc[source_group["distance_pips_abs"] <= max_distance_pips].copy()
            confluence_group = confluence_group.loc[confluence_group["distance_pips_abs"] <= max_distance_pips].copy()

        min_separation_pips = _config_number(min_separation_cfg, symbol)
        tolerance_pips = _config_number(confluence_tolerance_cfg, symbol)

        current_price = float(symbol_group["last_price"].iloc[0])
        asof_time = symbol_group["asof_time"].iloc[0]
        decimals = _price_decimals(symbol)

        res_selected = _pick_side_levels(source_group, "short", max_levels_per_side, symbol, min_separation_pips)
        sup_selected = _pick_side_levels(source_group, "long", max_levels_per_side, symbol, min_separation_pips)

        row = {
            "asof_time": asof_time,
            "table_type": table_name,
            "source_table_type": source_table_type,
            "instrument": symbol,
            "current_price": _round_price(current_price, decimals),
            "last_price": _round_price(current_price, decimals),
            "source_levels": int(len(source_group)),
            "source_resistances": int(len(source_group.loc[source_group["direction"] == "short"])),
            "source_supports": int(len(source_group.loc[source_group["direction"] == "long"])),
            "selected_resistances": int(len(res_selected)),
            "selected_supports": int(len(sup_selected)),
            "selected_levels": int(len(res_selected) + len(sup_selected)),
            "confluence_candidates": int(len(confluence_group)),
            "confluence_hits": 0,
        }

        for index in range(1, max_levels_per_side + 1):
            row.update(_empty_slot(_slot_prefix("short", index)))
            row.update(_empty_slot(_slot_prefix("long", index)))

        summary_parts = []

        for index, selected_row in enumerate(res_selected, start=1):
            prefix = _slot_prefix("short", index)
            conf = _matches_confluence(selected_row, confluence_group, symbol, tolerance_pips) if confluence_enabled else None
            if conf:
                row["confluence_hits"] += 1
            row.update(_empty_slot(prefix))
            row.update(
                {
                    f"{prefix}_name": selected_row["level_name"],
                    f"{prefix}_price": _round_price(selected_row["level_price"], decimals),
                    f"{prefix}_pips": _round_pips(selected_row["distance_pips"]),
                    f"{prefix}_family": selected_row["level_family"],
                    f"{prefix}_period": selected_row["level_period"],
                    f"{prefix}_status": selected_row["status"],
                    f"{prefix}_conf": conf["conf"] if conf else None,
                    f"{prefix}_conf_name": conf["conf_name"] if conf else None,
                    f"{prefix}_conf_pips": conf["conf_pips"] if conf else None,
                }
            )
            summary_parts.append(_slot_summary(prefix, selected_row, symbol, conf))

        for index, selected_row in enumerate(sup_selected, start=1):
            prefix = _slot_prefix("long", index)
            conf = _matches_confluence(selected_row, confluence_group, symbol, tolerance_pips) if confluence_enabled else None
            if conf:
                row["confluence_hits"] += 1
            row.update(_empty_slot(prefix))
            row.update(
                {
                    f"{prefix}_name": selected_row["level_name"],
                    f"{prefix}_price": _round_price(selected_row["level_price"], decimals),
                    f"{prefix}_pips": _round_pips(selected_row["distance_pips"]),
                    f"{prefix}_family": selected_row["level_family"],
                    f"{prefix}_period": selected_row["level_period"],
                    f"{prefix}_status": selected_row["status"],
                    f"{prefix}_conf": conf["conf"] if conf else None,
                    f"{prefix}_conf_name": conf["conf_name"] if conf else None,
                    f"{prefix}_conf_pips": conf["conf_pips"] if conf else None,
                }
            )
            summary_parts.append(_slot_summary(prefix, selected_row, symbol, conf))

        row["signal_summary"] = " | ".join(summary_parts) if summary_parts else ""
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    price_cols = [
        "current_price",
        "last_price",
        "res1_price",
        "res2_price",
        "sup1_price",
        "sup2_price",
    ]
    pip_cols = [
        "res1_pips",
        "res2_pips",
        "sup1_pips",
        "sup2_pips",
        "res1_conf_pips",
        "res2_conf_pips",
        "sup1_conf_pips",
        "sup2_conf_pips",
    ]

    for idx, row in out.iterrows():
        symbol = str(row["instrument"])
        decimals = _price_decimals(symbol)
        for col in price_cols:
            if col in out.columns:
                out.at[idx, col] = _round_price(row[col], decimals)
        for col in pip_cols:
            if col in out.columns:
                out.at[idx, col] = _round_pips(row[col])

    preferred_cols = [
        "asof_time",
        "table_type",
        "source_table_type",
        "instrument",
        "current_price",
        "last_price",
        "res1_name",
        "res1_price",
        "res1_pips",
        "res1_family",
        "res1_period",
        "res1_status",
        "res1_conf",
        "res1_conf_name",
        "res1_conf_pips",
        "res2_name",
        "res2_price",
        "res2_pips",
        "res2_family",
        "res2_period",
        "res2_status",
        "res2_conf",
        "res2_conf_name",
        "res2_conf_pips",
        "sup1_name",
        "sup1_price",
        "sup1_pips",
        "sup1_family",
        "sup1_period",
        "sup1_status",
        "sup1_conf",
        "sup1_conf_name",
        "sup1_conf_pips",
        "sup2_name",
        "sup2_price",
        "sup2_pips",
        "sup2_family",
        "sup2_period",
        "sup2_status",
        "sup2_conf",
        "sup2_conf_name",
        "sup2_conf_pips",
        "source_levels",
        "source_resistances",
        "source_supports",
        "selected_resistances",
        "selected_supports",
        "selected_levels",
        "confluence_candidates",
        "confluence_hits",
        "signal_summary",
    ]

    existing_cols = [col for col in preferred_cols if col in out.columns]
    return out[existing_cols].sort_values("instrument").reset_index(drop=True)


def build_matrix_view_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    preferred_cols = [
        "asof_time",
        "table_type",
        "instrument",
        "current_price",
        "res1_price",
        "res1_pips",
        "res1_conf",
        "res2_price",
        "res2_pips",
        "res2_conf",
        "sup1_price",
        "sup1_pips",
        "sup1_conf",
        "sup2_price",
        "sup2_pips",
        "sup2_conf",
        "selected_levels",
        "confluence_hits",
        "signal_summary",
    ]

    existing_cols = [col for col in preferred_cols if col in df.columns]
    if not existing_cols:
        return df.copy()

    return df[existing_cols].sort_values("instrument").reset_index(drop=True)
