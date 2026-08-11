# Data card

## Default dataset

The default GrowthLab dataset is deterministic synthetic data generated locally from a fixed random seed. It contains fictional users, acquisition contexts, campaign versions, product events, cohort activity, feature events, experiment assignments, and normalized economics.

### Intended use

- demonstrate an end-to-end growth analytics workflow;
- exercise metric, funnel, retention, decomposition, ROI, and experiment code;
- provide repeatable API and UI examples;
- support a public portfolio without exposing employer data.

### Not intended for

- estimating a real company's performance;
- training a production recommender or bidding model;
- making financial or user-policy decisions;
- benchmarking one platform against another.

### Reproducibility

The generator records seed, row counts, completion state, and data-quality results. Re-running with the same configuration produces the same analytical dataset. Generated databases and large extracts are excluded from version control.

### Version 2 snapshot and windows

`analysis_snapshot` records the deterministic analytical as-of date (`2025-07-15` in the canonical demo), the 14-day experiment horizon and the 30-day value follow-up. The windows are deliberately different:

- `value30` / `LTV30`: activation offsets **0 through 29** (30 natural days);
- exact D30 retention: qualifying activity at offset **30**;
- D1-7 window retention: at least one qualifying activity at offsets **1 through 7**;
- exact D7 retention: qualifying activity at offset **7**.

Immature D30 cells are `NULL`, never coerced to false. The canonical referral experiment is evaluated only after every linked invitee completes the required value follow-up.

### Known data-generating process for recovery tests

The public generator has an explicit `dgp_policy` record. For `referral_ui_simplification`, the treatment changes only the path:

```text
assignment → tracked exposure → invite click → referred activation
```

Control and treatment invitees use the same downstream retention, activity, value and cost data-generating policies. Both arms use the same incentive and variable-cost schedule. This prevents a UI treatment from silently becoming a cost or user-quality treatment. At adequate canonical sample size, the platform should recover the positive click/activation mechanism while treating downstream acquired-user quality differences as sampling variation. The policy is synthetic by design and is not an employer result.

### Data-quality invariants

The built-in checks include:

- inviter and invitee foreign-key integrity;
- every activated invitee has activity, value and variable-cost facts;
- exact D1/D3/D7/D30 flags agree bidirectionally with `user_daily_activity.relative_day`;
- D1-7 window flags agree with observed day 1..7 activity;
- `user_daily_value.relative_day` is restricted to 0..29;
- experiment exposure follows assignment;
- experiment-retention outcomes reconcile to the linked invitee;
- Contribution30 equals value minus service and all variable acquisition costs;
- referral UI experiment cost policy is identical across arms.

### Known limitations

Synthetic behavior is structurally simpler than real user behavior. Missingness, delayed events, bot traffic, identity stitching, attribution conflict, and interference are represented only to the extent required by the demo. Results should be evaluated as software and analytical-method examples, not empirical market evidence.

## Optional public sample

An optional adapter can be built around Google's public, obfuscated GA4 BigQuery sample dataset. Access requires the user's own Google Cloud authorization and may incur platform-specific limits or cost. GrowthLab does not commit or redistribute the raw third-party sample. When using any public source, verify current terms, schema, date range, obfuscation, and fitness for the analytical question.

## Sensitive-data policy

- no real names, contact details, device identifiers, cookies, advertising IDs, or production user IDs;
- no employer, business-line, campaign, internal metric, or confidential reward identifiers;
- no production credentials or `.env` files;
- monetary values are normalized;
- public documentation states when results are synthetic;
- repository scans run before publication.
