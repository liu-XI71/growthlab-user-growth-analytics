# GrowthLab progress log

## 2026-08-09

- Confirmed the public portfolio scope: user-growth metrics, referral funnel diagnostics, retention decomposition, and a complete A/A-to-A/B experimentation workflow.
- Enforced a strict public-data boundary: no company names, business-line names, internal URLs, real incentive amounts, or proprietary datasets.
- Split delivery across two independent workstreams: core architecture and implementation; independent quality assurance and statistical validation.
- Selected a compact stack for the 12-hour timebox: DuckDB, SQL, FastAPI, Streamlit, Plotly, Statsmodels, SciPy, Pytest, Docker Compose, and GitHub Actions.
- Started deterministic synthetic-data, analytics, API, UI, documentation, and validation work in parallel.

## 2026-08-10

- Created the public repository `liu-XI71/growthlab-user-growth-analytics` and published the complete 91-file source tree.
- Verified all remote file Blob hashes against the local Git index and corrected the one transport-corrupted large-file Blob before release acceptance.
- Completed GitHub Actions CI run `31364099680`: Python 3.12 compilation, Ruff lint and format checks, the full statistical/data/API/UI test suite, artifact upload, Docker Compose validation, and both image builds passed.
- Recorded the remote release evidence in the QA report and approved the repository for portfolio use.

## Definition of done

- The demo runs from a clean checkout without cloud credentials.
- The referral and retention case studies are reproducible from generated data.
- A/A and A/B workflows cover objective, metrics, sample size, duration, hash assignment, balance, SRM, inference, business significance, guardrails, and decision.
- Tests verify statistical calculations, data quality, API behavior, and sensitive-information boundaries.
- Documentation includes a metric dictionary, architecture, data card, case studies, interview guide, and final audit.
- A public GitHub repository is created only after all sensitive-data and validation gates pass. Completed at `https://github.com/liu-XI71/growthlab-user-growth-analytics`.
