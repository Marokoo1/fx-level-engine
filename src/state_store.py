from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from src.models import Level


class StateStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_levels(self, strategy: str, instrument: str, levels: list[Level]) -> Path:
        path = self.base_dir / f"{strategy}_{instrument}_levels.json"
        payload = [asdict(level) for level in levels]
        path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
        return path
