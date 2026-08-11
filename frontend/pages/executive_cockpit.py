from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import (
    as_number,
    growth_gate,
    render_decision_card,
    render_kpis,
)
from frontend.style import COLORS, note, page_header

page_header(
    "Executive decision cockpit",
    "增长质量与因果决策驾驶舱",
    "用一条可审计证据链回答：目标差距在哪里、策略是否真正带来高质量增量用户、是否值得上线。",
)

try:
    lifecycle = api_get("/lifecycle/summary")
    effects = api_get("/experiments/referral_ui_simplification/effects")
    decisions = api_get("/decisions")
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "G→H",
    "随机实验 ITT + 描述性生命周期证据",
    lifecycle.get("claim_boundary", "每万合格分流用户是默认决策分母；实际曝光仅用于诊断。"),
)

goal = lifecycle.get("goal", {})
primary = effects.get("primary_metric", {})
quality = effects.get("quality_adjusted_effects", {})
d7 = quality.get("d7_retained", {})
window = quality.get("d1_7_window_retained", {})
contribution = quality.get("contribution30", {})
render_kpis(
    [
        (
            "当前 DAU 指数",
            f"{float(goal.get('current_dau_index', 0)):.1f}",
            f"距目标 {float(goal.get('gap_index', 0)):+.1f}",
        ),
        ("邀请点击 ITT 提升", f"{float(primary.get('absolute_uplift_pp', 0)):.2f} pp", None),
        ("每万分流增量D7", f"{float(d7.get('estimate', 0)):.1f} 人", None),
        ("每万分流增量D1-7", f"{float(window.get('estimate', 0)):.1f} 人", None),
        ("每万分流增量贡献30", as_number(contribution.get("estimate")), None),
    ]
)

st.subheader("60 秒管理层答案")
decision = effects.get("decision_card", {})
failed = decision.get("failed_or_unknown_gates", [])
stories = [
    (
        "01 目标",
        f"DAU 目标指数 {goal.get('target_dau_index')}；当前差距 {float(goal.get('gap_index', 0)):+.1f}。",
    ),
    ("02 定位", "外部获客承压后，老带新成为可控增长杠杆；关键机制断点是邀请点击。"),
    ("03 策略", "简化邀请页信息层级，把核心 CTA 放回首屏，降低行动发现成本。"),
    ("04 可信度", "默认 ITT 保留全部随机分流用户；A/A、SRM、SMD、样本、周期、成熟度逐门检查。"),
    (
        "05 价值",
        f"每万合格分流用户带来 {float(d7.get('estimate', 0)):.1f} 个增量D7留存用户，并计入全部可变成本。",
    ),
    (
        "06 决策",
        f"{decision.get('decision', 'REVIEW')}；未通过门：{', '.join(failed) if failed else '无'}。",
    ),
]
cards = "".join(
    f'<div class="gl-story-card"><b>{escape(title)}</b><span>{escape(text)}</span></div>'
    for title, text in stories
)
st.markdown(f'<div class="gl-story-grid">{cards}</div>', unsafe_allow_html=True)

left, right = st.columns([1.35, 1])
with left:
    st.subheader("一条用户生命周期，而不是两张独立看板")
    steps = lifecycle.get("lifecycle", [])
    if steps:
        labels = [str(item.get("label")) for item in steps]
        values = [int(item.get("users", 0)) for item in steps]
        fig = go.Figure(
            go.Funnel(
                y=labels,
                x=values,
                textinfo="value+percent initial+percent previous",
                marker={
                    "color": [
                        COLORS["navy"],
                        COLORS["blue"],
                        COLORS["cyan"],
                        COLORS["green"],
                        "#6F7BF7",
                        COLORS["amber"],
                    ]
                },
            )
        )
        fig.update_layout(height=430, margin=dict(l=20, r=20, t=15, b=15))
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("固定期 ITT 效果与区间")
    interval = primary
    estimate = float(interval.get("absolute_uplift", 0))
    fig = go.Figure(
        go.Scatter(
            x=[estimate],
            y=["邀请点击率"],
            mode="markers",
            marker={"size": 15, "color": COLORS["blue"]},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": [float(interval.get("ci_upper", estimate)) - estimate],
                "arrayminus": [estimate - float(interval.get("ci_lower", estimate))],
            },
        )
    )
    fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"])
    fig.update_xaxes(tickformat=".1%", title="Treatment − Control")
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    note(
        "机制指标用于灵敏定位；最终决策同时要求增量留存、Incremental Contribution30、护栏和全部治理门通过。",
        "success",
    )

st.subheader("上线决策卡")
render_decision_card(decision)

with st.expander("3 分钟 Guided Flow", expanded=False):
    flow = pd.DataFrame(lifecycle.get("guided_flow", []))
    if not flow.empty:
        flow = flow.rename(
            columns={"minute": "时间", "gate": "GROWTH Gate", "question": "演示问题"}
        )
        st.dataframe(flow, use_container_width=True, hide_index=True)
    latest_decision = (decisions.get("items") or [{}])[0]
    st.markdown("#### 最终一句话")
    st.write(
        latest_decision.get("action", "在可信实验结果和经济性门槛共同通过后上线，并持续监控。")
    )
    st.caption(latest_decision.get("limitation", "所有公开结果均为隐私安全模拟数据。"))
