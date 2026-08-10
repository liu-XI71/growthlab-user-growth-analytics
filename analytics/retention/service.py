from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import pandas as pd


def _as_date(value: date | datetime | str) -> date:
    return pd.Timestamp(value).date()


def retention_flags(
    signup_date: date | datetime | str, active_dates: Iterable[Any]
) -> dict[str, bool]:
    """Compute exact-day and D1-7 window retention flags."""
    signup = _as_date(signup_date)
    offsets = {(_as_date(item) - signup).days for item in active_dates}
    return {
        "retained_d1": 1 in offsets,
        "retained_d3": 3 in offsets,
        "retained_d7": 7 in offsets,
        "retained_d1_7_window": bool(offsets.intersection(range(1, 8))),
        "retained_d30": 30 in offsets,
    }


def retention_rates(rows: Iterable[dict[str, bool]]) -> dict[str, float | int]:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"users": 0, "d1": 0.0, "d3": 0.0, "d7": 0.0, "d1_7_window": 0.0, "d30": 0.0}
    return {
        "users": len(frame),
        "d1": float(frame["retained_d1"].mean()),
        "d3": float(frame["retained_d3"].mean()),
        "d7": float(frame["retained_d7"].mean()),
        "d1_7_window": float(frame["retained_d1_7_window"].mean()),
        "d30": float(frame["retained_d30"].mean()),
    }
