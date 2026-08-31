import unittest
from pathlib import Path

from pipeline.farelab.warehouse import _sql_path, source_periods


class WarehouseTests(unittest.TestCase):
    def test_source_periods_respect_db1b_end(self):
        periods = source_periods(2024, 2025)
        self.assertEqual(periods[0], (2024, 1))
        self.assertEqual(periods[-1], (2025, 2))
        self.assertEqual(len(periods), 6)

    def test_source_periods_reject_invalid_range(self):
        with self.assertRaises(ValueError):
            source_periods(2026, 2026)

    def test_sql_path_escapes_single_quote(self):
        escaped = _sql_path(Path("folder/airline's.csv"))
        self.assertIn("airline''s.csv", escaped)


if __name__ == "__main__":
    unittest.main()
