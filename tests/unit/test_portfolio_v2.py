from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.export_portfolio_v2 import build_bundle, export_bundle
from scripts.portfolio_v2_data import portfolio_v2_frames


def test_portfolio_frames_freeze_two_case_business_contract() -> None:
    frames = portfolio_v2_frames()
    cases = frames["portfolio_case_registry"]
    assert cases["case_id"].tolist() == ["referral_growth", "new_user_retention"]
    assert set(frames) == {
        "portfolio_case_registry",
        "portfolio_business_kpis",
        "portfolio_decision_loop",
        "portfolio_referral_versions",
        "portfolio_referral_funnel",
        "portfolio_retention_trend",
        "portfolio_retention_segments",
        "portfolio_retention_path",
        "portfolio_benchmark_features",
        "portfolio_experiments",
        "portfolio_metric_contracts",
        "portfolio_decisions",
    }


def test_portfolio_key_claims_match_disclosed_narrative() -> None:
    frames = portfolio_v2_frames()
    experiments = frames["portfolio_experiments"].set_index("case_id")
    referral = experiments.loc["referral_growth"]
    assert referral["baseline_rate"] == pytest.approx(0.17)
    assert referral["treatment_rate"] == pytest.approx(0.235)
    assert referral["absolute_lift_pp"] == pytest.approx(6.5)
    assert pd.isna(referral["sample_size"])
    assert referral["sample_display"] == "百万级脱敏样本"
    assert referral["duration_days"] == 14
    retention = experiments.loc["new_user_retention"]
    assert retention["sample_size"] == 300_000
    assert retention["sample_display"] == "约30万样本"
    assert retention["duration_days"] == 14
    assert retention["significance"] == "p < 0.05"
    assert retention["baseline_rate"] != retention["baseline_rate"]
    assert retention["absolute_lift_pp"] != retention["absolute_lift_pp"]


def test_retention_metric_is_window_not_exact_d7() -> None:
    metrics = portfolio_v2_frames()["portfolio_metric_contracts"].set_index("metric_key")
    definition = metrics.loc["d1_7_window_retention"]
    assert "第1至7天" in definition["numerator"]
    assert "不等于精确第7日" in definition["boundary"]


def test_referral_economics_uses_ltv_cac_not_fake_roi() -> None:
    frames = portfolio_v2_frames()
    latest = frames["portfolio_referral_versions"].query("version_id == 'simplified_ui'").iloc[0]
    assert latest["ltv_cac"] == pytest.approx(2.18)
    contract = frames["portfolio_metric_contracts"].query("metric_key == 'month1_ltv_cac'").iloc[0]
    assert "不是净ROI" in contract["boundary"]


def test_static_bundle_is_strict_json_without_nan(tmp_path) -> None:
    output = export_bundle(tmp_path / "portfolio.json")
    raw = output.read_text(encoding="utf-8")
    assert "NaN" not in raw
    parsed = json.loads(raw)
    assert parsed == build_bundle()
    retention = parsed["retention"]["experiment"]
    assert retention["absolute_lift_pp"] is None


def test_every_decision_has_full_reasoning_chain() -> None:
    decisions = portfolio_v2_frames()["portfolio_decisions"]
    required = ["fact", "interpretation", "hypothesis", "action", "decision", "limitation"]
    assert decisions[required].notna().all().all()
    assert (decisions[required].map(len) > 8).all().all()
