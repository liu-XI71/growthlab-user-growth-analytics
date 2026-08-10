from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def calculate_roi(
    *,
    active_days_30: float,
    daily_active_hours: float,
    value_per_hour: float,
    incentive_cost_per_acquisition: float,
    retention_discount: float = 1.0,
    external_benchmark_ratio: float = 1.6,
) -> dict[str, float | bool]:
    values = [active_days_30, daily_active_hours, value_per_hour, incentive_cost_per_acquisition]
    if any(value < 0 for value in values) or not 0 <= retention_discount <= 1:
        raise ValueError("ROI inputs must be non-negative and retention_discount must be in [0, 1]")
    if incentive_cost_per_acquisition == 0:
        raise ValueError("incentive_cost_per_acquisition must be greater than zero")
    gross_ltv30 = active_days_30 * daily_active_hours * value_per_hour
    ltv30 = gross_ltv30 * retention_discount
    ratio = ltv30 / incentive_cost_per_acquisition
    return {
        "gross_ltv30": gross_ltv30,
        "ltv30": ltv30,
        "cac": incentive_cost_per_acquisition,
        "ltv_cac_ratio": ratio,
        "net_roi": (ltv30 - incentive_cost_per_acquisition) / incentive_cost_per_acquisition,
        "break_even_cac": ltv30,
        "external_benchmark_ratio": external_benchmark_ratio,
        "above_external_benchmark": ratio >= external_benchmark_ratio,
    }


def sensitivity_analysis(
    base: Mapping[str, float],
    variations: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    required = {
        "active_days_30",
        "daily_active_hours",
        "value_per_hour",
        "incentive_cost_per_acquisition",
        "retention_discount",
    }
    missing = required - set(base)
    if missing:
        raise ValueError(f"Missing base inputs: {sorted(missing)}")
    base_result = calculate_roi(**base)
    items = []
    for parameter, multipliers in variations.items():
        if parameter not in required:
            raise ValueError(f"Unsupported sensitivity parameter: {parameter}")
        for multiplier in multipliers:
            scenario = dict(base)
            scenario[parameter] = base[parameter] * float(multiplier)
            if parameter == "retention_discount":
                scenario[parameter] = min(1.0, max(0.0, scenario[parameter]))
            result = calculate_roi(**scenario)
            items.append(
                {
                    "parameter": parameter,
                    "multiplier": float(multiplier),
                    "input_value": scenario[parameter],
                    "ltv_cac_ratio": result["ltv_cac_ratio"],
                    "net_roi": result["net_roi"],
                    "change_from_base": result["ltv_cac_ratio"] - base_result["ltv_cac_ratio"],
                }
            )
    return {"base": base_result, "items": items}
