from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import dataframe
from frontend.style import COLORS, note, page_header

page_header(
    "Reusable analytical operating system",
    "GROWTH 数据分析决策方法论",
    "把一次项目复盘沉淀为可复用的个人分析操作系统：先治理目标与口径，再定位、解释、验证和决策。",
)

try:
    model = api_get("/methodology")
except APIError as exc:
    st.error(str(exc))
    st.stop()

st.markdown("### 一条主线，六道关口")
stage_labels = {
    "G": "目标与指标",
    "R": "可信度闸门",
    "O": "机会定位",
    "W": "机制假设",
    "T": "因果检验",
    "H": "价值与沉淀",
}
columns = st.columns(6)
for column, stage in zip(columns, model.get("stages", []), strict=False):
    with column:
        st.markdown(f"## {stage['code']}")
        st.markdown(f"**{stage_labels.get(stage['code'], stage['name'])}**")
        st.caption(stage["question"])

st.caption("G → R → O → W → T → H。任何前置关口未通过，结论强度都不能越级。")

for stage in model.get("stages", []):
    with st.expander(
        f"{stage['code']} · {stage_labels.get(stage['code'], stage['name'])} — {stage['name']}"
    ):
        st.markdown(f"**关键问题：** {stage['question']}")
        left, middle, right = st.columns(3)
        with left:
            st.markdown("**必须产出**")
            for value in stage.get("outputs", []):
                st.markdown(f"- {value}")
        with middle:
            st.markdown("**可选方法**")
            for value in stage.get("methods", []):
                st.markdown(f"- {value}")
        with right:
            st.markdown("**常见误区**")
            for value in stage.get("failure_modes", []):
                st.markdown(f"- {value}")
        note(stage.get("project_mapping", ""), "success")

st.markdown("### 证据等级：你的结论到底能说多重")
ladder = pd.DataFrame(model.get("evidence_ladder", []))
if not ladder.empty:
    fig = px.scatter(
        ladder,
        x="level",
        y=[1] * len(ladder),
        size=[18 + value * 4 for value in ladder["level"]],
        color="level",
        text="name",
        color_continuous_scale=[[0, COLORS["muted"]], [0.5, COLORS["cyan"]], [1, COLORS["blue"]]],
    )
    fig.update_traces(textposition="top center", marker={"line": {"width": 2, "color": "white"}})
    fig.update_yaxes(visible=False)
    fig.update_xaxes(dtick=1, title="证据等级")
    fig.update_layout(
        height=280, showlegend=False, coloraxis_showscale=False, margin=dict(t=55, b=35, l=20, r=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    dataframe(
        ladder.rename(
            columns={
                "level": "等级",
                "name": "阶段",
                "question": "必须回答",
                "claim_allowed": "可以声称",
                "cannot_claim": "仍不能声称",
            }
        ).to_dict("records")
    )

note(
    "漏斗、分层和 Mix-Shift 把问题定位到证据等级 2；用户研究形成等级 3 的机制假设；可靠随机实验才把结论推进到等级 4。",
    "warning",
)

st.markdown("### 权威方法来源与适用边界")
for source in model.get("sources", []):
    with st.container(border=True):
        st.markdown(
            f"**[{source['title']}]({source['url']})** · {source['organization']} · {source['year']}"
        )
        st.write(source["used_for"])
        st.caption(f"边界：{source['boundary']}")

st.markdown("### 两类项目如何统一到一套能力")
mapping = [
    {
        "能力": "目标拆解",
        "老带新项目": "最终拉新 → 邀请CTR机制指标 → LTV/CAC护栏",
        "留存项目": "窗口留存 → 分层/路径/功能机制",
    },
    {
        "能力": "异动定位",
        "老带新项目": "版本漏斗与最早实质断点",
        "留存项目": "结构、组内与交互项分解",
    },
    {
        "能力": "业务解释",
        "老带新项目": "激励强度与UI认知成本的权衡",
        "留存项目": "设备结构变化与产品功能发现",
    },
    {"能力": "因果验证", "老带新项目": "简化邀请界面随机实验", "留存项目": "功能发现引导随机实验"},
    {
        "能力": "决策质量",
        "老带新项目": "SRM/均衡/新奇/网络效应/ROI",
        "留存项目": "口径/成熟队列/护栏/相关性边界",
    },
    {
        "能力": "工程沉淀",
        "老带新项目": "SQL、API、看板、实验引擎",
        "留存项目": "分解引擎、工作台、测试、知识库",
    },
]
dataframe(mapping)
