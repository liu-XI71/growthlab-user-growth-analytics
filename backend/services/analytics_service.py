from __future__ import annotations

from typing import Any

from analytics.decomposition import mix_shift_decomposition
from analytics.experimentation import (
    analyze_aa,
    analyze_experiment,
    analyze_strata,
    balance_categorical,
    calculate_duration,
    calculate_sample_size,
)
from analytics.funnel import build_funnel, compare_funnels, diagnose_funnel
from analytics.metrics import METRIC_DEFINITIONS, metric_tree
from analytics.monitoring import analyze_growth_trend
from analytics.roi import calculate_roi, sensitivity_analysis
from backend.database import query_df, query_records
from backend.schemas.api import ExperimentAnalysisRequest, RoiSensitivityRequest

REFERRAL_STEPS = [
    "campaign_exposure",
    "campaign_click",
    "invite_click",
    "share_success",
    "new_user_landing",
    "new_user_register",
    "new_user_activate",
]
FUNNEL_COLUMN_MAP = {
    "campaign_exposure": "exposure_uv",
    "campaign_click": "page_click_uv",
    "invite_click": "invite_click_uv",
    "share_success": "share_success_uv",
    "new_user_landing": "new_user_landing_uv",
    "new_user_register": "new_user_register_uv",
    "new_user_activate": "new_user_activate_uv",
}
ALLOWED_DIMENSIONS = {
    "channel",
    "device_type",
    "device_brand",
    "os_name",
    "system_version",
    "region",
    "product_version",
}


def list_metrics() -> dict[str, Any]:
    return {"items": METRIC_DEFINITIONS, "count": len(METRIC_DEFINITIONS)}


def get_metric_tree() -> dict[str, Any]:
    tree = metric_tree()
    tree.update({"current_value": 100.0, "target_value": 120.0})
    return tree


def growth_trend(metric: str = "dau_index") -> dict[str, Any]:
    frame = query_df("SELECT * FROM growth_daily ORDER BY date")
    result = analyze_growth_trend(frame, metric=metric)
    result["synthetic_data"] = True
    return result


def _referral_counts(version: str) -> dict[str, int]:
    records = query_records(
        "SELECT * FROM referral_version_summary WHERE version = $version", {"version": version}
    )
    if not records:
        raise LookupError(f"Unknown referral version: {version}")
    row = records[0]
    return {step: int(row[column]) for step, column in FUNNEL_COLUMN_MAP.items()}


def referral_summary(version: str) -> dict[str, Any]:
    records = query_records(
        "SELECT * FROM referral_version_summary WHERE version = $version", {"version": version}
    )
    if not records:
        raise LookupError(f"Unknown referral version: {version}")
    return {"version": version, "kpis": records[0], "synthetic_data": True}


def referral_funnel(version: str, baseline_version: str = "variant_a") -> dict[str, Any]:
    counts = _referral_counts(version)
    funnel = build_funnel(counts, REFERRAL_STEPS)
    response: dict[str, Any] = {"version": version, "steps": funnel, "synthetic_data": True}
    if version != baseline_version:
        comparison = compare_funnels(_referral_counts(baseline_version), counts, REFERRAL_STEPS)
        response.update(
            {
                "baseline_version": baseline_version,
                "comparison": comparison,
                "diagnosis": diagnose_funnel(comparison),
            }
        )
    return response


def referral_versions() -> dict[str, Any]:
    items = query_records("SELECT * FROM referral_version_summary ORDER BY version")
    labels = {
        "variant_a": "Conservative incentive / focused interface",
        "variant_b": "Higher incentive / dense interface",
        "variant_c": "Higher incentive / simplified interface",
    }
    for item in items:
        item["label"] = labels.get(str(item["version"]), str(item["version"]))
    return {"versions": items, "synthetic_data": True}


def roi_summary(version: str) -> dict[str, Any]:
    records = query_records(
        """
        SELECT version,
               AVG(active_days_30) AS active_days_30,
               AVG(daily_active_hours) AS daily_active_hours,
               AVG(value_per_hour) AS value_per_hour,
               AVG(retention_discount) AS retention_discount,
               AVG(incentive_cost) AS incentive_cost_per_acquisition,
               AVG(ltv30) AS observed_average_ltv30,
               COUNT(*) AS acquired_users
        FROM acquired_users WHERE version = $version GROUP BY version
        """,
        {"version": version},
    )
    if not records:
        raise LookupError(f"Unknown referral version: {version}")
    inputs = records[0]
    result = calculate_roi(
        active_days_30=float(inputs["active_days_30"]),
        daily_active_hours=float(inputs["daily_active_hours"]),
        value_per_hour=float(inputs["value_per_hour"]),
        retention_discount=float(inputs["retention_discount"]),
        incentive_cost_per_acquisition=float(inputs["incentive_cost_per_acquisition"]),
    )
    observed_ltv = float(inputs["observed_average_ltv30"])
    cac = float(inputs["incentive_cost_per_acquisition"])
    result.update(
        {
            "ltv30": observed_ltv,
            "ltv_cac_ratio": observed_ltv / cac,
            "net_roi": (observed_ltv - cac) / cac,
            "break_even_cac": observed_ltv,
        }
    )
    return {"version": version, "inputs": inputs, **result, "synthetic_data": True}


def roi_sensitivity(request: RoiSensitivityRequest) -> dict[str, Any]:
    result = sensitivity_analysis(request.base.model_dump(), request.variations)
    result["synthetic_data"] = True
    return result


def retention_summary(period: str) -> dict[str, Any]:
    items = query_records(
        "SELECT * FROM retention_summary WHERE period = $period", {"period": period}
    )
    if not items:
        raise LookupError(f"Unknown period: {period}")
    item = items[0]
    return {
        "period": period,
        **item,
        "metric_note": "D7 is exact-day retention; D1-7 is a window metric.",
        "synthetic_data": True,
    }


def retention_cohorts(period: str = "current") -> dict[str, Any]:
    if period not in {"baseline", "current"}:
        raise LookupError(f"Unknown period: {period}")
    items = query_records(
        """
        SELECT CAST(DATE_TRUNC('week', signup_date) AS DATE) AS cohort_week,
               COUNT(*) AS users,
               AVG(retained_d1::INTEGER) AS d1,
               AVG(retained_d3::INTEGER) AS d3,
               AVG(retained_d7::INTEGER) AS d7,
               AVG(retained_d30::INTEGER) AS d30
        FROM new_user_retention
        WHERE period = $period
        GROUP BY 1 ORDER BY 1
        """,
        {"period": period},
    )
    return {
        "period": period,
        "items": items,
        "definition": {
            "inclusion": "signup week",
            "return": "any qualifying active event on the exact relative day",
            "grain": "calendar week × exact relative day",
        },
        "censoring_warning": "Only report a relative-day cell after the cohort has fully matured through that day.",
        "synthetic_data": True,
    }


def retention_segments(period: str, dimension: str) -> dict[str, Any]:
    if dimension not in ALLOWED_DIMENSIONS:
        raise ValueError(f"Unsupported dimension. Choose from: {sorted(ALLOWED_DIMENSIONS)}")
    sql = f"""
        SELECT {dimension} AS segment, COUNT(*) AS users,
               AVG(retained_d1::INTEGER) AS d1,
               AVG(retained_d3::INTEGER) AS d3,
               AVG(retained_d7::INTEGER) AS d7,
               AVG(retained_d1_7_window::INTEGER) AS d1_7_window,
               AVG(retained_d30::INTEGER) AS d30
        FROM new_user_retention WHERE period = $period
        GROUP BY {dimension} ORDER BY users DESC
    """
    return {
        "period": period,
        "dimension": dimension,
        "items": query_records(sql, {"period": period}),
        "synthetic_data": True,
    }


def retention_decomposition(dimension: str) -> dict[str, Any]:
    if dimension not in ALLOWED_DIMENSIONS:
        raise ValueError(f"Unsupported dimension. Choose from: {sorted(ALLOWED_DIMENSIONS)}")
    frame = query_df(f"SELECT period, {dimension}, retained_d1_7_window FROM new_user_retention")
    result = mix_shift_decomposition(
        frame,
        segment_col=dimension,
        period_col="period",
        outcome_col="retained_d1_7_window",
        baseline_period="baseline",
        current_period="current",
    )
    result.update({"dimension": dimension, "synthetic_data": True})
    return result


def retention_funnel(period: str) -> dict[str, Any]:
    row = query_records(
        """
        SELECT COUNT(*) AS first_open,
               SUM(register::INTEGER) AS register,
               SUM(home_view::INTEGER) AS home_view,
               SUM(content_view::INTEGER) AS content_view,
               SUM(content_interaction::INTEGER) AS content_interaction,
               SUM(save_or_follow::INTEGER) AS save_or_follow,
               SUM(return_visit::INTEGER) AS return_visit
        FROM new_user_funnel WHERE period = $period
        """,
        {"period": period},
    )
    if not row:
        raise LookupError(f"Unknown period: {period}")
    counts = {key: int(value) for key, value in row[0].items()}
    steps = list(counts)
    response: dict[str, Any] = {
        "period": period,
        "steps": build_funnel(counts, steps),
        "synthetic_data": True,
    }
    if period != "baseline":
        baseline = retention_funnel("baseline")
        baseline_counts = {item["step"]: item["uv"] for item in baseline["steps"]}
        comparison = compare_funnels(baseline_counts, counts, steps)
        response["comparison"] = comparison
        response["diagnosis"] = {
            "facts": [
                "No large first-session step deterioration is present in the generated scenario."
            ],
            "interpretation": "Current evidence does not show that first-use friction is the main retention driver.",
            "caution": "Absence of a visible funnel decline does not prove the product path has no issues.",
        }
    return response


def feature_analysis() -> dict[str, Any]:
    items = query_records(
        """
        SELECT benchmark_user, COUNT(*) AS users,
               AVG(feature_used::INTEGER) AS feature_penetration,
               AVG(feature_use_count) AS average_feature_uses,
               AVG(retained_d1_7_window::INTEGER) AS d1_7_window_retention,
               AVG(active_days_30) AS average_active_days_30,
               AVG(daily_active_hours) AS average_daily_hours
        FROM feature_usage GROUP BY benchmark_user ORDER BY benchmark_user DESC
        """
    )
    return {
        "benchmark_definition": "Top-quartile active days AND top-quartile daily active hours.",
        "items": items,
        "causality_warning": "Observed feature penetration is correlational. Self-selection and user propensity can explain the difference; use random assignment for causal claims.",
        "possible_confounders": [
            "acquisition_channel",
            "device_type",
            "interest_intensity",
            "prior_engagement",
        ],
        "synthetic_data": True,
    }


def list_experiments() -> dict[str, Any]:
    definitions = query_records("SELECT * FROM experiment_definitions ORDER BY experiment_id")
    summaries = query_records("SELECT * FROM experiment_summary ORDER BY experiment_id, group_name")
    by_id: dict[str, list[dict[str, Any]]] = {}
    for summary in summaries:
        by_id.setdefault(str(summary["experiment_id"]), []).append(summary)
    for definition in definitions:
        definition["groups"] = by_id.get(str(definition["experiment_id"]), [])
    return {"items": definitions, "synthetic_data": True}


def _experiment_inputs_from_db(
    experiment_id: str,
) -> tuple[dict[str, Any], dict[str, int], list[dict[str, Any]]]:
    definitions = query_records(
        "SELECT * FROM experiment_definitions WHERE experiment_id = $experiment_id",
        {"experiment_id": experiment_id},
    )
    if not definitions:
        raise LookupError(f"Unknown experiment: {experiment_id}")
    rows = query_records(
        "SELECT * FROM experiment_summary WHERE experiment_id = $experiment_id",
        {"experiment_id": experiment_id},
    )
    groups = {str(row["group_name"]): row for row in rows}
    if not {"control", "treatment"}.issubset(groups):
        raise LookupError("Experiment does not contain both groups")
    counts = {
        "control_successes": int(groups["control"]["successes"]),
        "control_n": int(groups["control"]["users"]),
        "treatment_successes": int(groups["treatment"]["successes"]),
        "treatment_n": int(groups["treatment"]["users"]),
    }
    guardrails = [
        {
            "name": "new_user_value_guardrail"
            if "referral" in experiment_id
            else "negative_feedback_guardrail",
            "control_value": float(groups["control"]["guardrail_value"]),
            "treatment_value": float(groups["treatment"]["guardrail_value"]),
            "desired_direction": "higher" if "referral" in experiment_id else "lower",
            "tolerance": 0.03 if "referral" in experiment_id else 0.002,
        }
    ]
    return definitions[0], counts, guardrails


def _dimension_balance(experiment_id: str) -> list[dict[str, Any]]:
    results = []
    for dimension in ("channel", "device_type", "region"):
        rows = query_records(
            f"""
            SELECT group_name, {dimension} AS category, COUNT(*) AS users
            FROM experiment_assignments WHERE experiment_id = $experiment_id
            GROUP BY group_name, {dimension}
            """,
            {"experiment_id": experiment_id},
        )
        control = {
            str(row["category"]): int(row["users"])
            for row in rows
            if row["group_name"] == "control"
        }
        treatment = {
            str(row["category"]): int(row["users"])
            for row in rows
            if row["group_name"] == "treatment"
        }
        results.append({"dimension": dimension, **balance_categorical(control, treatment)})
    return results


def _stratified_results(experiment_id: str, dimension: str = "device_type") -> dict[str, Any]:
    rows = query_records(
        f"""
        SELECT a.{dimension} AS stratum, o.group_name, COUNT(*) AS users,
               SUM(o.primary_outcome::INTEGER) AS successes
        FROM experiment_outcomes o JOIN experiment_assignments a
          USING (experiment_id, user_id, group_name)
        WHERE o.experiment_id = $experiment_id
        GROUP BY a.{dimension}, o.group_name
        """,
        {"experiment_id": experiment_id},
    )
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["stratum"]), {})[str(row["group_name"])] = row
    strata = []
    for stratum, groups in grouped.items():
        if {"control", "treatment"}.issubset(groups):
            strata.append(
                {
                    "stratum": stratum,
                    "control_n": int(groups["control"]["users"]),
                    "control_successes": int(groups["control"]["successes"]),
                    "treatment_n": int(groups["treatment"]["users"]),
                    "treatment_successes": int(groups["treatment"]["successes"]),
                }
            )
    return analyze_strata(strata)


def _aa_status() -> dict[str, Any]:
    _, counts, _ = _experiment_inputs_from_db("referral_aa_validation")
    return analyze_aa(**counts)


def analyze_experiment_request(request: ExperimentAnalysisRequest) -> dict[str, Any]:
    definition: dict[str, Any] = {}
    guardrails = [item.model_dump() for item in request.guardrails]
    experiment_id = request.experiment_id
    if experiment_id:
        definition, stored_counts, stored_guardrails = _experiment_inputs_from_db(experiment_id)
        explicit_counts = all(
            value is not None
            for value in (
                request.control_successes,
                request.control_n,
                request.treatment_successes,
                request.treatment_n,
            )
        )
        counts = (
            {
                "control_successes": int(request.control_successes),
                "control_n": int(request.control_n),
                "treatment_successes": int(request.treatment_successes),
                "treatment_n": int(request.treatment_n),
            }
            if explicit_counts
            else stored_counts
        )
        if not guardrails:
            guardrails = stored_guardrails
    else:
        counts = {
            "control_successes": int(request.control_successes or 0),
            "control_n": int(request.control_n or 0),
            "treatment_successes": int(request.treatment_successes or 0),
            "treatment_n": int(request.treatment_n or 0),
        }
    baseline = float(
        request.baseline_rate
        or definition.get("baseline_rate")
        or counts["control_successes"] / counts["control_n"]
    )
    mde = float(request.mde_absolute or definition.get("mde_absolute") or 0.01)
    alpha = float(
        request.alpha
        if request.alpha != 0.05 or not definition
        else definition.get("alpha", request.alpha)
    )
    power = float(
        request.power
        if request.power != 0.80 or not definition
        else definition.get("power", request.power)
    )
    traffic = int(definition.get("daily_eligible_users", request.eligible_users_per_day))
    sample = calculate_sample_size(
        baseline_rate=baseline, mde_absolute=mde, alpha=alpha, power=power
    )
    duration = calculate_duration(
        required_sample_total=int(sample["sample_total"]),
        eligible_users_per_day=traffic,
        minimum_full_weeks=request.minimum_full_weeks,
    )
    ab = analyze_experiment(
        **counts,
        alpha=alpha,
        business_mde_absolute=mde,
        expected_ratio=request.expected_treatment_ratio,
        guardrails=guardrails,
    )
    observed_days = (
        request.observed_days if request.observed_days is not None else (14 if experiment_id else 0)
    )
    sample_size_reached = bool(
        counts["control_n"] >= int(sample["sample_control"])
        and counts["treatment_n"] >= int(sample["sample_treatment"])
    )
    duration_reached = bool(observed_days >= int(duration["recommended_days"]))
    ab["sample_size_reached"] = sample_size_reached
    ab["duration_reached"] = duration_reached
    ab["observed_days"] = observed_days
    if ab["decision"] == "launch" and not (sample_size_reached and duration_reached):
        ab["decision"] = "continue_to_preregistered_sample_and_duration"
    dimension_checks = _dimension_balance(experiment_id) if experiment_id else []
    stratified = (
        _stratified_results(experiment_id)
        if experiment_id
        else {"simpson_warning": False, "items": []}
    )
    aa = (
        _aa_status()
        if experiment_id != "referral_aa_validation"
        else analyze_aa(**counts, alpha=alpha)
    )
    core_metric = str(request.core_metric or definition.get("core_metric") or "conversion_rate")
    design = {
        "objective": request.objective
        or definition.get("objective")
        or "Evaluate incremental impact on the primary metric.",
        "strategy": request.strategy
        or definition.get("strategy")
        or "Randomized treatment versus existing experience.",
        "core_metric": core_metric,
        "business_metric": request.business_metric
        or definition.get("business_metric")
        or "business_outcome",
        "guardrails": [item["name"] for item in guardrails],
        "related_metrics": [
            "referral_activation_rate",
            "users_per_inviter",
            "new_user_visit_frequency",
            "new_user_retention",
        ],
        "baseline": baseline,
        "mde": mde,
        "alpha": alpha,
        "power": power,
        "required_sample_per_group": sample["sample_per_group"],
        "required_sample_total": sample["sample_total"],
        "recommended_days": duration["recommended_days"],
        "recommended_weeks": duration["recommended_weeks"],
        "duration_note": duration["note"],
    }
    return {
        "experiment_id": experiment_id or "ad_hoc_analysis",
        "design": design,
        "assignment": {
            "unit": "user_id",
            "method": "SHA-256 hash(user_id + experiment_salt) modulo 100",
            "buckets": 100,
            "ratio": "1:1",
            "stability_note": "The same user and salt always map to the same bucket during the experiment.",
        },
        "balance": {
            "overall_srm": ab["srm"],
            "dimension_checks": dimension_checks,
            "stratified_results": stratified,
            "simpson_warning": bool(stratified.get("simpson_warning", False)),
        },
        "aa": aa,
        "ab": ab,
        "risks": {
            "novelty": "Keep the pre-registered duration through full business cycles; inspect stability by week.",
            "network": "If invitation treatment can spill over, consider cluster randomization by non-overlapping social or geographic clusters.",
            "peeking": "Monitor guardrails, but do not stop on repeated unadjusted p-value checks before the pre-registered end.",
            "composition": "Check channel, device and region before and after the experiment; report stratified effects.",
        },
        "decision": ab["decision"],
        "synthetic_data": True,
    }


def data_quality_status() -> dict[str, Any]:
    items = query_records(
        """
        SELECT * FROM data_quality_runs
        WHERE checked_at = (SELECT MAX(checked_at) FROM data_quality_runs)
        ORDER BY status DESC, check_name
        """
    )
    failed = sum(item["status"] != "pass" for item in items)
    return {
        "status": "pass" if items and failed == 0 else "fail",
        "checks": items,
        "check_count": len(items),
        "failed_count": failed,
        "synthetic_data": True,
    }
