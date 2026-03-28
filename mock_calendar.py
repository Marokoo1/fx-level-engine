"""
Mock Economic Calendar Data for Testing & Development
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

from src.economic_calendar import EconomicEvent, EconomicCalendar


def create_mock_events() -> list[EconomicEvent]:
    """Create realistic mock economic events for testing."""
    
    now = datetime.now(timezone.utc)
    
    return [
        # HIGH impact events
        EconomicEvent(
            time=now + timedelta(hours=1),
            symbol="EURUSD",
            country="EU",
            event_name="ECB Interest Rate Decision",
            importance="high",
            forecast="2.50%",
            previous="2.50%",
            source="mock"
        ),
        EconomicEvent(
            time=now + timedelta(hours=2, minutes=30),
            symbol="GBPUSD",
            country="GB",
            event_name="Bank of England Rate Decision",
            importance="high",
            forecast="5.50%",
            previous="5.50%",
            source="mock"
        ),
        
        # MEDIUM impact events
        EconomicEvent(
            time=now + timedelta(hours=3),
            symbol="AUDUSD",
            country="AU",
            event_name="Australia Employment Change",
            importance="medium",
            forecast="35.0K",
            previous="42.0K",
            source="mock"
        ),
        EconomicEvent(
            time=now + timedelta(hours=4),
            symbol="NZDUSD",
            country="NZ",
            event_name="NZ Inflation Rate",
            importance="medium",
            forecast="3.8%",
            previous="4.4%",
            source="mock"
        ),
        EconomicEvent(
            time=now + timedelta(hours=4, minutes=30),
            symbol="USDJPY",
            country="JP",
            event_name="Japan Industrial Production",
            importance="medium",
            forecast="1.4%",
            previous="2.0%",
            source="mock"
        ),
        
        # LOW impact events
        EconomicEvent(
            time=now + timedelta(hours=5),
            symbol="USDCAD",
            country="CA",
            event_name="Canada Manufacturing PMI",
            importance="low",
            forecast="48.5",
            previous="47.8",
            source="mock"
        ),
        EconomicEvent(
            time=now + timedelta(hours=6),
            symbol="EURGBP",
            country="EU",
            event_name="EU Manufacturing PMI",
            importance="low",
            forecast="46.2",
            previous="46.5",
            source="mock"
        ),
        EconomicEvent(
            time=now + timedelta(hours=23),
            symbol="USDJPY",
            country="US",
            event_name="US Jobless Claims",
            importance="medium",
            forecast="210K",
            previous="214K",
            source="mock"
        ),
    ]


def load_mock_calendar() -> EconomicCalendar:
    """Load calendar with mock data (for testing/development)."""
    
    cal = EconomicCalendar()
    cal.events = create_mock_events()
    
    # Save to cache so it's available
    cal._save_cache()
    
    return cal


if __name__ == "__main__":
    # Create and display mock events
    print("\n" + "="*60)
    print("MOCK ECONOMIC CALENDAR - FOR TESTING")
    print("="*60)
    
    events = create_mock_events()
    
    print(f"\nCreated {len(events)} mock events:\n")
    
    for event in sorted(events, key=lambda e: e.time):
        time_str = event.time.strftime("%H:%M UTC")
        importance_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }.get(event.importance, "⚪")
        
        print(f"{importance_emoji} {time_str} | {event.symbol:7} | {event.event_name}")
    
    # Test blocking
    cal = load_mock_calendar()
    blocked_high = cal.get_blocked_symbols(quiet_minutes=30, importance_threshold="high")
    blocked_medium = cal.get_blocked_symbols(quiet_minutes=30, importance_threshold="medium")
    blocked_low = cal.get_blocked_symbols(quiet_minutes=30, importance_threshold="low")
    
    print(f"\n{'='*60}")
    print(f"🔴 HIGH impact blocked (quiet_minutes=30): {blocked_high}")
    print(f"🟡 MEDIUM impact blocked: {blocked_medium}")
    print(f"🟢 LOW impact blocked: {blocked_low}")
    print(f"{'='*60}\n")
