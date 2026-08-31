import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryPolicyTests(unittest.TestCase):
    def test_site_copy_has_no_em_or_en_dash(self):
        checked_suffixes = {".ts", ".tsx", ".css", ".html", ".json"}
        violations = []
        for base in (ROOT / "web" / "src", ROOT / "web" / "public"):
            for path in base.rglob("*"):
                if path.is_file() and path.suffix in checked_suffixes:
                    text = path.read_text(encoding="utf-8")
                    if "\u2014" in text or "\u2013" in text:
                        violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations, [])

    def test_web_artifact_data_mode_is_governed(self):
        artifact_path = ROOT / "web" / "public" / "data" / "farelab-overview.json"
        if not artifact_path.exists():
            return

        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertIn(payload["data_mode"], {"development_fixture", "dot_observed"})
        if payload["data_mode"] == "development_fixture":
            self.assertIn("fixture", payload["source_vintage"].lower())
            return

        self.assertTrue(payload["routes"])
        self.assertIn("quality", payload)
        self.assertIn("forecastModel", payload)
        self.assertIn("identificationAudit", payload)
        self.assertIn("no dot-derived elasticity", payload["identificationAudit"]["status"].lower())
        for route in payload["routes"]:
            self.assertIn("forecast", route)
            self.assertIn("scenarioPolicy", route)
            self.assertIn("assumption", route["scenarioPolicy"]["source"].lower())
            self.assertNotIn("elasticity", route)
            self.assertNotIn("elasticityLow", route)
            self.assertNotIn("elasticityHigh", route)

        actions = {route["action"] for route in payload["routes"]}
        self.assertEqual(
            actions,
            {
                "Evaluate yield",
                "Protect share",
                "Review capacity",
                "Review fare position",
                "Hold and monitor",
            },
        )
        hold_scores = [route["score"] for route in payload["routes"] if route["action"] == "Hold and monitor"]
        review_scores = [route["score"] for route in payload["routes"] if route["action"] != "Hold and monitor"]
        self.assertLess(max(hold_scores), min(review_scores))

    def test_overview_artifact_respects_size_budget(self):
        artifact_path = ROOT / "web" / "public" / "data" / "farelab-overview.json"
        if artifact_path.exists():
            self.assertLessEqual(artifact_path.stat().st_size, 500_000)

    def test_public_artifact_matches_warehouse_manifest_summary(self):
        artifact_path = ROOT / "web" / "public" / "data" / "farelab-overview.json"
        manifest_path = ROOT / "data" / "manifests" / "warehouse_build.json"
        if not artifact_path.exists() or not manifest_path.exists():
            return
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_file_count = sum(source["file_count"] for source in manifest["sources"])
        self.assertEqual(source_file_count, manifest["source_manifest_rows"])
        self.assertEqual(source_file_count, artifact["quality"]["sourceFiles"])


if __name__ == "__main__":
    unittest.main()
