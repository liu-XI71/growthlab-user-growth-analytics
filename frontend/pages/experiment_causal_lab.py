from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import (
    as_number,
    as_percent,
    growth_gate,
    render_decision_card,
    render_kpis,
)
from frontend.style import COLORS, note, page_header

page_header(
    "Randomization → health → effect → decision",
    "实验与因果评估中心",
    "默认使用 assignment denominator 的固定期 ITT；实际曝光仅是诊断，不能通过事后筛选替代随机化。",
)

experiment_id = "referral_ui_simplification"
try:
    health = api_get(f"/experiments/{experiment_id}/health")
    effects = api_get(f"/experiments/{experiment_id}/effects")
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "T→H",
    "随机实验 ITT；分层结果带区间与多重比较标记",
    "用户级区间没有消除社交网络干扰；网络/地域簇随机化是后续识别路线。",
)

primary = effects.get("primary_metric", {})
quality = effects.get("quality_adjusted_effects", {})
render_kpis(
    [
        ("对照组邀请点击", as_percent(primary.get("control_rate")), None),
        ("实验组邀请点击", as_percent(primary.get("treatment_rate")), None),
        ("绝对提升", f"{float(primary.get('absolute_uplift_pp', 0)):.2f} pp", None),
        ("P 值", f"{float(primary.get('p_value', 1)):.3g}", None),
        ("每万分流增量D7", f"{float(quality.get('d7_retained', {}).get('estimate', 0)):.1f}", None),
    ]
)

tab_design, tab_health, tab_itt, tab_time, tab_segments, tab_decision = st.tabs(
    ["预注册", "实验健康度", "固定期 ITT", "新奇效应", "分层效果", "决策卡"]
)

with tab_design:
    st.markdown("#### Estimand Registry")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "字段": "业务问题",
                    "定义": "简化邀请页并将 CTA 放到首屏，是否提升高质量拉新？",
                },
                {"字段": "随机化单位", "定义": "user_id；稳定 SHA-256 hash 1:1 分流"},
                {"字段": "Primary estimand", "定义": "Intention-to-treat / assignment denominator"},
                {"字段": "机制指标", "定义": "邀请点击率"},
                {"字段": "最终指标", "定义": "每万分流增量D7、D1-7留存与Contribution30"},
                {"字段": "周期", "定义": "固定14天；价值随访独立要求30天"},
                {
                    "字段": "MDE",
                    "定义": f"{float(effects.get('decision_basis', {}).get('sample_plan', {}).get('mde_absolute', 0)) * 100:.1f} pp",
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    note(
        "Triggered / exposed 分析是 post-assignment 子集。它可以诊断界面实际触达，但存在选择偏差，不能替代 ITT 上线结论。",
        "warning",
    )

with tab_health:
    flow = pd.DataFrame(health.get("flow", []))
    if not flow.empty:
        melted = flow.melt(
            id_vars="group_name",
            value_vars=["assigned", "exposed", "observable"],
            var_name="stage",
            value_name="users",
        )
        fig = px.bar(
            melted,
            x="stage",
            y="users",
            color="group_name",
            barmode="group",
            color_discrete_map={"control": COLORS["muted"], "treatment": COLORS["blue"]},
            labels={"stage": "Assignment → Exposure → Observable", "users": "用户数"},
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    srm = health.get("overall_srm", {})
    cols = st.columns(3)
    cols[0].metric("SRM", "PASS" if srm.get("pass") is True else "FAIL/UNKNOWN")
    cols[1].metric("SRM P值", f"{float(srm.get('p_value') or 0):.4f}")
    cols[2].metric("SMD门槛", f"|SMD| ≤ {float(health.get('smd_threshold', 0.1)):.2f}")
    smd_rows = []
    for dimension in health.get("pre_treatment_balance", []):
        for item in dimension.get("items", []):
            smd_rows.append({"dimension": dimension.get("dimension"), **item})
    smd_frame = pd.DataFrame(smd_rows)
    if not smd_frame.empty:
        smd_frame["label"] = smd_frame["dimension"] + " / " + smd_frame["category"]
        fig = px.bar(
            smd_frame,
            x="smd",
            y="label",
            orientation="h",
            color="pass",
            color_discrete_map={True: COLORS["green"], False: COLORS["red"]},
            labels={"smd": "One-hot pre-treatment SMD", "label": "协变量"},
        )
        fig.add_vline(x=-0.1, line_dash="dash", line_color=COLORS["amber"])
        fig.add_vline(x=0.1, line_dash="dash", line_color=COLORS["amber"])
        fig.update_layout(height=460, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    triggered = health.get("triggered_diagnostic", {})
    note(
        triggered.get("selection_bias_warning", "Triggered analysis has selection bias."), "warning"
    )

with tab_itt:
    estimate = float(primary.get("absolute_uplift", 0))
    fig = go.Figure(
        go.Scatter(
            x=[estimate],
            y=["邀请点击率 ITT"],
            mode="markers",
            marker={"size": 16, "color": COLORS["blue"]},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": [float(primary.get("ci_upper", estimate)) - estimate],
                "arrayminus": [estimate - float(primary.get("ci_lower", estimate))],
            },
        )
    )
    fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"])
    fig.update_xaxes(tickformat=".1%")
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)
    metrics = [
        quality.get("d7_retained", {}),
        quality.get("d1_7_window_retained", {}),
        quality.get("contribution30", {}),
    ]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "指标": item.get("metric_name"),
                    "估计": item.get("estimate"),
                    "对照/每万": item.get("control_value"),
                    "实验/每万": item.get("treatment_value"),
                    "分母": item.get("denominator_type"),
                    "观察窗": item.get("window"),
                    "单位": item.get("unit"),
                }
                for item in metrics
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    cost_metric = quality.get("cost_per_incremental_d7", {})
    note(
        f"Cost per incremental D7 retained user：{as_number(cost_metric.get('value')) if cost_metric.get('status') == 'available' else '不可用'}。{cost_metric.get('reason') or ''}",
        "success" if cost_metric.get("status") == "available" else "warning",
    )

with tab_time:
    week_frame = pd.DataFrame(effects.get("week_slices", []))
    if not week_frame.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=week_frame["week"],
                y=week_frame["absolute_uplift"],
                mode="lines+markers",
                line={"color": COLORS["blue"], "width": 3},
                marker={"size": 10},
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": week_frame["ci_upper"] - week_frame["absolute_uplift"],
                    "arrayminus": week_frame["absolute_uplift"] - week_frame["ci_lower"],
                },
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"])
        fig.update_yaxes(tickformat=".1%", title="邀请点击率 ITT 提升")
        fig.update_xaxes(dtick=1, title="实验周")
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
    note(effects.get("week_slice_warning", "时间切片仅用于稳定性诊断。"), "warning")

with tab_segments:
    segment_frame = pd.DataFrame(effects.get("segment_effects", []))
    if not segment_frame.empty:
        segment_frame["label"] = (
            segment_frame["dimension"]
            + " / "
            + segment_frame["segment"]
            + " / "
            + segment_frame["classification"]
        )
        fig = go.Figure(
            go.Scatter(
                x=segment_frame["absolute_uplift"],
                y=segment_frame["label"],
                mode="markers",
                marker={"size": 9, "color": COLORS["blue"]},
                error_x={
                    "type": "data",
                    "symmetric": False,
                    "array": segment_frame["ci_upper"] - segment_frame["absolute_uplift"],
                    "arrayminus": segment_frame["absolute_uplift"] - segment_frame["ci_lower"],
                },
                customdata=segment_frame[["adjusted_p_value", "multiplicity_method"]],
                hovertemplate="%{y}<br>effect=%{x:.2%}<br>BH p=%{customdata[0]:.3g}<extra></extra>",
            )
        )
        fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"])
        fig.update_xaxes(tickformat=".1%", title="Treatment − Control")
        fig.update_layout(height=560, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    note(
        effects.get("segment_claim_boundary", "分层显著性差异不等于显著的分层效果差异。"), "warning"
    )

with tab_decision:
    render_decision_card(effects.get("decision_card", {}))
    basis = effects.get("decision_basis", {})
    left, right = st.columns(2)
    left.markdown("#### 样本与周期")
    left.json({"sample_plan": basis.get("sample_plan"), "timing": basis.get("timing")})
    right.markdown("#### 护栏与成熟度")
    right.json(
        {"guardrail": basis.get("guardrail"), "outcome_maturity": basis.get("outcome_maturity")}
    )
