from __future__ import annotations

import argparse
from pprint import pprint

from .config_loader import load_settings, load_symbols
from .logger import configure_logger
from .pipeline import build_all_levels, export_due_tables, export_tables, run_all, run_daily, run_download
from .scheduler import due_tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FX level engine: FXCM -> POC/IB -> tables")
    parser.add_argument(
        "--mode",
        choices=["download", "build-levels", "export-due", "export-all", "run-daily", "run-all"],
        default="run-daily",
    )
    parser.add_argument("--symbols", nargs="*", help="Optional list of FXCM symbols, e.g. EUR/USD GBP/USD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = configure_logger()
    settings = load_settings()
    symbols = args.symbols or load_symbols()

    logger.info(f"Mode={args.mode} symbols={len(symbols)} due_tables={due_tables()}")

    if args.mode == "download":
        result = run_download(settings, symbols)
        pprint(result)
        return

    if args.mode == "build-levels":
        df = build_all_levels(settings, symbols)
        print(df.head(50).to_string(index=False))
        return

    if args.mode == "export-due":
        df = build_all_levels(settings, symbols)
        result = export_due_tables(df, settings)
        pprint(result)
        return

    if args.mode == "export-all":
        df = build_all_levels(settings, symbols)
        result = export_tables(df, settings)
        pprint(result)
        return

    if args.mode == "run-all":
        result = run_all(settings, symbols)
        pprint(result)
        return

    result = run_daily(settings, symbols)
    pprint(result)


if __name__ == "__main__":
    main()
