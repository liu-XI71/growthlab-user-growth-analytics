from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import as_percent, dataframe, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Retention diagnosis",
    "新用户留存：分层、结构分解与路径排查",
    "区分设备/渠道结构效应和组内留存变化，并检查首次使用路径是否出现卡点。",
)

period = st.radio(
    "分析周期",
    ["baseline", "current"],
    format_func=lambda x: "基准周期" if x == "baseline" else "留存下降周期",
    horizontal=True,
)
dimension = st.selectbox(
    "分层维度",
    ["device_type", "channel", "operating_system", "region"],
    format_func=lambda x: {
        "device_type": "设备类型",
        "channel": "渠道",
        "operating_system": "操作系统",
        "region": "地域",
    }[x],
)

try:
    summary = api_get("/retention/summary", {"period": period})
    cohorts = api_get("/retention/cohorts", {"period": period})
    segments = api_get("/retention/segments", {"dimension": dimension, "period": period})
    decomposition = api_get("/retention/decomposition", {"dimension": dimension})
    funnel = api_get("/retention/funnel", {"period": period})
except APIError as exc:
    st.error(str(exc))
    st.stop()

render_kpis(
    [
        ("D1 精确日留存", as_percent(summary.get("d1")), None),
        ("D3 精确日留存", as_percent(summary.get("d3")), None),
        ("D7 精确日留存", as_percent(summary.get("d7")), None),
        ("D1-7 窗口留存", as_percent(summary.get("d1_7_window")), None),
        ("D30 精确日留存", as_percent(summary.get("d30")), None),
    ]
)
note("D7 是新增后第 7 天回访；D1-7 窗口留存是第 1 至 7 天至少回访一次。两者不能混用。")

st.subheader("新增 Cohort 成熟曲线")
cohort_items = cohorts.get("items", [])
if cohort_items:
    cohort_frame = pd.DataFrame(cohort_items).set_index("cohort_week")
    heatmap_columns = ["d1", "d3", "d7", "d30"]
    fig = px.imshow(
        cohort_frame[heatmap_columns],
        text_auto=".1%",
        aspect="auto",
        color_continuous_scale=[[0, "#F3F6FB"], [1, COLORS["blue"]]],
        labels={"x": "相对新增日", "y": "新增周 Cohort", "color": "留存率"},
    )
    fig.update_xaxes(ticktext=["D1", "D3", "D7", "D30"], tickvals=heatmap_columns)
    fig.update_layout(height=330, margin=dict(t=20, l=20, r=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    definition = cohorts.get("definition", {})
    st.caption(
        f"进入条件：{definition.get('inclusion')}；回访条件：{definition.get('return')}；粒度：{definition.get('grain')}。"
    )
    note(cohorts.get("censoring_warning", "近期 Cohort 未成熟时不要报告长期留存。"), "warning")

left, right = st.columns(2)
with left:
    st.subheader("分层留存")
    items = segments.get("items", [])
    if items:
        frame = pd.DataFrame(items)
        category = dimension if dimension in frame.columns else "segment"
        rate = "d1_7_window"
        fig = px.bar(
            frame,
            x=category,
            y=rate,
            color=category,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
        dataframe(items)

with right:
    st.subheader("整体变化分解")
    effects = [
        float(decomposition.get("structure_effect", 0)),
        float(decomposition.get("within_effect", 0)),
        float(decomposition.get("interaction_effect", 0)),
    ]
    fig = go.Figure(
        go.Waterfall(
            x=["结构效应", "组内效应", "交互项"],
            y=effects,
            connector={"line": {"color": COLORS["muted"]}},
        )
    )
    fig.update_layout(height=390, yaxis_tickformat=".1%", margin=dict(t=20, l=20, r=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    dataframe(decomposition.get("items", []))

st.subheader("新用户首次使用路径")
steps = funnel.get("steps", [])
if steps:
    frame = pd.DataFrame(steps)
    fig = px.funnel(frame, y="step", x="uv", color_discrete_sequence=[COLORS["cyan"]])
    st.plotly_chart(fig, use_container_width=True)
    dataframe(steps)

conclusion = (
    decomposition.get("conclusion")
    or "整体变化需要同时检查人群结构和各分组自身留存，不能仅凭总计指标下结论。"
)
note(str(conclusion), "success")
note(
    "若各路径步骤没有明显恶化，结论应是“当前没有证据表明留存下降主要由首次使用路径卡点造成”，而不是“已经证明路径没有问题”。",
    "warning",
)
