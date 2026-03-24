from __future__ import annotations

from pathlib import Path

from loguru import logger


def configure_logger(log_dir: str | Path = "logs"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(lambda msg: print(msg, end=""))
    logger.add(Path(log_dir) / "fx_level_engine.log", rotation="5 MB", retention=10)
    return logger
