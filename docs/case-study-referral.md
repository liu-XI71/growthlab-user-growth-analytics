# Case study: referral acquisition

> Synthetic portfolio reconstruction. Values in the application are simulated or normalized and do not describe a specific company.

## Business question

How should a growth team recover incremental acquisition when externally purchasable traffic becomes harder to scale, without losing control of unit economics or downstream user quality?

## Business model and strategic tension

Referral is not simply another media channel. It converts the installed user base into a distributed acquisition supply system:

```text
eligible old users × participation × invitations per participant
× share delivery × invited-user arrival × activation × retained value
```

Each lever creates a different risk. Higher rewards can improve participation but increase CAC, attract reward-seeking users, increase fraud exposure, or reduce marginal efficiency. A denser activity page can communicate more mechanics but hide the primary action. A strong click effect can still fail if invited users do not activate or retain. The analytical task is therefore to optimize incremental valuable users, not clicks or gross invitation volume in isolation.

The top-level normalized active-user target is treated as a portfolio objective, while this project estimates only the referral branch contribution. Paid, organic and retained-user components remain visible in the executive contribution view so the referral result is not presented as the entire growth story.

## Metric system

The top-level outcome is successfully activated referred users. The diagnostic path is:

```text
exposure → campaign visit → invite click → successful share
         → invited-user landing → invited-user activation
```

Supporting metrics include end-to-end referral rate, activated users per inviter, new-user visit frequency, new-user retention, 30-day LTV, CAC, LTV/CAC, and net ROI.

## Diagnosis

The simulated baseline shows that a more generous but information-heavy campaign version can improve perceived reward while reducing invitation action. The largest break occurs at campaign visit → invite click, not at platform sharing or downstream activation.

This pattern supports a focused product hypothesis: additional copy and secondary mechanics increased cognitive load and displaced the primary action below the first screen.

The diagnosis follows the earliest-material-break rule. Downstream steps have smaller denominators and can appear noisier; selecting the largest percentage-point fluctuation anywhere in the path can misidentify propagation as the root location. The platform therefore reports both every step and the earliest break above a declared materiality threshold.

## Intervention

The candidate version removes nonessential copy, restores one dominant invitation action, and places it on the first screen. The treatment changes presentation—not eligibility, incentive accounting, attribution, or downstream activation rules.

## Evaluation

The experiment is pre-registered with invitation click-through as the primary metric and activated new users as the final outcome. New-user 30-day LTV/CAC is the guardrail. Stable user-level hash assignment, A/A checks, SRM, segment balance, a fixed two-week horizon, and business-threshold evaluation are completed before the ship decision.

### Why these metrics have different roles

| Role | Metric | Business interpretation |
|---|---|---|
| Mechanism primary | Invite click-through | Did the simplified UI change the action it directly targets? |
| Final outcome | Activated referred users | Did the action propagate into actual acquisition? |
| Quality | New-user frequency and retention | Did the strategy attract users who engage rather than only claim rewards? |
| Economic guardrail | First-month LTV/CAC | Is faster acquisition still acceptable at the chosen value window? |
| Diagnostic | End-to-end referral rate and invitations per inviter | Which downstream mechanism limits total impact? |

### Alternative explanations that must be checked

- channel/city/device composition changed between arms;
- exposure logging differs by version;
- page latency, not information hierarchy, changed;
- a reward deadline or weekly seasonality shifted participation;
- inviter and invitee interactions violate ordinary user-level independence;
- novelty lifts first-week clicks but decays later.

## Economics

The analysis deliberately reports two different quantities:

- `LTV/CAC = first-month value / acquisition cost`;
- `net ROI = (first-month value − acquisition cost) / acquisition cost`.

A sensitivity grid varies active days, daily hours, monetization value per hour, and incentive cost. This shows which assumptions could reverse the decision rather than presenting one point estimate as certain.

## Recommendation format

- **Evidence:** the invite-click stage explains the largest incremental loss.
- **Interpretation:** the mechanism is consistent with UI complexity, but funnel data alone is not causal proof.
- **Action:** test a simplified first-screen primary action.
- **Decision:** ship only after statistical, business, design-integrity, and economic gates pass.
- **Next measurement:** monitor effect decay, downstream quality, and heterogeneous response by device/channel/city.

## Limitations

Thirty-day LTV is modeled and may miss long-tail value. Invitation products can create interference between users. A fixed two-week test may not identify long-term novelty decay. The public demo is designed to demonstrate reasoning and implementation, not estimate a real market effect.

## GROWTH method trace

| Gate | Project artifact |
|---|---|
| Goal | Referral activation metric tree and LTV/CAC guardrail |
| Reliability | Event order, monotonic funnel, A/A, SRM and segment balance |
| Opportunity | Version funnel and earliest material invite-click break |
| Why | UI information hierarchy hypothesis plus alternative explanations |
| Test | Pre-registered fixed-horizon randomized experiment |
| Harvest | Statistical/business gates, unit economics, novelty/interference review and staged rollout |
