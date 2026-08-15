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
from scripts.portfolio_v2_data import portfolio_v2_frames

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
            "activated_date": activated["exposure_date"].to_numpy(),×]»âÚ$z{-®éÜj×'WF–öã3’26öçG&–'WF–öã3 ¢e$ôÒÖ'EöW‡W&–ÖVçE÷W6W%÷fÇVP¢u$õU%’Ã ¢"" ¢  ¦FVb÷VÆ—G•ö6†V6·2†6öææV7F–öã¢GV6¶F"äGV6´D%”6öææV7F–öâÂ'Våö–C¢7G"’ÓâBäFFg&ÖS ¢VW&–W3¢Æ—7E·GWÆU·7G"Â7G"Â7G%ÕÒÒ°¢‚'W6W'5÷W6W%ö–Eöæ÷EöçVÆÂ"Â%4TÄT5B4õTåB‚¢’e$ôÒW6W'2t„U$RW6W%ö–B•2åTÄÂ"Â'fÇVRÒ"’À¢€¢'W6W'5÷W6W%ö–E÷Væ—VR"À¢%4TÄT5B4õTåB‚¢’Ò4õTåB„D•5D”ä5BW6W%ö–B’e$ôÒW6W'2"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…öWfVçEö–E÷Væ—VR"À¢%4TÄT5B4õTåB‚¢’Ò4õTåB„D•5D”ä5BWfVçEö–B’e$ôÒw&÷wF…öWfVçG2"À¢'fÇVRÒ"À¢’À¢€¢&7F—f—G•ögFW%÷6–vçW"À¢%4TÄT5B4õTåB‚¢’e$ôÒW6W%öF–Ç•ö7F—f—G’t„U$R7F—f—G•öFFRÂ6–vçWöFFR"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…öWfVçEögFW%÷6–vçW"À¢%4TÄT5B4õTåB‚¢’e$ôÒw&÷wF…öWfVçG2R¤ô”âW6W'2RU4”är‡W6W%ö–B’t„U$R45B†RæWfVçEöB2DDR’ÂRç6–vçWöFFR"À¢'fÇVRÒ"À¢’À¢€¢'&WFVçF–öåö&÷VæFVB"À¢%4TÄT5B4õTåB‚¢’e$ôÒæWu÷W6W%÷&WFVçF–öât„U$R&WF–æVEöCóu÷v–æF÷räõB”â…E%TRÂdÅ4R’"À¢'fÇVRÒ"À¢’À¢€¢'&Wv&EöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&Å÷&Wv&G2t„U$R–æ6VçF—fUö6÷7BÂ"À¢'fÇVRÒ"À¢’À¢€¢&W‡W&–ÖVçEöw&÷W÷fÆ–B"À¢%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEö76–væÖVçG2t„U$Rw&÷WöæÖRäõB”â‚v6öçG&öÂrÂwG&VFÖVçBr’"À¢'fÇVRÒ"À¢’À¢€¢&W‡W&–ÖVçE÷6–ævÆUö76–væÖVçB"À¢%4TÄT5B4õTåB‚¢’e$ôÒ…4TÄT5BW‡W&–ÖVçEö–BÇW6W%ö–BÄ4õTåB‚¢’âe$ôÒW‡W&–ÖVçEö76–væÖVçG2u$õU%’Ã"„d”ärãã’"À¢'fÇVRÒ"À¢’À¢€¢&÷WF6öÖUögFW%ö76–væÖVçB"À¢%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEö÷WF6öÖW2ò¤ô”âW‡W&–ÖVçEö76–væÖVçG2U4”är†W‡W&–ÖVçEö–BÇW6W%ö–BÆw&÷WöæÖR’t„U$Ròæö'6W'fVEöBÂæ76–væVEöB"À¢'fÇVRÒ"À¢’À¢€¢&gVææVÅöÖöæ÷Föæ–2"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&ÅögVææVÅöF–Ç’t„U$RäõB†W‡÷7W&U÷WbãÒvUö6Æ–6µ÷WbäBvUö6Æ–6µ÷WbãÒ–çf—FUö6Æ–6µ÷WbäB–çf—FUö6Æ–6µ÷WbãÒ6†&U÷7V66W75÷WbäB6†&U÷7V66W75÷WbãÒæWu÷W6W%öÆæF–æu÷WbäBæWu÷W6W%öÆæF–æu÷WbãÒæWu÷W6W%÷&Vv—7FW%÷WbäBæWu÷W6W%÷&Vv—7FW%÷WbãÒæWu÷W6W%ö7F—fFU÷Wb’"À¢'fÇVRÒ"À¢’À¢€¢&7F—f—G•öF•÷&ævR"À¢%4TÄT5B4õTåB‚¢’e$ôÒfVGW&U÷W6vRt„U$R7F—fUöF—5ó3äõB$UEtTTâäB3"À¢'fÇVRÒ"À¢’À¢€¢&fVGW&Uö6÷VçEöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒfVGW&U÷W6vRt„U$RfVGW&U÷W6Uö6÷VçBÂ"À¢'fÇVRÒ"À¢’À¢€¢&7V—&VEö6÷7EöæöææVvF—fR"À¢%4TÄT5B4õTåB‚¢’e$ôÒ7V—&VE÷W6W'2t„U$R–æ6VçF—fUö6÷7BÂ"À¢'fÇVRÒ"À¢’À¢€¢&ÖWG&–5öFVf–æ—F–öç5÷&W6VçB"À¢%4TÄT5B44Rt„Tâ4õTåB‚¢’ãÒD„TâTÅ4RTäBe$ôÒÖWG&–5öFVf–æ—F–öç2"À¢'fÇVRÒ"À¢’À¢€¢'W&–öG5÷&W6VçB"À¢%4TÄT5B44Rt„Tâ4õTåB„D•5D”ä5BW&–öB’Ò"D„TâTÅ4RTäBe$ôÒæWu÷W6W%÷&WFVçF–öâ"À¢'fÇVRÒ"À¢’À¢€¢&w&÷wF…÷G&VæEö6ö×ÆWFR"À¢%4TÄT5B44Rt„Tâ4õTåB‚¢’Ò“äBÔ”â†FUö–æFW‚’âäBÔ”â‡F&vWEö–æFW‚’âD„TâTÅ4RTäBe$ôÒw&÷wF…öF–Ç’"À¢'fÇVRÒ"À¢’À¢€¢'&VfW'&ÅöVFvUö–çf—FW%öf²"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&ÅöVFvW2RÄTeB¤ô”âW6W'2RôâRæ–çf—FW%÷W6W%ö–C×RçW6W%ö–Bt„U$RRçW6W%ö–B•2åTÄÂ"À¢'fÇVRÒ"À¢’À¢€¢'&VfW'&ÅöVFvUö–çf—FVUöf²"À¢%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&ÅöVFvW2RÄTeB¤ô”âW6W'2RôâRææWu÷W6W%ö–C×RçW6W%ö–Bt„U$RRçW6W%ö–B•2åTÄÂ"À¢'fÇVRÒ"À¢’À¢€¢'&VfW'&Åö–çf—FVUö†5ö7F—f—G•÷fÇVUö6÷7B"À¢""%4TÄT5B4õTåB‚¢’e$ôÒ&VfW'&ÅöVFvW2P¢t„U$RäõBU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’t„U$RçW6W%ö–CÖRææWu÷W6W%ö–B¢õ"äõBU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•÷fÇVRbt„U$RbçW6W%ö–CÖRææWu÷W6W%ö–B¢õ"äõBU„•5E2…4TÄT5Be$ôÒ6÷7EöWfVçG22t„U$R2çW6W%ö–CÖRææWu÷W6W%ö–B’"""À¢'fÇVRÒ"À¢’À¢€¢&W‡÷7W&UögFW%ö76–væÖVçB"À¢""%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEöW‡÷7W&W2P¢¤ô”âW‡W&–ÖVçEö76–væÖVçG2U4”är†W‡W&–ÖVçEö–BÇW6W%ö–BÆw&÷WöæÖR¢t„U$RRçv5öW‡÷6VBäBRæW‡÷6VEöBÂæ76–væVEöB"""À¢'fÇVRÒ"À¢’À¢€¢'&WFVçF–öåöW†7EöF•ö7F—f—G•ö6öç6—7FVçB"À¢""%4TÄT5B4õTåB‚¢’e$ôÒæWu÷W6W%÷&WFVçF–öâ"t„U$P¢&WF–æVEöCÃâU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’t„U$RçW6W%ö–C×"çW6W%ö–BäBç&VÆF—fUöF“Ó¢õ"&WF–æVEöC2ÃâU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’t„U$RçW6W%ö–C×"çW6W%ö–BäBç&VÆF—fUöF“Ó2¢õ"&WF–æVEöCrÃâU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’t„U$RçW6W%ö–C×"çW6W%ö–BäBç&VÆF—fUöF“Ór¢õ"†ÖGW&UöC3äB&WF–æVEöC3ÃâU„•5E2…4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’t„U$RçW6W%ö–C×"çW6W%ö–BäBç&VÆF—fUöF“Ó3’¢õ"„äõBÖGW&UöC3äB&WF–æVEöC3•2äõBåTÄÂ’"""À¢'fÇVRÒ"À¢’À¢€¢'&WFVçF–öå÷v–æF÷uö7F—f—G•ö6öç6—7FVçB"À¢""%4TÄT5B4õTåB‚¢’e$ôÒæWu÷W6W%÷&WFVçF–öâ"t„U$P¢&WF–æVEöCóu÷v–æF÷rÃâU„•5E2€¢4TÄT5Be$ôÒW6W%öF–Ç•ö7F—f—G’¢t„U$RçW6W%ö–C×"çW6W%ö–BäBç&VÆF—fUöF’$UEtTTâäBp¢’"""À¢'fÇVRÒ"À¢’À¢€¢&W‡W&–ÖVçE÷&VfW'&Åö÷WF6öÖUö6öç6—7FVçB"À¢""%4TÄT5B4õTåB‚¢’e$ôÒW‡W&–ÖVçEö÷WF6öÖW2ð¢¤ô”âæWu÷W6W%÷&WFVçF–öâ"ôâòææWu÷W6W%ö–C×"çW6W%ö–@¢t„U$RòæW‡W&–ÖVçEö–CÒw&VfW'&Å÷V•÷6–×Æ–f–6F–öâp¢äB†òç&WF–æVEöCrÃâ"ç&WF–æVEöCp¢õ"òç&WF–æVEöCóu÷v–æF÷rÃâ"ç&WF–æVEöCóu÷v–æF÷r’"""À¢'fÇVRÒ"À¢’À¢€¢&6öçG&–'WF–öã3ö–FVçF—G’"À¢""%4TÄT5B4õTåB‚¢’e$ôÒ7V—&VE÷W6W'0¢t„U$R%2†6öçG&–'WF–öã3Ò†ÇGc3×6W'f–6Uö6÷7C3×f&–&ÆUö7V—6—F–öåö6÷7B’’âRÓ’"""À¢'fÇVRÒ"À¢’À¢€¢'fÇVS3÷v–æF÷uööfg6WG5óó#’"À¢%4TÄT5B4õTåB‚¢’e$ôÒW6W%öF–Ç•÷fÇVRt„U$R&VÆF—fUöF’äõB$UEtTTâäB#’"À¢'fÇVRÒ"À¢’À¢€¢&FV6—6–öåöÆöu÷&W6VçB"À¢%4TÄT5B44Rt„Tâ4õTåB‚¢’ãÒ"D„TâTÅ4RTäBe$ôÒFV6—6–öåöÆör"À¢'fÇVRÒ"À¢’À¢€¢'V•öW‡W&–ÖVçEö6÷7E÷öÆ–7•öWVÂ"À¢""%4TÄT5B44Rt„Tâ4õTåB„D•5D”ä5B$õTäB†&6Uö–æ6VçF—fRÃ‚’“ÓD„TâTÅ4RTä@¢e$ôÒ7V—&VE÷W6W'2t„U$R7V—6—F–öå÷6÷W&6SÒw&VfW'&ÅöW‡W&–ÖVçBr"""À¢'fÇVRÒ"À¢’À¢€¢'V•öW‡W&–ÖVçEöFw÷öÆ–7•÷&W6VçB"À¢""%4TÄT5B44Rt„Tâ4õTåB‚¢“ÓD„TâTÅ4RTäBe$ôÒFw÷öÆ–7¢t„U$RW‡W&–ÖVçEö–CÒw&VfW'&Å÷V•÷6–×Æ–f–6F–öâp¢äBF÷vç7G&VÕ÷VÆ—G•÷öÆ–7’Ä”´Rv–FVçF–6ÂRp¢äB6÷7E÷öÆ–7’Ä”´Rv–FVçF–6ÂRr"""À¢'fÇVRÒ"À¢’À¢Ð¢æ÷rÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢&÷w2ÒµÐ¢f÷"æÖRÂVW'’ÂF‡&W6†öÆB–âVW&–W3 ¢fÇVRÒfÆöB†6öææV7F–öâæW†V7WFR‡VW'’’æfWF6†öæR‚•³Ò¢&÷w2æVæB€¢°¢''Våö–B#¢'Våö–BÀ¢&6†V6¶VEöB#¢æ÷rÀ¢&6†V6µöæÖR#¢æÖRÀ¢'7FGW2#¢'72"–bfÇVRÓÒVÇ6R&f–Â"À¢&ö'6W'fVE÷fÇVR#¢fÇVRÀ¢'F‡&W6†öÆB#¢F‡&W6†öÆBÀ¢&FWF–Ç2#¢$FWFW&Ö–æ—7F–2V&Æ–2ÖFVÖòfÆ–FF–öâ"À¢Ð¢¢&WGW&âBäFFg&ÖR‡&÷w2  ¦FVbvVæW&FUöFF&6R€¢F%÷Fƒ¢F‚Â¢ÂW6W'3¢–çBÂ6VVC¢–çBÂf÷&6S¢&ööÂÒfÇ6P¢’ÓâF–7E·7G"Âç•Ó ¢–bW6W'2Â%ó ¢&—6RfÇVTW'&÷"‚'W6W'2×W7B&RBÆV7B"Ãf÷"ÖVæ–ævgVÂFVÖò6VvÖVçG2"¢F%÷F‚ç&VçBæÖ¶F—"‡&VçG3ÕG'VRÂW†—7Eöö³ÕG'VR¢–bF%÷F‚æW†—7G2‚’æBæ÷Bf÷&6S ¢&—6Rf–ÆTW†—7G4W'&÷"†b$FF&6RÇ&VG’W†—7G3¢¶F%÷F‡ÒâW6RÒÖf÷&6RFò&WÆ6R—Bâ"¢–bF%÷F‚æW†—7G2‚“ ¢F%÷F‚çVæÆ–æ²‚¢&ærÒçç&æFöÒæFVfVÇE÷&ær‡6VVB¢'Våö–BÒ7G"‡WV–BçWV–CB‚’¢7F'FVBÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢g&ÖW3¢F–7E·7G"ÂBäFFg&ÖUÒÒ·Ð¢g&ÖW5²'W6W'2%ÒÒvVæW&FU÷W6W'2‡&ærÂW6W'2¢&VfW'&Åög&ÖW2ÒvVæW&FU÷&VfW'&Â‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW2çWFFR‡&VfW'&Åög&ÖW2¢€¢g&ÖW5²&W‡W&–ÖVçEö76–væÖVçG2%ÒÀ¢g&ÖW5²&W‡W&–ÖVçEöW‡÷7W&W2%ÒÀ¢g&ÖW5²&W‡W&–ÖVçEö÷WF6öÖW2%ÒÀ¢g&ÖW5²&W‡W&–ÖVçEöFVf–æ—F–öç2%ÒÀ¢W‡W&–ÖVçEöVFvW2À¢’ÒvVæW&FUöW‡W&–ÖVçG2‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW5²'&VfW'&ÅöVFvW2%ÒÒBæ6öæ6B€¢¶g&ÖW5²'&VfW'&ÅöVFvW2%ÒÂW‡W&–ÖVçEöVFvW5ÒÂ–væ÷&Uö–æFWƒÕG'VP¢¢g&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%ÒÂg&ÖW5²&fVGW&U÷W6vR%ÒÒvVæW&FU÷&WFVçF–öâ‡&ærÂg&ÖW5²'W6W'2%Ò¢g&ÖW5²'W6W%öF–Ç•ö7F—f—G’%ÒÒö7F—f—G•÷&÷w2€¢&ærÀ¢g&ÖW5²'W6W'2%ÒÀ¢g&ÖW5²&fVGW&U÷W6vR%ÒÀ¢g&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%ÒÀ¢¢öFW&—fU÷&WFVçF–öåög&öÕö7F—f—G’€¢g&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%ÒÀ¢g&ÖW5²&fVGW&U÷W6vR%ÒÀ¢g&ÖW5²'W6W%öF–Ç•ö7F—f—G’%ÒÀ¢¢g&ÖW5²&æWu÷W6W%ögVææVÂ%ÒÂæWu÷W6W%öWfVçG2ÒvVæW&FUöæWu÷W6W%ögVææVÂ€¢&ærÂg&ÖW5²'W6W'2%ÒÂg&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%Ð¢¢W‡W&–ÖVçEö7F—fF–öåöWfVçG2ÒW‡W&–ÖVçEöVFvW2ç&VæÖR€¢6öÇVÖç3×°¢&æWu÷W6W%ö–B#¢'W6W%ö–B"À¢&7F—fFVEöFFR#¢&WfVçEöB"À¢'fW'6–öâ#¢&6×–vå÷fW'6–öâ"À¢Ð¢¢–bæ÷BW‡W&–ÖVçEö7F—fF–öåöWfVçG2æV×G“ ¢W‡W&–ÖVçEö7F—fF–öåöWfVçG2ÒW‡W&–ÖVçEö7F—fF–öåöWfVçG2æ76–vâ€¢WfVçEö–CÖÆÖ&Fg&ÖS¢&W‡öæWuö7F—fFUò"²g&ÖU²'W6W%ö–B%Òæ7G—R‡7G"’À¢WfVçEöæÖSÒ&æWu÷W6W%ö7F—fFR"À¢WfVçEöCÖÆÖ&Fg&ÖS¢BçFõöFFWF–ÖR†g&ÖU²&WfVçEöB%Ò’À¢W&–öCÒ'&VfW'&ÅöW‡W&–ÖVçB"À¢•µ²&WfVçEö–B"Â'W6W%ö–B"Â&WfVçEöæÖR"Â&WfVçEöB"Â'W&–öB"Â&6×–vå÷fW'6–öâ%ÕÐ¢VÇ6S ¢W‡W&–ÖVçEö7F—fF–öåöWfVçG2ÒBäFFg&ÖR€¢6öÇVÖç3Õ²&WfVçEö–B"Â'W6W%ö–B"Â&WfVçEöæÖR"Â&WfVçEöB"Â'W&–öB"Â&6×–vå÷fW'6–öâ%Ð¢¢g&ÖW5²&w&÷wF…öWfVçG2%ÒÒBæ6öæ6B€¢¶g&ÖW5²&w&÷wF…öWfVçG2%ÒÂæWu÷W6W%öWfVçG2ÂW‡W&–ÖVçEö7F—fF–öåöWfVçG5ÒÀ¢–væ÷&Uö–æFWƒÕG'VRÀ¢¢€¢g&ÖW5²'W6W%öF–Ç•÷fÇVR%ÒÀ¢g&ÖW5²&6÷7EöWfVçG2%ÒÀ¢g&ÖW5²&7V—&VE÷W6W'2%ÒÀ¢’Ò÷fÇVUöæEö6÷7Eög&ÖW2€¢&ærÀ¢g&ÖW5²'W6W'2%ÒÀ¢g&ÖW5²'W6W%öF–Ç•ö7F—f—G’%ÒÀ¢g&ÖW5²&fVGW&U÷W6vR%ÒÀ¢¢g&ÖW5²&W‡W&–ÖVçEö÷WF6öÖW2%ÒÒöf–æÆ—¦UöW‡W&–ÖVçEö÷WF6öÖW2€¢g&ÖW5²&W‡W&–ÖVçEö÷WF6öÖW2%ÒÀ¢g&ÖW5²&æWu÷W6W%÷&WFVçF–öâ%ÒÀ¢g&ÖW5²&7V—&VE÷W6W'2%ÒÀ¢¢g&ÖW5²&ÖWG&–5öFVf–æ—F–öç2%ÒÒBäFFg&ÖR„ÔUE$”5ôDTd”ä•D”ôå2¢g&ÖW5²&w&÷wF…öF–Ç’%ÒÒvVæW&FUöw&÷wF…öF–Ç’‡6VVB¢g&ÖW5²&FV6—6–öåöÆör%ÒÒöFV6—6–öåöÆör‚¢g&ÖW5²&æÇ—6—5÷6æ6†÷B%ÒÒBäFFg&ÖR€¢°¢°¢'6æ6†÷Eö–B#¢'V&Æ–5öFVÖõ÷c""À¢&5ööeöFFR#¢äÅ•4•5ô5ôôeôDDRæFFR‚’À¢'&–Ö'•öW‡W&–ÖVçEö†÷&—¦öåöF—2#¢BÀ¢'fÇVUöföÆÆ÷wWöF—2#¢3À¢&FW67&—F–öâ#¢$FWFW&Ö–æ—7F–2&—f7’×6fRV&Æ–2÷'FföÆ–ò6æ6†÷B"À¢Ð¢Ð¢¢g&ÖW5²&Fw÷öÆ–7’%ÒÒBäFFg&ÖR€¢°¢°¢'öÆ–7•ö–B#¢'&VfW'&Å÷V•÷6–ævÆU÷G&VFÖVçE÷F‚"À¢&W‡W&–ÖVçEö–B#¢'&VfW'&Å÷V•÷6–×Æ–f–6F–öâ"À¢'G&VFÖVçE÷F‚#¢&76–væÖVçB(i"G&6¶VBW‡÷7W&R(i"–çf—FR6Æ–6²(i"&VfW'&VB7F—fF–öâ"À¢&F÷vç7G&VÕ÷VÆ—G•÷öÆ–7’#¢&–FVçF–6Â&WFVçF–öâÂ7F—f—G’æBfÇVRDu7&÷72&×2"À¢&6÷7E÷öÆ–7’#¢&–FVçF–6Â–æ6VçF—fRæBf&–&ÆR6÷7B66†VGVÆR7&÷72&×2"À¢&¶æ÷vå÷G'WF‚#¢'G&VFÖVçB–æ7&V6W2–çf—FRÖ6Æ–6²æB7F—fF–öâ&ö&&–Æ—G’öæÇ’"À¢&6Æ–Õö&÷VæF'’#¢&æWGv÷&²–çFW&fW&Væ6R—2æ÷B6–×VÆFVBv’æB&VÖ–ç2&—6²"À¢Ð¢Ð¢¢g&ÖW2çWFFR‡÷'FföÆ–õ÷c%ög&ÖW2‚’ ¢6öææV7F–öâÒGV6¶F"æ6öææV7B‡7G"†F%÷F‚’¢G'“ ¢66†VÖ÷F‚Ò$ô¤T5Eõ$ôõBò'7Â"ò'66†VÖ"ò#ö6÷&Rç7Â ¢6öææV7F–öâæW†V7WFR‡66†VÖ÷F‚ç&VE÷FW‡B†Væ6öF–æsÒ'WFbÓ‚"’¢f÷"F&ÆRÂg&ÖR–âg&ÖW2æ—FV×2‚“ ¢÷w&—FUög&ÖR†6öææV7F–öâÂF&ÆRÂg&ÖR¢ö7&VFU÷f–Ww2†6öææV7F–öâ¢VÆ—G’Ò÷VÆ—G•ö6†V6·2†6öææV7F–öâÂ'Våö–B¢÷w&—FUög&ÖR†6öææV7F–öâÂ&FF÷VÆ—G•÷'Vç2"ÂVÆ—G’¢6ö×ÆWFVBÒFFWF–ÖRææ÷r‡F–ÖW¦öæRçWF2’ç&WÆ6R‡G¦–æfóÔæöæR¢–ævW7F–öâÒBäFFg&ÖR€¢°¢°¢''Våö–B#¢'Våö–BÀ¢'6÷W&6UöæÖR#¢&FWFW&Ö–æ—7F–5÷7–çF†WF–5÷V&Æ–5öFVÖò"À¢'7F'FVEöB#¢7F'FVBÀ¢&6ö×ÆWFVEöB#¢6ö×ÆWFVBÀ¢'&÷uö6÷VçB#¢7VÒ†ÆVâ†g&ÖR’f÷"g&ÖR–âg&ÖW2çfÇVW2‚’’À¢'6VVB#¢6VVBÀ¢'7FGW2#¢&6ö×ÆWFVB"À¢Ð¢Ð¢¢÷w&—FUög&ÖR†6öææV7F–öâÂ&–ævW7F–öå÷'Vç2"Â–ævW7F–öâ¢6öææV7F–öâæW†V7WFR‚$4„T4µô”åB"¢6÷VçG2Ò°¢F&ÆS¢–çB†6öææV7F–öâæW†V7WFR†bu4TÄT5B4õTåB‚¢’e$ôÒ'·F&ÆWÒ"r’æfWF6†öæR‚•³Ò¢f÷"F&ÆR–âg&ÖW0¢Ð¢VÆ—G•öf–ÆVBÒ–çB‚‡VÆ—G•²'7FGW2%ÒÓÒ&f–Â"’ç7VÒ‚’¢&WGW&â°¢&FF&6R#¢7G"†F%÷F‚’À¢'6VVB#¢6VVBÀ¢'W6W'5÷&WVW7FVB#¢W6W'2À¢'&÷w2#¢6÷VçG2À¢'VÆ—G•ö6†V6·2#¢ÆVâ‡VÆ—G’’À¢'VÆ—G•öf–ÆVB#¢VÆ—G•öf–ÆVBÀ¢''Våö–B#¢'Våö–BÀ¢Ð¢f–æÆÇ“ ¢6öææV7F–öâæ6Æ÷6R‚  ¦FVb'6Uö&w2‚’Óâ&w'6RäæÖW76S ¢'6W"Ò&w'6Rä&wVÖVçE'6W"€¢FW67&—F–öãÒ$vVæW&FRw&÷wF„Æ"w2&—f7’×6fRFWFW&Ö–æ—7F–2FVÖòFF&6Râ ¢¢'6W"æFEö&wVÖVçB€¢"ÒÖF"×F‚"ÂG—SÕF‚ÂFVfVÇCÕF‚†÷2ævWFVçb‚$u$õuD„Ä%ôD%õD‚"ÂDTdTÅEôD"’¢¢'6W"æFEö&wVÖVçB€¢"Ò×W6W'2"ÂG—SÖ–çBÂFVfVÇCÖ–çB†÷2ævWFVçb‚$u$õuD„Ä%ôDTÔõõU4U%2"Â#"’¢¢'6W"æFEö&wVÖVçB‚"Ò×6VVB"ÂG—SÖ–çBÂFVfVÇCÖ–çB†÷2ævWFVçb‚$u$õuD„Ä%ôDTÔõõ4TTB"Â#C""’’¢'6W"æFEö&wVÖVçB‚"ÒÖf÷&6R"Â7F–öãÒ'7F÷&U÷G'VR"Â†VÇÒ%&WÆ6RâW†—7F–ærFVÖòFF&6Râ"¢&WGW&â'6W"ç'6Uö&w2‚  ¦FVbÖ–â‚’ÓâæöæS ¢&w2Ò'6Uö&w2‚¢&W7VÇBÒvVæW&FUöFF&6R€¢&w2æF%÷F‚ç&W6öÇfR‚’ÂW6W'3Ö&w2çW6W'2Â6VVCÖ&w2ç6VVBÂf÷&6SÖ&w2æf÷&6P¢¢&–çB†§6öâæGV×2‡&W7VÇBÂVç7W&Uö66–“ÔfÇ6RÂ–æFVçCÓ"’  ¦–bõöæÖUõòÓÒ%õöÖ–åõò# ¢Ö–â‚