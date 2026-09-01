# FareLab

FareLab is a U.S. airline route pricing and revenue analytics application built from public U.S. Department of Transportation data. It helps an analyst identify route-level pricing opportunities, inspect the evidence, and test fare or capacity scenarios with transparent assumptions.

## Decision question

> Which U.S. route and carrier markets deserve a yield, share, fare-position, or capacity review, and how does a proposed plan behave under explicit commercial assumptions?

FareLab is intentionally not presented as a production revenue management system. Public DOT data does not contain live inventory, booking curves, fare-class availability, ancillary revenue, or route-level accounting cost. The app makes this boundary visible wherever a user interprets a scenario.

## Product outputs

- An evidence-ranked route opportunity queue
- A route and carrier market explorer
- A forecast and price-identification workbench
- An assumption-driven fare and capacity scenario simulator
- A time-validated conditional demand forecast with forward-tested intervals
- A grounded AI decision brief that turns a governed scenario into an analyst handoff
- A methodology page with formulas, data contracts, limitations, and model cards

## Architecture

```text
DOT DB1B and DB1C fares     DOT T-100 traffic and capacity
             |                         |
             v                         v
        Raw immutable files and checksums
                       |
                       v
                  DuckDB and SQL
                       |
          route-quarter analytical marts
                       |
          Python econometrics and ML
                       |
        versioned JSON model artifacts
                |              |
                v              v
      React and TypeScript   FastAPI scenario
           web app           validation API
                |              |
                +------> Claude structured brief
```

The analytical application remains static-first. Data ingestion and model training happen offline, and the web build reads a versioned aggregate artifact. A small isolated API supports the optional AI decision brief. The API reloads the governed route record, recalculates the scenario in Python, and gives Claude only a constrained narrative task. It does not expose an API key to the browser or let the language model change calculations.

## Current analytical result

The production mart contains 238,526 route-carrier-quarter rows across 8,639 directional routes, 21 carriers, and 2017 Q1 through 2025 Q2. It was built from 34 DB1B quarters and nine T-100 annual extracts, representing more than 223 million staged source rows. Passenger-weighted fare and traffic join coverage is above 99% in every modeled period.

The project deliberately reports an identification failure. Passenger fixed effects, market-share fixed effects, and an instrumental-variable sensitivity specification all produced nonnegative fare coefficients. Those signs are inconsistent with an identified downward demand curve. FareLab does not use them as elasticity.

Instead, the production product separates two valid tasks:

- Observed route, fare, traffic, capacity, share, concentration, and revenue-proxy analytics
- A conditional passenger forecast that achieved 5.10% held-out WAPE versus 15.40% for the seasonal naive baseline
- A nominal 80% interval calibrated on 50,463 observations from the 2023 and 2024 folds, with 74.82% coverage on the untouched 12,329-observation 2025 H1 evaluation period
- A scenario simulator that requires an explicit analyst elasticity assumption and shows a governed sensitivity range
- An AI-generated decision brief whose recommendation and quantitative evidence are enforced by application code

This distinction is the central analytical finding, not a limitation hidden from the interface.

## Repository map

```text
config/              project and data-source configuration
api/                 isolated decision-brief API and policy validation
data/                local data zones and data instructions
docs/                product, methodology, research, and deployment notes
evals/               AI evaluation cases and aggregate results
models/              trained artifacts created by the pipeline
pipeline/farelab/    Python ingestion, validation, modeling, and export code
sql/                 version-controlled analytical transformations
tests/               Python tests and repository policy checks
web/                 Vite, React, and TypeScript application
```

## Local development

Requirements:

- Node.js 18 or later
- Python 3.11 or later
- DuckDB 1.4 or later

```bash
make web-install
make web-dev
```

To run the repository policy and model math tests without installing the analytics stack:

```bash
python3 -m unittest discover -s tests -v
```

The browser suite covers desktop and mobile navigation, nested-route refreshes, scenario controls, the decision-brief workflow, viewport containment, and automated WCAG A and AA audits across all five workspaces:

```bash
cd web
npx playwright install chromium
npm run build
npm run test:e2e
```

To reproduce the controlled 2024 source spike after downloading the files:

```bash
python3 -m pipeline.farelab.ingest db1b --year 2024 --quarter 4
python3 -m pipeline.farelab.t100_download --year 2024 --period All
make warehouse-spike
```

To rebuild the full warehouse, models, and production web artifact after source files are available:

```bash
make warehouse
make elasticity market-share iv-sensitivity forecast export
make check
```

To run the decision-brief API locally, install the API optional dependencies and provide `ANTHROPIC_API_KEY` through the environment:

```bash
python3 -m venv .venv-api
.venv-api/bin/pip install 'anthropic>=0.97,<1' 'fastapi>=0.116,<1' \
  'pydantic>=2.11,<3' 'uvicorn[standard]>=0.35,<1'
.venv-api/bin/uvicorn api.app:app --host 127.0.0.1 --port 8010
```

See [the AI decision-brief notes](docs/ai-decision-brief.md) for the grounding contract, failure behavior, and evaluation criteria.

## Portfolio positioning

FareLab is designed as evidence for U.S. pricing, revenue management analytics, and commercial analytics roles. It demonstrates SQL transformation, data contracts, panel-model judgment, time-ordered forecasting, scenario math, model governance, API delivery, and concise business communication. It does not claim airline inventory optimization, ATPCO fare filing, booking-curve forecasting, or production revenue management experience because the public data cannot support those tasks.

## Deployment target

The production target is `https://giriworks.com/farelab`. See `docs/deployment.md` for the isolated build and integration contract. Deployment changes are deliberately separate from this repository so existing services are not modified during development.

## License and attribution

Application code is released under the MIT License. Source data remains subject to the terms and definitions published by the Bureau of Transportation Statistics. FareLab links to the official source pages and reports the data vintage used by each artifact.

Detailed results are recorded in [the production data audit](docs/research/production-data-audit.md) and [the fare-response identification audit](docs/research/identification-audit.md).

Designed and built by Giridhar Achuthananda.
