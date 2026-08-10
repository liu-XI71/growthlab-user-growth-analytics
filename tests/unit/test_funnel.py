from __future__ import annotations

import pytest

from analytics.funnel import build_funnel, compare_funnels, diagnose_funnel

STEPS = ["exposure", "page", "invite", "share", "activate"]


def test_funnel_conversions_and_primary_diagnosis_are_computed() -> None:
    baseline = {"exposure": 10_000, "page": 5_000, "invite": 1_250, "share": 1_188, "activate": 300}
    current = {"exposure": 10_000, "page": 5_100, "invite": 867, "share": 824, "activate": 210}
    comparison = compare_funnels(baseline, current, STEPS)
    invite = next(row for row in comparison if row["step"] == "invite")
    assert invite["baseline_conversion"] == pytest.approx(0.25)
    assert invite["current_conversion"] == pytest.approx(0.17)
    assert invite["absolute_change"] == pytest.approx(-0.08)
    diagnosis = diagnose_funnel(comparison)
    assert diagnosis["primary_step"] == "invite"
    joined = " ".join(
        item
        for section in ("facts", "interpretations", "hypotheses", "actions")
        for item in diagnosis[section]
    ).lower()
    assert "causal" in " ".join(diagnosis["facts"]).lower()
    assert "random" in joined


def test_funnel_rejects_non_monotonic_counts() -> None:
    with pytest.raises(ValueError, match="monotonic"):
        build_funnel({"exposure": 100, "click": 101})


def test_funnel_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="negative"):
        build_funnel({"exposure": 100, "click": -1})
