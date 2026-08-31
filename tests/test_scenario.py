import unittest

from pipeline.farelab.scenario import ScenarioInput, simulate


class ScenarioTests(unittest.TestCase):
    def base(self, **overrides):
        values = {
            "baseline_fare": 250,
            "baseline_passengers": 80_000,
            "baseline_seats": 100_000,
            "elasticity": -0.8,
            "elasticity_low": -1.0,
            "elasticity_high": -0.6,
        }
        values.update(overrides)
        return ScenarioInput(**values)

    def test_zero_change_reproduces_baseline(self):
        result = simulate(self.base())
        self.assertAlmostEqual(result.passengers, 80_000)
        self.assertAlmostEqual(result.revenue_proxy, 20_000_000)
        self.assertAlmostEqual(result.load_factor, 0.8)

    def test_inelastic_demand_increases_revenue_after_small_fare_increase(self):
        result = simulate(self.base(fare_change=0.05))
        self.assertGreater(result.revenue_change_pct, 0)
        self.assertLess(result.passengers, 80_000)

    def test_capacity_constraint_caps_load_factor(self):
        result = simulate(self.base(capacity_change=-0.20, demand_factor=1.2))
        self.assertLessEqual(result.load_factor, 1)
        self.assertGreater(result.spill_passengers, 0)

    def test_elasticity_interval_is_sorted_for_price_cut(self):
        result = simulate(self.base(fare_change=-0.10))
        self.assertLessEqual(result.passenger_low, result.passenger_high)
        self.assertLessEqual(result.revenue_low, result.revenue_high)

    def test_analyst_cost_is_optional(self):
        without_cost = simulate(self.base())
        with_cost = simulate(self.base(unit_cost=150))
        self.assertIsNone(without_cost.contribution_proxy)
        self.assertAlmostEqual(with_cost.contribution_proxy, 8_000_000)

    def test_out_of_bounds_change_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate(self.base(fare_change=0.16))


if __name__ == "__main__":
    unittest.main()
