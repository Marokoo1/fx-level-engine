#!/usr/bin/env python3
"""Smoke test for the live Trading Economics calendar feed."""

from src.economic_calendar import get_calendar


MAJORS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
]


def main() -> bool:
    print("\n" + "=" * 72)
    print("Trading Economics live calendar smoke test")
    print("=" * 72)
    print()

    calendar = get_calendar()

    print("Fetching live calendar from Trading Economics...")
    success = calendar.update(sources=["trading_economics"])
    print(f"Update success: {success}")
    print(f"Cached events: {len(calendar.events)}")

    if not calendar.events:
        print("No events were fetched.")
        return False

    upcoming = calendar.get_upcoming_events(hours_ahead=72)
    print()
    print(f"Upcoming events in the next 72 hours: {len(upcoming)}")

    for i, event in enumerate(upcoming[:20], 1):
        time_str = event.time.strftime("%Y-%m-%d %H:%M UTC")
        print(f"{i:2}. {time_str} | {event.importance:6} | {event.country:15} | {event.event_name}")

    if len(upcoming) > 20:
        print(f"... and {len(upcoming) - 20} more events")

    print()
    print("Blocked majors now (medium+ impact, 30 minute quiet window):")
    blocked = calendar.get_blocked_symbols(
        symbols=MAJORS,
        quiet_minutes=30,
        importance_threshold="medium",
    )
    print(blocked)

    print()
    print("Blocked majors by symbol:")
    for symbol in MAJORS:
        status = "BLOCKED" if symbol in blocked else "open"
        print(f"  {symbol:7} -> {status}")

    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
