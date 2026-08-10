from __future__ import annotations

import pytest

from analytics.roi import calculate_roi, sensitivity_analysis


def test_roi_uses_documented_growth_economics_formulas() -> None:
    result = calculate_roi(
        active_days_30=10,
        daily_active_hours=0.5,
        value_per_hour=4,
        incentive_cost_per_acquisition=8,
        retention_discount=0.8,
        external_benchmark_ratio=1.9,
    )

    assert result["gross_ltv30"] == pytest.approx(20.0)
    assert result["ltv30"] == pytest.approx(16.0)
    assert result["cac"] == pytest.approx(8.0)
    assert result["ltv_cac_ratio"] == pytest.approx(2.0)
    assert result["net_roi"] == pytest.approx(1.0)
    assert result["break_even_cac"] == pytest.approx(16.0)
    assert result["above_external_benchmark"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"active_days_30": -1},
        {"daily_active_hours": -0.1},
        {"value_per_hour": -1},
        {"incentive_cost_per_acquisition": 0},
        {"retention_discount": -0.1},
        {"retention_discount": 1.1},
    ],
)
def test_roi_rejects_invalid_or_divide_by_zero_inputs(overrides: dict[str, float]) -> None:
    inputs = {
        "active_days_30": 10.0,
        "daily_active_hours": 0.5,
        "value_per_hour": 4.0,
        "incentive_cost_per_acquisition": 8.0,
        "retention_discount": 0.8,
    }
    inputs.update(overrides)
    with pytest.raises(ValueError):
        calculate_roi(**inputs)


def test_sensitivity_preserves_base_and_moves_cost_ratio_in_expected_direction() -> None:
    base = {
        "active_days_30": 10.0,
        "daily_active_hours": 0.5,
        "value_per_hour": 4.0,
        "incentive_cost_per_acquisition": 8.0,
        "retention_discount": 0.8,
    }
    output = sensitivity_analysis(base, {"incentive_cost_per_acquisition": [0.8, 1.2]})
    assert output["base"]["ltv_cac_ratio"] == pytest.approx(2.0)
    low_cost, high_cost = output["items"]
    assert low_cost["ltv_cac_ratio"] > output["base"]["ltv_cac_ratio"]
    assert high_cost["ltv_cac_ratio"] < output["base"]["ltv_cac_ratio"]
