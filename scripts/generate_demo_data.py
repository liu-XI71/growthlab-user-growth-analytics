from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from analytics.experimentation import assign_hash_group
from analytics.metrics import METRIC_DEFINITIONS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "demo" / "growthlab.duckdb"
ANALYSIS_AS_OF_DATE = pd.Timestamp("2025-07-15")

CHANNELS = np.array(["organic", "search_ads", "social_ads", "partner"])
REGIONS = np.array(["north", "east", "south", "west"])
DEVICE_BRANDS = {
    "phone": np.array(["brand_alpha", "brand_beta", "brand_gamma"]),
    "tablet": np.array(["brand_alpha", "brand_delta"]),
    "tv": np.array(["brand_epsilon", "brand_zeta"]),
}
EVENT_STEPS = [
    "campaign_exposure",
    "campaign_click",
    "invite_click",
    "share_success",
    "new_user_landing",
    "new_user_register",
    "new_user_activate",
]


def _choose_devices(rng: np.random.Generator, periods: np.ndarray) -> np.ndarray:
    output = np.empty(len(periods), dtype=object)
    baseline = periods == "baseline"
    output[baseline] = rng.choice(["phone", "tablet", "tv"], baseline.sum(), p=[0.80, 0.12, 0.08])
    output[~baseline] = rng.choice(
        ["phone", "tablet", "tv"], (~baseline).sum(), p=[0.66, 0.20, 0.14]
    )
    return output


def _brand_for_devices(rng: np.random.Generator, devices: np.ndarray) -> np.ndarray:
    return np.asarray([rng.choice(DEVICE_BRANDS[str(device)]) for device in devices], dtype=object)


def generate_users(rng: np.random.Generator, users: int) -> pd.DataFrame:
    user_ids = np.asarray([f"demo_u_{index:08d}" for index in range(users)])
    periods = np.where(np.arange(users) < users // 2, "baseline", "current")
    rng.shuffle(periods)
    devices = _choose_devices(rng, periods)
    signup_start = pd.Timestamp("2025-01-01")
    baseline_days = rng.integers(0, 28, size=users)
    current_days = rng.integers(42, 70, size=users)
    signup_offsets = np.where(periods == "baseline", baseline_days, current_days)
    signup_dates = signup_start + pd.to_timedelta(signup_offsets, unit="D")
    os_name = np.where(
        devices == "phone",
        rng.choice(["mobile_os_a", "mobile_os_b"], users, p=[0.58, 0.42]),
        np.where(devices == "tablet", "tablet_os", "tv_os"),
    )
    frame = pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_date": signup_dates.date,
            "period": periods,
            "channel": rng.choice(CHANNELS, users, p=[0.33, 0.26, 0.29, 0.12]),
            "device_type": devices,
            "device_brand": _brand_for_devices(rng, devices),
            "os_name": os_name,
            "system_version": rng.choice(["v1", "v2", "v3"], users, p=[0.20, 0.48, 0.32]),
            "region": rng.choice(REGIONS, users, p=[0.22, 0.35, 0.29, 0.14]),
            "product_version": rng.choice(["app_5", "app_6"], users, p=[0.42, 0.58]),
            # Acquisition identity is updated in-place when a generated referral edge
            # is created.  Keeping channel unchanged preserves the pre-treatment media
            # dimension while acquisition_source links the two portfolio cases.
            "acquisition_source": "non_referral",
            "referrer_user_id": None,
            "acquisition_campaign": None,
            "acquisition_treatment": None,
            "is_referral_inviter": False,
        }
    )
    recent_candidates = frame.index[frame["period"] == "current"][-max(1, users // 20) :]
    frame.loc[recent_candidates, "signup_date"] = (
        pd.Timestamp("2025-06-08")
        + pd.to_timedelta(np.arange(len(recent_candidates)) % 23, unit="D")
    ).date
    return frame


def generate_retention(
    rng: np.random.Generator, users: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    device_base = users["device_type"].map({"phone": 0.50, "tablet": 0.42, "tv": 0.40}).to_numpy()
    channel_adjustment = (
        users["channel"]
        .map({"organic": 0.025, "search_ads": 0.005, "social_ads": -0.012, "partner": -0.004})
        .to_numpy()
    )
    current_adjustment = np.where(users["period"].to_numpy() == "current", -0.004, 0.0)
    source_adjustment = (
        users["acquisition_source"]
        .map({"non_referral": 0.0, "referral_campaign": 0.026, "referral_experiment": 0.022})
        .fillna(0.0)
        .to_numpy()
    )
    window_probability = np.clip(
        device_base + channel_adjustment + current_adjustment + source_adjustment,
        0.08,
        0.90,
    )

    d1_probability = window_probability * 0.76
    d3_probability = window_probability * 0.56
    d7_probability = window_probability * 0.38
    d30_probability = window_probability * 0.24
    retained_d1 = rng.random(len(users)) < d1_probability
    retained_d3 = rng.random(len(users)) < d3_probability
    retained_d7 = rng.random(len(users)) < d7_probability
    retained_window = (
        (rng.random(len(users)) < window_probability) | retained_d1 | retained_d3 | retained_d7
    )
    retention = users[
        [
            "user_id",
            "signup_date",
            "period",
            "channel",
            "device_type",
            "device_brand",
            "os_name",
            "system_version",
            "region",
            "product_version",
            "acquisition_source",
            "referrer_user_id",
            "acquisition_campaign",
            "acquisition_treatment",
        ]
    ].copy()
    retention["retained_d1"] = retained_d1
    retention["retained_d3"] = retained_d3
    retention["retained_d7"] = retained_d7
    retention["retained_d1_7_window"] = retained_window
    retained_d30 = rng.random(len(users)) < d30_probability
    age_days = (ANALYSIS_AS_OF_DATE - pd.to_datetime(retention["signup_date"])).dt.days
    retention["cohort_age_days"] = age_days
    retention["mature_d7"] = age_days >= 7
    retention["mature_d30"] = age_days >= 30
    retention["retained_d30"] = pd.Series(retained_d30, dtype="boolean").where(
        retention["mature_d30"], pd.NA
    )

    active_days = np.clip(rng.poisson(4.2 + retained_window * 5.8, len(users)) + 1, 1, 30)
    daily_hours = np.clip(
        rng.lognormal(-0.45 + retained_window * 0.24, 0.48, len(users)), 0.08, 5.5
    )
    benchmark = (active_days >= np.quantile(active_days, 0.75)) & (
        daily_hours >= np.quantile(daily_hours, 0.75)
    )
    feature_probability = np.where(benchmark, 0.57, 0.21)
    feature_used = rng.random(len(users)) < feature_probability
    feature_usage = users[
        [
            "user_id",
            "period",
            "channel",
            "device_type",
            "region",
            "acquisition_source",
            "acquisition_campaign",
            "acquisition_treatment",
        ]
    ].copy()
    feature_usage["active_days_30"] = active_days
    feature_usage["daily_active_hours"] = daily_hours
    feature_usage["benchmark_user"] = benchmark
    feature_usage["feature_name"] = "content_save"
    feature_usage["feature_used"] = feature_used
    feature_usage["feature_use_count"] = np.where(
        feature_used, np.maximum(1, rng.poisson(np.where(benchmark, 5.2, 2.1))), 0
    )
    feature_usage["retained_d1_7_window"] = retained_window
    return retention, feature_usage


def generate_new_user_funnel(
    rng: np.random.Generator, users: pd.DataFrame, retention: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(users)
    registered = rng.random(n) < 0.94
    home_view = registered & (rng.random(n) < 0.91)
    content_view = home_view & (rng.random(n) < 0.73)
    content_interaction = content_view & (rng.random(n) < 0.55)
    save_or_follow = content_interaction & (rng.random(n) < 0.39)
    funnel = users[["user_id", "signup_date", "period", "device_type", "channel"]].copy()
    funnel["first_open"] = True
    funnel["register"] = registered
    funnel["home_view"] = home_view
    funnel["content_view"] = content_view
    funnel["content_interaction"] = content_interaction
    funnel["save_or_follow"] = save_or_follow
    # The path funnel is an ordered subset journey. Overall retention remains available
    # independently in new_user_retention and must not be inferred from this final step.
    funnel["return_visit"] = save_or_follow & retention["retained_d1_7_window"].to_numpy()

    event_rows: list[pd.DataFrame] = []
    event_map = [
        ("first_open", "first_open"),
        ("register", "register"),
        ("home_view", "home_view"),
        ("content_view", "content_view"),
        ("content_interaction", "content_interaction"),
        ("save_or_follow", "feature_save"),
        ("return_visit", "return_visit"),
    ]
    for day_offset, (column, event_name) in enumerate(event_map):
        selected = funnel[column].to_numpy(bool)
        block = funnel.loc[selected, ["user_id", "signup_date", "period"]].copy()
        block["event_id"] = [f"new_{event_name}_{uid}" for uid in block["user_id"]]
        block["event_name"] = event_name
        block["event_at"] = pd.to_datetime(block["signup_date"]) + pd.to_timedelta(
            day_offset, unit="h"
        )
        block["campaign_version"] = None
        event_rows.append(
            block[["event_id", "user_id", "event_name", "event_at", "period", "campaign_version"]]
        )
    return funnel, pd.concat(event_rows, ignore_index=True)


def generate_referral(rng: np.random.Generator, users: pd.DataFrame) -> dict[str, pd.DataFrame]:
    earliest_campaign_date = pd.Timestamp("2025-03-03").date()
    eligible_users = users.loc[users["signup_date"] <= earliest_campaign_date]
    sample_n = max(1_000, int(len(users) * 0.52))
    sample_n = min(sample_n, len(eligible_users))
    referral = eligible_users.sample(sample_n, random_state=17)[
        ["user_id", "signup_date", "channel", "device_type", "region"]
    ].reset_index(drop=True)
    versions = rng.choice(["variant_a", "variant_b", "variant_c"], sample_n, p=[0.33, 0.33, 0.34])
    referral["version"] = versions
    version_start = {
        "variant_a": pd.Timestamp("2025-03-03"),
        "variant_b": pd.Timestamp("2025-03-24"),
        "variant_c": pd.Timestamp("2025-04-14"),
    }
    referral["exposure_date"] = [
        (version_start[version] + pd.Timedelta(days=int(offset))).date()
        for version, offset in zip(versions, rng.integers(0, 14, sample_n), strict=True)
    ]
    referral["campaign_exposure"] = True
    for column in EVENT_STEPS[1:]:
        referral[column] = False

    def choose_nested(previous_indices: np.ndarray, rate: float) -> np.ndarray:
        count = min(len(previous_indices), int(round(rate * len(previous_indices))))
        if count == 0:
            return np.asarray([], dtype=int)
        return rng.choice(previous_indices, count, replace=False)

    invite_rate_by_version = {"variant_a": 0.205, "variant_b": 0.158, "variant_c": 0.228}
    for version in ("variant_a", "variant_b", "variant_c"):
        exposed = np.flatnonzero(versions == version)
        clicked = choose_nested(exposed, 0.77)
        invited = choose_nested(clicked, invite_rate_by_version[version])
        shared = choose_nested(invited, 0.92)
        landed = choose_nested(shared, 0.49)
        registered = choose_nested(landed, 0.81)
        activated = choose_nested(registered, 0.84)
        for column, selected in (
            ("campaign_click", clicked),
            ("invite_click", invited),
            ("share_success", shared),
            ("new_user_landing", landed),
            ("new_user_register", registered),
            ("new_user_activate", activated),
        ):
            referral.loc[selected, column] = True
    referral = referral.rename(columns={"user_id": "inviter_user_id"})
    users.loc[users["user_id"].isin(referral["inviter_user_id"]), "is_referral_inviter"] = True

    daily = (
        referral.groupby(["exposure_date", "version"], observed=True)
        .agg(
            exposure_uv=("campaign_exposure", "sum"),
            page_click_uv=("campaign_click", "sum"),
            invite_click_uv=("invite_click", "sum"),
            share_success_uv=("share_success", "sum"),
            new_user_landing_uv=("new_user_landing", "sum"),
            new_user_register_uv=("new_user_register", "sum"),
            new_user_activate_uv=("new_user_activate", "sum"),
        )
        .reset_index()
    )

    events: list[pd.DataFrame] = []
    for hour, event_name in enumerate(EVENT_STEPS):
        selected = referral[event_name].to_numpy(bool)
        block = referral.loc[selected, ["inviter_user_id", "exposure_date", "version"]].copy()
        block["event_id"] = [f"ref_{event_name}_{uid}" for uid in block["inviter_user_id"]]
        block["user_id"] = block["inviter_user_id"]
        block["event_name"] = event_name
        block["event_at"] = pd.to_datetime(block["exposure_date"]) + pd.to_timedelta(hour, unit="h")
        block["period"] = "referral_campaign"
        block["campaign_version"] = block["version"]
        events.append(
            block[["event_id", "user_id", "event_name", "event_at", "period", "campaign_version"]]
        )

    activated = referral.loc[referral["new_user_activate"]].copy().reset_index(drop=True)
    inviter_ids = set(referral["inviter_user_id"].astype(str))
    candidates = users.loc[~users["user_id"].isin(inviter_ids), "user_id"].to_numpy()
    if len(candidates) < len(activated):
        raise ValueError("Not enough unified user IDs to materialize referral invitees")
    activated["new_user_id"] = rng.choice(candidates, len(activated), replace=False)
    user_index = users.set_index("user_id").index
    for row in activated.itertuples(index=False):
        location = user_index.get_loc(str(row.new_user_id))
        users.loc[location, "signup_date"] = row.exposure_date
        users.loc[location, "period"] = "current"
        users.loc[location, "acquisition_source"] = "referral_campaign"
        users.loc[location, "referrer_user_id"] = row.inviter_user_id
        users.loc[location, "acquisition_campaign"] = row.version
        users.loc[location, "acquisition_treatment"] = "descriptive_version"
    active_days = np.clip(rng.poisson(8.0, len(activated)) + 1, 1, 30)
    daily_hours = np.clip(rng.lognormal(-0.38, 0.36, len(activated)), 0.1, 4.0)
    value_per_hour = np.clip(rng.normal(1.75, 0.14, len(activated)), 1.2, 2.3)
    unit_cost = (
        activated["version"].map({"variant_a": 5.8, "variant_b": 7.5, "variant_c": 7.5}).to_numpy()
    )
    retention_discount = rng.uniform(0.76, 0.94, len(activated))
    acquired = pd.DataFrame(
        {
            "new_user_id": activated["new_user_id"].to_numpy(),
            "inviter_user_id": activated["inviter_user_id"].to_numpy(),
            "version": activated["version"].to_numpy(),
            "activated_date": activated["exposure_date"].to_numpy(),
            "active_days_30": active_days,
            "daily_active_hours": daily_hours,
            "value_per_hour": value_per_hour,
            "retention_discount": retention_discount,
            "incentive_cost": unit_cost,
            "ltv30": active_days * daily_hours * value_per_hour * retention_discount,
            "source_kind": "descriptive_campaign",
        }
    )
    rewards = acquired[
        ["new_user_id", "inviter_user_id", "version", "activated_date", "incentive_cost"]
    ].copy()
    rewards["reward_id"] = [f"reward_{index:08d}" for index in range(len(rewards))]
    rewards["reward_status"] = "issued"
    referral_edges = acquired[
        ["inviter_user_id", "new_user_id", "version", "activated_date", "source_kind"]
    ].copy()
    referral_edges.insert(
        0, "edge_id", [f"campaign_edge_{index:08d}" for index in range(len(referral_edges))]
    )
    referral_edges["experiment_id"] = None
    referral_edges["group_name"] = None
    referral_edges["edge_status"] = "activated"

    if not activated.empty:
        activation_events = pd.DataFrame(
            {
                "event_id": [f"ref_new_activate_{uid}" for uid in activated["new_user_id"]],
                "user_id": activated["new_user_id"].to_numpy(),
                "event_name": "new_user_activate",
                "event_at": pd.to_datetime(activated["exposure_date"])
                + pd.to_timedelta(7, unit="h"),
                "period": "referral_campaign",
                "campaign_version": activated["version"].to_numpy(),
            }
        )
        events.append(activation_events)
    return {
        "referral_user_journeys": referral,
        "referral_funnel_daily": daily,
        "growth_events": pd.concat(events, ignore_index=True),
        "acquired_users": acquired,
        "referral_rewards": rewards,
        "referral_edges": referral_edges,
    }


def _assign_experiment(
    users: pd.DataFrame, experiment_id: str, salt: str, assigned_at: str
) -> pd.DataFrame:
    assignments = [assign_hash_group(user_id, salt=salt) for user_id in users["user_id"]]
    frame = users[["user_id", "channel", "device_type", "region"]].copy()
    frame = frame.reset_index(drop=True)
    frame["experiment_id"] = experiment_id
    frame["group_name"] = [item["group"] for item in assignments]
    frame["hash_bucket"] = [item["bucket"] for item in assignments]
    frame["assigned_at"] = pd.Timestamp(assigned_at)
    return frame


def generate_experiments(
    rng: np.random.Generator, users: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    experiment_specs = [
        {
            "experiment_id": "referral_aa_validation",
            "name": "Referral allocation A/A validation",
            "kind": "aa",
            "objective": "Validate assignment, metric definitions and instrumentation before treatment.",
            "strategy": "Identical invitation experience in both groups.",
            "core_metric": "invite_click_rate",
            "business_metric": "referral_new_users",
            "baseline_rate": 0.16,
            "mde_absolute": 0.02,
            "alpha": 0.05,
            "power": 0.80,
            "daily_eligible_users": 18000,
            "estimand": "intention_to_treat",
            "randomization_unit": "user_id",
            "decision_horizon_days": 14,
            "guardrail_metric": "normalized_value_safety_index",
            "guardrail_direction": "higher",
            "guardrail_threshold": 1.70,
            "guardrail_tolerance": 0.03,
        },
        {
            "experiment_id": "referral_ui_simplification",
            "name": "Invitation page simplification",
            "kind": "ab",
            "objective": "Increase invite clicks and ultimately referred activated users.",
            "strategy": "Simplify information hierarchy and place the invite call-to-action above the fold.",
            "core_metric": "invite_click_rate",
            "business_metric": "referral_new_users",
            "baseline_rate": 0.16,
            "mde_absolute": 0.02,
            "alpha": 0.05,
            "power": 0.80,
            "daily_eligible_users": 18000,
            "estimand": "intention_to_treat",
            "randomization_unit": "user_id",
            "decision_horizon_days": 14,
            "guardrail_metric": "normalized_value_safety_index",
            "guardrail_direction": "higher",
            "guardrail_threshold": 1.70,
            "guardrail_tolerance": 0.03,
        },
        {
            "experiment_id": "content_save_nudge",
            "name": "Content save feature nudge",
            "kind": "ab",
            "objective": "Evaluate whether encouraging content saving increases new-user retention.",
            "strategy": "Show a lightweight save prompt and a clear path to saved content.",
            "core_metric": "d1_7_window_retention",
            "business_metric": "new_user_retention",
            "baseline_rate": 0.40,
            "mde_absolute": 0.025,
            "alpha": 0.05,
            "power": 0.80,
            "daily_eligible_users": 10000,
            "estimand": "intention_to_treat",
            "randomization_unit": "user_id",
            "decision_horizon_days": 14,
            "guardrail_metric": "experience_complaint_rate",
            "guardrail_direction": "lower",
            "guardrail_threshold": 0.025,
            "guardrail_tolerance": 0.003,
        },
    ]
    specs = pd.DataFrame(experiment_specs)
    assignment_frames: list[pd.DataFrame] = []
    exposure_frames: list[pd.DataFrame] = []
    outcome_frames: list[pd.DataFrame] = []
    edge_frames: list[pd.DataFrame] = []
    eligible = users.loc[
        (pd.to_datetime(users["signup_date"]) < pd.Timestamp("2025-03-03"))
        & (users["acquisition_source"] == "non_referral")
    ].copy()
    sample_size = min(len(eligible), 80_000, max(1_000, int(len(users) * 0.45)))
    sample = eligible.sample(sample_size, random_state=29).copy()
    reserved_ids = set(sample["user_id"].astype(str))
    invitee_candidates = users.loc[
        (~users["user_id"].isin(reserved_ids))
        & (users["acquisition_source"] == "non_referral")
        & (~users["is_referral_inviter"]),
        "user_id",
    ].to_numpy()
    candidate_cursor = 0
    for index, spec in enumerate(experiment_specs):
        assignment = _assign_experiment(
            sample,
            str(spec["experiment_id"]),
            salt=f"growthlab_public_demo_{index}",
            assigned_at=f"2025-05-{5 + index * 7:02d}",
        )
        group = assignment["group_name"].to_numpy()
        day_index = np.arange(len(assignment)) % 14
        rng.shuffle(day_index)
        week_index = day_index // 7 + 1
        was_exposed = rng.random(len(assignment)) < 0.94
        exposure = assignment[["user_id", "experiment_id", "group_name"]].copy()
        exposure["exposure_id"] = [
            f"exposure_{spec['experiment_id']}_{user_id}" if exposed else None
            for user_id, exposed in zip(exposure["user_id"], was_exposed, strict=True)
        ]
        exposure["was_exposed"] = was_exposed
        exposure["exposure_week"] = week_index
        exposure["exposed_at"] = assignment["assigned_at"] + pd.to_timedelta(day_index, unit="D")
        exposure.loc[~exposure["was_exposed"], "exposed_at"] = pd.NaT

        if spec["kind"] == "aa":
            weekly_rates = {
                ("control", 1): 0.160,
                ("control", 2): 0.160,
                ("treatment", 1): 0.160,
                ("treatment", 2): 0.160,
            }
        elif spec["experiment_id"] == "referral_ui_simplification":
            # The treatment is deliberately strongest in week one and settles in
            # week two.  Week slices are durability diagnostics, never stopping rules.
            weekly_rates = {
                ("control", 1): 0.165,
                ("control", 2): 0.165,
                ("treatment", 1): 0.228,
                ("treatment", 2): 0.208,
            }
        else:
            weekly_rates = {
                ("control", 1): 0.401,
                ("control", 2): 0.401,
                ("treatment", 1): 0.444,
                ("treatment", 2): 0.432,
            }
        primary = np.zeros(len(assignment), dtype=bool)
        for (group_name, week), rate in weekly_rates.items():
            indices = np.flatnonzero((group == group_name) & (week_index == week) & was_exposed)
            assigned_count = int(((group == group_name) & (week_index == week)).sum())
            successes = min(len(indices), int(round(rate * assigned_count)))
            selected = rng.choice(indices, successes, replace=False) if successes else []
            primary[selected] = True
        if spec["experiment_id"] == "referral_ui_simplification":
            guardrail = np.clip(rng.normal(1.84, 0.12, len(assignment)), 1.1, 2.5)
        elif spec["experiment_id"] == "content_save_nudge":
            guardrail = np.clip(rng.normal(0.018, 0.004, len(assignment)), 0, 0.06)
        else:
            guardrail = np.clip(rng.normal(1.80, 0.12, len(assignment)), 1.1, 2.5)
        outcomes = assignment[["user_id", "experiment_id", "group_name"]].copy()
        outcomes["primary_outcome"] = primary
        outcomes["guardrail_outcome"] = guardrail
        outcomes["outcome_observable"] = was_exposed
        outcomes["analysis_week"] = week_index
        outcomes["new_user_id"] = None
        outcomes["referred_activated"] = False
        outcomes["retained_d7"] = False
        outcomes["retained_d1_7_window"] = False
        outcomes["value30"] = 0.0
        outcomes["variable_acquisition_cost"] = 0.0
        outcomes["contribution30"] = 0.0
        outcomes["observed_at"] = assignment["assigned_at"] + pd.to_timedelta(14, unit="D")

        if spec["experiment_id"] == "referral_ui_simplification":
            activation = np.zeros(len(assignment), dtype=bool)
            for group_name, click_to_activation in {"control": 0.085, "treatment": 0.105}.items():
                indices = np.flatnonzero((group == group_name) & primary)
                successes = int(round(click_to_activation * len(indices)))
                selected = rng.choice(indices, successes, replace=False) if successes else []
                activation[selected] = True
            activated_indices = np.flatnonzero(activation)
            remaining = len(invitee_candidates) - candidate_cursor
            if len(activated_indices) > remaining:
                raise ValueError("Not enough unified user IDs for experimental referral outcomes")
            new_ids = invitee_candidates[
                candidate_cursor : candidate_cursor + len(activated_indices)
            ]
            candidate_cursor += len(activated_indices)
            user_index = users.set_index("user_id").index
            rows = []
            for edge_number, (row_index, new_user_id) in enumerate(
                zip(activated_indices, new_ids, strict=True)
            ):
                inviter_id = str(assignment.iloc[row_index]["user_id"])
                group_name = str(group[row_index])
                activated_date = (
                    pd.Timestamp(assignment.iloc[row_index]["assigned_at"])
                    + pd.Timedelta(days=int(day_index[row_index]) + 1)
                ).date()
                location = user_index.get_loc(str(new_user_id))
                users.loc[location, "signup_date"] = activated_date
                users.loc[location, "period"] = "current"
                users.loc[location, "acquisition_source"] = "referral_experiment"
                users.loc[location, "referrer_user_id"] = inviter_id
                users.loc[location, "acquisition_campaign"] = "referral_ui_simplification"
                users.loc[location, "acquisition_treatment"] = group_name
                outcomes.loc[row_index, "new_user_id"] = str(new_user_id)
                outcomes.loc[row_index, "referred_activated"] = True
                rows.append(
                    {
                        "edge_id": f"experiment_edge_{edge_number:08d}",
                        "inviter_user_id": inviter_id,
                        "new_user_id": str(new_user_id),
                        "version": "experiment_v1",
                        "activated_date": activated_date,
                        "source_kind": "randomized_experiment",
                        "experiment_id": "referral_ui_simplification",
                        "group_name": group_name,
                        "edge_status": "activated",
                    }
                )
            edge_frames.append(pd.DataFrame(rows))
        assignment_frames.append(assignment)
        exposure_frames.append(exposure)
        outcome_frames.append(outcomes)
    empty_edges = pd.DataFrame(
        columns=[
            "edge_id",
            "inviter_user_id",
            "new_user_id",
            "version",
            "activated_date",
            "source_kind",
            "experiment_id",
            "group_name",
            "edge_status",
        ]
    )
    return (
        pd.concat(assignment_frames, ignore_index=True),
        pd.concat(exposure_frames, ignore_index=True),
        pd.concat(outcome_frames, ignore_index=True),
        specs,
        pd.concat(edge_frames, ignore_index=True) if edge_frames else empty_edges,
    )


def _activity_rows(
    rng: np.random.Generator,
    users: pd.DataFrame,
    feature_usage: pd.DataFrame,
    retention: pd.DataFrame,
) -> pd.DataFrame:
    retention_lookup = retention.set_index("user_id")
    target_days = feature_usage.set_index("user_id")["active_days_30"]
    rows: list[dict[str, Any]] = []
    realized_counts: dict[str, int] = {}
    for user in users.itertuples(index=False):
        retained = retention_lookup.loc[user.user_id]
        offsets = {0}
        if bool(retained["retained_d1"]):
            offsets.add(1)
        if bool(retained["retained_d3"]):
            offsets.add(3)
        if bool(retained["retained_d7"]):
            offsets.add(7)
        if bool(retained["retained_d1_7_window"]) and not offsets.intersection(range(1, 8)):
            offsets.add(2)
        if bool(retained["mature_d30"]) and bool(retained["retained_d30"]):
            offsets.add(30)
        age_days = max(0, int(retained["cohort_age_days"]))
        allowed = list(range(1, min(age_days, 30) + 1))
        # Exact-day and window flags remain auditable: no incidental activity may
        # contradict a false checkpoint or a false D1-7 window.
        if not bool(retained["retained_d1_7_window"]):
            allowed = [day for day in allowed if day > 7]
        allowed = [day for day in allowed if day not in {1, 3, 7, 30} and day not in offsets]
        desired = max(len(offsets), int(target_days.loc[user.user_id]))
        add_count = min(max(0, desired - len(offsets)), len(allowed))
        if add_count:
            offsets.update(int(day) for day in rng.choice(allowed, add_count, replace=False))
        realized_counts[str(user.user_id)] = len(offsets)
        for offset in sorted(offsets):
            rows.append(
                {
                    "user_id": user.user_id,
                    "signup_date": user.signup_date,
                    "period": user.period,
                    "acquisition_source": user.acquisition_source,
                    "acquisition_campaign": user.acquisition_campaign,
                    "acquisition_treatment": user.acquisition_treatment,
                    "activity_date": pd.Timestamp(user.signup_date) + pd.Timedelta(days=offset),
                    "relative_day": offset,
                }
            )
    activity = pd.DataFrame(rows)
    activity["active_minutes"] = np.clip(rng.lognormal(3.2, 0.55, len(activity)), 2, 320)
    activity["content_views"] = np.maximum(1, rng.poisson(activity["active_minutes"] / 3.5))
    feature_usage["active_days_30"] = (
        feature_usage["user_id"].map(realized_counts).fillna(1).astype(int)
    )
    return activity


def _derive_retention_from_activity(
    retention: pd.DataFrame,
    feature_usage: pd.DataFrame,
    activity: pd.DataFrame,
) -> None:
    """Make user-day activity the single source of truth for retention flags."""
    active_days = activity.groupby("user_id", observed=True)["relative_day"].agg(set)

    def has_day(user_id: str, day: int) -> bool:
        return day in active_days.get(user_id, set())

    def has_window(user_id: str) -> bool:
        return bool(active_days.get(user_id, set()).intersection(range(1, 8)))

    retention["retained_d1"] = retention["user_id"].map(lambda user_id: has_day(user_id, 1))
    retention["retained_d3"] = retention["user_id"].map(lambda user_id: has_day(user_id, 3))
    retention["retained_d7"] = retention["user_id"].map(lambda user_id: has_day(user_id, 7))
    retention["retained_d1_7_window"] = retention["user_id"].map(has_window)
    d30 = retention["user_id"].map(lambda user_id: has_day(user_id, 30)).astype("boolean")
    retention["retained_d30"] = d30.where(retention["mature_d30"], pd.NA)
    window_lookup = retention.set_index("user_id")["retained_d1_7_window"]
    feature_usage["retained_d1_7_window"] = feature_usage["user_id"].map(window_lookup)


def _value_and_cost_frames(
    rng: np.random.Generator,
    users: pd.DataFrame,
    activity: pd.DataFrame,
    feature_usage: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Materialize auditable user-day value and every variable acquisition cost.

    Normalized units deliberately avoid any employer-specific currency, price, or contract.
    """
    value = activity[
        [
            "user_id",
            "activity_date",
            "relative_day",
            "active_minutes",
            "acquisition_source",
            "acquisition_campaign",
            "acquisition_treatment",
        ]
    ].copy()
    value = value.loc[value["relative_day"].between(0, 29)].copy()
    source_multiplier = (
        value["acquisition_source"]
        .map({"non_referral": 1.0, "referral_campaign": 1.04, "referral_experiment": 1.035})
        .fillna(1.0)
    )
    value["value_per_hour"] = np.clip(
        3.10 * source_multiplier + rng.normal(0, 0.055, len(value)), 2.70, 3.60
    )
    value["gross_value"] = value["active_minutes"] / 60 * value["value_per_hour"]
    value["variable_service_cost"] = value["gross_value"] * 0.085
    value["contribution_value"] = value["gross_value"] - value["variable_service_cost"]
    value = value.rename(columns={"activity_date": "value_date"})

    acquired_mask = users["acquisition_source"].isin(["referral_campaign", "referral_experiment"])
    acquired_users = users.loc[
        acquired_mask,
        [
            "user_id",
            "signup_date",
            "referrer_user_id",
            "acquisition_source",
            "acquisition_campaign",
            "acquisition_treatment",
        ],
    ].copy()
    acquired_users["base_incentive"] = np.select(
        [
            acquired_users["acquisition_campaign"] == "variant_a",
            acquired_users["acquisition_campaign"].isin(["variant_b", "variant_c"]),
        ],
        [5.8, 7.5],
        default=7.5,
    )
    cost_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(acquired_users.itertuples(index=False)):
        # Fraud/invalid-reward cost is deterministic for a seed and explicitly visible.
        fraud_cost = float(0.42 if row_number % 37 == 0 else 0.0)
        for cost_type, amount in (
            ("incentive", float(row.base_incentive)),
            ("delivery_and_operations", 0.48),
            ("invalid_reward_loss", fraud_cost),
        ):
            cost_rows.append(
                {
                    "cost_event_id": f"cost_{row_number:08d}_{cost_type}",
                    "user_id": row.user_id,
                    "referrer_user_id": row.referrer_user_id,
                    "cost_date": row.signup_date,
                    "cost_type": cost_type,
                    "amount": amount,
                    "acquisition_source": row.acquisition_source,
                    "acquisition_campaign": row.acquisition_campaign,
                    "acquisition_treatment": row.acquisition_treatment,
                }
            )
    costs = pd.DataFrame(cost_rows)

    value_by_user = (
        value.groupby("user_id", observed=True)
        .agg(
            ltv30=("gross_value", "sum"),
            service_cost30=("variable_service_cost", "sum"),
            product_contribution30=("contribution_value", "sum"),
            observed_active_days=("value_date", "nunique"),
            daily_active_hours=("active_minutes", lambda series: float(series.mean() / 60)),
            value_per_hour=("value_per_hour", "mean"),
        )
        .reset_index()
    )
    cost_by_user = (
        costs.groupby("user_id", observed=True)["amount"].sum().rename("variable_acquisition_cost")
        if not costs.empty
        else pd.Series(dtype=float, name="variable_acquisition_cost")
    )
    feature_days = feature_usage.set_index("user_id")["active_days_30"]
    acquired = acquired_users.merge(value_by_user, on="user_id", how="left").fillna(
        {
            "ltv30": 0.0,
            "service_cost30": 0.0,
            "product_contribution30": 0.0,
            "observed_active_days": 0,
            "daily_active_hours": 0.0,
            "value_per_hour": 0.0,
        }
    )
    acquired = acquired.join(cost_by_user, on="user_id")
    acquired["variable_acquisition_cost"] = acquired["variable_acquisition_cost"].fillna(0.0)
    acquired["contribution30"] = (
        acquired["ltv30"] - acquired["service_cost30"] - acquired["variable_acquisition_cost"]
    )
    acquired["active_days_30"] = acquired["user_id"].map(feature_days).fillna(0).astype(int)
    acquired["retention_discount"] = 1.0
    acquired["incentive_cost"] = acquired["base_incentive"]
    acquired["new_user_id"] = acquired["user_id"]
    acquired["version"] = acquired["acquisition_campaign"]
    acquired["activated_date"] = acquired["signup_date"]
    acquired["source_kind"] = np.where(
        acquired["acquisition_source"] == "referral_experiment",
        "randomized_experiment",
        "descriptive_campaign",
    )
    return value, costs, acquired


def _finalize_experiment_outcomes(
    outcomes: pd.DataFrame,
    retention: pd.DataFrame,
    acquired: pd.DataFrame,
) -> pd.DataFrame:
    result = outcomes.copy()
    retained_lookup = retention.set_index("user_id")
    acquired_lookup = acquired.set_index("user_id")
    linked = result["new_user_id"].notna()
    linked_ids = result.loc[linked, "new_user_id"].astype(str)
    result.loc[linked, "retained_d7"] = (
        linked_ids.map(retained_lookup["retained_d7"]).fillna(False).to_numpy()
    )
    result.loc[linked, "retained_d1_7_window"] = (
        linked_ids.map(retained_lookup["retained_d1_7_window"]).fillna(False).to_numpy()
    )
    result.loc[linked, "value30"] = linked_ids.map(acquired_lookup["ltv30"]).fillna(0).to_numpy()
    result.loc[linked, "variable_acquisition_cost"] = (
        linked_ids.map(acquired_lookup["variable_acquisition_cost"]).fillna(0).to_numpy()
    )
    result.loc[linked, "contribution30"] = (
        linked_ids.map(acquired_lookup["contribution30"]).fillna(0).to_numpy()
    )
    return result


def _decision_log() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_id": "decision_referral_ui_v1",
                "decision_date": pd.Timestamp("2025-05-26"),
                "growth_stage": "T→H",
                "business_question": "Should the simplified referral invitation page ship?",
                "evidence_level": "randomized_itt",
                "decision": "ship_with_monitoring",
                "primary_metric": "invite_click_rate",
                "final_metric": "incremental_d7_retained_per_10k_assigned",
                "guardrail_metric": "incremental_contribution30_per_10k_assigned",
                "fact": "Fixed-horizon ITT estimate is positive and assignment health passes.",
                "interpretation": "The simplified hierarchy reduces invitation-action friction.",
                "hypothesis": "A first-screen call-to-action makes the intended action discoverable.",
                "action": "Ship with post-launch novelty, quality and interference monitoring.",
                "limitation": "User-level inference does not resolve social-network interference.",
                "owner_role": "growth_analytics",
                "review_status": "approved_demo_decision",
            },
            {
                "decision_id": "decision_retention_feature_v1",
                "decision_date": pd.Timestamp("2025-06-02"),
                "growth_stage": "W→T",
                "business_question": "Does improving content-save discovery increase early retention?",
                "evidence_level": "randomized_itt",
                "decision": "targeted_ship_then_monitor",
                "primary_metric": "d1_7_window_retention",
                "final_metric": "new_user_retention",
                "guardrail_metric": "experience_complaint_rate",
                "fact": "Feature-use correlation is large, but only randomized evidence is used to claim lift.",
                "interpretation": "Saving helps users create a reason to return.",
                "hypothesis": "A lightweight prompt improves discovery without adding onboarding friction.",
                "action": "Target new users and monitor prompt fatigue by acquisition source.",
                "limitation": "The public data is synthetic and the effect is not an employer result.",
                "owner_role": "growth_analytics",
                "review_status": "approved_demo_decision",
            },
        ]
    )


def generate_growth_daily(seed: int) -> pd.DataFrame:
    """Create a normalized executive growth trend with weekly seasonality and strategy shifts."""
    rng = np.random.default_rng(seed + 20_250)
    dates = pd.date_range("2025-02-17", periods=91, freq="D")
    day = np.arange(len(dates), dtype=float)
    weekly = np.sin(2 * np.pi * day / 7)
    external = 24.0 - 0.11 * np.maximum(day - 25, 0) + 0.30 * weekly + rng.normal(0, 0.16, len(day))
    organic = 16.0 + 0.015 * day + 0.25 * weekly + rng.normal(0, 0.12, len(day))
    referral = (
        4.0
        + 0.035 * day
        + 0.075 * np.maximum(day - 35, 0)
        - 1.65 * np.exp(-((day - 49) ** 2) / 14)
        + 2.0 / (1 + np.exp(-(day - 63) / 2.5))
        + rng.normal(0, 0.10, len(day))
    )
    retained = (
        50.0
        + 0.045 * day
        - 0.030 * np.maximum(day - 45, 0)
        + 0.75 * weekly
        + rng.normal(0, 0.18, len(day))
    )
    dau = retained + 0.35 * (external + organic + referral)
    return pd.DataFrame(
        {
            "date": dates.date,
            "dau_index": np.round(dau, 4),
            "target_index": 80.0,
            "external_new_index": np.round(external, 4),
            "organic_new_index": np.round(organic, 4),
            "referral_new_index": np.round(referral, 4),
            "retained_user_index": np.round(retained, 4),
        }
    )


def _write_frame(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
    temp_name = f"tmp_{table}"
    connection.register(temp_name, frame)
    connection.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM "{temp_name}"')
    connection.unregister(temp_name)


def _create_views(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE OR REPLACE VIEW referral_version_summary AS
        SELECT version,
               SUM(exposure_uv) AS exposure_uv,
               SUM(page_click_uv) AS page_click_uv,
               SUM(invite_click_uv) AS invite_click_uv,
               SUM(share_success_uv) AS share_success_uv,
               SUM(new_user_landing_uv) AS new_user_landing_uv,
               SUM(new_user_register_uv) AS new_user_register_uv,
               SUM(new_user_activate_uv) AS new_user_activate_uv,
               SUM(page_click_uv)::DOUBLE / NULLIF(SUM(exposure_uv), 0) AS page_click_rate,
               SUM(invite_click_uv)::DOUBLE / NULLIF(SUM(page_click_uv), 0) AS invite_click_rate,
               SUM(share_success_uv)::DOUBLE / NULLIF(SUM(invite_click_uv), 0) AS share_success_rate,
               SUM(new_user_activate_uv)::DOUBLE / NULLIF(SUM(exposure_uv), 0) AS activation_per_exposure,
               SUM(new_user_activate_uv)::DOUBLE / NULLIF(SUM(invite_click_uv), 0) AS activation_per_invite_click
        FROM referral_funnel_daily GROUP BY version
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW retention_summary AS
        SELECT period,
               COUNT(*) AS users,
               AVG(CASE WHEN cohort_age_days >= 1 THEN retained_d1::INTEGER END) AS d1,
               AVG(CASE WHEN cohort_age_days >= 3 THEN retained_d3::INTEGER END) AS d3,
               AVG(CASE WHEN mature_d7 THEN retained_d7::INTEGER END) AS d7,
               AVG(CASE WHEN mature_d7 THEN retained_d1_7_window::INTEGER END) AS d1_7_window,
               AVG(CASE WHEN mature_d30 THEN retained_d30::INTEGER END) AS d30
        FROM new_user_retention GROUP BY period
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW experiment_summary AS
        SELECT experiment_id, group_name, COUNT(*) AS users,
               SUM(primary_outcome::INTEGER) AS successes,
               AVG(primary_outcome::INTEGER) AS primary_rate,
               AVG(guardrail_outcome) AS guardrail_value
        FROM experiment_outcomes GROUP BY experiment_id, group_name
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW mart_user_lifecycle AS
        SELECT e.edge_id,
               e.source_kind,
               e.experiment_id,
               e.group_name,
               e.version AS journey_version,
               e.inviter_user_id,
               e.new_user_id,
               e.activated_date,
               u.acquisition_source,
               u.acquisition_campaign,
               u.acquisition_treatment,
               u.channel,
               u.device_type,
               u.region,
               r.cohort_age_days,
               r.mature_d7,
               r.mature_d30,
               r.retained_d1,
               r.retained_d7,
               r.retained_d1_7_window,
               r.retained_d30,
               a.ltv30 AS value30,
               a.variable_acquisition_cost,
               a.contribution30
        FROM referral_edges e
        JOIN users u ON u.user_id = e.new_user_id
        JOIN new_user_retention r ON r.user_id = e.new_user_id
        LEFT JOIN acquired_users a ON a.new_user_id = e.new_user_id
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW mart_acquisition_quality AS
        SELECT acquisition_source,
               COALESCE(acquisition_campaign, 'not_applicable') AS acquisition_campaign,
               COALESCE(acquisition_treatment, 'not_applicable') AS acquisition_treatment,
               COUNT(*) AS acquired_users,
               SUM(CASE WHEN mature_d7 THEN 1 ELSE 0 END) AS mature_d7_users,
               AVG(CASE WHEN mature_d7 THEN retained_d7::INTEGER END) AS d7_retention,
               AVG(CASE WHEN mature_d7 THEN retained_d1_7_window::INTEGER END) AS d1_7_window_retention,
               SUM(COALESCE(value30, 0)) AS total_value30,
               SUM(COALESCE(variable_acquisition_cost, 0)) AS total_variable_acquisition_cost,
               SUM(COALESCE(contribution30, 0)) AS total_contribution30,
               SUM(COALESCE(value30, 0)) / NULLIF(SUM(COALESCE(variable_acquisition_cost, 0)), 0) AS average_ltv_cac
        FROM mart_user_lifecycle
        GROUP BY acquisition_source,
                 COALESCE(acquisition_campaign, 'not_applicable'),
                 COALESCE(acquisition_treatment, 'not_applicable')
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW mart_experiment_user_value AS
        SELECT a.experiment_id,
               a.user_id AS assignment_user_id,
               a.group_name,
               a.hash_bucket,
               a.assigned_at,
               a.channel,
               a.device_type,
               a.region,
               COALESCE(x.was_exposed, FALSE) AS was_exposed,
               x.exposure_week,
               x.exposed_at,
               o.outcome_observable,
               o.primary_outcome,
               o.new_user_id,
               o.referred_activated,
               o.retained_d7,
               o.retained_d1_7_window,
               o.value30,
               o.variable_acquisition_cost,
               o.contribution30,
               o.observed_at
        FROM experiment_assignments a
        LEFT JOIN experiment_exposures x USING(experiment_id, user_id, group_name)
        JOIN experiment_outcomes o USING(experiment_id, user_id, group_name)
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW mart_experiment_effects_itt AS
        SELECT experiment_id,
               group_name,
               COUNT(*) AS assigned_users,
               SUM(was_exposed::INTEGER) AS exposed_users,
               SUM(primary_outcome::INTEGER) AS primary_successes,
               SUM(referred_activated::INTEGER) AS activated_new_users,
               SUM(retained_d7::INTEGER) AS retained_d7_users,
               SUM(retained_d1_7_window::INTEGER) AS retained_d1_7_window_users,
               SUM(value30) AS value30,
               SUM(variable_acquisition_cost) AS variable_acquisition_cost,
               SUM(contribution30) AS contribution30
        FROM mart_experiment_user_value
        GROUP BY 1,2
        """
    )


def _quality_checks(connection: duckdb.DuckDBPyConnection, run_id: str) -> pd.DataFrame:
    queries: list[tuple[str, str, str]] = [
        ("users_user_id_not_null", "SELECT COUNT(*) FROM users WHERE user_id IS NULL", "value = 0"),
        (
            "users_user_id_unique",
            "SELECT COUNT(*) - COUNT(DISTINCT user_id) FROM users",
            "value = 0",
        ),
        (
            "growth_event_id_unique",
            "SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM growth_events",
            "value = 0",
        ),
        (
            "activity_after_signup",
            "SELECT COUNT(*) FROM user_daily_activity WHERE activity_date < signup_date",
            "value = 0",
        ),
        (
            "growth_event_after_signup",
            "SELECT COUNT(*) FROM growth_events e JOIN users u USING(user_id) WHERE CAST(e.event_at AS DATE) < u.signup_date",
            "value = 0",
        ),
        (
            "retention_bounded",
            "SELECT COUNT(*) FROM new_user_retention WHERE retained_d1_7_window NOT IN (TRUE, FALSE)",
            "value = 0",
        ),
        (
            "reward_nonnegative",
            "SELECT COUNT(*) FROM referral_rewards WHERE incentive_cost < 0",
            "value = 0",
        ),
        (
            "experiment_group_valid",
            "SELECT COUNT(*) FROM experiment_assignments WHERE group_name NOT IN ('control','treatment')",
            "value = 0",
        ),
        (
            "experiment_single_assignment",
            "SELECT COUNT(*) FROM (SELECT experiment_id,user_id,COUNT(*) n FROM experiment_assignments GROUP BY 1,2 HAVING n>1)",
            "value = 0",
        ),
        (
            "outcome_after_assignment",
            "SELECT COUNT(*) FROM experiment_outcomes o JOIN experiment_assignments a USING(experiment_id,user_id,group_name) WHERE o.observed_at < a.assigned_at",
            "value = 0",
        ),
        (
            "funnel_monotonic",
            "SELECT COUNT(*) FROM referral_funnel_daily WHERE NOT (exposure_uv >= page_click_uv AND page_click_uv >= invite_click_uv AND invite_click_uv >= share_success_uv AND share_success_uv >= new_user_landing_uv AND new_user_landing_uv >= new_user_register_uv AND new_user_register_uv >= new_user_activate_uv)",
            "value = 0",
        ),
        (
            "activity_day_range",
            "SELECT COUNT(*) FROM feature_usage WHERE active_days_30 NOT BETWEEN 1 AND 30",
            "value = 0",
        ),
        (
            "feature_count_nonnegative",
            "SELECT COUNT(*) FROM feature_usage WHERE feature_use_count < 0",
            "value = 0",
        ),
        (
            "acquired_cost_nonnegative",
            "SELECT COUNT(*) FROM acquired_users WHERE incentive_cost < 0",
            "value = 0",
        ),
        (
            "metric_definitions_present",
            "SELECT CASE WHEN COUNT(*) >= 10 THEN 0 ELSE 1 END FROM metric_definitions",
            "value = 0",
        ),
        (
            "periods_present",
            "SELECT CASE WHEN COUNT(DISTINCT period) = 2 THEN 0 ELSE 1 END FROM new_user_retention",
            "value = 0",
        ),
        (
            "growth_trend_complete",
            "SELECT CASE WHEN COUNT(*) = 91 AND MIN(dau_index) > 0 AND MIN(target_index) > 0 THEN 0 ELSE 1 END FROM growth_daily",
            "value = 0",
        ),
        (
            "referral_edge_inviter_fk",
            "SELECT COUNT(*) FROM referral_edges e LEFT JOIN users u ON e.inviter_user_id=u.user_id WHERE u.user_id IS NULL",
            "value = 0",
        ),
        (
            "referral_edge_invitee_fk",
            "SELECT COUNT(*) FROM referral_edges e LEFT JOIN users u ON e.new_user_id=u.user_id WHERE u.user_id IS NULL",
            "value = 0",
        ),
        (
            "referral_invitee_has_activity_value_cost",
            """SELECT COUNT(*) FROM referral_edges e
               WHERE NOT EXISTS (SELECT 1 FROM user_daily_activity a WHERE a.user_id=e.new_user_id)
                  OR NOT EXISTS (SELECT 1 FROM user_daily_value v WHERE v.user_id=e.new_user_id)
                  OR NOT EXISTS (SELECT 1 FROM cost_events c WHERE c.user_id=e.new_user_id)""",
            "value = 0",
        ),
        (
            "exposure_after_assignment",
            """SELECT COUNT(*) FROM experiment_exposures e
               JOIN experiment_assignments a USING(experiment_id,user_id,group_name)
               WHERE e.was_exposed AND e.exposed_at < a.assigned_at""",
            "value = 0",
        ),
        (
            "retention_exact_day_activity_consistent",
            """SELECT COUNT(*) FROM new_user_retention r WHERE
               retained_d1 <> EXISTS(SELECT 1 FROM user_daily_activity a WHERE a.user_id=r.user_id AND a.relative_day=1)
               OR retained_d3 <> EXISTS(SELECT 1 FROM user_daily_activity a WHERE a.user_id=r.user_id AND a.relative_day=3)
               OR retained_d7 <> EXISTS(SELECT 1 FROM user_daily_activity a WHERE a.user_id=r.user_id AND a.relative_day=7)
               OR (mature_d30 AND retained_d30 <> EXISTS(SELECT 1 FROM user_daily_activity a WHERE a.user_id=r.user_id AND a.relative_day=30))
               OR (NOT mature_d30 AND retained_d30 IS NOT NULL)""",
            "value = 0",
        ),
        (
            "retention_window_activity_consistent",
            """SELECT COUNT(*) FROM new_user_retention r WHERE
               retained_d1_7_window <> EXISTS(
                 SELECT 1 FROM user_daily_activity a
                 WHERE a.user_id=r.user_id AND a.relative_day BETWEEN 1 AND 7
               )""",
            "value = 0",
        ),
        (
            "experiment_referral_outcome_consistent",
            """SELECT COUNT(*) FROM experiment_outcomes o
               JOIN new_user_retention r ON o.new_user_id=r.user_id
               WHERE o.experiment_id='referral_ui_simplification'
                 AND (o.retained_d7 <> r.retained_d7
                      OR o.retained_d1_7_window <> r.retained_d1_7_window)""",
            "value = 0",
        ),
        (
            "contribution30_identity",
            """SELECT COUNT(*) FROM acquired_users
               WHERE ABS(contribution30 - (ltv30-service_cost30-variable_acquisition_cost)) > 1e-9""",
            "value = 0",
        ),
        (
            "value30_window_offsets_0_29",
            "SELECT COUNT(*) FROM user_daily_value WHERE relative_day NOT BETWEEN 0 AND 29",
            "value = 0",
        ),
        (
            "decision_log_present",
            "SELECT CASE WHEN COUNT(*) >= 2 THEN 0 ELSE 1 END FROM decision_log",
            "value = 0",
        ),
        (
            "ui_experiment_cost_policy_equal",
            """SELECT CASE WHEN COUNT(DISTINCT ROUND(base_incentive,8))=1 THEN 0 ELSE 1 END
               FROM acquired_users WHERE acquisition_source='referral_experiment'""",
            "value = 0",
        ),
        (
            "ui_experiment_dgp_policy_present",
            """SELECT CASE WHEN COUNT(*)=1 THEN 0 ELSE 1 END FROM dgp_policy
               WHERE experiment_id='referral_ui_simplification'
                 AND downstream_quality_policy LIKE 'identical%'
                 AND cost_policy LIKE 'identical%'""",
            "value = 0",
        ),
    ]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = []
    for name, query, threshold in queries:
        value = float(connection.execute(query).fetchone()[0])
        rows.append(
            {
                "run_id": run_id,
                "checked_at": now,
                "check_name": name,
                "status": "pass" if value == 0 else "fail",
                "observed_value": value,
                "threshold": threshold,
                "details": "Deterministic public-demo validation",
            }
        )
    return pd.DataFrame(rows)


def generate_database(
    db_path: Path, *, users: int, seed: int, force: bool = False
) -> dict[str, Any]:
    if users < 2_000:
        raise ValueError("users must be at least 2,000 for meaningful demo segments")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not force:
        raise FileExistsError(f"Database already exists: {db_path}. Use --force to replace it.")
    if db_path.exists():
        db_path.unlink()
    rng = np.random.default_rng(seed)
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).replace(tzinfo=None)
    frames: dict[str, pd.DataFrame] = {}
    frames["users"] = generate_users(rng, users)
    referral_frames = generate_referral(rng, frames["users"])
    frames.update(referral_frames)
    (
        frames["experiment_assignments"],
        frames["experiment_exposures"],
        frames["experiment_outcomes"],
        frames["experiment_definitions"],
        experiment_edges,
    ) = generate_experiments(rng, frames["users"])
    frames["referral_edges"] = pd.concat(
        [frames["referral_edges"], experiment_edges], ignore_index=True
    )
    frames["new_user_retention"], frames["feature_usage"] = generate_retention(rng, frames["users"])
    frames["user_daily_activity"] = _activity_rows(
        rng,
        frames["users"],
        frames["feature_usage"],
        frames["new_user_retention"],
    )
    _derive_retention_from_activity(
        frames["new_user_retention"],
        frames["feature_usage"],
        frames["user_daily_activity"],
    )
    frames["new_user_funnel"], new_user_events = generate_new_user_funnel(
        rng, frames["users"], frames["new_user_retention"]
    )
    experiment_activation_events = experiment_edges.rename(
        columns={
            "new_user_id": "user_id",
            "activated_date": "event_at",
            "version": "campaign_version",
        }
    )
    if not experiment_activation_events.empty:
        experiment_activation_events = experiment_activation_events.assign(
            event_id=lambda frame: "exp_new_activate_" + frame["user_id"].astype(str),
            event_name="new_user_activate",
            event_at=lambda frame: pd.to_datetime(frame["event_at"]),
            period="referral_experiment",
        )[["event_id", "user_id", "event_name", "event_at", "period", "campaign_version"]]
    else:
        experiment_activation_events = pd.DataFrame(
            columns=["event_id", "user_id", "event_name", "event_at", "period", "campaign_version"]
        )
    frames["growth_events"] = pd.concat(
        [frames["growth_events"], new_user_events, experiment_activation_events],
        ignore_index=True,
    )
    (
        frames["user_daily_value"],
        frames["cost_events"],
        frames["acquired_users"],
    ) = _value_and_cost_frames(
        rng,
        frames["users"],
        frames["user_daily_activity"],
        frames["feature_usage"],
    )
    frames["experiment_outcomes"] = _finalize_experiment_outcomes(
        frames["experiment_outcomes"],
        frames["new_user_retention"],
        frames["acquired_users"],
    )
    frames["metric_definitions"] = pd.DataFrame(METRIC_DEFINITIONS)
    frames["growth_daily"] = generate_growth_daily(seed)
    frames["decision_log"] = _decision_log()
    frames["analysis_snapshot"] = pd.DataFrame(
        [
            {
                "snapshot_id": "public_demo_v2",
                "as_of_date": ANALYSIS_AS_OF_DATE.date(),
                "primary_experiment_horizon_days": 14,
                "value_followup_days": 30,
                "description": "Deterministic privacy-safe public portfolio snapshot",
            }
        ]
    )
    frames["dgp_policy"] = pd.DataFrame(
        [
            {
                "policy_id": "referral_ui_single_treatment_path",
                "experiment_id": "referral_ui_simplification",
                "treatment_path": "assignment → tracked exposure → invite click → referred activation",
                "downstream_quality_policy": "identical retention, activity and value DGP across arms",
                "cost_policy": "identical incentive and variable cost schedule across arms",
                "known_truth": "treatment increases invite-click and activation probability only",
                "claim_boundary": "network interference is not simulated away and remains a risk",
            }
        ]
    )

    connection = duckdb.connect(str(db_path))
    try:
        schema_path = PROJECT_ROOT / "sql" / "schema" / "001_core.sql"
        connection.execute(schema_path.read_text(encoding="utf-8"))
        for table, frame in frames.items():
            _write_frame(connection, table, frame)
        _create_views(connection)
        quality = _quality_checks(connection, run_id)
        _write_frame(connection, "data_quality_runs", quality)
        completed = datetime.now(timezone.utc).replace(tzinfo=None)
        ingestion = pd.DataFrame(
            [
                {
                    "run_id": run_id,
                    "source_name": "deterministic_synthetic_public_demo",
                    "started_at": started,
                    "completed_at": completed,
                    "row_count": sum(len(frame) for frame in frames.values()),
                    "seed": seed,
                    "status": "completed",
                }
            ]
        )
        _write_frame(connection, "ingestion_runs", ingestion)
        connection.execute("CHECKPOINT")
        counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in frames
        }
        quality_failed = int((quality["status"] == "fail").sum())
        return {
            "database": str(db_path),
            "seed": seed,
            "users_requested": users,
            "rows": counts,
            "quality_checks": len(quality),
            "quality_failed": quality_failed,
            "run_id": run_id,
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate GrowthLab's privacy-safe deterministic demo database."
    )
    parser.add_argument(
        "--db-path", type=Path, default=Path(os.getenv("GROWTHLAB_DB_PATH", DEFAULT_DB))
    )
    parser.add_argument(
        "--users", type=int, default=int(os.getenv("GROWTHLAB_DEMO_USERS", "100000"))
    )
    parser.add_argument("--seed", type=int, default=int(os.getenv("GROWTHLAB_DEMO_SEED", "42")))
    parser.add_argument("--force", action="store_true", help="Replace an existing demo database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_database(
        args.db_path.resolve(), users=args.users, seed=args.seed, force=args.force
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
