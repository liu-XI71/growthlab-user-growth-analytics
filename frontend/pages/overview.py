from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import as_number, as_percent, dataframe, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Growth operating system",
    "增长总览与指标树",
    "把 DAU 目标拆解到新增、裂变漏斗、留存和单位经济性；所有结果均为模拟或标准化数据。",
)

try:
    versions = api_get("/referral/versions").get("versions", [])
    kpis = versions[-1] if versions else {}
    retention = api_get("/retention/summary", {"period": "current"})
    trend_payload = api_get("/growth/trend", {"metric": "dau_index"})
    tree = api_get("/metrics/tree")
    metrics = api_get("/metrics").get("items", [])
except APIError as exc:
    st.error(str(exc))
    st.stop()

latest = trend_payload.get("latest", {})
latest_dau = float(latest.get("dau_index", 0))
target = float(latest.get("target_index", 80))
render_kpis(
    [
        ("当前 DAU 指数", f"{latest_dau:.1f}", f"距目标 {latest_dau - target:+.1f}"),
        ("老带新激活", as_number(kpis.get("new_user_activate_uv")), None),
        ("裂变率", as_percent(kpis.get("activation_per_exposure")), None),
        ("D1-7 窗口留存", as_percent(retention.get("d1_7_window")), None),
        ("邀请点击率", as_percent(kpis.get("invite_click_rate")), None),
    ]
)

st.subheader("目标进度与增长来源")
trend_frame = pd.DataFrame(trend_payload.get("items", []))
if not trend_frame.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend_frame["date"],
            y=trend_frame["dau_index"],
            mode="lines",
            name="每日 DAU 指数",
            line={"color": COLORS["cyan"], "width": 1.5},
            opacity=0.55,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_frame["date"],
            y=trend_frame["trend_7d"],
            mode="lines",
            name="7日趋势",
            line={"color": COLORS["blue"], "width": 3},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_frame["date"],
            y=trend_frame["target_index"],
            mode="lines",
            name="季度目标指数",
            line={"color": COLORS["amber"], "width": 2, "dash": "dash"},
        )
    )
    anomalies = trend_frame[trend_frame["is_anomaly"]]
    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(
                x=anomalies["date"],
                y=anomalies["dau_index"],
                mode="markers",
                name="待调查异常",
                marker={"color": COLORS["red"], "size": 9, "symbol": "diamond"},
            )
        )
    fig.update_layout(height=410, margin=dict(t=20, l=20, r=20, b=20), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    note(trend_payload.get("claim_boundary", "异常分数用于优先排查，不直接解释原因。"), "warning")

    component_frame = pd.DataFrame(trend_payload.get("components", []))
    if not component_frame.empty:
        component_labels = {
            "external_new_index": "外部拉新",
            "organic_new_index": "自然新增",
            "referral_new_index": "老带新",
            "retained_user_index": "存量留存",
        }
        component_frame["增长来源"] = component_frame["component"].map(component_labels)
        fig = px.bar(
            component_frame,
            x="增长来源",
            y="change",
            color="change",
            color_continuous_scale=[[0, COLORS["red"]], [0.5, "#E8EDF5"], [1, COLORS["green"]]],
            title="最近14日相对最初14日的组件变化",
        )
        fig.update_layout(height=330, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("业务指标树")
children = tree.get("children", [])
if children:
    rows: list[dict[str, object]] = []

    def walk(node: dict[str, object], parent: str = "") -> None:
        name = str(node.get("name", "metric"))
        rows.append(
            {
                "指标": name,
                "父指标": parent or "DAU目标",
                "值": node.get("value"),
                "单位": node.get("unit"),
            }
        )
        for child in node.get("children", []) or []:
            walk(child, name)

    for child in children:
        walk(child, str(tree.get("name", "DAU目标")))
    frame = pd.DataFrame(rows)
    tree_values = pd.to_numeric(frame["值"], errors="coerce").fillna(1.0).abs() + 1
    fig = px.treemap(
        frame,
        path=["父指标", "指标"],
        values=tree_values,
        color_discrete_sequence=[COLORS["blue"], COLORS["cyan"], COLORS["green"]],
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=430)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("指标树数据正在初始化。")

left, right = st.columns([1.25, 1])
with left:
    st.subheader("指标字典")
    dataframe(metrics)
with right:
    st.subheader("分析纪律")
    note("先确认指标口径和数据质量，再解释波动；漏斗定位提供证据，但不能单独证明产品改版是原因。")
    note("相关性分析用于提出假设；随机实验用于识别增量因果效果。", "warning")
    note("统计显著不等于业务显著：同时报告绝对提升、相对提升、置信区间、护栏和成本。", "success")
