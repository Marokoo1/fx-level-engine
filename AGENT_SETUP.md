# 🤖 Economic Calendar Agent - Implementation Summary

**Status:** ✅ Kompletně implementováno a připraveno k použití  
**Datum:** 2026-03-28  
**Autor:** Economic Calendar Agent Setup

---

## 📦 Co bylo vytvořeno

### 1. **src/economic_calendar.py** (500+ řádků)
Hlavní agent pro správu ekonomických eventů.

**Klíčové třídy:**
- `EconomicEvent` - Dataclass pro jednu ekonomickou zprávu
- `EconomicCalendar` - Agent pro stahování a správu eventů

**Hlavní funkce:**
- `fetch_forex_factory()` - Stahuje data z Forex Factory web scrapingem
- `fetch_trading_economics()` - Volitelné obohacení dat přes API klíč
- `fetch_myfxbook()` - Legacy fallback, nedoporučený jako default
- `get_blocked_symbols()` - Vrací symboly v "quiet period" (k blokování)
- `get_upcoming_events()` - Nadcházející eventy
- `get_events_for_symbol()` - Eventy pro konkrétní symbol
- Automatické cachování (4 hodiny TTL)

### 2. **src/market_monitor.py** (300+ řádků)
Integrační vrstva - Market Monitor pro trading pipeline.

**Klíčové třídy:**
- `MarketMonitor` - Integruje ekonomický kalendář s obchodním pipeline

**Hlavní funkce:**
- `refresh_calendar()` - Obnoví kalendář z internetu
- `can_trade_symbol(symbol)` - Kontrola jestli je symbol bezpečný
- `filter_tradeable_symbols(symbols)` - Filtrování seznamu párů
- `get_market_status()` - Status informace
- `get_trading_restrictions()` - Detailní seznam blokovaných párů

### 3. **config/settings.yaml** (aktualizáno)
Přidána konfigurace pro agent:

```yaml
economic_calendar:
  enabled: true
  sources: [forex_factory]
  cache_ttl_hours: 4
  
  trading_restrictions:
    enabled: true
    quiet_minutes: 30           # Blokování 30 minut před/po eventu
    importance_threshold: medium # Low/Medium/High
```

### 4. **src/pipeline.py** (aktualizováno)
Integrována automatická filtrování ekonomickým kalendářem:

```python
# V run_daily() a run_all() je nyní automaticky:
# 1. Refresh ekonomického kalendáře
# 2. Filtrování symbolů pro bezpečné obchodování
# 3. Reportování blokovaných párů
```

### 5. **docs/ECONOMIC_CALENDAR_AGENT.md** (800+ řádků)
Kompletní dokumentace:
- Plán a cíle
- Příklady kódu
- Konfigurace
- Integrace s projektem
- Zdroje dat
- Možná rozšíření

### 6. **example_economic_calendar.py** (400+ řádků)
6 praktických příkladů:
1. Základní monitoring
2. Filtrování symbolů
3. Nadcházející eventy
4. Eventy pro konkrétní symboly
5. Vlastní thresholdy pro různé strategie
6. Integrace s pipeline

### 7. **requirements.txt** (aktualizáno)
Přidány závislosti:
```
requests>=2.28.0
beautifulsoup4>=4.11.0
```

---

## 🚀 Jak používat

### Základní použití (nejjednoduší)

1. **Povolit v config/settings.yaml:**
```yaml
economic_calendar:
  enabled: true
```

2. **Agent se používá automaticky:**
```python
from src.pipeline import run_daily

# Při zavolání se automaticky:
# - Stáhne ekonomický kalendář
# - Filtruje symboly (blokuje při events)
# - Hlásí status
result = run_daily()

# result bude obsahovat:
# {
#   "downloaded": {...},
#   "rows": 1234,
#   "exported": {...},
#   "market_monitor": {
#     "status": "OK",
#     "original_symbols": 14,
#     "filtered_symbols": 12,
#     "blocked_by_high_impact": ["EURUSD", "GBPUSD"],
#     "upcoming_events_24h": 5,
#   }
# }
```

### Pokročilé použití

```python
from src.market_monitor import get_monitor
from src.config_loader import load_symbols

# Vytvoření monitoru
monitor = get_monitor(quiet_minutes=30, importance_threshold="medium")

# Refresh kalendáře
monitor.refresh_calendar()

# Kontrola symbolu
can_trade, reason = monitor.can_trade_symbol("EURUSD")

# Filtrování seznamu
safe_symbols = monitor.filter_tradeable_symbols(load_symbols())

# Status
monitor.print_status()
```

### Spuštění příkladů

```bash
# Aktivuj venv
& .\.venv\Scripts\Activate.ps1

# Spusť příklady
python example_economic_calendar.py
```

---

## 📊 Výstup / Status

Při každém spuštění uvidíš:

```
============================================================
📊 MARKET STATUS
============================================================
Calendar: ready
🔴 HIGH IMPACT blocked: EURUSD, GBPUSD
🟡 MEDIUM blocked: AUDUSD
🟢 LOW blocked: NZDUSD
Upcoming events (24h): 8
Next event: 2026-03-28T14:30:00+00:00
============================================================
```

---

## 🔧 Konfigurace

### Různá nastavení pro různé strategie:

**Intraday (agresivní, reaktivní):**
```yaml
economic_calendar:
  trading_restrictions:
    quiet_minutes: 30
    importance_threshold: low  # Reaguj na všechny
```

**Swing (středně konzervativní):**
```yaml
economic_calendar:
  trading_restrictions:
    quiet_minutes: 60
    importance_threshold: medium
```

**Invest (velmi konzervativní):**
```yaml
economic_calendar:
  trading_restrictions:
    quiet_minutes: 120
    importance_threshold: high  # Jen velké eventy
```

---

## 📋 Zdroje dat

### Forex Factory (Default)
- **URL:** https://www.forexfactory.com/calendar.php
- **Metoda:** Web scraping
- **Výhody:** Nejpoužívanější, nezbytný žádný API klíč
- **Nevýhody:** HTML parsing není 100% spolehlivý

### Trading Economics (Optional)
- **URL:** https://api.tradingeconomics.com/calendar
- **Metoda:** REST API
- **Potřeba:** API klíč (z env proměnné `TRADING_ECONOMICS_API_KEY`)
- **Výhody:** Strukturované data, vhodné jako volitelný doplněk

---

## 🧪 Testování

```bash
# Test stahování
python -c "from src.economic_calendar import get_calendar; cal = get_calendar(); print(cal.fetch_forex_factory())"

# Test integrace
python example_economic_calendar.py

# Test pipeline s agentem
python -m src.main --mode run-daily
```

**Očekávaný výstup:** Filtrované symboly, status ekonomických eventů v logu.

---

## 📁 Struktura souborů

```
fx-level-engine/
├── src/
│   ├── economic_calendar.py     ✨ NEW - Agent
│   ├── market_monitor.py        ✨ NEW - Integrator
│   ├── pipeline.py              ✅ UPDATED - Integrován
│   ├── main.py                  (bez změn, ale nyní filtruje symboly)
│   └── ... ostatní soubory
├── config/
│   └── settings.yaml            ✅ UPDATED
├── docs/
│   ├── ECONOMIC_CALENDAR_AGENT.md  ✨ NEW - Dokumentace
│   └── ... ostatní docs
├── example_economic_calendar.py  ✨ NEW - Příklady
├── requirements.txt             ✅ UPDATED
└── ... ostatní soubory
```

---

## ✅ Checklist - Co je hotovo

- [x] **Economic Calendar Agent** - Stahuje z Forex Factory
- [x] **Market Monitor** - Integruje s pipeline
- [x] **Automatické filtrování** - Symboly se filtrují při run_daily/run_all
- [x] **Caching** - 4 hodiny TTL pro ekonomické eventy
- [x] **Konfigurace** - Nastavitelné v settings.yaml
- [x] **Dokumentace** - Kompletní README s příklady
- [x] **Příklady** - 6 praktických příkladů
- [x] **Integrace s pipeline** - run_daily/run_all automaticky filtrují
- [x] **Error handling** - Fallback na Forex Factory
- [x] **Logging** - Detailní informace v logu

---

## 🚧 Možná budoucí rozšíření

1. **Real-time Updates** - WebSocket pro živé aktualizace
2. **Machine Learning** - Predikce dopadů eventů
3. **Historical Analysis** - Jak se trh choval v minulosti
4. **Notifications** - Telegram/Email alerts
5. **Advanced Filtering** - Custom importance ratings
6. **Correlation Analysis** - Detekce korelovaných párů

---

## 🔗 Jak se to všechno propojuje

```
Internet (Forex Factory / Trading Economics)
    ↓
economic_calendar.py (EconomicCalendar agent)
    ↓
Cache: data/state/economic_events.json
    ↓
market_monitor.py (MarketMonitor)
    ↓
pipeline.py: run_daily() / run_all()
    ↓
Filtrované symboly → Trading pipeline
```

---

## 💡 Tips & Tricks

1. **Ruční refresh:** `monitor.refresh_calendar()`
2. **Debug mode:** Zvýšit log level na DEBUG
3. **Offline:** Agent se rozpadne na cahned data (4 hodiny)
4. **Custom threshold:** `get_monitor(quiet_minutes=60, importance_threshold="high")`
5. **Sledování symbolu:** `calendar.get_events_for_symbol("EURUSD")`

---

## ❓ FAQ

**Q: Co se stane když nefunguje internet?**  
A: Agent použije cached data (do 4 hodin). Pokud cache je stará, pak agent vypíše warning a pokračuje bez filtrování.

**Q: Jak dlouho trvá stahování?**  
A: Forex Factory ~2-5 sekund. Trading Economics závisí na API klíči. Cache se používá primárně (pokud je platný).

**Q: Mohu vypnout agenta?**  
A: Ano, nastavit `economic_calendar.enabled: false` v settings.yaml. Pipeline pak nefiltruje symboly.

**Q: Jak přidat vlastní zdroj dat?**  
A: Rozšířit `EconomicCalendar` třidu s novou metodou `fetch_custom_source()`.

---

## 📞 Kontakt / Support

Pokud se vyskytne problém:

1. Zkontroluj logs (DEBUG level)
2. Zkontroluj internet spojení
3. Zkontroluj settings.yaml
4. Spusť `example_economic_calendar.py` pro diagnostiku

---

**Implementace hotova! Agent je připraven k использованию.** ✅

