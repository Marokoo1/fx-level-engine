#!/usr/bin/env python3
"""
Example script demonstrating Economic Calendar Agent usage.
Shows how to use market monitor to block trading during economic events.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config_loader import load_settings, load_symbols
from src.market_monitor import get_monitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to use mock data for testing
try:
    from mock_calendar import load_mock_calendar
    USE_MOCK = True
except ImportError:
    USE_MOCK = False


def example_1_basic_monitoring():
    """Example 1: Basic market monitoring."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Market Monitoring")
    print("="*60)
    
    # Use mock data if available (for testing/dev without internet)
    if USE_MOCK:
        print("📌 Using MOCK data (for development/testing)")
        from mock_calendar import load_mock_calendar
        calendar = load_mock_calendar()
        monitor = get_monitor()
        monitor.calendar = calendar
    else:
        # Initialize monitor
        monitor = get_monitor(quiet_minutes=30, importance_threshold="medium")
        
        # Refresh calendar from Forex Factory
        success = monitor.refresh_calendar()
        if not success:
            print("❌ Failed to refresh calendar")
            return

    symbols = load_symbols()
    
    # Print market status
    print("\n📊 Current Market Status:")
    monitor.print_status(symbols)
    
    # Check specific symbol
    symbol = "EURUSD"
    can_trade, reason = monitor.can_trade_symbol(symbol)
    print(f"\n🔍 {symbol}: {'✅ OK to trade' if can_trade else '❌ ' + reason}")


def example_2_filter_symbols():
    """Example 2: Filter symbols list for trading."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Filter Symbols for Safe Trading")
    print("="*60)
    
    settings = load_settings()
    symbols = load_symbols()
    
    monitor = get_monitor(
        quiet_minutes=30,
        importance_threshold="medium"
    )
    
    # Use mock data if available
    if USE_MOCK:
        print("📌 Using MOCK data")
        from mock_calendar import load_mock_calendar
        monitor.calendar = load_mock_calendar()
    else:
        monitor.refresh_calendar()
    
    # Get trading restrictions
    restrictions = monitor.get_trading_restrictions(symbols)
    
    print(f"\n📋 Analyzing {len(symbols)} symbols...")
    
    if restrictions["high"]:
        print(f"\n🔴 HIGH IMPACT - DO NOT TRADE:")
        for sym in restrictions["high"]:
            print(f"   • {sym}")
    
    if restrictions["medium"]:
        print(f"\n🟡 MEDIUM IMPACT - CAUTION:")
        for sym in restrictions["medium"]:
            print(f"   • {sym}")
    
    # Filter for safe trading
    safe_symbols = monitor.filter_tradeable_symbols(symbols)
    
    print(f"\n✅ SAFE TO TRADE ({len(safe_symbols)}/{len(symbols)}):")
    for sym in safe_symbols[:10]:  # Show first 10
        print(f"   • {sym}")
    
    if len(safe_symbols) > 10:
        print(f"   ... and {len(safe_symbols) - 10} more")


def example_3_upcoming_events():
    """Example 3: Show upcoming economic events."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Upcoming Economic Events")
    print("="*60)
    
    monitor = get_monitor(quiet_minutes=30, importance_threshold="low")
    
    # Use mock data if available
    if USE_MOCK:
        print("📌 Using MOCK data")
        from mock_calendar import load_mock_calendar
        monitor.calendar = load_mock_calendar()
    else:
        monitor.refresh_calendar()
    
    # Get upcoming events
    upcoming = monitor.calendar.get_upcoming_events(hours_ahead=24)
    
    print(f"\n📅 Next 24 hours - {len(upcoming)} events:\n")
    
    for i, event in enumerate(upcoming[:10], 1):  # Show top 10
        time_str = event.time.strftime("%H:%M UTC")
        importance_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }.get(event.importance, "⚪")
        
        print(f"{i}. {importance_emoji} {time_str} | {event.country:3} | {event.event_name}")
    
    if len(upcoming) > 10:
        print(f"\n... and {len(upcoming) - 10} more events")


def example_4_specific_symbol_events():
    """Example 4: Get all events for specific symbol."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Events for Specific Symbols")
    print("="*60)
    
    monitor = get_monitor(quiet_minutes=30, importance_threshold="low")
    
    # Use mock data if available
    if USE_MOCK:
        print("📌 Using MOCK data")
        from mock_calendar import load_mock_calendar
        monitor.calendar = load_mock_calendar()
    else:
        monitor.refresh_calendar()
    
    symbols_to_check = ["EURUSD", "GBPUSD", "USDJPY"]
    
    for symbol in symbols_to_check:
        events = monitor.calendar.get_events_for_symbol(symbol)
        
        print(f"\n{symbol}: {len(events)} events")
        
        for event in events[:3]:  # Show top 3
            time_str = event.time.strftime("%H:%M UTC")
            importance_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(event.importance, "⚪")
            
            print(f"  {importance_emoji} {time_str} | {event.event_name}")
        
        if len(events) > 3:
            print(f"  ... and {len(events) - 3} more")


def example_5_custom_thresholds():
    """Example 5: Use different thresholds for different strategies."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Custom Thresholds for Different Strategies")
    print("="*60)
    
    settings = load_settings()
    symbols = load_symbols()
    
    strategies = {
        "intraday": {
            "quiet_minutes": 30,
            "importance_threshold": "low"  # React to all events
        },
        "swing": {
            "quiet_minutes": 60,
            "importance_threshold": "medium"  # Only medium+ events
        },
        "invest": {
            "quiet_minutes": 120,
            "importance_threshold": "high"  # Only high impact events
        }
    }
    
    print(f"\n📊 Filtering {len(symbols)} symbols for different strategies:\n")
    
    for strategy_name, params in strategies.items():
        monitor = get_monitor(
            quiet_minutes=params["quiet_minutes"],
            importance_threshold=params["importance_threshold"]
        )
        
        # Use mock data if available
        if USE_MOCK:
            from mock_calendar import load_mock_calendar
            monitor.calendar = load_mock_calendar()
        else:
            monitor.refresh_calendar()
        
        safe_symbols = monitor.filter_tradeable_symbols(symbols)
        blocked = len(symbols) - len(safe_symbols)
        
        print(f"{strategy_name.upper():10} | Safe: {len(safe_symbols):2} | Blocked: {blocked:2}")


def example_6_integration_with_pipeline():
    """Example 6: Integration with trading pipeline."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Integration with Trading Pipeline")
    print("="*60)
    
    from src.pipeline import run_daily
    
    print("\nThis example shows how market monitor integrates with the pipeline.")
    print("When you call run_daily() or run_all(), the economic calendar is")
    print("automatically applied if enabled in config/settings.yaml\n")
    
    settings = load_settings()
    
    if settings.get("economic_calendar", {}).get("enabled"):
        print("✅ Economic Calendar is ENABLED in settings.yaml")
        print("\nThe pipeline will automatically:")
        print("1. Refresh the economic calendar")
        print("2. Filter symbols based on current events")
        print("3. Report blocked symbols in results")
        
        # You would normally call:
        # result = run_daily(settings)
        # This would include market monitor info in the result
        
    else:
        print("⚠️  Economic Calendar is DISABLED in settings.yaml")
        print("\nTo enable it, update config/settings.yaml:")
        print("""
economic_calendar:
  enabled: true
  sources:
    - forex_factory
    - myfxbook
  trading_restrictions:
    enabled: true
    quiet_minutes: 30
    importance_threshold: medium
""")


def main():
    """Run all examples."""
    examples = [
        ("Basic Monitoring", example_1_basic_monitoring),
        ("Filter Symbols", example_2_filter_symbols),
        ("Upcoming Events", example_3_upcoming_events),
        ("Symbol Events", example_4_specific_symbol_events),
        ("Custom Thresholds", example_5_custom_thresholds),
        ("Pipeline Integration", example_6_integration_with_pipeline),
    ]
    
    print("\n" + "="*60)
    print("ECONOMIC CALENDAR AGENT - EXAMPLES")
    if USE_MOCK:
        print("⚠️  RUNNING WITH MOCK DATA (no internet required)")
    else:
        print("🌐 Running with live data from Forex Factory")
    print("="*60)
    
    for i, (name, example_func) in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in example {i} ({name}): {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Examples completed!")
    if USE_MOCK:
        print("💡 For REAL data, agent will fetch from internet when needed")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
