"""Grounded decision-brief generation for FareLab scenarios."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import anthropic
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pipeline.farelab.scenario import ScenarioInput, ScenarioOutput, simulate

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = PROJECT_ROOT / "web" / "public" / "data" / "farelab-overview.json"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
CROSS_PRICE_ELASTICITY = 0.15

Recommendation = Literal["Run controlled test", "Hold for review", "Do not proceed"]
EvidenceKey = Literal[
    "baseline",
    "fare_support",
    "passenger_outlook",
    "revenue_proxy",
    "capacity",
    "competitive_context",
    "forecast_context",
    "unit_cost",
    "route_signal",
]
RiskKey = Literal[
    "noncausal",
    "elasticity_assumed",
    "revenue_not_profit",
    "public_data_lag",
    "fare_support",
    "capacity",
    "forecast_conditional",
    "unit_cost_assumed",
]


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, extra="forbid")


class DecisionBriefRequest(ApiModel):
    route_id: str = Field(min_length=3, max_length=100)
    fare_change: float = Field(ge=-0.15, le=0.15)
    capacity_change: float = Field(ge=-0.20, le=0.20)
    competitor_fare_change: float = Field(ge=-0.10, le=0.10)
    elasticity: float = Field(ge=-2.0, le=-0.2)
    demand_factor: Literal[0.95, 1.0, 1.05]
    unit_cost: float | None = Field(default=None, ge=0, le=10_000)


class DraftBrief(ApiModel):
    recommendation: Recommendation
    headline: str = Field(min_length=8, max_length=90)
    summary: str = Field(min_length=30, max_length=700)
    evidence_keys: list[EvidenceKey] = Field(min_length=2, max_length=4)
    risk_keys: list[RiskKey] = Field(min_length=2, max_length=4)
    next_step: str = Field(min_length=15, max_length=320)

    @field_validator("evidence_keys", "risk_keys")
    @classmethod
    def unique_keys(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Brief keys must be unique")
        return value


class DecisionBrief(ApiModel):
    recommendation: Recommendation
    headline: str
    summary: str
    evidence: list[str]
    risks: list[str]
    next_step: str


class DecisionBriefResponse(ApiModel):
    route_id: str
    provider: str
    model: str
    generated_at_utc: str
    generation_mode: Literal["ai"] = "ai"
    calculation_source: str
    support: str
    scenario: dict[str, float | None]
    brief: DecisionBrief


@dataclass(frozen=True)
class BriefContext:
    route: dict[str, Any]
    inputs: DecisionBriefRequest
    output: ScenarioOutput
    support: str
    expected_recommendation: Recommendation
    evidence: dict[str, str]
    risks: dict[str, str]


class BriefProvider(Protocol):
    model: str

    def generate(self, context: BriefContext) -> DraftBrief: ...


class RouteStore:
    def __init__(self, artifact_path: Path = DEFAULT_ARTIFACT) -> None:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        if payload.get("data_mode") != "dot_observed":
            raise ValueError("Decision briefs require the governed DOT artifact")
        self.schema_version = str(payload["schema_version"])
        self.routes = {route["id"]: route for route in payload["routes"]}

    def get(self, route_id: str) -> dict[str, Any]:
        try:
            return self.routes[route_id]
        except KeyError as error:
            raise KeyError("Route is not in the published workflow sample") from error


def support_label(proposed_fare: float, observed_min: float, observed_max: float) -> str:
    if observed_min <= proposed_fare <= observed_max:
        return "Within observed range"
    buffer = max(observed_max - observed_min, 1.0) * 0.10
    if observed_min - buffer <= proposed_fare <= observed_max + buffer:
        return "Near observed range"
    return "Extrapolation"


def policy_recommendation(output: ScenarioOutput, support: str) -> Recommendation:
    if support == "Extrapolation" or output.revenue_change_pct <= -0.005:
        return "Do not proceed"
    if output.spill_passengers > 0 or abs(output.revenue_change_pct) < 0.005:
        return "Hold for review"
    return "Run controlled test"


def build_context(route: dict[str, Any], request: DecisionBriefRequest) -> BriefContext:
    policy = route["scenarioPolicy"]
    output = simulate(
        ScenarioInput(
            baseline_fare=float(route["baselineFare"]),
            baseline_passengers=float(route["passengers"]),
            baseline_seats=float(route["seats"]),
            elasticity=request.elasticity,
            elasticity_low=float(policy["sensitivityLow"]),
            elasticity_high=float(policy["sensitivityHigh"]),
            fare_change=request.fare_change,
            capacity_change=request.capacity_change,
            demand_factor=request.demand_factor,
            competitor_fare_change=request.competitor_fare_change,
            cross_price_elasticity=CROSS_PRICE_ELASTICITY,
            unit_cost=request.unit_cost,
        )
    )
    support = support_label(
        output.proposed_fare,
        float(route["observedFareMin"]),
        float(route["observedFareMax"]),
    )
    recommendation = policy_recommendation(output, support)
    passenger_change = output.passengers / float(route["passengers"]) - 1
    evidence = {
        "baseline": (
            f"Baseline: ${float(route['baselineFare']):,.2f} average fare, "
            f"{int(route['passengers']):,} passengers, and "
            f"{float(route['loadFactor']):.1%} load factor."
        ),
        "fare_support": (
            f"Proposed fare: ${output.proposed_fare:,.2f}. Historical support: {support.lower()} "
            f"against an observed ${float(route['observedFareMin']):,.2f} to "
            f"${float(route['observedFareMax']):,.2f} range."
        ),
        "passenger_outlook": (
            f"Scenario passenger change: {passenger_change:+.1%}, with a sensitivity range of "
            f"{output.passenger_low:,.0f} to {output.passenger_high:,.0f} passengers."
        ),
        "revenue_proxy": (
            f"Scenario revenue proxy change: {output.revenue_change_pct:+.1%}, with a range of "
            f"${output.revenue_low / 1_000_000:,.2f}M to ${output.revenue_high / 1_000_000:,.2f}M."
        ),
        "capacity": (
            f"Scenario load factor: {output.load_factor:.1%}. Potential passenger spill: "
            f"{output.spill_passengers:,.0f}."
        ),
        "competitive_context": (
            f"Competitor fare assumption: {request.competitor_fare_change:+.1%}, using a governed "
            f"cross-price elasticity of {CROSS_PRICE_ELASTICITY:.2f}."
        ),
        "forecast_context": (
            f"Conditional {route['forecast']['period']} forecast: "
            f"{int(route['forecast']['passengers']):,} passengers, with an interval of "
            f"{int(route['forecast']['low']):,} to {int(route['forecast']['high']):,}."
        ),
        "route_signal": (
            f"Current queue signal: {route['action']}. "
            f"Priority score: {int(route['score'])} of 100. "
            f"Confidence label: {route['confidence'].lower()}."
        ),
    }
    if request.unit_cost is not None:
        evidence["unit_cost"] = (
            f"Analyst unit-cost assumption: ${request.unit_cost:,.2f}. "
            "Scenario contribution proxy: "
            f"${(output.contribution_proxy or 0) / 1_000_000:,.2f}M."
        )

    risks = {
        "noncausal": (
            "The scenario is decision-support arithmetic, not a causal estimate or "
            "automated fare filing."
        ),
        "elasticity_assumed": (
            f"Own-price elasticity of {request.elasticity:.2f} is analyst supplied because the DOT "
            "identification tests did not pass the economic sign check."
        ),
        "revenue_not_profit": "Revenue proxy excludes ancillary revenue and route accounting cost.",
        "public_data_lag": (
            "Public DOT data is quarterly and does not represent current booking activity."
        ),
        "fare_support": f"The proposed fare is classified as {support.lower()}.",
        "capacity": "The seat constraint binds, so schedule feasibility needs review.",
        "forecast_conditional": "The demand forecast is conditional on supplied commercial inputs.",
        "unit_cost_assumed": (
            "Contribution uses a user-provided unit cost, not observed accounting cost."
        ),
    }
    return BriefContext(
        route=route,
        inputs=request,
        output=output,
        support=support,
        expected_recommendation=recommendation,
        evidence=evidence,
        risks=risks,
    )


TOOL_SCHEMA = {
    "name": "emit_decision_brief",
    "description": "Return the review-ready FareLab decision brief using only approved keys.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recommendation": {
                "type": "string",
                "enum": ["Run controlled test", "Hold for review", "Do not proceed"],
            },
            "headline": {"type": "string", "minLength": 8, "maxLength": 90},
            "summary": {"type": "string", "minLength": 30, "maxLength": 700},
            "evidenceKeys": {
                "type": "array",
                "description": "Select two to four approved evidence keys.",
                "minItems": 1,
                "items": {
                    "type": "string",
                    "enum": [
                        "baseline",
                        "fare_support",
                        "passenger_outlook",
                        "revenue_proxy",
                        "capacity",
                        "competitive_context",
                        "forecast_context",
                        "unit_cost",
                        "route_signal",
                    ],
                },
            },
            "riskKeys": {
                "type": "array",
                "description": "Select two to four approved risk keys.",
                "minItems": 1,
                "items": {
                    "type": "string",
                    "enum": [
                        "noncausal",
                        "elasticity_assumed",
                        "revenue_not_profit",
                        "public_data_lag",
                        "fare_support",
                        "capacity",
                        "forecast_conditional",
                        "unit_cost_assumed",
                    ],
                },
            },
            "nextStep": {"type": "string", "minLength": 15, "maxLength": 320},
        },
        "required": [
            "recommendation",
            "headline",
            "summary",
            "evidenceKeys",
            "riskKeys",
            "nextStep",
        ],
    },
}


class ClaudeBriefProvider:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("FARELAB_AI_MODEL", DEFAULT_MODEL)

    def generate(self, context: BriefContext) -> DraftBrief:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=15.0)
        allowed_evidence = list(context.evidence)
        allowed_risks = [
            "noncausal",
            "elasticity_assumed",
            "revenue_not_profit",
            "public_data_lag",
            "fare_support",
            "forecast_conditional",
        ]
        if context.output.spill_passengers > 0:
            allowed_risks.append("capacity")
        if context.inputs.unit_cost is not None:
            allowed_risks.append("unit_cost_assumed")
        passenger_change = context.output.passengers / float(context.route["passengers"]) - 1

        def direction(value: float, threshold: float = 0.0005) -> str:
            if value > threshold:
                return "higher"
            if value < -threshold:
                return "lower"
            return "unchanged"

        prompt_context = {
            "route": (
                f"{context.route['origin']} to {context.route['destination']} on "
                f"{context.route['carrierName']}"
            ),
            "expectedRecommendation": context.expected_recommendation,
            "support": context.support,
            "currentQueueAction": context.route["action"],
            "scenarioSignals": {
                "fare": direction(context.inputs.fare_change),
                "capacity": direction(context.inputs.capacity_change),
                "competitorFare": direction(context.inputs.competitor_fare_change),
                "passengers": direction(passenger_change),
                "revenueProxy": direction(context.output.revenue_change_pct),
                "capacityBinds": context.output.spill_passengers > 0,
                "demandRegime": {
                    0.95: "soft",
                    1.0: "base",
                    1.05: "strong",
                }[context.inputs.demand_factor],
                "unitCostProvided": context.inputs.unit_cost is not None,
            },
            "allowedEvidenceKeys": allowed_evidence,
            "allowedRiskKeys": allowed_risks,
        }
        response = client.messages.create(
            model=self.model,
            max_tokens=450,
            temperature=0,
            system=(
                "You write concise airline pricing review briefs for an analyst. FareLab owns all "
                "calculations and the recommendation policy. You may not change the expected "
                "recommendation. Select only keys listed as allowed. Do not put digits, currency, "
                "percentages, profit claims, causal claims, certainty claims, or markdown in the "
                "headline, summary, or next step. Select between two and four evidence keys and "
                "between two and four risk keys. Keep the summary to at most three short sentences "
                "and the next step to one short sentence. Use plain professional language. The "
                "context intentionally contains no quantitative values. Do not invent any. The "
                "brief must sound like a careful analyst handoff, not marketing copy."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "<task>Prepare a decision brief from the governed scenario context.</task>"
                        f"<context>{json.dumps(prompt_context, separators=(',', ':'))}</context>"
                    ),
                }
            ],
            tools=[TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "emit_decision_brief"},
        )
        tool_blocks = [block for block in response.content if block.type == "tool_use"]
        if len(tool_blocks) != 1:
            raise ValueError("Provider did not return one structured decision brief")
        return DraftBrief.model_validate(tool_blocks[0].input)


FORBIDDEN_PATTERN = re.compile(
    r"\d|\bprofit(?:able|ability)?\b|\bcaus(?:al|e|es|ed|ation)\b|"
    r"\bguarantee(?:d|s)?\b|\boptimal(?:ly)?\b|\boptimi[sz](?:e|ed|es|ing|ation)\b|"
    r"\bpercent(?:age)?\b|\bdollars?\b|\bpoints?\b",
    re.IGNORECASE,
)


def validate_draft(draft: DraftBrief, context: BriefContext) -> None:
    if draft.recommendation != context.expected_recommendation:
        raise ValueError("Provider recommendation does not match the governed policy")
    narrative = " ".join((draft.headline, draft.summary, draft.next_step))
    if FORBIDDEN_PATTERN.search(narrative):
        raise ValueError("Provider narrative contains a prohibited claim or number")
    if any(key not in context.evidence for key in draft.evidence_keys):
        raise ValueError("Provider selected unavailable evidence")
    if context.output.spill_passengers <= 0 and "capacity" in draft.risk_keys:
        raise ValueError("Provider selected an inapplicable capacity risk")
    if context.inputs.unit_cost is None and "unit_cost_assumed" in draft.risk_keys:
        raise ValueError("Provider selected an inapplicable cost risk")


def assemble_brief(draft: DraftBrief, context: BriefContext) -> DecisionBrief:
    validate_draft(draft, context)
    return DecisionBrief(
        recommendation=draft.recommendation,
        headline=draft.headline,
        summary=draft.summary,
        evidence=[context.evidence[key] for key in draft.evidence_keys],
        risks=[context.risks[key] for key in draft.risk_keys],
        next_step=draft.next_step,
    )


def generate_validated_brief(
    provider: BriefProvider,
    context: BriefContext,
    attempts: int = 2,
) -> DecisionBrief:
    """Retry one schema or policy failure, then fail closed."""
    if attempts < 1:
        raise ValueError("At least one generation attempt is required")
    last_error: ValueError | None = None
    for _ in range(attempts):
        try:
            return assemble_brief(provider.generate(context), context)
        except ValueError as error:
            last_error = error
    if last_error is None:
        raise RuntimeError("Decision brief generation did not run")
    raise last_error
