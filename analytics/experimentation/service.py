from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import numpy as np
from scipy.stats import chi2_contingency, chisquare, norm
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest


def assign_hash_group(
    unit_id: str | int,
    *,
    salt: str,
    buckets: int = 100,
    treatment_buckets: int = 50,
) -> dict[str, int | str]:
    """Stable SHA-256 based user assignment suitable for a portfolio demo."""
    if buckets < 2 or not 0 < treatment_buckets < buckets:
        raise ValueError("Require 0 < treatment_buckets < buckets")
    digest = hashlib.sha256(f"{salt}:{unit_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], byteorder="big", signed=False) % buckets
    return {
        "unit_id": str(unit_id),
        "bucket": bucket,
        "group": "treatment" if bucket < treatment_buckets else "control",
    }


def calculate_sample_size(
    *,
    baseline_rate: float,
    mde_absolute: float,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
    two_sided: bool = True,
) -> dict[str, int | float]:
    """Required sample size for a two-independent-proportion test."""
    treatment_rate = baseline_rate + mde_absolute
    if not 0 < baseline_rate < 1 or not 0 < treatment_rate < 1:
        raise ValueError("baseline_rate and baseline_rate + mde_absolute must be in (0, 1)")
    if not 0 < alpha < 1 or not 0 < power < 1 or ratio <= 0:
        raise ValueError("alpha, power and ratio are invalid")
    effect = abs(proportion_effectsize(treatment_rate, baseline_rate))
    n_control = NormalIndPower().solve_power(
        effect_size=effect,
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative="two-sided" if two_sided else "larger",
    )
    n_control_ceil = int(math.ceil(n_control))
    n_treatment_ceil = int(math.ceil(n_control * ratio))
    return {
        "baseline_rate": baseline_rate,
        "target_rate": treatment_rate,
        "mde_absolute": mde_absolute,
        "mde_percentage_points": mde_absolute * 100,
        "alpha": alpha,
        "power": power,
        "ratio": ratio,
        "sample_control": n_control_ceil,
        "sample_treatment": n_treatment_ceil,
        "sample_per_group": max(n_control_ceil, n_treatment_ceil),
        "sample_total": n_control_ceil + n_treatment_ceil,
        "effect_size": effect,
    }


def calculate_mde(
    *,
    baseline_rate: float,
    sample_per_group: int,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> dict[str, float | int]:
    """Numerically invert sample size to estimate detectable absolute uplift."""
    if sample_per_group < 2:
        raise ValueError("sample_per_group must be at least 2")
    low, high = 1e-7, min(1 - baseline_rate - 1e-7, 0.5)
    for _ in range(60):
        mid = (low + high) / 2
        required = calculate_sample_size(
            baseline_rate=baseline_rate,
            mde_absolute=mid,
            alpha=alpha,
            power=power,
            two_sided=two_sided,
        )["sample_per_group"]
        if int(required) > sample_per_group:
            low = mid
        else:
            high = mid
    return {
        "baseline_rate": baseline_rate,
        "sample_per_group": sample_per_group,
        "mde_absolute": high,
        "mde_percentage_points": high * 100,
        "alpha": alpha,
        "power": power,
    }


def calculate_duration(
    *,
    required_sample_total: int,
    eligible_users_per_day: int,
    minimum_full_weeks: int = 2,
) -> dict[str, int | str]:
    if required_sample_total <= 0 or eligible_users_per_day <= 0:
        raise ValueError("Sample size and daily traffic must be positive")
    traffic_days = math.ceil(required_sample_total / eligible_users_per_day)
    business_cycle_days = math.ceil(traffic_days / 7) * 7
    recommended_days = max(business_cycle_days, minimum_full_weeks * 7)
    return {
        "traffic_days": traffic_days,
        "recommended_days": recommended_days,
        "recommended_weeks": math.ceil(recommended_days / 7),
        "note": "Run through complete weekly cycles and pre-register the end date to reduce novelty and peeking bias.",
    }


def check_srm(
    observed: Sequence[int],
    *,
    expected_proportions: Sequence[float] | None = None,
    alpha: float = 0.05,
) -> dict[str, Any]:
    values = np.asarray(observed, dtype=float)
    if values.ndim != 1 or len(values) < 2 or np.any(values < 0) or values.sum() == 0:
        raise ValueError("observed must contain at least two non-negative group counts")
    proportions = np.asarray(
        expected_proportions or np.repeat(1 / len(values), len(values)), dtype=float
    )
    if len(proportions) != len(values) or np.any(proportions <= 0):
        raise ValueError("expected_proportions do not match observed groups")
    proportions = proportions / proportions.sum()
    expected = values.sum() * proportions
    if np.any(expected < 5):
        return {
            "applicable": False,
            "pass": None,
            "p_value": None,
            "observed": values.astype(int).tolist(),
            "expected": expected.tolist(),
            "warning": "Expected frequency below 5; asymptotic chi-square SRM result is not reliable.",
        }
    statistic, p_value = chisquare(values, f_exp=expected)
    return {
        "applicable": True,
        "pass": bool(p_value >= alpha),
        "statistic": float(statistic),
        "p_value": float(p_value),
        "alpha": alpha,
        "observed": values.astype(int).tolist(),
        "expected": expected.tolist(),
        "warning": None
        if p_value >= alpha
        else "Sample ratio mismatch detected; investigate assignment and tracking before interpreting outcomes.",
    }


def balance_categorical(
    control_counts: Mapping[str, int],
    treatment_counts: Mapping[str, int],
    *,
    alpha: float = 0.05,
    practical_threshold: float = 0.02,
) -> dict[str, Any]:
    categories = sorted(set(control_counts) | set(treatment_counts))
    table = np.asarray(
        [
            [control_counts.get(category, 0) for category in categories],
            [treatment_counts.get(category, 0) for category in categories],
        ],
        dtype=float,
    )
    valid = table.sum(axis=0) > 0
    table = table[:, valid]
    categories = [value for value, keep in zip(categories, valid, strict=True) if keep]
    if table.shape[1] < 2 or np.any(table.sum(axis=1) == 0):
        return {
            "applicable": False,
            "pass": None,
            "warning": "At least two populated categories per group are required.",
            "categories": categories,
        }
    statistic, p_value, _, expected = chi2_contingency(table)
    control_share = table[0] / table[0].sum()
    treatment_share = table[1] / table[1].sum()
    max_diff = float(np.max(np.abs(control_share - treatment_share)))
    reliable = bool(np.all(expected >= 5))
    passed = bool(max_diff <= practical_threshold and (p_value >= alpha or not reliable))
    return {
        "applicable": reliable,
        "pass": passed,
        "p_value": float(p_value) if reliable else None,
        "statistic": float(statistic) if reliable else None,
        "max_absolute_share_difference": max_diff,
        "practical_threshold": practical_threshold,
        "categories": [
            {
                "category": category,
                "control_share": float(control_share[index]),
                "treatment_share": float(treatment_share[index]),
                "absolute_difference": float(abs(control_share[index] - treatment_share[index])),
            }
            for index, category in enumerate(categories)
        ],
        "warning": None
        if passed
        else "Covariate composition differs between groups; inspect randomization and stratified estimates.",
    }


def _difference_confidence_interval(
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    alpha: float,
) -> tuple[float, float]:
    control_rate = control_successes / control_n
    treatment_rate = treatment_successes / treatment_n
    difference = treatment_rate - control_rate
    standard_error = math.sqrt(
        treatment_rate * (1 - treatment_rate) / treatment_n
        + control_rate * (1 - control_rate) / control_n
    )
    critical = norm.ppf(1 - alpha / 2)
    return difference - critical * standard_error, difference + critical * standard_error


def _guardrail_results(
    guardrails: Sequence[Mapping[str, Any]] | None,
) -> tuple[list[dict[str, Any]], bool]:
    output = []
    all_pass = True
    for item in guardrails or []:
        control = float(item["control_value"])
        treatment = float(item["treatment_value"])
        tolerance = float(item.get("tolerance", 0.0))
        direction = str(item.get("desired_direction", "higher"))
        if direction == "higher":
            passed = treatment >= control - tolerance
        elif direction == "lower":
            passed = treatment <= control + tolerance
        else:
            raise ValueError("desired_direction must be higher or lower")
        all_pass = all_pass and passed
        output.append(
            {
                "name": str(item["name"]),
                "control_value": control,
                "treatment_value": treatment,
                "absolute_change": treatment - control,
                "desired_direction": direction,
                "tolerance": tolerance,
                "pass": passed,
            }
        )
    return output, all_pass


def analyze_experiment(
    *,
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    alpha: float = 0.05,
    business_mde_absolute: float = 0.0,
    expected_ratio: float = 1.0,
    guardrails: Sequence[Mapping[str, Any]] | None = None,
    alternative: Literal["two-sided", "larger", "smaller"] = "two-sided",
) -> dict[str, Any]:
    for successes, total in ((control_successes, control_n), (treatment_successes, treatment_n)):
        if total <= 0 or not 0 <= successes <= total:
            raise ValueError("Successes must be in [0, n], and n must be positive")
    control_rate = control_successes / control_n
    treatment_rate = treatment_successes / treatment_n
    absolute = treatment_rate - control_rate
    relative = None if control_rate == 0 else absolute / control_rate
    z_stat, p_value = proportions_ztest(
        [treatment_successes, control_successes],
        [treatment_n, control_n],
        alternative=alternative,
    )
    ci_low, ci_high = _difference_confidence_interval(
        control_successes, control_n, treatment_successes, treatment_n, alpha
    )
    srm = check_srm(
        [control_n, treatment_n],
        expected_proportions=[1 / (1 + expected_ratio), expected_ratio / (1 + expected_ratio)],
        alpha=alpha,
    )
    guardrail_items, guardrails_pass = _guardrail_results(guardrails)
    statistical = bool(p_value < alpha)
    business = bool(absolute >= business_mde_absolute)
    valid_assignment = srm["pass"] is not False
    if not valid_assignment:
        decision = "investigate_assignment"
    elif not guardrails_pass:
        decision = "do_not_launch_guardrail_regression"
    elif statistical and business and absolute > 0:
        decision = "launch"
    elif statistical and absolute > 0:
        decision = "continue_or_reassess_business_value"
    elif not statistical:
        decision = "continue_to_preregistered_end_or_stop_inconclusive"
    else:
        decision = "do_not_launch"
    return {
        "rates": {"control": control_rate, "treatment": treatment_rate},
        "counts": {
            "control_successes": control_successes,
            "control_n": control_n,
            "treatment_successes": treatment_successes,
            "treatment_n": treatment_n,
        },
        "absolute_uplift": absolute,
        "absolute_uplift_pp": absolute * 100,
        "relative_uplift": relative,
        "relative_uplift_pct": None if relative is None else relative * 100,
        "z_stat": float(z_stat),
        "p_value": float(p_value),
        "confidence_level": 1 - alpha,
        "confidence_interval_absolute": {"lower": ci_low, "upper": ci_high},
        "stat_significant": statistical,
        "business_significant": business,
        "business_mde_absolute": business_mde_absolute,
        "srm": srm,
        "guardrails": guardrail_items,
        "guardrails_pass": guardrails_pass,
        "decision": decision,
        "interpretation_note": "Statistical significance, practical significance, allocation validity, and guardrails are separate gates.",
        "peeking_warning": "Use the pre-registered sample size and duration; repeated unadjusted p-value checks inflate false positives.",
    }


def analyze_aa(
    *,
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    alpha: float = 0.05,
    tolerance_absolute: float = 0.005,
) -> dict[str, Any]:
    result = analyze_experiment(
        control_successes=control_successes,
        control_n=control_n,
        treatment_successes=treatment_successes,
        treatment_n=treatment_n,
        alpha=alpha,
        business_mde_absolute=tolerance_absolute,
    )
    passed = bool(
        result["srm"]["pass"] is not False
        and result["p_value"] >= alpha
        and abs(result["absolute_uplift"]) < tolerance_absolute
    )
    return {
        "metric": "invite_click_rate",
        "p_value": result["p_value"],
        "absolute_difference": result["absolute_uplift"],
        "tolerance_absolute": tolerance_absolute,
        "srm": result["srm"],
        "pass": passed,
        "action": "proceed_to_ab"
        if passed
        else "fix_assignment_metric_or_instrumentation_and_rerun_aa",
    }


def analyze_strata(strata: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare aggregate and subgroup directions to flag possible Simpson reversal."""
    if not strata:
        return {"items": [], "simpson_warning": False, "aggregate": None}
    total_cn = sum(int(row["control_n"]) for row in strata)
    total_tn = sum(int(row["treatment_n"]) for row in strata)
    total_cs = sum(int(row["control_successes"]) for row in strata)
    total_ts = sum(int(row["treatment_successes"]) for row in strata)
    aggregate_diff = total_ts / total_tn - total_cs / total_cn
    items = []
    nonzero_directions = []
    for row in strata:
        control_rate = int(row["control_successes"]) / int(row["control_n"])
        treatment_rate = int(row["treatment_successes"]) / int(row["treatment_n"])
        difference = treatment_rate - control_rate
        direction = int(np.sign(difference))
        if direction:
            nonzero_directions.append(direction)
        items.append(
            {
                "stratum": str(row["stratum"]),
                "control_rate": control_rate,
                "treatment_rate": treatment_rate,
                "absolute_uplift": difference,
                "control_share": int(row["control_n"]) / total_cn,
                "treatment_share": int(row["treatment_n"]) / total_tn,
            }
        )
    aggregate_direction = int(np.sign(aggregate_diff))
    homogeneous_subgroup_direction = (
        len(set(nonzero_directions)) == 1 if nonzero_directions else False
    )
    simpson = bool(
        homogeneous_subgroup_direction
        and aggregate_direction != 0
        and nonzero_directions[0] != aggregate_direction
    )
    return {
        "aggregate": {
            "control_rate": total_cs / total_cn,
            "treatment_rate": total_ts / total_tn,
            "absolute_uplift": aggregate_diff,
        },
        "items": items,
        "simpson_warning": simpson,
        "heterogeneity_warning": len(set(nonzero_directions)) > 1,
        "note": "A warning prompts stratified review; it is not by itself proof of a causal identification failure.",
    }
