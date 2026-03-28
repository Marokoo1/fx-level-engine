from __future__ import annotations

import logging
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .html_report import save_html_report
from .config_loader import load_settings, load_symbols
from .fxcm_source import FXCMSource
from .ib_engine import calculate_active_ib, enabled_ib_periods
from .level_builder import build_ib_rows, build_poc_rows
from .matrix_builder import build_matrix_table, build_matrix_view_table
from .level_ranker import rank_levels
from .market_data import download_symbol_histories, get_last_price, load_symbol_history
from .profile_engine import calculate_active_poc
from .reporting import save_master_levels, save_table
from .report_hub import save_report_hub
from .scheduler import due_tables
from .summary_builder import build_summary_table
from .view_builder import build_view_table

logger = logging.getLogger(__name__)


TABLE_ENTRY_TF = {
    "intraday": "M1",
    "swing": "H1",
    "invest": "H4",
}

BASE_TABLES = ["intraday", "swing", "invest"]


def _calendar_runtime_config(settings: dict) -> dict:
    calendar_config = settings.get("economic_calendar", {})
    trading_restrictions = calendar_config.get("trading_restrictions", {})
    cache_ttl_hours = int(calendar_config.get("cache_ttl_hours", 4))
    sources = [str(source).lower() for source in (calendar_config.get("sources") or ["trading_economics"])]
    monitor_symbols = [str(symbol) for symbol in (calendar_config.get("monitor_symbols") or []) if str(symbol).strip()]
    te_env = calendar_config.get("trading_economics_api_key_env", "TRADING_ECONOMICS_API_KEY")
    myfxbook_env = calendar_config.get("myfxbook_api_token_env", "MYFXBOOK_API_TOKEN")

    return {
        "enabled": bool(calendar_config.get("enabled", False)),
        "trading_restrictions_enabled": bool(trading_restrictions.get("enabled", True)),
        "quiet_minutes": trading_restrictions.get("quiet_minutes", 30),
        "importance_threshold": trading_restrictions.get("importance_threshold", "medium"),
        "cache_ttl_hours": cache_ttl_hours,
        "sources": sources,
        "monitor_symbols": monitor_symbols,
        "trading_economics_api_key": os.getenv(te_env) if "trading_economics" in sources else None,
        "myfxbook_api_token": os.getenv(myfxbook_env) if "myfxbook" in sources else None,
    }


def _format_calendar_event(event) -> str:
    time_str = event.time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"{time_str} | {event.importance} | {event.country} | {event.event_name}"


def _build_calendar_status_table(monitor, symbols: list[str], hours_ahead: int = 48) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours_ahead)
    importance_levels = {"low": 1, "medium": 2, "high": 3}
    threshold = str(monitor.importance_threshold or "medium").lower()
    threshold_value = importance_levels.get(threshold, 2)

    rows: list[dict] = []

    for symbol in symbols:
        all_events = sorted(monitor.calendar.get_events_for_symbol(symbol), key=lambda event: event.time)
        future_events = [event for event in all_events if now <= event.time]
        future_threshold_events = [
            event
            for event in future_events
            if importance_levels.get(str(event.importance).lower(), 0) >= threshold_value
        ]
        upcoming_events = [event for event in future_events if event.time <= cutoff]
        threshold_upcoming = [
            event
            for event in upcoming_events
            if importance_levels.get(str(event.importance).lower(), 0) >= threshold_value
        ]
        active_events = [event for event in threshold_upcoming if event.is_active_now(monitor.quiet_minutes)]

        can_trade, reason = monitor.can_trade_symbol(symbol, min_importance=threshold)
        next_event = future_events[0] if future_events else None
        next_threshold_event = future_threshold_events[0] if future_threshold_events else None
        active_event = active_events[0] if active_events else None

        rows.append(
            {
                "asof_time": now.isoformat(),
                "symbol": symbol,
                "trade_status": "blocked" if active_events else "open",
                "blocked_now": bool(active_events),
                "block_reason": reason if not can_trade else "",
                "importance_threshold": threshold,
                "quiet_minutes": monitor.quiet_minutes,
                "active_event_count": len(active_events),
                "active_event_time": active_event.time.isoformat() if active_event else "",
                "active_event_importance": active_event.importance if active_event else "",
                "active_event_country": active_event.country if active_event else "",
                "active_event_name": active_event.event_name if active_event else "",
                "next_event_time": next_event.time.isoformat() if next_event else "",
                "next_event_importance": next_event.importance if next_event else "",
                "next_event_country": next_event.country if next_event else "",
                "next_event_name": next_event.event_name if next_event else "",
                "next_threshold_event_time": next_threshold_event.time.isoformat() if next_threshold_event else "",
                "next_threshold_event_importance": next_threshold_event.importance if next_threshold_event else "",
                "next_threshold_event_country": next_threshold_event.country if next_threshold_event else "",
                "next_threshold_event_name": next_threshold_event.event_name if next_threshold_event else "",
                "upcoming_event_count_48h": len(upcoming_events),
                "upcoming_threshold_event_count_48h": len(threshold_upcoming),
                "active_events": " || ".join(_format_calendar_event(event) for event in active_events[:5]),
                "upcoming_events_48h": " || ".join(_format_calendar_event(event) for event in upcoming_events[:8]),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["blocked_sort"] = out["blocked_now"].astype(str)
    out = out.sort_values(
        ["blocked_sort", "next_threshold_event_time", "next_event_time", "symbol"],
        ascending=[False, True, True, True],
        na_position="last",
    ).reset_index(drop=True)
    return out.drop(columns=["blocked_sort"])


def _build_calendar_events_table(monitor, symbols: list[str], hours_ahead: int = 48) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    importance_levels = {"low": 1, "medium": 2, "high": 3}
    threshold = str(monitor.importance_threshold or "medium").lower()
    threshold_value = importance_levels.get(threshold, 2)
    rows: list[dict] = []

    for event in monitor.calendar.get_upcoming_events(hours_ahead=hours_ahead):
        affected_symbols = [symbol for symbol in symbols if event.affects_symbol(symbol)]
        if not affected_symbols:
            continue

        event_importance = str(event.importance).lower()
        importance_value = importance_levels.get(event_importance, 0)
        threshold_match = importance_value >= threshold_value
        active_now = event.is_active_now(monitor.quiet_minutes)

        if threshold_match and active_now:
            event_status = "blocking"
        elif threshold_match:
            event_status = "watch"
        else:
            event_status = "info"

        rows.append(
            {
                "asof_time": now.isoformat(),
                "event_time": event.time.isoformat(),
                "event_status": event_status,
                "event_importance": event_importance,
                "country": event.country,
                "event_name": event.event_name,
                "affected_symbol_count": len(affected_symbols),
                "affected_symbols": ", ".join(affected_symbols),
                "threshold_match": threshold_match,
                "active_now": active_now,
                "quiet_window_start": (event.time - timedelta(minutes=monitor.quiet_minutes)).isoformat(),
                "quiet_window_end": (event.time + timedelta(minutes=monitor.quiet_minutes)).isoformat(),
                "forecast": event.forecast or "",
                "previous": event.previous or "",
                "actual": event.actual or "",
                "source": event.source,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["status_sort"] = out["event_status"].map({"blocking": 0, "watch": 1, "info": 2}).fillna(9)
    out["importance_sort"] = out["event_importance"].map({"high": 0, "medium": 1, "low": 2}).fillna(9)
    out = out.sort_values(
        ["status_sort", "event_time", "importance_sort", "country", "event_name"],
        ascending=[True, True, True, True, True],
    ).reset_index(drop=True)
    return out.drop(columns=["status_sort", "importance_sort"])


def _prepare_calendar_report_data(settings: dict, symbols: list[str], monitor=None):
    runtime = _calendar_runtime_config(settings)
    if not runtime["enabled"]:
        return None, [], pd.DataFrame(), pd.DataFrame()

    symbols_to_monitor = [symbol for symbol in symbols if symbol in runtime["monitor_symbols"]] if runtime["monitor_symbols"] else symbols
    if not symbols_to_monitor:
        symbols_to_monitor = symbols

    if monitor is None:
        from .market_monitor import get_monitor

        monitor = get_monitor(
            cache_ttl_hours=runtime["cache_ttl_hours"],
            quiet_minutes=runtime["quiet_minutes"],
            importance_threshold=runtime["importance_threshold"],
        )
        monitor.refresh_calendar(
            sources=runtime["sources"],
            trading_economics_api_key=runtime["trading_economics_api_key"],
            myfxbook_api_token=runtime["myfxbook_api_token"],
        )

    status_df = _build_calendar_status_table(monitor, symbols_to_monitor, hours_ahead=48)
    events_df = _build_calendar_events_table(monitor, symbols_to_monitor, hours_ahead=48)
    return monitor, symbols_to_monitor, status_df, events_df


def _merge_calendar_context(view_df: pd.DataFrame, calendar_status_df: pd.DataFrame, symbol_col: str = "symbol") -> pd.DataFrame:
    if view_df.empty or calendar_status_df.empty or symbol_col not in view_df.columns:
        return view_df

    status_cols = [
        "symbol",
        "trade_status",
        "block_reason",
        "next_threshold_event_time",
        "next_threshold_event_importance",
        "next_threshold_event_name",
        "next_event_time",
        "next_event_importance",
        "next_event_name",
        "upcoming_threshold_event_count_48h",
    ]
    merge_df = calendar_status_df[status_cols].copy()
    if symbol_col != "symbol":
        merge_df = merge_df.rename(columns={"symbol": symbol_col})

    return view_df.merge(merge_df, how="left", on=symbol_col)


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
    ib_periods = enabled_ib_periods(settings)

    for symbol in symbols:
        df_m30 = load_symbol_history(symbol, "m30", settings)
        df_d1 = load_symbol_history(symbol, "d1", settings)
        last_price = get_last_price(symbol, settings)

        pocs = {period: calculate_active_poc(df_m30, symbol, period, settings) for period in ["W", "M", "Y"]}
        ibs = {period: calculate_active_ib(df_m30, df_d1, period, settings) for period in ib_periods}

        post_poc = {period: _post_creation_slice(df_m30, pocs[period].end_time) for period in pocs}
        post_ib = {}
        for period, ib_result in ibs.items():
            post_ib[period] = _post_creation_slice(df_m30, pd.Timestamp(ib_result.anchor_end))

        for table_type in ["intraday", "swing", "invest"]:
            build_tf = settings["tables"][table_type]["build_timeframe"]
            entry_tf = TABLE_ENTRY_TF[table_type]
            for period in settings["tables"][table_type]["included_periods"]:
                all_rows.extend(
                    build_poc_rows(symbol, pocs[period], last_price, post_poc[period], table_type, build_tf, entry_tf)
                )
                if period in ibs:
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
    symbols: list[str] | None = None,
    monitor=None,
):
    settings = settings or load_settings()
    table_names = table_names or _exportable_table_names(settings)
    symbols = symbols or load_symbols()
    outputs = {}
    calendar_monitor, symbols_to_monitor, calendar_status_df, calendar_events_df = _prepare_calendar_report_data(
        settings,
        symbols,
        monitor=monitor,
    )

    tables_dir = settings["storage"]["tables_dir"]
    matrix_specs = settings.get("matrix_tables") or {}

    for table_name in table_names:
        if table_name in BASE_TABLES:
            raw_subset = df.loc[df["table_type"] == table_name].copy()
            filtered_subset = _filter_table(raw_subset, table_name)

            detail_subset = _prettify_detail_table(filtered_subset)
            summary_subset = build_summary_table(filtered_subset, table_name)
            view_subset = build_view_table(filtered_subset, table_name)
            view_subset = _merge_calendar_context(view_subset, calendar_status_df, symbol_col="symbol")
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

    if not calendar_status_df.empty:
        csv_path, parquet_path = save_table(calendar_status_df, tables_dir, "calendar_status")
        html_path = save_html_report(
            calendar_status_df,
            Path(tables_dir) / "calendar_status.html",
            "Economic calendar status",
        )
        outputs["calendar_status"] = {
            "csv": str(csv_path),
            "parquet": str(parquet_path),
            "html": str(html_path),
        }

    if not calendar_events_df.empty:
        csv_path, parquet_path = save_table(calendar_events_df, tables_dir, "calendar_events")
        html_path = save_html_report(
            calendar_events_df,
            Path(tables_dir) / "calendar_events.html",
            "Economic calendar events",
        )
        outputs["calendar_events"] = {
            "csv": str(csv_path),
            "parquet": str(parquet_path),
            "html": str(html_path),
        }

    tables_path = Path(tables_dir)
    project_root = tables_path.parent.parent
    save_report_hub(project_root)

    return outputs

def export_due_tables(
    df: pd.DataFrame,
    settings: dict | None = None,
    table_names: list[str] | None = None,
    symbols: list[str] | None = None,
    monitor=None,
):
    settings = settings or load_settings()
    table_names = table_names or due_tables()
    return export_tables(df, settings, table_names, symbols=symbols, monitor=monitor)


def run_daily(settings: dict | None = None, symbols: list[str] | None = None) -> dict:
    settings = settings or load_settings()
    requested_symbols = symbols or load_symbols()
    
    # Calendar status is collected for reporting, but we do not filter downloads/builds.
    _, monitor_info, monitor = _apply_market_monitor_filter(requested_symbols, settings)
    
    downloaded = run_download(settings, requested_symbols)
    df = build_all_levels(settings, requested_symbols)
    exported = export_due_tables(df, settings, symbols=requested_symbols, monitor=monitor)
    
    result = {
        "downloaded": downloaded,
        "rows": int(len(df)),
        "exported": exported,
    }
    
    # Add market monitor info to result
    if monitor_info:
        result["market_monitor"] = monitor_info
    
    return result


def run_all(settings: dict | None = None, symbols: list[str] | None = None) -> dict:
    settings = settings or load_settings()
    requested_symbols = symbols or load_symbols()
    
    # Calendar status is collected for reporting, but we do not filter downloads/builds.
    _, monitor_info, monitor = _apply_market_monitor_filter(requested_symbols, settings)
    
    downloaded = run_download(settings, requested_symbols)
    df = build_all_levels(settings, requested_symbols)
    exported = export_tables(df, settings, symbols=requested_symbols, monitor=monitor)
    
    result = {
        "downloaded": downloaded,
        "rows": int(len(df)),
        "exported": exported,
    }
    
    # Add market monitor info to result
    if monitor_info:
        result["market_monitor"] = monitor_info
    
    return result


def _apply_market_monitor_filter(symbols: list[str], settings: dict) -> tuple[list[str], dict, object | None]:
    """
    Collect economic-calendar tradeability status for a symbol list.
    
    Returns:
        (tradeable_symbols, monitor_info_dict, monitor)
    """
    runtime = _calendar_runtime_config(settings)
    
    # If disabled, return original symbols
    if not runtime["enabled"]:
        return symbols, {}, None
    if not runtime["trading_restrictions_enabled"]:
        return symbols, {"status": "disabled"}, None
    
    try:
        from .market_monitor import get_monitor
        
        monitor = get_monitor(
            cache_ttl_hours=runtime["cache_ttl_hours"],
            quiet_minutes=runtime["quiet_minutes"],
            importance_threshold=runtime["importance_threshold"],
        )
        
        # Refresh calendar
        success = monitor.refresh_calendar(
            sources=runtime["sources"],
            trading_economics_api_key=runtime["trading_economics_api_key"],
            myfxbook_api_token=runtime["myfxbook_api_token"],
        )
        if not success:
            logger.warning("Failed to refresh economic calendar")
            return symbols, {"status": "failed_to_refresh", "sources": runtime["sources"]}, monitor
        
        symbols_to_monitor = [symbol for symbol in symbols if symbol in runtime["monitor_symbols"]] if runtime["monitor_symbols"] else symbols

        # Filter symbols
        filtered_monitored_symbols = monitor.filter_tradeable_symbols(symbols_to_monitor)
        if runtime["monitor_symbols"]:
            monitored_set = set(symbols_to_monitor)
            filtered_symbols = [
                symbol
                for symbol in symbols
                if symbol not in monitored_set or symbol in filtered_monitored_symbols
            ]
        else:
            filtered_symbols = filtered_monitored_symbols
        
        # Get status
        status_dict = monitor.get_market_status(symbols_to_monitor)
        blocked_count = len(symbols_to_monitor) - len(filtered_monitored_symbols)
        
        monitor_info = {
            "status": "OK",
            "calendar_status": status_dict["calendar_status"],
            "sources": runtime["sources"],
            "original_symbols": len(symbols),
            "filtered_symbols": len(filtered_symbols),
            "monitored_symbols": len(symbols_to_monitor),
            "blocked_by_high_impact": status_dict.get("blocked_high", []),
            "blocked_by_medium_impact": status_dict.get("blocked_medium", []),
            "upcoming_events_24h": status_dict["upcoming_events_24h"],
            "cache_ttl_hours": runtime["cache_ttl_hours"],
        }
        
        # Log status
        logger.info(f"Market Monitor: {len(symbols)} symbols -> {len(filtered_symbols)} tradeable")
        if blocked_count > 0:
            logger.info(f"Blocked symbols: {blocked_count} due to economic events")
        monitor.print_status(symbols_to_monitor)
        
        return filtered_symbols, monitor_info, monitor
        
    except ImportError:
        logger.debug("market_monitor module not available")
        return symbols, {}, None
    except Exception as e:
        logger.error(f"Error applying market monitor filter: {e}")
        return symbols, {"status": "error", "error": str(e)}, None
