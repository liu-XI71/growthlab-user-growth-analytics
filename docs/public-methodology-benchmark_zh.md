# 公开增长分析方法论对照

## 说明

这份文档只用公开权威材料校验分析流程与术语，不把外部公司的案例数字、阈值或结果混进两个项目。页面中的项目事实仍以用户提供的脱敏内容为准；新增的可信度检查属于作品集沉淀的标准 SOP，不反向声称实习期间已执行全部平台功能。

## 1. 指标树与业务结果

Amplitude 的 North Star Framework 强调，顶层指标应反映用户获得的价值、处于团队影响范围，并能领先反映可持续业务结果；团队通过少量可控输入指标推动它。[Amplitude North Star Framework](https://amplitude.com/books/north-star/about-north-star-framework)

Mixpanel 的 Metric Tree 进一步强调结果指标与 L1/L2/L3 输入指标的关系，并为指标配置负责人、定义和决策上下文。[Mixpanel Metric Tree](https://mixpanel.com/blog/north-star-metric/)

Microsoft 将实验指标区分为总体评价、局部诊断、护栏和数据质量，避免只凭一个局部点击指标做上线决策。[Microsoft Trustworthy Experimentation Metrics](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/)

本平台采用：

```text
公司级背景：DAU目标差距
├─ 获客数量：老带新拉新用户数
│  └─ 机制指标：邀请点击率
├─ 用户质量：次7日内留存率
│  └─ 机制指标：主页浏览与关注
└─ 经济性：首月LTV/CAC
```

它不是一个严格数学等式，也不声称两个案例可以完整解释全部 DAU 变化。

## 2. 推荐漏斗

Adjust 将推荐流程拆为邀请、分享、被推荐用户转化和奖励；转化必须提前定义为下载、注册、首购或其他明确事件。[Adjust Referral Marketing](https://www.adjust.com/glossary/referral-marketing/)

AppsFlyer 强调邀请归因应把新安装或新行为正确归因到邀请者，并同时评估邀请成本和 ROI。[AppsFlyer User Invite Attribution](https://support.appsflyer.com/hc/en-us/articles/115004480866-User-invite-attribution)

Amplitude 的漏斗规范要求固定事件顺序、转化窗口、UV/事件计数方式、进入步骤和属性生效时点。[Amplitude Funnel Computation](https://amplitude.com/docs/analytics/charts/funnel-analysis/funnel-analysis-how-amplitude-computes)

因此案例一明确展示：

```text
活动页面曝光UV → 页面访问UV → 邀请点击UV → 微信分享成功UV → 新用户到达/新增
```

每一步同时保留用户数、相邻转化率、版本与数据状态。分享成功率稳定作为排除性证据，而不是只展示最终上涨结果。

## 3. 留存与 Cohort

Amplitude 区分 exact return、on-or-after return 与 bracketed retention；“第 1—7 天内至少回来一次”属于自定义区间留存，而不是精确第 7 日留存。[Amplitude Retention Interpretation](https://amplitude.com/docs/analytics/charts/retention-analysis/retention-analysis-interpret)

Amplitude 还强调自然日与滚动 24 小时窗口差异，以及近期 Cohort 尚未完整经过观察窗时的成熟度问题。[Amplitude Retention Time](https://amplitude.com/docs/analytics/charts/retention-analysis/retention-analysis-time)

因此案例二统一使用：

```text
次7日内留存率
= Day 1—7至少回访一次的新用户
÷ 已完整经历7天观察窗的新用户
```

## 4. Mix Shift 与辛普森悖论

Sequoia 的数据科学文章说明，即使每个子群表现不变，仅因人群占比变化，总体指标也可能改变。[Sequoia Metrics Mix Shift](https://articles.sequoiacap.com/metrics-mix-shift)

Microsoft 将辛普森悖论与不当分层列为线上实验常见解释陷阱，提醒分析者不能无限递归寻找显著子群。[Microsoft Dirty Dozen](https://www.microsoft.com/en-us/research/publication/a-dirty-dozen-twelve-common-metric-interpretation-pitfalls-in-online-controlled-experiments/)

案例二因此同时展示设备内留存与新增设备占比，并将结论限定为：设备结构变化可以解释总体下降的重要部分，但不能证明平板投放是唯一因果机制。

## 5. 产品路径与负证据

Amplitude 将漏斗用于沿关键产品路径识别转化损失，同时要求固定顺序、窗口和计数方式。[Amplitude Funnel Analysis](https://amplitude.com/docs/analytics/charts/funnel-analysis/funnel-analysis-get-the-most)

案例二对比留存下降前后的下载—注册—首页—浏览—互动—主页—关注路径。没有发现足以解释总体下降的断点，因此结论是“现有证据不支持基础路径卡点是主要解释”，而不是“证明产品没有任何体验问题”。

## 6. 标杆用户与因果边界

Amplitude Compass 用新用户行为与后续留存的相关性寻找候选行为，但明确强调相关不等于因果；候选行为应进入 A/B 或 split test 验证。[Amplitude Compass](https://amplitude.com/docs/analytics/charts/compass/compass-interpret-1)

因此 2.5 倍主页浏览与关注渗透率只用于生成产品假设。随机实验能够验证“退出页面增加主页与关注引导”这一完整策略的总效果，但不能把所有提升都归因到关注这一单一中介。

## 7. A/B 实验可信度 SOP

### 实验前

Microsoft 建议在实验前写清可证伪假设，并冻结总体结果、功能诊断、护栏和数据质量指标。[Microsoft Pre-Experiment Patterns](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-pre-experiment-stage)

样本量设计需要同时考虑基线、MDE、显著性水平和统计功效。老带新实验中的 17% 基线、3pp MDE、`α=0.05`、80% Power 用于估算最低样本；公开版仅披露实际回收为百万级脱敏样本，且不能把实际回收量冒充计算得到的最低样本。[Amplitude Experiment Goals](https://amplitude.com/docs/feature-experiment/workflow/define-goals)

### 分流与 A/A

Uber 的公开实验实践强调随机化需要与用户和环境信息独立，并用唯一实验 Key 保证不同实验的随机化独立。[Uber A/B Testing](https://www.uber.com/en-FR/blog/supercharging-a-b-testing-at-uber/)

Microsoft 将 A/A 用于端到端验证分流、埋点、指标与统计管道。[Microsoft A/A Testing](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/p-values-for-your-p-values-validating-metric-trustworthiness-by-simulated-a-a-tests/)

本平台示例：

```text
bucket = hash(experiment_id + user_id) % 100
```

### SRM 与均衡

Microsoft 将 Sample Ratio Mismatch 视为分流、记录丢失、处理差异或遥测问题的症状；未定位原因前通常不应使用实验效果做决策。[Microsoft SRM Diagnosis](https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/)

SMD 只作为渠道、设备、城市等实验前属性的辅助均衡诊断，不能替代随机化，也不能把所有变量等于零当成随机化成立的必要条件。[Austin Balance Diagnostics](https://pubmed.ncbi.nlm.nih.gov/19757444/)

### 固定周期、新奇效应与网络干扰

传统固定周期检验若反复查看并在刚显著时停止，会放大第一类错误；因此实验运行到预设样本与周期，再统一做最终判断。[Microsoft During-Experiment Patterns](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/)

Microsoft 提醒新功能初期可能存在新奇效应，短期结果不一定代表长期效果。[Microsoft External Validity](https://www.microsoft.com/en-us/research/articles/external-validity-of-online-experiments-can-we-predict-the-future/)

Google 与 LinkedIn 的网络实验公开资料说明，相连用户互相影响时，普通用户级随机可能受到 treatment contamination；老带新天然存在这一风险，但若真实项目没有使用集群随机，只能记录为风险与备选方案，不能写成已执行。[Google Network A/B Tests](https://research.google/pubs/designing-ab-tests-in-a-collaboration-network/) · [LinkedIn Network Interference](https://www.linkedin.com/blog/engineering/ab-testing-experimentation/detecting-interference-an-a-b-test-of-a-b-tests)

## 8. LTV/CAC 与净 ROI

Adjust 将 ROI 定义为 `(回报 - 成本) / 成本`。[Adjust ROI](https://www.adjust.com/glossary/return-on-investment-roi/)

Stripe 将 LTV/CAC 作为客户生命周期价值相对于获客成本的倍数，用于判断单位经济性。[Stripe CAC and LTV/CAC](https://stripe.com/resources/more/cac-in-saas)

因此本项目中的“新用户价值 ÷ 激励成本”统一命名为首月 LTV/CAC 或首月价值成本比，不能写成净 ROI 218%。

## 9. 最终对照结论

平台与公开成熟实践保持一致的部分包括：

- outcome-input 指标树；
- 推荐邀请—分享—新用户转化链路；
- Day 1–7 窗口留存与 Cohort 成熟度；
- 设备结构 Mix Shift；
- 产品路径与负证据；
- 标杆用户相关性边界；
- hypothesis、MDE、Power、A/A、SRM、固定周期、新奇效应与网络干扰；
- LTV/CAC 与净 ROI 的专业区分；
- 描述性、相关性、因果性和业务决策的证据分级。

最重要的边界是：公开方法只校验流程，不替用户补造经历。
