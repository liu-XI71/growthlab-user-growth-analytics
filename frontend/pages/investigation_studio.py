from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import as_percent, explain_result, growth_gate, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Diagnose before proposing",
    "增长诊断工作台",
    "用漏斗断点、Mix-Shift 和真实路径证据定位问题；把事实、解释与待验证机制严格分开。",
)

dimensions = {
    "device_type": "设备类型",
    "channel": "渠道",
    "region": "地域",
    "product_version": "产品版本",
}
sources = {
    "all": "全部新用户",
    "non_referral": "非邀请新增",
    "referral_campaign": "历史老带新",
    "referral_experiment": "实验老带新",
}
filter_columns = st.columns(3)
dimension = filter_columns[0].selectbox(
    "留存拆解维度", list(dimensions), format_func=lambda value: dimensions[value]
)
source = filter_columns[1].selectbox(
    "路径来源", list(sources), format_func=lambda value: sources[value]
)

try:
    versions = api_get("/referral/versions").get("versions", [])
    version_ids = [str(item.get("version")) for item in versions]
    selected_version = filter_columns[2].selectbox(
        "历史活动版本", version_ids, index=max(0, len(version_ids) - 1)
    )
    funnel = api_get(
        "/referral/funnel",
        {"version": selected_version, "baseline_version": "variant_a"},
    )
    mix_shift = api_get("/investigation/mix-shift", {"dimension": dimension})
    paths = api_get("/investigation/paths", {"acquisition_source": source})
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "O→W",
    "描述性定位 + 机制假设",
    "漏斗、分解和路径可以定位损失与提出机制，但不能单独证明产品改版造成变化。",
)

tab_funnel, tab_mix, tab_paths = st.tabs(["漏斗断点", "结构与组内拆解", "用户路径证据"])

with tab_funnel:
    steps = funnel.get("steps", [])
    diagnosis = funnel.get("diagnosis", {})
    step_labels = {
        "campaign_exposure": "活动曝光",
        "campaign_click": "活动访问",
        "invite_click": "访问→邀请点击",
        "share_success": "邀请→分享成功",
        "new_user_landing": "分享→新用户落地",
        "new_user_register": "落地→新用户注册",
        "new_user_activate": "注册→新用户激活",
    }
    short_step_labels = {
        "campaign_exposure": "活动曝光",
        "campaign_click": "曝光→访问",
        "invite_click": "访问→邀请",
        "share_success": "邀请→分享",
        "new_user_landing": "分享→落地",
        "new_user_register": "落地→注册",
        "new_user_activate": "注册→激活",
    }
    primary_step = str(diagnosis.get("primary_step", "待定位"))
    render_kpis(
        [
            ("分析版本", selected_version, None),
            ("主要断点", short_step_labels.get(primary_step, primary_step), None),
            ("影响强度", as_percent(diagnosis.get("rate_change")), None),
            ("证据类型", "Descriptive", None),
        ]
    )
    if steps:
        frame = pd.DataFrame(steps)
        fig = go.Figure(
            go.Funnel(
                y=frame["step"],
                x=frame["uv"],
                textinfo="value+percent previous",
                marker={"color": COLORS["blue"]},
            )
        )
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    comparison = pd.DataFrame(funnel.get("comparison", []))
    if not comparison.empty:
        fig = px.bar(
            comparison,
            x="step",
            y="absolute_change",
            color="absolute_change",
            color_continuous_scale=[[0, COLORS["red"]], [0.5, "#E8EDF5"], [1, COLORS["green"]]],
            labels={"absolute_change": "相对基线环节转化变化", "step": "环节"},
        )
        fig.update_yaxes(tickformat=".1%")
        fig.update_layout(height=320, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    explain_result(
        f"版本 {selected_version} 的主要漏损集中在 {step_labels.get(primary_step, primary_step)}。",
        "界面信息层级和 CTA 可发现性是与断点一致的产品解释。",
        "把邀请按钮放回首屏会提升邀请点击，并进一步增加激活新用户。",
        "预注册随机实验，在固定周期内同时检查机制、最终质量和经济性。",
        "版本分时上线，不能排除时期、渠道结构与奖励策略等替代解释。",
    )

with tab_mix:
    render_kpis(
        [
            ("基线D1-7留存", as_percent(mix_shift.get("baseline_rate")), None),
            ("当前D1-7留存", as_percent(mix_shift.get("current_rate")), None),
            ("总变化", f"{float(mix_shift.get('total_change', 0)) * 100:+.2f} pp", None),
            ("结构效应", f"{float(mix_shift.get('structure_effect', 0)) * 100:+.2f} pp", None),
            ("组内效应", f"{float(mix_shift.get('within_effect', 0)) * 100:+.2f} pp", None),
        ]
    )
    total_components = pd.DataFrame(
        [
            {"effect": "结构变化", "value": mix_shift.get("structure_effect", 0)},
            {"effect": "组内变化", "value": mix_shift.get("within_effect", 0)},
            {"effect": "交互项", "value": mix_shift.get("interaction_effect", 0)},
        ]
    )
    fig = go.Figure(
        go.Waterfall(
            x=total_components["effect"],
            y=total_components["value"],
            measure=["relative", "relative", "relative"],
            connector={"line": {"color": "#A9B8CA"}},
            increasing={"marker": {"color": COLORS["green"]}},
            decreasing={"marker": {"color": COLORS["red"]}},
        )
    )
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    contribution = pd.DataFrame(mix_shift.get("items", []))
    if not contribution.empty:
        fig = px.bar(
            contribution,
            x="segment",
            y="total_contribution",
            color="total_contribution",
            color_continuous_scale="RdBu",
            labels={"segment": dimensions[dimension], "total_contribution": "对总留存变化贡献"},
        )
        fig.update_yaxes(tickformat=".1%")
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    note(
        f"重构误差 {float(mix_shift.get('reconciliation_error', 0)):.2e}；结构、组内和交互项精确还原总体变化。",
        "success",
    )

with tab_paths:
    path_frame = pd.DataFrame(paths.get("items", []))
    if not path_frame.empty:
        path_frame["path_short"] = path_frame["path_signature"].str.slice(0, 62)
        fig = px.bar(
            path_frame.sort_values("users"),
            x="users",
            y="path_short",
            orientation="h",
            color="d1_7_window_retention",
            color_continuous_scale="Tealgrn",
            labels={"users": "用户数", "path_short": "路径", "d1_7_window_retention": "D1-7留存"},
        )
        fig.update_layout(height=500, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    note(paths.get("claim_boundary", "路径用于定位，不用于因果归因。"), "warning")
