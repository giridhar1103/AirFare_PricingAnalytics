# FareLab research report source

## Executive recommendation

Build FareLab as an evidence-led U.S. route pricing decision lab using historical DB1B fares and T-100 traffic and capacity. Add DB1C as a clearly separate monthly monitoring product after the July 2025 survey transition. Use a time-validated conditional demand forecast, publish the failed fare-response identification audit, and make the capacity-constrained scenario simulator require explicit analyst assumptions.

The project is feasible and professionally relevant if it avoids three unsupported claims: causal elasticity, airline profit, and real-time dynamic pricing. Public DOT data supports market pricing analysis and route scenario planning, not the inventory and customer-level decisions of a production revenue management platform.

## Decision framework

The application answers one question: which route-carrier markets deserve a fare test, share defense, capacity review, or hold decision, and what passenger, revenue-proxy, and load-factor changes are implied under a transparent scenario?

The workflow is detect, investigate, model, simulate, and document. This is stronger than a collection of dashboard tabs because each page contributes to a single analyst decision.

## Evidence synthesis

The Bureau of Transportation Statistics states that DB1B was a quarterly 10% sample before July 2025 and DB1C became a monthly 40% sample at that point. This is a material survey break. The two products should have separate quality histories and model monitoring rather than being appended as if they were homogeneous.

T-100 supplies monthly operating passengers, seats, departures, and route attributes. BTS explicitly states that it contains no carrier financial information. FareLab therefore uses a revenue proxy, fare multiplied by passengers, and labels it as calculated rather than reported revenue.

Airline fare and demand are jointly determined. Published airline elasticity research warns that failing to account for price endogeneity can produce biased recommendations. FareLab tested passenger fixed effects, market-share fixed effects, and a network-fare IV sensitivity. All three fare coefficients were nonnegative. The application treats that as an identification failure and does not use the coefficients as demand elasticity.

The ML extension has a narrower purpose: improve next-period passenger forecasting over a transparent seasonal baseline. Expanding-window evaluation prevents future leakage. The gradient boosting model achieved 5.10% held-out WAPE versus 15.40% for the seasonal naive baseline. The model does not choose a fare. Scenario results use a user-controlled constant-elasticity assumption, capacity constraints, support checks, and a sensitivity range.

## Product and visual direction

The visual design should resemble a clean commercial analytics workspace. Important decisions appear at the top, supporting evidence follows, and filters coordinate views. A light canvas, restrained palette, direct chart labels, visible uncertainty, and accessible table alternatives create a professional identity without imitating an existing project.

## Technical direction

The pipeline uses immutable source files, checksums, DuckDB, version-controlled SQL marts, Python econometrics and forecasting, and compact versioned JSON exports. The React and TypeScript frontend remains static-first for its first release. It deploys at `/farelab` without adding a new long-running service or touching active ports.

## Build sequence

1. Build the product shell and scenario math against an unmistakably labeled deterministic fixture.
2. Complete a one-period DB1B and T-100 ingestion spike and publish join-quality results.
3. Expand to a controlled route panel, fit the interpretive model, and replace fixture artifacts.
4. Add the route opportunity queue and time-validated forecast comparison.
5. Perform accessibility, model, data-quality, and path-based deployment checks.

## Go or no-go conclusion

Go. FareLab is a stronger U.S.-market portfolio project than the grocery concept for airline, travel, revenue, and pricing roles. Its professional edge comes from disciplined scope, mathematical transparency, source contracts, and a decision-oriented interface, not from adding more algorithms.
