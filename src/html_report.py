from __future__ import annotations

from pathlib import Path
import html

import pandas as pd


def _is_numeric_series(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _format_timestamp(value) -> str:
    if pd.isna(value):
        return ""
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return html.escape(str(value))
    return ts.strftime("%Y-%m-%d %H:%M UTC")


def _price_decimals(symbol: str) -> int:
    return 3 if "JPY" in str(symbol).upper() else 5


def _row_symbol(row: pd.Series | dict) -> str | None:
    if row is None:
        return None
    if hasattr(row, "get"):
        symbol = row.get("symbol")
        if symbol is None:
            symbol = row.get("instrument")
        if symbol is not None:
            return str(symbol)
    return None


def _is_matrix_view(df: pd.DataFrame) -> bool:
    return any(
        col in df.columns
        for col in ["res1_price", "sup1_price", "selected_levels", "confluence_hits", "above_levels", "below_levels"]
    )


def _is_calendar_status_view(df: pd.DataFrame) -> bool:
    return "trade_status" in df.columns and "next_event_name" in df.columns


def _is_calendar_events_view(df: pd.DataFrame) -> bool:
    return "event_status" in df.columns and "event_time" in df.columns


def _select_display_columns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return list(df.columns)

    if _is_calendar_status_view(df):
        focused = [
            "asof_time",
            "symbol",
            "trade_status",
            "block_reason",
            "active_event_time",
            "active_event_importance",
            "active_event_country",
            "active_event_name",
            "next_threshold_event_time",
            "next_threshold_event_importance",
            "next_threshold_event_country",
            "next_threshold_event_name",
            "next_event_time",
            "next_event_importance",
            "next_event_country",
            "next_event_name",
            "upcoming_threshold_event_count_48h",
            "upcoming_event_count_48h",
            "upcoming_events_48h",
        ]
        return [col for col in focused if col in df.columns]

    if _is_calendar_events_view(df):
        focused = [
            "event_time",
            "event_status",
            "event_importance",
            "country",
            "event_name",
            "affected_symbol_count",
            "affected_symbols",
            "quiet_window_start",
            "quiet_window_end",
            "forecast",
            "previous",
            "actual",
            "source",
        ]
        return [col for col in focused if col in df.columns]

    if _is_matrix_view(df):
        focused = [
            "instrument",
            "current_price",
            "above_levels",
            "below_levels",
            "selected_levels",
            "confluence_hits",
        ]
        return [col for col in focused if col in df.columns]

    focused = [
        "asof_time",
        "symbol",
        "trade_status",
        "next_threshold_event_time",
        "next_threshold_event_importance",
        "next_threshold_event_name",
        "next_event_time",
        "next_event_importance",
        "next_event_name",
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
        "fresh_levels",
        "tested_levels",
        "crossed_levels",
        "total_levels",
    ]

    if "current_price" in df.columns:
        return [col for col in focused if col in df.columns]

    if "signal_summary" in df.columns:
        fallback = [
            "asof_time",
            "symbol",
            "signal_summary",
            "last_price",
            "fresh_levels",
            "tested_levels",
            "crossed_levels",
            "total_levels",
        ]
        return [col for col in fallback if col in df.columns]

    return list(df.columns)


def _metric_value(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return 0
    series = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return int(series.sum())


def _build_metrics(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    rows = int(len(df))
    symbol_col = "symbol" if "symbol" in df.columns else "instrument" if "instrument" in df.columns else None
    symbols = int(df[symbol_col].nunique()) if symbol_col else 0

    updated = ""
    if "asof_time" in df.columns and not df.empty:
        updated = _format_timestamp(df["asof_time"].max())

    if _is_calendar_status_view(df):
        blocked = int(df["trade_status"].astype(str).str.lower().eq("blocked").sum()) if "trade_status" in df.columns else 0
        watch = 0
        if "upcoming_threshold_event_count_48h" in df.columns:
            watch = int((pd.to_numeric(df["upcoming_threshold_event_count_48h"], errors="coerce").fillna(0) > 0).sum())
        pair_events = 0
        if "upcoming_event_count_48h" in df.columns:
            pair_events = int(pd.to_numeric(df["upcoming_event_count_48h"], errors="coerce").fillna(0).sum())
        next_due = ""
        for col in ["active_event_time", "next_threshold_event_time", "next_event_time"]:
            if col in df.columns:
                series = pd.to_datetime(df[col], utc=True, errors="coerce").dropna()
                if not series.empty:
                    next_due = _format_timestamp(series.min())
                    break
        return [
            ("Pairs", f"{symbols}", "monitored instruments"),
            ("Blocked", f"{blocked}", "blocked right now"),
            ("Watchlist", f"{watch}", "pairs with threshold events ahead"),
            ("Pair-events", f"{pair_events}", "pair/event links in 48h"),
            ("Next due", next_due or "n/a", "nearest relevant calendar time"),
            ("Updated", updated or "n/a", "latest snapshot"),
        ]

    if _is_calendar_events_view(df):
        high = int(df["event_importance"].astype(str).str.lower().eq("high").sum()) if "event_importance" in df.columns else 0
        threshold_events = int(df["event_status"].astype(str).str.lower().isin(["blocking", "watch"]).sum()) if "event_status" in df.columns else 0
        blocking = int(df["event_status"].astype(str).str.lower().eq("blocking").sum()) if "event_status" in df.columns else 0
        affected_pairs = 0
        if "affected_symbol_count" in df.columns:
            affected_pairs = int(pd.to_numeric(df["affected_symbol_count"], errors="coerce").fillna(0).sum())
        next_due = ""
        if "event_time" in df.columns:
            series = pd.to_datetime(df["event_time"], utc=True, errors="coerce").dropna()
            if not series.empty:
                next_due = _format_timestamp(series.min())
        return [
            ("Events", f"{rows}", "upcoming calendar rows"),
            ("High", f"{high}", "high-impact events"),
            ("Watch", f"{threshold_events}", "medium/high threshold matches"),
            ("Blocking", f"{blocking}", "blocking now"),
            ("Affected", f"{affected_pairs}", "symbol-event links"),
            ("Next due", next_due or "n/a", "nearest event time"),
        ]

    if _is_matrix_view(df):
        selected = _metric_value(df, "selected_levels")
        confluences = _metric_value(df, "confluence_hits")
        return [
            ("Instruments", f"{symbols}", "unique instruments"),
            ("Rows", f"{rows}", "rows in this view"),
            ("Selected", f"{selected}", "filled support/resistance slots"),
            ("Confluence", f"{confluences}", "badge hits"),
            ("Updated", updated or "n/a", "latest snapshot"),
        ]

    fresh = _metric_value(df, "fresh_levels")
    tested = _metric_value(df, "tested_levels")
    crossed = _metric_value(df, "crossed_levels")

    return [
        ("Symbols", f"{symbols}", "unique instruments"),
        ("Rows", f"{rows}", "rows in this view"),
        ("Fresh", f"{fresh}", "fresh opportunities"),
        ("Tested", f"{tested}", "already tested"),
        ("Crossed", f"{crossed}", "crossed or invalidated"),
        ("Updated", updated or "n/a", "latest snapshot"),
    ]


def _status_badge(value) -> str:
    text = "" if pd.isna(value) else str(value)
    token = text.lower()
    if token in {"fresh", "tested", "crossed", "open", "blocked", "blocking", "watch", "info", "low", "medium", "high"}:
        klass = "blocked" if token == "blocking" else token
        return f'<span class="badge {html.escape(klass)}">{html.escape(text)}</span>'
    if token in {"ib", "poc", "poc+ib", "+ib", "+poc"}:
        return f'<span class="badge marker">{html.escape(text)}</span>'
    return html.escape(text)


def _format_cell(value, col: str, symbol: str | None = None) -> str:
    if pd.isna(value):
        return ""

    if col == "asof_time" or col.endswith("_time") or col == "event_time":
        return _format_timestamp(value)

    if col.endswith("_status") or col == "status" or col in {"trade_status", "event_status"} or col.endswith("_conf") or col.endswith("_marker") or col.endswith("_importance"):
        return _status_badge(value)

    if col in {"signal_summary", "block_reason", "active_events", "upcoming_events_48h", "affected_symbols", "above_levels", "below_levels"}:
        return html.escape(str(value)).replace("\n", "<br>")

    if col in {"symbol", "instrument", "table_type", "source_table_type"} or col.endswith("_name") or col in {"direction", "level_family", "level_period"}:
        return html.escape(str(value))

    if col.endswith("_price") or col in {"current_price", "last_price", "level_price", "zone_low", "zone_high"}:
        decimals = _price_decimals(symbol or "")
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return html.escape(str(value))

    if col.endswith("_pips") or col.endswith("_score") or col.endswith("_count") or col in {"rank", "fresh_levels", "tested_levels", "crossed_levels", "total_levels", "touch_count"}:
        try:
            number = float(value)
            if number.is_integer():
                return str(int(number))
            return f"{number:.2f}"
        except Exception:
            return html.escape(str(value))

    return html.escape(str(value))


def _column_type(df: pd.DataFrame, col: str) -> str:
    if col == "asof_time" or col.endswith("_time") or col == "event_time":
        return "date"
    if col.endswith("_status") or col == "status" or col in {"trade_status", "event_status"} or col.endswith("_conf") or col.endswith("_marker") or col.endswith("_importance"):
        return "status"
    if col.endswith("_price") or col in {"current_price", "last_price", "level_price", "zone_low", "zone_high"}:
        return "number"
    if col.endswith("_pips") or col.endswith("_score") or col.endswith("_count") or col in {"rank", "fresh_levels", "tested_levels", "crossed_levels", "total_levels", "touch_count", "selected_levels", "confluence_hits"}:
        return "number"
    if _is_numeric_series(df[col]):
        return "number"
    return "text"


def _table_header(df: pd.DataFrame, table_id: str) -> str:
    headers = []
    for col in df.columns:
        label = html.escape(str(col).replace("_", " "))
        dtype = _column_type(df, col)
        headers.append(f'<th data-col="{html.escape(str(col))}" data-type="{dtype}">{label}</th>')
    header_row = "".join(headers)
    return f'<table id="{table_id}" class="report-table"><thead><tr>{header_row}</tr></thead><tbody>'


def _table_rows(df: pd.DataFrame) -> str:
    rows = []
    for _, row in df.iterrows():
        symbol = _row_symbol(row)
        cells = []
        row_classes = []
        trade_status = str(row.get("trade_status", "")).lower() if hasattr(row, "get") else ""
        event_status = str(row.get("event_status", "")).lower() if hasattr(row, "get") else ""
        upcoming_threshold_count = 0.0
        if hasattr(row, "get"):
            try:
                upcoming_threshold_count = float(row.get("upcoming_threshold_event_count_48h", 0) or 0)
            except Exception:
                upcoming_threshold_count = 0.0

        if trade_status == "blocked" or event_status == "blocking":
            row_classes.append("row-blocked")
        elif event_status == "watch" or upcoming_threshold_count > 0:
            row_classes.append("row-watch")

        for col in df.columns:
            value = row[col]
            display = _format_cell(value, col, symbol=str(symbol) if symbol is not None else None)
            raw = "" if pd.isna(value) else str(value)
            cell_class = []
            if col in {"symbol", "instrument"}:
                cell_class.append("symbol-cell")
            if col.endswith("_status") or col == "status" or col.endswith("_conf") or col.endswith("_marker"):
                cell_class.append("status-cell")
            if col.endswith("_price") or col in {"current_price", "last_price", "level_price", "zone_low", "zone_high"}:
                cell_class.append("number-cell")
            if col.endswith("_pips") or col.endswith("_score") or col in {"rank", "fresh_levels", "tested_levels", "crossed_levels", "total_levels", "touch_count"}:
                cell_class.append("number-cell")
            if col in {"signal_summary", "block_reason", "active_events", "upcoming_events_48h", "affected_symbols", "event_name", "above_levels", "below_levels"} or col.endswith("_name"):
                cell_class.append("text-cell")
            if col in {"above_levels", "below_levels"}:
                cell_class.append("level-list-cell")
            class_attr = f' class="{" ".join(cell_class)}"' if cell_class else ""
            data_sort = html.escape(raw, quote=True)
            cells.append(f'<td{class_attr} data-sort="{data_sort}">{display}</td>')
        row_class_attr = f' class="{" ".join(row_classes)}"' if row_classes else ""
        rows.append(f"<tr{row_class_attr}>" + "".join(cells) + "</tr>")
    return "\n".join(rows)


def _build_table(df: pd.DataFrame, table_id: str) -> str:
    table = _table_header(df, table_id)
    table += _table_rows(df)
    table += "</tbody></table>"
    return table


def dataframe_to_html(df: pd.DataFrame, title: str) -> str:
    display_df = df.loc[:, _select_display_columns(df)].copy()
    table_id = "levels_table"
    table_html = _build_table(display_df, table_id)
    metrics_html = "\n".join(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-note">{html.escape(note)}</div>
        </div>
        """.strip()
        for label, value, note in _build_metrics(df)
    )

    if _is_calendar_status_view(df):
        subtitle = "Pair-level trading guardrail view showing what is blocked now and what is coming next."
    elif _is_calendar_events_view(df):
        subtitle = "Event-level calendar feed for the monitored pairs, including quiet-window timing and affected symbols."
    if _is_matrix_view(df):
        subtitle = "Offline matrix snapshot showing fresh, untested support and resistance levels."
    elif not (_is_calendar_status_view(df) or _is_calendar_events_view(df)):
        subtitle = "Offline dashboard snapshot generated from local parquet data."

    if _is_calendar_status_view(df) or _is_calendar_events_view(df):
        legend_html = """
                <span class="badge blocked">Blocked</span>
                <span class="badge open">Open</span>
                <span class="badge watch">Watch</span>
                <span class="badge high">High</span>
                <span class="badge medium">Medium</span>
                <span class="badge low">Low</span>
        """.strip()
    else:
        legend_html = """
                <span class="badge fresh">Fresh</span>
                <span class="badge tested">Tested</span>
                <span class="badge crossed">Crossed</span>
        """.strip()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
    --bg: #07111d;
    --bg-soft: #0d1726;
    --surface: rgba(12, 18, 32, 0.88);
    --surface-2: rgba(17, 24, 39, 0.96);
    --border: rgba(148, 163, 184, 0.16);
    --text: #e5eef8;
    --muted: #98a8be;
    --accent: #7dd3fc;
    --accent-strong: #38bdf8;
    --fresh: #86efac;
    --tested: #fde68a;
    --crossed: #fda4af;
    --blocked: #fda4af;
    --open: #86efac;
    --watch: #93c5fd;
    --low: #cbd5e1;
    --medium: #fde68a;
    --high: #fca5a5;
}}
* {{
    box-sizing: border-box;
}}
body {{
    margin: 0;
    min-height: 100vh;
    color: var(--text);
    background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.16), transparent 32%),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.09), transparent 28%),
        linear-gradient(180deg, #050b14 0%, var(--bg) 45%, #09121d 100%);
    font-family: "Aptos", "Segoe UI", "Trebuchet MS", sans-serif;
}}
.shell {{
    max-width: 1560px;
    margin: 0 auto;
    padding: 32px 24px 48px;
}}
.hero {{
    display: flex;
    justify-content: space-between;
    gap: 24px;
    align-items: flex-end;
    margin-bottom: 18px;
}}
.eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(56, 189, 248, 0.12);
    color: #c8efff;
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}
.title {{
    margin: 14px 0 10px;
    font-size: clamp(30px, 3.8vw, 58px);
    line-height: 0.98;
    letter-spacing: -0.05em;
}}
.subtitle {{
    margin: 0;
    color: var(--muted);
    max-width: 68ch;
    font-size: 15px;
    line-height: 1.6;
}}
.hero-meta {{
    text-align: right;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
}}
.hero-meta strong {{
    color: var(--text);
}}
.metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin: 24px 0 18px;
}}
.metric-card {{
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(11, 16, 28, 0.94));
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px 16px 14px;
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.24);
}}
.metric-label {{
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.14em;
}}
.metric-value {{
    margin-top: 8px;
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.04em;
}}
.metric-note {{
    margin-top: 6px;
    color: var(--muted);
    font-size: 13px;
}}
.toolbar {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    margin: 18px 0 14px;
}}
.search-wrap {{
    flex: 1 1 360px;
    position: relative;
}}
.search-wrap input {{
    width: 100%;
    border: 1px solid var(--border);
    background: rgba(6, 12, 20, 0.76);
    color: var(--text);
    border-radius: 14px;
    padding: 14px 16px 14px 44px;
    font-size: 14px;
    outline: none;
}}
.search-wrap input:focus {{
    border-color: rgba(125, 211, 252, 0.6);
    box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.12);
}}
.search-icon {{
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    pointer-events: none;
}}
.pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.03);
    color: var(--text);
    font-size: 13px;
}}
.status-legend {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}}
.badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 72px;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid transparent;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.badge.fresh {{
    background: rgba(134, 239, 172, 0.16);
    color: var(--fresh);
    border-color: rgba(134, 239, 172, 0.25);
}}
.badge.tested {{
    background: rgba(253, 230, 138, 0.16);
    color: var(--tested);
    border-color: rgba(253, 230, 138, 0.25);
}}
.badge.crossed {{
    background: rgba(253, 164, 175, 0.16);
    color: var(--crossed);
    border-color: rgba(253, 164, 175, 0.25);
}}
.badge.marker {{
    background: rgba(125, 211, 252, 0.16);
    color: var(--accent);
    border-color: rgba(125, 211, 252, 0.25);
}}
.badge.open {{
    background: rgba(134, 239, 172, 0.16);
    color: var(--open);
    border-color: rgba(134, 239, 172, 0.25);
}}
.badge.blocked {{
    background: rgba(253, 164, 175, 0.16);
    color: var(--blocked);
    border-color: rgba(253, 164, 175, 0.25);
}}
.badge.watch {{
    background: rgba(147, 197, 253, 0.16);
    color: var(--watch);
    border-color: rgba(147, 197, 253, 0.25);
}}
.badge.low {{
    background: rgba(203, 213, 225, 0.12);
    color: var(--low);
    border-color: rgba(203, 213, 225, 0.18);
}}
.badge.medium {{
    background: rgba(253, 230, 138, 0.16);
    color: var(--medium);
    border-color: rgba(253, 230, 138, 0.25);
}}
.badge.high {{
    background: rgba(252, 165, 165, 0.16);
    color: var(--high);
    border-color: rgba(252, 165, 165, 0.25);
}}
.table-shell {{
    border: 1px solid var(--border);
    border-radius: 22px;
    overflow: hidden;
    background: linear-gradient(180deg, rgba(8, 14, 25, 0.88), rgba(5, 10, 18, 0.92));
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
}}
.table-scroll {{
    overflow: auto;
    max-height: min(72vh, 960px);
}}
.report-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    min-width: 100%;
}}
.report-table thead th {{
    position: sticky;
    top: 0;
    z-index: 1;
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(10, 16, 28, 0.98));
    color: var(--accent);
    text-align: left;
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 15px 14px;
    border-bottom: 1px solid rgba(125, 211, 252, 0.14);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}}
.report-table tbody td {{
    padding: 14px 14px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    color: var(--text);
    vertical-align: top;
    white-space: nowrap;
}}
.report-table tbody tr:nth-child(even) td {{
    background: rgba(255, 255, 255, 0.015);
}}
.report-table tbody tr:hover td {{
    background: rgba(125, 211, 252, 0.08);
}}
.report-table tbody tr.row-blocked td {{
    background: rgba(127, 29, 29, 0.22);
}}
.report-table tbody tr.row-watch td {{
    background: rgba(30, 64, 175, 0.14);
}}
.report-table td.number-cell {{
    text-align: right;
    font-variant-numeric: tabular-nums;
}}
.report-table td.symbol-cell {{
    font-weight: 700;
    letter-spacing: 0.02em;
}}
.report-table td.status-cell {{
    white-space: nowrap;
}}
.report-table td.text-cell {{
    white-space: normal;
    min-width: 180px;
    line-height: 1.45;
}}
.report-table td.level-list-cell {{
    min-width: 220px;
    max-width: 280px;
}}
.report-table th.sorted-asc::after {{
    content: " ^";
    color: var(--accent-strong);
}}
.report-table th.sorted-desc::after {{
    content: " v";
    color: var(--accent-strong);
}}
.empty-state {{
    padding: 28px;
    color: var(--muted);
}}
.footer-note {{
    margin-top: 12px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
}}
@media (max-width: 900px) {{
    .hero {{
        flex-direction: column;
        align-items: flex-start;
    }}
    .hero-meta {{
        text-align: left;
    }}
    .table-scroll {{
        max-height: none;
    }}
}}
</style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div>
                <div class="eyebrow">FX level engine dashboard</div>
                <h1 class="title">{html.escape(title)}</h1>
                <p class="subtitle">{html.escape(subtitle)}</p>
            </div>
            <div class="hero-meta">
                <div><strong>Mode:</strong> offline self-contained report</div>
                <div><strong>Rows:</strong> {len(display_df)}</div>
                <div><strong>Columns:</strong> {len(display_df.columns)}</div>
            </div>
        </section>

        <section class="metrics">
            {metrics_html}
        </section>

        <section class="toolbar">
            <div class="search-wrap">
                <span class="search-icon">Search</span>
                <input id="table-search" type="search" placeholder="Search instrument, level, price or status">
            </div>
            <div class="pill" id="row-count">Showing {len(display_df)} rows</div>
            <div class="status-legend">
                {legend_html}
            </div>
        </section>

        <section class="table-shell">
            <div class="table-scroll">
                {table_html}
            </div>
        </section>

        <div class="footer-note">
            Tip: click any column header to sort. The HTML is fully self-contained, so it works offline and does not rely on CDN assets.
        </div>
    </div>

<script>
(function() {{
    const table = document.getElementById('levels_table');
    const search = document.getElementById('table-search');
    const rowCount = document.getElementById('row-count');
    if (!table) {{
        return;
    }}

    const tbody = table.tBodies[0];
    const headers = Array.from(table.tHead.rows[0].cells);
    let sortState = {{ index: -1, direction: 1 }};
    let allRows = Array.from(tbody.rows);

    function normalize(value, type) {{
        const raw = (value ?? '').toString().trim();
        if (!raw) {{
            return '';
        }}
        if (type === 'number') {{
            const parsed = parseFloat(raw.replace(/[^0-9+\\-\\.]/g, ''));
            return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed;
        }}
        if (type === 'date') {{
            const parsed = Date.parse(raw);
            return Number.isNaN(parsed) ? raw.toLowerCase() : parsed;
        }}
        if (type === 'status') {{
            return raw.toLowerCase();
        }}
        return raw.toLowerCase();
    }}

    function renderRows(rows) {{
        tbody.replaceChildren(...rows);
        allRows = rows;
    }}

    function updateRowCount() {{
        const visible = allRows.filter(row => row.style.display !== 'none').length;
        rowCount.textContent = 'Showing ' + visible + ' / ' + allRows.length + ' rows';
    }}

    function sortBy(index) {{
        const header = headers[index];
        const type = header.dataset.type || 'text';
        const direction = sortState.index === index ? -sortState.direction : 1;
        sortState = {{ index, direction }};

        headers.forEach(th => {{
            th.classList.remove('sorted-asc', 'sorted-desc');
        }});
        header.classList.add(direction === 1 ? 'sorted-asc' : 'sorted-desc');

        const rows = Array.from(allRows);
        rows.sort((a, b) => {{
            const left = normalize(a.cells[index].dataset.sort || a.cells[index].textContent, type);
            const right = normalize(b.cells[index].dataset.sort || b.cells[index].textContent, type);
            if (left < right) return -1 * direction;
            if (left > right) return 1 * direction;
            return 0;
        }});

        renderRows(rows);
        applyFilter();
    }}

    function applyFilter() {{
        const query = search.value.trim().toLowerCase();
        allRows.forEach(row => {{
            const match = !query || row.textContent.toLowerCase().includes(query);
            row.style.display = match ? '' : 'none';
        }});
        updateRowCount();
    }}

    headers.forEach((th, index) => {{
        th.addEventListener('click', () => sortBy(index));
    }});

    search.addEventListener('input', applyFilter);
    applyFilter();
}})();
</script>
</body>
</html>
"""


def save_html_report(df: pd.DataFrame, output_path: str | Path, title: str) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dataframe_to_html(df, title), encoding="utf-8")
    return output_path
