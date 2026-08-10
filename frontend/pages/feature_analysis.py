from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import dataframe
from frontend.style import COLORS, note, page_header

page_header(
    "Correlation → causality",
    "核心功能：从标杆用户差异到随机实验",
    "功能渗透差异用于提出假设；只有可靠的随机实验才能识别增量因果效果。",
)

try:
    result = api_get("/feature-analysis")
except APIError as exc:
    st.error(str(exc))
    st.stop()

st.subheader("标杆用户定义")
st.write(result.get("benchmark_definition", "首月活跃天数和日均使用时长均处于高分位的用户。"))

items = result.get("items", [])
if items:
    frame = pd.DataFrame(items)
    label = next(
        (c for c in ["benchmark_user", "segment", "group", "user_type"] if c in frame.columns),
        frame.columns[0],
    )
    measures = [c for c in frame.select_dtypes("number").columns if c != label]
    value = "feature_penetration" if "feature_penetration" in frame.columns else measures[0]
    fig = px.bar(
        frame,
        x=label,
        y=value,
        color=label,
        color_discrete_sequence=[COLORS["blue"], COLORS["amber"]],
    )
    if "rate" in value:
        fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    dataframe(items)

note(
    str(
        result.get(
            "causality_warning", "观察到功能使用与留存相关，并不意味着功能使用导致留存提升。"
        )
    ),
    "warning",
)

st.subheader("为什么不能直接下因果结论")
columns = st.columns(3)
columns[0].markdown("**自选择偏差**\n\n原本就更喜欢产品的用户，更可能主动使用保存功能。")
columns[1].markdown("**共同原因**\n\n渠道、设备和兴趣强度可能同时影响功能使用与留存。")
columns[2].markdown("**反向因果**\n\n高活跃可能带来更多功能使用，而不是功能使用带来高活跃。")

st.subheader("下一步证据")
note(
    "以 user_id 为随机化单位，实验组展示保存引导、对照组保持原体验；预注册 D1-7 窗口留存为核心指标，并监控弹窗关闭率、首日时长和内容消费等护栏。",
    "success",
)
