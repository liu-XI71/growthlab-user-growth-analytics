from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.api_client import APIError, api_get  # noqa: E402
from frontend.style import apply_theme, note  # noqa: E402

st.set_page_config(
    page_title="GrowthLab | 增长质量与因果决策",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

st.sidebar.markdown("# GrowthLab")
st.sidebar.caption("Quality-Adjusted Growth Decision OS")

pages = {
    "Quality-Adjusted Growth OS": [
        st.Page("pages/executive_cockpit.py", title="01 决策驾驶舱", icon="🧭", default=True),
        st.Page("pages/growth_lifecycle.py", title="02 增长生命周期", icon="🔗"),
        st.Page("pages/investigation_studio.py", title="03 诊断工作台", icon="🔎"),
        st.Page("pages/experiment_causal_lab.py", title="04 实验与因果", icon="🧪"),
        st.Page("pages/growth_economics.py", title="05 经济性与预算", icon="📈"),
        st.Page("pages/decision_governance.py", title="06 决策与治理", icon="🛡️"),
    ],
}

try:
    health = api_get("/health")
    quality = api_get("/data-quality/status")
    st.sidebar.success(f"API · {health.get('status', 'ok')}")
    st.sidebar.caption(f"数据状态：{health.get('database', 'ready')}")
    st.sidebar.caption(
        f"质量门：{quality.get('status', 'unknown')} · {quality.get('check_count', 0)} checks"
    )
except APIError as exc:
    st.sidebar.error("API 未连接")
    note(f"后端服务暂不可用：{exc}", "danger")

st.sidebar.divider()
st.sidebar.markdown("**G → R → O → W → T → H**")
st.sidebar.caption("目标 · 可信 · 定位 · 机制 · 因果 · 价值")
st.sidebar.caption("主决策：ITT / 每万合格分流用户")
st.sidebar.divider()
st.sidebar.caption("全部结果来自公开或确定性模拟数据，不代表任何真实公司。")

navigation = st.navigation(pages)
navigation.run()
