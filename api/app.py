"""FastAPI entry point for FareLab's grounded AI decision brief."""

import logging
import os
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .brief import (
    ClaudeBriefProvider,
    DecisionBriefRequest,
    DecisionBriefResponse,
    RouteStore,
    build_context,
    generate_validated_brief,
)

app = FastAPI(
    title="FareLab Decision Brief API",
    description="Grounded narrative support for FareLab pricing scenarios.",
    version="1.0.0",
)

origins = os.environ.get(
    "FARELAB_FRONTEND_ORIGINS",
    "https://giriworks.com,http://127.0.0.1:44179,http://localhost:44179",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

store = RouteStore()
logger = logging.getLogger("farelab.ai")


@app.get("/health")
def health() -> dict[str, str | bool | int]:
    return {
        "status": "ok",
        "providerConfigured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "routes": len(store.routes),
        "artifactSchema": store.schema_version,
    }


@app.post("/brief", response_model=DecisionBriefResponse)
def decision_brief(request: DecisionBriefRequest) -> DecisionBriefResponse:
    try:
        route = store.get(request.route_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    context = build_context(route, request)
    provider = ClaudeBriefProvider()
    try:
        brief = generate_validated_brief(provider, context)
    except Exception as error:
        logger.warning(
            "Decision brief failed for route %s with %s: %s",
            request.route_id,
            type(error).__name__,
            error,
        )
        raise HTTPException(
            status_code=503,
            detail="Decision brief generation is temporarily unavailable",
        ) from error

    output = context.output
    return DecisionBriefResponse(
        route_id=request.route_id,
        provider="Anthropic",
        model=provider.model,
        generated_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        calculation_source="FareLab server calculation using governed scenario equations",
        support=context.support,
        scenario={
            "proposedFare": output.proposed_fare,
            "passengers": output.passengers,
            "passengerLow": output.passenger_low,
            "passengerHigh": output.passenger_high,
            "seats": output.seats,
            "loadFactor": output.load_factor,
            "revenueProxy": output.revenue_proxy,
            "revenueLow": output.revenue_low,
            "revenueHigh": output.revenue_high,
            "revenueChange": output.revenue_change_pct,
            "spillPassengers": output.spill_passengers,
            "contributionProxy": output.contribution_proxy,
        },
        brief=brief,
    )
