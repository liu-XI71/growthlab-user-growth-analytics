from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import dataframe, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Trust before interpretation",
    "数据质量、口径治理与可复现性",
    "业务解释必须建立在可信数据之上：把唯一性、完整性、时序、范围、分流和隐私做成自动化闸门。",
)

try:
    health = api_get("/health")
    quality = api_get("/data-quality/status")
    metrics = api_get("/metrics")
except APIError as exc:
    st.error(str(exc))
    st.stop()

checks = quality.get("checks", [])
passed = sum(item.get("status") == "pass" for item in checks)
render_kpis(
    [
        ("API 状态", str(health.get("status", "unknown")).upper(), None),
        ("数据库", str(health.get("database", "unknown")).upper(), None),
        ("质量检查", f"{passed}/{len(checks)}", None),
        ("治理指标", metrics.get("count", 0), None),
        ("敏感信息", "PUBLIC-SAFE", None),
    ]
)

if quality.get("status") == "pass":
    note(
        "所有内建数据质量检查通过；这允许进入业务诊断，但不替代对指标含义和因果假设的审查。",
        "success",
    )
else:
    note("质量闸门失败：停止业务归因和实验上线判断，先修复数据。", "danger")

st.subheader("自动化质量闸门")
if checks:
    frame = pd.DataFrame(checks)
    status_counts = frame["status"].value_counts().rename_axis("status").reset_index(name="checks")
    fig = px.bar(
        status_counts,
        x="status",
        y="checks",
        color="status",
        color_discrete_map={"pass": COLORS["green"], "fail": COLORS["red"]},
    )
    fig.update_layout(height=260, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    dataframe(checks)

st.subheader("质量模型：检查什么，失败后做什么")
taxonomy = [
    {
        "维度": "完整性",
        "例子": "用户、事件、周期、指标定义是否齐全",
        "失败动作": "检查上游任务、过滤条件和迟到数据",
    },
    {
        "维度": "唯一性",
        "例子": "user_id、event_id、实验分组是否重复",
        "失败动作": "停止UV、漏斗和实验分析",
    },
    {
        "维度": "合法性",
        "例子": "留存率范围、成本非负、桶号与组名合法",
        "失败动作": "定位生成/清洗/枚举映射",
    },
    {
        "维度": "时序性",
        "例子": "事件不得早于注册，结果不得早于实验分流",
        "失败动作": "检查时区、回填和事件时间",
    },
    {
        "维度": "关系一致",
        "例子": "漏斗单调、实验一人一组、分子不大于分母",
        "失败动作": "检查身份去重和口径边界",
    },
    {
        "维度": "实验可信",
        "例子": "A/A、SRM、渠道/设备/地域均衡",
        "失败动作": "修复分流、曝光或埋点后重跑",
    },
    {
        "维度": "隐私发布",
        "例子": "公司标识、内部规模、密钥和大文件扫描",
        "失败动作": "阻断公开发布",
    },
]
dataframe(taxonomy)

st.subheader("从数据到决策的可审计链路")
layers = [
    ("01", "Generate", "固定 seed 的脱敏模拟用户、事件与实验"),
    ("02", "Store", "DuckDB 明细、汇总视图与 SQL 模型"),
    ("03", "Govern", "指标合同、白名单维度与质量检查"),
    ("04", "Analyze", "漏斗、留存、分解、ROI 与实验统计"),
    ("05", "Serve", "FastAPI 类型校验与统一 JSON 契约"),
    ("06", "Decide", "Streamlit 证据、解释、风险与决策"),
]
columns = st.columns(3)
for index, (number, title, description) in enumerate(layers):
    with columns[index % 3].container(border=True):
        st.caption(number)
        st.markdown(f"**{title}**")
        st.write(description)

note(
    "公开仓库不提交生成后的 DuckDB 文件；任何人都能用相同 seed 重建数据并复现测试、API 与看板。",
    "warning",
)
