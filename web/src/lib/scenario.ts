export interface ScenarioInput {
  baselineFare: number;
  baselinePassengers: number;
  baselineSeats: number;
  elasticity: number;
  elasticityLow: number;
  elasticityHigh: number;
  fareChange: number;
  capacityChange: number;
  demandFactor: number;
  competitorFareChange: number;
  crossPriceElasticity?: number;
  unitCost?: number;
}

export interface ScenarioResult {
  proposedFare: number;
  passengers: number;
  passengerLow: number;
  passengerHigh: number;
  seats: number;
  loadFactor: number;
  baselineRevenue: number;
  revenue: number;
  revenueLow: number;
  revenueHigh: number;
  passengerChange: number;
  revenueChange: number;
  spillPassengers: number;
  contribution?: number;
}

const demand = (
  baseline: number,
  priceRatio: number,
  elasticity: number,
  demandFactor: number,
  competitorRatio: number,
  crossPriceElasticity: number
) => baseline * Math.pow(priceRatio, elasticity) * demandFactor * Math.pow(competitorRatio, crossPriceElasticity);

export function simulateScenario(input: ScenarioInput): ScenarioResult {
  if (input.fareChange < -0.15 || input.fareChange > 0.15) {
    throw new Error("Fare change is outside the supported range");
  }
  if (input.capacityChange < -0.2 || input.capacityChange > 0.2) {
    throw new Error("Capacity change is outside the supported range");
  }
  const proposedFare = input.baselineFare * (1 + input.fareChange);
  const priceRatio = proposedFare / input.baselineFare;
  const seats = input.baselineSeats * (1 + input.capacityChange);
  const competitorRatio = 1 + input.competitorFareChange;
  const cross = input.crossPriceElasticity ?? 0.15;
  const centerUnconstrained = demand(
    input.baselinePassengers,
    priceRatio,
    input.elasticity,
    input.demandFactor,
    competitorRatio,
    cross
  );
  const interval = [input.elasticityLow, input.elasticityHigh].map((elasticity) =>
    demand(input.baselinePassengers, priceRatio, elasticity, input.demandFactor, competitorRatio, cross)
  );
  const passengers = Math.min(centerUnconstrained, seats);
  const passengerLow = Math.min(Math.min(...interval), seats);
  const passengerHigh = Math.min(Math.max(...interval), seats);
  const baselineRevenue = input.baselineFare * input.baselinePassengers;
  const revenue = proposedFare * passengers;
  return {
    proposedFare,
    passengers,
    passengerLow,
    passengerHigh,
    seats,
    loadFactor: passengers / seats,
    baselineRevenue,
    revenue,
    revenueLow: proposedFare * passengerLow,
    revenueHigh: proposedFare * passengerHigh,
    passengerChange: passengers / input.baselinePassengers - 1,
    revenueChange: revenue / baselineRevenue - 1,
    spillPassengers: Math.max(centerUnconstrained - seats, 0),
    contribution:
      input.unitCost === undefined ? undefined : (proposedFare - input.unitCost) * passengers
  };
}

export function supportLabel(proposedFare: number, observedMin: number, observedMax: number) {
  if (proposedFare >= observedMin && proposedFare <= observedMax) return "Within observed range";
  const buffer = Math.max(observedMax - observedMin, 1) * 0.1;
  if (proposedFare >= observedMin - buffer && proposedFare <= observedMax + buffer) return "Near observed range";
  return "Extrapolation";
}
