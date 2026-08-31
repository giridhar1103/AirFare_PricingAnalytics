# FareLab definitive build plan

## Goal

Deliver a public U.S. airline route pricing decision product at `giriworks.com/farelab` that lets a user detect a market issue, inspect observed evidence, review a time-validated conditional forecast, and stress test fare and capacity plans with explicit assumptions.

## Scope locked for release 1

- U.S. domestic directional airport markets
- Direct itineraries only
- Reporting, ticketing, and operating carrier aligned
- DB1B history through 2025 Q2
- T-100 traffic and capacity at route-carrier-quarter grain
- 2020 and 2021 visible in trends but excluded from the default baseline fit
- Revenue proxy, not accounting revenue or historical profit
- Static public application with an offline pipeline

## Phase 1: product and architecture

Status: complete

Outputs:

- Decision question and user workflow
- Page map and visual language
- Data, model, artifact, and deployment contracts
- Claim-source ledger and research report

Acceptance:

- Product does not claim real-time dynamic pricing, causal elasticity, or profit optimization.
- Every planned output is classified as observed, calculated, model-implied, or assumed.

## Phase 2: application vertical slice

Status: complete

Outputs:

- Opportunity overview
- Market explorer
- Forecast and identification workbench
- Interactive scenario lab
- Methodology and risk register
- Responsive navigation and accessible table alternatives

Acceptance:

- Development values carry an unavoidable fixture label.
- Fare and capacity controls enforce supported bounds.
- Python and TypeScript calculations agree by contract.
- No em dash or en dash appears in site copy.

## Phase 3: governed multi-period panel

Status: complete

Work:

1. Download DB1B quarters for 2017 through 2025 Q2.
2. Download T-100 years for 2017 through 2025.
3. Record checksum, byte count, schema, row count, and source vintage for every file.
4. Load normalized source tables into DuckDB.
5. Apply direct-itinerary and aligned-carrier scope.
6. Build route-carrier-quarter fare, capacity, share, HHI, competitor fare, and revenue-proxy measures.
7. Publish join, exclusion, duplicate, range, and null audits by period.

Acceptance:

- Passenger-weighted source join is at least 98% in each production period.
- Duplicate canonical keys equal zero.
- Excluded codeshare share is visible by period and carrier.
- Survey-transition data is not silently combined.

## Phase 4: interpretable price-sensitivity model

Status: complete, with no coefficient approved for scenario use

Work:

1. Fit the global two-way fixed-effects benchmark.
2. Fit a market-share fixed-effects sensitivity model.
3. Test a leave-one-route-out network-fare instrument as a research sensitivity.
4. Apply an economic sign gate before allowing any estimate into the product.
5. Publish the rejected coefficients and identification reasoning in model cards.

Acceptance:

- Three tested coefficients and their decisions are visible.
- No nonnegative fare coefficient is presented as demand elasticity.
- Scenario elasticity is explicitly analyst supplied.
- Scenario outputs remain finite, ordered, and capacity constrained.

## Phase 5: forecasting and ML challenger

Status: complete

Work:

1. Build seasonal-naive and regularized-linear baselines.
2. Train a histogram gradient boosting demand challenger using lagged demand, fare, seats, distance, season, HHI, share, and competitor fare.
3. Evaluate with expanding time windows and no future leakage.
4. Report MAE, WAPE, bias, and interval coverage by volume band.
5. Retain ML only if it improves WAPE without material bias instability.

Acceptance:

- Forecast features are available at prediction time.
- The ML model never sets a fare automatically.
- Baseline and challenger performance remain visible side by side.

## Phase 6: production artifacts and interface integration

Status: complete

Work:

1. Export a compact overview with route history, conditional forecasts, data quality, and the identification audit.
2. Reject fixture mode during the production export.
3. Replace the development fixture with observed and model-backed data.
4. Add route selection, linked scenarios, accessible data tables, and responsive views.
5. Complete keyboard, contrast, responsive, and reduced-motion review.

Acceptance:

- Every public number traces to a build identifier and source vintage.
- Browser payloads stay within the documented size limits.
- Direct URL refresh works for every page under `/farelab`.

Result:

- Production artifact is 409 KB against a 500 KB budget.
- Eight desktop and mobile interaction tests plus five workspace accessibility audits pass.
- Production dependencies have zero known npm audit vulnerabilities.

## Phase 7: isolated deployment

Status: pending

Work:

1. Build and verify the static artifact.
2. Review the current host route and fallback configuration again immediately before deployment.
3. Publish only the FareLab artifact at `/farelab`.
4. Run smoke tests for HTML, JavaScript, CSS, data, deep links, and simulator behavior.
5. Retain the prior artifact for atomic rollback.

Acceptance:

- No existing port, service, or project is changed.
- Existing portfolio routes continue to pass smoke tests.
- Production never exposes the development fixture.

## Planned Git history

Commits will follow coherent review units once the GitHub remote and author identity are supplied:

1. `docs: define FareLab product and analytical contracts`
2. `feat: add interactive route pricing workspace`
3. `feat: add verified DOT ingestion and route marts`
4. `feat: add price sensitivity model and diagnostics`
5. `feat: add time-validated demand forecast challenger`
6. `test: add artifact, accessibility, and deployment checks`

No commit message, source comment, or project copy will refer to an automated coding agent.
