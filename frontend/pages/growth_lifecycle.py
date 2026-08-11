from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import explain_result, growth_gate
from frontend.style import COLORS, note, page_header

page_header(
    "Acquisition → retention → value",
    "增长生命周期与获客质量",
    "把 inviter→invitee 身份、激活、精确留存、30日价值和全部可变成本连接到同一用户。",
)

source_labels = {
    "all": "全部已激活邀请用户",
    "randomized_experiment": "随机实验拉新",
    "descriptive_campaign": "历史活动版本（描述性）",
}
source_kind = st.selectbox(
    "生命周期来源",
    list(source_labels),
    format_func=lambda value: source_labels[value],
)

try:
    summary = api_get("/lifecycle/summary")
    cohorts = api_get("/lifecycle/cohorts", {"source_kind": source_kind})
    quality = api_get("/lifecycle/acquisition-quality")
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "O→H",
    "身份级生命周期 + 成熟 Cohort；版本比较仅描述性",
    quality.get("claim_boundary", "只有随机实验端点可以使用 causal/incremental 标签。"),
)

st.subheader("同一批用户的完整生命周期")
steps = summary.get("lifecycle", [])
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
    fig.update_layout(height=440, margin=dict(l=25, r=25, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
note(
    "主决策分母是 eligible assignment（合格且已随机分流）；tracked exposure 是 post-assignment 诊断分母，不能替代 ITT。",
    "warning",
)

left, right = st.columns([1.15, 1])
with left:
    st.subheader("获客质量矩阵")
    quality_frame = pd.DataFrame(quality.get("items", []))
    if not quality_frame.empty:
        quality_frame["cost_per_acquired"] = (
            quality_frame["total_variable_acquisition_cost"] / quality_frame["acquired_users"]
        )
        quality_frame["label"] = (
            quality_frame["acquisition_campaign"].astype(str)
            + " / "
            + quality_frame["acquisition_treatment"].astype(str)
        )
        fig = px.scatter(
            quality_frame,
            x="cost_per_acquired",
            y="d7_retention",
            size="acquired_users",
            color="average_ltv_cac",
            hover_name="label",
            hover_data=["d1_7_window_retention", "total_contribution30"],
            color_continuous_scale="Blues",
            labels={
                "cost_per_acquired": "每名获客全部可变成本",
                "d7_retention": "精确D7留存",
                "average_ltv_cac": "平均LTV/CAC",
            },
        )
        fig.update_yaxes(tickformat=".1%")
        fig.update_layout(height=430, margin=dict(l=15, r=15, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("为什么数量不是终点")
    st.markdown(
        """
        - **规模**：真正激活了多少邀请用户？
        - **质量**：这些用户是否在精确 D7 / D1-7 窗口返回？
        - **价值**：offset 0..29 的价值扣除服务与全部获客可变成本后还剩多少？
        - **因果**：差异来自随机分配，还是版本时期与人群结构？
        """
    )
    explain_result(
        "历史活动版本可以比较获客量、成熟留存和平均经济性。",
        "高转化但低留存或高成本的来源，不一定贡献高质量增长。",
        "简化界面可能同时影响邀请规模与最终留存用户规模。",
        "用随机实验 ITT 的每万分流增量留存和增量贡献决定是否上线。",
        "历史版本不同时上线，版本间差异不得称作增量或因果效果。",
    )

st.subheader("成熟 Cohort：分子、分母与删失同时可见")
cohort_frame = pd.DataFrame(cohorts.get("items", []))
if not cohort_frame.empty:
    cohort_frame["cohort_week"] = pd.to_datetime(cohort_frame["cohort_week"])
    fig = px.line(
        cohort_frame,
        x="cohort_week",
        y=["d7_retention", "d1_7_window_retention", "d30_retention"],
        color="cohort_variant",
        markers=True,
        labels={"value": "留存率", "cohort_week": "激活周", "variable": "留存口径"},
    )
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(height=420, margin=dict(l=15, r=15, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    display_columns = [
        "cohort_week",
        "source_kind",
        "cohort_variant",
        "activated_users",
        "retained_d7_users",
        "mature_d7_users",
        "retained_d1_7_window_users",
        "retained_d30_users",
        "mature_d30_users",
        "immature_d30_users",
        "as_of_date",
    ]
    st.dataframe(cohort_frame[display_columns], use_container_width=True, hide_index=True)
st.caption(cohorts.get("maturity_rule", "未成熟 cohort 不被记作未留存。"))
