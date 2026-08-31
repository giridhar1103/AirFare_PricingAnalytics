import unittest

from pipeline.farelab.contracts import validate_artifact


class ContractTests(unittest.TestCase):
    def artifact(self, **overrides):
        values = {
            "schema_version": "2.0.0",
            "data_mode": "development_fixture",
            "source_vintage": "deterministic-ui-fixture-v1",
            "built_at_utc": "2026-08-30T00:00:00Z",
        }
        values.update(overrides)
        return values

    def test_development_artifact_is_valid_outside_production(self):
        validate_artifact(self.artifact())

    def test_development_artifact_cannot_be_promoted(self):
        with self.assertRaises(ValueError):
            validate_artifact(self.artifact(), production=True)

    def test_observed_artifact_can_be_promoted(self):
        validate_artifact(self.artifact(data_mode="dot_observed"), production=True)


if __name__ == "__main__":
    unittest.main()
