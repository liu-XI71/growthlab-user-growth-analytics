from __future__ import annotations

import math
import time
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from scripts.generate_demo_data import generate_database


@pytest.fixture(scope="module")
def api_client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    database = tmp_path_factory.mktemp("growthlab-api") / "api.duckdb"
    # Five thousand users is the smallest supported QA profile that preserves
    # the intended funnel and experiment mechanisms without small-cell noise.
    generate_database(database, users=5_000, seed=42)
    original_path = settings.db_path
    original_auto = settings.auto_generate_demo
    settings.db_path = Path(database)
    settings.auto_generate_demo = False
    try:
        with TestClient(app) as client:
            yield client
    finally:
        settings.db_path = original_path
        settings.auto_generate_demo = original_auto


def test_health_openapi_and_metric_catalog_smoke(api_client: TestClient) -> None:
    health = api_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["database"] == "ready"
    openapi = api_client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/experiments/analyze" in openapi.json()["paths"]
    metrics = api_client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["count"] >= 10


@pytest.mark.parametrize(
    "endpoint",
    [
        "/metrics/tree",
        "/growth/trend?metric=dau_index",
        "/referral/summary?version=variant_c",
        "/referral/funnel?version=variant_b&baseline_version=variant_a",
        "/referral/versions",
        "/roi/summary?version=variant_c",
        "/retention/summary?period=current",
        "/retention/cohorts?period=current",
        "/retention/segments?dimension=device_type&period=current",
        "/retention/decomposition?dimension=device_type",
        "/retention/funnel?period=current",
        "/feature-analysis",
        "/experiments",
        "/data-quality/status",
    ],
)
def test_critical_read_endpoints_return_json(api_client: TestClient, endpoint: str) -> None:
    response = api_client.get(endpoint)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), dict)


def test_referral_endpoint_returns_computed_diagnostic_not_hardcoded_ui_text(
    api_client: TestClient,
) -> None:
    response = api_client.get("/referral/funnel?version=variant_b&baseline_version=variant_a")
    body = response.json()
    assert response.status_code == 200
    assert body["diagnosis"]["primary_step"] == "invite_click"
    assert body["synthetic_data"] is True
    assert body["comparison"]


def test_retention_response_distinguishes_exact_d7_from_window_metric(
    api_client: TestClient,
) -> None:
    response = api_client.get("/retention/summary?period=current")
    body = response.json()
    assert response.status_code == 200
    assert "d7" in body and "d1_7_window" in body
    assert "exact-day" in body["metric_note"]
    assert body["d1_7_window"] >= body["d7"]

    cohorts = api_client.get("/retention/cohorts?period=current").json()
    assert cohorts["definition"]["inclusion"] == "signup week"
    assert all({"d1", "d3", "d7", "d30"}.issubset(item) for item in cohorts["items"])
    assert "matured" in cohorts["censoring_warning"]


def test_feature_analysis_is_explicitly_correlational(api_client: TestClient) -> None:
    body = api_client.get("/feature-analysis").json()
    warning = body["causality_warning"].lower()
    assert "correlational" in warning
    assert "self-selection" in warning
    assert "random" in warning
    assert body["possible_confounders"]


def test_dimension_whitelist_blocks_arbitrary_sql(api_client: TestClient) -> None:
    response = api_client.get(
        "/retention/segments",
        params={"dimension": "device_type; DROP TABLE users;--", "period": "current"},
    )
    assert response.status_code == 422
    assert "Unsupported dimension" in response.json()["detail"]
    assert api_client.get("/health").status_code == 200


def test_unknown_governed_values_return_useful_404(api_client: TestClient) -> None:
    response = api_client.get("/referral/summary?version=does-not-exist")
    assert response.status_code == 404
    assert "Unknown referral version" in response.json()["detail"]


def test_roi_sensitivity_api_validates_payload_and_returns_scenarios(
    api_client: TestClient,
) -> None:
    payload = {
        "base": {
            "active_days_30": 10,
            "daily_active_hours": 0.5,
            "value_per_hour": 4,
            "incentive_cost_per_acquisition": 8,
            "retention_discount": 0.8,
            "external_benchmark_ratio": 1.9,
        },
        "variations": {"incentive_cost_per_acquisition": [0.8, 1.2]},
    }
    response = api_client.post("/roi/sensitivity", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["base"]["ltv_cac_ratio"] == pytest.approx(2.0)
    assert len(response.json()["items"]) == 2
    invalid = dict(payload)
    invalid["base"] = {**payload["base"], "incentive_cost_per_acquisition": 0}
    assert api_client.post("/roi/sensitivity", json=invalid).status_code == 422


def test_stored_experiment_response_covers_full_governance_flow(api_client: TestClient) -> None:
    response = api_client.post(
        "/experiments/analyze",
        json={"experiment_id": "referral_ui_simplification"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["design"]["core_metric"] == "invite_click_rate"
    assert body["design"]["business_metric"] == "referral_new_users"
    assert body["assignment"]["unit"] == "user_id"
    assert body["assignment"]["ratio"] == "1:1"
    assert body["aa"]["pass"] is True
    assert body["balance"]["overall_srm"]["pass"] is not False
    assert {item["dimension"] for item in body["balance"]["dimension_checks"]} == {
        "channel",
        "device_type",
        "region",
    }
    assert body["ab"]["absolute_uplift_pp"] > 0
    assert body["ab"]["confidence_interval_absolute"]["lower"] > 0
    assert set(body["risks"]) == {"novelty", "network", "peeking", "composition"}
    assert "do not stop" in body["risks"]["peeking"].lower()


def test_ad_hoc_experiment_requires_complete_counts(api_client: TestClient) -> None:
    invalid = api_client.post(
        "/experiments/analyze",
        json={"control_successes": 170, "control_n": 1_000},
    )
    assert invalid.status_code == 422
    valid = api_client.post(
        "/experiments/analyze",
        json={
            "control_successes": 1_700,
            "control_n": 10_000,
            "treatment_successes": 2_000,
            "treatment_n": 10_000,
            "baseline_rate": 0.17,
            "mde_absolute": 0.03,
            "eligible_users_per_day": 5_000,
            "minimum_full_weeks": 2,
            "core_metric": "invite_click_rate",
        },
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["ab"]["absolute_uplift_pp"] == pytest.approx(3.0)


def test_data_quality_endpoint_matches_generated_database(api_client: TestClient) -> None:
    body = api_client.get("/data-quality/status").json()
    assert body["status"] == "pass"
    assert body["failed_count"] == 0
    assert body["check_count"] >= 15
    assert all(item["status"] == "pass" for item in body["checks"])


def test_methodology_and_playbook_endpoints_expose_claim_boundaries(api_client: TestClient) -> None:
    methodology = api_client.get("/methodology")
    assert methodology.status_code == 200
    body = methodology.json()
    assert "".join(item["code"] for item in body["stages"]) == "GROWTH"
    assert all(item["boundary"] for item in body["sources"])
    playbooks = api_client.get("/methodology/playbooks")
    assert playbooks.status_code == 200
    assert len(playbooks.json()["items"]) >= 5
    assert api_client.get("/methodology/playbooks/not-found").status_code == 404


def test_growth_trend_exposes_normalized_target_and_investigation_boundary(
    api_client: TestClient,
) -> None:
    response = api_client.get("/growth/trend?metric=dau_index")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == 91
    assert len(body["components"]) == 4
    assert body["latest"]["target_index"] == 80
    assert "do not identify" in body["claim_boundary"]
    assert api_client.get("/growth/trend?metric=raw_internal_metric").status_code == 422


def test_workbench_funnel_and_mix_shift_accept_aggregate_data(api_client: TestClient) -> None:
    funnel = api_client.post(
        "/workbench/funnel",
        json={
            "steps": [
                {"step": "exposure", "baseline_uv": 10_000, "current_uv": 10_000},
                {"step": "visit", "baseline_uv": 7_500, "current_uv": 7_500},
                {"step": "invite", "baseline_uv": 1_875, "current_uv": 1_275},
                {"step": "share", "baseline_uv": 1_725, "current_uv": 1_173},
            ]
        },
    )
    assert funnel.status_code == 200, funnel.text
    assert funnel.json()["diagnosis"]["primary_step"] == "invite"
    invalid_funnel = api_client.post(
        "/workbench/funnel",
        json={
            "steps": [
                {"step": "start", "baseline_uv": 10, "current_uv": 10},
                {"step": "impossible", "baseline_uv": 11, "current_uv": 9},
            ]
        },
    )
    assert invalid_funnel.status_code == 422

    decomposition = api_client.post(
        "/workbench/mix-shift",
        json={
            "rows": [
                {
                    "segment": "phone",
                    "baseline_users": 80,
                    "current_users": 60,
                    "baseline_rate": 0.5,
                    "current_rate": 0.5,
                },
                {
                    "segment": "large_screen",
                    "baseline_users": 20,
                    "current_users": 40,
                    "baseline_rate": 0.3,
                    "current_rate": 0.3,
                },
            ]
        },
    )
    assert decomposition.status_code == 200, decomposition.text
    assert decomposition.json()["structure_effect"] < 0
    assert decomposition.json()["reconciliation_error"] == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/lifecycle/summary",
        "/lifecycle/cohorts",
        "/lifecycle/acquisition-quality",
        "/investigation/paths",
        "/investigation/mix-shift",
        "/experiments/referral_ui_simplification/health",
        "/experiments/referral_ui_simplification/effects",
        "/economics/summary",
        "/decisions",
        "/metrics/incremental_d7_retained_per_10k_assigned/lineage",
    ],
)
def test_option_b_read_routes_return_serializable_deterministic_json(
    api_client: TestClient, endpoint: str
) -> None:
    first = api_client.get(endpoint)
    second = api_client.get(endpoint)
    assert first.status_code == 200, first.text
    assert first.headers["content-type"].startswith("application/json")
    assert first.json() == second.json()

    def assert_finite(value: object) -> None:
        if isinstance(value, float):
            assert math.isfinite(value)
        elif isinstance(value, dict):
            for nested in value.values():
                assert_finite(nested)
        elif isinstance(value, list):
            for nested in value:
                assert_finite(nested)

    assert_finite(first.json())


def test_lifecycle_api_links_identity_maturity_and_quality_adjusted_estimands(
    api_client: TestClient,
) -> None:
    summary = api_client.get("/lifecycle/summary").json()
    assert summary["north_star"] == "incremental high-quality retained users and contribution value"
    assert [item["step"] for item in summary["lifecycle"]] == [
        "eligible_assignment",
        "tracked_exposure",
        "invite_click",
        "new_user_activate",
        "d1_7_retained",
        "d7_retained",
    ]
    assert all(
        left["users"] >= right["users"]
        for left, right in zip(summary["lifecycle"], summary["lifecycle"][1:], strict=False)
    )
    quality = summary["quality_adjusted_effects"]
    for key in ("d7_retained", "d1_7_window_retained", "contribution30"):
        metric = quality[key]
        assert metric["denominator_type"] == "assignment"
        assert metric["population"] == "intention_to_treat"
        assert metric["non_acquired_contribution"] == 0
        assert metric["window"]
        assert metric["unit"]

    cohorts = api_client.get("/lifecycle/cohorts").json()
    assert cohorts["invitee_identity"].startswith("referral_edges.new_user_id")
    assert cohorts["horizons"]["d7"].startswith("exact")
    assert "day 1" in cohorts["horizons"]["d1_7_window"]
    assert cohorts["items"]
    for row in cohorts["items"]:
        assert row["retained_d7_users"] <= row["mature_d7_users"]
        assert row["retained_d1_7_window_users"] <= row["mature_d7_users"]
        assert row["retained_d30_users"] <= row["mature_d30_users"]
        assert row["immature_d7_users"] == row["activated_users"] - row["mature_d7_users"]
        assert row["immature_d30_users"] == row["activated_users"] - row["mature_d30_users"]
        assert row["as_of_date"] == cohorts["horizons"]["as_of_date"]


def test_option_b_api_metrics_match_direct_itt_sql(api_client: TestClient) -> None:
    effects = api_client.get("/experiments/referral_ui_simplification/effects").json()
    with duckdb.connect(str(settings.db_path), read_only=True) as connection:
        golden = connection.execute(
            """
            WITH arm AS (
              SELECT group_name, COUNT(*) AS n,
                     SUM(retained_d7::INT) AS d7,
                     SUM(retained_d1_7_window::INT) AS win,
                     SUM(contribution30) AS contribution
              FROM mart_experiment_user_value
              WHERE experiment_id='referral_ui_simplification'
              GROUP BY 1
            )
            SELECT
              10000*(MAX(d7/n::DOUBLE) FILTER(group_name='treatment')
                     -MAX(d7/n::DOUBLE) FILTER(group_name='control')),
              10000*(MAX(win/n::DOUBLE) FILTER(group_name='treatment')
                     -MAX(win/n::DOUBLE) FILTER(group_name='control')),
              10000*(MAX(contribution/n::DOUBLE) FILTER(group_name='treatment')
                     -MAX(contribution/n::DOUBLE) FILTER(group_name='control'))
            FROM arm
            """
        ).fetchone()
    assert golden is not None
    quality = effects["quality_adjusted_effects"]
    actual = (
        quality["d7_retained"]["estimate"],
        quality["d1_7_window_retained"]["estimate"],
        quality["contribution30"]["estimate"],
    )
    assert actual == pytest.approx(golden)


def test_experiment_health_separates_itt_from_triggered_and_uses_pre_treatment_smd(
    api_client: TestClient,
) -> None:
    health = api_client.get("/experiments/referral_ui_simplification/health").json()
    assert health["primary_estimand"] == {
        "population": "intention_to_treat",
        "denominator_type": "assignment",
        "reason": "Preserves randomization and includes non-exposed assignments.",
    }
    triggered = health["triggered_diagnostic"]
    assert triggered["denominator_type"] == "tracked_exposure"
    assert triggered["population"] == "post_assignment_exposed"
    assert "must not replace" in triggered["selection_bias_warning"]
    assert health["smd_threshold"] == pytest.approx(0.1)
    assert {item["dimension"] for item in health["pre_treatment_balance"]} == {
        "channel",
        "device_type",
        "region",
    }
    assert all(
        item["method"].endswith("pre-treatment covariates")
        for item in health["pre_treatment_balance"]
    )


def test_small_profile_decision_is_no_go_on_explicit_sample_gate(api_client: TestClient) -> None:
    effects = api_client.get("/experiments/referral_ui_simplification/effects").json()
    card = effects["decision_card"]
    gates = {item["gate"]: item for item in card["gates"]}
    required = {
        "data_quality",
        "assignment_and_exposure_integrity",
        "srm",
        "pre_treatment_balance",
        "exposure_tracking",
        "sample_size",
        "fixed_horizon_duration",
        "outcome_maturity",
        "guardrail",
        "statistical_significance",
        "business_significance",
        "incremental_contribution30",
    }
    assert required <= gates.keys()
    assert gates["sample_size"]["pass"] is False
    assert card["decision"] == "DO_NOT_SHIP"
    assert card["all_gates_pass"] is False
    assert "sample_size" in card["failed_or_unknown_gates"]
    timing = effects["decision_basis"]["timing"]
    assert timing["experiment_duration_days"] >= timing["experiment_required_days"]
    assert timing["value_followup_observed_days"] >= timing["value_followup_required_days"]


def test_week_and_segment_results_cannot_masquerade_as_unadjusted_decision_rules(
    api_client: TestClient,
) -> None:
    effects = api_client.get("/experiments/referral_ui_simplification/effects").json()
    assert "must not change" in effects["week_slice_warning"]
    assert all(
        row["purpose"] == "novelty_and_durability_diagnostic_only" for row in effects["week_slices"]
    )
    assert effects["segment_effects"]
    for row in effects["segment_effects"]:
        assert row["classification"] in {"pre_specified", "exploratory"}
        assert row["ci_lower"] <= row["absolute_uplift"] <= row["ci_upper"]
        assert 0 <= row["adjusted_p_value"] <= 1
        assert row["multiplicity_method"]
        assert row["heterogeneity_claim"] == "not_claimed_from_subgroup_significance"


def test_descriptive_economics_never_claim_incrementality(api_client: TestClient) -> None:
    quality = api_client.get("/lifecycle/acquisition-quality").json()
    assert quality["evidence_level"] == "descriptive"
    assert quality["causal_claim_allowed"] is False
    assert "not incremental" in quality["claim_boundary"]
    assert all(not any("incremental" in key.lower() for key in row) for row in quality["items"])
    economics = api_client.get("/economics/summary").json()
    assert "descriptive" in economics["average_ltv_cac_definition"].lower()
    assert economics["causal_itt_economics"]["primary_estimand"] == "intention_to_treat"
    assert "intentionally not reported" in economics["no_incremental_ltv_cac"]


@pytest.mark.parametrize(
    ("endpoint", "status"),
    [
        ("/lifecycle/cohorts?source_kind=unknown", 422),
        ("/investigation/paths?acquisition_source=unknown", 422),
        ("/experiments/not-a-real-experiment/effects", 404),
        ("/experiments/not-a-real-experiment/health", 404),
        ("/metrics/not-a-real-metric/lineage", 404),
    ],
)
def test_option_b_read_route_error_boundaries(
    api_client: TestClient, endpoint: str, status: int
) -> None:
    response = api_client.get(endpoint)
    assert response.status_code == status
    assert response.status_code != 500


@pytest.mark.parametrize(
    "payload",
    [
        {"experiment_id": "not-real", "budget_multipliers": [1, 2]},
        {"budget_multipliers": [0, 1]},
        {"budget_multipliers": [1, 1]},
        {"budget_multipliers": [1, 2], "eligible_population": -1},
        {"budget_multipliers": [1, 2], "response_elasticity": 0},
    ],
)
def test_economics_scenario_rejects_invalid_inputs_without_500(
    api_client: TestClient, payload: dict
) -> None:
    response = api_client.post("/economics/scenarios", json=payload)
    assert response.status_code == 422, response.text


def test_representative_option_b_routes_meet_ci_fixture_latency(api_client: TestClient) -> None:
    endpoints = [
        "/lifecycle/summary",
        "/experiments/referral_ui_simplification/effects",
        "/economics/summary",
    ]
    for endpoint in endpoints:
        api_client.get(endpoint)  # warm connection and imports
        started = time.perf_counter()
        response = api_client.get(endpoint)
        elapsed = time.perf_counter() - started
        assert response.status_code == 200, response.text
        assert elapsed < 2.0, f"{endpoint} took {elapsed:.3f}s on the 5k CI fixture"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v2/portfolio",
        "/api/v2/overview",
        "/api/v2/cases/referral",
        "/api/v2/cases/retention",
        "/api/v2/experiments",
        "/api/v2/metrics/contracts",
        "/api/v2/decisions",
    ],
)
def test_portfolio_v2_routes_are_serializable_and_stable(
    api_client: TestClient, endpoint: str
) -> None:
    first = api_client.get(endpoint)
    second = api_client.get(endpoint)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()


def test_portfolio_v2_retention_does_not_invent_undisclosed_lift(
    api_client: TestClient,
) -> None:
    body = api_client.get("/api/v2/cases/retention").json()
    assert body["experiment"]["absolute_lift_pp"] is None
    assert body["experiment"]["baseline_rate"] is None
    assert body["experiment"]["significance"] == "p < 0.05"
    assert body["experiment"]["sample_size"] == 300_000
    assert body["experiment"]["sample_display"] == "约30万样本"


def test_portfolio_v2_referral_uses_anonymized_incentive_index(
    api_client: TestClient,
) -> None:
    body = api_client.get("/api/v2/cases/referral").json()
    assert [row["incentive_index"] for row in body["versions"]] == [100.0, 160.0, 160.0]
    assert body["experiment"]["absolute_lift_pp"] == pytest.approx(6.5)
    assert body["experiment"]["sample_size"] is None
    assert body["experiment"]["sample_display"] == "百万级脱敏样本"
