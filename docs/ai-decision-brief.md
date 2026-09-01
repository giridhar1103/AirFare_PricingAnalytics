# AI decision brief

## Purpose

The decision brief helps an analyst turn one completed FareLab scenario into a concise review handoff. It does not estimate elasticity, predict demand, calculate scenario outputs, choose an unconstrained action, file a fare, or change inventory.

## Grounding contract

The browser sends only a published route identifier and bounded scenario inputs. The API then:

1. Resolves the route from the governed public artifact.
2. Recomputes the scenario with `pipeline/farelab/scenario.py`.
3. Applies the deterministic recommendation policy.
4. Sends a compact context and approved key lists to Claude.
5. Forces a structured tool response.
6. Rejects any response that violates the policy or narrative rules.
7. Replaces selected keys with exact server-owned evidence and risk statements.

The model cannot introduce quantitative evidence because generated headline, summary, and next-step fields may not contain digits or quantitative terms. It cannot change the recommendation. The API key remains in the server environment and is never included in the static application.

## Decision policy

| Condition | Enforced result |
| --- | --- |
| Proposed fare is extrapolated | Do not proceed |
| Revenue proxy declines by at least 0.5% | Do not proceed |
| Capacity constraint binds | Hold for review |
| Absolute revenue proxy movement is below 0.5% | Hold for review |
| Supported scenario clears the prior controls | Run controlled test |

These labels mean review actions, not production fare instructions.

## Provider and model

The deployed provider is Anthropic and the default model is `claude-haiku-4-5-20251001`. The model is configurable through `FARELAB_AI_MODEL`. Claude is used because structured tool calls can be forced and validated against a strict JSON schema. The integration follows Anthropic's official [tool-use guidance](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools).

## Evaluation

The case set in `evals/ai_brief_cases.json` covers:

- A supported fare increase
- A neutral scenario
- A negative revenue-proxy result
- Fare extrapolation
- A binding seat constraint
- Competitor fare movement
- A soft demand regime
- Optional analyst cost

The runner checks deterministic recommendation and support classification before any provider call. In live mode it also checks recommendation agreement, prohibited narrative, grounded evidence, grounded risks, and latency. Aggregate results are stored under `evals/results/`; generated prose is not committed.

Release criteria:

- 100% policy agreement
- 100% schema-valid responses
- 100% grounded evidence and risk statements
- Zero prohibited numeric, profit, causal, certainty, or optimization claims in generated prose
- Live p95 response time below eight seconds for the release case set

The release evaluation completed on 2026-09-02 with all eight cases passing. Median response time was 2.77 seconds and p95 response time was 5.54 seconds. The committed result contains validation outcomes and latency only, not generated prose.

## Failure behavior

If the provider times out, rejects the request, or returns an invalid brief, the API returns a generic service-unavailable response. The UI keeps the deterministic scenario visible and states that the calculation is unaffected. It does not show invented fallback text as AI output.

## Known limitations

- Generated prose can still be awkward or omit useful nuance within the allowed schema.
- Evaluation cases are intentionally small and do not represent every airline pricing condition.
- Provider behavior can change across model versions.
- The brief is not trained or evaluated on internal airline decision records.
- Human review remains required.
