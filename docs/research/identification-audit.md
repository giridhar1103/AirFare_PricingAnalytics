# Fare-response identification audit

## Decision

No DOT-derived fare coefficient is approved for use as demand elasticity in FareLab release 1.

## Results

| Model | Fare coefficient | Supporting diagnostic | Product decision |
| --- | ---: | --- | --- |
| Passenger two-way fixed effects | +0.05845 | 80,872 observations and 3,756 route-carrier entities | Rejected |
| Market-share two-way fixed effects | +0.02787 | Same non-disruption panel policy | Rejected |
| Leave-one-route-out network-fare IV | +0.02136 | Partial F 1455 and partial R squared 0.135 | Research only |

The expected own-price demand sign is negative. All three estimates are nonnegative. A strong first stage does not establish a valid exclusion restriction, and it does not make a nonnegative second-stage coefficient economically usable.

## Interpretation

Airlines adjust fares, capacity, schedules, and inventory using private demand information. Quarterly public DOT data does not observe search demand, booking curves, inventory controls, or all schedule-quality changes. The fare coefficient therefore mixes demand response with the carrier's endogenous commercial response.

Fixed effects remove persistent route-carrier differences and common period shocks, but they do not solve this simultaneity. The research result is still valuable because it determines what the product must not claim.

## Product control

- The public Model Lab displays all three coefficients and their rejected status.
- The scenario simulator does not read any fitted fare coefficient.
- Elasticity defaults to an explicit analyst assumption of -1.0.
- A governed range from -1.5 to -0.5 is labeled sensitivity, not confidence.
- Scenario output is labeled assumption based and noncausal.

## Future identification options

A causal extension would require a defensible source of fare variation, such as a well-supported natural experiment, policy shock, or schedule change with a documented exclusion argument. Model complexity alone is not a substitute for identification.
