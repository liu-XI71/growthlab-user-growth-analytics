# GrowthLab Option B independent QA report

## 1. Current verdict

**Current QA result: LOCAL GO for the integration/publication candidate.**

All analytical, data, API, decision-gate, Streamlit execution and desktop-browser acceptance
checks pass. The previously open first-run issue is closed: the backend health check now has a
six-minute `start_period`, and both READMEs document the canonical 100,000-user boot time plus
the PowerShell 5,000-user fast-start profile and its expected `DO_NOT_SHIP` decision.

Real-browser QA was completed with the official portable Node runtime and Playwright CLI at
1440x1000 and 1280x720. Six modules, sidebar navigation and representative controls rendered
without Streamlit exceptions, browser-console errors or horizontal overflow. Visual defects
found in the first pass were fixed and rechecked from fresh browser renders.

This is a local code-quality **GO**, not evidence that the final GitHub commit has already
passed remote CI. Because Docker is unavailable on the QA host, the public-release claim still
requires the final GitHub Actions Docker config/build job, commit SHA and public-page readback.

## 2. Independence and tested state

QA was performed independently from the production implementation. Numerical conclusions
were recalculated from direct SQL and hand-calculated micro-fixtures rather than accepted from
UI labels or implementation claims.

| Item | Tested value |
|---|---|
| QA date | 2026-08-11 (Asia/Shanghai) |
| Local platform | Windows / PowerShell |
| Local Python | 3.10.11 isolated `.venv` |
| Canonical profile | 100,000 users, seed 42 |
| Independent secondary profile | 100,000 users, seed 4,242 |
| Fast integration profile | 5,000 users, seed 42 |
| Independent data golden profile | 2,000 users, seed 4,242 |
| Full automated suite | 143 passed, 0 failed |
| Coverage | 91% across `analytics` and `backend` (1,255 statements, 108 missed) |
| Built-in canonical DQ | 29/29 passed |
| Canonical database rows recorded by ingestion | 3,352,628 |
| Docker availability on QA host | unavailable; remote CI is the required Docker gate |
| Browser QA runtime | portable Node v22.23.2 + Playwright CLI + Chrome |
| Desktop viewports | 1440x1000 full-page visual review; 1280x720 six-page smoke |
| Worktree tested | uncommitted Option B implementation; final commit SHA pending integration |

The final public-release report must replace the pending commit and CI fields after the
integration commit is pushed and the remote workflow succeeds.

## 3. Commands and results

### Compilation, lint, format and patch hygiene

```powershell
.\.venv\Scripts\python.exe -m compileall -q analytics backend scripts frontend tests
.\.venv\Scripts\python.exe -m ruff check analytics backend scripts frontend tests
.\.venv\Scripts\python.exe -m ruff format --check analytics backend scripts frontend tests
git diff --check
```

Result: passed. Ruff reported all checks passed and 93 Python files already formatted.

### Full tests and coverage

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  --cov=analytics `
  --cov=backend `
  --cov-report=term-missing `
  --cov-report=xml:coverage.xml `
  --cov-fail-under=85 `
  --junitxml=pytest-results.xml
```

Result after the final governance-lineage visual fix and Windows startup-retry regression:
**143 passed, 0 failed**, 91.39% combined analytics/backend coverage, in 163.6 seconds.
The only warning is a third-party Starlette TestClient deprecation notice about its HTTPX
adapter; application behavior is unaffected.

The GitHub workflow now enforces an 85% coverage floor and uploads JUnit and coverage XML
artifacts.

### Canonical deterministic generation

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_demo_data `
  --db <temporary-canonical-db> --users 100000 --seed 4242
```

Independent seed 4,242 result: generation completed in 209.9 seconds with 29/29 built-in DQ
checks passing. Important row counts were 100,000 users, 135,000 assignments, 3,252 activated
referral edges, 984,519 user-day rows and 973,482 value rows.

The default local canonical seed-42 database was then independently opened and probed:
100,000 users, 135,000 assignments, 3,254 referral edges, 29/29 DQ checks passed, and its final
decision was `SHIP_WITH_MONITORING` with no failed gate.

## 4. Lifecycle and identity acceptance

Independent SQL and automated tests verify:

- every inviter and invitee resolves to the canonical `users.user_id` identity;
- every activated referral edge resolves to one and only one acquired-user record;
- every acquired invitee has activity, retention, user-day value and all three variable-cost
  event types;
- no referral invitee or acquired user is attributed to more than one edge;
- all cost-event IDs are unique and cost totals reconcile to acquired-user aggregates;
- activation, activity, assignment, exposure and outcome timestamps are ordered correctly;
- assignment rows and `mart_experiment_user_value` rows conserve exactly;
- a non-acquired assignment has null invitee identity and contributes zero retention, value,
  cost and Contribution30;
- overall lifecycle totals equal the sum of mutually exclusive acquisition-quality segments.

`source_kind` has only two governed values:

- `descriptive_campaign` for non-randomized historical campaign versions;
- `randomized_experiment` for the referral UI experiment.

The descriptive acquisition-quality mart exposes no field containing `incremental`, and its
API explicitly sets `causal_claim_allowed=false`.

## 5. Retention maturity and value-window acceptance

`user_daily_activity.relative_day` is the single source of truth. Independent bidirectional
SQL checks show zero mismatch for exact D1, D3, D7 and mature D30, and zero mismatch for the
D1-7 window. Immature D30 is null rather than false.

The off-by-one boundary is verified independently:

```text
value30 / LTV30 = relative days 0..29 inclusive
exact D30       = relative day 30
```

No `user_daily_value` row falls outside 0..29. Exact-D30 activity is retained in the activity
fact but never enters value30. Each acquired-user LTV30 and service-cost aggregate was
recomputed from offsets 0..29 and matched exactly.

The canonical analysis snapshot is 2025-07-15. All 831 seed-42 referral-experiment invitees
were mature for D7 and D30, the experiment ran for the fixed 14-day period, and the most recent
invitee had 50 days of observable value follow-up versus the required 30 days.

## 6. Metric golden standards

### Hand-calculated eight-assignment fixture

An in-memory fixture with four control and four treatment assignments includes acquired and
non-acquired units. The governed SQL recovered the independent golden values exactly:

| Metric | Golden result |
|---|---:|
| Incremental exact-D7 retained users / 10k assigned | 2,500 |
| Incremental D1-7 retained users / 10k assigned | 2,500 |
| Incremental Contribution30 / 10k assigned | 30,000 normalized value units |
| Observed incremental D7 retained users | 1 |
| Incremental variable cost | 7 normalized cost units |
| Cost per incremental D7 retained user | 7 |

A zero or negative incremental-D7 fixture returns an unavailable efficiency ratio rather than
infinity, NaN, a negative pseudo-efficiency claim, or an accidental launch decision.

### Canonical seed-42 results

| Result | Estimate | Uncertainty / gate |
|---|---:|---|
| Invite-click ITT control | 16.4974% | assignment denominator |
| Invite-click ITT treatment | 21.7871% | assignment denominator |
| Absolute invite-click lift | +5.2897 pp | 95% CI +4.5646 to +6.0148 pp; p=2.25e-46 |
| Incremental exact-D7 / 10k | 19.4789 users | 95% CI 7.9982 to 30.9596 |
| Incremental D1-7 / 10k | 72.1942 users | 95% CI 49.6798 to 94.7087 |
| Incremental Contribution30 / 10k | 574.2175 | bootstrap CI 364.8519 to 776.9015; P(positive)=1.0 |
| Cost per incremental D7 retained user | 36.3010 | available because the D7 increment is positive |

The API values matched an independent direct SQL arm-level recalculation. Treatment and
control terms come from the same randomized experiment and use assignment denominators; no
cross-population funnel rate is multiplied by an unrelated retention average.

Average LTV/CAC is independently verified as `SUM(value30) / SUM(variable acquisition cost)`
among acquired users. It is structurally and visually separate from Incremental
Contribution30 and cannot independently trigger a causal ship decision.

## 7. Data-generating-process acceptance

The referral UI treatment is constrained to one mechanism path: assignment -> tracked
exposure -> invite click -> referred activation. It does not change the downstream acquired
user's retention, activity, value or cost policy.

Independent white-box recovery tests create otherwise identical control and treatment user
frames under the same random seeds. Retention flags, value, service cost, incentive,
operational cost and contribution are identical row for row. The canonical database further
shows the same 7.5 normalized incentive and 0.48 operating-cost schedule in both arms; the
same deterministic invalid-reward rule is applied to both.

This prevents the positive IC30 result from being manufactured by an arm-specific price,
retention or monetization parameter.

## 8. Experiment health and adversarial gates

The primary estimand is assignment-denominator ITT. The exposed-user diagnostic reports a
post-assignment population and a selection-bias warning; it is not used for launch.

Verified health evidence includes:

- overall and weekly SRM;
- assignment -> exposure -> observable counts;
- one-hot pre-treatment SMD for channel, device and region using threshold 0.1;
- exact sample-size planning for baseline 16%, MDE +2 pp, alpha 0.05 and 80% power;
- fixed 14-day duration and separate 30-day value follow-up;
- guardrail metric, direction, floor and tolerance;
- segment confidence intervals, pre-specified/exploratory labels and Benjamini-Hochberg
  multiplicity markers;
- week slices labelled novelty/durability diagnostics that cannot alter the fixed-horizon
  rule.

Adversarial gate tests hold sample and every other gate true, then independently set each of
the following to false or unknown: DQ, SRM, exposure tracking, sample size, duration, outcome
maturity and guardrail. Every case returns `DO_NOT_SHIP`. Separate tests prove that failed
statistical significance, business MDE or Incremental Contribution30 also blocks ship. Only
an explicit all-true conjunction can return `SHIP_WITH_MONITORING`.

The 5,000-user integration profile correctly returns `DO_NOT_SHIP` because it is below the
pre-registered sample requirement, even though its point estimate is positive. The canonical
100,000-user profile passes all 12 gates.

## 9. API acceptance

New and legacy routes were exercised against deterministic live databases. Verified Option B
families are:

- `/lifecycle/summary`, `/lifecycle/cohorts`, `/lifecycle/acquisition-quality`;
- `/investigation/paths`, `/investigation/mix-shift`;
- `/experiments/{id}/health`, `/experiments/{id}/effects`;
- `/economics/summary`, `/economics/scenarios`;
- `/decisions`;
- `/metrics/{name}/lineage`.

Repeated requests return deterministic, finite, JSON-serializable values. Invalid source
kinds, acquisition sources, metric/experiment IDs, budget multipliers, populations and
elasticities return 404 or 422 rather than unhandled 500. On the 5,000-user CI fixture,
representative warmed routes remain under the two-second QA performance threshold.

## 10. Frontend and real-browser acceptance

The navigation shell exposes exactly six modules:

1. Executive Decision Cockpit;
2. Growth Lifecycle;
3. Investigation Studio;
4. Experiment & Causal Lab;
5. Growth Economics & Allocation;
6. Decision & Governance.

All six modules executed through Streamlit AppTest against a live FastAPI service with the
canonical schema and raised no exception. The navigation shell also executed without an
exception. Source-contract tests verify each module has its header, GROWTH evidence gate,
required API family, chart/table and causal/descriptive boundary language. A separate
headless Streamlit process returned `ok` from `/_stcore/health`.

The independent real-browser pass then exercised Chrome through Playwright CLI against the
live FastAPI and Streamlit processes. At 1440x1000, all six first-screen renders had zero
Streamlit exception nodes, zero console errors after normal sidebar navigation, zero
horizontal overflow, and their expected charts/tables. Because Streamlit uses an internal
main-content scroll container, QA separately scrolled every module to its bottom viewport and
inspected the lower charts, tables and decision content. The following interactions triggered
clean Streamlit reruns with no exception:

- lifecycle source: all activated invitees -> historical campaign versions;
- investigation breakdown: device -> channel;
- economics elasticity slider: 0.80 -> 0.78;
- sidebar navigation through all six modules.

First-pass visual findings were the lifecycle Sankey label collision, truncated investigation
breakpoint, truncated IC30 title, truncated governance unit and a stale 27-vs-29 DQ label. The
scroll-container pass then found a second long-label collision in the governance metric-lineage
Sankey. The final render uses a readable lifecycle funnel, short business labels, dynamic DQ
count and a four-stage vertical lineage flow whose complete technical labels remain available
through hover and an expandable table. Every finding was visually rechecked. Six clean
1440x1000 first-screen screenshots are stored under `docs/assets/`, and the executive cockpit
is linked from both READMEs.

A second 1280x720 navigation smoke verified all six titles at y=94, first KPI cards within the
initial viewport where applicable, zero exception nodes and zero horizontal overflow. The
project is accepted as a desktop analytics application; mobile and cross-browser rendering are
not release claims.

## 11. Privacy, repository hygiene and licence acceptance

The full passing test suite scans tracked/publication-candidate source, SQL, Markdown and
configuration for protected company/product/org identifiers, real internal scale, real reward
or sample values, obvious credentials, private keys, credential URLs, committed environment
secrets and files over 10 MiB. No finding was produced.

Generated DuckDB files are ignored by Git and excluded from Docker build context. The dataset
is deterministic synthetic data, normalized value units are used, and public documentation
states that results are not employer outcomes. No external dataset is redistributed in the
default build. The repository remains MIT licensed.

## 12. Defects found during independent QA

| Finding | Severity | Disposition | Regression evidence |
|---|---:|---|---|
| New acquisition-quality view referenced a missing treatment field and the generator could not build a database | Blocker | Fixed | independent seed-4,242 2k and 100k generation complete |
| Random retention flags did not initially reconcile to exact user-day activity | Blocker | Fixed | bidirectional D1/D3/D7/D30/window SQL mismatch = 0 |
| Experiment decision initially omitted sample, actual duration, DQ and guardrail gates; SRM unknown could pass | Blocker | Fixed | adversarial gate suite; small profile no-go; canonical all-gates pass |
| Experimental invitees initially had incomplete value follow-up but were labelled value30 | Blocker | Fixed | snapshot advanced; all experiment invitees D30 mature; follow-up 50 >= 30 days |
| Exact-D30 activity initially entered value30, creating an offset-30/31-day off-by-one | Blocker | Fixed | every value row is offset 0..29; D30 excluded and aggregates reconcile |
| UI treatment initially had a direct downstream retention adjustment | Blocker | Fixed | arm-invariant retention/value/cost DGP white-box test and `dgp_policy` |
| Cohort API initially omitted retained numerators and as-of metadata | High | Fixed | API rows expose retained, mature, immature and as-of fields |
| 100k first-run time exceeded the original Compose health-check window | High | Fixed | backend health check now has `start_period: 6m`; both READMEs document 3-4 minute canonical boot and 5k fast start |
| Lifecycle and governance-lineage chart labels overlapped; three KPI labels were truncated; governance showed stale 27-vs-29 DQ text | High/Medium | Fixed | final first-screen and bottom-scroll browser renders show readable funnel, vertical lineage, short labels and dynamic 29-check text |
| Playwright CLI was initially unavailable | Verification gap | Fixed | portable Node v22.23.2 and Playwright CLI used for six-page Chrome QA at two desktop viewports |
| Windows could transiently reset the first Streamlit health request during startup | Medium | Fixed | bounded retry now covers transport `OSError`; a deterministic first-request reset regression passed three consecutive targeted runs and the full suite |
| Starlette TestClient emits an HTTPX adapter deprecation warning | Low | Accepted | third-party warning only |

## 13. Remaining release gates

Local QA is complete. Final publication evidence still requires:

1. push the final integration commit and require the remote GitHub Actions test and Docker jobs
   to pass, including `docker compose config --quiet` and both image builds;
2. record the final commit SHA and CI run URL/ID;
3. verify the public GitHub README/screenshots and release artifact after the final commit, then
   record the downloadable artifact hash.

Until these remote checks are recorded, this report authorizes integration and publication
work but not a statement that the GitHub release itself has already passed CI.
