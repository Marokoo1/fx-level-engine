"""
Economic Calendar Agent - Fetches and manages forex economic events.
Integrates with Trading Economics and optional external sources.
Uses Playwright for JavaScript-heavy sites when available.
"""

from __future__ import annotations

import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
import re

logger = logging.getLogger(__name__)

_FX_CURRENCY_ALIASES: dict[str, list[str]] = {
    "US": ["USD"],
    "USA": ["USD"],
    "UNITED STATES": ["USD"],
    "UNITED STATES OF AMERICA": ["USD"],
    "EU": ["EUR"],
    "EUROZONE": ["EUR"],
    "EURO AREA": ["EUR"],
    "EURO ZONE": ["EUR"],
    "EUROPEAN UNION": ["EUR"],
    "GB": ["GBP"],
    "UK": ["GBP"],
    "UNITED KINGDOM": ["GBP"],
    "GREAT BRITAIN": ["GBP"],
    "JAPAN": ["JPY"],
    "JP": ["JPY"],
    "AU": ["AUD"],
    "AUSTRALIA": ["AUD"],
    "NZ": ["NZD"],
    "NEW ZEALAND": ["NZD"],
    "CA": ["CAD"],
    "CANADA": ["CAD"],
    "CH": ["CHF"],
    "SWITZERLAND": ["CHF"],
}


def _normalize_lookup(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).upper().replace("-", " ").split())


def _normalize_fx_symbol(symbol: str | None) -> str:
    if not symbol:
        return ""
    return re.sub(r"[^A-Z]", "", str(symbol).upper())


def _infer_affected_currencies(value: str | None) -> list[str]:
    """
    Infer currency codes from a source-specific currency/country label.

    Examples:
    - "USD" -> ["USD"]
    - "United States" -> ["USD"]
    - "EUR/USD" -> ["EUR", "USD"]
    """
    lookup = _normalize_lookup(value)
    if not lookup:
        return []

    if lookup in _FX_CURRENCY_ALIASES:
        return _FX_CURRENCY_ALIASES[lookup]

    compact = _normalize_fx_symbol(lookup)
    if len(compact) == 3:
        return [compact]
    if len(compact) == 6:
        return [compact[:3], compact[3:]]
    return []


def _symbol_currencies(symbol: str | None) -> set[str]:
    compact = _normalize_fx_symbol(symbol)
    if len(compact) == 3:
        return {compact}
    if len(compact) == 6:
        return {compact[:3], compact[3:]}
    return set()

# Try to import Playwright (optional dependency)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class EconomicEvent:
    """Represents a single economic event."""
    time: datetime
    symbol: str
    country: str
    event_name: str
    importance: str  # "low", "medium", "high"
    forecast: Optional[str] = None
    previous: Optional[str] = None
    actual: Optional[str] = None
    source: str = "forex_factory"
    affected_currencies: Optional[list[str]] = None
    
    def is_active_now(self, quiet_minutes: int = 30) -> bool:
        """Check if event is active (within quiet_minutes before and after)."""
        now = datetime.now(timezone.utc)
        time_utc = self.time if self.time.tzinfo else self.time.replace(tzinfo=timezone.utc)
        time_utc = time_utc.astimezone(timezone.utc)
        
        before = time_utc - timedelta(minutes=quiet_minutes)
        after = time_utc + timedelta(minutes=quiet_minutes)
        
        return before <= now <= after

    def currency_set(self) -> set[str]:
        """Return affected currencies for matching against FX pairs."""
        currencies = [c.upper() for c in (self.affected_currencies or []) if c]
        if currencies:
            return set(currencies)
        return set(_infer_affected_currencies(self.symbol))

    def affects_symbol(self, symbol: str) -> bool:
        """
        Check whether this event should affect a specific FX symbol.

        Matches either:
        - exact pair match
        - one of the pair currencies is listed in affected_currencies
        - the event symbol itself represents a currency code that is part of the pair
        """
        symbol_upper = _normalize_fx_symbol(symbol)
        if not symbol_upper:
            return False

        event_symbol = _normalize_fx_symbol(self.symbol)
        if event_symbol and event_symbol == symbol_upper:
            return True

        if event_symbol and event_symbol in _symbol_currencies(symbol):
            return True

        return bool(self.currency_set() & _symbol_currencies(symbol))


class EconomicCalendar:
    """Main agent for fetching and managing economic calendar data."""
    
    def __init__(self, cache_dir: Path = Path("data/state"), cache_ttl_hours: int = 4):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "economic_events.json"
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.events: list[EconomicEvent] = []
        self._load_cache()
    
    def set_events_from_list(self, events: list[EconomicEvent]) -> None:
        """Directly set events (for testing/manual updates)."""
        self.events = events
        self._save_cache()
        
    def _load_cache(self) -> None:
        """Load events from cache if valid."""
        if not self.cache_file.exists():
            return
            
        try:
            stat = self.cache_file.stat()
            age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
            
            if age > self.cache_ttl:
                logger.info(f"Cache expired (age={age})")
                return
            
            with open(self.cache_file, "r") as f:
                data = json.load(f)
                self.events = [
                    EconomicEvent(
                        time=datetime.fromisoformat(e["time"]),
                        symbol=e["symbol"],
                        country=e["country"],
                        event_name=e["event_name"],
                        importance=e["importance"],
                        forecast=e.get("forecast"),
                        previous=e.get("previous"),
                        actual=e.get("actual"),
                        source=e.get("source", "forex_factory"),
                        affected_currencies=e.get("affected_currencies") or e.get("currencies") or _infer_affected_currencies(e.get("symbol")),
                    )
                    for e in data
                ]
                logger.info(f"Loaded {len(self.events)} events from cache")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
    
    def _save_cache(self) -> None:
        """Save events to cache."""
        try:
            with open(self.cache_file, "w") as f:
                payload = []
                for e in self.events:
                    item = asdict(e)
                    item["time"] = e.time.isoformat()
                    payload.append(item)
                json.dump(payload, f, indent=2)
                logger.info(f"Cached {len(self.events)} events")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def fetch_forex_factory(self) -> list[EconomicEvent]:
        """
        Fetch events from Forex Factory.
        Uses Playwright for JavaScript rendering if available, else fallback to requests.
        """
        # Try Playwright first (for JavaScript-rendered content)
        if PLAYWRIGHT_AVAILABLE:
            events = self._fetch_forex_factory_playwright()
            if events:
                return events
            logger.debug("Playwright fetch failed, falling back to requests")
        
        # Fallback: try requests (may not work if content is JS-rendered)
        try:
            url = "https://www.forexfactory.com/calendar.php"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Basic HTML parsing - extract events from table
            events = self._parse_forex_factory_html(response.text)
            logger.info(f"Fetched {len(events)} events from Forex Factory (requests)")
            return events
            
        except Exception as e:
            logger.error(f"Failed to fetch from Forex Factory: {e}")
            return []
    
    def _fetch_forex_factory_playwright(self) -> list[EconomicEvent]:
        """
        Fetch Forex Factory using Playwright (handles JavaScript).
        """
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        try:
            from playwright.sync_api import sync_playwright
            
            events = []
            
            with sync_playwright() as p:
                # Launch browser (headless=True means no UI window)
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set User-Agent to avoid bot detection
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                try:
                    logger.debug("Fetching Forex Factory with Playwright...")
                    page.goto("https://www.forexfactory.com/calendar.php", timeout=30000)
                    
                    # Wait for calendar table to load
                    page.wait_for_selector("tr.calendar__row", timeout=10000)
                    
                    # Get all event rows
                    rows = page.locator("tr.calendar__row").all()
                    logger.debug(f"Found {len(rows)} calendar rows")
                    
                    now = datetime.now(timezone.utc)
                    
                    for row in rows:
                        try:
                            # Extract time
                            time_text = row.locator("td.calendar__time").text_content()
                            if not time_text or time_text.strip() == "":
                                continue
                            
                            time_text = time_text.strip()
                            
                            # Parse time (format: HH:MM)
                            try:
                                event_time = datetime.strptime(time_text, "%H:%M")
                                event_time = event_time.replace(
                                    year=now.year,
                                    month=now.month,
                                    day=now.day,
                                    tzinfo=timezone.utc
                                )
                            except ValueError:
                                continue
                            
                            # Extract currency
                            currency_text = row.locator("td.calendar__currency").text_content()
                            currency = currency_text.strip() if currency_text else ""
                            
                            # Extract event name
                            event_text = row.locator("td.calendar__event").text_content()
                            event_name = event_text.strip() if event_text else ""
                            
                            # Extract importance (by checking for specific classes)
                            importance = "medium"  # default
                            try:
                                importance_elem = row.locator("span.icon")
                                class_attr = importance_elem.get_attribute("class") or ""
                                
                                if "red" in class_attr.lower():
                                    importance = "high"
                                elif "orange" in class_attr.lower():
                                    importance = "medium"
                                else:
                                    importance = "low"
                            except:
                                pass
                            
                            if currency and event_name:
                                affected_currencies = _infer_affected_currencies(currency)
                                event_symbol = affected_currencies[0] if affected_currencies else currency
                                event = EconomicEvent(
                                    time=event_time,
                                    symbol=event_symbol,
                                    country=currency,
                                    event_name=event_name,
                                    importance=importance,
                                    affected_currencies=affected_currencies,
                                    source="forex_factory"
                                )
                                events.append(event)
                                
                        except Exception as e:
                            logger.debug(f"Failed to parse row: {e}")
                            continue
                    
                    logger.info(f"Fetched {len(events)} events from Forex Factory (Playwright)")
                    return events
                    
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"Playwright fetch failed: {e}")
            return []
    
    def _parse_forex_factory_html(self, html: str) -> list[EconomicEvent]:
        """Parse Forex Factory HTML response."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup4 not installed, skipping HTML parsing")
            return []
        
        events = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Forex Factory uses specific table structure
            rows = soup.find_all("tr", class_="calendar__row")
            
            for row in rows:
                try:
                    # Extract time
                    time_elem = row.find("td", class_="calendar__time")
                    if not time_elem:
                        continue
                    
                    time_str = time_elem.get_text(strip=True)
                    if not time_str or time_str == "":
                        continue
                    
                    # Parse time (Forex Factory shows in server time, usually EST)
                    try:
                        event_time = datetime.strptime(time_str, "%H:%M")
                        event_time = event_time.replace(
                            year=datetime.now().year,
                            month=datetime.now().month,
                            day=datetime.now().day,
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        continue
                    
                    # Extract currency
                    currency_elem = row.find("td", class_="calendar__currency")
                    currency = currency_elem.get_text(strip=True) if currency_elem else ""
                    
                    # Extract event name
                    event_elem = row.find("td", class_="calendar__event")
                    event_name = event_elem.get_text(strip=True) if event_elem else ""
                    
                    # Extract importance (star rating)
                    importance_elem = row.select_one("span.icon")
                    importance = "medium"  # default
                    if importance_elem:
                        # Forex Factory uses stars for importance
                        importance_class = importance_elem.get("class", [])
                        if any("red" in c for c in importance_class):
                            importance = "high"
                        elif any("orange" in c for c in importance_class):
                            importance = "medium"
                        else:
                            importance = "low"
                    
                    if currency and event_name:
                        affected_currencies = _infer_affected_currencies(currency)
                        event_symbol = affected_currencies[0] if affected_currencies else currency
                        event = EconomicEvent(
                            time=event_time,
                            symbol=event_symbol,
                            country=currency,
                            event_name=event_name,
                            importance=importance,
                            affected_currencies=affected_currencies,
                            source="forex_factory"
                        )
                        events.append(event)
                        
                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
        
        return events
    
    def fetch_myfxbook(self, api_token: Optional[str] = None) -> list[EconomicEvent]:
        """
        Fetch events from myfxbook API.
        Requires API token: https://www.myfxbook.com/api/get-economic-calendar
        """
        if not api_token:
            logger.debug("Skipping myfxbook fetch (no API token)")
            return []
        
        try:
            url = "https://api.myfxbook.com/api/get-economic-calendar"
            params = {"token": api_token}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                logger.warning(f"myfxbook API error: {data}")
                return []
            
            events = []
            for event_data in data.get("events", []):
                try:
                    source_label = (
                        event_data.get("Currency")
                        or event_data.get("currency")
                        or event_data.get("Country")
                        or event_data.get("country")
                        or ""
                    )
                    affected_currencies = _infer_affected_currencies(source_label)
                    event_symbol = affected_currencies[0] if affected_currencies else _normalize_lookup(source_label) or "UNKNOWN"

                    raw_time = event_data.get("date") or event_data.get("Date")
                    if raw_time is None:
                        continue
                    try:
                        event_time = datetime.fromtimestamp(int(raw_time), tz=timezone.utc)
                    except (TypeError, ValueError):
                        try:
                            event_time = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
                        except ValueError:
                            continue

                    importance_raw = str(event_data.get("impact", "medium")).strip().lower()
                    if importance_raw not in {"low", "medium", "high"}:
                        importance_raw = "medium"

                    event = EconomicEvent(
                        time=event_time,
                        symbol=event_symbol,
                        country=str(event_data.get("country") or event_data.get("Country") or source_label),
                        event_name=str(event_data.get("title") or event_data.get("event") or "Economic event"),
                        importance=importance_raw,
                        forecast=event_data.get("forecast"),
                        previous=event_data.get("previous"),
                        affected_currencies=affected_currencies,
                        source="myfxbook"
                    )
                    events.append(event)
                except Exception as e:
                    logger.debug(f"Failed to parse myfxbook event: {e}")
            
            logger.info(f"Fetched {len(events)} events from myfxbook")
            return events
            
        except Exception as e:
            logger.error(f"Failed to fetch from myfxbook: {e}")
            return []
    
    def update(
        self,
        sources: list[str] | None = None,
        *,
        trading_economics_api_key: Optional[str] = None,
        myfxbook_api_token: Optional[str] = None,
    ) -> bool:
        """
        Update calendar from specified sources.

        Args:
            sources: List of sources to fetch from. Defaults to Trading Economics only.
            trading_economics_api_key: Optional API key for Trading Economics API.
            myfxbook_api_token: Optional token for legacy myfxbook support.

        Returns:
            True if at least one source was successful.
        """
        sources = [str(source).lower() for source in (sources or ["trading_economics"])]

        new_events: list[EconomicEvent] = []
        success = False

        if "forex_factory" in sources:
            events = self.fetch_forex_factory()
            if events:
                new_events.extend(events)
                success = True

        if "trading_economics" in sources:
            events = self.fetch_trading_economics(api_key=trading_economics_api_key)
            if events:
                new_events.extend(events)
                success = True

        if "myfxbook" in sources:
            events = self.fetch_myfxbook(api_token=myfxbook_api_token)
            if events:
                new_events.extend(events)
                success = True

        if new_events:
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            seen: set[tuple[str, str, str, str]] = set()
            filtered: list[EconomicEvent] = []

            for event in new_events:
                if event.time <= cutoff:
                    continue

                key = (
                    event.time.astimezone(timezone.utc).isoformat(),
                    _normalize_lookup(event.symbol),
                    _normalize_lookup(event.event_name),
                    event.source,
                )
                if key in seen:
                    continue
                seen.add(key)
                filtered.append(event)

            self.events = sorted(filtered, key=lambda event: event.time)
            self._save_cache()

        return success

    def fetch_trading_economics(self, api_key: Optional[str] = None) -> list[EconomicEvent]:
        """
        Fetch events from Trading Economics API or public calendar page.

        API docs: https://docs.tradingeconomics.com/
        """
        if not api_key:
            logger.debug("No Trading Economics API key provided; using public calendar page")
            return self._fetch_trading_economics_web()

        try:
            url = "https://api.tradingeconomics.com/calendar"
            params = {"c": api_key}

            logger.debug("Fetching from Trading Economics API...")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Unexpected Trading Economics payload: {type(data)}")
                return []

            events: list[EconomicEvent] = []

            for item in data:
                try:
                    event_time_str = item.get("Date") or item.get("date")
                    event_name = str(item.get("Event") or item.get("event") or "").strip()
                    country_label = str(item.get("Country") or item.get("country") or "").strip()
                    currency_label = str(item.get("Currency") or item.get("currency") or "").strip()

                    if not event_time_str or not event_name:
                        continue

                    try:
                        event_time = datetime.fromisoformat(str(event_time_str).replace("Z", "+00:00"))
                    except ValueError:
                        continue

                    importance_raw = item.get("Importance") or item.get("importance") or item.get("Impact") or item.get("impact")
                    if str(importance_raw).isdigit():
                        importance_map = {"1": "low", "2": "medium", "3": "high"}
                        importance = importance_map.get(str(int(float(importance_raw))), "medium")
                    else:
                        importance = str(importance_raw or "").strip().lower()
                        if importance in {"1", "low"}:
                            importance = "low"
                        elif importance in {"2", "medium", "moderate"}:
                            importance = "medium"
                        elif importance in {"3", "high"}:
                            importance = "high"
                        else:
                            event_lower = event_name.lower()
                            if any(x in event_lower for x in ["interest rate", "gdp", "inflation", "employment", "fed", "ecb"]):
                                importance = "high"
                            elif any(x in event_lower for x in ["pmi", "retail", "industrial", "consumer"]):
                                importance = "medium"
                            else:
                                importance = "low"

                    affected_currencies = _infer_affected_currencies(currency_label or country_label)
                    event_symbol = affected_currencies[0] if affected_currencies else (currency_label or country_label or "UNKNOWN")

                    forecast = item.get("Forecast") or item.get("forecast")
                    previous = item.get("Previous") or item.get("previous")
                    actual = item.get("Actual") or item.get("actual")

                    events.append(
                        EconomicEvent(
                            time=event_time,
                            symbol=event_symbol,
                            country=country_label or currency_label or "UNKNOWN",
                            event_name=event_name,
                            importance=importance,
                            forecast=str(forecast) if forecast not in (None, "") else None,
                            previous=str(previous) if previous not in (None, "") else None,
                            actual=str(actual) if actual not in (None, "") else None,
                            source="trading_economics",
                            affected_currencies=affected_currencies,
                        )
                    )
                except Exception as e:
                    logger.debug(f"Failed to parse Trading Economics event: {e}")

            logger.info(f"Fetched {len(events)} events from Trading Economics")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch from Trading Economics: {e}")
            logger.debug("Falling back to Trading Economics web calendar")
            return self._fetch_trading_economics_web()

    def _fetch_trading_economics_web(self) -> list[EconomicEvent]:
        """
        Fetch events from the public Trading Economics calendar page.

        This path does not require an API key and works well for a live
        calendar snapshot with country, event name, time, and importance.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup4 not installed, skipping Trading Economics web parsing")
            return []

        try:
            url = "https://tradingeconomics.com/calendar"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select("tr[data-id]")
            events: list[EconomicEvent] = []

            importance_map = {
                "calendar-date-1": "low",
                "calendar-date-2": "medium",
                "calendar-date-3": "high",
            }

            for row in rows:
                try:
                    cells = row.find_all("td", recursive=False)
                    if len(cells) < 7:
                        continue

                    time_cell = cells[0]
                    time_span = time_cell.find("span")
                    if not time_span:
                        continue

                    date_class = None
                    for cls in time_cell.get("class", []):
                        if re.match(r"^\d{4}-\d{2}-\d{2}$", cls):
                            date_class = cls
                            break

                    if not date_class:
                        continue

                    time_text = time_span.get_text(" ", strip=True)
                    if not time_text:
                        continue

                    event_time: Optional[datetime] = None
                    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"):
                        try:
                            event_time = datetime.strptime(f"{date_class} {time_text}", fmt).replace(
                                tzinfo=timezone.utc
                            )
                            break
                        except ValueError:
                            continue

                    if event_time is None:
                        try:
                            event_time = datetime.strptime(date_class, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue

                    country_label = str(row.get("data-country") or "").strip()
                    country_cell = cells[1]
                    country_display = str(country_cell.get("title") or country_cell.get_text(" ", strip=True) or "").strip()

                    event_cell = cells[2]
                    event_link = event_cell.find("a", class_="calendar-event")
                    event_name = event_link.get_text(" ", strip=True) if event_link else event_cell.get_text(" ", strip=True)
                    event_name = event_name.strip()
                    if not event_name:
                        continue

                    actual = cells[3].get_text(" ", strip=True) or None
                    previous = cells[4].get_text(" ", strip=True) or None
                    consensus = cells[5].get_text(" ", strip=True) or None
                    forecast = consensus or (cells[6].get_text(" ", strip=True) or None)

                    importance = "low"
                    for cls in time_span.get("class", []):
                        if cls in importance_map:
                            importance = importance_map[cls]
                            break

                    affected_currencies = _infer_affected_currencies(country_label or country_display)
                    event_symbol = affected_currencies[0] if affected_currencies else _normalize_lookup(country_label or country_display) or "UNKNOWN"

                    events.append(
                        EconomicEvent(
                            time=event_time,
                            symbol=event_symbol,
                            country=country_label or country_display or "UNKNOWN",
                            event_name=event_name,
                            importance=importance,
                            forecast=forecast,
                            previous=previous,
                            actual=actual,
                            source="trading_economics",
                            affected_currencies=affected_currencies,
                        )
                    )
                except Exception as e:
                    logger.debug(f"Failed to parse Trading Economics web row: {e}")

            logger.info(f"Fetched {len(events)} events from Trading Economics web")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch from Trading Economics web page: {e}")
            return []
    
    def get_blocked_symbols(
        self,
        symbols: list[str] | None = None,
        quiet_minutes: int = 30,
        importance_threshold: str = "medium",
    ) -> list[str]:
        """
        Get list of symbols that should not be traded due to upcoming events.

        Args:
            symbols: Optional candidate symbols to filter. If omitted, returns
                event labels from the calendar itself.
            quiet_minutes: Minutes before/after event during which to block trading
            importance_threshold: Minimum importance level ("low", "medium", "high")

        Returns:
            List of symbol strings.
        """
        importance_levels = {"low": 1, "medium": 2, "high": 3}
        threshold_value = importance_levels.get(importance_threshold, 2)

        active_events = [
            event
            for event in self.events
            if importance_levels.get(event.importance, 0) >= threshold_value
            and event.is_active_now(quiet_minutes)
        ]

        if symbols is None:
            return sorted({event.symbol for event in active_events})

        blocked: list[str] = []
        for symbol in symbols:
            if any(event.affects_symbol(symbol) for event in active_events):
                blocked.append(symbol)
        return blocked
    
    def get_upcoming_events(self, hours_ahead: int = 24) -> list[EconomicEvent]:
        """
        Get upcoming events in next N hours.
        
        Args:
            hours_ahead: Number of hours to look ahead
        
        Returns:
            Sorted list of events
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours_ahead)
        
        upcoming = [e for e in self.events if now <= e.time <= cutoff]
        return sorted(upcoming, key=lambda e: e.time)
    
    def get_events_for_symbol(self, symbol: str) -> list[EconomicEvent]:
        """Get all events that can affect a specific symbol."""
        return [event for event in self.events if event.affects_symbol(symbol)]
    
    def summary_text(self) -> str:
        """Get human-readable summary of upcoming events."""
        upcoming = self.get_upcoming_events(hours_ahead=24)
        if not upcoming:
            return "No upcoming events in next 24 hours"
        
        lines = ["📅 Upcoming Economic Events (next 24h):"]
        for event in upcoming[:10]:  # Show top 10
            time_str = event.time.strftime("%H:%M UTC")
            importance_emoji = "🔴" if event.importance == "high" else "🟡" if event.importance == "medium" else "🟢"
            lines.append(f"{importance_emoji} {time_str} - {event.country} {event.event_name}")
        
        return "\n".join(lines)


def get_calendar(
    cache_dir: Path = Path("data/state"),
    cache_ttl_hours: int = 4,
) -> EconomicCalendar:
    """Factory function to get or create calendar instance."""
    return EconomicCalendar(cache_dir=cache_dir, cache_ttl_hours=cache_ttl_hours)
