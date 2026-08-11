from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODULES = {
    "executive_cockpit.py": {
        "/lifecycle/summary",
        "/experiments/referral_ui_simplification/effects",
        "render_decision_card",
    },
    "growth_lifecycle.py": {
        "/lifecycle/summary",
        "/lifecycle/cohorts",
        "/lifecycle/acquisition-quality",
    },
    "investigation_studio.py": {
        "/referral/funnel",
        "/investigation/mix-shift",
        "/investigation/paths",
    },
    "experiment_causal_lab.py": {
        'f"/experiments/{experiment_id}/health"',
        'f"/experiments/{experiment_id}/effects"',
        "render_decision_card",
    },
    "growth_economics.py": {
        "/economics/summary",
        "/economics/scenarios",
        "Incremental Contribution30",
    },
    "decision_governance.py": {
        "/decisions",
        "/data-quality/status",
        "/metrics",
    },
}


def test_navigation_exposes_exactly_the_six_option_b_modules() -> None:
    source = (PROJECT_ROOT / "frontend" / "streamlit_app.py").read_text(encoding="utf-8")
    expected_paths = {f"pages/{name}" for name in MODULES}
    assert {path for path in expected_paths if path in source} == expected_paths
    assert source.count("st.Page(") == 6
    assert "Quality-Adjusted Growth Decision OS" in source
    assert "主决策：ITT" in source
    assert "不代表任何真实公司" in source


def test_each_module_has_header_growth_gate_visual_and_required_decision_contract() -> None:
    for filename, required_tokens in MODULES.items():
        path = PROJECT_ROOT / "frontend" / "pages" / filename
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        assert "page_header(" in source, filename
        assert "growth_gate(" in source, filename
        assert "st.plotly_chart(" in source or "st.dataframe(" in source, filename
        for token in required_tokens:
            assert token in source, f"{filename} is missing {token}"


def test_causal_and_descriptive_language_is_not_conflated_in_ui_source() -> None:
    lifecycle = (PROJECT_ROOT / "frontend" / "pages" / "growth_lifecycle.py").read_text(
        encoding="utf-8"
    )
    experiment = (PROJECT_ROOT / "frontend" / "pages" / "experiment_causal_lab.py").read_text(
        encoding="utf-8"
    )
    economics = (PROJECT_ROOT / "frontend" / "pages" / "growth_economics.py").read_text(
        encoding="utf-8"
    )
    assert "历史活动版本（描述性）" in lifecycle
    assert "不得称作增量或因果效果" in lifecycle
    assert "Triggered / exposed 分析是 post-assignment 子集" in experiment
    assert "不能替代 ITT 上线结论" in experiment
    assert "selection" in experiment.lower() or "选择偏差" in experiment
    assert "Average LTV/CAC" in economics
    assert "Incremental Contribution30" in economics
    assert "不构造不稳定的 incremental LTV/CAC" in economics
