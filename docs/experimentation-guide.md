# Experiment design and evaluation playbook

This document describes the complete fixed-horizon workflow implemented by GrowthLab. The UI-simplification example uses synthetic data; the methodology is general.

## 1. Define strategy and objective

- **Strategy:** simplify the invitation screen and surface the invitation action on the first screen.
- **Immediate objective:** improve old-user invite click-through.
- **Ultimate objective:** increase successfully activated referred users.
- **Causal contrast:** assignment to the new experience versus assignment to the current experience.

The final business metric remains important, but the primary metric should match the mechanism the treatment is intended to change. If the diagnosed bottleneck is invitation click-through, making it primary increases interpretability and statistical sensitivity.

## 2. Freeze the metric set

| Role | Metric | Purpose |
|---|---|---|
| Primary | Invite click-through rate | Tests the direct product mechanism |
| Final business | Referred new-user activations | Connects the mechanism to growth |
| Guardrail | New-user 30-day LTV/CAC | Prevents buying low-value growth at unacceptable economics |
| Supporting | End-to-end referral rate | Shows downstream propagation |
| Supporting | Activated users per inviter | Measures invitation depth |
| Supporting | New-user visit frequency | Detects low-quality activations |
| Supporting | New-user retention | Detects downstream quality changes |

Document numerator, denominator, eligibility, deduplication, attribution, time zone, late-arriving-event policy, and exclusion rules before assignment begins.

## 3. Calculate minimum sample and duration

For a two-sided two-proportion test, specify:

- historical baseline `p0`;
- smallest effect worth acting on, `MDE = p1 − p0`;
- significance level `alpha`;
- power `1 − beta`;
- allocation ratio.

GrowthLab uses `baseline = 0.17`, an illustrative `MDE = +0.03` absolute, `alpha = 0.05`, and power `0.80` as its public statistical gold case. This is not a production forecast.

The naive duration is required total sample divided by eligible daily sample. Round up to complete business weeks and add enough observation time to inspect whether the effect decays after initial novelty. The minimum duration and minimum sample must both be met.

## 4. Assign users with a stable hash

```text
bucket = stable_hash(experiment_salt, user_id) mod 100
0–49  → treatment
50–99 → control
```

Properties to test:

- one user is stable across sessions and dates;
- a different experiment salt can produce an independent allocation;
- actual assignment ratio matches the pre-registered ratio;
- randomization unit matches the interference model.

If users can communicate treatment information or invite one another across arms, user-level independence may fail. Consider city, social-cluster, household, or other cluster assignment and use inference at the same randomization unit.

## 5. Run A/A and allocation checks

In A/A both arms receive the same product. Use it to validate:

- event instrumentation and metric definitions;
- allocation and exposure logging;
- sample-ratio mismatch (SRM);
- pre-treatment channel, city, device, platform, and tenure balance;
- unexpected primary-metric differences.

SRM asks whether observed group sizes are plausible under planned allocation. A passing SRM test does not prove randomization is correct; it is one diagnostic. Likewise, one noisy balance p-value should not trigger endless re-randomization. Inspect effect sizes, distributions, and the family of pre-treatment checks.

If the platform cannot randomize, stop describing the result as an ordinary A/B test. DID and PSM can support an observational identification strategy, but each introduces additional assumptions: parallel trends for DID and conditional exchangeability/overlap for PSM.

## 6. Execute the fixed-horizon A/B test

- Treatment: simplified first-screen invitation UI.
- Control: current UI.
- Keep eligibility, event definitions, and assignment fixed.
- Monitor guardrails for safety incidents.
- Do not repeatedly inspect an ordinary fixed-horizon p-value and stop when it crosses 0.05.
- Preserve exposure logs, assignment logs, analysis population counts, and exclusions.

If continuous decision-making is required, pre-specify a valid sequential design instead of informally peeking.

## 7. Evaluate statistical and business significance

GrowthLab reports:

- treatment and control rates;
- absolute uplift and relative uplift;
- pooled two-proportion Z statistic and two-sided p-value;
- unpooled confidence interval for the rate difference;
- achieved sample versus required sample;
- SRM and segment balance diagnostics;
- statistical significance (`p < alpha`; for a two-sided 5% large-sample test, `|Z| > 1.96`);
- business significance (effect reaches the pre-registered action threshold);
- guardrail status;
- a final decision with reasons.

Statistical significance is not sufficient. Ship only when the data pipeline is credible, the planned horizon is complete, the effect is precise enough, the business threshold is met, downstream economics are acceptable, and no material segment or interference risk invalidates the aggregate conclusion.

## Simpson's paradox and stratified reporting

An aggregate direction can differ from every segment direction when group composition differs. GrowthLab requires both:

1. pre/post assignment balance tables for channel, city, and device; and
2. aggregate and stratified treatment effects with segment sample sizes.

The correct response is not to choose whichever view is favorable. Reconcile eligibility, assignment, composition, and the estimand, then report the decision for the pre-registered target population.

## Decision record template

```text
Decision: ship / iterate / stop
Primary effect: absolute, relative, confidence interval, p-value
Business threshold: passed / failed
Guardrail: passed / failed
Design integrity: SRM, balance, exposure, exclusions
Time behavior: week-by-week effect and novelty assessment
Heterogeneity: pre-registered segment results
Limitations: interference, missingness, novelty, generalization
Next action and owner:
```
