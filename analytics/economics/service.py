from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


def parametric_bootstrap_difference(
    control_values: Sequence[float],
    treatment_values: Sequence[float],
    *,
    scale: float = 10_000,
    draws: int = 4_000,
    seed: int = 20_260_811,
) -> dict[str, Any]:
    """Reproducible uncertainty for a mean-difference ITT estimand."""
    control = np.asarray(control_values, dtype=float)
    treatment = np.asarray(treatment_values, dtype=float)
    if len(control) < 2 or len(treatment) < 2 or draws < 100:
        raise ValueError("Both arms require at least two rows and draws must be >= 100")
    rng = np.random.default_rng(seed)
    control_se = control.std(ddof=1) / np.sqrt(len(control))
    treatment_se = treatment.std(ddof=1) / np.sqrt(len(treatment))
    sampled = rng.normal(treatment.mean(), treatment_se, draws) - rng.normal(
        control.mean(), control_se, draws
    )
    scaled = sampled * scale
    estimate = float((treatment.mean() - control.mean()) * scale)
    return {
        "estimate": estimate,
        "ci_lower": float(np.quantile(scaled, 0.025)),
        "ci_upper": float(np.quantile(scaled, 0.975)),
        "probability_positive": float((scaled > 0).mean()),
        "draws": draws,
        "seed": seed,
        "method": "fixed-seed parametric bootstrap of the randomized arm mean difference",
        "scale": scale,
    }


def budget_curve(
    *,
    acquired_per_10k: float,
    value_per_acquired: float,
    cost_per_acquired: float,
    multipliers: Sequence[float],
    elasticity: float = 0.82,
    eligible_population: int | None = None,
) -> dict[str, Any]:
    if acquired_per_10k < 0 or value_per_acquired < 0 or cost_per_acquired <= 0:
        raise ValueError("Economics inputs must be non-negative and cost must be positive")
    if not 0 < elasticity <= 1:
        raise ValueError("elasticity must be in (0, 1]")
    population = int(eligible_population) if eligible_population is not None else 10_000
    if population <= 0:
        raise ValueError("eligible_population must be positive")
    items = []
    for multiplier in multipliers:
        if multiplier <= 0:
            raise ValueError("Budget multipliers must be positive")
        acquired = acquired_per_10k * (population / 10_000) * float(multiplier) ** elasticity
        unit_cost = cost_per_acquired * float(multiplier) ** (1 - elasticity)
        spend = acquired * unit_cost
        contribution = acquired * value_per_acquired - spend
        items.append(
            {
                "budget_multiplier": float(multiplier),
                "eligible_population": population,
                "modelled_acquired_users": acquired,
                "modelled_variable_cost": spend,
                "modelled_value30": acquired * value_per_acquired,
                "modelled_contribution30": contribution,
                "modelled_ltv_cac": value_per_acquired / unit_cost,
            }
        )
    return {
        "items": items,
        "population_basis": "user_supplied"
        if eligible_population is not None
        else "normalized_10k",
        "eligible_population": population,
        "model_type": "descriptive response-curve scenario, not a randomized causal estimate",
        "elasticity": elasticity,
        "claim_boundary": "Use for sensitivity and planning; do not report as realized impact.",
    }
