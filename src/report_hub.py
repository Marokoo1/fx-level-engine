from __future__ import annotations

from pathlib import Path
import html

import pandas as pd


HUB_SECTIONS = [
    {
        "id": "calendar",
        "label": "Overview",
        "title": "Calendar",
        "description": "Global tradeability status and upcoming event details across the configured instruments.",
        "cards": [
            {
                "eyebrow": "Status",
                "title": "Calendar Status",
                "description": "See which pairs are open, blocked, or on watch because of relevant economic news.",
                "href": "data/tables/calendar_status.html",
                "csv": "data/tables/calendar_status.csv",
                "button": "Open status",
                "primary": True,
            },
            {
                "eyebrow": "Events",
                "title": "Calendar Events",
                "description": "Detailed list of upcoming events, quiet windows, and affected symbols.",
                "href": "data/tables/calendar_events.html",
                "csv": "data/tables/calendar_events.csv",
                "button": "Open events",
                "primary": True,
            },
        ],
    },
    {
        "id": "intraday",
        "label": "Trading Horizon",
        "title": "Intraday",
        "description": "Main intraday level view plus the POC and IB matrix snapshots for faster scanning.",
        "cards": [
            {
                "eyebrow": "Primary View",
                "title": "Intraday Levels",
                "description": "Main intraday report with nearest supports, resistances, and calendar context.",
                "href": "data/tables/intraday_view.html",
                "csv": "data/tables/intraday_view.csv",
                "button": "Open intraday",
                "primary": True,
            },
            {
                "eyebrow": "Matrix",
                "title": "Intraday POC Matrix",
                "description": "Fresh intraday POC supports and resistances with compact side-by-side distance view.",
                "href": "data/tables/poc_matrix_view.html",
                "csv": "data/tables/poc_matrix_view.csv",
                "button": "Open POC matrix",
                "primary": False,
            },
            {
                "eyebrow": "Matrix",
                "title": "Intraday IB Matrix",
                "description": "Fresh intraday IB supports and resistances across the full configured instrument set.",
                "href": "data/tables/ib_matrix_view.html",
                "csv": "data/tables/ib_matrix_view.csv",
                "button": "Open IB matrix",
                "primary": False,
            },
        ],
    },
    {
        "id": "swing",
        "label": "Trading Horizon",
        "title": "Swing",
        "description": "Swing-level report family with the same structure as intraday, but built from the swing table scope.",
        "cards": [
            {
                "eyebrow": "Primary View",
                "title": "Swing Levels",
                "description": "Higher-timeframe level report with calendar-aware status and next-event context.",
                "href": "data/tables/swing_view.html",
                "csv": "data/tables/swing_view.csv",
                "button": "Open swing",
                "primary": True,
            },
            {
                "eyebrow": "Matrix",
                "title": "Swing POC Matrix",
                "description": "Fresh swing POC support and resistance slots in the compact matrix layout.",
                "href": "data/tables/swing_poc_matrix_view.html",
                "csv": "data/tables/swing_poc_matrix_view.csv",
                "button": "Open swing POC",
                "primary": False,
            },
            {
                "eyebrow": "Matrix",
                "title": "Swing IB Matrix",
                "description": "Fresh swing IB support and resistance slots for the configured instrument universe.",
                "href": "data/tables/swing_ib_matrix_view.html",
                "csv": "data/tables/swing_ib_matrix_view.csv",
                "button": "Open swing IB",
                "primary": False,
            },
        ],
    },
    {
        "id": "invest",
        "label": "Trading Horizon",
        "title": "Invest",
        "description": "Longer-horizon report family for broader support and resistance inspection.",
        "cards": [
            {
                "eyebrow": "Primary View",
                "title": "Invest Levels",
                "description": "Longer-horizon level report with calendar context and key structural levels.",
                "href": "data/tables/invest_view.html",
                "csv": "data/tables/invest_view.csv",
                "button": "Open invest",
                "primary": True,
            },
            {
                "eyebrow": "Matrix",
                "title": "Invest POC Matrix",
                "description": "Longer-horizon POC matrix view for scanning fresh invest-table POC levels.",
                "href": "data/tables/invest_poc_matrix_view.html",
                "csv": "data/tables/invest_poc_matrix_view.csv",
                "button": "Open invest POC",
                "primary": False,
            },
            {
                "eyebrow": "Matrix",
                "title": "Invest IB Matrix",
                "description": "Longer-horizon IB matrix view for the invest table family and configured symbols.",
                "href": "data/tables/invest_ib_matrix_view.html",
                "csv": "data/tables/invest_ib_matrix_view.csv",
                "button": "Open invest IB",
                "primary": False,
            },
        ],
    },
]


def _format_timestamp(value) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return "n/a"
    return ts.strftime("%Y-%m-%d %H:%M UTC")


def _instrument_count(df: pd.DataFrame) -> int:
    if "symbol" in df.columns:
        return int(df["symbol"].dropna().astype(str).nunique())
    if "instrument" in df.columns:
        return int(df["instrument"].dropna().astype(str).nunique())
    if "affected_symbols" in df.columns:
        instruments: set[str] = set()
        for raw in df["affected_symbols"].dropna().astype(str):
            for token in raw.split(","):
                token = token.strip()
                if token:
                    instruments.add(token)
        return len(instruments)
    return int(len(df))


def _report_stats(project_root: Path, csv_rel_path: str) -> dict[str, str]:
    csv_path = project_root / csv_rel_path
    if not csv_path.exists():
        return {"instruments": "n/a", "rows": "n/a", "updated": "not generated"}

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return {"instruments": "n/a", "rows": "n/a", "updated": "unreadable"}

    updated = _format_timestamp(df["asof_time"].max()) if "asof_time" in df.columns and not df.empty else _format_timestamp(None)
    return {
        "instruments": str(_instrument_count(df)),
        "rows": str(int(len(df))),
        "updated": updated,
    }


def _render_card(project_root: Path, card: dict) -> str:
    stats = _report_stats(project_root, card["csv"])
    button_class = "button" if card.get("primary", False) else "button secondary"
    return f"""
        <article class="card">
          <div>
            <small>{html.escape(card['eyebrow'])}</small>
            <h3>{html.escape(card['title'])}</h3>
            <p>{html.escape(card['description'])}</p>
            <div class="stats">
              <span class="stat-pill">{html.escape(stats['instruments'])} instruments</span>
              <span class="stat-pill">{html.escape(stats['rows'])} rows</span>
              <span class="stat-pill">Updated {html.escape(stats['updated'])}</span>
            </div>
          </div>
          <div class="button-row">
            <a class="{button_class}" href="{html.escape(card['href'])}" target="_blank" rel="noopener noreferrer">{html.escape(card['button'])}</a>
          </div>
          <div class="hint">Opens in a new tab.</div>
        </article>
    """.strip()


def _render_section(project_root: Path, section: dict) -> str:
    cards_html = "\n".join(_render_card(project_root, card) for card in section["cards"])
    return f"""
    <section class="section" id="{html.escape(section['id'])}">
      <div class="section-header">
        <div>
          <span class="section-label">{html.escape(section['label'])}</span>
          <h2>{html.escape(section['title'])}</h2>
        </div>
        <p>{html.escape(section['description'])}</p>
      </div>
      <div class="section-grid">
{cards_html}
      </div>
    </section>
    """.strip()


def render_report_hub(project_root: Path | str = ".") -> str:
    project_root = Path(project_root)
    nav_html = "\n".join(
        f'      <a href="#{html.escape(section["id"])}">{html.escape(section["title"])}</a>'
        for section in HUB_SECTIONS
    )
    sections_html = "\n\n".join(_render_section(project_root, section) for section in HUB_SECTIONS)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FX Level Engine Report Hub</title>
  <style>
    :root {{
      --bg: #f4efe5;
      --panel: rgba(255, 252, 246, 0.94);
      --panel-strong: #fffaf0;
      --section: rgba(255, 255, 255, 0.52);
      --text: #1f2b24;
      --muted: #5e6d64;
      --line: rgba(31, 43, 36, 0.12);
      --accent: #1b7f5b;
      --accent-strong: #0e5b40;
      --accent-soft: rgba(27, 127, 91, 0.1);
      --shadow: 0 18px 50px rgba(31, 43, 36, 0.12);
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(27, 127, 91, 0.16), transparent 34%),
        radial-gradient(circle at top right, rgba(201, 126, 40, 0.14), transparent 28%),
        linear-gradient(180deg, #f7f1e7 0%, #efe6d7 100%);
      min-height: 100vh;
    }}

    .shell {{
      width: min(1160px, calc(100% - 32px));
      margin: 36px auto;
      padding: 28px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent-strong);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 18px 0 10px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(34px, 5vw, 56px);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}

    .lead {{
      max-width: 780px;
      margin: 0 0 24px;
      font-size: 18px;
      line-height: 1.6;
      color: var(--muted);
    }}

    .jumpnav {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 0 0 28px;
    }}

    .jumpnav a {{
      display: inline-flex;
      align-items: center;
      min-height: 40px;
      padding: 0 14px;
      border-radius: 999px;
      border: 1px solid rgba(14, 91, 64, 0.14);
      background: rgba(255, 255, 255, 0.78);
      color: var(--accent-strong);
      text-decoration: none;
      font-weight: 700;
    }}

    .jumpnav a:hover {{
      background: var(--accent-soft);
    }}

    .section {{
      margin-top: 22px;
      padding: 22px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: var(--section);
    }}

    .section-header {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: end;
      justify-content: space-between;
      margin-bottom: 18px;
    }}

    .section-label {{
      display: inline-block;
      margin-bottom: 8px;
      color: var(--accent-strong);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .section h2 {{
      margin: 0;
      font-size: clamp(28px, 4vw, 38px);
      line-height: 1.05;
      font-family: Georgia, "Times New Roman", serif;
    }}

    .section p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      max-width: 760px;
    }}

    .section-grid {{
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }}

    .card {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 220px;
      padding: 20px;
      border-radius: 20px;
      background: var(--panel-strong);
      border: 1px solid var(--line);
      box-shadow: 0 10px 24px rgba(31, 43, 36, 0.08);
    }}

    .card small {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}

    .card h3 {{
      margin: 14px 0 10px;
      font-size: 24px;
      line-height: 1.15;
    }}

    .card p {{
      margin: 0 0 16px;
      color: var(--muted);
      line-height: 1.5;
    }}

    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 18px;
    }}

    .stat-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      padding: 0 10px;
      border-radius: 999px;
      background: rgba(27, 127, 91, 0.08);
      border: 1px solid rgba(14, 91, 64, 0.1);
      color: var(--accent-strong);
      font-size: 12px;
      font-weight: 700;
    }}

    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      font-weight: 700;
      transition: transform 0.15s ease, background 0.15s ease;
    }}

    .button:hover {{
      background: var(--accent-strong);
      transform: translateY(-1px);
    }}

    .button.secondary {{
      background: transparent;
      color: var(--accent-strong);
      border: 1px solid rgba(14, 91, 64, 0.2);
    }}

    .button.secondary:hover {{
      background: rgba(27, 127, 91, 0.08);
    }}

    .hint {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 8px;
    }}

    .notes {{
      margin-top: 24px;
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}

    .note {{
      padding: 18px 20px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.62);
    }}

    .note h3 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}

    .note p,
    .note li {{
      color: var(--muted);
      line-height: 1.5;
    }}

    .note ul {{
      margin: 0;
      padding-left: 18px;
    }}

    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.95em;
      background: rgba(31, 43, 36, 0.06);
      padding: 2px 6px;
      border-radius: 6px;
    }}

    @media (max-width: 640px) {{
      .shell {{
        width: calc(100% - 20px);
        margin: 10px auto;
        padding: 20px;
      }}

      .section {{
        padding: 18px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <div class="eyebrow">FX Level Engine</div>
    <h1>Open reports without losing the hub.</h1>
    <p class="lead">
      This page is the simplest browser starting point. Every report link below opens in a new tab
      so the hub stays available. If you want to refresh data first, double-click
      <code>RUN_AND_OPEN_REPORTS.cmd</code> in the project root.
    </p>

    <nav class="jumpnav">
{nav_html}
    </nav>

{sections_html}

    <section class="notes">
      <article class="note">
        <h3>One-click usage</h3>
        <ul>
          <li>Double-click <code>OPEN_REPORT_HUB.cmd</code> to open this hub.</li>
          <li>Double-click <code>RUN_AND_OPEN_REPORTS.cmd</code> to refresh data and then open reports.</li>
        </ul>
      </article>

      <article class="note">
        <h3>If a rebuild fails</h3>
        <p>
          Close any open CSV or HTML preview tabs that may lock files in <code>data/tables</code>,
          then run <code>RUN_AND_OPEN_REPORTS.cmd</code> again.
        </p>
      </article>

      <article class="note">
        <h3>Session notes</h3>
        <p>
          The current handoff summary is stored in <code>SESSION_HANDOFF.md</code>.
        </p>
      </article>
    </section>
  </main>
</body>
</html>
"""


def save_report_hub(project_root: Path | str = ".") -> Path:
    project_root = Path(project_root)
    output_path = project_root / "REPORT_HUB.html"
    output_path.write_text(render_report_hub(project_root), encoding="utf-8")
    return output_path
