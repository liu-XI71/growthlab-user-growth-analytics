# Interview guide

## 30-second introduction

“GrowthLab is an end-to-end user-growth analytics workbench I built to show how I turn a business target into an auditable decision. It covers referral acquisition and new-user retention, but the main value is the complete chain: governed metrics and SQL, diagnosis, experiment design, statistical and business significance, unit economics, API, dashboard, tests, and reproducible deployment. The public data is entirely synthetic and privacy-safe.”

## Three-minute walkthrough

1. **Problem framing:** external acquisition is constrained, so I model a referral path and separately investigate a new-user retention decline.
2. **Metric system:** I define the final growth outcome, the diagnostic funnel, user-quality measures, and LTV/CAC guardrail. Every rate has an explicit numerator, denominator, grain, and owner.
3. **Diagnosis:** funnel comparison localizes the referral loss to invitation click-through; retention decomposition separates device/channel mix from within-segment change; stable onboarding conversion helps deprioritize a broad onboarding redesign.
4. **Hypothesis:** simplify the invitation screen and improve discovery of a promising feature. Feature penetration among highly engaged users is treated as correlation, not causal proof.
5. **Experiment:** choose the mechanism metric, MDE, alpha, power, sample, and whole-week duration; assign by stable hash; run A/A; check SRM and segment balance; then run a fixed-horizon A/B test.
6. **Decision:** combine confidence intervals and p-values with a pre-registered business threshold, LTV/CAC guardrail, downstream quality, novelty, interference, and segment consistency.
7. **Delivery:** package the logic into DuckDB, SQL, Python modules, FastAPI, Streamlit, Docker, tests, and CI so the analysis is reproducible rather than a one-off notebook.

The shorthand is **GROWTH**: Goal and governed metrics → Reliability gate → Opportunity localization → Why hypothesis → Test causally → Harvest value and learning. Use the acronym only after explaining the business chain; it is a memory aid for your workflow, not a claim of inventing new statistics.

## Ten-minute product demonstration route

1. Start on the executive page and explain the normalized target, trend, component contribution and why anomaly flags are investigative—not causal.
2. Open the GROWTH page and spend less than one minute on the six gates and evidence ladder.
3. Show the referral version funnel and the earliest material invite-click break; distinguish fact, interpretation and UI hypothesis.
4. Open the experiment center and show primary/final/guardrail metrics, MDE/power/sample, hash assignment, A/A, SRM/balance, effect/CI and the dual decision gate.
5. Open unit economics and state the LTV/CAC versus net ROI formulas without looking at notes.
6. Switch to retention: exact-day/window contract, cohort maturity, device Mix-Shift and stable onboarding path as negative evidence.
7. Open feature analysis and explicitly refuse to call benchmark-user penetration causal.
8. Use the workbench to edit one funnel or segment row and rerun the API-backed calculation.
9. Finish on data quality to show that the result is generated, tested, privacy-scanned and reproducible.

The demonstration should feel like one decision narrative. Do not tour every chart or lead with the technology stack.

## Questions you should be ready to answer

### Why is invitation click-through primary instead of new users?

The treatment directly changes the invitation screen, and prior funnel diagnosis identifies invitation action as the bottleneck. The final activation metric remains a business outcome and supporting endpoint, but the closer mechanism metric is more sensitive and interpretable for this treatment.

### Why is LTV/CAC not ROI?

LTV/CAC is a value-to-cost multiple. Net ROI subtracts cost first: `(LTV − CAC) / CAC`. Calling the ratio ROI overstates net return and creates avoidable ambiguity.

### What does p < 0.05 prove?

It does not prove the product is valuable or the null is false with 95% probability. Under the model and null, it indicates the observed or more extreme statistic is sufficiently unusual. The result still needs a confidence interval, design integrity, adequate sample/horizon, business threshold, guardrail, and limitation review.

### Why do an A/A test?

To catch broken allocation, instrumentation, metric definitions, eligibility, and unexpected arm differences before interpreting treatment effects. SRM, exposure logs, and pre-treatment segment balance are complementary checks.

### What if total and segment conclusions conflict?

Check group composition, eligibility, assignment, and the pre-registered estimand. Report aggregate and segment sample sizes/effects, determine whether composition creates Simpson's paradox, and do not select the most favorable view after seeing the result.

### Why use first-month value?

It supports faster iteration and can provide dense behavior signals, but it is a modeled proxy rather than complete lifetime value. I therefore show assumptions and sensitivity, and I would back-test longer-horizon predictions as cohorts mature.

### Why not conclude the feature causes retention from benchmark users?

Feature use is post-treatment behavior and highly engaged users are selected. Motivation and exposure can cause both usage and retention. The comparison forms a hypothesis; randomized discovery treatment provides the causal test.

## Resume bullets

Use only bullets you can explain and reproduce. Example wording:

- Built a privacy-safe full-stack user-growth analytics workbench with governed SQL metrics, DuckDB, FastAPI, Streamlit, Docker, and CI, covering referral acquisition, retention decomposition, and unit economics.
- Implemented an experiment decision engine with stable hash assignment, A/A diagnostics, sample-size planning, SRM and segment-balance checks, two-proportion inference, business thresholds, and LTV/CAC guardrails.
- Developed a retention diagnostic workflow separating user-mix and within-segment effects, with tested exact-day/window definitions and a correlation-to-causality product evaluation path.

Do not insert simulated uplift as a real employer achievement. If discussing a private internship project, use the exact version approved for disclosure and keep it separate from this public repository.
