from __future__ import annotations

import pytest

from analytics.decisions import build_decision_card
from analytics.experimentation import itt_quality_effects, proportion_effect

ALL_HEALTH_GATES = {
    "data_quality": True,
    "assignment_and_exposure_integrity": True,
    "srm": True,
    "pre_treatment_balance": True,
    "exposure_tracking": True,
    "sample_size": True,
    "fixed_horizon_duration": True,
    "outcome_maturity": True,
    "guardrail": True,
}


@pytest.mark.parametrize(
    ("failed_gate", "failed_value"),
    [
        ("data_quality", False),
        ("srm", False),
        ("srm", None),
        ("guardrail", False),
        ("sample_size", False),
        ("fixed_horizon_duration", False),
        ("outcome_maturity", False),
        ("exposure_tracking", False),
    ],
)
def test_any_failed_or_unknown_health_gate_blocks_ship(
    failed_gate: str, failed_value: bool | None
) -> None:
    health = {**ALL_HEALTH_GATES, failed_gate: failed_value}
    card = build_decision_card(
        health=health,
        statistical_significant=True,
        business_significant=True,
        contribution_positive=True,
    )
    assert card["decision"] == "DO_NOT_SHIP"
    assert card["all_gates_pass"] is False
    assert failed_gate in card["failed_or_unknown_gates"]
    result = {item["gate"]: item for item in card["gates"]}[failed_gate]
    assert result["status"] == ("unknown" if failed_value is None else "fail")


@pytest.mark.parametrize(
    "outcomes",
    [
        {
            "statistical_significant": False,
            "business_significant": True,
            "contribution_positive": True,
        },
        {
            "statistical_significant": True,
            "business_significant": False,
            "contribution_positive": True,
        },
        {
            "statistical_significant": True,
            "business_significant": True,
            "contribution_positive": False,
        },
    ],
)
def test_statistical_business_or_economic_failure_blocks_ship(outcomes: dict[str, bool]) -> None:
    card = build_decision_card(health=ALL_HEALTH_GATES, **outcomes)
    assert card["decision"] == "DO_NOT_SHIP"
    assert card["all_gates_pass"] is False


def test_only_all_explicitly_true_gates_can_ship() -> None:
    card = build_decision_card(
        health=ALL_HEALTH_GATES,
        statistical_significant=True,
        business_significant=True,
        contribution_positive=True,
    )
    assert card["decision"] == "SHIP_WITH_MONITORING"
    assert card["all_gates_pass"] is True
    assert card["failed_or_unknown_gates"] == []


def test_itt_effect_helper_rejects_zero_denominator_and_preserves_zero_nonacquirers() -> None:
    with pytest.raises(ValueError, match="positive .*assignment denominators"):
        itt_quality_effects(
            {
                "assigned_users": 0,
                "retained_d7_users": 0,
                "retained_d1_7_window_users": 0,
                "contribution30": 0,
                "variable_acquisition_cost": 0,
            },
            {
                "assigned_users": 10,
                "retained_d7_users": 1,
                "retained_d1_7_window_users": 2,
                "contribution30": 10,
                "variable_acquisition_cost": 5,
            },
        )

    result = itt_quality_effects(
        {
            "assigned_users": 10,
            "retained_d7_users": 1,
            "retained_d1_7_window_users": 2,
            "contribution30": 10,
            "variable_acquisition_cost": 5,
        },
        {
            "assigned_users": 10,
            "retained_d7_users": 2,
            "retained_d1_7_window_users": 3,
            "contribution30": 20,
            "variable_acquisition_cost": 7,
        },
    )
    assert result["d7_retained"]["estimate"] == pytest.approx(1_000)
    assert result["d1_7_window_retained"]["estimate"] == pytest.approx(1_000)
    assert result["contribution30"]["estimate"] == pytest.approx(10_000)
    assert result["d7_retained"]["non_acquired_contribution"] == 0


@pytest.mark.parametrize(
    "inputs",
    [
        (-1, 100, 1, 100),
        (101, 100, 1, 100),
        (1, 0, 1, 100),
        (1, 100, 101, 100),
    ],
)
def test_proportion_effect_rejects_invalid_success_denominator_pairs(
    inputs: tuple[int, int, int, int],
) -> None:
    with pytest.raises(ValueError):
        proportion_effect(*inputs)
