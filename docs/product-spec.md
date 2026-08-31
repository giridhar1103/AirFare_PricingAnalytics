# FareLab definitive product specification

## 1. Product objective

FareLab turns public U.S. airline fare, passenger, and capacity data into a defensible route pricing workflow:

1. Detect a route or carrier market that deserves attention.
2. Explain the observed fare, demand, capacity, and competition evidence.
3. Forecast next-quarter demand conditional on planned inputs.
4. Audit whether price response is identified before using it.
5. Test a feasible fare and capacity scenario with explicit assumptions.

The primary user is a pricing, revenue, network, or commercial analyst with one to three years of experience. The interface should help this user prepare a route review, not replace commercial judgment.

## 2. Core decision unit

The initial decision unit is:

```text
operating carrier x directional airport market x calendar quarter
```

Airport-market identifiers are preferred over airport codes for longitudinal work because DOT identifiers are more stable. Direction can be normalized for route-level views when the business question does not require directional differences.

## 3. Primary user outputs

### Opportunity queue

Each row has one action, a concise rationale, model support, and uncertainty:

- Evaluate yield
- Protect share
- Review capacity
- Review fare position
- Hold and monitor

The ranking is evidence based. It does not claim to be an automated price optimizer.

### Market explorer

The user selects a route, carrier, and period. The page shows:

- Passenger-weighted market fare
- T-100 passengers and available seats
- Load factor
- Carrier market share
- Market concentration
- Fare index versus competing carriers
- Direct-service share
- Seasonality and trend

### Model lab

The page compares the time-validated demand forecast with a seasonal baseline and exposes the fare-response identification audit. Failed sign checks remain visible and no rejected coefficient enters the scenario model.

### Scenario lab

Inputs:

- Route and carrier
- Fare change between -15% and +15%
- Capacity change between -20% and +20%
- Competitor fare index change between -10% and +10%
- Analyst price-elasticity assumption between -2.0 and -0.2
- Demand regime: base, soft, or strong
- Optional analyst unit cost assumption

Outputs:

- Assumption-based passengers
- Revenue proxy
- Load factor
- Change from baseline
- Sensitivity range
- Data-support status
- Break-even elasticity
- Calculation trail and interpretation boundary

### Forecast lab

The baseline forecast and ML challenger predict next-period route demand. Evaluation is time ordered and reports MAE, WAPE, bias, and interval coverage. ML remains a supporting demonstration and does not set the recommended fare.

## 4. Page map

| Route | Purpose | First release |
| --- | --- | --- |
| `/farelab` | Opportunity overview and portfolio health | Yes |
| `/farelab/markets` | Route and carrier investigation | Yes |
| `/farelab/models` | Forecast benchmark and identification audit | Yes |
| `/farelab/scenario` | Interactive fare and capacity simulation | Yes |
| `/farelab/methodology` | Sources, formulas, validation, and limitations | Yes |

## 5. Visual language

FareLab uses a light analytical workspace instead of a generic dark dashboard.

- Warm off-white canvas and white analytical surfaces
- Deep navy text for hierarchy and legibility
- Blue for quantitative series and selection
- Teal for supported opportunities
- Amber for review states and uncertainty
- Red only for material risk or invalid support
- Direct chart labels where space permits
- Tables alongside complex charts for accessibility
- Sparse KPI row with no more than five headline metrics
- Consistent route and carrier context across all pages

The overview follows an F-shaped reading order: decision context first, action queue second, supporting evidence third. Filters stay compact and coordinated across charts.

## 6. Recommendation policy

An opportunity action is emitted only when the descriptive evidence gates pass:

- At least 12 observed route-carrier periods
- At least 10,000 quarterly passengers
- At least 3% carrier market share
- A supported competitor-fare comparison
- Conditional forecast inputs and interval are finite and ordered
- Data source and vintage are present

Then a transparent score combines:

```text
yield review score
  + fare position versus competitors
  + positive demand and share movement
  + stable forecast support
  - capacity constraint risk
  - concentration and uncertainty penalty

capacity review score
  + persistent high load factor
  + positive time-validated demand trend
  - weak schedule completion
  - high forecast uncertainty
```

Score components remain visible in the interface. A score is an analyst triage aid, not a causal estimate.

## 7. Release plan

### Release 1: working decision product

- DB1B and T-100 ingestion for selected domestic markets
- Governed route-quarter marts
- Opportunity queue
- Route explorer
- Fare-response identification audit
- Interactive simulator
- Static deployment under `/farelab`

### Release 2: strong portfolio version

- National route coverage
- Competition and market-concentration features
- Time-ordered baseline and ML forecast comparison
- Forecast calibration and backtest evidence
- Scenario bookmarking and CSV export

### Release 3: advanced analytical extension

- DB1C monthly monitoring as a separate post-transition product
- Carrier-entry or schedule-shock event study
- Instrumental-variable research track if a defensible instrument is established
- Model drift monitoring and data-quality history

## 8. Definition of done

FareLab is portfolio ready when:

- Every visible number traces to a versioned artifact and source vintage.
- Development fixtures are absent from the production build.
- Scenario math has automated boundary and monotonicity tests.
- Time validation has no future leakage.
- All claims distinguish observed, calculated, model-implied, and assumed values.
- The app works by keyboard and charts have table or text alternatives.
- The production build resolves correctly under `/farelab`.
- Existing host ports, services, and routes are unchanged.
