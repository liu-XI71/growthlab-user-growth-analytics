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
            "nao]º¶‰ËkºwµçF–æU÷&FR#¢ãCÀ¢&ÖFUö'6öÇWFR#¢ã#RÀ¢&Ç†#¢ãRÀ¢'÷vW"#¢ãƒÀ¢&F–Ç•öVÆ–v–&ÆU÷W6W'2#¢À¢ÒÀ¢Ğ¢7V72ÒBäFFg&ÖR†W‡W&–ÖVçE÷7V72¢76–væÖVçEög&ÖW2ÒµĞ¢÷WF6öÖUög&ÖW2ÒµĞ¢6×ÆRÒW6W'2ç6×ÆR†Ö–â†ÆVâ‡W6W'2’Âƒ’Â&æFöÕ÷7FFSÓ#’’æ6÷’‚¢f÷"–æFW‚Â7V2–âVçVÖW&FR†W‡W&–ÖVçE÷7V72“ ¢76–væÖVçBÒö76–våöW‡W&–ÖVçB€¢6×ÆRÀ¢7G"‡7V5²&W‡W&–ÖVçEö–B%Ò’À¢6ÇCÖb&w&÷wF†Æ%÷V&Æ–5öFVÖõ÷¶–æFW‡Ò"À¢76–væVEöCÖb###RÓR×³R²–æFW‚¢s£&GÒ"À¢¢w&÷WÒ76–væÖVçE²&w&÷WöæÖR%ÒçFõöçV×’‚¢–b7V5²&¶–æB%ÒÓÒ&# ¢w&÷W÷&FW2Ò²&6öçG&öÂ#¢ãcÂ'G&VFÖVçB#¢ãcĞ¢VÆ–b7V5²&W‡W&–ÖVçEö–B%ÒÓÒ'&VfW'&Å÷V•÷6–×Æ–f–6F–öâ# ¢w&÷W÷&FW2Ò²&6öçG&öÂ#¢ãcÂ'G&VFÖVçB#¢ã#7Ğ¢VÇ6S ¢w&÷W÷&FW2Ò²&6öçG&öÂ#¢ãCÂ'G&VFÖVçB#¢ãC3‡Ğ¢2W6RW†7Bw&÷WÖÆWfVÂ&FW26òF†RV&Æ–2FVÖò&VÖ–ç27F&ÆRWfVâv†Và¢2vVæW&FW26ÖÆÂFF&6Râ–æF—f–GVÂ÷WF6öÖW2&R7F–ÆÂ&æFöÖÇ¢26VÆV7FVBv—F†–âV6‚†6‚Ö76–væVBw&÷Wà¢&–Ö'’Òçç¦W&÷2†ÆVâ†76–væÖVçB’ÂGG—SÖ&ööÂ¢f÷"w&÷WöæÖRÂ&FR–âw&÷W÷&FW2æ—FV×2‚“ ¢–æF–6W2ÒçæfÆFæöç¦W&ò†w&÷WÓÒw&÷WöæÖR¢7V66W76W2Ò–çB‡&÷VæB‡&FR¢ÆVâ†–æF–6W2’’¢6VÆV7FVBÒ&æræ6†ö–6R†–æF–6W2Â7V66W76W2Â&WÆ6SÔfÇ6R¢&–Ö'•·6VÆV7FVEÒÒG'VP¢–b7V5²&W‡W&–ÖVçEö–B%ÒÓÒ'&VfW'&Å÷V•÷6–×Æ–f–6F–öâ# ¢wV&G&–ÂÒçæ6Æ—‡&ærææ÷&ÖÂƒãƒBÂã"ÂÆVâ†76–væÖVçB’’ÂãÂ"ãR¢VÆ–b7V5²&W‡W&–ÖVçEö–B%ÒÓÒ&6öçFVçE÷6fUöçVFvR# ¢wV&G&–ÂÒçæ6Æ—‡&ærææ÷&ÖÂƒã‚ÂãBÂÆVâ†76–væÖVçB’’ÂÂãb¢VÇ6S ¢wV&G&–ÂÒçæ6Æ—‡&ærææ÷&ÖÂƒãƒÂã"ÂÆVâ†76–væÖVçB’’ÂãÂ"ãR¢÷WF6öÖW2Ò76–væÖVçEµ²'W6W%ö–B"Â&W‡W&–ÖVçEö–B"Â&w&÷WöæÖR%ÕÒæ6÷’‚¢÷WF6öÖW5²'&–Ö'•ö÷WF6öÖR%ÒÒ&–Ö'¢÷WF6öÖW5²&wV&G&–Åö÷WF6öÖR%ÒÒwV&G&–À¢÷WF6öÖW5²&ö'6W'fVEöB%ÒÒ76–væÖVçE²&76–væVEöB%Ò²BçFõ÷F–ÖVFVÇFƒBÂVæ—CÒ$B"¢76–væÖVçEög&ÖW2æVæB†76–væÖVçB¢÷WF6öÖUög&ÖW2æVæB†÷WF6öÖW2¢&WGW&â€¢Bæ6öæ6B†76–væÖVçEög&ÖW2Â–væ÷&Uö–æFWƒÕG'VR’À¢Bæ6öæ6B†÷WF6öÖUög&ÖW2Â–væ÷&Uö–æFWƒÕG'VR’À¢7V72À¢  ¦FVbö7F—f—G•÷&÷w2€¢&æs¢çç&æFöÒävVæW&F÷"ÂW6W'3¢BäFFg&ÖRÂfVGW&U÷W6vS¢BäFFg&ÖP¢’ÓâBäFFg&ÖS ¢&WVEö6÷VçBÒçæ6Æ—†fVGW&U÷W6vU²&7F—fUöF—5ó3%ÒçFõöçV×’‚’ÂÂ"¢&WVFVEö–æFW‚Òçç&WVB†çæ&ævR†ÆVâ‡W6W'2’’Â&WVEö6÷VçB¢7F—f—G’ÒW6W'2æ–Æö5·&WVFVEö–æFW…Õµ²'W6W%ö–B"Â'6–vçWöFFR"Â'W&–öB%ÕÒç&W6WEö–æFW‚€¢G&÷ÕG'VP¢¢v—F†–å÷W6W%ööfg6WBÒçæ6öæ6FVæFR…¶çæ&ævR†6÷VçB’f÷"6÷VçB–â&WVEö6÷VçEÒ¢7F—f—G•²&7F—f—G•öFFR%ÒÒBçFõöFFWF–ÖR†7F—f—G•²'6–vçWöFFR%Ò’²BçFõ÷F–ÖVFVÇF€¢v—F†–å÷W6W%ööfg6WBÂVæ—CÒ$B ¢¢7F—f—G•²&7F—fUöÖ–çWFW2%ÒÒçæ6Æ—‡&æræÆövæ÷&ÖÂƒ2ã"ÂãSRÂÆVâ†7F—f—G’’’Â"Â3#¢7F—f—G•²&6öçFVçE÷f–Ww2%ÒÒçæÖ†–×VÒƒÂ&ærçö—76öâ†7F—f—G•²&7F—fUöÖ–çWFW2%Òò2ãR’¢&WGW&â7F—f—G  ¦FVbvVæW&FUöw&÷wF…öF–Ç’‡6VVC¢–çB’ÓâBäFFg&ÖS ¢""$7&VFRæ÷&ÖÆ—¦VBW†V7WF—fRw&÷wF‚G&VæBv—F‚vVV¶Ç’6V6öæÆ—G’æB7G&FVw’6†–gG2â"" ¢&ærÒçç&æFöÒæFVfVÇE÷&ær‡6VVB²#ó#S¢FFW2ÒBæFFU÷&ævR‚###RÓ"Ór"ÂW&–öG3Ó“Âg&WÒ$B"¢F’Òçæ&ævR†ÆVâ†FFW2’ÂGG—SÖfÆöB¢vVV¶Ç’Òçç6–âƒ"¢çç’¢F’òr¢W‡FW&æÂÒ#BãÒã¢çæÖ†–×VÒ†F’Ò#RÂ’²ã3¢vVV¶Ç’²&ærææ÷&ÖÂƒÂãbÂÆVâ†F’’¢÷&væ–2Òbã²ãR¢F’²ã#R¢vVV¶Ç’²&ærææ÷&ÖÂƒÂã"ÂÆVâ†F’’¢&VfW'&ÂÒ€¢Bã ¢²ã3R¢F¢²ãsR¢çæÖ†–×VÒ†F’Ò3RÂ¢ÒãcR¢çæW‡‚Ò‚†F’ÒC’’¢¢"’òB¢²"ãòƒ²çæW‡‚Ò†F’Òc2’ò"ãR’¢²&ærææ÷&ÖÂƒÂãÂÆVâ†F’’¢¢&WF–æVBÒ€¢Sã ¢²ãCR¢F¢Òã3¢çæÖ†–×VÒ†F’ÒCRÂ¢²ãsR¢vVV¶Ç¢²&ærææ÷&ÖÂƒÂã‚ÂÆVâ†F’’¢¢FRÒ&WF–æVB²ã3R¢†W‡FW&æÂ²÷&væ–2²&VfW'&Â¢&WGW&âBäFFg&ÖR€¢°¢&FFR#¢FFW2æFFRÀ¢&FUö–æFW‚#¢çç&÷VæB†FRÂB’À¢'F&vWEö–æFW‚#¢ƒãÀ¢&W‡FW&æÅöæWuö–æFW‚#¢çç&÷VæB†W‡FW&æÂÂB’À¢&÷&væ–5öæWuö–æFW‚#¢çç&÷VæB†÷&væ–2ÂB’À¢'&VfW'&ÅöæWuö–æFW‚#¢çç&÷VæB‡&VfW'&ÂÂB’À¢'&WF–æVE÷W6W%ö–æFW‚#¢çç&÷VæB‡&WF–æVBÂB’À¢Ğ¢  ¦FVb÷w&—FUög&ÖR†6öææV7F–öã¢GV6¶F"äGV6´D%”6öææV7F–öâÂF&ÆS¢7G"Âg&ÖS¢BäFFg&ÖR’ÓâæöæS ¢FV×öæÖRÒb'F×÷·F&ÆWÒ ¢6öææV7F–öâç&Vv—7FW"‡FV×öæÖRÂg&ÖR¢6öææV7F–öâæW†V7WFR†bt5$TDRõ"$UÄ4RD$ÄR'·F&ÆWÒ"24TÄT5B¢e$ôÒ'·FV×öæÖWÒ"r¢6öææV7F–öâçVç&Vv—7FW"‡FV×öæÖR  ¦FVbö7&VFU÷f–Ww2†6öææV7F–öã¢GV6¶F"äGV6´D%”6öææV7F–öâ’ÓâæöæS ¢6öææV7F–öâæW†V7WFR€¢"" ¢5$TDRõ"$UÄ4Rd”Ur&VfW'&Å÷fW'6–öå÷7VÖÖ'’0¢4TÄT5BfW'6–öâÀ¢5TÒ†W‡÷7W&U÷Wb’2W‡÷7W&U÷WbÀ¢5TÒ‡vUö6Æ–6µ÷Wb’2vUö6Æ–6µ÷WbÀ¢5TÒ†–çf—FUö6Æ–6µ÷Wb’2–çf—FUö6Æ–6µ÷WbÀ¢5TÒ‡6†&U÷7V66W75÷Wb’26†&U÷7V66W75÷WbÀ¢5TÒ†æWu÷W6W%öÆæF–æu÷Wb’2æWu÷W6W%öÆæF–æu÷WbÀ¢5TÒ†æWu÷W6W%÷&Vv—7FW%÷Wb’2æWu÷W6W%÷&Vv—7FW%÷WbÀ¢5TÒ†æWu÷W6W%ö7F—fFU÷Wb’2æWu÷W6W%ö7F—fFU÷WbÀ¢5TÒ‡vUö6Æ–6µ÷Wb“£¤DõT$ÄRòåTÄÄ”b…5TÒ†W‡÷7W&U÷Wb’Â’2vUö6Æ–6µ÷&FRÀ¢5TÒ†–çf—FUö6Æ–6µ÷Wb“£¤DõT$ÄRòåTÄÄ”b…5TÒ‡vUö6Æ–6µ÷Wb’Â’2–çf—FUö6Æ–6µ÷&FRÀ¢5TÒ‡6†&U÷7V66W75÷Wb“£¤DõT$ÄRòåTÄÄ”b…5TÒ†–çf—FUö6Æ–6µ÷Wb’Â’26†&U÷7V66W75÷&FRÀ¢5TÒ†æWu÷W6W%ö7F—fFU÷Wb“£¤DõT$ÄRòåTÄÄ”b…5TÒ†W‡÷7W&U÷Wb’Â’27F—fF–öå÷W%öW‡÷7W&RÀ¢5TÒ†æWu÷W6W%ö7F—fFU÷Wb“£¤DõT$ÄRòåTÄÄ”b…5TÒ†–çf—FUö6Æ–6µ÷Wb’Â’27F—fF–öå÷W%ö–çf—FUö6Æ–6°¢e$ôÒ&VfW'&ÅögVææVÅöF–Ç’u$õU%’fW'6–öà¢"" ¢¢6öææV7F–öâæW†V7WFR€¢"" ¢5$TDRõ"$UÄ4Rd”Ur&WFVçF–öå÷7VÖÖ'’0¢4TÄT5BW&–öBÀ¢4õTåB‚¢’2W6W'2À¢dr‡&WF–æVEöC£¤”åDTtU"’2CÀ¢dr‡&WF–æVEöC3£¤”åDTtU"’2C2À¢dr‡&WF–æVEöCs£¤”åDTtU"’2CrÀ¢dr‡&WF–æVEöCóu÷v–æF÷s£¤”åDTtU"’2Cóu÷v–æF÷rÀ¢dr‡&WF–æVEöC3£¤”åDTtU"’2C3 ¢e$ôÒæWu÷W6W%÷&WFVçF–öâu$õU%’W&–ö@¢"" ¢¢6öææV7F–öâæW†V7WFR€¢"" ¢5$TDRõ"$UÄ4Rd”UrW‡W&–ÖVçE÷7VÖÖ'’0¢4TÄT5BW‡W&–ÖVçEö–BÂw&÷WöæÖRÂ4õTåB‚¢’2W6W'2À¢5TÒ‡&–Ö'•ö÷WF6öÖS£¤”åDTtU"’27V66W76W2À¢dr‡&–Ö'•ö÷WF6öÖS£¤”åDTtU"’2&–Ö'•÷&FRÀ¢dr†wV&G&–Åö÷WF6öÖR’2wV&G&–Å÷fÇVP¢e$ôÒW‡W&–ÖVçEö÷WF6öÖW2u$õU%’W‡W&–ÖVçEö–BÂw&÷WöæÖP¢"" ¢  ¦FVb÷VÆ—G•ö6†V6·2†6öææV7F–öã¢GV6¶F"äGV6´D%”6öææV7F–öâÂ'Våö–C¢7G"’ÓâBäFFg&ÖS ¢VW&–W3¢Æ—7E·GWÆU·7G"Â7G"Â7G%ÕÒÒ°¢‚'W6W'5÷W6W%ö–Eöæ÷EöçVÆÂ"Â%4TÄT5B4õTåB‚¢’e$ôÒW6W'2t„U$RW6W%ö–B•2åTÄÂ"Â'fÇVRÒ"’À¢€¢'W6W'5÷W6W%ö–E÷Væ—VR"À¢%4TÄT5B4õTåB‚¢’Ò4õTåB„D•5D”ä5BW6W%ö–B’e$ôÒW6W'2"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…öWfVçEö–E÷Væ—VR"À¢%4TÄT5B4õTåB‚¢’Ò4õTåB„D•5D”ä5BWfVçEö–B’e$ôÒw&÷wF…öWfVçG2"À¢'fÇVRÒ"À¢’À¢€¢&7F—f—G•ögFW%÷6–vçW"À¢%4TÄT5B4õTåB‚¢’e$ôÒW6W%öF–Ç•ö7F—f—G’t„U$R7F—f—G•öFFRÂ6–vçWöFFR"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…öWfVçEögFW%÷6–vçW"À¢%4TÄT5B4õTåB‚¢’e$ôÒw&÷wF…öWfVçG2R¤ô”âW6W'2RU4”är‡W6W%ö–B’t„U$R45B†RæWfVçEöB2DDR’ÂRç6–vçWöFFR"À¢'fÇVRÒ"À¢’À¢€¢'&WFVçF–öåö&÷VæFVB"À¢%4TÄT5B4õTåB‚¢’e$ôÒæWu÷W6W%÷&WFVçF–öât„U$R&WF–æVEöCóu÷v–æF÷räõB”â…E%TRÂdÅ4R’"À¢'fÇVRÒ"À¢’À¢€¢'&Wv&EöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&Å÷&Wv&G2t„U$R–æ6VçF—fUö6÷7BÂ"À¢'fÇVRÒ"À¢’À¢€¢&W‡W&–ÖVçEöw&÷W÷fÆ–B"À¢%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEö76–væÖVçG2t„U$Rw&÷WöæÖRäõB”â‚v6öçG&öÂrÂwG&VFÖVçBr’"À¢'fÇVRÒ"À¢’À¢€¢&W‡W&–ÖVçE÷6–ævÆUö76–væÖVçB"À¢%4TÄT5B4õTåB‚¢’e$ôÒ…4TÄT5BW‡W&–ÖVçEö–BÇW6W%ö–BÄ4õTåB‚¢’âe$ôÒW‡W&–ÖVçEö76–væÖVçG2u$õU%’Ã"„d”ärãã’"À¢'fÇVRÒ"À¢’À¢€¢&÷WF6öÖUögFW%ö76–væÖVçB"À¢%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEö÷WF6öÖW2ò¤ô”âW‡W&–ÖVçEö76–væÖVçG2U4”är†W‡W&–ÖVçEö–BÇW6W%ö–BÆw&÷WöæÖR’t„U$Ròæö'6W'fVEöBÂæ76–væVEöB"À¢'fÇVRÒ"À¢’À¢€¢&gVææVÅöÖöæ÷Föæ–2"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&ÅögVææVÅöF–Ç’t„U$RäõB†W‡÷7W&U÷WbãÒvUö6Æ–6µ÷WbäBvUö6Æ–6µ÷WbãÒ–çf—FUö6Æ–6µ÷WbäB–çf—FUö6Æ–6µ÷WbãÒ6†&U÷7V66W75÷WbäB6†&U÷7V66W75÷WbãÒæWu÷W6W%öÆæF–æu÷WbäBæWu÷W6W%öÆæF–æu÷WbãÒæWu÷W6W%÷&Vv—7FW%÷WbäBæWu÷W6W%÷&Vv—7FW%÷WbãÒæWu÷W6W%ö7F—fFU÷Wb’"À¢'fÇVRÒ"À¢’À¢€¢&7F—f—G•öF•÷&ævR"À¢%4TÄT5B4õTåB‚¢’e$ôÒfVGW&U÷W6vRt„U$R7F—fUöF—5ó3äõB$UEtTTâäB3"À¢'fÇVRÒ"À¢’À¢€¢&fVGW&Uö6÷VçEöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒfVGW&U÷W6vRt„U$RfVGW&U÷W6Uö6÷VçBÂ"À¢'fÇVRÒ"À¢’À¢€¢&7V—&VEö6÷7EöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒ7V—&VE÷W6W'2t„U$R–æ6VçF—fUö6÷7BÂ"À¢'fÇVRÒ"À¢’À¢€¢&ÖWG&–5öFVf–æ—F–öç5÷&W6VçB"À¢%4TÄT5B44Rt„Tâ4õTåB‚¢’ãÒD„TâTÅ4RTäBe$ôÒÖWG&–5öFVf–æ—F–öç2"À¢'fÇVRÒ"À¢’À¢€¢'W&–öG5÷&W6VçB"À¢%4TÄT5B44Rt„Tâ4õTåB„D•5D”ä5BW&–öB’Ò"D„TâTÅ4RTäBe$ôÒæWu÷W6W%÷&WFVçF–öâ"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…÷G&VæEö6ö×ÆWFR"À¢%4TÄT5B44Rt„Tâ4õTåB‚¢’Ò“äBÔ”â†FUö–æFW‚’âäBÔ”â‡F&vWEö–æFW‚’âD„TâTÅ4RTäBe$ôÒw&÷wF…öF–Ç’"À¢'fÇVRÒ"À¢’À¢Ğ¢æ÷rÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢&÷w2ÒµĞ¢f÷"æÖRÂVW'’ÂF‡&W6†öÆB–âVW&–W3 ¢fÇVRÒfÆöB†6öææV7F–öâæW†V7WFR‡VW'’’æfWF6†öæR‚•³Ò¢&÷w2æVæB€¢°¢''Våö–B#¢'Våö–BÀ¢&6†V6¶VEöB#¢æ÷rÀ¢&6†V6µöæÖR#¢æÖRÀ¢'7FGW2#¢'72"–bfÇVRÓÒVÇ6R&f–Â"À¢&ö'6W'fVE÷fÇVR#¢fÇVRÀ¢'F‡&W6†öÆB#¢F‡&W6†öÆBÀ¢&FWF–Ç2#¢$FWFW&Ö–æ—7F–2V&Æ–2ÖFVÖòfÆ–FF–öâ"À¢Ğ¢¢&WGW&âBäFFg&ÖR‡&÷w2  ¦FVbvVæW&FUöFF&6R€¢F%÷Fƒ¢F‚Â¢ÂW6W'3¢–çBÂ6VVC¢–çBÂf÷&6S¢&ööÂÒfÇ6P¢’ÓâF–7E·7G"Âç•Ó ¢–bW6W'2Â%ó ¢&—6RfÇVTW'&÷"‚'W6W'2×W7B&RBÆV7B"Ãf÷"ÖVæ–ævgVÂFVÖò6VvÖVçG2"¢F%÷F‚ç&VçBæÖ¶F—"‡&VçG3ÕG'VRÂW†—7Eöö³ÕG'VR¢–bF%÷F‚æW†—7G2‚’æBæ÷Bf÷&6S ¢&—6Rf–ÆTW†—7G4W'&÷"†b$FF&6RÇ&VG’W†—7G3¢¶F%÷F‡ÒâW6RÒÖf÷&6RFò&WÆ6R—Bâ"¢–bF%÷F‚æW†—7G2‚“ ¢F%÷F‚çVæÆ–æ²‚¢&ærÒçç&æFöÒæFVfVÇE÷&ær‡6VVB¢'Våö–BÒ7G"‡WV–BçWV–CB‚’¢7F'FVBÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢g&ÖW3¢F–7E·7G"ÂBäFFg&ÖUÒÒ·Ğ¢g&ÖW5²'W6W'2%ÒÒvVæW&FU÷W6W'2‡&ærÂW6W'2¢g&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%ÒÂg&ÖW5²&fVGW&U÷W6vR%ÒÒvVæW&FU÷&WFVçF–öâ‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW5²&æWu÷W6W%ögVææVÂ%ÒÂæWu÷W6W%öWfVçG2ÒvVæW&FUöæWu÷W6W%ögVææVÂ€¢&ærÂg&ÖW5²'W6W'2%ÒÂg&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%Ğ¢¢&VfW'&Åög&ÖW2ÒvVæW&FU÷&VfW'&Â‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW2çWFFR‡&VfW'&Åög&ÖW2¢g&ÖW5²&w&÷wF…öWfVçG2%ÒÒBæ6öæ6B€¢¶g&ÖW5²&w&÷wF…öWfVçG2%ÒÂæWu÷W6W%öWfVçG5ÒÂ–væ÷&Uö–æFWƒÕG'VP¢¢€¢g&ÖW5²&W‡W&–ÖVçEö76–væÖVçG2%ÒÀ¢g&ÖW5²&W‡W&–ÖVçEö÷WF6öÖW2%ÒÀ¢g&ÖW5²&W‡W&–ÖVçEöFVf–æ—F–öç2%ÒÀ¢’ÒvVæW&FUöW‡W&–ÖVçG2‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW5²'W6W%öF–Ç•ö7F—f—G’%ÒÒö7F—f—G•÷&÷w2‡&ærÂg&ÖW5²'W6W'2%ÒÂg&ÖW5²&fVGW&U÷W6vR%Ò¢g&ÖW5²&ÖWG&–5öFVf–æ—F–öç2%ÒÒBäFFg&ÖR„ÔUE$”5ôDTd”ä•D”ôå2¢g&ÖW5²&w&÷wF…öF–Ç’%ÒÒvVæW&FUöw&÷wF…öF–Ç’‡6VVB ¢6öææV7F–öâÒGV6¶F"æ6öææV7B‡7G"†F%÷F‚’¢G'“ ¢66†VÖ÷F‚Ò$ô¤T5Eõ$ôõBò'7Â"ò'66†VÖ"ò#ö6÷&Rç7Â ¢6öææV7F–öâæW†V7WFR‡66†VÖ÷F‚ç&VE÷FW‡B†Væ6öF–æsÒ'WFbÓ‚"’¢f÷"F&ÆRÂg&ÖR–âg&ÖW2æ—FV×2‚“ ¢÷w&—FUög&ÖR†6öææV7F–öâÂF&ÆRÂg&ÖR¢ö7&VFU÷f–Ww2†6öææV7F–öâ¢VÆ—G’Ò÷VÆ—G•ö6†V6·2†6öææV7F–öâÂ'Våö–B¢÷w&—FUög&ÖR†6öææV7F–öâÂ&FF÷VÆ—G•÷'Vç2"ÂVÆ—G’¢6ö×ÆWFVBÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢–ævW7F–öâÒBäFFg&ÖR€¢°¢°¢''Våö–B#¢'Våö–BÀ¢'6÷W&6UöæÖR#¢&FWFW&Ö–æ—7F–5÷7–çF†WF–5÷V&Æ–5öFVÖò"À¢'7F'FVEöB#¢7F'FVBÀ¢&6ö×ÆWFVEöB#¢6ö×ÆWFVBÀ¢'&÷uö6÷VçB#¢7VÒ†ÆVâ†g&ÖR’f÷"g&ÖR–âg&ÖW2çfÇVW2‚’’À¢'6VVB#¢6VVBÀ¢'7FGW2#¢&6ö×ÆWFVB"À¢Ğ¢Ğ¢¢÷w&—FUög&ÖR†6öææV7F–öâÂ&–ævW7F–öå÷'Vç2"Â–ævW7F–öâ¢6öææV7F–öâæW†V7WFR‚$4„T4µô”åB"¢6÷VçG2Ò°¢F&ÆS¢–çB†6öææV7F–öâæW†V7WFR†bu4TÄT5B4õTåB‚¢’e$ôÒ'·F&ÆWÒ"r’æfWF6†öæR‚•³Ò¢f÷"F&ÆR–âg&ÖW0¢Ğ¢VÆ—G•öf–ÆVBÒ–çB‚‡VÆ—G•²'7FGW2%ÒÓÒ&f–Â"’ç7VÒ‚’¢&WGW&â°¢&FF&6R#¢7G"†F%÷F‚’À¢'6VVB#¢6VVBÀ¢'W6W'5÷&WVW7FVB#¢W6W'2À¢'&÷w2#¢6÷VçG2À¢'VÆ—G•ö6†V6·2#¢ÆVâ‡VÆ—G’’À¢'VÆ—G•öf–ÆVB#¢VÆ—G•öf–ÆVBÀ¢''Våö–B#¢'Våö–BÀ¢Ğ¢f–æÆÇ“ ¢6öææV7F–öâæ6Æ÷6R‚  ¦FVb'6Uö&w2‚’Óâ&w'6RäæÖW76S ¢'6W"Ò&w'6Rä&wVÖVçE'6W"€¢FW67&—F–öãÒ$vVæW&FRw&÷wF„Æ"w2&—f7’×6fRFWFW&Ö–æ—7F–2FVÖòFF&6Râ ¢¢'6W"æFEö&wVÖVçB€¢"ÒÖF"×F‚"ÂG—SÕF‚ÂFVfVÇCÕF‚†÷2ævWFVçb‚$u$õuD„Ä%ôD%õD‚"ÂDTdTÅEôD"’¢¢'6W"æFEö&wVÖVçB€¢"Ò×W6W'2"ÂG—SÖ–çBÂFVfVÇCÖ–çB†÷2ævWFVçb‚$u$õuD„Ä%ôDTÔõõU4U%2"Â#"’¢¢'6W"æFEö&wVÖVçB‚"Ò×6VVB"ÂG—SÖ–çBÂFVfVÇCÖ–çB†÷2ævWFVçb‚$u$õuD„Ä%ôDTÔõõ4TTB"Â#C""’’¢'6W"æFEö&wVÖVçB‚"ÒÖf÷&6R"Â7F–öãÒ'7F÷&U÷G'VR"Â†VÇÒ%&WÆ6RâW†—7F–ærFVÖòFF&6Râ"¢&WGW&â'6W"ç'6Uö&w2‚  ¦FVbÖ–â‚’ÓâæöæS ¢&w2Ò'6Uö&w2‚¢&W7VÇBÒvVæW&FUöFF&6R€¢&w2æF%÷F‚ç&W6öÇfR‚’ÂW6W'3Ö&w2çW6W'2Â6VVCÖ&w2ç6VVBÂf÷&6SÖ&w2æf÷&6P¢¢&–çB†§6öâæGV×2‡&W7VÇBÂVç7W&Uö66–“ÔfÇ6RÂ–æFVçCÓ"’  ¦–bõöæÖUõòÓÒ%õöÖ–åõò# ¢Ö–â‚