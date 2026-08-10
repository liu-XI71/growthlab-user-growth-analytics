from __future__ import annotations

import pandas as pd
import pytest

from analytics.decomposition import mix_shift_decomposition


def _rows(period: str, segment: str, users: int, retained: int) -> list[dict[str, object]]:
    return [
        {"period": period, "device": segment, "retained": index < retained}
        for index in range(users)
    ]


def test_mix_shift_exactly_reconciles_observed_retention_change() -> None:
    frame = pd.DataFrame(
        _rows("baseline", "mobile", 80, 48)
        + _rows("baseline", "large_screen", 20, 8)
        + _rows("current", "mobile", 60, 36)
        + _rows("current", "large_screen", 40, 16)
    )
    result = mix_shift_decomposition(
        frame,
        segment_col="device",
        period_col="period",
        outcome_col="retained",
        baseline_period="baseline",
        current_period="current",
    )

    assert result["baseline_rate"] == pytest.approx(0.56)
    assert result["current_rate"] == pytest.approx(0.52)
    assert result["total_change"] == pytest.approx(-0.04)
    assert result["structure_effect"] == pytest.approx(-0.04)
    assert result["within_effect"] == pytest.approx(0.0)
    assert result["interaction_effect"] == pytest.approx(0.0)
    assert result["reconciliation_error"] == pytest.approx(0.0, abs=1e-12)
    reconstructed = (
        result["structure_effect"] + result["within_effect"] + result["interaction_effect"]
    )
    assert reconstructed == pytest.approx(result["total_change"], abs=1e-12)


def test_mix_shift_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="Missing columns"):
        mix_shift_decomposition(
            pd.DataFrame({"period": ["baseline"]}),
            segment_col="device",
            period_col="period",
            outcome_col="retained",
            baseline_period="baseline",
            current_period="current",
        )
