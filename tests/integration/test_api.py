from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

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
