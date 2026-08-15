# Growth Analytics Decision Platform

**用户增长全链路分析与实验决策平台**

A business-first analytics portfolio built around two anonymized growth cases: referral acquisition and new-user retention. It demonstrates how monitoring signals become metric trees, diagnostic evidence, falsifiable hypotheses, controlled experiments, economic decisions, and reusable governance.

> This public repository contains anonymized narratives and deterministic synthetic data. It does not contain employer production data, code, dashboards, or confidential metric definitions.

## Live dashboard

[Open the six-module dashboard](https://liu-xi71.github.io/growth-analytics-decision-platform/)

![Dashboard overview](docs/assets/v2-overview.png)

## What this portfolio proves

- Business outcomes are separated from mechanism, diagnostic, guardrail, and data-quality metrics.
- Funnel and segment analyses retain negative evidence instead of forcing every chart into a positive story.
- Benchmark-user differences are treated as correlation and hypothesis generation, not causality.
- A/B decisions include the hypothesis, sample and duration, trust checks, effect, business threshold, and guardrail.
- First-month `LTV/CAC` is correctly distinguished from net ROI.
- Every public claim is labelled as disclosed narrative, anonymized value, synthetic detail, or unresolved definition.

## The two cases

| Case | Business question | Key diagnosis | Experiment | Decision |
|---|---|---|---|---|
| Referral growth | How can we expand acquisition when external traffic supply declines? | A more complex page reduced invite CTR to 17%; ~95% share success ruled out the downstream sharing step. | Simplified first-screen CTA; million-scale anonymized sample, 14 days; invite CTR 17% → 23.5%, `p < 0.05`. | Launch and iterate; month-one LTV/CAC 2.18 vs external benchmark 1.90. |
| New-user retention | Why did paid-acquisition users stop returning? | Device mix shift explained an important part; product-path conversions remained stable; benchmark users had 2.5× profile/follow penetration. | Exit-page profile/follow prompt; about 300K samples, 14 days; Day 1–7 window retention significantly improved, `p < 0.05`. | Roll out and iterate; absolute retention lift is intentionally not fabricated. |

## Architecture

```text
React + Vite + ECharts dashboard
          │
          ├── static privacy-safe JSON → GitHub Pages
          └── FastAPI /api/v2          → local full-stack mode
                         │
                      DuckDB
                         │
          deterministic synthetic generator + SQL marts
```

## Local quick start

The simplest route is Docker:

```powershell
docker compose up --build
```

Open `http://localhost:8501`. The default 100K-user dataset may need 3–4 minutes on first boot. For a faster 5K demo:

```powershell
$env:GROWTHLAB_DEMO_USERS='5000'
docker compose up --build
```

For complete Chinese beginner instructions, see [README_zh.md](README_zh.md).

## Quality gates

- Python statistical/data/API tests with coverage gate
- React lint, TypeScript check, and production build
- Deterministic data and strict JSON export
- Docker Compose configuration and image builds in CI
- Browser checks for six routes, scrolling, layout, and console errors
- Privacy scan for employer names, raw scale, secrets, and real incentive values

## Documentation

- [Chinese beginner guide](README_zh.md)
- [Recruiter review guide](docs/recruiter-review-guide_zh.md)
- [V2 product specification](docs/v2-product-spec_zh.md)
- [Referral case](docs/case-study-referral.md)
- [Retention case](docs/case-study-retention.md)
- [Public methodology benchmark](docs/public-methodology-benchmark_zh.md)
- [Metric dictionary](docs/metric-dictionary.md)
- [QA report](docs/qa-report.md)

## License and boundary

Code is released under the MIT License. Public demo data is synthetic and is provided only to reproduce the analysis workflow. Company names, internal IDs, raw DAU scale, real incentive amounts, and unreleased experiment values are excluded.
