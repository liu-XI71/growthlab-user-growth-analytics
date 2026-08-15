from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.portfolio_v2_data import portfolio_v2_frames

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "web" / "public" / "data" / "portfolio.json"


def _value(value: Any) -> Any:
    if value is None or (isinstance(value, (float, np.floating)) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [{key: _value(value) for key, value in row.items()} for row in frame.to_dict("records")]


def build_bundle() -> dict[str, Any]:
    frames = portfolio_v2_frames()
    experiments = _records(frames["portfolio_experiments"])
    cases = _records(frames["portfolio_case_registry"])
    decisions = _records(frames["portfolio_decisions"])
    return {
        "meta": {
            "projectName": "Growth Analytics Decision Platform",
            "projectNameZh": "用户增长全链路分析与实验决策平台",
            "version": "2.0",
            "dataBoundary": (
                "公开作品集：项目事实来自脱敏叙述；明细、未披露分组值和辅助趋势为确定性模拟数据。"
            ),
        },
        "cases": cases,
        "businessKpis": _records(frames["portfolio_business_kpis"]),
        "decisionLoop": _records(frames["portfolio_decision_loop"]),
        "referral": {
            "versions": _records(frames["portfolio_referral_versions"]),
            "funnel": _records(frames["portfolio_referral_funnel"]),
            "experiment": next(
                item for item in experiments if item["case_id"] == "referral_growth"
            ),
        },
        "retention": {
            "trend": _records(frames["portfolio_retention_trend"]),
            "segments": _records(frames["portfolio_retention_segments"]),
            "path": _records(frames["portfolio_retention_path"]),
            "benchmark": _records(frames["portfolio_benchmark_features"]),
            "experiment": next(
                item for item in experiments if item["case_id"] == "new_user_retention"
            ),
        },
        "experiments": experiments,
        "metricContracts": _records(frames["portfolio_metric_contracts"]),
        "decisions": decisions,
    }


def export_bundle(output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_bundle(), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the V2 public portfolio data bundle")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(export_bundle(args.output))


if __name__ == "__main__":
    main()
