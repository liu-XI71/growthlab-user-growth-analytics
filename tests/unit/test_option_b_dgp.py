from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.generate_demo_data import (
    _activity_rows,
    _derive_retention_from_activity,
    _value_and_cost_frames,
    generate_retention,
    generate_users,
)


def _arm_frames(group_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    users = generate_users(np.random.default_rng(17), 2_000)
    users["acquisition_source"] = "referral_experiment"
    users["referrer_user_id"] = "common_referrer"
    users["acquisition_campaign"] = "referral_ui_simplification"
    users["acquisition_treatment"] = group_name
    retention, feature = generate_retention(np.random.default_rng(23), users)
    activity = _activity_rows(np.random.default_rng(29), users, feature, retention)
    _derive_retention_from_activity(retention, feature, activity)
    _, costs, acquired = _value_and_cost_frames(np.random.default_rng(31), users, activity, feature)
    return retention, costs, acquired


def test_ui_treatment_does_not_change_post_acquisition_quality_or_value_dgp() -> None:
    control_retention, control_costs, control_acquired = _arm_frames("control")
    treatment_retention, treatment_costs, treatment_acquired = _arm_frames("treatment")

    retention_columns = [
        "retained_d1",
        "retained_d3",
        "retained_d7",
        "retained_d1_7_window",
        "retained_d30",
        "cohort_age_days",
        "mature_d7",
        "mature_d30",
    ]
    pd.testing.assert_frame_equal(
        control_retention[retention_columns],
        treatment_retention[retention_columns],
        check_dtype=True,
    )

    acquired_numeric = [
        "base_incentive",
        "ltv30",
        "service_cost30",
        "product_contribution30",
        "variable_acquisition_cost",
        "contribution30",
        "active_days_30",
        "daily_active_hours",
        "value_per_hour",
    ]
    pd.testing.assert_frame_equal(
        control_acquired[acquired_numeric],
        treatment_acquired[acquired_numeric],
        check_dtype=True,
    )
    pd.testing.assert_series_equal(
        control_costs["amount"], treatment_costs["amount"], check_names=False
    )
    pd.testing.assert_series_equal(
        control_costs["cost_type"], treatment_costs["cost_type"], check_names=False
    )


def test_experimental_cost_schedule_is_arm_invariant() -> None:
    _, control_costs, control_acquired = _arm_frames("control")
    _, treatment_costs, treatment_acquired = _arm_frames("treatment")
    assert control_acquired["base_incentive"].unique().tolist() == [7.5]
    assert treatment_acquired["base_incentive"].unique().tolist() == [7.5]
    for costs in (control_costs, treatment_costs):
        policy = {
            cost_type: set(values)
            for cost_type, values in costs.groupby("cost_type", observed=True)["amount"]
        }
        assert policy["incentive"] == {7.5}
        assert policy["delivery_and_operations"] == {0.48}
        assert policy["invalid_reward_loss"] <= {0.0, 0.42}
