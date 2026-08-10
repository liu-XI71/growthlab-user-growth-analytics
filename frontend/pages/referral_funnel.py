from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import as_number, as_percent, dataframe, explain_result, render_kpis
from frontend.style import COLORS, page_header

page_header(
    "Referral growth",
    "老带新漏斗与版本诊断",
    "比较激励与界面迭代，定位增长链路中真正发生变化的环节。",
)

try:
    version_payload = api_get("/referral/versions")
    versions = version_payload.get("versions", [])
except APIError as exc:
    st.error(str(exc))
    st.stop()

labels = {item.get("version"): item.get("label", item.get("version")) for item in versions}
selected = (
    st.selectbox("活动版本", list(labels), format_func=lambda key: labels.get(key, key))
    if labels
    else "variant_c"
)

try:
    summary = api_get("/referral/summary", {"version": selected})
    funnel = api_get("/referral/funnel", {"version": selected})
except APIError as exc:
    st.error(str(exc))
    st.stop()

kpis = summary.get("kpis", {})
render_kpis(
    [
        ("页面点击率", as_percent(kpis.get("page_click_rate")), None),
        ("邀请点击率", as_percent(kpis.get("invite_click_rate")), None),
        ("分享成功率", as_percent(kpis.get("share_success_rate")), None),
        ("曝光到激活裂变率", as_percent(kpis.get("activation_per_exposure")), None),
        ("激活新用户", as_number(kpis.get("new_user_activate_uv")), None),
    ]
)

steps = funnel.get("steps", [])
if steps:
    frame = pd.DataFrame(steps)
    fig = px.funnel(frame, y="step", x="uv", color_discrete_sequence=[COLORS["blue"]])
    fig.update_layout(height=480, margin=dict(t=20, l=20, r=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    dataframe(steps)

st.subheader("版本对比")
comparison = []
for item in versions:
    row = {"版本": item.get("label", item.get("version"))}
    row.update({key: value for key, value in item.items() if key not in {"label", "version"}})
    comparison.append(row)
dataframe(comparison)

insight = summary.get("insight", summary.get("diagnosis", {}))
if isinstance(insight, dict):

    def join_text(value: object, fallback: str) -> str:
        if isinstance(value, list):
            return "\n\n".join(f"- {item}" for item in value)
        return str(value or fallback)

    st.subheader("诊断结论")
    explain_result(
        join_text(insight.get("facts"), "漏斗数据已计算，重点检查邀请点击环节。"),
        join_text(
            insight.get("interpretations", insight.get("interpretation")),
            "变化发生在邀请动作之前，后续分享链路相对稳定。",
        ),
        join_text(
            insight.get("hypotheses", insight.get("hypothesis")),
            "页面信息密度和核心 CTA 位置可能提高了操作成本。",
        ),
        join_text(
            insight.get("actions", insight.get("action")), "简化界面并通过用户级随机实验验证。"
        ),
    )
