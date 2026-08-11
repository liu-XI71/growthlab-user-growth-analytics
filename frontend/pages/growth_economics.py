from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get, api_post
from frontend.components import as_number, growth_gate, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Average economics ≠ incremental economics",
    "增长经济学与预算分配",
    "把获客用户平均LTV/CAC与随机实验的增量Contribution30分开；未获客分流用户贡献记0。",
)

try:
    economics = api_get("/economics/summary")
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "H",
    "随机实验 ITT 增量价值 + 描述性获客用户平均经济性",
    economics.get("no_incremental_ltv_cac", "不构造不稳定的 incremental LTV/CAC 比值。"),
)

causal = economics.get("causal_itt_economics", {})
contribution = causal.get("contribution30", {})
d7 = causal.get("d7_retained", {})
cost_d7 = causal.get("cost_per_incremental_d7", {})
uncertainty = contribution.get("uncertainty", {})
render_kpis(
    [
        ("每万增量IC30", as_number(contribution.get("estimate")), None),
        ("IC30为正概率", f"{float(uncertainty.get('probability_positive', 0)) * 100:.1f}%", None),
        ("每万分流增量D7", f"{float(d7.get('estimate', 0)):.1f} 人", None),
        (
            "每增量D7成本",
            as_number(cost_d7.get("value")) if cost_d7.get("status") == "available" else "不可用",
            None,
        ),
        ("默认外推", "关闭", "仅每万标准化"),
    ]
)

left, right = st.columns([1.1, 1])
with left:
    st.subheader("Incremental Contribution30 不确定性")
    estimate = float(contribution.get("estimate", 0))
    lower = float(uncertainty.get("ci_lower", estimate))
    upper = float(uncertainty.get("ci_upper", estimate))
    fig = go.Figure(
        go.Scatter(
            x=[estimate],
            y=["IC30 / 10k assigned"],
            mode="markers",
            marker={"size": 16, "color": COLORS["green"] if estimate > 0 else COLORS["red"]},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": [upper - estimate],
                "arrayminus": [estimate - lower],
            },
        )
    )
    fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"])
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{uncertainty.get('method', '')}；draws={uncertainty.get('draws')}，seed={uncertainty.get('seed')}。"
    )
with right:
    st.subheader("两种经济性不能混用")
    st.markdown(
        """
        **Average LTV/CAC** 只在已获客用户中计算：`ΣLTV30 / Σ全部可变获客成本`，适合描述用户价值与成本结构。

        **Incremental Contribution30** 以全部随机 assignment 为分母，未获客记0，同时捕捉转化规模、用户价值和成本，是上线与资源配置门。
        """
    )
    note(
        "Value30 固定为激活日起 offset 0..29；exact D30 retention 使用 offset=30，两个窗口不会发生 off-by-one 混用。",
        "success",
    )

st.subheader("已获客用户平均经济性（描述性）")
average_frame = pd.DataFrame(economics.get("average_acquired_user_economics", []))
if not average_frame.empty:
    average_frame["label"] = (
        average_frame["acquisition_campaign"].astype(str)
        + " / "
        + average_frame["acquisition_treatment"].astype(str)
    )
    fig = px.bar(
        average_frame,
        x="label",
        y="average_ltv_cac",
        color="acquisition_source",
        hover_data=["acquired_users", "d7_retention", "total_contribution30"],
        labels={"label": "获客来源/处理", "average_ltv_cac": "Average LTV/CAC"},
    )
    fig.add_hline(y=1, line_dash="dash", line_color=COLORS["amber"])
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
note(
    "活动版本跨时期上线，以上版本均值不能写成 causal / incremental；随机实验经济性见页面上方。",
    "warning",
)

st.subheader("预算响应曲线：情景规划，不伪装成已实现收益")
controls = st.columns(3)
elasticity = controls[0].slider("边际响应弹性", 0.50, 1.00, 0.82, 0.02)
explicit_population = controls[1].toggle("显式输入合格人群", value=False)
eligible_population = (
    controls[2].number_input("合格人群", 10_000, 10_000_000, 100_000, 10_000)
    if explicit_population
    else None
)
try:
    scenarios = api_post(
        "/economics/scenarios",
        {
            "budget_multipliers": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
            "response_elasticity": elasticity,
            "eligible_population": eligible_population,
        },
    )
except APIError as exc:
    st.error(str(exc))
else:
    scenario_frame = pd.DataFrame(scenarios.get("items", []))
    if not scenario_frame.empty:
        fig = px.line(
            scenario_frame,
            x="modelled_variable_cost",
            y="modelled_contribution30",
            markers=True,
            hover_data=["budget_multiplier", "modelled_acquired_users", "modelled_ltv_cac"],
            labels={
                "modelled_variable_cost": "模型化可变成本",
                "modelled_contribution30": "模型化Contribution30",
            },
        )
        fig.update_traces(line={"color": COLORS["blue"], "width": 3}, marker={"size": 9})
        fig.update_layout(height=390)
        st.plotly_chart(fig, use_container_width=True)
    note(
        f"{scenarios.get('model_type')}；population basis={scenarios.get('population_basis')}。{scenarios.get('claim_boundary')}",
        "warning",
    )

with st.expander("Break-even 与输入明细"):
    st.dataframe(
        pd.DataFrame(economics.get("break_even", [])), use_container_width=True, hide_index=True
    )
