export type ActionKind = "Evaluate yield" | "Protect share" | "Review capacity" | "Review fare position" | "Hold and monitor";
export type Confidence = "High" | "Medium" | "Low";

export interface HistoryPoint {
  period: string;
  fare: number;
  passengers: number;
  seats: number;
  loadFactor: number;
  competitorFare: number | null;
  marketShare: number;
  hhi: number;
  revenueProxy: number;
}

export interface RouteChanges {
  fareYoY: number;
  passengersYoY: number;
  seatsYoY: number;
  shareYoYPoints: number;
}

export interface RouteForecast {
  period: string;
  passengers: number;
  low: number;
  high: number;
  yearOverYearChange: number;
  assumption: string;
}

export interface ScenarioPolicy {
  defaultElasticity: number;
  sensitivityLow: number;
  sensitivityHigh: number;
  source: string;
}

export interface RouteMarket {
  id: string;
  origin: string;
  destination: string;
  carrier: string;
  carrierName: string;
  distanceMiles: number;
  baselineFare: number;
  passengers: number;
  seats: number;
  loadFactor: number;
  marketShare: number;
  hhi: number;
  fareIndex: number;
  observedFareMin: number;
  observedFareMax: number;
  observations: number;
  action: ActionKind;
  confidence: Confidence;
  score: number;
  rationale: string;
  evidence: string[];
  changes: RouteChanges;
  forecast: RouteForecast;
  scenarioPolicy: ScenarioPolicy;
  history: HistoryPoint[];
}

export interface QualitySummary {
  martRows: number;
  directionalRoutes: number;
  carriers: number;
  firstPeriod: string;
  lastPeriod: string;
  acceptedRows: number;
  reviewRows: number;
  sourceFiles: number;
  minimumPassengerWeightedJoinRate: number;
}

export interface ForecastModelSummary {
  version: string;
  champion: string;
  wape: number;
  bias: number;
  seasonalNaiveWape: number;
  intervalLevel: number;
  intervalCoverage: number;
  intervalEvaluationPeriods: string[];
  intervalEvaluationObservations: number;
  intervalCalibrationObservations: number;
  validationObservations: number;
}

export interface IdentificationAudit {
  status: string;
  passengerFixedEffectsCoefficient: number;
  marketShareFixedEffectsCoefficient: number;
  ivSensitivityCoefficient: number;
  reason: string;
}

export interface OverviewArtifact {
  schema_version: string;
  data_mode: "development_fixture" | "dot_observed";
  source_vintage: string;
  built_at_utc: string;
  title: string;
  notice: string;
  quality: QualitySummary;
  forecastModel: ForecastModelSummary;
  identificationAudit: IdentificationAudit;
  routes: RouteMarket[];
}
