from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get, api_post
from frontend.components import as_percent, dataframe, explain_result, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Bring your own aggregate data",
    "通用分析工作台",
    "不上传用户明细：使用聚合漏斗和分层留存数据复用同一套诊断引擎，并生成有边界的分析结论。",
)

router_tab, funnel_tab, mix_tab, memo_tab = st.tabs(
    ["问题路由器", "漏斗诊断器", "Mix-Shift 分解", "结论备忘录"]
)

with router_tab:
    try:
        playbooks = api_get("/methodology/playbooks").get("items", [])
    except APIError as exc:
        st.error(str(exc))
        playbooks = []
    if playbooks:
        labels = {item["id"]: item["name"] for item in playbooks}
        selected = st.selectbox(
            "你现在需要解决什么问题？", list(labels), format_func=lambda key: labels[key]
        )
        item = next(value for value in playbooks if value["id"] == selected)
        note(f"触发场景：{item['trigger']}")
        st.markdown("#### 建议分析路线")
        route = item.get("route", [])
        st.progress(0.01, text=" → ".join(route))
        columns = st.columns(len(route))
        for index, (column, value) in enumerate(zip(columns, route, strict=False), start=1):
            column.markdown(f"**{index:02d}**")
            column.caption(value)
        left, right = st.columns(2)
        with left:
            st.markdown("**最小交付物**")
            for value in item.get("minimum_output", []):
                st.markdown(f"- {value}")
        with right:
            st.markdown("**停止线**")
            note(item.get("stop_rule", ""), "warning")

with funnel_tab:
    st.markdown("#### 输入同口径的基准期与当前期 UV")
    funnel_default = pd.DataFrame(
        [
            {"step": "活动曝光", "baseline_uv": 100_000, "current_uv": 100_000},
            {"step": "活动访问", "baseline_uv": 77_000, "current_uv": 77_000},
            {"step": "点击邀请", "baseline_uv": 19_250, "current_uv": 13_090},
            {"step": "成功分享", "baseline_uv": 17_710, "current_uv": 12_040},
            {"step": "新用户到达", "baseline_uv": 8_680, "current_uv": 5_900},
            {"step": "新用户激活", "baseline_uv": 5_900, "current_uv": 4_010},
        ]
    )
    funnel_input = st.data_editor(
        funnel_default,
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        key="custom_funnel",
    )
    material_pp = st.slider("实质性断点阈值（百分点）", 0.5, 10.0, 2.0, 0.5)
    if st.button("运行漏斗诊断", type="primary", use_container_width=True):
        try:
            result = api_post(
                "/workbench/funnel",
                {"steps": funnel_input.to_dict("records"), "material_threshold": material_pp / 100},
            )
        except APIError as exc:
            st.error(str(exc))
        else:
            comparison = result["comparison"]
            frame = pd.DataFrame(comparison)
            chart = frame.melt(
                id_vars="step",
                value_vars=["baseline_conversion", "current_conversion"],
                var_name="period",
                value_name="conversion",
            )
            fig = px.bar(
                chart,
                x="step",
                y="conversion",
                color="period",
                barmode="group",
                color_discrete_map={
                    "baseline_conversion": COLORS["muted"],
                    "current_conversion": COLORS["blue"],
                },
            )
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            diagnosis = result["diagnosis"]
            facts = "\n\n".join(diagnosis.get("facts", []))
            interpretations = "\n\n".join(diagnosis.get("interpretations", []))
            hypotheses = "\n\n".join(diagnosis.get("hypotheses", []))
            actions = "\n\n".join(diagnosis.get("actions", []))
            explain_result(facts, interpretations, hypotheses, actions)
            note(result["claim_boundary"], "warning")
            dataframe(comparison)

with mix_tab:
    st.markdown("#### 输入各分层在两个时期的人数与留存率")
    mix_default = pd.DataFrame(
        [
            {
                "segment": "手机",
                "baseline_users": 70_000,
                "current_users": 58_000,
                "baseline_rate": 0.47,
                "current_rate": 0.465,
            },
            {
                "segment": "平板",
                "baseline_users": 18_000,
                "current_users": 25_000,
                "baseline_rate": 0.405,
                "current_rate": 0.398,
            },
            {
                "segment": "电视",
                "baseline_users": 12_000,
                "current_users": 17_000,
                "baseline_rate": 0.39,
                "current_rate": 0.382,
            },
        ]
    )
    mix_input = st.data_editor(
        mix_default,
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        key="custom_mix",
        column_config={
            "baseline_rate": st.column_config.NumberColumn(
                format="%.1%%", min_value=0.0, max_value=1.0
            ),
            "current_rate": st.column_config.NumberColumn(
                format="%.1%%", min_value=0.0, max_value=1.0
            ),
        },
    )
    if st.button("运行结构—表现分解", type="primary", use_container_width=True):
        try:
            result = api_post("/workbench/mix-shift", {"rows": mix_input.to_dict("records")})
        except APIError as exc:
            st.error(str(exc))
        else:
            render_kpis(
                [
                    ("基准总留存", as_percent(result["baseline_rate"]), None),
                    ("当前总留存", as_percent(result["current_rate"]), None),
                    ("总变化", f"{result['total_change'] * 100:+.2f} pp", None),
                    ("结构效应", f"{result['structure_effect'] * 100:+.2f} pp", None),
                    ("组内效应", f"{result['within_effect'] * 100:+.2f} pp", None),
                ]
            )
            effects = [
                result["structure_effect"],
                result["within_effect"],
                result["interaction_effect"],
            ]
            fig = go.Figure(
                go.Waterfall(
                    x=["结构效应", "组内效应", "交互项"],
                    y=effects,
                    connector={"line": {"color": COLORS["muted"]}},
                    increasing={"marker": {"color": COLORS["green"]}},
                    decreasing={"marker": {"color": COLORS["red"]}},
                )
            )
            fig.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)
            note(result["claim_boundary"], "warning")
            dataframe(result["items"])

with memo_tab:
    st.markdown("#### 用统一结构约束分析表达")
    evidence_level = st.select_slider(
        "当前证据等级",
        options=[0, 1, 2, 3, 4, 5],
        value=2,
        format_func=lambda value: [
            "口径",
            "可信观察",
            "定位",
            "机制假设",
            "因果识别",
            "决策与耐久性",
        ][value],
    )
    fact = st.text_area(
        "已确认事实", "当前期相较基准期，最大且最早的实质转化下滑集中在邀请点击环节。"
    )
    interpretation = st.text_area(
        "合理解释", "问题更可能发生在邀请动作之前或当下，而非分享平台跳转之后。"
    )
    hypothesis = st.text_area("待验证假设", "信息密度增加、主按钮下移提高了认知和操作成本。")
    action = st.text_area("建议动作", "先核验埋点与人群结构，再随机测试首屏突出主CTA的简化版本。")
    limitation = st.text_area(
        "局限与反证", "漏斗定位不证明UI是原因；若A/A、SRM或护栏异常，应停止上线判断。"
    )
    st.markdown("#### 决策备忘录预览")
    st.markdown(
        f"""
**证据等级：{evidence_level}/5**

**事实**
{fact}

**解释**
{interpretation}

**假设**
{hypothesis}

**动作**
{action}

**局限 / 反证条件**
{limitation}
"""
    )
    if evidence_level < 4:
        note("当前证据不足以声称因果效果；建议使用随机实验或明确假设的准实验继续推进。", "warning")
