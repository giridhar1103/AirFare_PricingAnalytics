# Methodology

## Analytical scope

FareLab estimates route-level relationships from public market data. It does not observe individual shopping sessions, booking-class inventory, customer willingness to pay, or airline route cost. Results support market review and scenario planning, not automated fare filing.

## Core measures

### Passenger-weighted fare

For route-carrier-period group \(g\):

```text
weighted_fare_g = sum(fare_i * sampled_passengers_i) / sum(sampled_passengers_i)
```

Fares represent the ticket value described by BTS. Optional-service fees such as baggage fees are not included.

### Load factor

```text
load_factor = T100_passengers / T100_available_seats
```

The metric is valid only after aligning service class, carrier, airport pair, and period. Invalid seat counts and implausible ratios are quarantined.

### Revenue proxy

```text
revenue_proxy = weighted_market_fare * T100_passengers
```

This is a decision-support proxy, not reported airline revenue. It excludes ancillaries and can differ from accounting revenue because fare and traffic sources have different survey designs.

### Market concentration

For market shares \(s_k\) expressed as fractions:

```text
HHI = sum(s_k ^ 2)
```

The application displays both the 0 to 1 value used by models and the 0 to 10,000 convention familiar in competition analysis.

## Fare-response identification audit

The first interpretable specification is a log-log route-carrier panel:

```text
log(passengers_it) =
    beta_price * log(fare_it)
  + beta_capacity * log(seats_it)
  + beta_competitor * log(competitor_fare_index_it)
  + route_carrier_effect_i
  + calendar_period_effect_t
  + error_it
```

Route-carrier fixed effects absorb persistent market characteristics. Calendar effects absorb common shocks. Standard errors are clustered at the route-carrier level.

Three specifications were evaluated:

| Specification | Fare coefficient | Decision |
| --- | ---: | --- |
| Passenger fixed effects | +0.058 | Rejected for elasticity use |
| Market-share fixed effects | +0.028 | Rejected for elasticity use |
| Network-fare IV sensitivity | +0.021 | Research only |

All three estimates have the wrong economic sign for a downward-sloping demand response. The IV first stage is statistically strong, but that does not validate the exclusion restriction or repair the nonnegative second-stage result. Airlines change fares and capacity in response to private demand information that the quarterly public panel does not observe. The estimates therefore follow endogenous commercial decisions rather than identify a causal demand curve.

No DOT-derived coefficient is used by the scenario simulator. This is a governed model decision and is visible in the product.

## Scenario model

Let baseline price and passengers be \(P_0\) and \(Q_0\), proposed fare change be \(d_p\), capacity change be \(d_s\), and analyst-supplied elasticity be \(e\).

```text
P1 = P0 * (1 + d_p)
Q_price = Q0 * (P1 / P0) ^ e
Seats1 = Seats0 * (1 + d_s)
Q1 = min(Q_price * demand_regime_factor, Seats1)
Revenue0 = P0 * Q0
Revenue1 = P1 * Q1
LoadFactor1 = Q1 / Seats1
```

The capacity constraint is explicit. If unconstrained demand exceeds available seats, the simulator reports spill risk rather than silently accepting a load factor above 100%.

For a constant-elasticity model without a capacity constraint, the local revenue break-even elasticity is -1. When elasticity is greater than -1, a small fare increase raises model-implied revenue. When it is less than -1, a small fare increase lowers model-implied revenue.

### Sensitivity range

FareLab computes low and high scenario outcomes using a governed assumption range of -1.5 to -0.5 by default. This range is not a confidence interval. Because price changes reverse the direction of the elasticity effect, endpoints are evaluated and sorted rather than assigned by name.

Competitor fare movement enters through a governed cross-price assumption of 0.15. It is not estimated from the rejected DOT fare-response models and is identified in the calculation trail.

## Forecasting and ML

The forecasting task predicts next-quarter passengers at the route-carrier level, conditional on actual or planned future fare, seats, competitor fare, and market structure inputs.

Models evaluated:

- Same-quarter seasonal naive baseline
- Regularized linear model
- Histogram gradient boosting regressor

Features include one-quarter and seasonal passenger lags, planned fare and seats, competitor fare, prior market share, HHI, distance, carrier, and calendar quarter.

Validation uses expanding time windows. A model never trains on a period later than its evaluation period. Reported metrics are:

```text
MAE = mean(abs(actual - forecast))
WAPE = sum(abs(actual - forecast)) / sum(abs(actual))
Bias = sum(forecast - actual) / sum(actual)
Coverage = share(actual within prediction interval)
```

Expanding-window holdouts cover 2023, 2024, and the first half of 2025. The gradient boosting champion achieved 5.10% aggregate WAPE and 1.79% bias across 62,792 held-out rows. The seasonal naive baseline produced 15.40% WAPE. An out-of-fold absolute-log-error calibration produces an 80% interval with 80.0% empirical holdout coverage.

This remains a conditional forecast. Changing the future fare input does not make the resulting forecast difference causal.

## Pandemic treatment

Calendar years 2020 and 2021 are treated as a structural disruption. The default model-development window excludes them from the standard elasticity fit and reports a sensitivity model that includes a disruption indicator. Those periods remain visible in descriptive trend views with a clear annotation.

## Support and guardrails

- Fare changes are limited to -15% through +15%.
- Capacity changes are limited to -20% through +20%.
- A scenario outside the route's historical fare range is labeled extrapolation.
- Markets require at least 10,000 quarterly passengers, 3% carrier share, a competitor fare, and complete model inputs to enter the public route set.
- Optional unit cost is user supplied and clearly separated from observed data.
- Scenario outputs use assumption-based language, never guaranteed or causal language.
