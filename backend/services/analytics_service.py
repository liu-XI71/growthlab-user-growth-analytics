from __future__ import annotations

from typing import Any

from analytics.decisions import build_decision_card
from analytics.decomposition import mix_shift_decomposition
from analytics.economics import budget_curve, parametric_bootstrap_difference
from analytics.experimentation import (
    analyze_aa,
    analyze_experiment,
    analyze_strata,
    balance_categorical,
    balance_smd,
    benjamini_hochberg,
    calculate_duration,
    calculate_sample_size,
    check_srm,
    itt_quality_effects,
    proportion_effect,
)
from analytics.funnel import build_funnel, compare_funnels, diagnose_funnel
from analytics.lifecycle import lifecycle_funnel
from analytics.metrics import METRIC_DEFINITIONS, metric_tree
from analytics.monitoring import analyze_growth_trend
from analytics.roi import calculate_roi, sensitivity_analysis
from backend.database import query_df, query_records
from backend.schemas.api import (
    EconomicsScenarioRequest,
    ExperimentAnalysisRequest,
    RoiSensitivityRequest,
)

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


def metric_lineage(metric_name: str) -> dict[str, Any]:
    records = query_records(
        "SELECT * FROM metric_definitions WHERE metric_name = $metric_name",
        {"metric_name": metric_name},
    )
    if not records:
        raise LookupError(f"Unknown governed metric: {metric_name}")
    metric = records[0]
    evidence = {
        "incremental_d7_retained_per_10k_assigned": {
            "source": "experiment assignment → referral edge → exact-day user activity",
            "mart": "mart_experiment_user_value",
            "sql": "sql/experiments/quality_adjusted_effects.sql",
        },
        "incremental_d1_7_retained_per_10k_assigned": {
            "source": "experiment assignment → referral edge → day 1-7 user activity",
            "mart": "mart_experiment_user_value",
            "sql": "sql/experiments/quality_adjusted_effects.sql",
        },
        "incremental_contribution30_per_10k_assigned": {
            "source": "experiment assignment → referral edge → user-day value − all variable costs",
            "mart": "mart_experiment_user_value",
            "sql": "sql/experiments/quality_adjusted_effects.sql",
        },
    }.get(
        metric_name,
        {
            "source": str(metric.get("source_table") or "governed source table"),
            "mart": str(metric.get("source_table") or "metric_definitions"),
            "sql": str(metric.get("sql_model") or "governed SQL model"),
        },
    )
    return {
        "metric": metric,
        "lineage": [
            {"order": 1, "node": "source", "label": evidence["source"]},
            {"order": 2, "node": "mart", "label": evidence["mart"]},
            {"order": 3, "node": "metric_contract", "label": metric_name},
            {"order": 4, "node": "decision", "label": str(metric.get("decision_use"))},
        ],
        "sql_evidence": evidence["sql"],
        "synthetic_data": True,
    }


def _itt_arm_rows(experiment_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = query_records(
        "SELECT * FROM mart_experiment_effects_itt WHERE experiment_id=$experiment_id",
        {"experiment_id": experiment_id},
    )
    groups = {str(row["group_name"]): row for row in rows}
    if not {"control", "treatment"}.issubset(groups):
        raise LookupError(f"Experiment does not have both randomized arms: {experiment_id}")
    return groups["control"], groups["treatment"]


def lifecycle_summary(experiment_id: str = "referral_ui_simplification") -> dict[str, Any]:
    control, treatment = _itt_arm_rows(experiment_id)
    totals = {
        key: int(control[key]) + int(treatment[key])
        for key in (
            "assigned_users",
            "exposed_users",
            "primary_successes",
            "activated_new_users",
            "retained_d1_7_window_users",
            "retained_d7_users",
        )
    }
    steps = lifecycle_funnel(
        [
            {
                "step": "eligible_assignment",
                "label": "合格且已分流老用户",
                "users": totals["assigned_users"],
            },
            {
                "step": "tracked_exposure",
                "label": "实际看到活动界面",
                "users": totals["exposed_users"],
            },
            {"step": "invite_click", "label": "点击邀请", "users": totals["primary_successes"]},
            {
                "step": "new_user_activate",
                "label": "新用户激活",
                "users": totals["activated_new_users"],
            },
            {
                "step": "d1_7_retained",
                "label": "D1-7窗口留存新用户",
                "users": totals["retained_d1_7_window_users"],
            },
            {
                "step": "d7_retained",
                "label": "精确D7留存新用户",
                "users": totals["retained_d7_users"],
            },
        ]
    )
    quality_effects = itt_quality_effects(control, treatment)
    trend = growth_trend()
    latest = trend.get("latest", {})
    return {
        "experiment_id": experiment_id,
        "title": "Quality-adjusted referral growth decision",
        "north_star": "incremental high-quality retained users and contribution value",
        "goal": {
            "current_dau_index": latest.get("dau_index"),
            "target_dau_index": latest.get("target_index"),
            "gap_index": float(latest.get("dau_index", 0)) - float(latest.get("target_index", 0)),
        },
        "lifecycle": steps,
        "quality_adjusted_effects": quality_effects,
        "mechanism_metric": "invite_click_rate",
        "final_metrics": [
            "incremental_d7_retained_per_10k_assigned",
            "incremental_d1_7_retained_per_10k_assigned",
            "incremental_contribution30_per_10k_assigned",
        ],
        "guided_flow": [
            {"minute": "0:00", "gate": "G", "question": "What is the growth gap?"},
            {"minute": "0:25", "gate": "R", "question": "Can the metrics be trusted?"},
            {"minute": "0:50", "gate": "O", "question": "Where is the lifecycle bottleneck?"},
            {"minute": "1:20", "gate": "W", "question": "What mechanism could explain it?"},
            {"minute": "1:50", "gate": "T", "question": "Did the randomized strategy cause lift?"},
            {
                "minute": "2:30",
                "gate": "H",
                "question": "Did quality and contribution justify shipping?",
            },
        ],
        "growth_gate": "G→R→O→W→T→H",
        "evidence_level": "randomized ITT for effects; descriptive for campaign history",
        "claim_boundary": (
            "The lifecycle is linked at invitee identity. ITT uses every eligible assignment; "
            "tracked exposure is a diagnostic denominator only."
        ),
        "synthetic_data": True,
    }


def lifecycle_cohorts(source_kind: str = "all") -> dict[str, Any]:
    if source_kind not in {"all", "descriptive_campaign", "randomized_experiment"}:
        raise ValueError("Unsupported source_kind")
    predicate = "" if source_kind == "all" else "WHERE source_kind=$source_kind"
    snapshot = query_records("SELECT * FROM analysis_snapshot LIMIT 1")[0]
    items = query_records(
        f"""
        SELECT CAST(DATE_TRUNC('week', activated_date) AS DATE) AS cohort_week,
               source_kind,
               COALESCE(group_name, acquisition_campaign) AS cohort_variant,
               COUNT(*) AS activated_users,
               SUM(mature_d7::INTEGER) AS mature_d7_users,
               SUM(CASE WHEN mature_d7 AND retained_d7 THEN 1 ELSE 0 END) AS retained_d7_users,
               SUM(CASE WHEN mature_d7 AND retained_d1_7_window THEN 1 ELSE 0 END) AS retained_d1_7_window_users,
               AVG(CASE WHEN mature_d7 THEN retained_d7::INTEGER END) AS d7_retention,
               AVG(CASE WHEN mature_d7 THEN retained_d1_7_window::INTEGER END) AS d1_7_window_retention,
               SUM(mature_d30::INTEGER) AS mature_d30_users,
               SUM(CASE WHEN mature_d30 AND retained_d30 THEN 1 ELSE 0 END) AS retained_d30_users,
               AVG(CASE WHEN mature_d30 THEN retained_d30::INTEGER END) AS d30_retention,
               SUM(value30) AS value30,
               SUM(variable_acquisition_cost) AS variable_acquisition_cost,
               SUM(contribution30) AS contribution30
        FROM mart_user_lifecycle {predicate}
        GROUP BY 1,2,3 ORDER BY 1,2,3
        """,
        {"source_kind": source_kind} if source_kind != "all" else {},
    )
    for item in items:
        item["immature_d7_users"] = int(item["activated_users"]) - int(item["mature_d7_users"])
        item["immature_d30_users"] = int(item["activated_users"]) - int(item["mature_d30_users"])
        item["as_of_date"] = snapshot["as_of_date"]
    return {
        "items": items,
        "source_kind": source_kind,
        "invitee_identity": "referral_edges.new_user_id is the canonical invitee user_id",
        "maturity_rule": "D7/D30 cells use only fully matured invitees; immature D30 is NULL, never false.",
        "horizons": {
            "d7": "exact qualifying activity on relative day 7",
            "d1_7_window": "at least one qualifying activity on relative day 1 through 7",
            "d30": "exact qualifying activity on relative day 30",
            "as_of_date": snapshot["as_of_date"],
        },
        "evidence_level": "descriptive cohort evidence",
        "synthetic_data": True,
    }


def acquisition_quality() -> dict[str, Any]:
    items = query_records(
        "SELECT * FROM mart_acquisition_quality ORDER BY acquisition_source, acquisition_campaign, acquisition_treatment"
    )
    return {
        "items": items,
        "metric_definition": {
            "average_ltv_cac": "SUM(value30) / SUM(all variable acquisition cost) among acquired users",
            "d7_retention": "exact-day D7 among matured acquired users",
        },
        "evidence_level": "descriptive",
        "causal_claim_allowed": False,
        "claim_boundary": (
            "Campaign-version rows were launched in different periods and are not incremental estimates. "
            "Use the randomized experiment endpoint for causal effects."
        ),
        "synthetic_data": True,
    }


def investigation_paths(acquisition_source: str = "all") -> dict[str, Any]:
    allowed = {"all", "non_referral", "referral_campaign", "referral_experiment"}
    if acquisition_source not in allowed:
        raise ValueError(f"Unsupported acquisition_source. Choose from {sorted(allowed)}")
    predicate = "" if acquisition_source == "all" else "WHERE u.acquisition_source=$source"
    items = query_records(
        f"""
        SELECT CONCAT(
                 'open>',
                 CASE WHEN f.register THEN 'register>' ELSE 'exit_register' END,
                 CASE WHEN f.home_view THEN 'home>' ELSE '' END,
                 CASE WHEN f.content_view THEN 'content>' ELSE '' END,
                 CASE WHEN f.content_interaction THEN 'interact>' ELSE '' END,
                 CASE WHEN f.save_or_follow THEN 'save>' ELSE '' END,
                 CASE WHEN f.return_visit THEN 'return' ELSE 'exit' END
               ) AS path_signature,
               COUNT(*) AS users,
               AVG(r.retained_d1_7_window::INTEGER) AS d1_7_window_retention
        FROM new_user_funnel f
        JOIN users u USING(user_id)
        JOIN new_user_retention r USING(user_id)
        {predicate}
        GROUP BY 1 ORDER BY users DESC LIMIT 12
        """,
        {"source": acquisition_source} if acquisition_source != "all" else {},
    )
    return {
        "items": items,
        "acquisition_source": acquisition_source,
        "evidence_level": "descriptive path evidence",
        "claim_boundary": "Paths can localize friction but do not identify a product-change effect.",
        "synthetic_data": True,
    }


def experiment_health(experiment_id: str) -> dict[str, Any]:
    definitions = query_records(
        "SELECT * FROM experiment_definitions WHERE experiment_id=$experiment_id",
        {"experiment_id": experiment_id},
    )
    if not definitions:
        raise LookupError(f"Unknown experiment: {experiment_id}")
    flow = query_records(
        """
        SELECT group_name,
               COUNT(*) AS assigned,
               SUM(was_exposed::INTEGER) AS exposed,
               SUM(outcome_observable::INTEGER) AS observable,
               SUM(primary_outcome::INTEGER) AS primary_successes
        FROM mart_experiment_user_value
        WHERE experiment_id=$experiment_id GROUP BY 1 ORDER BY 1
        """,
        {"experiment_id": experiment_id},
    )
    group_flow = {str(row["group_name"]): row for row in flow}
    overall_srm = check_srm(
        [int(group_flow["control"]["assigned"]), int(group_flow["treatment"]["assigned"])]
    )
    weekly_rows = query_records(
        """
        SELECT exposure_week, group_name, COUNT(*) AS assigned
        FROM mart_experiment_user_value WHERE experiment_id=$experiment_id
        GROUP BY 1,2 ORDER BY 1,2
        """,
        {"experiment_id": experiment_id},
    )
    weekly: list[dict[str, Any]] = []
    for week in sorted({int(row["exposure_week"]) for row in weekly_rows}):
        counts = {
            str(row["group_name"]): int(row["assigned"])
            for row in weekly_rows
            if int(row["exposure_week"]) == week
        }
        weekly.append({"week": week, "srm": check_srm([counts["control"], counts["treatment"]])})
    balance = []
    for dimension in ("channel", "device_type", "region"):
        rows = query_records(
            f"""SELECT group_name, {dimension} AS category, COUNT(*) AS users
                FROM experiment_assignments WHERE experiment_id=$experiment_id
                GROUP BY 1,2""",
            {"experiment_id": experiment_id},
        )
        counts = {"control": {}, "treatment": {}}
        for row in rows:
            counts[str(row["group_name"])][str(row["category"])] = int(row["users"])
        balance.append(
            {"dimension": dimension, **balance_smd(counts["control"], counts["treatment"])}
        )
    triggered = {}
    for group_name, row in group_flow.items():
        triggered[group_name] = (
            int(row["primary_successes"]) / int(row["exposed"]) if int(row["exposed"]) else None
        )
    return {
        "experiment_id": experiment_id,
        "flow": flow,
        "overall_srm": overall_srm,
        "weekly_srm": weekly,
        "pre_treatment_balance": balance,
        "smd_threshold": 0.1,
        "primary_estimand": {
            "population": "intention_to_treat",
            "denominator_type": "assignment",
            "reason": "Preserves randomization and includes non-exposed assignments.",
        },
        "triggered_diagnostic": {
            "rates_per_exposed": triggered,
            "denominator_type": "tracked_exposure",
            "population": "post_assignment_exposed",
            "selection_bias_warning": (
                "Exposed users are a post-assignment subset. This diagnostic must not replace the ITT decision."
            ),
        },
        "network_interference": {
            "status": "unresolved_risk",
            "route": "Use non-overlapping network/geographic clusters and inference at the randomization unit.",
        },
        "growth_gate": "R — reliability before effect interpretation",
        "evidence_level": "randomization and instrumentation health",
        "synthetic_data": True,
    }


def _segment_effects(experiment_id: str) -> list[dict[str, Any]]:
    output = []
    for dimension, classification in (
        ("device_type", "pre_specified"),
        ("channel", "pre_specified"),
        ("region", "exploratory"),
    ):
        rows = query_records(
            f"""
            SELECT {dimension} AS segment, group_name, COUNT(*) AS users,
                   SUM(primary_outcome::INTEGER) AS successes
            FROM mart_experiment_user_value WHERE experiment_id=$experiment_id
            GROUP BY 1,2 ORDER BY 1,2
            """,
            {"experiment_id": experiment_id},
        )
        by_segment: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            by_segment.setdefault(str(row["segment"]), {})[str(row["group_name"])] = row
        for segment, groups in by_segment.items():
            if not {"control", "treatment"}.issubset(groups):
                continue
            result = proportion_effect(
                int(groups["control"]["successes"]),
                int(groups["control"]["users"]),
                int(groups["treatment"]["successes"]),
                int(groups["treatment"]["users"]),
            )
            output.append(
                {
                    "dimension": dimension,
                    "segment": segment,
                    "classification": classification,
                    **result,
                }
            )
    adjusted = benjamini_hochberg([float(item["p_value"]) for item in output])
    for item, adjusted_p in zip(output, adjusted, strict=True):
        item["adjusted_p_value"] = adjusted_p
        item["multiplicity_method"] = "Benjamini-Hochberg across displayed segment estimates"
        item["heterogeneity_claim"] = "not_claimed_from_subgroup_significance"
    return output


def experiment_effects(experiment_id: str) -> dict[str, Any]:
    control, treatment = _itt_arm_rows(experiment_id)
    primary = proportion_effect(
        int(control["primary_successes"]),
        int(control["assigned_users"]),
        int(treatment["primary_successes"]),
        int(treatment["assigned_users"]),
    )
    quality = itt_quality_effects(control, treatment)
    d7_test = proportion_effect(
        int(control["retained_d7_users"]),
        int(control["assigned_users"]),
        int(treatment["retained_d7_users"]),
        int(treatment["assigned_users"]),
    )
    window_test = proportion_effect(
        int(control["retained_d1_7_window_users"]),
        int(control["assigned_users"]),
        int(treatment["retained_d1_7_window_users"]),
        int(treatment["assigned_users"]),
    )
    quality["d7_retained"]["uncertainty"] = {
        "ci_lower": float(d7_test["ci_lower"]) * 10_000,
        "ci_upper": float(d7_test["ci_upper"]) * 10_000,
        "p_value": d7_test["p_value"],
    }
    quality["d1_7_window_retained"]["uncertainty"] = {
        "ci_lower": float(window_test["ci_lower"]) * 10_000,
        "ci_upper": float(window_test["ci_upper"]) * 10_000,
        "p_value": window_test["p_value"],
    }
    values = query_df(
        """SELECT group_name, contribution30 FROM mart_experiment_user_value
           WHERE experiment_id=$experiment_id""",
        {"experiment_id": experiment_id},
    )
    contribution_uncertainty = parametric_bootstrap_difference(
        values.loc[values["group_name"] == "control", "contribution30"],
        values.loc[values["group_name"] == "treatment", "contribution30"],
    )
    quality["contribution30"]["uncertainty"] = contribution_uncertainty

    weekly_rows = query_records(
        """
        SELECT exposure_week, group_name, COUNT(*) AS users,
               SUM(primary_outcome::INTEGER) AS successes
        FROM mart_experiment_user_value WHERE experiment_id=$experiment_id
        GROUP BY 1,2 ORDER BY 1,2
        """,
        {"experiment_id": experiment_id},
    )
    week_slices = []
    for week in sorted({int(row["exposure_week"]) for row in weekly_rows}):
        groups = {
            str(row["group_name"]): row for row in weekly_rows if int(row["exposure_week"]) == week
        }
        week_slices.append(
            {
                "week": week,
                **proportion_effect(
                    int(groups["control"]["successes"]),
                    int(groups["control"]["users"]),
                    int(groups["treatment"]["successes"]),
                    int(groups["treatment"]["users"]),
                ),
                "purpose": "novelty_and_durability_diagnostic_only",
            }
        )
    definition = query_records(
        "SELECT * FROM experiment_definitions WHERE experiment_id=$experiment_id",
        {"experiment_id": experiment_id},
    )[0]
    health = experiment_health(experiment_id)
    sample_plan = calculate_sample_size(
        baseline_rate=float(definition["baseline_rate"]),
        mde_absolute=float(definition["mde_absolute"]),
        alpha=float(definition["alpha"]),
        power=float(definition["power"]),
    )
    sample_reached = bool(
        int(control["assigned_users"]) >= int(sample_plan["sample_control"])
        and int(treatment["assigned_users"]) >= int(sample_plan["sample_treatment"])
    )
    timing = query_records(
        """
        SELECT MIN(a.assigned_at) AS first_assignment,
               MAX(o.observed_at) AS experiment_end,
               DATE_DIFF('day', MIN(a.assigned_at), MAX(o.observed_at)) AS experiment_duration_days,
               (SELECT MAX(r.signup_date) FROM experiment_outcomes eo
                JOIN new_user_retention r ON r.user_id=eo.new_user_id
                WHERE eo.experiment_id=$experiment_id) AS last_referred_activation,
               (SELECT MAX(r.signup_date) + INTERVAL 30 DAY FROM experiment_outcomes eo
                JOIN new_user_retention r ON r.user_id=eo.new_user_id
                WHERE eo.experiment_id=$experiment_id) AS value_followup_complete_date,
               (SELECT as_of_date FROM analysis_snapshot LIMIT 1) AS snapshot_as_of_date,
               (SELECT DATE_DIFF('day', MAX(r.signup_date), (SELECT as_of_date FROM analysis_snapshot LIMIT 1))
                FROM experiment_outcomes eo JOIN new_user_retention r ON r.user_id=eo.new_user_id
                WHERE eo.experiment_id=$experiment_id) AS value_followup_observed_days,
               30 AS value_followup_required_days
        FROM experiment_assignments a
        JOIN experiment_outcomes o USING(experiment_id,user_id,group_name)
        WHERE a.experiment_id=$experiment_id
        """,
        {"experiment_id": experiment_id},
    )[0]
    required_days = int(definition["decision_horizon_days"])
    duration_reached = int(timing["experiment_duration_days"]) >= required_days
    timing["experiment_required_days"] = required_days
    timing["experiment_duration_pass"] = duration_reached
    timing["duration_pass"] = duration_reached
    guardrail_rows = query_records(
        """SELECT group_name, AVG(guardrail_outcome) AS value
           FROM experiment_outcomes WHERE experiment_id=$experiment_id GROUP BY 1""",
        {"experiment_id": experiment_id},
    )
    guardrail_groups = {str(item["group_name"]): float(item["value"]) for item in guardrail_rows}
    direction = str(definition["guardrail_direction"])
    threshold = float(definition["guardrail_threshold"])
    tolerance = float(definition["guardrail_tolerance"])
    guardrail_control = guardrail_groups.get("control")
    guardrail_treatment = guardrail_groups.get("treatment")
    if guardrail_control is None or guardrail_treatment is None:
        guardrail_pass: bool | None = None
    elif direction == "higher":
        guardrail_pass = bool(
            guardrail_treatment >= threshold
            and guardrail_treatment >= guardrail_control - tolerance
        )
    elif direction == "lower":
        guardrail_pass = bool(
            guardrail_treatment <= threshold
            and guardrail_treatment <= guardrail_control + tolerance
        )
    else:
        guardrail_pass = None
    dq = data_quality_status()
    mature = query_records(
        """
        SELECT COUNT(*) AS linked_users,
               SUM(CASE WHEN r.mature_d7 THEN 1 ELSE 0 END) AS mature_d7_users,
               SUM(CASE WHEN r.mature_d30 THEN 1 ELSE 0 END) AS mature_d30_users
        FROM experiment_outcomes o
        JOIN new_user_retention r ON r.user_id=o.new_user_id
        WHERE o.experiment_id=$experiment_id
        """,
        {"experiment_id": experiment_id},
    )[0]
    linked_users = int(mature["linked_users"])
    outcomes_mature = bool(
        linked_users == int(mature["mature_d7_users"]) == int(mature["mature_d30_users"])
        and timing["value_followup_observed_days"] is not None
        and int(timing["value_followup_observed_days"])
        >= int(timing["value_followup_required_days"])
    )
    srm_pass = bool(
        health["overall_srm"].get("applicable") is True
        and health["overall_srm"].get("pass") is True
    )
    health_pass = {
        "data_quality": dq["status"] == "pass" and dq["failed_count"] == 0,
        "assignment_and_exposure_integrity": all(
            int(item["observable"]) <= int(item["exposed"]) <= int(item["assigned"])
            for item in health["flow"]
        ),
        "srm": srm_pass,
        "pre_treatment_balance": all(item["pass"] for item in health["pre_treatment_balance"]),
        "exposure_tracking": all(
            int(item["exposed"]) / int(item["assigned"]) >= 0.9 for item in health["flow"]
        ),
        "sample_size": sample_reached,
        "fixed_horizon_duration": duration_reached,
        "outcome_maturity": outcomes_mature,
        "guardrail": guardrail_pass,
    }
    gate_reasons = {
        "data_quality": f"Latest DQ: {dq['failed_count']} failed of {dq['check_count']} checks.",
        "assignment_and_exposure_integrity": "Exposure counts cannot exceed assignments.",
        "srm": "SRM must be applicable and explicitly pass; unknown is a failure.",
        "pre_treatment_balance": "Every pre-treatment one-hot |SMD| must be <= 0.1.",
        "exposure_tracking": "Each arm must have at least 90% tracked exposure.",
        "sample_size": (
            f"Required control/treatment={sample_plan['sample_control']}/{sample_plan['sample_treatment']}; "
            f"observed={control['assigned_users']}/{treatment['assigned_users']}."
        ),
        "fixed_horizon_duration": (
            f"Required {required_days} days; observed {timing['experiment_duration_days']} days from "
            f"{timing['first_assignment']} to {timing['experiment_end']}."
        ),
        "outcome_maturity": (
            f"Linked={linked_users}; mature D7={mature['mature_d7_users']}; "
            f"mature D30={mature['mature_d30_users']}."
        ),
        "guardrail": (
            f"{definition['guardrail_metric']} direction={direction}, threshold={threshold}, "
            f"tolerance={tolerance}, control={guardrail_control}, treatment={guardrail_treatment}."
        ),
        "statistical_significance": (
            f"Fixed-horizon p={primary['p_value']:.6g} versus alpha={definition['alpha']}."
        ),
        "business_significance": (
            f"Observed uplift={primary['absolute_uplift']:.6g}; "
            f"pre-registered MDE={definition['mde_absolute']}."
        ),
        "incremental_contribution30": (
            "ITT Incremental Contribution30 per 10k assigned="
            f"{quality['contribution30']['estimate']:.6g}."
        ),
    }
    decision = build_decision_card(
        health=health_pass,
        statistical_significant=bool(primary["stat_significant"]),
        business_significant=float(primary["absolute_uplift"]) >= float(definition["mde_absolute"]),
        contribution_positive=float(quality["contribution30"]["estimate"]) > 0,
        gate_reasons=gate_reasons,
    )
    return {
        "experiment_id": experiment_id,
        "primary_metric": {
            **primary,
            "metric_name": definition["core_metric"],
            "denominator_type": "assignment",
            "population": "intention_to_treat",
            "window": "pre-registered fixed 14-day horizon",
        },
        "quality_adjusted_effects": quality,
        "week_slices": week_slices,
        "week_slice_warning": (
            "Week slices diagnose novelty/durability and must not change the fixed-horizon stopping rule."
        ),
        "segment_effects": _segment_effects(experiment_id),
        "segment_claim_boundary": (
            "Intervals and multiplicity are reported. A significant result in one segment and not another "
            "is not evidence of heterogeneity; no such claim is made without an interaction test."
        ),
        "decision_card": decision,
        "decision_basis": {
            "sample_plan": sample_plan,
            "timing": timing,
            "guardrail": {
                "metric": definition["guardrail_metric"],
                "direction": direction,
                "threshold": threshold,
                "tolerance": tolerance,
                "control": guardrail_control,
                "treatment": guardrail_treatment,
                "pass": guardrail_pass,
            },
            "data_quality": {"status": dq["status"], "failed_count": dq["failed_count"]},
            "outcome_maturity": mature,
        },
        "growth_gate": "T→H — causal effect to harvestable value",
        "evidence_level": "randomized ITT",
        "synthetic_data": True,
    }


def economics_summary(experiment_id: str = "referral_ui_simplification") -> dict[str, Any]:
    descriptive = acquisition_quality()
    effects = experiment_effects(experiment_id)
    break_even = query_records(
        """
        SELECT acquisition_treatment,
               AVG(ltv30-service_cost30) AS break_even_variable_acquisition_cost,
               SUM(ltv30)/NULLIF(SUM(variable_acquisition_cost),0) AS average_ltv_cac,
               COUNT(*) AS acquired_users
        FROM acquired_users WHERE acquisition_source='referral_experiment'
        GROUP BY 1 ORDER BY 1
        """
    )
    return {
        "experiment_id": experiment_id,
        "average_acquired_user_economics": descriptive["items"],
        "average_ltv_cac_definition": (
            "SUM(LTV30) / SUM(all variable acquisition costs) among acquired users only; descriptive."
        ),
        "causal_itt_economics": effects["quality_adjusted_effects"],
        "break_even": break_even,
        "no_incremental_ltv_cac": (
            "An unstable incremental LTV/CAC ratio is intentionally not reported. "
            "Use Incremental Contribution30 and cost per incremental D7 retained user."
        ),
        "growth_gate": "H — unit economics and allocation",
        "evidence_level": "randomized ITT for incremental contribution; descriptive for acquired-user averages",
        "synthetic_data": True,
    }


def economics_scenarios(request: EconomicsScenarioRequest) -> dict[str, Any]:
    if request.experiment_id != "referral_ui_simplification":
        raise ValueError("Budget scenarios are available for referral_ui_simplification")
    row = query_records(
        """
        SELECT COUNT(*) AS assigned_users,
               SUM(referred_activated::INTEGER) AS acquired_users,
               SUM(value30) AS value30,
               SUM(variable_acquisition_cost) AS variable_acquisition_cost
        FROM mart_experiment_user_value
        WHERE experiment_id=$experiment_id AND group_name='treatment'
        """,
        {"experiment_id": request.experiment_id},
    )[0]
    acquired = int(row["acquired_users"])
    if acquired <= 0:
        raise ValueError("Scenario requires at least one acquired treatment user")
    result = budget_curve(
        acquired_per_10k=10_000 * acquired / int(row["assigned_users"]),
        value_per_acquired=float(row["value30"]) / acquired,
        cost_per_acquired=float(row["variable_acquisition_cost"]) / acquired,
        multipliers=request.budget_multipliers,
        elasticity=request.response_elasticity,
        eligible_population=request.eligible_population,
    )
    result.update(
        {
            "experiment_id": request.experiment_id,
            "source_estimate": "treatment-arm observed acquired-user economics",
            "growth_gate": "H — scenario planning after causal validation",
            "synthetic_data": True,
        }
    )
    return result


def decisions() -> dict[str, Any]:
    items = query_records("SELECT * FROM decision_log ORDER BY decision_date DESC")
    return {
        "items": items,
        "count": len(items),
        "decision_contract": [
            "fact",
            "interpretation",
            "hypothesis",
            "action",
            "limitation",
        ],
        "evidence_ladder": [
            {"level": "descriptive", "claim": "what happened"},
            {"level": "diagnostic", "claim": "where the loss concentrates"},
            {"level": "correlational", "claim": "which mechanisms merit testing"},
            {"level": "randomized_itt", "claim": "what the assigned strategy caused"},
        ],
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
