from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper().replace("/", "") else 0.0001


def bucket_size_for_symbol(symbol: str, settings: dict) -> float:
    pips = settings["poc"]["bucket_size_pips"]["JPY"] if "JPY" in symbol.upper() else settings["poc"]["bucket_size_pips"]["default"]
    return pip_size(symbol) * float(pips)


def to_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")
