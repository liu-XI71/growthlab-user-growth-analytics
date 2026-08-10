from __future__ import annotations

import pytest

from analytics.decomposition import mix_shift_from_aggregates
from analytics.methodology import framework, get_playbook, list_playbooks
from backend.schemas.api import FunnelWorkbenchRequest, MixShiftWorkbenchRequest
from backend.services.workbench_service import decompose_custom_mix_shift, diagnose_custom_funnel


def test_growth_framework_is_complete_and_sources_include_boundaries() -> None:
    result = framework()
    assert "".join(stage["code"] for stage in result["stages"]) == "GROWTH"
    assert len(result["evidence_ladder"]) == 6
    assert len(result["sources"]) >= 8
    assert all(source["url"].startswith("https://") for source in result["sources"])
    assert all(source["boundary"] for source in result["sources"])


def test_problem_playbooks_have_route_output_and_stop_rule() -> None:
    result = list_playbooks()
    assert len(result["items"]) >= 5
    assert all(
        item["route"] and item["minimum_output"] and item["stop_rule"] for item in result["items"]
    )
    assert get_playbook("retention_decline")["id"] == "retention_decline"
    with pytest.raises(LookupError):
        get_playbook("unknown")


def test_aggregate_mix_shift_reconciles_exactly() -> None:
    result = mix_shift_from_aggregates(
        [
            {
                "segment": "mobile",
                "baseline_users": 700,
                "current_users": 550,
                "baseline_rate": 0.48,
                "current_rate": 0.47,
            },
            {
                "segment": "tablet",
                "baseline_users": 200,
                "current_users": 280,
                "baseline_rate": 0.41,
                "current_rate": 0.40,
            },
            {
                "segment": "tv",
                "baseline_users": 100,
                "current_users": 170,
                "baseline_rate": 0.38,
                "current_rate": 0.37,
            },
        ]
    )
    assert result["total_change"] == pytest.approx(
        result["structure_effect"] + result["within_effect"] + result["interaction_effect"]
    )
    assert result["reconciliation_error"] == pytest.approx(0, abs=1e-12)
    assert result["structure_effect"] < 0
    assert result["within_effect"] < 0


def test_aggregate_mix_shift_rejects_duplicate_segments_and_bad_rates() -> None:
    duplicate = [
        {
            "segment": "same",
            "baseline_users": 10,
            "current_users": 10,
            "baseline_rate": 0.4,
            "current_rate": 0.4,
        },
        {
            "segment": "same",
            "baseline_users": 20,
            "current_users": 20,
            "baseline_rate": 0.5,
            "current_rate": 0.5,
        },
    ]
    with pytest.raises(ValueError, match="unique"):
        mix_shift_from_aggregates(duplicate)
    duplicate[1]["segment"] = "other"
    duplicate[1]["current_rate"] = 1.2
    with pytest.raises(ValueError, match="Rates"):
        mix_shift_from_aggregates(duplicate)


def test_custom_funnel_localizes_earliest_material_break() -> None:
    request = FunnelWorkbenchRequest.model_validate(
        {
            "steps": [
                {"step": "exposure", "baseline_uv": 10_000, "current_uv": 10_000},
                {"step": "visit", "baseline_uv": 7_500, "current_uv": 7_500},
                {"step": "invite", "baseline_uv": 1_875, "current_uv": 1_275},
                {"step": "share", "baseline_uv": 1_725, "current_uv": 1_173},
            ],
            "material_threshold": 0.02,
        }
    )
    result = diagnose_custom_funnel(request)
    assert result["diagnosis"]["primary_step"] == "invite"
    assert result["evidence_level"] == 2
    assert "does not prove" in result["claim_boundary"]


def test_custom_mix_shift_service_marks_claim_boundary() -> None:
    request = MixShiftWorkbenchRequest.model_validate(
        {
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
        }
    )
    result = decompose_custom_mix_shift(request)
    assert result["structure_effect"] < 0
    assert result["within_effect"] == pytest.approx(0)
    assert result["evidence_level"] == 2
    assert "not a causal" in result["claim_boundary"]
