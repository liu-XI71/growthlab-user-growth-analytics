from __future__ import annotations

from typing import Any

from analytics.decomposition import mix_shift_from_aggregates
from analytics.funnel import compare_funnels, diagnose_funnel
from backend.schemas.api import FunnelWorkbenchRequest, MixShiftWorkbenchRequest


def diagnose_custom_funnel(request: FunnelWorkbenchRequest) -> dict[str, Any]:
    steps = [item.step for item in request.steps]
    if len(set(steps)) != len(steps):
        raise ValueError("Funnel step names must be unique")
    baseline = {item.step: item.baseline_uv for item in request.steps}
    current = {item.step: item.current_uv for item in request.steps}
    comparison = compare_funnels(baseline, current, steps)
    diagnosis = diagnose_funnel(comparison, material_threshold=request.material_threshold)
    return {
        "comparison": comparison,
        "diagnosis": diagnosis,
        "evidence_level": 2,
        "claim_boundary": "The ordered break localizes the change; it does not prove the product mechanism caused it.",
    }


def decompose_custom_mix_shift(request: MixShiftWorkbenchRequest) -> dict[str, Any]:
    result = mix_shift_from_aggregates([item.model_dump() for item in request.rows])
    result.update(
        {
            "evidence_level": 2,
            "claim_boundary": "The decomposition is an exact arithmetic attribution, not a causal estimate.",
        }
    )
    return result
