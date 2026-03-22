from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.models import Level


class Reporter:
    def save_levels_csv(self, path: Path, levels: list[Level]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [asdict(level) for level in levels]
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)
        return path
