from __future__ import annotations

from typing import Any

METRIC_DEFINITIONS: list[dict[str, str | None]] = [
    {
        "metric_name": "referral_new_users",
        "display_name_zh": "老带新激活用户数",
        "display_name_en": "Referral activated users",
        "description": "通过邀请链路完成激活的新用户去重数。",
        "formula": "COUNT(DISTINCT new_user_id WHERE activated)",
        "numerator": None,
        "denominator": None,
        "unit": "users",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "invite_click_rate",
        "display_name_zh": "邀请点击率",
        "display_name_en": "Invite click-through rate",
        "description": "访问活动页面的老用户中点击邀请按钮的比例。",
        "formula": "invite_click_uv / campaign_page_visit_uv",
        "numerator": "invite_click_uv",
        "denominator": "campaign_page_visit_uv",
        "unit": "ratio",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "share_success_rate",
        "display_name_zh": "分享成功率",
        "display_name_en": "Share success rate",
        "description": "点击邀请的用户中完成分享的比例。",
        "formula": "share_success_uv / invite_click_uv",
        "numerator": "share_success_uv",
        "denominator": "invite_click_uv",
        "unit": "ratio",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "activation_per_exposure",
        "display_name_zh": "曝光到激活裂变率",
        "display_name_en": "Activation per exposure",
        "description": "默认裂变率口径：激活新用户数除以活动曝光老用户数。",
        "formula": "new_user_activate_uv / campaign_exposure_uv",
        "numerator": "new_user_activate_uv",
        "denominator": "campaign_exposure_uv",
        "unit": "ratio",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "activation_per_invite_click",
        "display_name_zh": "点击邀请到激活裂变率",
        "display_name_en": "Activation per invite click",
        "description": "备选裂变率口径：激活新用户数除以邀请点击用户数。",
        "formula": "new_user_activate_uv / invite_click_uv",
        "numerator": "new_user_activate_uv",
        "denominator": "invite_click_uv",
        "unit": "ratio",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "invites_per_inviter",
        "display_name_zh": "邀请者人均拉新",
        "display_name_en": "Activated users per inviter",
        "description": "完成激活的新用户数除以有效邀请者数。",
        "formula": "new_user_activate_uv / effective_inviter_uv",
        "numerator": "new_user_activate_uv",
        "denominator": "effective_inviter_uv",
        "unit": "users_per_inviter",
        "grain": "day × campaign_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "ltv30",
        "display_name_zh": "新用户首月价值",
        "display_name_en": "30-day lifetime value",
        "description": "用活跃天数、日均时长和单位时长价值估算的首月价值。",
        "formula": "active_days_30 × daily_hours × value_per_hour",
        "numerator": None,
        "denominator": None,
        "unit": "normalized_value",
        "grain": "acquisition_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "cac",
        "display_name_zh": "获客成本",
        "display_name_en": "Customer acquisition cost",
        "description": "成功激活一个新用户所需的平均激励成本。",
        "formula": "total_incentive_cost / activated_new_users",
        "numerator": "total_incentive_cost",
        "denominator": "activated_new_users",
        "unit": "normalized_cost",
        "grain": "acquisition_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "ltv_cac_ratio",
        "display_name_zh": "LTV/CAC",
        "display_name_en": "LTV/CAC ratio",
        "description": "首月用户价值与获客成本的比值，不等同于净ROI。",
        "formula": "ltv30 / cac",
        "numerator": "ltv30",
        "denominator": "cac",
        "unit": "ratio",
        "grain": "acquisition_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "net_roi",
        "display_name_zh": "净ROI",
        "display_name_en": "Net ROI",
        "description": "扣除获客成本后的收益相对获客成本比例。",
        "formula": "(ltv30 - cac) / cac",
        "numerator": "ltv30 - cac",
        "denominator": "cac",
        "unit": "ratio",
        "grain": "acquisition_version",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "d1_7_window_retention",
        "display_name_zh": "次1至7日窗口留存",
        "display_name_en": "Day 1-7 window retention",
        "description": "新增后第1至7天内至少活跃一次的用户占比，不等同于精确D7留存。",
        "formula": "users active on any day 1..7 / new users",
        "numerator": "retained_d1_7_window_users",
        "denominator": "new_users",
        "unit": "ratio",
        "grain": "signup_cohort",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "incremental_d7_retained_per_10k_assigned",
        "display_name_zh": "每万分流增量D7留存新用户",
        "display_name_en": "Incremental D7 retained users per 10k assigned",
        "description": "随机实验ITT口径：每万名被分流老用户带来的增量精确D7留存新用户。未拉新用户贡献为0。",
        "formula": "10000 × (retained_D7_T / assigned_T - retained_D7_C / assigned_C)",
        "numerator": "difference in D7-retained referred users",
        "denominator": "experiment assignment",
        "unit": "users_per_10k_assigned",
        "grain": "experiment × arm",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "incremental_d1_7_retained_per_10k_assigned",
        "display_name_zh": "每万分流增量D1-7窗口留存新用户",
        "display_name_en": "Incremental D1-7 retained users per 10k assigned",
        "description": "随机实验ITT口径：每万名被分流老用户带来的增量D1-7窗口留存新用户。未拉新用户贡献为0。",
        "formula": "10000 × (retained_D1_7_T / assigned_T - retained_D1_7_C / assigned_C)",
        "numerator": "difference in D1-7 retained referred users",
        "denominator": "experiment assignment",
        "unit": "users_per_10k_assigned",
        "grain": "experiment × arm",
        "owner_role": "growth_analytics",
    },
    {
        "metric_name": "incremental_contribution30_per_10k_assigned",
        "display_name_zh": "每万分流首月增量贡献价值",
        "display_name_en": "Incremental Contribution30 per 10k assigned",
        "description": "随机实验ITT口径：未获客用户贡献记0，比较每万分流用户带来的30日价值减全部可变获客成本。",
        "formula": "10000 × [Σ(value30 - variable acquisition costs)_T / assigned_T - same_C]",
        "numerator": "difference in net 30-day contribution",
        "denominator": "experiment assignment",
        "unit": "normalized_value_per_10k_assigned",
        "grain": "experiment × arm",
        "owner_role": "growth_analytics",
    },
]


# A metric is a governed decision contract, not merely a display label.  Defaults keep
# the legacy catalog backward compatible while making every row traceable and auditable.
for _metric in METRIC_DEFINITIONS:
    _metric.setdefault("metric_type", "diagnostic")
    _metric.setdefault("decision_use", "Diagnose a governed stage of the growth lifecycle.")
    _metric.setdefault("eligibility", "Rows satisfying the documented source-table contract.")
    _metric.setdefault(
        "inclusion_exclusion", "Deduplicate by governed user and window; exclude test traffic."
    )
    _metric.setdefault("attribution_window", "As defined in formula and grain.")
    _metric.setdefault("observation_window", "As defined in formula and grain.")
    _metric.setdefault("timezone", "UTC")
    _metric.setdefault("freshness_sla", "Public demo regenerated as one deterministic snapshot.")
    _metric.setdefault("source_table", "See metric lineage endpoint.")
    _metric.setdefault("sql_model", "See metric lineage endpoint.")
    _metric.setdefault(
        "claim_boundary", "Descriptive unless an explicit randomized estimand is named."
    )

for _metric_name in {
    "incremental_d7_retained_per_10k_assigned",
    "incremental_d1_7_retained_per_10k_assigned",
    "incremental_contribution30_per_10k_assigned",
}:
    _item = next(item for item in METRIC_DEFINITIONS if item["metric_name"] == _metric_name)
    _item["metric_type"] = "final_business"
    _item["decision_use"] = "Primary causal rollout and resource-allocation decision evidence."
    _item["eligibility"] = "All users assigned to the pre-registered referral UI experiment."
    _item["inclusion_exclusion"] = (
        "ITT: retain every assignment; non-acquired users contribute zero."
    )
    _item["attribution_window"] = "Assignment through referred-user activation."
    _item["observation_window"] = "Exact D7, D1-7 window, or 30 days as named."
    _item["source_table"] = "mart_experiment_user_value"
    _item["sql_model"] = "sql/experiments/quality_adjusted_effects.sql"
    _item["claim_boundary"] = "Causal only for the randomized ITT population and fixed horizon."

for _metric_name in {"invite_click_rate", "share_success_rate", "activation_per_exposure"}:
    _item = next(item for item in METRIC_DEFINITIONS if item["metric_name"] == _metric_name)
    _item["metric_type"] = "mechanism"
    _item["decision_use"] = "Localize the mechanism; never substitute for the final value outcome."

for _metric_name in {"ltv_cac_ratio", "net_roi"}:
    _item = next(item for item in METRIC_DEFINITIONS if item["metric_name"] == _metric_name)
    _item["metric_type"] = "guardrail"


def metric_tree() -> dict[str, Any]:
    """Return the governed business tree shown by the application."""
    return {
        "name": "Active user growth index",
        "display_name": "活跃用户增长指数",
        "unit": "index",
        "children": [
            {"name": "paid_acquisition", "display_name": "外部获客新增"},
            {"name": "organic_acquisition", "display_name": "自然新增"},
            {
                "name": "referral_new_users",
                "display_name": "老带新新增",
                "children": [
                    {"name": "campaign_exposure_uv", "display_name": "活动曝光UV"},
                    {"name": "campaign_page_visit_uv", "display_name": "活动访问UV"},
                    {"name": "invite_click_uv", "display_name": "邀请点击UV"},
                    {"name": "share_success_uv", "display_name": "分享成功UV"},
                    {"name": "new_user_landing_uv", "display_name": "新用户到达UV"},
                    {"name": "new_user_activate_uv", "display_name": "新用户激活UV"},
                ],
            },
        ],
        "disclaimer": "All values in the public demo are synthetic and normalized.",
    }
