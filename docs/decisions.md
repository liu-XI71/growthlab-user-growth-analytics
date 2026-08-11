# Engineering and analytical decisions

| Decision | Why | Trade-off / production next step |
|---|---|---|
| Deterministic synthetic data by default | Safe public portfolio, instant reproducibility | Does not reproduce all production-data pathologies |
| DuckDB analytical store | Embedded SQL engine, simple local and CI execution | Replace with a governed warehouse for multi-user production scale |
| FastAPI between UI and database | Typed, documented, testable contracts | Add auth, quotas, tracing, and deployment policy in production |
| Streamlit multipage UI | Fast decision-product delivery for an analytics portfolio | A custom frontend offers greater interaction and design control |
| Pure Python statistical functions | Gold-case testing and UI independence | Production experiment platforms also need exposure services and registries |
| Fixed-horizon default | Clear error-rate assumptions and no informal optional stopping | Use a pre-specified sequential method if continuous decisions are required |
| Difference-in-proportions CI | Directly interpretable absolute effect | Add robust/clustered methods when assignment is clustered or interference exists |
| Explicit mix-shift interaction term | Exact decomposition reconciliation | Other index decompositions allocate interaction differently |
| Normalized value units | Protects confidential economics | Real deployment requires currency, tax, attribution, and finance reconciliation |
| API returns interpretations and warnings | Keeps decision caveats near the result | Governance should also persist decisions, owners, and approvals |
| Canonical inviter→invitee identity | Connect acquisition quantity to the same user's retention and value | Production identity stitching needs consent, deletion and conflict policy |
| Assignment-denominator ITT is primary | Preserves randomization and includes non-exposed assignments | Triggered analysis remains useful only as a selection-biased diagnostic |
| Per-10k quality-adjusted outcomes | Avoids multiplying unrelated funnel and cohort averages | Absolute totals require an explicit eligible population and are never silently extrapolated |
| Contribution30 instead of incremental LTV/CAC | Stable additive decision estimand; non-acquired assignments contribute zero | Finance deployment needs audited value and cost allocation |
| Pre-treatment one-hot SMD | Practical balance measure unaffected by sample-size-driven p-values | Stratified/cluster designs require design-specific balance policy |
| Conservative conjunctive launch gate | Unknown or failed DQ, SRM, sample, duration, maturity, guardrail, statistical, business or economic evidence blocks ship | Teams may add approved overrides, but must persist owner and rationale |
| Separate 14-day experiment and 30-day value follow-up | Prevents partial value from being labelled `value30` | Longer-term value requires a separately validated forecast or mature cohort |

## What this repository intentionally does not claim

- Synthetic results are not real commercial impact.
- A benchmark-user feature gap is not causal evidence.
- A passing p-value is not a product launch decision.
- A passing SRM check is not proof that every assignment assumption holds.
- First-month modeled value is not audited lifetime revenue.
- Full-stack delivery does not substitute for production security and platform engineering.
