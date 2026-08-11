from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.stats import norm

from analytics.lifecycle import causal_metric_contract


def binary_smd(control_share: float, treatment_share: float) -> float:
    """One-hot standardized mean difference for a pre-treatment category."""
    pooled_variance = (
        control_share * (1 - control_share) + treatment_share * (1 - treatment_share)
    ) / 2
    if pooled_variance <= 0:
        return 0.0
    return (treatment_share - control_share) / math.sqrt(pooled_variance)


def balance_smd(
    control_counts: Mapping[str, int],
    treatment_counts: Mapping[str, int],
    *,
    threshold: float = 0.1,
) -> dict[str, Any]:
    categories = sorted(set(control_counts) | set(treatment_counts))
    control_n = sum(int(value) for value in control_counts.values())
    treatment_n = sum(int(value) for value in treatment_counts.values())
    if not control_n or not treatment_n:
        raise ValueError("Both experiment arms require observations")
    items = []
    for category in categories:
        control_share = int(control_counts.get(category, 0)) / control_n
        treatment_share = int(treatment_counts.get(category, 0)) / treatment_n
        smd = binary_smd(control_share, treatment_share)
        items.append(
            {
                "category": category,
                "control_share": control_share,
                "treatment_share": treatment_share,
                "smd": smd,
                "absolute_smd": abs(smd),
                "pass": abs(smd) <= threshold,
            }
        )
    maximum = max((item["absolute_smd"] for item in items), default=0.0)
    return {
        "items": items,
        "max_absolute_smd": maximum,
        "threshold": threshold,
        "pass": maximum <= threshold,
        "method": "one-hot standardized mean difference on pre-treatment covariates",
    }


def proportion_effect(
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    *,
    alpha: float = 0.05,
) -> dict[str, float | int | bool]:
    if min(control_n, treatment_n) <= 0:
        raise ValueError("Both arms require positive denominators")
    if not 0 <= control_successes <= control_n or not 0 <= treatment_successes <= treatment_n:
        raise ValueError("Success counts must be within their arm denominators")
    control_rate = control_successes / control_n
    treatment_rate = treatment_successes / treatment_n
    effect = treatment_rate - control_rate
    standard_error = math.sqrt(
        control_rate * (1 - control_rate) / control_n
        + treatment_rate * (1 - treatment_rate) / treatment_n
    )
    critical = float(norm.ppf(1 - alpha / 2))
    z_stat = effect / standard_error if standard_error else 0.0
    p_value = float(2 * norm.sf(abs(z_stat))) if standard_error else 1.0
    return {
        "control_successes": control_successes,
        "control_n": control_n,
        "treatment_successes": treatment_successes,
        "treatment_n": treatment_n,
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "absolute_uplift": effect,
        "absolute_uplift_pp": effect * 100,
        "ci_lower": effect - critical * standard_error,
        "ci_upper": effect + critical * standard_error,
        "z_stat": z_stat,
        "p_value": p_value,
        "stat_significant": p_value < alpha,
    }


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    if not p_values:
        return []
    values = np.asarray(p_values, dtype=float)
    order = np.argsort(values)
    adjusted = np.empty(len(values), dtype=float)
    running = 1.0
    for reverse_rank, index in enumerate(order[::-1], start=1):
        rank = len(values) - reverse_rank + 1
        running = min(running, values[index] * len(values) / rank)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def itt_quality_effects(
    control: Mapping[str, Any],
    treatment: Mapping[str, Any],
) -> dict[str, Any]:
    control_n = int(control["assigned_users"])
    treatment_n = int(treatment["assigned_users"])
    if control_n <= 0 or treatment_n <= 0:
        raise ValueError(
            "ITT effects require positive control and treatment assignment denominators"
        )

    def count_metric(column: str, name: str, window: str) -> dict[str, Any]:
        control_rate = float(control[column]) / control_n
        treatment_rate = float(treatment[column]) / treatment_n
        return causal_metric_contract(
            name=name,
            estimate=10_000 * (treatment_rate - control_rate),
            control_value=10_000 * control_rate,
            treatment_value=10_000 * treatment_rate,
            window=window,
            unit="users_per_10k_assigned",
        )

    control_contribution = float(control["contribution30"]) / control_n
    treatment_contribution = float(treatment["contribution30"]) / treatment_n
    contribution = causal_metric_contract(
        name="incremental_contribution30_per_10k_assigned",
        estimate=10_000 * (treatment_contribution - control_contribution),
        control_value=10_000 * control_contribution,
        treatment_value=10_000 * treatment_contribution,
        window="30-day contribution after referred-user activation",
        unit="normalized_value_per_10k_assigned",
    )
    d7 = count_metric(
        "retained_d7_users",
        "incremental_d7_retained_per_10k_assigned",
        "exact day 7 after referred-user activation",
    )
    window = count_metric(
        "retained_d1_7_window_users",
        "incremental_d1_7_retained_per_10k_assigned",
        "any qualifying activity on day 1 through day 7",
    )
    incremental_d7_rate = d7["estimate"] / 10_000
    incremental_cost_rate = (
        float(treatment["variable_acquisition_cost"]) / treatment_n
        - float(control["variable_acquisition_cost"]) / control_n
    )
    cost_per_incremental_d7 = (
        incremental_cost_rate / incremental_d7_rate if incremental_d7_rate > 0 else None
    )
    cost_metric = {
        "value": cost_per_incremental_d7,
        "unit": "normalized_cost_per_incremental_d7_retained_user",
        "status": "available" if cost_per_incremental_d7 is not None else "unavailable",
        "reason": None
        if cost_per_incremental_d7 is not None
        else "Incremental D7 retained-user effect is not positive.",
    }
    return {
        "d7_retained": d7,
        "d1_7_window_retained": window,
        "contribution30": contribution,
        "cost_per_incremental_d7": cost_metric,
        "cost_per_incremental_d7_retained_user": cost_metric,
        "primary_estimand": "intention_to_treat",
    }
