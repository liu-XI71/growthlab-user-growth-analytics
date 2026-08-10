from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from analytics.methodology import framework, get_playbook, list_playbooks
from backend.database.connection import ensure_database
from backend.schemas.api import (
    ExperimentAnalysisRequest,
    FunnelWorkbenchRequest,
    MixShiftWorkbenchRequest,
    RoiSensitivityRequest,
)
from backend.services import analytics_service as service
from backend.services import workbench_service as workbench

router = APIRouter()


def _translate_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=500, detail="Unexpected analytics service error")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    path = ensure_database()
    return {
        "status": "ok",
        "database": "ready" if path.exists() else "missing",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics", tags=["metrics"])
def metrics() -> dict:
    return service.list_metrics()


@router.get("/metrics/tree", tags=["metrics"])
def metrics_tree() -> dict:
    return service.get_metric_tree()


@router.get("/growth/trend", tags=["growth"])
def growth_trend(metric: str = "dau_index") -> dict:
    try:
        return service.growth_trend(metric)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/referral/summary", tags=["referral"])
def referral_summary(version: str = "variant_c") -> dict:
    try:
        return service.referral_summary(version)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/referral/funnel", tags=["referral"])
def referral_funnel(version: str = "variant_c", baseline_version: str = "variant_a") -> dict:
    try:
        return service.referral_funnel(version, baseline_version)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/referral/versions", tags=["referral"])
def referral_versions() -> dict:
    return service.referral_versions()


@router.get("/roi/summary", tags=["roi"])
def roi_summary(version: str = "variant_c") -> dict:
    try:
        return service.roi_summary(version)
    except Exception as error:
        raise _translate_error(error) from error


@router.post("/roi/sensitivity", tags=["roi"])
def roi_sensitivity(request: RoiSensitivityRequest) -> dict:
    try:
        return service.roi_sensitivity(request)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/retention/summary", tags=["retention"])
def retention_summary(period: str = "current") -> dict:
    try:
        return service.retention_summary(period)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/retention/cohorts", tags=["retention"])
def retention_cohorts(period: str = "current") -> dict:
    try:
        return service.retention_cohorts(period)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/retention/segments", tags=["retention"])
def retention_segments(
    dimension: Annotated[
        str, Query(description="Governed dimension; arbitrary SQL is not accepted")
    ] = "device_type",
    period: str = "current",
) -> dict:
    try:
        return service.retention_segments(period, dimension)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/retention/decomposition", tags=["retention"])
def retention_decomposition(dimension: str = "device_type") -> dict:
    try:
        return service.retention_decomposition(dimension)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/retention/funnel", tags=["retention"])
def retention_funnel(period: str = "current") -> dict:
    try:
        return service.retention_funnel(period)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/feature-analysis", tags=["feature-analysis"])
def feature_analysis() -> dict:
    return service.feature_analysis()


@router.get("/experiments", tags=["experimentation"])
def experiments() -> dict:
    return service.list_experiments()


@router.post("/experiments/analyze", tags=["experimentation"])
def analyze_experiment(request: ExperimentAnalysisRequest) -> dict:
    try:
        return service.analyze_experiment_request(request)
    except Exception as error:
        raise _translate_error(error) from error


@router.get("/data-quality/status", tags=["data-quality"])
def data_quality() -> dict:
    return service.data_quality_status()


@router.get("/methodology", tags=["methodology"])
def methodology() -> dict:
    return framework()


@router.get("/methodology/playbooks", tags=["methodology"])
def methodology_playbooks() -> dict:
    return list_playbooks()


@router.get("/methodology/playbooks/{playbook_id}", tags=["methodology"])
def methodology_playbook(playbook_id: str) -> dict:
    try:
        return get_playbook(playbook_id)
    except Exception as error:
        raise _translate_error(error) from error


@router.post("/workbench/funnel", tags=["workbench"])
def workbench_funnel(request: FunnelWorkbenchRequest) -> dict:
    try:
        return workbench.diagnose_custom_funnel(request)
    except Exception as error:
        raise _translate_error(error) from error


@router.post("/workbench/mix-shift", tags=["workbench"])
def workbench_mix_shift(request: MixShiftWorkbenchRequest) -> dict:
    try:
        return workbench.decompose_custom_mix_shift(request)
    except Exception as error:
        raise _translate_error(error) from error
