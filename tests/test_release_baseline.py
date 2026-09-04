import importlib.util
from pathlib import Path
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "live" / "tools" / "release_baseline.py"
SPEC = importlib.util.spec_from_file_location("release_baseline", MODULE_PATH)
baseline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(baseline)


class ReleaseBaselineTests(unittest.TestCase):
    def test_git_blob_matches_known_empty_blob(self):
        self.assertEqual(
            baseline._git_blob(b""),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
        )

    def test_latest_deployment_uses_created_at(self):
        rows = [
            {"id": "old", "createdAt": "2026-01-01T00:00:00Z"},
            {"id": "new", "createdAt": "2026-02-01T00:00:00Z"},
        ]
        self.assertEqual(baseline._latest_deployment(rows)["id"], "new")

    def test_latest_deployment_can_select_success(self):
        rows = [
            {"id": "running", "status": "SUCCESS", "createdAt": "2026-01-01T00:00:00Z"},
            {"id": "event", "status": "SKIPPED", "createdAt": "2026-02-01T00:00:00Z"},
        ]
        self.assertEqual(baseline._latest_deployment(rows, "SUCCESS")["id"], "running")

    def test_safe_roles_never_includes_keys(self):
        vault = {
            "MODEL_A_MODEL": "example-model",
            "MODEL_A_API_KEY": "secret",
            "DIAG_KEY": "secret",
            "GITHUB_TOKEN": "secret",
        }
        result = baseline._safe_roles(vault)
        self.assertEqual(result["MODEL_A_MODEL"], "example-model")
        self.assertNotIn("MODEL_A_API_KEY", result)
        self.assertNotIn("DIAG_KEY", result)
        self.assertNotIn("GITHUB_TOKEN", result)

    def test_commit_from_meta_accepts_known_railway_shapes(self):
        self.assertEqual(baseline._commit_from_meta({"commitHash": "abc"}), "abc")
        self.assertEqual(baseline._commit_from_meta({"commitSha": "def"}), "def")
        self.assertIsNone(baseline._commit_from_meta({}))

    def test_diag_key_uses_header_not_url(self):
        with mock.patch.object(baseline, "_request_json", return_value=(200, {})) as request:
            baseline._engine_get("https://engine.example", "/diag/engine", "master-secret")
        args, kwargs = request.call_args
        self.assertNotIn("master-secret", args[0])
        self.assertEqual(kwargs["headers"], {"X-Diag-Key": "master-secret"})


if __name__ == "__main__":
    unittest.main()
