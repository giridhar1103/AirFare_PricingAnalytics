export interface DecisionBriefRequest {
  routeId: string;
  fareChange: number;
  capacityChange: number;
  competitorFareChange: number;
  elasticity: number;
  demandFactor: 0.95 | 1 | 1.05;
  unitCost?: number;
}

export interface DecisionBriefResponse {
  routeId: string;
  provider: string;
  model: string;
  generatedAtUtc: string;
  generationMode: "ai";
  calculationSource: string;
  support: string;
  scenario: Record<string, number | null>;
  brief: {
    recommendation: "Run controlled test" | "Hold for review" | "Do not proceed";
    headline: string;
    summary: string;
    evidence: string[];
    risks: string[];
    nextStep: string;
  };
}

const endpoint = import.meta.env.VITE_FARELAB_AI_URL ?? "https://api.giriworks.com/farelab-ai";

export async function generateDecisionBrief(
  request: DecisionBriefRequest,
  signal?: AbortSignal
): Promise<DecisionBriefResponse> {
  const response = await fetch(`${endpoint}/brief`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal
  });
  if (!response.ok) throw new Error("The decision brief service is unavailable");
  return response.json() as Promise<DecisionBriefResponse>;
}
