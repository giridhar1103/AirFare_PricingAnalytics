"""Run deterministic and optional live checks for the FareLab decision brief."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from api.brief import FORBIDDEN_PATTERN, DecisionBriefRequest, RouteStore, build_context


def _post(endpoint: str, payload: dict) -> tuple[dict, float]:
    request = Request(
        f"{endpoint.rstrip('/')}/brief",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body, time.perf_counter() - started


def evaluate(cases_path: Path, endpoint: str | None) -> dict:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    store = RouteStore()
    results = []
    latencies = []
    for case in cases:
        api_request = DecisionBriefRequest.model_validate(case["request"])
        context = build_context(store.get(api_request.route_id), api_request)
        checks = {
            "deterministicRecommendation": (
                context.expected_recommendation == case["expectedRecommendation"]
            ),
            "supportClassification": context.support == case["expectedSupport"],
        }
        if endpoint:
            try:
                response, latency = _post(endpoint, case["request"])
            except HTTPError as error:
                checks["liveResponse"] = False
                checks["httpStatus"] = error.code
            else:
                latencies.append(latency)
                narrative = " ".join(
                    (
                        response["brief"]["headline"],
                        response["brief"]["summary"],
                        response["brief"]["nextStep"],
                    )
                )
                checks.update(
                    {
                        "liveResponse": True,
                        "responseRecommendation": (
                            response["brief"]["recommendation"] == case["expectedRecommendation"]
                        ),
                        "prohibitedNarrative": FORBIDDEN_PATTERN.search(narrative) is None,
                        "groundedEvidence": all(
                            item in context.evidence.values()
                            for item in response["brief"]["evidence"]
                        ),
                        "groundedRisks": all(
                            item in context.risks.values() for item in response["brief"]["risks"]
                        ),
                    }
                )
        results.append({"id": case["id"], "passed": all(checks.values()), "checks": checks})

    passed = sum(result["passed"] for result in results)
    report = {
        "evaluatedAtUtc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "mode": "live" if endpoint else "deterministic",
        "cases": len(results),
        "passed": passed,
        "passRate": passed / len(results),
        "results": results,
    }
    if latencies:
        ordered = sorted(latencies)
        report["latencySeconds"] = {
            "median": statistics.median(ordered),
            "p95": ordered[min(round(0.95 * (len(ordered) - 1)), len(ordered) - 1)],
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("evals/ai_brief_cases.json"))
    parser.add_argument("--endpoint")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(args.cases, args.endpoint)
    except URLError as error:
        raise SystemExit(f"Live evaluation request failed: {error}") from error
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["passed"] != report["cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
