from __future__ import annotations

import math

import pytest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from analytics.experimentation import (
    analyze_aa,
    analyze_experiment,
    analyze_strata,
    assign_hash_group,
    balance_categorical,
    calculate_duration,
    calculate_mde,
    calculate_sample_size,
    check_srm,
)


def test_hash_assignment_is_stable_bounded_and_approximately_half_split() -> None:
    first = assign_hash_group("user-42", salt="growthlab-v1")
    assert first == assign_hash_group("user-42", salt="growthlab-v1")
    assignments = [assign_hash_group(index, salt="growthlab-v1") for index in range(20_000)]
    assert all(0 <= int(item["bucket"]) < 100 for item in assignments)
    treatment_share = sum(item["group"] == "treatment" for item in assignments) / len(assignments)
    assert treatment_share == pytest.approx(0.5, abs=0.015)
    assert any(
        assign_hash_group(index, salt="growthlab-v1")["group"]
        != assign_hash_group(index, salt="independent-experiment")["group"]
        for index in range(100)
    )


@pytest.mark.parametrize(
    ("buckets", "treatment_buckets"),
    [(1, 0), (100, 0), (100, 100), (20, 21)],
)
def test_hash_assignment_rejects_invalid_bucket_configuration(
    buckets: int, treatment_buckets: int
) -> None:
    with pytest.raises(ValueError):
        assign_hash_group(
            "user-1", salt="experiment", buckets=buckets, treatment_buckets=treatment_buckets
        )


def test_17_percent_baseline_plus_3pp_sample_size_matches_statsmodels_golden_value() -> None:
    result = calculate_sample_size(
        baseline_rate=0.17,
        mde_absolute=0.03,
        alpha=0.05,
        power=0.80,
    )
    effect = abs(proportion_effectsize(0.20, 0.17))
    golden = math.ceil(
        NormalIndPower().solve_power(
            effect_size=effect,
            alpha=0.05,
            power=0.80,
            ratio=1.0,
            alternative="two-sided",
        )
    )
    assert result["target_rate"] == pytest.approx(0.20)
    assert result["mde_percentage_points"] == pytest.approx(3.0)
    assert result["sample_control"] == golden
    assert result["sample_treatment"] == golden
    assert result["sample_total"] == 2 * golden


def test_sample_size_and_mde_round_trip() -> None:
    planned = calculate_sample_size(baseline_rate=0.17, mde_absolute=0.03)
    inverted = calculate_mde(
        baseline_rate=0.17,
        sample_per_group=int(planned["sample_per_group"]),
    )
    assert inverted["mde_absolute"] == pytest.approx(0.03, abs=2e-5)


def test_duration_uses_required_traffic_but_rounds_to_full_weeks_and_novelty_floor() -> None:
    result = calculate_duration(
        required_sample_total=100_001,
        eligible_users_per_day=20_000,
        minimum_full_weeks=2,
    )
    assert result["traffic_days"] == 6
    assert result["recommended_days"] == 14
    assert result["recommended_weeks"] == 2
    note = str(result["note"]).lower()
    assert "pre-register" in note
    assert "novelty" in note


def test_balanced_aa_passes_and_equal_rates_are_not_significant() -> None:
    result = analyze_aa(
        control_successes=17_000,
        control_n=100_000,
        treatment_successes=17_000,
        treatment_n=100_000,
    )
    assert result["srm"]["pass"] is True
    assert result["p_value"] == pytest.approx(1.0)
    assert result["absolute_difference"] == pytest.approx(0.0)
    assert result["pass"] is True
    assert result["action"] == "proceed_to_ab"


def test_srm_detects_allocation_mismatch_before_effect_interpretation() -> None:
    result = check_srm([60_000, 40_000], expected_proportions=[0.5, 0.5])
    assert result["applicable"] is True
    assert result["pass"] is False
    assert result["p_value"] < 0.05
    experiment = analyze_experiment(
        control_successes=10_200,
        control_n=60_000,
        treatment_successes=9_400,
        treatment_n=40_000,
    )
    assert experiment["srm"]["pass"] is False
    assert experiment["decision"] == "investigate_assignment"


def test_srm_refuses_unreliable_small_expected_frequencies() -> None:
    result = check_srm([2, 3])
    assert result["applicable"] is False
    assert result["pass"] is None
    assert "below 5" in result["warning"]


def test_41_to_44_9_reports_3_9pp_and_9_51_percent_relative() -> None:
    result = analyze_experiment(
        control_successes=41_000,
        control_n=100_000,
        treatment_successes=44_900,
        treatment_n=100_000,
        business_mde_absolute=0.03,
    )
    assert result["absolute_uplift"] == pytest.approx(0.039)
    assert result["absolute_uplift_pp"] == pytest.approx(3.9)
    assert result["relative_uplift"] == pytest.approx(0.039 / 0.41)
    assert result["relative_uplift_pct"] == pytest.approx(9.512195121951219)


def test_17_to_23_5_reports_6_5pp_and_38_24_percent_relative() -> None:
    result = analyze_experiment(
        control_successes=17_000,
        control_n=100_000,
        treatment_successes=23_500,
        treatment_n=100_000,
        business_mde_absolute=0.03,
    )
    assert result["absolute_uplift_pp"] == pytest.approx(6.5)
    assert result["relative_uplift_pct"] == pytest.approx(38.23529411764706)


def test_z_stat_p_value_and_ci_match_independent_reference() -> None:
    control_successes, control_n = 1_700, 10_000
    treatment_successes, treatment_n = 1_900, 10_000
    result = analyze_experiment(
        control_successes=control_successes,
        control_n=control_n,
        treatment_successes=treatment_successes,
        treatment_n=treatment_n,
    )
    golden_z, golden_p = proportions_ztest(
        [treatment_successes, control_successes],
        [treatment_n, control_n],
        alternative="two-sided",
    )
    assert result["z_stat"] == pytest.approx(golden_z)
    assert result["p_value"] == pytest.approx(golden_p)
    assert result["confidence_interval_absolute"]["lower"] < result["absolute_uplift"]
    assert result["confidence_interval_absolute"]["upper"] > result["absolute_uplift"]
    assert result["confidence_interval_absolute"]["lower"] > 0


def test_significance_alone_does_not_pass_business_gate() -> None:
    result = analyze_experiment(
        control_successes=340_000,
        control_n=2_000_000,
        treatment_successes=342_000,
        treatment_n=2_000_000,
        business_mde_absolute=0.003,
    )
    assert result["stat_significant"] is True
    assert result["business_significant"] is False
    assert result["decision"] == "continue_or_reassess_business_value"
    assert "separate gates" in result["interpretation_note"]


def test_failed_guardrail_blocks_launch_even_with_positive_core_effect() -> None:
    result = analyze_experiment(
        control_successes=17_000,
        control_n=100_000,
        treatment_successes=20_000,
        treatment_n=100_000,
        business_mde_absolute=0.02,
        guardrails=[
            {
                "name": "new_user_ltv_cac",
                "control_value": 1.9,
                "treatment_value": 1.7,
                "desired_direction": "higher",
                "tolerance": 0.05,
            }
        ],
    )
    assert result["stat_significant"] is True
    assert result["business_significant"] is True
    assert result["guardrails_pass"] is False
    assert result["decision"] == "do_not_launch_guardrail_regression"


def test_result_warns_against_unadjusted_repeated_peeking() -> None:
    result = analyze_experiment(
        control_successes=170,
        control_n=1_000,
        treatment_successes=200,
        treatment_n=1_000,
    )
    warning = result["peeking_warning"].lower()
    assert "pre-registered" in warning
    assert "false positives" in warning


def test_covariate_balance_reports_practical_distribution_difference() -> None:
    balanced = balance_categorical(
        {"mobile": 5_000, "tablet": 500, "tv": 500},
        {"mobile": 5_020, "tablet": 490, "tv": 490},
    )
    assert balanced["pass"] is True
    imbalanced = balance_categorical(
        {"mobile": 5_000, "tablet": 500, "tv": 500},
        {"mobile": 4_000, "tablet": 1_000, "tv": 1_000},
    )
    assert imbalanced["pass"] is False
    assert "composition" in imbalanced["warning"]


def test_simpson_reversal_is_flagged_for_stratified_review() -> None:
    result = analyze_strata(
        [
            {
                "stratum": "high-intent",
                "control_successes": 810,
                "control_n": 900,
                "treatment_successes": 92,
                "treatment_n": 100,
            },
            {
                "stratum": "low-intent",
                "control_successes": 10,
                "control_n": 100,
                "treatment_successes": 108,
                "treatment_n": 900,
            },
        ]
    )
    assert all(item["absolute_uplift"] > 0 for item in result["items"])
    assert result["aggregate"]["absolute_uplift"] < 0
    assert result["simpson_warning"] is True
    assert "not by itself proof" in result["note"]
