from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from ib_insync import IB, Forex, util


@dataclass
class IBConnectionConfig:
    host: str
    port: int
    client_id: int


class IBClient:
    def __init__(self, config: IBConnectionConfig):
        self.config = config
        self.ib = IB()

    def connect(self) -> None:
        if not self.ib.isConnected():
            self.ib.connect(
                self.config.host,
                self.config.port,
                clientId=self.config.client_id,
                readonly=True,
            )

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    @staticmethod
    def make_fx_contract(symbol: str) -> Forex:
        if len(symbol) != 6:
            raise ValueError(f"FX symbol must have 6 characters, got: {symbol}")
        base = symbol[:3]
        quote = symbol[3:]
        return Forex(f"{base}{quote}")

    @staticmethod
    def _ib_bar_size(timeframe: str) -> str:
        mapping = {
            "M1": "1 min",
            "M5": "5 mins",
            "M15": "15 mins",
            "M30": "30 mins",
            "H1": "1 hour",
            "H4": "4 hours",
            "D1": "1 day",
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return mapping[timeframe]

    @staticmethod
    def _ib_duration(timeframe: str, bars: int) -> str:
        """
        Approximate duration string accepted by IB.
        Better to slightly overshoot than undershoot.
        """
        if timeframe == "M1":
            days = max(1, math.ceil(bars / (24 * 60)) + 2)
            return f"{days} D"
        if timeframe == "M5":
            days = max(1, math.ceil(bars / (24 * 12)) + 3)
            return f"{days} D"
        if timeframe == "M15":
            days = max(2, math.ceil(bars / (24 * 4)) + 5)
            return f"{days} D"
        if timeframe == "M30":
            days = max(3, math.ceil(bars / (24 * 2)) + 10)
            return f"{days} D"
        if timeframe == "H1":
            days = max(7, math.ceil(bars / 24) + 20)
            return f"{days} D"
        if timeframe == "H4":
            days = max(30, math.ceil(bars / 6) + 40)
            return f"{days} D"
        if timeframe == "D1":
            years = max(1, math.ceil((bars + 50) / 365))
            return f"{years} Y"
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    def fetch_historical_fx_bars(
        self,
        symbol: str,
        timeframe: str,
        bars: int = 500,
        end_datetime: str = "",
        what_to_show: str = "MIDPOINT",
        use_rth: bool = False,
    ) -> pd.DataFrame:
        contract = self.make_fx_contract(symbol)
        self.ib.qualifyContracts(contract)

        bar_size = self._ib_bar_size(timeframe)
        duration = self._ib_duration(timeframe, bars)

        bars_data = self.ib.reqHistoricalData(
            contract,
            endDateTime=end_datetime,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=False,
        )

        if not bars_data:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]
            )

        df = util.df(bars_data).copy()

        if df.empty:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]
            )

        df.rename(columns={"date": "timestamp"}, inplace=True)

        if "volume" not in df.columns:
            df["volume"] = 0.0

        keep_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        df = df[keep_cols].copy()

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df["symbol"] = symbol
        df["timeframe"] = timeframe

        df.dropna(subset=["timestamp"], inplace=True)
        df.sort_values("timestamp", inplace=True)
        df.drop_duplicates(subset=["timestamp"], inplace=True)

        if len(df) > bars:
            df = df.tail(bars).copy()

        df.reset_index(drop=True, inplace=True)
        return df
