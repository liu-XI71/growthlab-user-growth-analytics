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
    page_title="GrowthLab | 用户增长分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

st.sidebar.markdown("# GrowthLab")
st.sidebar.caption("GROWTH Decision OS · 用户增长分析与实验决策平台")

pages = {
    "方法与工具": [
        st.Page("pages/methodology.py", title="GROWTH 方法论", icon="🧠"),
        st.Page("pages/workbench.py", title="通用分析工作台", icon="🛠️"),
        st.Page("pages/data_quality.py", title="数据质量与治理", icon="🛡️"),
    ],
    "增长诊断": [
        st.Page("pages/overview.py", title="增长总览与指标树", icon="📈", default=True),
        st.Page("pages/referral_funnel.py", title="老带新漏斗诊断", icon="🔗"),
        st.Page("pages/roi_ltv.py", title="ROI / LTV", icon="💰"),
    ],
    "留存与实验": [
        st.Page("pages/retention.py", title="新用户留存诊断", icon="🧭"),
        st.Page("pages/feature_analysis.py", title="相关与因果", icon="🧩"),
        st.Page("pages/experiments.py", title="A/A 与 A/B 实验", icon="🧪"),
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
st.sidebar.caption("目标 · 可信 · 定位 · 假设 · 因果 · 价值")
st.sidebar.divider()
st.sidebar.caption("全部结果来自公开或确定性模拟数据，不代表任何真实公司。")

navigation = st.navigation(pages)
navigation.run()
