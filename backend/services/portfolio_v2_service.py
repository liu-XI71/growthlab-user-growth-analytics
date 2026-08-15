from __future__ import annotations

from typing import Any

from backend.database.connection import query_records


def _rows(table: str, order_by: str | None = None) -> list[dict[str, Any]]:
    allowed = {
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
    if table not in allowed:
        raise ValueError(f"Unsupported portfolio table: {table}")
    clause = f" ORDER BY {order_by}" if order_by else ""
    return query_records(f'SELECT * FROM "{table}"{clause}')


def portfolio_bundle() -> dict[str, Any]:
    return {
        "meta": {
            "projectName": "Growth Analytics Decision Platform",
            "projectNameZh": "用户增长全链路分析与实验决策平台",
            "version": "2.0",
            "dataBoundary": (
                "公开作品集：项目事实来自脱敏叙述；明细、未披露分组值和辅助趋势为确定性模拟数据。"
            ),
        },
        "cases": _rows("portfolio_case_registry", "case_order"),
        "businessKpis": _rows("portfolio_business_kpis", "display_order"),
        "decisionLoop": _rows("portfolio_decision_loop", "step_order"),
        "referral": {
            "versions": _rows("portfolio_referral_versions", "version_order"),
            "funnel": _rows("portfolio_referral_funnel", "version_id, step_order"),
            "experiment": _experiment("referral_growth"),
        },
        "retention": {
            "trend": _rows("portfolio_retention_trend", "period, cohort_day"),
            "segments": _rows("portfolio_retention_segments", "period, segment"),
            "path": _rows("portfolio_retention_path", "step_order"),
            "benchmark": _rows("portfolio_benchmark_features", "ratio DESC"),
            "experiment": _experiment("new_user_retention"),
        },
        "experiments": _rows("portfolio_experiments", "experiment_id"),
        "metricContracts": _rows("portfolio_metric_contracts", "metric_key"),
        "decisions": _rows("portfolio_decisions", "decision_id"),
    }


def _experiment(case_id: str) -> dict[str, Any]:
    records = query_records("SELECT * FROM portfolio_experiments WHERE case_id = ?", [case_id])
    if not records:
        raise LookupError(f"Experiment not found for case: {case_id}")
    return records[0]


def overview() -> dict[str, Any]:
    bundle = portfolio_bundle()
    return {
        "meta": bundle["meta"],
        "cases": bundle["cases"],
        "businessKpis": bundle["businessKpis"],
        "decisionLoop": bundle["decisionLoop"],
    }


def referral_case() -> dict[str, Any]:
    bundle = portfolio_bundle()
    return {
        "case": next(item for item in bundle["cases"] if item["case_id"] == "referral_growth"),
        **bundle["referral"],
        "decision": next(
            item for item in bundle["decisions"] if item["case_id"] == "referral_growth"
        ),
    }


def retention_case() -> dict[str, Any]:
    bundle = portfolio_bundle()
    return {
        "case": next(item for item in bundle["cases"] if item["case_id"] == "new_user_retention"),
        **bundle["retention"],
        "decision": next(
            item for item in bundle["decisions"] if item["case_id"] == "new_user_retention"
        ),
    }


def experiments_center() -> dict[str, Any]:
    return {"items": _rows("portfolio_experiments", "experiment_id")}


def metrics_governance() -> dict[str, Any]:
    return {"items": _rows("portfolio_metric_contracts", "metric_key")}


def decision_records() -> dict[str, Any]:
    return {"items": _rows("portfolio_decisions", "decision_id")}
