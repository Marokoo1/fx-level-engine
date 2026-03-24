from __future__ import annotations

from datetime import datetime, timezone


def due_tables(now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    due = ["intraday"]
    # Weekly refresh on Monday UTC
    if now.weekday() == 0:
        due.append("swing")
        # Biweekly refresh every second ISO week
        if now.isocalendar().week % 2 == 0:
            due.append("invest")
    return due
