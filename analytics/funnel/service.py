from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _safe_rate(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else float(numerator / denominator)


def build_funnel(
    counts: Mapping[str, int | float],
    steps: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Build a monotonic funnel with step and exposure conversions."""
    ordered = list(steps or counts.keys())
    if not ordered:
        return []
    exposure = float(counts[ordered[0]])
    result: list[dict[str, Any]] = []
    previous = None
    for index, step in enumerate(ordered):
        uv = float(counts[step])
        if uv < 0:
            raise ValueError(f"Funnel count cannot be negative: {step}")
        if previous is not None and uv > previous:
            raise ValueError(f"Funnel must be monotonic: {step} exceeds previous step")
        result.append(
            {
                "order": index + 1,
                "step": step,
                "uv": int(uv),
                "conversion_from_previous": 1.0 if previous is None else _safe_rate(uv, previous),
                "conversion_from_exposure": _safe_rate(uv, exposure),
                "dropoff_from_previous": 0.0
                if previous is None
                else 1.0 - float(_safe_rate(uv, previous) or 0.0),
            }
        )
        previous = uv
    return result


def compare_funnels(
    baseline: Mapping[str, int | float],
    current: Mapping[str, int | float],
    steps: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    ordered = list(steps or baseline.keys())
    base = build_funnel(baseline, ordered)
    curr = build_funnel(current, ordered)
    output = []
    for b, c in zip(base, curr, strict=True):
        b_rate = b["conversion_from_previous"]
        c_rate = c["conversion_from_previous"]
        absolute = None if b_rate is None or c_rate is None else c_rate - b_rate
        relative = None if absolute is None or b_rate == 0 else absolute / b_rate
        output.append(
            {
                "step": b["step"],
                "baseline_uv": b["uv"],
                "current_uv": c["uv"],
                "baseline_conversion": b_rate,
                "current_conversion": c_rate,
                "absolute_change": absolute,
                "relative_change": relative,
            }
        )
    return output


def diagnose_funnel(
    comparison: Sequence[Mapping[str, Any]], *, material_threshold: float = 0.02
) -> dict[str, Any]:
    candidates = [row for row in comparison[1:] if row.get("absolute_change") is not None]
    if not candidates:
        return {
            "status": "insufficient_data",
            "facts": [],
            "interpretations": [],
            "hypotheses": [],
            "actions": [],
        }
    # Root-cause triage selects the earliest material break. A downstream rate can
    # look noisier because its denominator is smaller, while the first break is
    # the actionable location in the ordered journey.
    material_declines = [
        row for row in candidates if float(row["absolute_change"]) <= -material_threshold
    ]
    primary = (
        material_declines[0]
        if material_declines
        else min(candidates, key=lambda item: float(item["absolute_change"]))
    )
    change_pp = 100.0 * float(primary["absolute_change"])
    step = str(primary["step"])
    return {
        "status": "diagnosed",
        "primary_step": step,
        "facts": [
            f"The largest step conversion decline occurs at {step}: {change_pp:.2f} percentage points.",
            "This statement is computed from the funnel; it does not establish a causal mechanism.",
        ],
        "interpretations": [
            "The issue is more likely to be upstream of or at this action than in later conversion steps."
        ],
        "hypotheses": [
            "Information density, action prominence, technical latency, or audience mix may explain the decline."
        ],
        "actions": [
            "Validate event instrumentation and segment mix first.",
            "Use qualitative research to refine the product hypothesis.",
            "Run a pre-registered randomized A/B experiment before claiming causality.",
        ],
    }
