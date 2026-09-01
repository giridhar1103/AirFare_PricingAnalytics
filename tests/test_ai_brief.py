import unittest

from api.brief import (
    DecisionBriefRequest,
    DraftBrief,
    RouteStore,
    assemble_brief,
    build_context,
    generate_validated_brief,
)


class DecisionBriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = RouteStore()
        cls.route = next(iter(cls.store.routes.values()))

    def request(self, **overrides):
        values = {
            "route_id": self.route["id"],
            "fare_change": 0.03,
            "capacity_change": 0.0,
            "competitor_fare_change": 0.0,
            "elasticity": -0.8,
            "demand_factor": 1.0,
        }
        values.update(overrides)
        return DecisionBriefRequest(**values)

    def draft(self, recommendation="Run controlled test", **overrides):
        values = {
            "recommendation": recommendation,
            "headline": "Test the supported fare change with clear guardrails",
            "summary": (
                "The scenario supports a controlled market test while the analyst monitors "
                "demand and the competitive response."
            ),
            "evidence_keys": ["fare_support", "revenue_proxy"],
            "risk_keys": ["noncausal", "elasticity_assumed"],
            "next_step": "Review the test cell and define rollback criteria before filing.",
        }
        values.update(overrides)
        return DraftBrief(**values)

    def test_route_store_loads_governed_public_sample(self):
        self.assertEqual(len(self.store.routes), 60)
        self.assertIn(self.store.schema_version, {"2.0.0", "2.1.0"})

    def test_supported_positive_scenario_can_run_controlled_test(self):
        context = build_context(self.route, self.request())
        self.assertEqual(context.support, "Within observed range")
        self.assertEqual(context.expected_recommendation, "Run controlled test")
        brief = assemble_brief(self.draft(), context)
        self.assertEqual(brief.recommendation, "Run controlled test")
        self.assertEqual(len(brief.evidence), 2)

    def test_extrapolated_scenario_cannot_proceed(self):
        route = self.store.get("10397:12478:DL")
        context = build_context(route, self.request(route_id=route["id"], fare_change=0.15))
        self.assertEqual(context.support, "Extrapolation")
        self.assertEqual(context.expected_recommendation, "Do not proceed")

    def test_capacity_constraint_requires_review(self):
        route = self.store.get("14635:13487:SY")
        context = build_context(
            route,
            self.request(
                route_id=route["id"],
                fare_change=0.03,
                capacity_change=-0.02,
                demand_factor=1.05,
            ),
        )
        self.assertGreater(context.output.spill_passengers, 0)
        self.assertEqual(context.expected_recommendation, "Hold for review")

    def test_changed_recommendation_is_rejected(self):
        context = build_context(self.route, self.request())
        with self.assertRaisesRegex(ValueError, "governed policy"):
            assemble_brief(self.draft(recommendation="Do not proceed"), context)

    def test_generated_numbers_and_profit_claims_are_rejected(self):
        context = build_context(self.route, self.request())
        for summary in (
            "The projected result improves revenue by three percent and supports a test.",
            "This fare is profitable and should move into a controlled market test.",
        ):
            with self.subTest(summary=summary), self.assertRaisesRegex(ValueError, "prohibited"):
                assemble_brief(self.draft(summary=summary), context)

    def test_cost_evidence_only_exists_when_supplied(self):
        without_cost = build_context(self.route, self.request())
        with_cost = build_context(self.route, self.request(unit_cost=180))
        self.assertNotIn("unit_cost", without_cost.evidence)
        self.assertIn("unit_cost", with_cost.evidence)

    def test_one_invalid_provider_draft_is_retried(self):
        context = build_context(self.route, self.request())
        invalid = self.draft(summary="The result supports a guaranteed return from the test.")
        valid = self.draft()

        class SequencedProvider:
            model = "test-provider"

            def __init__(self):
                self.drafts = iter((invalid, valid))

            def generate(self, _context):
                return next(self.drafts)

        brief = generate_validated_brief(SequencedProvider(), context)
        self.assertEqual(brief.summary, valid.summary)


if __name__ == "__main__":
    unittest.main()
