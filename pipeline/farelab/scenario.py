"""Transparent, capacity-constrained route scenario mathematics."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ScenarioInput:
    baseline_fare: float
    baseline_passengers: float
    baseline_seats: float
    elasticity: float
    elasticity_low: float
    elasticity_high: float
    fare_change: float = 0.0
    capacity_change: float = 0.0
    demand_factor: float = 1.0
    unit_cost: float | None = None


@dataclass(frozen=True)
class ScenarioOutput:
    proposed_fare: float
    unconstrained_passengers: float
    passengers: float
    passenger_low: float
    passenger_high: float
    seats: float
    load_factor: float
    baseline_revenue_proxy: float
    revenue_proxy: float
    revenue_low: float
    revenue_high: float
    revenue_change_pct: float
    spill_passengers: float
    contribution_proxy: float | None


def _passenger_response(
    baseline_passengers: float,
    price_ratio: float,
    elasticity: float,
    demand_factor: float,
) -> float:
    return baseline_passengers * price_ratio**elasticity * demand_factor


def _validate(inputs: ScenarioInput) -> None:
    numeric = (
        inputs.baseline_fare,
        inputs.baseline_passengers,
        inputs.baseline_seats,
        inputs.elasticity,
        inputs.elasticity_low,
        inputs.elasticity_high,
        inputs.fare_change,
        inputs.capacity_change,
        inputs.demand_factor,
    )
    if not all(isfinite(value) for value in numeric):
        raise ValueError("Scenario inputs must be finite")
    if inputs.baseline_fare <= 0:
        raise ValueError("Baseline fare must be positive")
    if inputs.baseline_passengers < 0 or inputs.baseline_seats <= 0:
        raise ValueError("Baseline passengers must be nonnegative and seats must be positive")
    if not -0.15 <= inputs.fare_change <= 0.15:
        raise ValueError("Fare change must be between -15% and 15%")
    if not -0.20 <= inputs.capacity_change <= 0.20:
        raise ValueError("Capacity change must be between -20% and 20%")
    if inputs.demand_factor <= 0:
        raise ValueError("Demand factor must be positive")
    if inputs.unit_cost is not None and inputs.unit_cost < 0:
        raise ValueError("Unit cost cannot be negative")


def simulate(inputs: ScenarioInput) -> ScenarioOutput:
    """Run one model-implied fare and capacity scenario.

    Revenue is a proxy. Optional contribution uses an analyst-provided unit cost.
    """

    _validate(inputs)
    proposed_fare = inputs.baseline_fare * (1 + inputs.fare_change)
    seats = inputs.baseline_seats * (1 + inputs.capacity_change)
    price_ratio = proposed_fare / inputs.baseline_fare

    center_unconstrained = _passenger_response(
        inputs.baseline_passengers, price_ratio, inputs.elasticity, inputs.demand_factor
    )
    interval_candidates = [
        _passenger_response(
            inputs.baseline_passengers, price_ratio, estimate, inputs.demand_factor
        )
        for estimate in (inputs.elasticity_low, inputs.elasticity_high)
    ]

    passengers = min(center_unconstrained, seats)
    passenger_low = min(min(interval_candidates), seats)
    passenger_high = min(max(interval_candidates), seats)
    baseline_revenue = inputs.baseline_fare * inputs.baseline_passengers
    revenue = proposed_fare * passengers
    revenue_low = proposed_fare * passenger_low
    revenue_high = proposed_fare * passenger_high
    contribution = None
    if inputs.unit_cost is not None:
        contribution = (proposed_fare - inputs.unit_cost) * passengers

    return ScenarioOutput(
        proposed_fare=proposed_fare,
        unconstrained_passengers=center_unconstrained,
        passengers=passengers,
        passenger_low=passenger_low,
        passenger_high=passenger_high,
        seats=seats,
        load_factor=passengers / seats,
        baseline_revenue_proxy=baseline_revenue,
        revenue_proxy=revenue,
        revenue_low=revenue_low,
        revenue_high=revenue_high,
        revenue_change_pct=(revenue / baseline_revenue - 1) if baseline_revenue else 0,
        spill_passengers=max(center_unconstrained - seats, 0),
        contribution_proxy=contribution,
    )
