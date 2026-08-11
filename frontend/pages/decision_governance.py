from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get
from frontend.components import explain_result, growth_gate
from frontend.style import COLORS, note, page_header

page_header(
    "Metric contract → evidence → decision",
    "决策与证据治理",
    "让每个指标可追溯到口径、SQL、数据源、证据等级、决策和复盘边界。",
)

try:
    metrics = api_get("/metrics").get("items", [])
    decisions = api_get("/decisions")
    quality = api_get("/data-quality/status")
except APIError as exc:
    st.error(str(exc))
    st.stop()

growth_gate(
    "R→H",
    f"指标合同 + {quality.get('check_count', 0)}项数据质量 + 决策日志",
    "描述性、诊断、相关性和随机因果证据分层保存；每一级只做其证据允许的主张。",
)

cols = st.columns(4)
cols[0].metric("治理指标", len(metrics))
cols[1].metric("最新DQ", str(quality.get("status", "unknown")).upper())
cols[2].metric("质量检查", quality.get("check_count", 0))
cols[3].metric("决策记录", decisions.get("count", 0))

tab_lineage, tab_decisions, tab_quality, tab_catalog = st.tabs(
    ["指标血缘与SQL", "决策日志", "数据质量", "指标合同目录"]
)

with tab_lineage:
    metric_names = [str(item.get("metric_name")) for item in metrics]
    default_name = "incremental_d7_retained_per_10k_assigned"
    default_index = metric_names.index(default_name) if default_name in metric_names else 0
    selected = st.selectbox("选择指标合同", metric_names, index=default_index)
    try:
        lineage = api_get(f"/metrics/{selected}/lineage")
    except APIError as exc:
        st.error(str(exc))
    else:
        contract = lineage.get("metric", {})
        st.markdown(f"### {contract.get('display_name_zh', selected)}")
        st.caption(contract.get("description", ""))
        contract_cols = st.columns(3)
        contract_cols[0].metric("指标类型", contract.get("metric_type", "—"))
        contract_cols[1].metric("粒度", contract.get("grain", "—"))
        unit = str(contract.get("unit", "—"))
        unit_labels = {
            "users_per_10k_assigned": "用户 / 每万分流",
            "normalized_value_per_10k_assigned": "价值 / 每万分流",
            "normalized_cost_per_incremental_d7_retained_user": "成本 / 增量D7用户",
            "ratio": "比率",
            "users": "用户数",
        }
        contract_cols[2].metric("单位", unit_labels.get(unit, unit))
        contract_cols[2].caption(f"API unit: `{unit}`")
        st.code(str(contract.get("formula", "")), language="sql")
        nodes = lineage.get("lineage", [])
        if nodes:
            stage_labels = {
                "source": "1  Source facts · 来源事实",
                "mart": "2  User-value mart · 用户价值宽表",
                "metric_contract": "3  Governed metric · 治理指标",
                "decision": "4  Decision evidence · 决策证据",
            }
            short_labels = [
                stage_labels.get(str(item.get("node")), f"{index + 1}  Lineage step")
                for index, item in enumerate(nodes)
            ]
            technical_labels = [str(item.get("label", "—")) for item in nodes]
            y_positions = list(reversed(range(len(nodes))))
            stage_colors = [
                COLORS["navy"],
                COLORS["blue"],
                COLORS["cyan"],
                COLORS["green"],
            ]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=[0] * len(nodes),
                    y=y_positions,
                    mode="lines",
                    line={"color": "rgba(47,107,255,.30)", "width": 5},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[0] * len(nodes),
                    y=y_positions,
                    mode="markers+text",
                    text=short_labels,
                    textposition="middle right",
                    customdata=technical_labels,
                    hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
                    marker={
                        "size": 30,
                        "color": [
                            stage_colors[index % len(stage_colors)] for index in range(len(nodes))
                        ],
                        "line": {"color": "white", "width": 3},
                    },
                    showlegend=False,
                )
            )
            fig.update_xaxes(visible=False, range=[-0.15, 1.1], fixedrange=True)
            fig.update_yaxes(
                visible=False,
                range=[-0.5, max(len(nodes) - 0.5, 0.5)],
                fixedrange=True,
            )
            fig.update_layout(
                height=max(360, 90 * len(nodes)),
                margin=dict(l=60, r=30, t=15, b=15),
                hoverlabel={"align": "left"},
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("纵向展示决策血缘；悬停节点查看完整 API 技术定义。")
            with st.expander("查看完整技术血缘（API 原始字段）"):
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "step": item.get("order", index + 1),
                                "node": item.get("node", "—"),
                                "technical_lineage": item.get("label", "—"),
                            }
                            for index, item in enumerate(nodes)
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
        st.markdown("#### SQL evidence")
        st.code(str(lineage.get("sql_evidence")), language="text")
        note(
            str(contract.get("claim_boundary", "只有与识别策略一致的结果可以做因果主张。")),
            "warning",
        )

with tab_decisions:
    decision_items = decisions.get("items", [])
    if decision_items:
        labels = {
            str(
                item.get("decision_id")
            ): f"{item.get('decision_date')} · {item.get('business_question')}"
            for item in decision_items
        }
        selected_decision = st.selectbox(
            "选择决策记录", list(labels), format_func=lambda value: labels[value]
        )
        item = next(
            row for row in decision_items if str(row.get("decision_id")) == selected_decision
        )
        st.markdown(
            f"**Decision：** `{item.get('decision')}`　 **Evidence：** `{item.get('evidence_level')}`　 **GROWTH：** `{item.get('growth_stage')}`"
        )
        explain_result(
            str(item.get("fact")),
            str(item.get("interpretation")),
            str(item.get("hypothesis")),
            str(item.get("action")),
            str(item.get("limitation")),
        )
        st.dataframe(
            pd.DataFrame(decision_items),
            use_container_width=True,
            hide_index=True,
            column_config={"decision_id": st.column_config.TextColumn("Decision ID")},
        )
    st.markdown("#### 证据阶梯")
    st.dataframe(
        pd.DataFrame(decisions.get("evidence_ladder", [])),
        use_container_width=True,
        hide_index=True,
    )

with tab_quality:
    checks = pd.DataFrame(quality.get("checks", []))
    if not checks.empty:
        st.dataframe(
            checks,
            use_container_width=True,
            hide_index=True,
            column_config={
                "status": st.column_config.TextColumn("Status"),
                "observed_value": st.column_config.NumberColumn("Observed", format="%.3f"),
            },
        )
    note(
        "实验决策中的 data_quality gate 读取同一最新检查结果；任何 fail 都会阻断 SHIP。",
        "success" if quality.get("status") == "pass" else "danger",
    )

with tab_catalog:
    catalog = pd.DataFrame(metrics)
    preferred = [
        "metric_name",
        "display_name_zh",
        "metric_type",
        "formula",
        "denominator",
        "grain",
        "decision_use",
        "claim_boundary",
    ]
    st.dataframe(
        catalog[[column for column in preferred if column in catalog]],
        use_container_width=True,
        hide_index=True,
    )
