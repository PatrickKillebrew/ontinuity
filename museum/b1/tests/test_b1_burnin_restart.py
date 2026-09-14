import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FILE_SERVER = ROOT / "live" / "box" / "file_server.py"


class BurninRestartOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.previous_db = os.environ.get("ONTINUITY_DB_PATH")
        os.environ["ONTINUITY_DB_PATH"] = str(Path(cls.temp.name) / "ops.db")
        cls.previous_workspace_module = sys.modules.get("workspace_db_endpoint")
        sys.modules["workspace_db_endpoint"] = None
        spec = importlib.util.spec_from_file_location(
            "b1_burnin_restart_file_server", FILE_SERVER)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        if cls.previous_workspace_module is None:
            sys.modules.pop("workspace_db_endpoint", None)
        else:
            sys.modules["workspace_db_endpoint"] = cls.previous_workspace_module
        cls.module.app.config["TESTING"] = True
        cls.client = cls.module.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if cls.previous_db is None:
            os.environ.pop("ONTINUITY_DB_PATH", None)
        else:
            os.environ["ONTINUITY_DB_PATH"] = cls.previous_db
        cls.temp.cleanup()

    def setUp(self):
        self.events = []
        self.load_config = mock.patch.object(
            self.module, "load_config", return_value={"diag_key": "box-root"})
        self.begin = mock.patch.object(
            self.module, "_ops_begin", side_effect=self._begin)
        self.finish = mock.patch.object(
            self.module, "_ops_finish", side_effect=self._finish)
        self.load_config.start()
        self.begin.start()
        self.finish.start()

    def tearDown(self):
        self.finish.stop()
        self.begin.stop()
        self.load_config.stop()

    def _begin(self, *args):
        self.events.append(("begin", args))
        return 41

    def _finish(self, *args):
        self.events.append(("finish", args))

    @property
    def headers(self):
        return {"X-Diag-Key": "box-root"}

    def test_requires_header_auth_before_any_process(self):
        with mock.patch.object(self.module.subprocess, "run") as run:
            response = self.client.post("/op/restart_burnin", json={})
        self.assertEqual(response.status_code, 401)
        run.assert_not_called()
        self.assertEqual(self.events, [])

    def test_rejects_every_noncanonical_input_form(self):
        cases = (
            ("query", "/op/restart_burnin?unit=other", b"{}",
             "application/json"),
            ("form", "/op/restart_burnin", b"unit=other",
             "application/x-www-form-urlencoded"),
            ("empty-text", "/op/restart_burnin", b"", "text/plain"),
            ("text", "/op/restart_burnin", b"{}", "text/plain"),
            ("json-null", "/op/restart_burnin", b"null", "application/json"),
            ("json-list", "/op/restart_burnin", b"[]", "application/json"),
            ("json-scalar", "/op/restart_burnin", b"1", "application/json"),
            ("json-object", "/op/restart_burnin", b'{"unit":"other"}',
             "application/json"),
        )
        for label, path, body, content_type in cases:
            with self.subTest(case=label), mock.patch.object(
                    self.module.subprocess, "run") as run:
                response = self.client.post(
                    path, headers=self.headers, data=body,
                    content_type=content_type)
            self.assertEqual(response.status_code, 400)
            run.assert_not_called()
        self.assertEqual(self.events, [])

    def test_uses_fixed_argv_and_dual_end_ledger_then_proves_active(self):
        completed = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "active\n", ""),
        ]
        with mock.patch.object(
                self.module.subprocess, "run", side_effect=completed) as run:
            response = self.client.post(
                "/op/restart_burnin", headers=self.headers, json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            "ok": True, "state": "active", "unit": "ontinuity-burnin",
        })
        self.assertEqual(run.call_args_list, [
            mock.call(
                ["systemctl", "restart", "ontinuity-burnin"],
                capture_output=True, text=True, timeout=30,
            ),
            mock.call(
                ["systemctl", "is-active", "ontinuity-burnin"],
                capture_output=True, text=True, timeout=10,
            ),
        ])
        self.assertEqual(self.events[0], (
            "begin",
            ("restart_burnin", "REVIEW", "diag-key", "127.0.0.1",
             {"unit": "ontinuity-burnin"}),
        ))
        self.assertEqual(self.events[-1], (
            "finish", (41, "ok", "restart rc=0, is-active=active"),
        ))

    def test_restart_failure_is_logged_and_skips_status_check(self):
        with mock.patch.object(
                self.module.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 1, "", "failed")) as run:
            response = self.client.post(
                "/op/restart_burnin", headers=self.headers, json={})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(self.events[-1], (
            "finish", (41, "fail", "restart rc=1"),
        ))

    def test_ledger_unavailable_refuses_before_any_process(self):
        self.begin.stop()
        self.begin = mock.patch.object(
            self.module, "_ops_begin", return_value=None)
        self.begin.start()
        with mock.patch.object(self.module.subprocess, "run") as run:
            response = self.client.post(
                "/op/restart_burnin", headers=self.headers, json={})
        self.assertEqual(response.status_code, 503)
        self.assertIn("ledger unavailable", response.get_json()["error"])
        run.assert_not_called()
        self.assertEqual(self.events, [])

    def test_inactive_service_fails_after_bounded_status_check(self):
        completed = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 3, "inactive\n", ""),
        ]
        with mock.patch.object(
                self.module.subprocess, "run", side_effect=completed):
            response = self.client.post(
                "/op/restart_burnin", headers=self.headers, json={})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["state"], "inactive")
        self.assertEqual(self.events[-1], (
            "finish", (41, "fail", "is-active rc=3, state=inactive"),
        ))


if __name__ == "__main__":
    unittest.main()
