from __future__ import annotations

from datetime import date, timedelta

import pytest

from analytics.retention import retention_flags, retention_rates


def test_exact_day_and_d1_7_window_retention_are_not_conflated() -> None:
    signup = date(2026, 1, 1)
    flags = retention_flags(
        signup,
        [signup, signup + timedelta(days=2), signup + timedelta(days=30)],
    )
    assert flags == {
        "retained_d1": False,
        "retained_d3": False,
        "retained_d7": False,
        "retained_d1_7_window": True,
        "retained_d30": True,
    }


def test_retention_rates_stay_in_probability_bounds() -> None:
    rows = [
        retention_flags("2026-01-01", ["2026-01-02", "2026-01-08"]),
        retention_flags("2026-01-01", ["2026-01-04"]),
        retention_flags("2026-01-01", []),
    ]
    rates = retention_rates(rows)
    assert rates["users"] == 3
    assert rates["d1"] == pytest.approx(1 / 3)
    assert rates["d3"] == pytest.approx(1 / 3)
    assert rates["d7"] == pytest.approx(1 / 3)
    assert rates["d1_7_window"] == pytest.approx(2 / 3)
    assert rates["d30"] == pytest.approx(0)
    assert all(0 <= float(rates[key]) <= 1 for key in ("d1", "d3", "d7", "d1_7_window", "d30"))


def test_empty_retention_cohort_is_explicit() -> None:
    rates = retention_rates([])
    assert rates["users"] == 0
    assert rates["d1_7_window"] == 0.0
