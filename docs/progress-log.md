# GrowthLab progress log

## 2026-08-09

- Confirmed the public portfolio scope: user-growth metrics, referral funnel diagnostics, retention decomposition, and a complete A/A-to-A/B experimentation workflow.
- Enforced a strict public-data boundary: no company names, business-line names, internal URLs, real incentive amounts, or proprietary datasets.
- Split delivery across two independent workstreams: core architecture and implementation; independent quality assurance and statistical validation.
- Selected a compact stack for the 12-hour timebox: DuckDB, SQL, FastAPI, Streamlit, Plotly, Statsmodels, SciPy, Pytest, Docker Compose, and GitHub Actions.
- Started deterministic synthetic-data, analytics, API, UI, documentation, and validation work in parallel.

## Definition of done

- The demo runs from a clean checkout without cloud credentials.
- The referral and retention case studies are reproducible from generated data.
- A/A and A/B workflows cover objective, metrics, sample size, duration, hash assignment, balance, SRM, inference, business significance, guardrails, and decision.
- Tests verify statistical calculations, data quality, API behavior, and sensitive-information boundaries.
- Documentation includes a metric dictionary, architecture, data card, case studies, interview guide, and final audit.
- A public GitHub repository is created only after all sensitive-data and validation gates pass.
