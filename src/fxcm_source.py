from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


@dataclass
class FXCMCredentials:
    user: str
    password: str
    url: str
    connection: str
    session_id: str | None = None
    pin: str | None = None


class FXCMSource:
    """
    FXCM ForexConnect adapter.

    Uses ForexConnect.get_history(instrument, timeframe, date_from, date_to, quotes_count)
    as documented in the official ForexConnect Python docs.
    """

    def __init__(self, credentials: FXCMCredentials):
        self.credentials = credentials
        self.fx = None

    @classmethod
    def from_env(cls, settings: dict) -> "FXCMSource":
        load_dotenv()
        fx = settings["fxcm"]
        creds = FXCMCredentials(
            user=os.getenv(fx["user_env"], ""),
            password=os.getenv(fx["password_env"], ""),
            url=os.getenv(fx["url_env"], "http://www.fxcorporate.com/Hosts.jsp"),
            connection=os.getenv(fx["connection_env"], "Demo"),
            session_id=os.getenv(fx["session_id_env"], "") or None,
            pin=os.getenv(fx["pin_env"], "") or None,
        )
        missing = [k for k, v in {
            fx["user_env"]: creds.user,
            fx["password_env"]: creds.password,
            fx["url_env"]: creds.url,
            fx["connection_env"]: creds.connection,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing FXCM environment variables: {', '.join(missing)}")
        return cls(creds)

    def connect(self) -> None:
        try:
            from forexconnect import ForexConnect  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "ForexConnect Python package/SDK is not installed in this environment. "
                "Install the FXCM ForexConnect SDK that matches your OS and Python."
            ) from exc

        self.fx = ForexConnect()
        self.fx.login(
            self.credentials.user,
            self.credentials.password,
            self.credentials.url,
            self.credentials.connection,
            self.credentials.session_id,
            self.credentials.pin,
        )

    def disconnect(self) -> None:
        if self.fx is not None:
            try:
                self.fx.logout()
            finally:
                self.fx = None

    def __enter__(self) -> "FXCMSource":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    @staticmethod
    def _normalize_history(history, symbol: str, timeframe: str) -> pd.DataFrame:
        df = pd.DataFrame(history)
        if df.empty:
            return df

        rename_map = {
            "Date": "timestamp",
            "BidOpen": "bid_open",
            "BidHigh": "bid_high",
            "BidLow": "bid_low",
            "BidClose": "bid_close",
            "AskOpen": "ask_open",
            "AskHigh": "ask_high",
            "AskLow": "ask_low",
            "AskClose": "ask_close",
            "Volume": "volume",
        }
        df = df.rename(columns=rename_map)
        if "timestamp" not in df.columns:
            raise ValueError(f"Unexpected FXCM history columns: {list(df.columns)}")

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        if all(c in df.columns for c in ["bid_open", "bid_high", "bid_low", "bid_close", "ask_open", "ask_high", "ask_low", "ask_close"]):
            df["open"] = (df["bid_open"] + df["ask_open"]) / 2.0
            df["high"] = (df["bid_high"] + df["ask_high"]) / 2.0
            df["low"] = (df["bid_low"] + df["ask_low"]) / 2.0
            df["close"] = (df["bid_close"] + df["ask_close"]) / 2.0
        else:
            direct_map = {
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
            }
            df = df.rename(columns=direct_map)

        if "volume" not in df.columns:
            df["volume"] = 0.0

        df["symbol"] = symbol
        df["timeframe"] = timeframe.lower()
        keep = [
            "symbol", "timeframe", "timestamp",
            "open", "high", "low", "close", "volume",
            "bid_open", "bid_high", "bid_low", "bid_close",
            "ask_open", "ask_high", "ask_low", "ask_close",
        ]
        keep = [c for c in keep if c in df.columns]
        return df[keep].sort_values("timestamp").reset_index(drop=True)

    def get_history(
        self,
        symbol: str,
        timeframe: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        quotes_count: int = -1,
    ) -> pd.DataFrame:
        if self.fx is None:
            raise RuntimeError("FXCM session is not connected")
        history = self.fx.get_history(symbol, timeframe, date_from, date_to, quotes_count)
        return self._normalize_history(history, symbol=symbol, timeframe=timeframe)

    @staticmethod
    def save_history(df: pd.DataFrame, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".parquet":
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False)
        return path
