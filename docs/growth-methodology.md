# GROWTH Decision OS: a personal analytics operating system

GrowthLab consolidates the two portfolio cases into one reusable operating system. The framework does not claim to be a new statistical theory. It is a practical orchestration layer that connects established product-metrics, decomposition, cohort, experimentation and decision methods while making their claim boundaries explicit.

```text
G — Goal & governed metrics
R — Reliability gate
O — Opportunity localization
W — Why hypothesis & evidence
T — Test causally
H — Harvest value & learning
```

The core discipline is simple: analytical work cannot skip a gate merely because a later method produces an attractive number.

## G — Goal and governed metrics

### Question

What business decision is the analysis meant to enable, what top-level outcome represents success, and how does it decompose into observable mechanisms?

### Required artifacts

- decision owner and decision deadline;
- overall evaluation criterion or top-level outcome;
- metric tree linking lagging business value to leading mechanism metrics;
- primary metric, final business outcome, guardrails and diagnostics;
- numerator, denominator, grain, identity, eligibility, attribution, time-zone, latency and exclusion contracts.

The goals → signals → metrics direction is informed by Google Research's HEART work, which describes user-centered dimensions and a process for mapping product goals to metrics. GrowthLab uses the process, not the HEART acronym as a causal method: [Rodden, Hutchinson and Fu, CHI 2010](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/).

### Portfolio mapping

For referral acquisition, successfully activated referred users are the final outcome. Invite click-through is primary only after the path decomposition identifies it as the mechanism the UI treatment is intended to move. First-month LTV/CAC is a guardrail, while end-to-end referral rate, invitations per inviter, new-user frequency and retention are supporting outcomes.

For retention, the first contract is definitional: exact D7 is activity on signup date + 7; day 1–7 window retention is activity at least once in the window. They cannot share an ambiguous “D7” label.

## R — Reliability gate

### Question

Can the observed movement be trusted before anyone tries to explain it?

### Required checks

- source freshness, row volume and missingness;
- unique user/event identity and deduplication;
- event order and cohort maturity;
- numerator ≤ denominator and ordered funnel invariants;
- experiment assignment/exposure/outcome order;
- A/A, sample-ratio mismatch and pre-treatment composition.

Microsoft's SRM taxonomy treats a sample-ratio mismatch as a high-value symptom of possible assignment, eligibility, exposure or telemetry failures. GrowthLab follows that interpretation: SRM is a diagnostic gate, while a pass is not complete proof of randomization quality. See [Fabijan et al., KDD 2019](https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners/).

### Stop rule

If the reliability gate fails, the output is a data incident, not a business explanation. The platform returns errors or blocks launch rather than silently proceeding.

## O — Opportunity localization

### Question

Where is the movement generated, and how much does each component contribute?

### Method router

| Symptom | First methods | Output |
|---|---|---|
| Top-line movement | trend, seasonality, data freshness, contribution tree | when it began and which component moved |
| Ordered conversion loss | same-population version funnel | earliest material break and downstream propagation |
| Retention decline | cohort definition/maturity, segment table, Mix-Shift | composition, within-segment and interaction contributions |
| Feature gap | benchmark comparison and confounder inventory | testable product hypothesis, not a causal claim |
| Cost increase | value/cost boundary and sensitivity | break-even point and decision-sensitive assumptions |

### Mix-Shift decomposition

GrowthLab uses an exact three-part decomposition for an aggregate rate:

```text
total change = structure effect + within-segment effect + interaction effect
```

For segment `i`, baseline share/rate are `w0_i`, `r0_i` and current values are `w1_i`, `r1_i`:

```text
structure_i   = (w1_i - w0_i) × r0_i
within_i      = w0_i × (r1_i - r0_i)
interaction_i = (w1_i - w0_i) × (r1_i - r0_i)
```

This implementation is a transparent baseline-weight formulation that reconciles exactly. It is connected to the broader rate-decomposition tradition established by Kitagawa: [Components of a Difference Between Two Rates, JASA 1955](https://doi.org/10.1080/01621459.1955.10501299). Other symmetric allocation conventions exist, so the weighting convention must be documented.

The decomposition answers “how the arithmetic change is distributed,” not “what caused user behavior.”

### Cohort discipline

A cohort result must declare its inclusion condition, return condition, grain and calculation. Google Analytics' official cohort documentation distinguishes standard, rolling and cumulative calculations and makes the inclusion/return criteria explicit: [GA4 cohort exploration](https://support.google.com/analytics/answer/9670133?hl=en).

GrowthLab also displays a maturity warning. A recent cohort cannot be compared on D30 until every included user has had the opportunity to reach day 30.

### Time-series discipline

The executive trend uses a transparent seven-day moving trend and robust median-absolute-deviation residual score. This is a triage mechanism, not a causal model. The distinction between trend, seasonality and remainder follows the general decomposition framing in [Hyndman and Athanasopoulos, Forecasting: Principles and Practice](https://otexts.com/fpp3/decomposition.html).

## W — Why hypothesis and evidence

### Question

Which statements are facts, which are interpretations, and which remain testable mechanisms?

GrowthLab requires five fields:

1. **Fact** — directly computed and definition-bound.
2. **Interpretation** — a reasoned reading of the pattern.
3. **Hypothesis** — a falsifiable product mechanism.
4. **Action** — the smallest test that discriminates among explanations.
5. **Limitation / refutation condition** — evidence that would weaken the story.

### Evidence ladder

| Level | Evidence | Claim strength |
|---:|---|---|
| 0 | Reproducible definition | The metric is defined consistently |
| 1 | Reliable observation | The measured movement is real in this population |
| 2 | Funnel/segment/cohort/decomposition localization | The movement is concentrated here |
| 3 | Product logic plus qualitative/mechanism evidence | This explanation is plausible enough to test |
| 4 | Valid randomized or justified quasi-experimental identification | The intervention caused an estimated effect under assumptions |
| 5 | Business, economic, heterogeneity and durability gates | A defined rollout decision is justified |

Benchmark-user feature penetration is level 2–3 evidence. High-engagement users may use the feature because they were already motivated; the feature-use gap cannot establish causality.

## T — Test causally

### Question

What estimand, assignment, sample, duration and inference identify incremental impact?

GrowthLab operationalizes online experimentation as a decision system, consistent with the role of randomization described in [Online Experimentation at Microsoft](https://www.microsoft.com/en-us/research/publication/online-experimentation-at-microsoft/).

### Pre-registration

- strategy, treatment and control;
- target population and randomization unit;
- primary, business, guardrail and supporting metrics;
- baseline, absolute MDE, alpha, power and allocation;
- minimum sample and complete-business-cycle duration;
- exclusions, missing-data policy and analysis population;
- novelty, interference, composition and stopping risks;
- statistical and business decision gates.

### Assignment and A/A

GrowthLab maps `(experiment_salt, user_id)` through SHA-256 into 100 buckets and assigns 0–49/50–99. Stable assignment is tested. A/A then checks metric definitions, telemetry, allocation, SRM and pre-treatment channel/device/region composition.

### Fixed-horizon inference

For the binary primary outcomes used by the two cases, the platform reports:

- treatment/control rates and counts;
- absolute percentage-point and relative uplift;
- pooled two-proportion Z statistic and two-sided p-value;
- an unpooled normal confidence interval for the absolute difference;
- required versus achieved sample and duration;
- SRM, balance and stratified directions;
- statistical, business and guardrail gates.

Ordinary fixed-horizon p-values cannot be watched repeatedly and used to stop whenever they cross 0.05. A continuous decision system requires a pre-specified sequential method.

### Variance reduction

CUPED can reduce estimator variance by using a predictive pre-treatment covariate. It is a precision method, not a bias repair: [Deng et al., WSDM 2013](https://doi.org/10.1145/2433396.2433413). GrowthLab documents the route but does not apply CUPED to the headline proportion example because the public aggregate workflow does not expose a validated pre-treatment user-level covariate.

### Network interference

Referral products are unusually vulnerable to spillovers: one treated inviter can affect another user's behavior. The platform therefore flags cluster assignment and inference at the randomization unit. Network-interference methods require assumptions beyond ordinary user-level A/B testing; see [Athey, Eckles and Imbens](https://www.nber.org/papers/w21313).

### When randomization is unavailable

DID and PSM are not “backup buttons.” DID requires a defensible parallel-trends structure; PSM requires conditional exchangeability and overlap, cannot balance unobserved confounding, and must avoid post-treatment covariates. The platform routes analysts to these methods but does not relabel an observational contrast as an A/B test.

## H — Harvest value and learning

### Question

Should the treatment ship, to whom, at what cost, and what will be learned after rollout?

### Decision gates

```text
data quality
AND assignment / exposure integrity
AND required sample
AND required duration
AND statistical significance
AND business significance
AND guardrail acceptance
AND economic acceptance
AND no unresolved material segment/interference risk
```

### Unit economics

```text
LTV30  = active days × daily hours × value/hour × retention discount
CAC    = attributed acquisition cost / activated acquired users
LTV/CAC = LTV30 / CAC
Net ROI = (LTV30 - CAC) / CAC
```

LTV/CAC and net ROI answer different questions. Sensitivity analysis varies activity, monetization value, cost and retention assumptions to identify the break-even boundary. A modeled first-month value supports faster iteration but must be back-tested against mature cohorts.

### Learning record

Every decision should preserve:

- decision and owner;
- evidence, effect, confidence interval and business threshold;
- data-quality, SRM, balance, sample and duration state;
- guardrail/economic result;
- heterogeneous and time-slice result;
- limitations and refutation conditions;
- staged-rollout policy and post-launch monitoring;
- next experiment or model update.

## How the two cases form one capability narrative

The referral case shows objective decomposition, path diagnosis, product iteration, experimentation and economics. The retention case shows metric-definition discipline, segment/mix decomposition, negative evidence from a stable onboarding path, hypothesis formation from benchmark users, and the transition from correlation to causal validation.

Together they demonstrate one repeatable skill: converting an ambiguous business movement into a trustworthy, bounded and economically defensible product decision—and packaging that logic as reusable software rather than a one-off slide deck.
