from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

PROJECT_NAME = "Growth Analytics Decision Platform"
PROJECT_NAME_ZH = "用户增长全链路分析与实验决策平台"


def _case_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": "referral_growth",
                "case_order": 1,
                "title": "老带新获客增长",
                "business_question": "外部拉新供给承压时，如何扩大高质量新增并守住首月价值成本比？",
                "primary_metric": "拉新用户数",
                "mechanism_metric": "邀请点击率",
                "decision_metric": "首月 LTV/CAC",
                "evidence_boundary": "漏斗和版本变化用于定位；随机实验支持页面改版的因果结论。",
            },
            {
                "case_id": "new_user_retention",
                "case_order": 2,
                "title": "新用户留存提升",
                "business_question": "投放带来的新用户为什么留不住，什么产品引导能够提升次7日内留存？",
                "primary_metric": "次7日内留存率",
                "mechanism_metric": "博主主页浏览与关注渗透率",
                "decision_metric": "次7日内留存实验结果",
                "evidence_boundary": "分层、路径和标杆用户用于解释与提出假设；随机实验支持因果结论。",
            },
        ]
    )


def _business_kpis() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": "overview",
                "metric_key": "dau_gap_index",
                "label": "标准化 DAU 目标完成度",
                "value": 81.25,
                "unit": "%",
                "display_value": "81.25%",
                "status": "attention",
                "evidence_type": "normalized narrative",
                "note": "公开版将实际规模标准化为当前81.25、目标100。",
                "display_order": 1,
            },
            {
                "case_id": "referral_growth",
                "metric_key": "invite_click_lift",
                "label": "邀请点击率实验提升",
                "value": 6.5,
                "unit": "pp",
                "display_value": "+6.5 pp",
                "status": "positive",
                "evidence_type": "anonymized experiment narrative",
                "note": "简化页面并将邀请按钮放回首屏：17.0%→23.5%。",
                "display_order": 2,
            },
            {
                "case_id": "new_user_retention",
                "metric_key": "retention_decline",
                "label": "次7日内留存异常",
                "value": -7.0,
                "unit": "pp",
                "display_value": "48% → 41%",
                "status": "negative",
                "evidence_type": "anonymized monitoring narrative",
                "note": "窗口留存：新增后第1至7天内至少再次访问一次。",
                "display_order": 3,
            },
            {
                "case_id": "referral_growth",
                "metric_key": "ltv_cac_guardrail",
                "label": "首月 LTV/CAC",
                "value": 2.18,
                "unit": "x",
                "display_value": "2.18× vs 1.90×",
                "status": "positive",
                "evidence_type": "anonymized economic narrative",
                "note": "老带新版本高于外部投放基准；它是价值成本比，不是净ROI。",
                "display_order": 4,
            },
        ]
    )


def _decision_loop() -> pd.DataFrame:
    rows = [
        (
            1,
            "monitor",
            "监测异常",
            "发生了什么？",
            "外部拉新供给下降，DAU存在目标差距。",
            "次7日内留存率从48%下滑到41%。",
        ),
        (
            2,
            "define",
            "定义指标",
            "什么指标真正代表业务结果？",
            "拉新用户数为核心，邀请点击率为机制指标，首月LTV/CAC为护栏。",
            "次7日内窗口留存为核心，同时观察分层、路径与功能渗透。",
        ),
        (
            3,
            "diagnose",
            "拆解定位",
            "损失发生在哪个环节或人群？",
            "新玩法后邀请点击率从约21%降到17%，主要断点在邀请动作。",
            "平板留存低约10pp且新增占比提高，形成结构性压力。",
        ),
        (
            4,
            "exclude",
            "保留负证据",
            "哪些解释不被数据支持？",
            "分享成功率约95%，分享环节不是主要断点。",
            "下载到关注的主要路径转化稳定，基础使用卡点不是主要解释。",
        ),
        (
            5,
            "hypothesize",
            "提出机制",
            "什么产品机制能解释全部证据？",
            "页面信息过多且CTA位于第二页，提高邀请发现成本。",
            "浏览博主主页并关注可能帮助建立持续内容关系。",
        ),
        (
            6,
            "experiment",
            "实验验证",
            "策略是否真的产生增量效果？",
            "简化页面；两周、百万级脱敏样本，邀请点击率17%→23.5%，p<0.05。",
            "退出页关注引导；两周、约30万样本，次7日内留存显著提升，p<0.05。",
        ),
        (
            7,
            "decide",
            "价值决策",
            "结果是否值得上线并持续治理？",
            "首月LTV/CAC 2.18，高于外部投放1.90，持续迭代。",
            "策略推广并持续优化；未提供的真实绝对提升不在公开版补造。",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "step_order",
            "step_key",
            "label",
            "question",
            "referral_application",
            "retention_application",
        ],
    )


def _referral_versions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "version_id": "baseline",
                "version_order": 1,
                "label": "初始活动版本",
                "invite_click_rate": 0.23,
                "share_success_rate": 0.95,
                "viral_rate": 0.0214,
                "incentive_index": 100.0,
                "ltv_cac": 2.90,
                "decision": "存在增长再投资空间",
                "diagnosis": "策略有效，但增长目标优先，可使用经济性余量扩大拉新。",
            },
            {
                "version_id": "complex_growth",
                "version_order": 2,
                "label": "激励与玩法升级",
                "invite_click_rate": 0.17,
                "share_success_rate": 0.95,
                "viral_rate": 0.029,
                "incentive_index": 160.0,
                "ltv_cac": np.nan,
                "decision": "定位异常并二次改版",
                "diagnosis": "信息增多、重点分散、邀请按钮位于第二页，增加发现成本。",
            },
            {
                "version_id": "simplified_ui",
                "version_order": 3,
                "label": "首屏CTA简化版",
                "invite_click_rate": 0.235,
                "share_success_rate": 0.95,
                "viral_rate": np.nan,
                "incentive_index": 160.0,
                "ltv_cac": 2.18,
                "decision": "上线并持续优化",
                "diagnosis": "简化信息层级并将邀请按钮放回首页。",
            },
        ]
    )


def _referral_funnel() -> pd.DataFrame:
    rates: Mapping[str, list[float]] = {
        "baseline": [1.0, 0.80, 0.23, 0.95, 0.52, 0.82],
        "complex_growth": [1.0, 0.82, 0.17, 0.95, 0.53, 0.82],
        "simplified_ui": [1.0, 0.82, 0.235, 0.95, 0.53, 0.82],
    }
    labels = ["活动曝光", "活动页访问", "点击邀请", "分享成功", "新用户到达", "新用户激活"]
    keys = ["exposure", "visit", "invite_click", "share", "landing", "activation"]
    rows: list[dict[str, object]] = []
    for version, step_rates in rates.items():
        count = 100_000
        for order, (key, label, rate) in enumerate(zip(keys, labels, step_rates, strict=True), 1):
            if order == 1:
                count = 100_000
            else:
                count = round(count * rate)
            rows.append(
                {
                    "version_id": version,
                    "step_order": order,
                    "step_key": key,
                    "step_label": label,
                    "users": count,
                    "conversion_from_previous": rate,
                    "data_status": "synthetic demonstration",
                }
            )
    return pd.DataFrame(rows)


def _retention_trend() -> pd.DataFrame:
    baseline = np.array([0.486, 0.482, 0.480, 0.478, 0.481, 0.476, 0.480])
    current = np.array([0.421, 0.415, 0.409, 0.413, 0.405, 0.412, 0.415])
    rows: list[dict[str, object]] = []
    for week, values in [("下滑前", baseline), ("下滑后", current)]:
        for day, value in enumerate(values, 1):
            rows.append(
                {
                    "period": week,
                    "cohort_day": day,
                    "retention_d1_7_window": value,
                    "data_status": "deterministic synthetic trend calibrated to 48%→41% narrative",
                }
            )
    return pd.DataFrame(rows)


def _retention_segments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"period": "下滑前", "segment": "手机", "share": 0.72, "retention": 0.50},
            {"period": "下滑前", "segment": "平板", "share": 0.18, "retention": 0.40},
            {"period": "下滑前", "segment": "其他", "share": 0.10, "retention": 0.45},
            {"period": "下滑后", "segment": "手机", "share": 0.57, "retention": 0.49},
            {"period": "下滑后", "segment": "平板", "share": 0.33, "retention": 0.39},
            {"period": "下滑后", "segment": "其他", "share": 0.10, "retention": 0.44},
        ]
    ).assign(
        dimension="设备类型",
        data_status="synthetic shares; only the direction and ~10pp gap come from the narrative",
    )


def _retention_path() -> pd.DataFrame:
    rows = [
        (1, "download", "下载", 1.000, 1.000),
        (2, "register", "注册登录", 0.950, 0.949),
        (3, "home", "进入首页", 0.900, 0.901),
        (4, "browse", "浏览点击", 0.700, 0.699),
        (5, "consume", "浏览内容", 0.620, 0.618),
        (6, "interact", "点赞/收藏/评论", 0.500, 0.501),
        (7, "profile", "浏览博主主页", 0.230, 0.229),
        (8, "follow", "关注博主", 0.140, 0.141),
    ]
    return pd.DataFrame(
        rows,
        columns=["step_order", "step_key", "step_label", "baseline_rate", "current_rate"],
    ).assign(data_status="synthetic stable path consistent with the narrative")


def _benchmark_features() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("浏览主页并关注", 0.50, 0.20),
            ("浏览博主主页", 0.60, 0.28),
            ("评论", 0.35, 0.20),
            ("收藏", 0.55, 0.32),
            ("点赞", 0.70, 0.45),
            ("直播", 0.30, 0.20),
            ("内容浏览", 0.95, 0.88),
        ],
        columns=["feature", "benchmark_penetration", "other_penetration"],
    ).assign(
        ratio=lambda frame: frame["benchmark_penetration"] / frame["other_penetration"],
        evidence_type="correlation / hypothesis generation",
        claim_boundary="标杆用户由首月行为事后定义，渗透差异不能单独证明因果。",
    )


def _experiments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "experiment_id": "referral_ui_simplification_v2",
                "case_id": "referral_growth",
                "title": "邀请页面简化实验",
                "strategy": "简化信息层级并将邀请CTA放回首屏",
                "control": "复杂活动页，邀请按钮位于第二页",
                "treatment": "简化活动页，邀请按钮位于首页",
                "primary_metric": "邀请点击率",
                "final_metric": "拉新用户数",
                "guardrail": "新用户首月 LTV/CAC",
                "baseline_rate": 0.17,
                "treatment_rate": 0.235,
                "absolute_lift_pp": 6.5,
                "sample_size": np.nan,
                "sample_display": "百万级脱敏样本",
                "duration_days": 14,
                "mde_pp": 3.0,
                "alpha": 0.05,
                "power": 0.80,
                "significance": "p < 0.05",
                "decision": "上线并持续优化",
                "result_disclosure": "anonymized user-provided narrative",
            },
            {
                "experiment_id": "creator_follow_prompt_v1",
                "case_id": "new_user_retention",
                "title": "博主主页与关注引导实验",
                "strategy": "内容退出页弹窗引导浏览博主主页并关注",
                "control": "不展示额外引导",
                "treatment": "展示主页浏览与关注引导",
                "primary_metric": "次7日内留存率",
                "final_metric": "次7日内留存率",
                "guardrail": "未在用户提供材料中披露",
                "baseline_rate": np.nan,
                "treatment_rate": np.nan,
                "absolute_lift_pp": np.nan,
                "sample_size": 300_000,
                "sample_display": "约30万样本",
                "duration_days": 14,
                "mde_pp": np.nan,
                "alpha": 0.05,
                "power": np.nan,
                "significance": "p < 0.05",
                "decision": "策略推广并持续优化",
                "result_disclosure": "significant lift only; absolute effect not publicly disclosed",
            },
        ]
    )


def _metric_contracts() -> pd.DataFrame:
    rows = [
        (
            "invite_click_rate",
            "邀请点击率",
            "点击邀请UV",
            "活动页访问UV",
            "日×版本",
            "老带新页面机制指标，不是最终业务目标。",
        ),
        (
            "share_success_rate",
            "分享成功率",
            "微信分享成功UV",
            "点击邀请UV",
            "日×版本",
            "用于判断问题是否发生在分享环节。",
        ),
        (
            "viral_rate",
            "裂变率",
            "成功带来的新用户数",
            "活动曝光或参与用户（实施前需冻结唯一口径）",
            "日×版本",
            "原始材料未给出唯一分母，V2上线前必须冻结。",
        ),
        (
            "d1_7_window_retention",
            "次7日内留存率",
            "新增后第1至7天至少再次访问一次的用户数",
            "新增用户数",
            "新增Cohort",
            "窗口留存，不等于精确第7日留存。",
        ),
        (
            "feature_penetration",
            "功能渗透率",
            "该组中使用过功能的用户UV",
            "该组用户UV",
            "人群×功能",
            "标杆/非标杆差异是相关性证据。",
        ),
        (
            "month1_ltv_cac",
            "首月 LTV/CAC",
            "新用户首月活跃天数×日均时长×单位时长商业化价值",
            "归因范围内的激励成本",
            "活动版本",
            "价值成本比，不是净ROI。",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["metric_key", "metric_name", "numerator", "denominator", "grain", "boundary"],
    )


def _decision_records() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_id": "referral_ui_v2",
                "case_id": "referral_growth",
                "fact": "玩法升级后邀请点击率从约21%下降到17%，分享成功率约95%。",
                "interpretation": "主要断点在邀请发现，不在分享链路。",
                "hypothesis": "信息层级复杂且CTA位于第二页，提高了行动发现成本。",
                "action": "简化页面并将CTA放回首页，进行两周随机实验。",
                "decision": "邀请点击率提升至23.5%，首月LTV/CAC为2.18，高于外部投放1.90；上线并持续优化。",
                "limitation": "公开版本使用脱敏叙述和模拟明细，不代表雇主生产数据。",
            },
            {
                "decision_id": "retention_follow_v1",
                "case_id": "new_user_retention",
                "fact": "平板留存低约10pp且占比提高；产品主路径转化稳定；标杆关注渗透约2.5倍。",
                "interpretation": "结构变化解释总体压力，关注行为是产品机会但仅有相关性。",
                "hypothesis": "主动引导浏览主页和关注可帮助新用户形成持续内容关系。",
                "action": "内容退出页增加关注引导，进行两周随机实验。",
                "decision": "约30万样本下次7日内留存显著提升，p<0.05；推广并持续优化。",
                "limitation": "真实绝对提升和未披露护栏不在公开版补造；投放结构建议短期未落地。",
            },
        ]
    )


def portfolio_v2_frames() -> dict[str, pd.DataFrame]:
    return {
        "portfolio_case_registry": _case_registry(),
        "portfolio_business_kpis": _business_kpis(),
        "portfolio_decision_loop": _decision_loop(),
        "portfolio_referral_versions": _referral_versions(),
        "portfolio_referral_funnel": _referral_funnel(),
        "portfolio_retention_trend": _retention_trend(),
        "portfolio_retention_segments": _retention_segments(),
        "portfolio_retention_path": _retention_path(),
        "portfolio_benchmark_features": _benchmark_features(),
        "portfolio_experiments": _experiments(),
        "portfolio_metric_contracts": _metric_contracts(),
        "portfolio_decisions": _decision_records(),
    }
