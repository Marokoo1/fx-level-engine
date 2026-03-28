# Economic Calendar Agent

Autonomní agent pro stahování a správu forex ekonomického kalendáře. Agent se integruje s obchodním pipeline a dočasně blokuje obchodování na měnových párech během vyhlašování ekonomických zpráv.

## 🎯 Cíl

- Automaticky stahovat ekonomické eventy z Trading Economics a volitelně z Forex Factory
- Detekovat nadcházející vyhlášení zpráv
- Blokovat obchodování na dotčených měnových párech během "quiet hours"
- Integrace s existujícím pipeline

## 📋 Komponenty

### 1. `economic_calendar.py` - Economic Calendar Agent

Hlavní agent pro správu ekonomických eventů.

**Hlavní třídy:**

- `EconomicEvent` - Dataclass reprezentující jednu ekonomickou zprávu
- `EconomicCalendar` - Agent pro stahování a správu eventů

**Klíčové metody:**

```python
from src.economic_calendar import get_calendar

# Vytvoření/získání calendar instance
calendar = get_calendar()

# Aktualizace z internetu
calendar.update(sources=["trading_economics"])

# Seznamy symbolů v "quiet period"
blocked = calendar.get_blocked_symbols(quiet_minutes=30, importance_threshold="medium")

# Nadcházející eventy
upcoming = calendar.get_upcoming_events(hours_ahead=24)

# Eventy pro konkrétní symbol
events = calendar.get_events_for_symbol("EURUSD")
```

### 2. `market_monitor.py` - Market Monitor (Integrator)

Integruje ekonomický kalendář s obchodním pipeline. Poskytuje rozhodovací podporu.

**Klíčové metody:**

```python
from src.market_monitor import get_monitor

# Vytvoření market monitoru
monitor = get_monitor(
    quiet_minutes=30,
    importance_threshold="medium"
)

# Refresh kalendáře
monitor.refresh_calendar()

# Kontrola konkrétního symbolu
can_trade, reason = monitor.can_trade_symbol("EURUSD")

# Filtrování seznamu symbolů
safe_symbols = monitor.filter_tradeable_symbols(
    ["EURUSD", "GBPUSD", "USDJPY"],
    min_importance="medium"
)

# Status zprávě
status_dict = monitor.get_market_status()
monitor.print_status()  # Log output
```

## 🔧 Konfiguracja

Přidán do `config/settings.yaml`:

```yaml
economic_calendar:
  enabled: true
  sources:
    - trading_economics  # Live Trading Economics calendar
    # - forex_factory     # Legacy fallback
  cache_ttl_hours: 4     # Jak dlouho se cache drží
  
  trading_restrictions:
    enabled: true
    quiet_minutes: 30    # Minut před/po eventu pro blokování
    importance_threshold: medium  # Jakou úroveň blokovat
```

## 💻 Příklady Používání

### Příklad 1: Aktualizace kalendáře a kontrola symbolů

```python
from src.market_monitor import get_monitor

# Inicializace monitoru
monitor = get_monitor(quiet_minutes=30, importance_threshold="medium")

# Refresh kalendáře z internetu (Trading Economics)
monitor.refresh_calendar()

# Kontrola konkrétního symbolu
can_trade, reason = monitor.can_trade_symbol("EURUSD")
if not can_trade:
    print(f"❌ Nelze obchodovat EURUSD: {reason}")
else:
    print(f"✅ EURUSD je volný k obchodování")

# Filtrování seznamu obchodních párů
all_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
safe_symbols = monitor.filter_tradeable_symbols(all_symbols)
print(f"Bezpečné k obchodování: {safe_symbols}")
```

### Příklad 2: Integrační use-case v pipeline

```python
# V pipeline.py nebo main.py
from src.market_monitor import get_monitor
from src.config_loader import load_settings, load_symbols

settings = load_settings()
symbols = load_symbols()

# Inicializace
monitor = get_monitor(
    quiet_minutes=settings["economic_calendar"]["trading_restrictions"]["quiet_minutes"],
    importance_threshold=settings["economic_calendar"]["trading_restrictions"]["importance_threshold"]
)

# Refresh kalendáře
if settings["economic_calendar"]["enabled"]:
    monitor.refresh_calendar()
    monitor.print_status()
    
    # Filtrování symbolů pro obchodování
    safe_symbols = monitor.filter_tradeable_symbols(symbols)
    
    # Pokračuj s bezpečnými symboly
    run_trading_pipeline(safe_symbols, settings)
```

### Příklad 3: Scheduler integrace

```python
import schedule
from src.market_monitor import get_monitor

monitor = get_monitor()

def refresh_calendar():
    """Refresh ekonomického kalendáře každou hodinu."""
    monitor.refresh_calendar()
    monitor.print_status()

# Refresh každou hodinu
schedule.every().hour.do(refresh_calendar)

# Refresh každý den v 22:00 UTC (refresh data pro příští den)
schedule.every().day.at("22:00").do(refresh_calendar)
```

### Příklad 4: Event listening a alerting

```python
from src.economic_calendar import get_calendar
from datetime import datetime, timezone, timedelta

calendar = get_calendar()
calendar.update()

# Najdi nadcházející eventy
upcoming = calendar.get_upcoming_events(hours_ahead=4)

for event in upcoming:
    time_until = (event.time - datetime.now(timezone.utc)).total_seconds() / 60
    importance_icon = "🔴" if event.importance == "high" else "🟡" if event.importance == "medium" else "🟢"
    
    if time_until > 0:
        print(f"{importance_icon} Za {time_until:.0f} minut: {event.country} {event.event_name}")
```

## 🌐 Zdroje Dat

### Forex Factory
- **URL:** https://www.forexfactory.com/calendar.php
- **Metoda:** Web scraping (HTML parsing)
- **Výhody:** Nejpoužívanější, nejspolehlivější
- **Nevýhody:** Bez oficiálního API, web scraping není 100% spolehlivý

### Trading Economics API
- **URL:** https://api.tradingeconomics.com/calendar
- **Metoda:** REST API (vyžaduje API klíč)
- **Výhody:** Spolehlivý, strukturované data
- **Nevýhody:** Vyžaduje registraci a API token

## 🔌 Instalace Závislostí

Agent vyžaduje:
- `requests` - pro HTTP requesty
- `beautifulsoup4` - pro HTML parsing (volitelně)

```bash
pip install requests beautifulsoup4
```

Nebo přidej do `requirements.txt`:
```
requests>=2.28.0
beautifulsoup4>=4.11.0
```

## 🧪 Testování

```python
# Test 1: Stahování z Forex Factory bez BeautifulSoup (fallback)
from src.economic_calendar import get_calendar

cal = get_calendar()
events = cal.fetch_forex_factory()
print(f"Staženo {len(events)} eventů")

# Test 2: Kontrola caching
print(f"Cached events: {len(cal.events)}")

# Test 3: Get blocked symbols
blocked = cal.get_blocked_symbols(quiet_minutes=30, importance_threshold="high")
print(f"Blokované (high impact): {blocked}")
```

## ⚙️ Konfigurace pro Váš Projekt

### Doporučená nastavení:

```yaml
# Pro intraday trading (agresivní - reaguj na všechny eventy)
economic_calendar:
  trading_restrictions:
    quiet_minutes: 30
    importance_threshold: low

# Pro swing trading (konzervativnější)
economic_calendar:
  trading_restrictions:
    quiet_minutes: 60
    importance_threshold: medium

# Pro invest trading (jen vysoká dopad)
economic_calendar:
  trading_restrictions:
    quiet_minutes: 120
    importance_threshold: high
```

## 📊 Market Status Output

```
============================================================
📊 MARKET STATUS
============================================================
Calendar: ready
🔴 HIGH IMPACT blocked: EURUSD, GBPUSD
🟡 MEDIUM blocked: AUDUSD, NZDUSD
🟢 LOW blocked: CADJPY
Upcoming events (24h): 8
Next event: 2026-03-28T14:30:00+00:00
============================================================
```

## 🚀 Další Rozšíření

### Možná vylepšení:
1. **Real-time WebSocket** - Live aktualizace eventů
2. **Machine Learning** - Predikce dopadů eventů na volatilitu
3. **Historical Analysis** - Analýza jak se trh choval v minulosti během podobných eventů
4. **Telegram/Email Alerts** - Notifikace před důležitými eventy
5. **Event Impact Rating** - Custom rating systém pro váš styl obchodování
6. **Symbol Correlation** - Automatická detekce korelovaných párů (např. EURUSD a GBPUSD)

## 📝 Poznámky

- **Cache** se ukládá do `data/state/economic_events.json`
- **TTL** (time-to-live) slouží aby se data neaktualizovala příliš často
- **Timezone** - všechny časy jsou v UTC pro konzistenci
- **Importance levels** - Low < Medium < High (pro blokování se používá threshold)

## 🔗 Integrace s Existujícím Kódem

Agent se integruje do:
1. `config_loader.py` - načítání konfigurace
2. `pipeline.py` - filtrování symbolů před obchodováním
3. `scheduler.py` - scheduling refreshů kalendáře
4. `main.py` - CLI rozhraní pro status checks

---

**Status:** ✅ Připraveno k používání
**Autor:** Economic Calendar Agent
**Datum:** 2026-03-28
