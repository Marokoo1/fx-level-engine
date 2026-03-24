from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config_loader import load_settings, load_symbols
from .fxcm_source import FXCMSource
from .ib_engine import calculate_active_ib
from .level_builder import build_ib_rows, build_poc_rows
from .level_ranker import rank_levels
from .market_data import download_symbol_histories, get_last_price, load_symbol_history
from .profile_engine import calculate_active_poc
from .reporting import save_master_levels, save_table
from .scheduler import due_tables


TABLE_ENTRY_TF = {
    "intraday": "M1",
    "swing": "H1",
    "invest": "H4",
}


def _post_creation_slice(df: pd.DataFrame, created_after) -> pd.DataFrame:
    return df.loc[df["timestamp"] > created_after].copy()


def _is_jpy_symbol(symbol: str) -> bool:
    return "JPY" in symbol.upper()


def _filter_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()

    jpy_mask = out["symbol"].str.upper().str.contains("JPY", na=False)

    if table_name == "intraday":
        # Jen weekly + monthly levely
        out = out[out["level_period"].isin(["W", "M"])].copy()

        # Distance filtry
        out = out.loc[
            ((jpy_mask) & (out["distance_pips_abs"] <= 300))
            | ((~jpy_mask) & (out["distance_pips_abs"] <= 150))
        ].copy()

        # Max 3 long pod cenou + max 3 short nad cenou na symbol
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
        # Weekly + monthly + yearly jen když je rozumně blízko
        out = out[out["level_period"].isin(["W", "M", "Y"])].copy()

        out = out.loc[
            ((jpy_mask) & (out["distance_pips_abs"] <= 800))
            | ((~jpy_mask) & (out["distance_pips_abs"] <= 300))
        ].copy()

    elif table_name == "invest":
        # Invest = monthly + yearly major map
        out = out[out["level_period"].isin(["M", "Y"])].copy()

    return out.sort_values(["symbol", "rank", "distance_pips_abs"]).reset_index(drop=True)


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
) -> dict[str, tuple[str, str]]:
    settings = settings or load_settings()
    table_names = table_names or ["intraday", "swing", "invest"]
    outputs: dict[str, tuple[str, str]] = {}

    tables_dir = settings["storage"]["tables_dir"]
    for table_name in table_names:
        subset = df.loc[df["table_type"] == table_name].copy()
        subset = _filter_table(subset, table_name)
        csv_path, parquet_path = save_table(subset, tables_dir, f"{table_name}_signals")
        outputs[table_name] = (str(csv_path), str(parquet_path))

    levels_dir = settings["storage"]["levels_dir"]
    save_master_levels(df, levels_dir)
    return outputs


def export_due_tables(
    df: pd.DataFrame,
    settings: dict | None = None,
    table_names: list[str] | None = None,
) -> dict[str, tuple[str, str]]:
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
    exported = export_tables(df, settings, ["intraday", "swing", "invest"])
    return {
        "downloaded": downloaded,
        "rows": int(len(df)),
        "exported": exported,
    }