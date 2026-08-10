from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.monitoring import analyze_growth_trend


def test_growth_trend_reports_target_gap_components_and_spike() -> None:
    day = np.arange(42)
    values = 65 + 0.1 * day + 0.3 * np.sin(2 * np.pi * day / 7)
    values[25] -= 5
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=len(day)),
            "dau_index": values,
            "target_index": 80,
            "external_new_index": 20 - 0.05 * day,
            "organic_new_index": 15 + 0.01 * day,
            "referral_new_index": 4 + 0.06 * day,
            "retained_user_index": 45 + 0.02 * day,
        }
    )
    result = analyze_growth_trend(frame)
    assert result["latest"]["gap_to_target"] == pytest.approx(80 - values[-1])
    assert len(result["components"]) == 4
    assert any(item["date"].startswith("2025-01-26") for item in result["anomalies"])
    assert "do not identify" in result["claim_boundary"]


def test_growth_trend_rejects_unknown_metric_and_short_history() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=10),
            "dau_index": range(10),
            "target_index": 10,
        }
    )
    with pytest.raises(ValueError, match="Unsupported"):
        analyze_growth_trend(frame, metric="secret_metric")
    with pytest.raises(ValueError, match="14"):
        analyze_growth_trend(frame)
