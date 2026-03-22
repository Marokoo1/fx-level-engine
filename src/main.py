from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.config_loader import load_instruments, load_settings
from src.ib_client import IBClient, IBConnectionConfig
from src.logger import configure_logger
from src.market_data import MarketDataStore


def parse_args():
    parser = argparse.ArgumentParser(description="FX Level Engine bootstrap CLI")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["download-data"],
        help="Action to perform",
    )
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["intraday", "swing", "invest", "all"],
        help="Which instrument group to use",
    )
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["M1", "M30", "H4", "D1"],
        help="List of timeframes to download",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=500,
        help="Approximate number of bars to keep per timeframe",
    )
    return parser.parse_args()


def resolve_ib_config(settings: dict) -> IBConnectionConfig:
    env_host = os.getenv("IB_HOST")
    env_port = os.getenv("IB_PORT")
    env_client_id = os.getenv("IB_CLIENT_ID")

    ib_cfg = settings["ib"]

    host = env_host or ib_cfg["host"]
    port = int(env_port) if env_port else int(ib_cfg["port"])
    client_id = int(env_client_id) if env_client_id else int(ib_cfg["client_id"])

    return IBConnectionConfig(host=host, port=port, client_id=client_id)


def get_symbols(instruments_cfg: dict, strategy: str) -> list[str]:
    if strategy == "all":
        merged = []
        for key in ("intraday", "swing", "invest"):
            merged.extend(instruments_cfg.get(key, []))
        return sorted(set(merged))
    return instruments_cfg.get(strategy, [])


def main():
    load_dotenv()
    args = parse_args()

    settings = load_settings()
    instruments_cfg = load_instruments()

    logger = configure_logger(settings.get("log_level", "INFO"))
    raw_dir = Path(settings["paths"]["raw_data"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    store = MarketDataStore(raw_dir=raw_dir)
    ib_client = IBClient(resolve_ib_config(settings))

    symbols = get_symbols(instruments_cfg, args.strategy)
    if not symbols:
        raise ValueError(f"No symbols found for strategy: {args.strategy}")

    logger.info(f"Selected symbols: {symbols}")
    logger.info(f"Selected timeframes: {args.timeframes}")
    logger.info(f"Bars per timeframe: {args.bars}")

    if args.mode == "download-data":
        ib_client.connect()
        try:
            for symbol in symbols:
                for timeframe in args.timeframes:
                    logger.info(f"Downloading {symbol} {timeframe} ...")
                    df = ib_client.fetch_historical_fx_bars(
                        symbol=symbol,
                        timeframe=timeframe,
                        bars=args.bars,
                    )
                    path = store.save_bars(symbol, timeframe, df)
                    logger.info(f"Saved {len(df)} rows to {path}")
        finally:
            ib_client.disconnect()
            logger.info("Disconnected from IB")


if __name__ == "__main__":
    main()
