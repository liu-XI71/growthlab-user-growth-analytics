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
    return pd.DataFrame(
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
        }
    )


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
    window_probability = np.clip(device_base + channel_adjustment + current_adjustment, 0.08, 0.90)

    d1_probability = window_probability * 0.76
    d3_probability = window_probability * 0.56
    d7_probability = window_probability * 0.38
    d30_probability = window_probability * 0.24
    retained_window = rng.random(len(users)) < window_probability
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
        ]
    ].copy()
    retention["retained_d1"] = rng.random(len(users)) < d1_probability
    retention["retained_d3"] = rng.random(len(users)) < d3_probability
    retention["retained_d7"] = rng.random(len(users)) < d7_probability
    retention["retained_d1_7_window"] = retained_window
    retention["retained_d30"] = rng.random(len(users)) < d30_probability

    active_days = np.clip(rng.poisson(4.2 + retained_window * 5.8, len(users)) + 1, 1, 30)
    daily_hours = np.clip(
        rng.lognormal(-0.45 + retained_window * 0.24, 0.48, len(users)), 0.08, 5.5
    )
    benchmark = (active_days >= np.quantile(active_days, 0.75)) & (
        daily_hours >= np.quantile(daily_hours, 0.75)
    )
    feature_probability = np.where(benchmark, 0.57, 0.21)
    feature_used = rng.random(len(users)) < feature_probability
    feature_usage = users[["user_id", "period", "channel", "device_type", "region"]].copy()
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

    activated = referral.loc[referral["new_user_activate"]].copy()
    activated["new_user_id"] = [f"ref_new_{index:08d}" for index in range(len(activated))]
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
        }
    )
    rewards = acquired[
        ["new_user_id", "inviter_user_id", "version", "activated_date", "incentive_cost"]
    ].copy()
    rewards["reward_id"] = [f"reward_{index:08d}" for index in range(len(rewards))]
    rewards["reward_status"] = "issued"
    return {
        "referral_user_journeys": referral,
        "referral_funnel_daily": daily,
        "growth_events": pd.concat(events, ignore_index=True),
        "acquired_users": acquired,
        "referral_rewards": rewards,
    }


def _assign_experiment(
    users: pd.DataFrame, experiment_id: str, salt: str, assigned_at: str
) -> pd.DataFrame:
    assignments = [assign_hash_group(user_id, salt=salt) for user_id in users["user_id"]]
    frame = users[["user_id", "channel", "device_type", "region"]].copy()
    frame["experiment_id"] = experiment_id
    frame["group_name"] = [item["group"] for item in assignments]
    frame["hash_bucket"] = [item["bucket"] for item in assignments]
    frame["assigned_at"] = pd.Timestamp(assigned_at)
    return frame


def generate_experiments(
    rng: np.random.Generator, users: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
        },
    ]
    specs = pd.DataFrame(experiment_specs)
    assignment_frames = []
    outcome_frames = []
    sample = users.sample(min(len(users), 80000), random_state=29).copy()
    for index, spec in enumerate(experiment_specs):
        assignment = _assign_experiment(
            sample,
            str(spec["experiment_id"]),
            salt=f"growthlab_public_demo_{index}",
            assigned_at=f"2025-05-{5 + index * 7:02d}",
        )
        group = assignment["group_name"].to_numpy()
        if spec["kind"] == "aa":
            group_rates = {"control": 0.160, "treatment": 0.160}
        elif spec["experiment_id"] == "referral_ui_simplification":
            group_rates = {"control": 0.160, "treatment": 0.213}
        else:
            group_rates = {"control": 0.401, "treatment": 0.438}
        # Use exact group-level rates so the public demo remains stable even when
        # QA generates a small database. Individual outcomes are still randomly
        # selected within each hash-assigned group.
        primary = np.zeros(len(assignment), dtype=bool)
        for group_name, rate in group_rates.items():
            indices = np.flatnonzero(group == group_name)
            successes = int(round(rate * len(indices)))
            selected = rng.choice(indices, successes, replace=False)
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
        outcomes["observed_at"] = assignment["assigned_at"] + pd.to_timedelta(14, unit="D")
        assignment_frames.append(assignment)
        outcome_frames.append(outcomes)
    return (
        pd.concat(assignment_frames, ignore_index=True),
        pd.concat(outcome_frames, ignore_index=True),
        specs,
    )


def _activity_rows(
    rng: np.random.Generator, users: pd.DataFrame, feature_usage: pd.DataFrame
) -> pd.DataFrame:
    repeat_count = np.clip(feature_usage["active_days_30"].to_numpy(), 1, 12)
    repeated_index = np.repeat(np.arange(len(users)), repeat_count)
    activity = users.iloc[repeated_index][["user_id", "signup_date", "period"]].reset_index(
        drop=True
    )
    within_user_offset = np.concatenate([np.arange(count) for count in repeat_count])
    activity["activity_date"] = pd.to_datetime(activity["signup_date"]) + pd.to_timedelta(
        within_user_offset, unit="D"
    )
    activity["active_minutes"] = np.clip(rng.lognormal(3.2, 0.55, len(activity)), 2, 320)
    activity["content_views"] = np.maximum(1, rng.poisson(activity["active_minutes"] / 3.5))
    return activity


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
               AVG(retained_d1::INTEGER) AS d1,
               AVG(retained_d3::INTEGER) AS d3,
               AVG(retained_d7::INTEGER) AS d7,
               AVG(retained_d1_7_window::INTEGER) AS d1_7_window,
               AVG(retained_d30::INTEGER) AS d30
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
    frames["new_user_retention"], frames["feature_usage"] = generate_retention(rng, frames["users"])
    frames["new_user_funnel"], new_user_events = generate_new_user_funnel(
        rng, frames["users"], frames["new_user_retention"]
    )
    referral_frames = generate_referral(rng, frames["users"])
    frames.update(referral_frames)
    frames["growth_events"] = pd.concat(
        [frames["growth_events"], new_user_events], ignore_index=True
    )
    (
        frames["experiment_assignments"],
        frames["experiment_outcomes"],
        frames["experiment_definitions"],
    ) = generate_experiments(rng, frames["users"])
    frames["user_daily_activity"] = _activity_rows(rng, frames["users"], frames["feature_usage"])
    frames["metric_definitions"] = pd.DataFrame(METRIC_DEFINITIONS)
    frames["growth_daily"] = generate_growth_daily(seed)

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
