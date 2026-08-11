# GrowthLab Option B independent QA plan

## 1. Purpose and independence

This plan validates the Option B flagship upgrade as a decision-grade growth analytics
system. QA is independent from feature implementation. UI text, screenshots, README
claims, seeded conclusions, and application output are not accepted as proof of a correct
calculation: numerical results must reconcile to independently computed SQL or closed-form
golden values.

The release rule is strict:

- any **Blocker** finding is an unconditional no-go;
- a **High** finding is a no-go unless the affected feature is removed from the public claim
  and the primary acquisition-to-value journey remains complete;
- **Medium** and **Low** findings must be documented with a bounded impact and owner;
- synthetic results must never be represented as outcomes achieved for a real employer.

## 2. Severity model

| Severity | Meaning | Examples |
|---|---|---|
| Blocker | Wrong business decision, broken primary journey, confidentiality/security exposure, or non-runnable release | average value labelled incremental; orphan acquired users; failed guardrail still produces `launch`; real company identifiers or credentials in tracked files |
| High | Materially incomplete Option B claim or a major route/page unavailable | assignment and exposure conflated; mature cohorts include censored users; one of the six modules fails to render; API returns an unhandled 500 for supported input |
| Medium | Important weakness with a correct fallback or narrow scope | missing optional segment, incomplete empty-state copy, performance above target without timeout |
| Low | Cosmetic or documentation-only defect without analytical ambiguity | minor spacing inconsistency; non-critical wording issue |

## 3. Required Option B acceptance matrix

| Area | Required evidence | Severity if absent/wrong |
|---|---|---|
| Lifecycle identity | Every activated referral-acquired `new_user_id` resolves to the canonical user, referral edge, activation, user-day activity, D1/D7/D30 observability, cost and value records using one documented identity key | Blocker |
| Referential integrity | No orphan inviter/invitee, assignment, exposure, cost, value, or user-day keys; no duplicate primary keys at the documented grain | Blocker |
| Temporal integrity | Registration precedes or equals activation; assignment precedes exposure; exposure precedes attributable outcome; activity/value/cost timestamps stay inside their declared windows | Blocker |
| Cohort maturity | D1/D7/D30 denominators include only users old enough to observe that horizon; immature results are null/unavailable, not false/zero; right censoring is explicit in API and UI | Blocker |
| Conservation | Funnel stages are monotonic where semantically required; overall counts reconcile to mutually exclusive segment totals; lifecycle and experiment totals reconcile to source facts | Blocker |
| Per-10K incremental D7 | Formula, denominator type, causal population, unit and outcome horizon are explicit; treatment-control counterfactual is used | Blocker |
| Incremental retained users | Projected and observed-window increments are separately labelled and exactly reconstruct from arm rates and the stated projection population | Blocker |
| Incremental Contribution30 | Net 30-day value is computed per randomized unit in each arm, differenced against control, and scaled only by a labelled population; costs and value share a compatible window and unit | Blocker |
| Average economics | Average LTV/CAC and Net ROI remain available but are visually and structurally separate from incremental value; neither may be used as evidence of causal incrementality | Blocker |
| Experiment estimand | ITT and triggered/exposed analyses have distinct denominators and labels; launch defaults to the pre-registered primary estimand | Blocker |
| Experiment health | SRM, exposure mismatch, timestamp integrity and covariate balance are evaluated before effect interpretation | Blocker |
| Experiment dynamics | Week slices expose novelty/durability; pre-specified segment effects include uncertainty and interaction/multiplicity metadata | High |
| Decision gate | Sample, duration, data quality, SRM, balance policy, statistical, business, guardrail and economic gates all participate in the final decision | Blocker |
| API contract | New and legacy routes return serializable, schema-consistent, deterministic JSON; supported bad input returns 4xx rather than unhandled 500 | High |
| Six-module UI | Executive Cockpit, Growth Lifecycle, Investigation Studio, Experiment & Causal Lab, Growth Economics & Allocation, and Decision & Governance all load with required headings, charts, filters, empty states and decision cards | High |
| Privacy/publication | No protected company/product/org names, internal scale, real reward/sample values, personal identifiers, private URLs, tokens, keys, or accidental raw local databases are publication candidates | Blocker |
| Reproducibility | Same seed produces the same identities, analytical aggregates and decisions; different seed changes data while preserving invariants | High |
| Tooling | Compile, Ruff lint/format, pytest, coverage gate, API/UI smoke, data generation and privacy scans pass on Python 3.12 | High |
| Containers | Compose validates and backend/frontend images build in CI; local absence of Docker is recorded, never silently treated as pass | High |

## 4. Statistical and business golden standards

### 4.1 Lifecycle denominator contract

Each retention response must publish at least:

- `cohort_start` / acquisition or registration timestamp;
- `as_of_date`;
- `horizon_days`;
- `eligible_users` (mature denominator);
- `retained_users`;
- `retention_rate`;
- `immature_users` excluded from the denominator;
- retention definition (`exact_day` or declared window).

For exact D7, a user registered on day `s` is mature only when `as_of_date >= s + 7 days`.
An activity on `s + 6` must not count as exact D7. An immature user must not be counted as
not retained. The same rule applies independently to D1 and D30.

The value and retention clocks have an intentional boundary difference:

```text
LTV30 / value30 observation offsets = 0..29 inclusive (exactly 30 calendar days)
exact D30 retention checkpoint      = offset 30
```

The exact-D30 activity row must never enter `value30`; QA recomputes value and service cost
from offsets 0..29 and compares them to every acquired-user aggregate. D30 maturity requires
the snapshot to reach activation plus 30 days, while a complete value30 window reaches
activation plus 29 days. The synthetic flagship snapshot must satisfy both for every
experiment-linked invitee used by the final economics decision.

### 4.2 Incremental D7 / D1-7 retained users per 10K

The canonical user-level rate is:

```text
arm_d7_rate = downstream D7-retained acquired users in arm / arm denominator
incremental_d7_per_10k = 10,000 * (treatment_d7_rate - control_d7_rate)
```

The response must state whether `arm denominator` is assigned eligible inviters (ITT) or
actually exposed inviters (triggered). A metric labelled "per 10K exposures" must use unique
qualified exposed units, not event rows and not acquired-user count. The primary launch
decision uses the pre-registered ITT population; triggered results are diagnostic.

The treatment and control terms must come from the same randomized experiment and the same
estimand population. It is invalid to multiply average acquisition, retention or value
figures taken from different populations. The D1-7 window variant uses the identical
arm-level calculation with a clearly labelled `D1-7 window` outcome; it must not be labelled
exact D7.

Golden fixture:

```text
treatment: 120 D7-retained downstream users / 10,000 units
control:    80 D7-retained downstream users / 10,000 units
incremental_d7_per_10k = 40 retained users
```

Zero denominators return a validated unavailable result or 422 at an analysis boundary;
they must not produce infinity, NaN, or a fabricated zero effect.

### 4.3 Incremental retained users

For a labelled projection population `N`:

```text
incremental_retained_users = N * (treatment_retention_rate - control_retention_rate)
```

For the observed treatment arm only:

```text
observed_increment = treatment_retained
                     - treatment_denominator * control_retention_rate
```

The API/UI must not mix these two quantities. It must expose the projection basis, time
window, rounding policy and units.

### 4.4 Incremental Contribution30

The canonical ITT calculation is:

```text
unit_net_value30 = attributed_value_in_days_0_30 - all_attributed_cost_in_days_0_30
arm_mean_net30 = sum(unit_net_value30) / assigned_eligible_units_in_arm
incremental_contribution30_per_unit = treatment_arm_mean_net30 - control_arm_mean_net30
incremental_contribution30 = projection_population * incremental_contribution30_per_unit
incremental_contribution30_per_10k = 10,000 * incremental_contribution30_per_unit
```

Zero-value users remain in the ITT denominator. Referral incentive, channel/media cost,
operating cost and invalid/fraud/chargeback treatment must be named. Unsupported costs may
be declared zero only when visibly documented as a synthetic-data assumption.

For a triggered diagnostic, every qualified exposure is retained in the denominator and an
exposed unit that acquires nobody contributes zero. The default causal decision nevertheless
uses ITT; triggered estimates must carry a selection-bias warning. Descriptive campaign
version comparisons are never allowed to use `incremental` field names or labels.

Golden fixture:

```text
treatment: total value 2,000; total cost 800; 100 assigned units -> mean net 12
control:    total value 1,500; total cost 700; 100 assigned units -> mean net 8
incremental contribution per assigned unit = 4
projected to 1,000 eligible units = 4,000 value units
```

The result is invalid if it subtracts aggregate totals with unequal denominators, compares
incompatible windows, or reports treatment average net value without the control
counterfactual.

### 4.5 Average economics remain separate

The portfolio may continue to report:

```text
average CAC = total acquisition cost / activated acquired users
average LTV30 = total 30-day value / activated acquired users
average LTV/CAC = average LTV30 / average CAC
average Net ROI = (average LTV30 - average CAC) / average CAC
```

These outputs must be labelled descriptive averages. They must not reuse incremental field
names and must not independently cause a causal `launch` decision.

The portfolio must also report cost per incremental D7 retained user only when the D7
increment is positive and causally identified:

```text
incremental_variable_cost = treatment_total_variable_cost
                            - treatment_denominator * control_cost_per_unit
cost_per_incremental_d7 = incremental_variable_cost / observed_incremental_d7_users
```

The outcome window and analysis population must match the D7 increment. Zero or negative
incremental D7 returns an unavailable result and explanation rather than a negative or
infinite efficiency number.

### 4.6 Experiment health and inference

Independent fixtures cover:

1. 50/50 assignment with no SRM and a deliberate 60/40 SRM failure;
2. missing/duplicate exposures and outcome-before-exposure failures;
3. SMD for every declared covariate, with `abs(SMD) < 0.10` as the displayed practical
   balance convention unless another threshold is pre-registered;
4. baseline 17%, absolute MDE +3 percentage points, alpha 0.05, two-sided power 80%;
5. 17.0% to 23.5% = +6.5 percentage points and about +38.2353% relative;
6. 41.0% to 44.9% = +3.9 percentage points and about +9.5122% relative;
7. Week 1 positive / Week 2 null fixture that must surface novelty/durability risk without
   retroactively changing the fixed-horizon primary decision or enabling interim peeking;
8. pre-specified segment effects with estimates and 95% confidence intervals;
9. aggregate/segment direction conflict that must surface a Simpson/interaction warning;
10. exploratory multiplicity metadata (`adjustment_method`, adjusted p-value or an explicit
    "exploratory/not decision-gating" label);
11. statistically significant but sub-MDE result must not launch;
12. positive primary effect with SRM, insufficient duration/sample, guardrail regression,
    or economic-threshold failure must not launch.

## 5. Data-quality and adversarial fixtures

The deterministic QA database must exercise both pass and fail paths:

- orphan inviter, invitee, user-day, cost and value identities;
- duplicate referral edge and duplicate assignment at the documented grain;
- event before registration, outcome before exposure, exposure before assignment;
- exact-day vs window retention and D7/D30 immature cohorts;
- zero exposure, zero control rate and empty cohort;
- negative cost/value, null covariate and unknown category;
- SRM failure and exposure-rate mismatch;
- sample and duration below pre-registration;
- guardrail and economic threshold failure;
- contradictory aggregate and segment direction;
- segment with a zero cell and interval edge cases;
- repeated API calls to prove deterministic ordering and values.

No invalid fixture may accidentally receive `launch`, `ship`, `pass`, or an equivalent
positive decision.

The hand-calculated micro-fixture must additionally prove conservation: every assigned unit
appears exactly once per arm denominator; non-acquirers contribute zero D7 and zero value;
arm totals equal the sum of mutually exclusive segments; and aggregate incremental D7,
D1-7, cost and Contribution30 reconstruct exactly from the assignment-level rows.

## 6. API acceptance

For every new and legacy critical route QA verifies:

- OpenAPI registration and response serialization;
- required field names, types, units, window, population and provenance metadata;
- deterministic response to repeated calls on the same database;
- 404 for missing resource identifiers;
- 422 for invalid enums, dates, negative monetary inputs, impossible denominators and
  unsupported dimensions;
- no NaN/Infinity in JSON;
- no raw exception detail, path, SQL or secret in errors;
- a representative endpoint latency target of <2 seconds at the CI fixture size after the
  first connection (performance warning, not an unsupported production-SLA claim);
- legacy routes either remain compatible or return a documented migration response.

## 7. Frontend acceptance

The primary automated route is Streamlit AppTest when compatible with the installed
Streamlit version. Source-level assertions and HTTP health probes supplement but do not
replace a render test. The six modules must each prove:

- stable load against a live deterministic API;
- expected module heading and narrative step;
- at least one relevant chart/table and one interpretation/decision artifact;
- filters with stable, unique widget keys;
- valid empty/error/loading state;
- no uncaught `KeyError`, serialization error or duplicate widget key;
- a connected navigation story from goal -> lifecycle -> diagnosis -> experiment ->
  economics -> decision/governance.

Required visible artifacts include the quality-adjusted growth thesis, acquisition-to-D30
lifecycle, ITT/triggered distinction, experiment decision gates, average vs incremental
economics, metric lineage/contract, limitations and explicit synthetic-data disclosure.

If a real-browser tool is unavailable, QA must say that pixel-level layout, responsive
breakpoints, clipping, overlap, tooltip behavior and cross-browser behavior remain unverified.
A public release then requires either remote screenshot evidence or a documented manual
visual pass; import/source assertions alone cannot justify "visuals verified".

## 8. Privacy, licensing and repository hygiene

Tracked/publication-candidate files are scanned for:

- protected company, product, org and internal-scale markers from the source brief;
- real reward and experiment-size values;
- email, phone, national ID and credential-bearing URLs;
- API/cloud/GitHub tokens and private keys;
- `.env` files other than `.env.example`;
- local absolute paths, database credentials and internal hostnames;
- files over 10 MiB, accidental local DuckDB/CSV extracts, generated caches and logs;
- datasets/assets without documented source and licence;
- absence of a clear synthetic-data and non-employer-results disclosure.

## 9. Execution order

1. Inventory changed schema, public APIs and all six UI modules.
2. Run fast unit/statistical golden tests.
3. Generate a small deterministic Option B QA database and run lifecycle invariants.
4. Independently reconcile lifecycle, experimental and economic goldens using direct SQL.
5. Run API schema, boundary, determinism and latency tests.
6. Run Streamlit AppTest/live-API page tests and headless health smoke.
7. Run compile, Ruff lint/format, full pytest and coverage.
8. Validate Compose/build locally when available; otherwise require a green CI container job.
9. Run privacy, secret, licence and large-file scans.
10. Record exact commands, versions, counts, defects, unverified items and go/no-go in
    `docs/qa-report.md`.

## 10. Required release evidence

The final report must include:

- commit SHA and dirty-worktree state tested;
- Python/OS and deterministic data seed/size;
- schema/table row counts and lifecycle reconciliation values;
- every command and exit status;
- passed/failed/skipped/xfailed test counts and coverage;
- endpoint list and performance sample;
- six-module UI evidence and visual-verification boundary;
- privacy/licence/large-file scan result;
- local Compose/build result or exact remote CI run evidence;
- defects by severity and disposition;
- an independent **GO** or **NO-GO** verdict.
