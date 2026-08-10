from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, api_get, api_post
from frontend.components import as_number, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Unit economics",
    "LTV / CAC 与成本敏感性",
    "首月快速回收反馈，同时区分 LTV/CAC 比率和净 ROI，避免指标口径混淆。",
)

try:
    versions = api_get("/referral/versions").get("versions", [])
except APIError as exc:
    st.error(str(exc))
    st.stop()

labels = {item.get("version"): item.get("label", item.get("version")) for item in versions}
selected = (
    st.selectbox(
        "活动版本",
        list(labels),
        index=max(0, len(labels) - 1),
        format_func=lambda key: labels.get(key, key),
    )
    if labels
    else "variant_c"
)

try:
    summary = api_get("/roi/summary", {"version": selected})
except APIError as exc:
    st.error(str(exc))
    st.stop()

render_kpis(
    [
        ("LTV30", as_number(summary.get("ltv30")), None),
        ("CAC", as_number(summary.get("cac")), None),
        ("LTV / CAC", as_number(summary.get("ltv_cac_ratio")), None),
        ("Net ROI", as_number(summary.get("net_roi")), None),
        ("盈亏平衡 CAC", as_number(summary.get("break_even_cac")), None),
    ]
)

note("LTV/CAC = LTV30 ÷ CAC；Net ROI = (LTV30 − CAC) ÷ CAC。二者不能混用。", "success")

inputs = summary.get("inputs", {})
with st.form("sensitivity"):
    left, middle, right = st.columns(3)
    active_days = left.slider(
        "首月人均活跃天数", 1.0, 30.0, float(inputs.get("active_days_30", 9.0)), 0.5
    )
    daily_hours = middle.slider(
        "日均活跃小时", 0.1, 5.0, float(inputs.get("daily_active_hours", 0.8)), 0.1
    )
    hourly_value = right.slider(
        "单位时长商业化价值", 0.1, 10.0, float(inputs.get("value_per_hour", 1.2)), 0.1
    )
    cost = left.slider("人均获客激励成本", 1.0, 100.0, float(summary.get("cac", 20.0)), 1.0)
    retention_discount = middle.slider(
        "留存价值折扣", 0.1, 1.0, float(inputs.get("retention_discount", 0.8)), 0.05
    )
    submitted = st.form_submit_button("运行敏感性分析", use_container_width=True)

if submitted:
    try:
        result = api_post(
            "/roi/sensitivity",
            {
                "base": {
                    "active_days_30": active_days,
                    "daily_active_hours": daily_hours,
                    "value_per_hour": hourly_value,
                    "incentive_cost_per_acquisition": cost,
                    "retention_discount": retention_discount,
                    "external_benchmark_ratio": float(summary.get("external_benchmark_ratio", 1.6)),
                },
            },
        )
        items = result.get("items", [])
        if items:
            frame = pd.DataFrame(items)
            value_column = (
                "impact" if "impact" in frame.columns else frame.select_dtypes("number").columns[-1]
            )
            label_column = "parameter" if "parameter" in frame.columns else frame.columns[0]
            fig = px.bar(
                frame,
                x=value_column,
                y=label_column,
                orientation="h",
                color=value_column,
                color_continuous_scale=[
                    [0, COLORS["red"]],
                    [0.5, COLORS["amber"]],
                    [1, COLORS["green"]],
                ],
            )
            st.plotly_chart(fig, use_container_width=True)
        st.json(result.get("base", result), expanded=False)
    except APIError as exc:
        st.error(str(exc))
