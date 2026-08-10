from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIError, api_get, api_post
from frontend.components import as_percent, dataframe, render_kpis
from frontend.style import COLORS, note, page_header

page_header(
    "Experiment operating procedure",
    "A/A 与 A/B 实验评估中心",
    "从目标、指标和样本量开始，经过 Hash 分流、A/A、均衡性与 SRM 检查，最后同时判断统计和业务显著性。",
)

steps = [
    "目标与策略",
    "指标与护栏",
    "样本量与周期",
    "Hash分流",
    "A/A与均衡",
    "A/B执行",
    "显著性与决策",
]
st.progress(1.0, text=" → ".join(steps))

try:
    experiments = api_get("/experiments").get("items", [])
except APIError as exc:
    st.error(str(exc))
    st.stop()

experiment_ids = [
    item.get("id", item.get("experiment_id", f"experiment-{idx}"))
    for idx, item in enumerate(experiments)
]
labels = {
    item.get("id", item.get("experiment_id", f"experiment-{idx}")): item.get(
        "name", item.get("label", "实验")
    )
    for idx, item in enumerate(experiments)
}
selected = (
    st.selectbox("选择预置实验", experiment_ids, format_func=lambda value: labels.get(value, value))
    if experiment_ids
    else "invite_ui_simplification"
)
meta = next(
    (item for item in experiments if item.get("id", item.get("experiment_id")) == selected), {}
)
groups = {str(item.get("group_name")): item for item in meta.get("groups", [])}
control_group = groups.get("control", {})
treatment_group = groups.get("treatment", {})

tab_design, tab_aa, tab_ab, tab_risks = st.tabs(
    ["实验设计", "A/A 与分流", "A/B 结果", "风险与决策纪律"]
)

with tab_design:
    left, right = st.columns(2)
    with left:
        st.markdown("#### 1. 目标策略与目的")
        st.write(meta.get("strategy", "简化邀请界面，将核心邀请按钮放在首屏。"))
        st.write(meta.get("objective", "提升老用户邀请点击率，最终提高成功激活的新用户数。"))
        st.markdown("#### 2. 指标")
        st.markdown("**核心指标：** 邀请点击率")
        st.markdown("**最终业务指标：** 成功激活的新用户数")
        st.markdown("**护栏指标：** 新用户首月 LTV/CAC")
        st.markdown("**相关指标：** 裂变率、人均邀请、新用户访问频次、新用户留存")
    with right:
        st.markdown("#### 3. 最小样本与周期")
        baseline = st.number_input(
            "历史邀请点击率",
            0.01,
            0.90,
            float(meta.get("baseline_rate", 0.17)),
            0.01,
            format="%.2f",
        )
        mde_pp = st.number_input(
            "业务 MDE（百分点）", 0.1, 20.0, float(meta.get("mde_absolute", 0.03)) * 100, 0.5
        )
        alpha = st.number_input("显著性水平 α", 0.001, 0.20, float(meta.get("alpha", 0.05)), 0.01)
        power = st.number_input("统计功效 Power", 0.50, 0.99, float(meta.get("power", 0.80)), 0.05)
        daily_sample = st.number_input(
            "每日可进入实验样本",
            100,
            10_000_000,
            int(meta.get("daily_eligible_users", 50_000)),
            1000,
        )
        st.caption("周期取 max(样本量÷每日样本量, 完整业务周)，并预留新奇效应观察窗口。")

with tab_aa:
    st.markdown("#### 4. 稳定 Hash 分流")
    st.code(
        "bucket = stable_hash(user_id, experiment_salt) % 100\nexperiment: 0–49 | control: 50–99"
    )
    st.write("相同 user_id 在整个实验周期内保持固定分组；实验盐隔离不同实验。")
    st.markdown("#### 5. A/A 预检")
    st.write("在相同体验下检查邀请点击率是否出现显著差异，同时检查埋点、口径、SRM 和关键人群分布。")
    note(
        "若 A/A 异常：先排查分流、埋点和指标口径并重跑；无法随机化时，DID/PSM 只能作为有额外假设的替代识别策略。",
        "warning",
    )
    st.markdown("#### 辛普森悖论与分层均衡")
    st.write(
        "实验前后检查渠道、城市、设备等构成；同时报告总体和分层结果，防止总计结论被人群结构反转。"
    )

with tab_ab:
    st.markdown("#### 6. 输入聚合实验结果")
    columns = st.columns(4)
    control_n = columns[0].number_input(
        "对照组样本", 100, 10_000_000, int(control_group.get("users", 100_000)), 1000
    )
    treatment_n = columns[1].number_input(
        "实验组样本", 100, 10_000_000, int(treatment_group.get("users", 100_000)), 1000
    )
    control_rate = columns[2].number_input(
        "对照组邀请点击率",
        0.0,
        1.0,
        float(control_group.get("primary_rate", baseline)),
        0.001,
        format="%.3f",
    )
    treatment_rate = columns[3].number_input(
        "实验组邀请点击率",
        0.0,
        1.0,
        float(treatment_group.get("primary_rate", min(1.0, baseline + mde_pp / 100))),
        0.001,
        format="%.3f",
    )
    guardrails = st.columns(2)
    guardrail_control = guardrails[0].number_input(
        "护栏：对照组首月 LTV/CAC",
        0.0,
        10.0,
        float(control_group.get("guardrail_value", 2.0)),
        0.05,
    )
    guardrail_treatment = guardrails[1].number_input(
        "护栏：实验组首月 LTV/CAC",
        0.0,
        10.0,
        float(treatment_group.get("guardrail_value", 2.0)),
        0.05,
    )
    st.caption(f"业务显著阈值与预注册 MDE 保持一致：{mde_pp:.1f} 个百分点。")
    run = st.button("完成预注册检查并评估实验", type="primary", use_container_width=True)

    if run:
        payload = {
            "experiment_id": selected,
            "baseline_rate": baseline,
            "mde_absolute": mde_pp / 100,
            "alpha": alpha,
            "power": power,
            "eligible_users_per_day": daily_sample,
            "control_n": control_n,
            "treatment_n": treatment_n,
            "control_successes": int(round(control_n * control_rate)),
            "treatment_successes": int(round(treatment_n * treatment_rate)),
            "minimum_full_weeks": 2,
            "guardrails": [
                {
                    "name": "new_user_first_month_ltv_cac",
                    "control_value": guardrail_control,
                    "treatment_value": guardrail_treatment,
                    "desired_direction": "higher",
                    "tolerance": 0.03,
                }
            ],
        }
        try:
            result = api_post("/experiments/analyze", payload)
        except APIError as exc:
            st.error(str(exc))
        else:
            ab = result.get("ab", result.get("result", result))
            srm = result.get("balance", {}).get("overall_srm", ab.get("srm", {}))
            required = result.get(
                "required_sample_per_group",
                result.get("design", {}).get("required_sample_per_group"),
            )
            render_kpis(
                [
                    ("对照组", as_percent(ab.get("rates", {}).get("control", control_rate)), None),
                    (
                        "实验组",
                        as_percent(ab.get("rates", {}).get("treatment", treatment_rate)),
                        None,
                    ),
                    (
                        "绝对提升",
                        f"{float(ab.get('absolute_uplift_pp', (treatment_rate - control_rate) * 100)):.2f} pp",
                        None,
                    ),
                    (
                        "相对提升",
                        f"{float(ab.get('relative_uplift_pct', ((treatment_rate / control_rate) - 1) * 100 if control_rate else math.nan)):.2f}%",
                        None,
                    ),
                    ("P 值", f"{float(ab.get('p_value', math.nan)):.4g}", None),
                ]
            )
            status_cols = st.columns(4)
            status_cols[0].metric("所需每组样本", f"{int(required):,}" if required else "—")
            status_cols[1].metric(
                "SRM", "通过" if srm.get("pass", srm.get("passed", True)) else "异常"
            )
            status_cols[2].metric(
                "统计显著",
                "是" if ab.get("stat_significant", ab.get("significant", False)) else "否",
            )
            status_cols[3].metric(
                "业务显著", "是" if ab.get("business_significant", False) else "否"
            )

            ci = ab.get("confidence_interval_absolute", {})
            if isinstance(ci, dict) and {"lower", "upper"}.issubset(ci):
                fig = go.Figure()
                estimate = float(ab.get("absolute_uplift", treatment_rate - control_rate))
                fig.add_trace(
                    go.Scatter(
                        x=[estimate],
                        y=["邀请点击率差"],
                        mode="markers",
                        marker={"size": 14, "color": COLORS["blue"]},
                        error_x={
                            "type": "data",
                            "symmetric": False,
                            "array": [float(ci["upper"]) - estimate],
                            "arrayminus": [estimate - float(ci["lower"])],
                        },
                    )
                )
                fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"])
                fig.update_xaxes(tickformat=".1%")
                fig.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            st.subheader("实验决策")
            decision = result.get("decision", "需要结合统计显著、业务阈值、护栏和预设周期判断。")
            decision_labels = {
                "launch": "建议上线：统计显著、业务阈值、分流与护栏均通过。",
                "investigate_assignment": "暂不决策：SRM 异常，先排查分流与埋点。",
                "do_not_launch_guardrail_regression": "不建议上线：护栏指标恶化。",
                "continue_or_reassess_business_value": "效果统计显著但未达到业务阈值，需要评估价值或继续迭代。",
                "continue_to_preregistered_end_or_stop_inconclusive": "结论不充分：达到预注册周期和样本后再统一判断。",
                "do_not_launch": "不建议上线：未通过完整决策门槛。",
            }
            decision_text = decision_labels.get(str(decision), str(decision))
            note(decision_text, "success" if decision == "launch" else "warning")
            with st.expander("完整统计输出"):
                st.json(result)

with tab_risks:
    st.markdown("#### 新奇效应")
    st.write(
        "新界面可能因好奇带来短期点击上升；实验至少覆盖完整业务周，并在时间切片中检查效果是否衰减。"
    )
    st.markdown("#### 网络效应")
    st.write(
        "邀请活动可能产生用户间干扰。记录城市/社交关系等聚类维度，必要时采用城市或人群簇级分流，并使用与随机化单位一致的推断。"
    )
    st.markdown("#### 禁止中途偷看后停止")
    st.write(
        "实验过程中持续监控护栏用于安全处置，但最终结论要等预设周期和样本量达到后统一判断；常规 P 值不能用于随看随停。"
    )
    st.markdown("#### 显著性双重门槛")
    dataframe(
        [
            {
                "门槛": "统计显著",
                "要求": "p < α，且置信区间不跨越零；双侧 α=0.05 时大样本 Z 临界值约 ±1.96",
            },
            {
                "门槛": "业务显著",
                "要求": "效果达到预注册 MDE/业务阈值，护栏不恶化，单位经济性可接受",
            },
        ]
    )
    note(
        "只有同时满足数据可信、分流正常、预设周期完成、统计显著、业务显著和护栏可接受，才建议全量上线。",
        "success",
    )
