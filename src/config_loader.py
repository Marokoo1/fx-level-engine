from __future__ import annotations

from pathlib import Path
import yaml

CONFIG_DIR = Path("config")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_settings() -> dict:
    return load_yaml(CONFIG_DIR / "settings.yaml")


def load_instruments() -> dict:
    return load_yaml(CONFIG_DIR / "instruments.yaml")


def load_strategy_config(strategy_name: str) -> dict:
    return load_yaml(CONFIG_DIR / f"{strategy_name}.yaml")
