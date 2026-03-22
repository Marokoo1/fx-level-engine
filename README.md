# fx-level-engine

Python projekt pro výpočet a správu FX levelů založených na Market Profile / volume-at-price logice.

## Vrstvy systému

- intraday: build z M30, entry na M1
- swing: build z H4, entry z M30/H1
- invest: build z D1, entry z H4

## První cíl

- stáhnout historická data z IB/TWS
- uložit data do Parquetu
- připravit základ pro M30 intraday level engine
- připravit základ pro paper execution

## Instalace

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Spuštění

```bash
python -m src.main --mode download-data --strategy all --timeframes M1 M30 H4 D1 --bars 500
```

## Poznámka

První verze projektu je zaměřená na datovou vrstvu a bootstrap architektury. Exekuce do TWS přijde až v další fázi.
