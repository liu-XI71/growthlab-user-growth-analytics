from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def causal_metric_contract(
    *,
    name: str,
    estimate: float,
    control_value: float,
    treatment_value: float,
    window: str,
    unit: str,
) -> dict[str, Any]:
    """Attach the identification contract to a randomized lifecycle metric."""
    return {
        "metric_name": name,
        "estimate": float(estimate),
        "control_value": float(control_value),
        "treatment_value": float(treatment_value),
        "denominator_type": "assignment",
        "population": "intention_to_treat",
        "window": window,
        "unit": unit,
        "non_acquired_contribution": 0,
        "claim_boundary": (
            "Causal for the randomized fixed-horizon ITT population; "
            "network interference remains a monitored risk."
        ),
    }


def lifecycle_funnel(steps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate and annotate one linked acquisition-to-value lifecycle."""
    output: list[dict[str, Any]] = []
    previous: int | None = None
    first: int | None = None
    for order, row in enumerate(steps, start=1):
        count = int(row["users"])
        if count < 0 or (previous is not None and count > previous):
            raise ValueError("Lifecycle steps must be non-negative and monotonic")
        first = count if first is None else first
        output.append(
            {
                **dict(row),
                "order": order,
                "users": count,
                "step_conversion": 1.0
                if previous is None
                else count / previous
                if previous
                else 0.0,
                "conversion_from_eligible": count / first if first else 0.0,
            }
        )
        previous = count
    return output
