from __future__ import annotations

from typing import Any

SOURCES: list[dict[str, Any]] = [
    {
        "id": "heart",
        "title": "Measuring the User Experience on a Large Scale: HEART",
        "organization": "Google Research / CHI",
        "year": 2010,
        "url": "https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/",
        "used_for": "Map product goals to signals and governed metrics instead of selecting dashboard KPIs after the fact.",
        "boundary": "HEART is a user-experience metric framework, not a causal identification method.",
    },
    {
        "id": "online_experiments",
        "title": "Online Experimentation at Microsoft",
        "organization": "Microsoft Research",
        "year": 2009,
        "url": "https://www.microsoft.com/en-us/research/publication/online-experimentation-at-microsoft/",
        "used_for": "Treat randomized controlled experiments as a product decision system, not a p-value calculator.",
        "boundary": "Randomization identifies the contrast only when assignment, exposure, telemetry and interference assumptions hold.",
    },
    {
        "id": "srm",
        "title": "Diagnosing Sample Ratio Mismatch in Online Controlled Experiments",
        "organization": "Microsoft Research / KDD",
        "year": 2019,
        "url": "https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners/",
        "used_for": "Use SRM as a high-value symptom of assignment, eligibility, exposure or telemetry problems.",
        "boundary": "Passing SRM is necessary evidence, not proof that every randomization assumption holds.",
    },
    {
        "id": "cuped",
        "title": "Improving the Sensitivity of Online Controlled Experiments Using Pre-Experiment Data",
        "organization": "Microsoft Research / WSDM",
        "year": 2013,
        "url": "https://doi.org/10.1145/2433396.2433413",
        "used_for": "Use pre-period covariates to reduce estimator variance when the covariate is measured before treatment.",
        "boundary": "Variance reduction improves precision; it cannot repair biased assignment or post-treatment adjustment.",
    },
    {
        "id": "kitagawa",
        "title": "Components of a Difference Between Two Rates",
        "organization": "Journal of the American Statistical Association",
        "year": 1955,
        "url": "https://doi.org/10.1080/01621459.1955.10501299",
        "used_for": "Separate an aggregate rate change into composition, within-segment and interaction components.",
        "boundary": "Decomposition attributes an arithmetic change; it does not identify a causal mechanism.",
    },
    {
        "id": "cohort",
        "title": "Cohort exploration",
        "organization": "Google Analytics documentation",
        "year": 2026,
        "url": "https://support.google.com/analytics/answer/9670133?hl=en",
        "used_for": "Make cohort inclusion, return criterion, time grain and calculation type explicit in retention analysis.",
        "boundary": "Different identity, return and window definitions produce different retention metrics.",
    },
    {
        "id": "time_series",
        "title": "Forecasting: Principles and Practice — Time-series decomposition",
        "organization": "OTexts",
        "year": 2026,
        "url": "https://otexts.com/fpp3/decomposition.html",
        "used_for": "Separate trend, seasonality and remainder before treating a point movement as a business anomaly.",
        "boundary": "Anomaly scores prioritize investigation; they are not explanations of the underlying cause.",
    },
    {
        "id": "network_interference",
        "title": "Exact P-values for Network Interference",
        "organization": "NBER / Journal of the American Statistical Association",
        "year": 2018,
        "url": "https://www.nber.org/papers/w21313",
        "used_for": "Recognize that one user's treatment may affect another in referral and social products.",
        "boundary": "Ordinary user-level inference can be invalid when spillovers violate no-interference assumptions.",
    },
]


EVIDENCE_LADDER = [
    {
        "level": 0,
        "name": "Definition",
        "question": "Are we measuring the same business event, population and window?",
        "claim_allowed": "Metric is reproducibly defined.",
        "cannot_claim": "The metric change is real or caused by a product change.",
    },
    {
        "level": 1,
        "name": "Observation",
        "question": "Is the change robust to freshness, missingness, duplication and seasonality?",
        "claim_allowed": "A trustworthy movement occurred in this measured population.",
        "cannot_claim": "Why the movement occurred.",
    },
    {
        "level": 2,
        "name": "Localization",
        "question": "Which funnel step, cohort, segment or mix component contributes most?",
        "claim_allowed": "The change is concentrated at a specific analytical location.",
        "cannot_claim": "The product mechanism at that location is causal.",
    },
    {
        "level": 3,
        "name": "Mechanism hypothesis",
        "question": "Do qualitative evidence, path behavior and product logic support one explanation?",
        "claim_allowed": "The explanation is plausible enough to test.",
        "cannot_claim": "Users would improve if the proposed feature shipped.",
    },
    {
        "level": 4,
        "name": "Causal identification",
        "question": "Does a valid randomized or justified quasi-experimental contrast estimate incrementality?",
        "claim_allowed": "The intervention caused an estimated change for the target population under stated assumptions.",
        "cannot_claim": "The effect is durable, economically worthwhile or universal.",
    },
    {
        "level": 5,
        "name": "Decision and durability",
        "question": "Does the effect clear business, guardrail, economic, heterogeneity and time-stability gates?",
        "claim_allowed": "The action is justified for a defined rollout and monitoring policy.",
        "cannot_claim": "Future cohorts and contexts will behave identically.",
    },
]


STAGES = [
    {
        "code": "G",
        "name": "Goal & governed metrics",
        "question": "What business decision are we enabling, and how does the top-line outcome decompose?",
        "outputs": [
            "OEC / north-star outcome",
            "metric tree",
            "primary metric",
            "guardrails",
            "metric contracts",
        ],
        "methods": [
            "goal → signal → metric mapping",
            "numerator/denominator/grain governance",
            "leading/lagging metric separation",
        ],
        "failure_modes": [
            "metric chosen because it is easy to move",
            "one ambiguous retention or ROI label",
            "dashboard without a decision owner",
        ],
        "project_mapping": "Referral activations are the final outcome; invite CTR is the mechanism metric; first-month LTV/CAC is the guardrail.",
    },
    {
        "code": "R",
        "name": "Reliability gate",
        "question": "Can the movement be trusted before anyone explains it?",
        "outputs": [
            "freshness/volume/uniqueness checks",
            "event-order invariants",
            "SRM",
            "A/A",
            "population balance",
        ],
        "methods": [
            "data contracts",
            "instrumentation triangulation",
            "sample-ratio test",
            "pre-treatment balance",
        ],
        "failure_modes": [
            "interpreting a tracking break",
            "ignoring late events",
            "treating a passing SRM as complete proof",
        ],
        "project_mapping": "GrowthLab blocks experiment decisions when assignment, sample, duration or telemetry quality is not credible.",
    },
    {
        "code": "O",
        "name": "Opportunity localization",
        "question": "Where is the change generated and how much does each component contribute?",
        "outputs": [
            "time trend",
            "funnel breakpoint",
            "segment table",
            "cohort view",
            "mix-shift decomposition",
        ],
        "methods": [
            "trend/seasonality/remainder",
            "ordered funnel",
            "cohort retention",
            "Kitagawa-style decomposition",
            "contribution ranking",
        ],
        "failure_modes": [
            "only comparing totals",
            "confusing mix with within-segment deterioration",
            "selecting a segment after seeing a favorable result",
        ],
        "project_mapping": "Referral loss localizes to invite click; retention decline is separated into device mix, within-device performance and interaction.",
    },
    {
        "code": "W",
        "name": "Why hypothesis & evidence",
        "question": "What is fact, what is interpretation, and what remains a testable mechanism?",
        "outputs": [
            "fact list",
            "alternative explanations",
            "product hypothesis",
            "qualitative research question",
            "evidence level",
        ],
        "methods": [
            "fact → interpretation → hypothesis → action",
            "negative evidence / exclusion",
            "correlation-to-causality ladder",
        ],
        "failure_modes": [
            "turning a correlation into a recommendation",
            "claiming a stable funnel proves no UX problem",
            "one-story confirmation bias",
        ],
        "project_mapping": "Dense copy and a displaced CTA are hypotheses supported by the localized break and research, then validated through randomization.",
    },
    {
        "code": "T",
        "name": "Test causally",
        "question": "What estimand, assignment, sample, duration and inference identify incremental impact?",
        "outputs": [
            "pre-registration",
            "MDE/power/sample",
            "stable hash allocation",
            "A/A",
            "effect/CI/p-value",
            "segment effects",
        ],
        "methods": [
            "randomized A/B",
            "two-proportion inference",
            "CUPED when valid",
            "cluster assignment for interference",
            "DID/PSM with explicit assumptions",
        ],
        "failure_modes": [
            "peeking and optional stopping",
            "post-treatment adjustment",
            "network spillover",
            "statistical significance as the only gate",
        ],
        "project_mapping": "Invite UI and feature-discovery treatments use fixed-horizon experiments with SRM, balance and business thresholds.",
    },
    {
        "code": "H",
        "name": "Harvest value & learning",
        "question": "Should we ship, to whom, at what cost, and what will we learn after rollout?",
        "outputs": [
            "ship/iterate/stop decision",
            "LTV/CAC and net ROI",
            "sensitivity",
            "rollout policy",
            "monitoring and knowledge record",
        ],
        "methods": [
            "dual statistical/business gates",
            "unit economics",
            "sensitivity analysis",
            "staged rollout",
            "decision log",
        ],
        "failure_modes": [
            "calling LTV/CAC net ROI",
            "ignoring effect decay",
            "average win harming a critical segment",
            "no post-launch learning",
        ],
        "project_mapping": "A positive click effect is not enough: new-user value, retention, novelty, interference and economics determine rollout.",
    },
]


PLAYBOOKS: dict[str, dict[str, Any]] = {
    "metric_anomaly": {
        "name": "核心指标异动",
        "trigger": "DAU、拉新、留存或商业化指标偏离预期",
        "route": [
            "口径/数据质量",
            "趋势与季节性",
            "贡献拆解",
            "人群/渠道分层",
            "机制假设",
            "策略评估",
        ],
        "minimum_output": ["异动是否真实", "开始时间", "贡献最大的组件", "影响人群", "下一步验证"],
        "stop_rule": "数据口径、延迟或埋点未通过时，停止业务归因。",
    },
    "referral_funnel": {
        "name": "老带新增长诊断",
        "trigger": "外部拉新空间下降，需要提升内部裂变效率",
        "route": ["指标树", "版本漏斗", "最早实质断点", "UI/激励假设", "A/A→A/B", "质量与ROI护栏"],
        "minimum_output": [
            "最终拉新与机制指标",
            "断点及量级",
            "替代解释",
            "实验设计",
            "单位经济性",
        ],
        "stop_rule": "只看到总裂变率变化、未定位链路时，不直接修改激励或界面。",
    },
    "retention_decline": {
        "name": "新用户留存下滑",
        "trigger": "精确日或窗口留存低于基准",
        "route": [
            "留存口径",
            "cohort成熟度",
            "渠道/设备/地域分层",
            "Mix-Shift",
            "上手漏斗排除",
            "功能假设",
            "随机验证",
        ],
        "minimum_output": ["结构/组内/交互贡献", "被排除的原因", "候选机制", "因果验证方案"],
        "stop_rule": "标杆用户功能渗透差异只能形成假设，不能直接形成因果结论。",
    },
    "experiment_decision": {
        "name": "产品策略实验评估",
        "trigger": "需要判断策略是否全量上线",
        "route": [
            "估计目标",
            "指标与护栏",
            "MDE/样本/周期",
            "Hash与A/A",
            "SRM/均衡",
            "固定周期推断",
            "业务/经济门槛",
        ],
        "minimum_output": [
            "绝对/相对提升",
            "置信区间",
            "p值",
            "业务阈值",
            "护栏",
            "设计完整性",
            "决策",
        ],
        "stop_rule": "任一数据可信、样本、周期、SRM或关键护栏门槛失败时，不返回上线。",
    },
    "unit_economics": {
        "name": "增长单位经济性",
        "trigger": "策略提升增长但增加成本",
        "route": [
            "价值窗口",
            "增量成本归因",
            "LTV/CAC",
            "净ROI",
            "外部基准",
            "敏感性",
            "成熟队列回测",
        ],
        "minimum_output": ["公式与假设", "点估计", "盈亏平衡点", "关键敏感参数", "回测计划"],
        "stop_rule": "价值和成本不在同一归因边界、同一窗口时，不比较比率。",
    },
}


def framework() -> dict[str, Any]:
    return {
        "name": "GROWTH Decision OS",
        "description": "A reusable analytical operating system from a governed goal to trustworthy evidence, causal testing and an economically defensible decision.",
        "stages": STAGES,
        "evidence_ladder": EVIDENCE_LADDER,
        "sources": SOURCES,
        "synthetic_data": True,
    }


def list_playbooks() -> dict[str, Any]:
    return {"items": [{"id": key, **value} for key, value in PLAYBOOKS.items()]}


def get_playbook(playbook_id: str) -> dict[str, Any]:
    try:
        return {"id": playbook_id, **PLAYBOOKS[playbook_id]}
    except KeyError as error:
        raise LookupError(f"Unknown methodology playbook: {playbook_id}") from error
