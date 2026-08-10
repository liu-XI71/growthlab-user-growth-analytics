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
