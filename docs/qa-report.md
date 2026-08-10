# GrowthLab independent QA report

## 1. Release verdict

**QA result: PASS for source release, subject to the first remote Docker build completing in GitHub Actions.**

The analytics, statistical inference, deterministic demo data, data-quality checks, FastAPI contract, Streamlit startup, privacy scan, lint and formatting gates pass locally. The repository contains a CI workflow that repeats these gates on Python 3.12 and builds both Docker images. Docker is not installed on the local Windows host, so container configuration/build is the only gate that could not be executed locally; it must be confirmed by the first GitHub Actions run.

## 2. Verified environment

| Item | Value |
|---|---|
| QA date | 2026-08-09 (Asia/Shanghai) |
| Local platform | Windows / PowerShell |
| Local Python | 3.10.11 isolated `.venv` |
| CI Python | 3.12 (`actions/setup-python`) |
| Test runner | Pytest 8.x |
| Statistical references | Statsmodels and SciPy from the locked project dependency ranges |
| Demo profile used by API integration tests | 5,000 deterministic synthetic users, seed 42 |
| Full local demo verified by implementation audit | 100,000 deterministic synthetic users, seed 42 |

## 3. Commands and results

### Compilation

```powershell
.\.venv\Scripts\python.exe -m compileall -q analytics backend scripts frontend tests
```

Result: passed; no syntax/import compilation error.

### Lint

```powershell
.\.venv\Scripts\python.exe -m ruff check analytics backend scripts frontend tests
```

Result: `All checks passed!`

### Format gate

```powershell
.\.venv\Scripts\python.exe -m ruff format --check analytics backend scripts frontend tests
```

Result: all 47 Python files already formatted.

### Full test suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result after the methodology/workbench expansion: **81 passed, 0 failed** in the final local run.

Test groups:

- 43 unit/statistical/methodology golden tests;
- 9 generated-data, reproducibility, confidentiality, secret and large-file tests;
- 29 FastAPI and Streamlit integration/smoke tests, including live-API execution of all nine pages.

One non-blocking third-party warning is present: FastAPI's current test client emits a Starlette deprecation warning about its HTTPX adapter. This is outside GrowthLab's runtime behavior and does not affect the test result.

### Docker

Attempted locally:

```powershell
docker --version
docker compose config --quiet
```

Result: Docker CLI is not installed on the local host. The CI workflow therefore owns the authoritative Compose validation and two-image build:

```yaml
docker compose config --quiet
docker compose build --pull
```

## 4. Statistical acceptance evidence

### Stable hash assignment

- The same `user_id` and experiment salt always produce the same bucket.
- Buckets remain in `[0, 99]`.
- A 20,000-user deterministic fixture is approximately 50/50 within a 1.5 percentage-point tolerance.
- Changing the experiment salt changes assignments, preventing accidental cross-experiment coupling.
- Invalid bucket configurations are rejected.

### A/A and SRM

- The balanced A/A fixture returns no statistically significant primary-metric difference and passes SRM.
- A deliberate 60/40 allocation against an expected 50/50 split is rejected before treatment-effect interpretation.
- SRM refuses to present an asymptotic result when expected cell frequency is below five.
- Channel, device and region composition checks expose practical distribution differences.

### Sample size, MDE and duration

- Baseline click rate 17%, absolute MDE +3 percentage points, two-sided alpha 0.05 and 80% power match an independent Statsmodels golden calculation.
- Sample-size-to-MDE numerical inversion reconstructs the planned MDE within tolerance.
- Traffic duration rounds up to complete weekly cycles and applies a two-week floor for the configured scenario.
- The response includes a pre-registration/novelty warning.

### Absolute and relative lift

Golden interpretation fixtures pass:

- 41.0% to 44.9% = **+3.9 percentage points** and approximately **+9.51% relative**;
- 17.0% to 23.5% = **+6.5 percentage points** and approximately **+38.24% relative**.

These are tested independently so the UI cannot silently confuse percentage points with relative percentages.

### Z-test and confidence interval

- The two-sample proportion Z statistic and two-sided p-value match a direct Statsmodels reference.
- The 95% unpooled difference interval contains the observed lift in the golden fixture.
- Statistical significance and business significance are separate result fields.
- A very large sample with a statistically detectable but sub-MDE effect does not receive a launch decision.
- A positive primary effect with a failed guardrail does not receive a launch decision.

### Experiment governance

The stored experiment response contains:

1. objective and treatment strategy;
2. core metric, downstream business metric, related metrics and guardrail;
3. sample-size/MDE/power and whole-cycle duration planning;
4. stable `user_id` hash allocation and 1:1 split;
5. A/A result and SRM result;
6. channel/device/region balance checks;
7. stratified analysis and Simpson-reversal warning capability;
8. novelty-effect guidance;
9. network/spillover guidance and cluster-randomization suggestion;
10. an explicit prohibition on stopping from repeated unadjusted interim p-value checks;
11. separate statistical, practical and guardrail gates.

## 5. Business-analysis acceptance evidence

### Referral funnel

- Funnel counts must be non-negative and monotonic.
- Step conversion, exposure conversion, drop-off, absolute change and relative change are independently verified.
- The synthetic dense-interface version is diagnosed at the invite-click step in the supported QA profile.
- Diagnosis is split into computed facts, interpretations, hypotheses and actions.
- The result explicitly states that a funnel break does not establish a UI causal mechanism and recommends instrumentation checks, qualitative research and a randomized experiment.

### Retention

- Exact-day D1/D3/D7/D30 flags are distinct from the D1-7 window metric.
- Retention values remain inside `[0, 1]`.
- Device mix-shift decomposition reconciles exactly:

```text
observed aggregate change
= structure effect
+ within-group effect
+ interaction effect
```

- The reconciliation error is verified at numeric tolerance.
- Product-path wording correctly says that current evidence does not identify first-use friction as the main driver; it does not claim to have proved the path has no issue.
- Feature-penetration analysis states correlation, names plausible confounders and routes causal evaluation to random assignment.

### Growth economics

The following formulas and failure cases are verified:

```text
CAC = incentive cost / activated acquired user
LTV30 = active days × daily active hours × value per hour × retention discount
LTV/CAC = LTV30 / CAC
Net ROI = (LTV30 - CAC) / CAC
```

- Zero CAC and negative inputs are rejected.
- Sensitivity output moves in the expected direction as acquisition cost changes.
- LTV/CAC and Net ROI are not mislabeled as the same quantity.

## 6. Data-quality acceptance evidence

The generator includes 17 built-in checks and the independent suite adds direct SQL verification. The verified invariants include:

- non-null and unique users;
- unique event IDs;
- activity and growth events do not predate signup;
- valid experiment groups and hash buckets;
- one assignment per user per experiment;
- outcomes occur after assignment;
- referral funnels are monotonic;
- retention is bounded;
- incentives and usage counts are non-negative;
- active days stay inside the defined range;
- governed metric definitions and both comparison periods exist;
- same seed reproduces analytical aggregates;
- the generator refuses tiny unsupported samples and accidental overwrite without `force`.

The full 100,000-user implementation audit produced 512,005 growth events, 240,000 experiment assignment/outcome records and a 91-day normalized executive trend with all 17 built-in quality checks passing.

## 7. API and UI acceptance evidence

Verified API behaviors:

- `/health` and `/openapi.json`;
- metric catalog and metric tree;
- normalized growth trend, target gap, source contribution and anomaly claim boundary;
- referral summary/version/funnel diagnosis;
- ROI summary and sensitivity validation;
- retention summary, cohort definitions/maturity, governed segmentation, decomposition and path funnel;
- correlational feature analysis;
- stored and ad-hoc experiment evaluation;
- GROWTH methodology, evidence ladder and problem playbooks;
- editable aggregate funnel and Mix-Shift workbench contracts;
- data-quality status;
- useful 404/422 responses;
- whitelist rejection of arbitrary SQL-like dimension input.

The Streamlit application starts headlessly and returns `ok` from its health endpoint even when the API is unavailable, exercising its graceful error state. The application is not required to reach a cloud service or use credentials for this smoke test.

## 8. Privacy and public-release acceptance evidence

The public-repository scan checks source, SQL, Markdown, configuration and tracked artifacts for:

- protected real-company/product identifiers from the original business context;
- internal scale, real reward and experiment-size markers;
- common API/cloud/GitHub credential formats;
- private keys and credential-bearing database URLs;
- committed `.env` files other than `.env.example`;
- publication candidates larger than 10 MiB.

Result: no finding. This is a heuristic safeguard, not a substitute for the repository owner's contractual confidentiality review before publication.

## 9. Defects found and resolved during QA

| Finding | Severity | Resolution | Regression evidence |
|---|---:|---|---|
| Some referral events could occur before inviter signup because campaign dates were generated independently | Blocker | Eligible inviters are now constrained to users registered before campaign start; a built-in temporal check was added | Direct event-to-user SQL assertion and full data-quality suite pass |
| Small demo profiles could obscure the intended invite-click funnel break with downstream sampling noise | Major | Diagnosis selects the earliest material break and the supported API QA profile uses 5,000 users | Referral API integration test passes |
| A/A synthetic outcomes could exceed the practical tolerance by chance | Blocker | A/A fixture now uses a deterministic near-null result while retaining hash allocation and SRM checks | Stored A/A reports pass; independent equal-rate golden test passes |
| Return-visit output could violate the ordered demonstration path | Major | Generated return visit is constrained to the supported path semantics | Funnel monotonicity checks pass |

## 10. Residual limitations

1. Docker images were not built on the local machine because Docker CLI is absent. Remote CI must be green before treating container delivery as verified.
2. The data is synthetic and validates the analytical method, not commercial impact at any real company.
3. Z-test and normal-approximation confidence intervals are intended for adequately sized samples. Small-cell SRM is guarded; analysts should use an exact method for genuinely sparse outcome experiments.
4. Secret scanning is regex-based and should be complemented by GitHub secret scanning where available.
5. Network-effect guidance is present, but the demo does not model a real social graph or estimate cluster-level standard errors.

## 11. Final release checklist

- [x] Python compilation passes.
- [x] Ruff lint passes.
- [x] Ruff formatting gate passes.
- [x] 81 local tests pass.
- [x] Statistical golden tests pass.
- [x] Data generation and 17 built-in data checks pass.
- [x] FastAPI smoke and contract tests pass.
- [x] Streamlit headless startup passes.
- [x] Confidentiality, secret and large-file scans pass.
- [x] GitHub Actions workflow is present.
- [ ] First remote GitHub Actions run is green.
- [ ] Remote Docker Compose validation and image builds are green.

**Release recommendation:** publish the repository, wait for the first GitHub Actions run, and only advertise “Docker-verified” after both CI jobs are green.
