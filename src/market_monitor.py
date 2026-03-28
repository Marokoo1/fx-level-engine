"""
Market Monitor - Integrates economic calendar with trading pipeline.
Provides decision support for blocking trades during high-impact events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .economic_calendar import EconomicCalendar, get_calendar

logger = logging.getLogger(__name__)


class MarketMonitor:
    """
    Monitors market conditions and provides trading recommendations.
    Integrates economic calendar with trading pipeline.
    """

    def __init__(
        self,
        calendar: Optional[EconomicCalendar] = None,
        cache_dir: Path = Path("data/state"),
        cache_ttl_hours: int = 4,
        quiet_minutes: int = 30,
        importance_threshold: str = "medium",
    ):
        """
        Initialize market monitor.

        Args:
            calendar: EconomicCalendar instance (or None to create new)
            cache_dir: Directory for caching economic data
            cache_ttl_hours: TTL for cached calendar data
            quiet_minutes: Minutes before/after event to block trading
            importance_threshold: Minimum event importance ("low", "medium", "high")
        """
        self.calendar = calendar or get_calendar(cache_dir, cache_ttl_hours=cache_ttl_hours)
        self.quiet_minutes = quiet_minutes
        self.importance_threshold = importance_threshold

    def refresh_calendar(
        self,
        sources: list[str] | None = None,
        trading_economics_api_key: Optional[str] = None,
        myfxbook_api_token: Optional[str] = None,
    ) -> bool:
        """
        Update economic calendar from sources.

        Returns:
            True if update was successful
        """
        logger.info("Refreshing economic calendar...")
        success = self.calendar.update(
            sources=sources,
            trading_economics_api_key=trading_economics_api_key,
            myfxbook_api_token=myfxbook_api_token,
        )
        if success:
            logger.info(f"Calendar updated: {len(self.calendar.events)} events loaded")
        return success

    def can_trade_symbol(self, symbol: str, min_importance: str | None = None) -> tuple[bool, str]:
        """
        Check if symbol is safe to trade right now.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            min_importance: Optional override for the importance threshold

        Returns:
            (can_trade: bool, reason: str)
        """
        threshold = min_importance or self.importance_threshold
        importance_levels = {"low": 1, "medium": 2, "high": 3}
        threshold_value = importance_levels.get(threshold, 2)

        active_events = [
            event
            for event in self.calendar.get_events_for_symbol(symbol)
            if importance_levels.get(event.importance, 0) >= threshold_value
            and event.is_active_now(self.quiet_minutes)
        ]

        if active_events:
            event_str = ", ".join(event.event_name for event in active_events)
            return False, f"Blocked: {event_str}"

        return True, "OK"

    def get_trading_restrictions(self, symbols: list[str] | None = None) -> dict[str, list[str]]:
        """
        Get all current trading restrictions by importance level.

        Returns:
            Dict with keys "high", "medium", "low" and symbol lists as values
        """
        return {
            "high": self.calendar.get_blocked_symbols(
                symbols=symbols,
                quiet_minutes=self.quiet_minutes,
                importance_threshold="high",
            ),
            "medium": self.calendar.get_blocked_symbols(
                symbols=symbols,
                quiet_minutes=self.quiet_minutes,
                importance_threshold="medium",
            ),
            "low": self.calendar.get_blocked_symbols(
                symbols=symbols,
                quiet_minutes=self.quiet_minutes,
                importance_threshold="low",
            ),
        }

    def filter_tradeable_symbols(self, symbols: list[str], min_importance: str = "medium") -> list[str]:
        """
        Filter list of symbols to only tradeable ones.

        Args:
            symbols: List of symbols to check
            min_importance: Minimum event importance to consider

        Returns:
            Filtered list of safe symbols
        """
        return [symbol for symbol in symbols if self.can_trade_symbol(symbol, min_importance=min_importance)[0]]

    def get_market_status(self, symbols: list[str] | None = None) -> dict:
        """
        Get overall market status and trading conditions.

        Returns:
            Dict with status information
        """
        restrictions = self.get_trading_restrictions(symbols=symbols)
        upcoming = self.calendar.get_upcoming_events(hours_ahead=24)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "calendar_status": "ready" if self.calendar.events else "empty",
            "blocked_high": restrictions["high"],
            "blocked_medium": restrictions["medium"],
            "blocked_low": restrictions["low"],
            "upcoming_events_24h": len(upcoming),
            "next_event": upcoming[0].time.isoformat() if upcoming else None,
        }

    def print_status(self, symbols: list[str] | None = None) -> None:
        """Print market status to logger."""
        restrictions = self.get_trading_restrictions(symbols=symbols)
        status = self.get_market_status(symbols=symbols)

        logger.info("=" * 60)
        logger.info("MARKET STATUS")
        logger.info("=" * 60)
        logger.info(f"Calendar: {status['calendar_status']}")

        if restrictions["high"]:
            logger.warning(f"HIGH IMPACT blocked: {', '.join(restrictions['high'])}")

        if restrictions["medium"]:
            logger.info(f"MEDIUM blocked: {', '.join(restrictions['medium'])}")

        if restrictions["low"]:
            logger.debug(f"LOW blocked: {', '.join(restrictions['low'])}")

        logger.info(f"Upcoming events (24h): {status['upcoming_events_24h']}")
        if status["next_event"]:
            logger.info(f"Next event: {status['next_event']}")
        logger.info("=" * 60)


def get_monitor(
    cache_dir: Path = Path("data/state"),
    cache_ttl_hours: int = 4,
    quiet_minutes: int = 30,
    importance_threshold: str = "medium",
) -> MarketMonitor:
    """Factory function to create market monitor instance."""
    return MarketMonitor(
        cache_dir=cache_dir,
        cache_ttl_hours=cache_ttl_hours,
        quiet_minutes=quiet_minutes,
        importance_threshold=importance_threshold,
    )
