from __future__ import annotations

import pandas as pd
from pathlib import Path

from .html_report import save_html_report
from .config_loader import load_settings, load_symbols
from .fxcm_source import FXCMSource
from .ib_engine import calculate_active_ib
from .level_builder import build_ib_rows, build_poc_rows
from .matrix_builder import build_matrix_table, build_matrix_view_table
from .level_ranker import rank_levels
from .market_data import download_symbol_histories, get_last_price, load_symbol_history
from .profile_engine import calculate_active_poc
from .reporting import save_master_levels, save_table
from .scheduler import due_tables
from .summary_builder import build_summary_table
from .view_builder import build_view_table


TABLE_ENTRY_TF = {
    "intraday": "M1",
    "swing": "H1",
    "invest": "H4",
}

BASE_TABLES = ["intraday", "swing", "invest"]


def _matrix_table_names(settings: dict) -> list[str]:
    matrix_tables = settings.get("matrix_tables") or {}
    return [name for name, spec in matrix_tables.items() if spec.get("enabled", True)]


def _exportable_table_names(settings: dict) -> list[str]:
    return BASE_TABLES + _matrix_table_names(settings)


def _post_creation_slice(df: pd.DataFrame, created_after) -> pd.DataFrame:
    return df.loc[df["timestamp"] > created_after].copy()


def _filter_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    jpy_mask = out["symbol"].str.upper().str.contains("JPY", na=False)

    if table_name == "intraday":
        out = out[out["level_period"].isin(["W", "M"])].copy()

        out = out.loc[
            ((jpy_mask) & (out["distance_pips_abs"] <= 300))
            | ((~jpy_mask) & (out["distance_pips_abs"] <= 150))
        ].copy()

        long_part = (
            out[out["direction"] == "long"]
            .sort_values(["symbol", "distance_pips_abs", "rank"])
            .groupby("symbol", as_index=False, group_keys=False)
            .head(3)
        )
        short_part = (
            out[out["direction"] == "short"]
            .sort_values(["symbol", "distance_pips_abs", "rank"])
            .groupby("symbol", as_index=False, group_keys=False)
            .head(3)
        )
        out = pd.concat([long_part, short_part], ignore_index=True)

    elif table_name == "swing":
        out = out[out["level_period"].isin(["W", "M", "Y"])].copy()

        out = out.loc[
            ((jpy_mask) & (out["distance_pips_abs"] <= 800))
            | ((~jpy_mask) & (out["distance_pips_abs"] <= 300))
        ].copy()

    elif table_name == "invest":
        out = out[out["level_period"].isin(["M", "Y"])].copy()

    return out.sort_values(["symbol", "rank", "distance_pips_abs"]).reset_index(drop=True)


def _prettify_detail_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()

    status_order = {"fresh": 0, "tested": 1, "crossed": 2}
    family_order = {"POC": 0, "IB": 1}
    period_order = {"W": 0, "M": 1, "Y": 2}

    out["status_order"] = out["status"].map(status_order).fillna(9)
    out["family_order"] = out["level_family"].map(family_order).fillna(9)
    out["period_order"] = out["level_period"].map(period_order).fillna(9)

    out = out.sort_values(
        [
            "symbol",
            "status_order",
            "distance_pips_abs",
            "family_order",
            "period_order",
            "rank",
        ]
    ).reset_index(drop=True)

    for col in ["level_price", "zone_low", "zone_high", "last_price"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(5)

    for col in ["distance_pips", "distance_pips_abs"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    out["signal_side"] = out["direction"].map({"long": "support", "short": "resistance"})
    out["level_tag"] = out["level_period"].astype(str) + "_" + out["level_family"].astype(str)

    preferred_cols = [
        "asof_time",
        "symbol",
        "table_type",
        "signal_side",
        "level_tag",
        "level_name",
        "direction",
        "status",
        "level_price",
        "zone_low",
        "zone_high",
        "last_price",
        "distance_pips",
        "distance_pips_abs",
        "level_family",
        "level_period",
        "touch_count",
        "first_touch_time",
        "first_cross_time",
        "build_timeframe",
        "entry_timeframe",
        "notes",
        "rank",
        "strength_score",
        "fresh_score",
        "family_score",
        "period_score",
        "distance_score",
        "source_data",
    ]

    existing_cols = [c for c in preferred_cols if c in out.columns]
    return out[existing_cols].copy()


def run_download(settings: dict | None = None, symbols: list[str] | None = None) -> dict[str, dict[str, str]]:
    settings = settings or load_settings()
    symbols = symbols or load_symbols()
    saved: dict[str, dict[str, str]] = {}
    with FXCMSource.from_env(settings) as source:
        for symbol in symbols:
            outputs = download_symbol_histories(source, symbol, settings)
            saved[symbol] = {k: str(v) for k, v in outputs.items()}
    return saved


def build_all_levels(settings: dict | None = None, symbols: list[str] | None = None) -> pd.DataFrame:
    settings = settings or load_settings()
    symbols = symbols or load_symbols()
    all_rows: list[dict] = []

    for symbol in symbols:
        df_m30 = load_symbol_history(symbol, "m30", settings)
        df_d1 = load_symbol_history(symbol, "d1", settings)
        last_price = get_last_price(symbol, settings)

        pocs = {period: calculate_active_poc(df_m30, symbol, period, settings) for period in ["W", "M", "Y"]}
        ibs = {period: calculate_active_ib(df_m30, df_d1, period, settings) for period in ["W", "M", "Y"]}

        post_poc = {period: _post_creation_slice(df_m30, pocs[period].end_time) for period in pocs}
        post_ib = {
            "W": _post_creation_slice(df_m30, ibs["W"].anchor_end),
            "M": _post_creation_slice(df_m30, ibs["M"].anchor_end),
            "Y": _post_creation_slice(df_m30, pd.Timestamp(ibs["Y"].anchor_end)),
        }

        for table_type in ["intraday", "swing", "invest"]:
            build_tf = settings["tables"][table_type]["build_timeframe"]
            entry_tf = TABLE_ENTRY_TF[table_type]
            for period in settings["tables"][table_type]["included_periods"]:
                all_rows.extend(
                    build_poc_rows(symbol, pocs[period], last_price, post_poc[period], table_type, build_tf, entry_tf)
                )
                all_rows.extend(
                    build_ib_rows(symbol, ibs[period], last_price, post_ib[period], table_type, build_tf, entry_tf)
                )

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    return rank_levels(df)


def export_tables(
    df: pd.DataFrame,
    settings: dict | None = None,
    table_names: list[str] | None = None,
):
    settings = settings or load_settings()
    table_names = table_names or _exportable_table_names(settings)
    outputs = {}

    tables_dir = settings["storage"]["tables_dir"]
    matrix_specs = settings.get("matrix_tables") or {}

    for table_name in table_names:
        if table_name in BASE_TABLES:
            raw_subset = df.loc[df["table_type"] == table_name].copy()
            filtered_subset = _filter_table(raw_subset, table_name)

            detail_subset = _prettify_detail_table(filtered_subset)
            summary_subset = build_summary_table(filtered_subset, table_name)
            view_subset = build_view_table(filtered_subset, table_name)
            title = f"{table_name.capitalize()} view"
        elif table_name in matrix_specs:
            spec = matrix_specs[table_name]
            detail_subset = build_matrix_table(df, table_name, spec)
            view_subset = build_matrix_view_table(detail_subset, table_name)
            summary_subset = view_subset.copy()
            title = spec.get("title") or f"{table_name.replace('_', ' ').title()}"
        else:
            continue

        detail_csv, detail_parquet = save_table(detail_subset, tables_dir, f"{table_name}_signals")
        summary_csv, summary_parquet = save_table(summary_subset, tables_dir, f"{table_name}_summary")
        view_csv, view_parquet = save_table(view_subset, tables_dir, f"{table_name}_view")

        html_path = save_html_report(
            view_subset,
            Path(tables_dir) / f"{table_name}_view.html",
            title,
        )

        outputs[table_name] = {
            "signals": (str(detail_csv), str(detail_parquet)),
            "summary": (str(summary_csv), str(summary_parquet)),
            "view": (str(view_csv), str(view_parquet)),
            "html": str(html_path),
        }

    levels_dir = settings["storage"]["levels_dir"]
    save_master_levels(df, levels_dir)
    return outputs

def export_due_tables(
    df: pd.DataFrame,
    settings: dict | None = None,
    table_names: list[str] | None = None,
):
    settings = settings or load_settings()
    table_names = table_names or due_tables()
    return export_tables(df, settings, table_names)


def run_daily(settings: dict | None = None, symbols: list[str] | None = None) -> dict:
    settings = settings or load_settings()
    symbols = symbols or load_symbols()
    downloaded = run_download(settings, symbols)
    df = build_all_levels(settings, symbols)
    exported = export_due_tables(df, settings)
    return {
        "downloaded": downloaded,
        "rows": int(len(df)),
        "exported": exported,
    }


def run_all(settings: dict | None = None, symbols: list[str] | None = None) -> dict:
    settings = settings or load_settings()
    symbols = symbols or load_symbols()
    downloaded = run_download(settings, symbols)
    df = build_all_levels(settings, symbols)
    exported = export_tables(df, settings)
    return {
        "downloaded": downloaded,
        "rows": int(len(df)),
        "exported": exported,
    }
