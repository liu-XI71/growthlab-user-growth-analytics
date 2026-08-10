# GrowthLab independent QA plan

## Objective

Validate that the public portfolio project is statistically correct, reproducible, privacy-safe, and runnable without cloud credentials. QA is independent from feature implementation and treats generated outputs, API responses, and documentation claims as evidence that must agree.

## Acceptance matrix

| Area | Required evidence | Failure severity |
|---|---|---|
| Hash allocation | The same `user_id` always maps to the same bucket; 100 buckets are valid; the configured 50/50 split is approximately balanced on a large deterministic sample | Blocker |
| A/A validation | No SRM for a correctly balanced split; the core rate is not spuriously significant for the deterministic A/A fixture; imbalance is detected before effect interpretation | Blocker |
| Sample planning | Two-sided two-proportion sample size supports baseline 17%, target 20% (+3 percentage points), alpha 0.05 and power 0.80; achieved power/MDE are internally consistent | Blocker |
| A/B inference | Absolute lift, relative lift, two-proportion z-test, two-sided p-value, 95% CI, business threshold and guardrails are reported separately | Blocker |
| Interpretation fixtures | 41.0% to 44.9% is 3.9 percentage points and about 9.51% relative; 17.0% to 23.5% is 6.5 percentage points and about 38.24% relative | Blocker |
| Experiment governance | Analysis records a precommitted end/sample target, warns against optional stopping, distinguishes novelty and network effects, and does not call `p < 0.05` sufficient for launch | Major |
| Segment balance | Pre-experiment channel/device/region distributions can be compared; aggregate and segment output makes Simpson's-paradox risk visible | Major |
| Retention | Exact-day D1/D3/D7/D30 and D1-7 window definitions are distinct; rates remain in [0, 1] | Blocker |
| Cohort analysis | Inclusion, return, grain and maturity warning are explicit; cohort API exposes exact-day cells rather than relabeling a window metric | Major |
| Mix-shift | Structure, within-group and interaction effects reconstruct the observed aggregate change within numeric tolerance | Blocker |
| Monitoring | Normalized target trend returns a transparent seven-day trend, robust anomaly score, target gap and component changes; anomaly output includes a non-causal claim boundary | Major |
| Methodology | GROWTH stages are complete and ordered; evidence levels, playbooks, source links and method boundaries are machine-readable | Major |
| Aggregate workbench | User-supplied funnels enforce monotonicity and localize the earliest material break; user-supplied Mix-Shift rows validate ranges/uniqueness and reconcile exactly | Blocker |
| Correlation language | Feature-usage analysis states association, potential confounding, and the need for randomized evidence | Major |
| Growth economics | `CAC = incentives / activated users`, `LTV30 = active_days * daily_hours * hourly_value`, `LTV/CAC = LTV30 / CAC`, and `Net ROI = (LTV30 - CAC) / CAC`; divide-by-zero is handled | Blocker |
| Data quality | IDs, temporal order, funnel monotonicity, assignment uniqueness, rates, amounts, category domains, reproducibility, and aggregate consistency are checked | Blocker |
| API | `/health` and all critical read/analysis endpoints return validated JSON and useful errors | Major |
| Streamlit | App and pages import without initialization failure and can start headlessly | Major |
| Containers | Compose topology is valid; API and frontend have health-aware startup; image builds are reproducible | Major |
| CI | Small deterministic fixture runs formatting/static checks, tests, API/Streamlit smoke checks, Docker validation/build, secret scan and large-file scan without cloud credentials | Major |
| Confidentiality | No real company/business-line names, proprietary URLs, access tokens, fixed real incentive amounts, or real internal sample-size statements occur in tracked public artifacts | Blocker |

## Statistical golden tests

Reference values are computed independently with Statsmodels/SciPy or closed-form formulas in tests rather than copied from application output. Tests assert both numerical accuracy and interpretation fields:

1. Baseline 0.17, target 0.20, two-sided alpha 0.05, power 0.80.
2. Control 41.0%, treatment 44.9%: +0.039 absolute, +9.512195% relative.
3. Control 17.0%, treatment 23.5%: +0.065 absolute, +38.235294% relative.
4. Balanced A/A fixture with identical observed rates and deterministic sample sizes.
5. Deliberate 60/40 allocation under an expected 50/50 split to prove SRM detection.
6. A statistically significant but business-insignificant fixture.
7. A positive core effect with a failed guardrail to prove that launch is not automatic.

## Privacy and public-release checks

The scanner covers tracked source, SQL, configuration, tests, Markdown, notebooks and generated screenshots. It excludes `.git`, virtual environments, caches and local databases. Secret patterns include common cloud/API token formats, private keys, `.env` secrets and credential URLs. Internal identifiers supplied in the source project brief are blocker terms and must not appear in the public repository.

## Execution order

1. Run fast unit and statistical golden tests.
2. Generate the small deterministic QA dataset.
3. Run data-quality and integration tests.
4. Start FastAPI and probe health/OpenAPI/critical endpoints.
5. Start Streamlit headlessly and probe its health endpoint.
6. Validate Docker Compose and build images when Docker is available.
7. Run confidentiality, secret and large-file scans.
8. Record exact commands, environment, passed/failed/skipped counts, known limitations and release recommendation in `docs/qa-report.md`.

## Release rule

Any blocker prevents a public push. Major findings may be accepted only when the affected feature is explicitly marked unavailable and the core portfolio path remains correct. QA does not accept screenshots, documentation text, or hard-coded conclusions as proof of a working calculation.
