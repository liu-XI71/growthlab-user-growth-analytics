# Case study: new-user retention

> Synthetic portfolio reconstruction. Values in the application are simulated or normalized and do not describe a specific company.

## Business question

Why did day 1–7 window retention decline, and which intervention has the strongest causal case for improving it?

## Business model and strategic tension

An aggregate retention decline can come from at least three systems:

1. **Acquisition composition:** more users arrive from lower-intent channels or device contexts.
2. **Within-segment product performance:** the same type of new user has a worse experience.
3. **Measurement/cohort maturity:** identity, return criteria, censoring or late events changed.

These explanations imply different actions. Reallocating spend may improve the average but reduce total incremental value or scale. Rebuilding onboarding is costly and unfocused if the first-use path is stable. Promoting a feature based only on high-engagement users can amplify selection bias. The analysis therefore separates arithmetic attribution, negative evidence, mechanism hypotheses and causal validation.

## Analysis sequence

### 1. Segment the retention change

Break new users down by acquisition channel, device type, device brand, operating system, and geography. Report both segment retention and segment share. This avoids mistaking a change in user composition for a deterioration inside every group.

GrowthLab uses a mix-shift decomposition:

```text
total change = structure effect + within-segment effect + interaction effect
```

The components reconcile exactly to the observed total change and are regression-tested.

Device retention cannot be interpreted outside context. Large-screen users may have different session occasions, input friction, content preferences and acquisition costs. The decision is not “buy more phone users because their retention is higher”; it is “compare incremental retained value per acquisition cost at the feasible channel mix, then test product improvements for underserved contexts.”

### 2. Test for onboarding friction

Measure the same-cohort funnel from download through login, home arrival, content interaction, and a meaningful engagement action. If conversion is stable at every step, the evidence does not support an onboarding-breakage explanation. This is an exclusion result, not proof that the product journey is perfect.

This negative result has decision value: it narrows the next investigation and prevents a broad onboarding redesign from being justified by the retention total alone.

### 3. Compare benchmark-user behavior

Define benchmark users using only clearly documented activity dimensions, then compare feature penetration and frequency with other users. A large feature-use gap is a hypothesis generator: active users may discover the feature because they are already more motivated.

The benchmark definition itself is post-signup selection. Motivation, channel, device, content fit and prior engagement can drive both feature use and retention. The platform therefore displays plausible confounders beside the penetration gap and labels this result evidence level 2–3, not causal evidence level 4.

### 4. Move from correlation to causal validation

Test a targeted feature-discovery prompt. The treatment changes discovery; the control preserves the current experience. Feature adoption is a mechanism metric, while day 1–7 window retention is the outcome. Apply the same pre-registration, assignment, A/A, SRM, balance, fixed-horizon, confidence-interval, business-threshold, and guardrail discipline as the referral experiment.

## Recommendation format

- **Evidence:** quantify how much decline is attributable to device/channel mix and how much remains within segment.
- **Exclusion:** onboarding conversion is stable, so deprioritize a broad onboarding rebuild.
- **Hypothesis:** one discovery gap is unusually large among benchmark users.
- **Causal test:** randomize a focused discovery treatment and measure both feature use and retention.
- **Decision:** scale only if retention improves, the result is robust to segment composition, and guardrails remain acceptable.

## Definition warning

“Day-7 retention” and “active at least once during days 1–7” are different metrics. GrowthLab labels the latter as a window metric and never treats it as exact D7. This distinction is part of the tested metric contract.

## Limitations

Benchmark-user comparisons are selected on post-signup behavior and are therefore not causal. A discovery prompt can have novelty effects. Retention windows introduce censoring for recent cohorts. Device strategy should be based on incremental value and acquisition cost, not retention alone.

## GROWTH method trace

| Gate | Project artifact |
|---|---|
| Goal | Exact-day/window retention contracts and decision owner |
| Reliability | Cohort inclusion/return/grain, maturity warning and bounded event checks |
| Opportunity | Device/channel/region segmentation, Mix-Shift and onboarding path |
| Why | Negative onboarding evidence plus feature-discovery hypothesis and confounders |
| Test | Randomized discovery prompt with mechanism and retention outcomes |
| Harvest | Segment consistency, guardrails, durable retention and acquisition economics |
