# Metric dictionary and governance

Metrics are governed by formula, unit, grain, ownership, and interpretation. The API endpoint `/metrics` exposes the same definitions used by the application.

| Metric | Definition | Grain | Interpretation guardrail |
|---|---|---|---|
| Referral activated users | Distinct invited new users who complete activation | day × campaign version | Final acquisition outcome, not merely a landing visit |
| Invite click-through rate | invite-click UV / campaign-page-visit UV | day × version | Primary diagnostic metric when the bottleneck is the invitation action |
| Share success rate | successful-share UV / invite-click UV | day × version | Keep distinct from platform handoff attempts |
| Activation per exposure | activated-new-user UV / campaign-exposure UV | day × version | Default end-to-end referral rate; label the denominator every time |
| Activation per invite click | activated-new-user UV / invite-click UV | day × version | Diagnostic alternative, never silently called the same “viral rate” |
| Activated users per inviter | activated-new-user UV / effective-inviter UV | day × version | Supporting depth metric, sensitive to inviter definition |
| 30-day LTV | active days × daily active hours × normalized value/hour | acquisition version | Modeled first-month value, not audited revenue |
| CAC | total incentive cost / activated new users | acquisition version | Attribute only the cost inside the decision boundary |
| LTV/CAC | 30-day LTV / CAC | acquisition version | Value-to-cost multiple, not net ROI |
| Net ROI | (30-day LTV − CAC) / CAC | acquisition version | Incremental net return relative to acquisition cost |
| Exact D7 retention | active exactly on signup day + 7 / new users | signup cohort | Different from a day 1–7 window metric |
| Day 1–7 window retention | active at least once on days 1…7 / new users | signup cohort | Always greater than or equal to exact D7 for the same cohort |
| Incremental D7 retained users per 10k assigned | 10,000 × (D7-retained referred users / assignments in treatment − control) | experiment × arm | Randomized ITT; non-acquired assignments contribute zero |
| Incremental D1–7 retained users per 10k assigned | Same-arm difference using day 1..7 window-retained referred users | experiment × arm | Window outcome, not exact D7 |
| Incremental Contribution30 per 10k assigned | 10,000 × arm difference in Σ(value30 − all variable acquisition costs) / assignments | experiment × arm | Primary additive economic estimand; value30 offsets 0..29 |
| Average acquired-user LTV/CAC | Σvalue30 / Σall variable acquisition costs among acquired users | source × campaign × treatment label | Descriptive; never labelled incremental |
| Cost per incremental D7 retained user | incremental variable cost rate / incremental D7 retained-user rate | experiment | Only available when incremental D7 is positive |

## Metric tree

The public demo uses an indexed active-user growth objective and separates paid acquisition, organic acquisition, and referral acquisition. The referral branch is decomposed into:

```text
campaign exposure UV
  → campaign page visit UV
  → invite click UV
  → successful share UV
  → invited new-user landing UV
  → invited new-user activation UV
```

## Governance rules

1. Every rate must expose its numerator and denominator.
2. UV is deduplicated at the metric's declared grain.
3. Event-time windows are calculated relative to the cohort anchor, not calendar labels alone.
4. Exact-day and window retention may not share one ambiguous label.
5. LTV/CAC and net ROI are separate metrics.
6. Experiment primary metrics and guardrails are frozen before outcome inspection.
7. Changes to formulas require a versioned definition and regression test.
8. The primary referral experiment denominator is every eligible assignment; tracked exposure is diagnostic.
9. Descriptive campaign versions cannot use `causal` or `incremental` labels.
10. Value30 is relative day 0..29; exact D30 retention is relative day 30.
11. Recent cohorts expose mature and immature counts; unavailable D30 remains null.
12. Metric lineage must identify source, mart, SQL evidence, decision use and claim boundary.
