import json
import tempfile
import unittest
from pathlib import Path

from pipeline.farelab.release import REQUIRED_ACTIONS, _verify_artifact, _verify_index, preflight_host


class ReleaseTests(unittest.TestCase):
    def artifact(self):
        routes = []
        for index, action in enumerate(sorted(REQUIRED_ACTIONS)):
            routes.append(
                {
                    "id": f"route-{index}",
                    "action": action,
                    "forecast": {"low": 90, "passengers": 100, "high": 110},
                    "scenarioPolicy": {"source": "Analyst assumption"},
                }
            )
        return {
            "schema_version": "2.0.0",
            "data_mode": "dot_observed",
            "source_vintage": "DOT test vintage",
            "built_at_utc": "2026-08-31T00:00:00Z",
            "identificationAudit": {
                "status": "No DOT-derived elasticity is approved for scenario use"
            },
            "routes": routes,
        }

    def test_index_references_must_resolve_inside_base_path(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / "assets").mkdir()
            (dist / "assets/app.js").write_text("export {};\n", encoding="utf-8")
            index = dist / "index.html"
            index.write_text(
                '<script type="module" src="/farelab/assets/app.js"></script>',
                encoding="utf-8",
            )
            references = _verify_index(index, dist, "/farelab/")
            self.assertEqual(references, ["/farelab/assets/app.js"])

    def test_release_artifact_accepts_governed_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "overview.json"
            artifact_path.write_text(json.dumps(self.artifact()), encoding="utf-8")
            result = _verify_artifact(artifact_path, artifact_path, "2.0.0", 500_000)
            self.assertEqual(len(result["routes"]), 5)

    def test_release_artifact_rejects_route_elasticity(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.artifact()
            artifact["routes"][0]["elasticity"] = -0.8
            artifact_path = Path(directory) / "overview.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rejected elasticity"):
                _verify_artifact(artifact_path, artifact_path, "2.0.0", 500_000)

    def test_host_preflight_is_read_only_and_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Path(directory)
            public = host / "client/public"
            public.mkdir(parents=True)
            (host / "package.json").write_text(
                json.dumps({"scripts": {"build:pages": "vite build"}}),
                encoding="utf-8",
            )
            (public / "_redirects").write_text("/* /index.html 200\n", encoding="utf-8")
            result = preflight_host(host)
            self.assertFalse(result["farelab_target_exists"])
            self.assertFalse(result["service_changes_required"])
            self.assertFalse(result["port_changes_required"])
            self.assertEqual(len(result["required_changes"]), 2)


if __name__ == "__main__":
    unittest.main()
