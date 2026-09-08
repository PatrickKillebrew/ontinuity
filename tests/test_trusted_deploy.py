import fcntl
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from live.box import trusted_deploy as deploy

PROJECT = "11111111-1111-4111-8111-111111111111"
ENVIRONMENT = "22222222-2222-4222-8222-222222222222"
MAIN_SERVICE = "33333333-3333-4333-8333-333333333333"
FARM_SERVICE = "44444444-4444-4444-8444-444444444444"
DEPLOYMENT = "55555555-5555-4555-8555-555555555555"
COMMIT = "a" * 40


class TrustedDeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            "ONTINUITY_DEPLOY_STATE_DIR": self.tmp.name,
            "HOSTING_PROVIDER": "railway", "RAILWAY_TOKEN": "server-only-token",
            "RAILWAY_PROJECT_ID": PROJECT,
            "RAILWAY_ENVIRONMENT_ID": ENVIRONMENT,
            "RAILWAY_SERVICE_ID_MAIN": MAIN_SERVICE,
            "RAILWAY_SERVICE_ID_FARM": FARM_SERVICE,
        }, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def provider(self, *responses):
        return mock.patch.object(deploy, "_provider_request", side_effect=responses)

    def start(self):
        with self.provider({"serviceInstanceDeployV2": DEPLOYMENT}):
            return deploy.start("block-1", "main", COMMIT)

    def state_path(self):
        track = deploy.tracking_id("block-1", "main", COMMIT)
        return Path(self.tmp.name) / (track + ".json")

    def state(self):
        track = deploy.tracking_id("block-1", "main", COMMIT)
        return deploy.load_state(track, "block-1", "main", COMMIT)

    def node(self, status="SUCCESS", **changes):
        node = {"id": DEPLOYMENT, "status": status,
                "serviceId": MAIN_SERVICE, "meta": {"commitHash": COMMIT}}
        node.update(changes)
        return {"deployments": {"edges": [{"node": node}]}}

    def test_request_contract_rejects_extra_bad_and_nonstrings(self):
        valid = {"action": "start", "target": "main",
                 "signoff_block_id": "block-1", "commit_sha": COMMIT}
        for key in ("provider", "url", "header", "query", "graphql",
                    "project_id", "environment_id", "service_id",
                    "deployment_id", "log_limit", "token", "dry_run", "shell"):
            with self.subTest(key=key), self.assertRaises(deploy.DeployError):
                deploy.validate_request({**valid, key: "attacker-choice"})
        for key, value in (("action", "run"), ("target", "box"),
                           ("commit_sha", "A" * 40), ("commit_sha", "a" * 39),
                           ("signoff_block_id", "bad block"), ("target", 1)):
            with self.subTest(key=key), self.assertRaises(deploy.DeployError):
                deploy.validate_request({**valid, key: value})

    def test_transport_is_only_literal_curl_config_stdin_without_shell(self):
        source = inspect.getsource(deploy._provider_request)
        self.assertIn('["curl", "--config", "-"]', source)
        self.assertIn("shell=False", source)
        self.assertIn('"CURL_HOME": "/dev/null"', source)
        self.assertNotIn('"HOME":', source)
        self.assertNotIn('"XDG_CONFIG_HOME":', source)
        whole = inspect.getsource(deploy)
        for forbidden in ("urllib", "requests", "httpx"):
            self.assertNotIn(forbidden, whole)

    def test_fake_curl_executes_without_network_with_private_stdin_config(self):
        fake_dir = Path(self.tmp.name) / "fake-bin"
        fake_dir.mkdir()
        args_path = Path(self.tmp.name) / "argv.txt"
        facts_path = Path(self.tmp.name) / "facts.txt"
        script = fake_dir / "curl"
        script.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$#\" \"$1\" \"$2\" > {str(args_path)!r}\n"
            "token=0; proto=0; timeout=0; redirect=0; fail=0; status=0\n"
            "home=0; xdg=0; curlhome=0\n"
            "[ \"${HOME+x}\" = x ] && home=1\n"
            "[ \"${XDG_CONFIG_HOME+x}\" = x ] && xdg=1\n"
            "[ \"${CURL_HOME-}\" = /dev/null ] && curlhome=1\n"
            "while IFS= read -r line || [ -n \"$line\" ]; do\n"
            " case \"$line\" in\n"
            "  *server-only-token*) token=1;;\n"
            "  'proto = \"=https\"') proto=1;;\n"
            "  'max-time = 8') timeout=1;;\n"
            "  'location = false') redirect=1;;\n"
            "  'fail = true') fail=1;;\n"
            "  'write-out = \"%{http_code}\"') status=1;;\n"
            " esac\n"
            "done\n"
            f"printf '%s\\n' \"$token\" \"$proto\" \"$timeout\" \"$redirect\" \"$fail\" \"$status\" \"$home\" \"$xdg\" \"$curlhome\" > {str(facts_path)!r}\n"
            f"printf '%s' '{{\"data\":{{\"serviceInstanceDeployV2\":\"{DEPLOYMENT}\"}}}}200'\n",
            encoding="utf-8")
        script.chmod(0o700)
        _provider, config = deploy._provider_config("main")
        with mock.patch.object(deploy.os, "defpath", str(fake_dir)):
            data = deploy._provider_request(config, deploy.RAILWAY_DEPLOY_MUTATION, {
                "serviceId": MAIN_SERVICE, "environmentId": ENVIRONMENT,
                "commitSha": COMMIT})
        self.assertEqual(data["serviceInstanceDeployV2"], DEPLOYMENT)
        argv = args_path.read_text(encoding="utf-8")
        self.assertEqual(argv.splitlines(), ["2", "--config", "-"])
        self.assertNotIn("server-only-token", argv)
        self.assertEqual(facts_path.read_text(encoding="utf-8").splitlines(),
                         ["1", "1", "1", "1", "1", "1", "0", "0", "1"])

    def test_fake_curl_rejects_data_shaped_redirect_without_network(self):
        fake_dir = Path(self.tmp.name) / "redirect-bin"
        fake_dir.mkdir()
        script = fake_dir / "curl"
        script.write_text(
            "#!/bin/sh\n"
            "while IFS= read -r line || [ -n \"$line\" ]; do :; done\n"
            f"printf '%s' '{{\"data\":{{\"serviceInstanceDeployV2\":\"{DEPLOYMENT}\"}}}}302'\n",
            encoding="utf-8")
        script.chmod(0o700)
        _provider, config = deploy._provider_config("main")
        with mock.patch.object(deploy.os, "defpath", str(fake_dir)):
            with self.assertRaisesRegex(deploy.DeployError, "HTTP status"):
                deploy._provider_request(
                    config, deploy.RAILWAY_DEPLOY_MUTATION,
                    {"serviceId": MAIN_SERVICE,
                     "environmentId": ENVIRONMENT,
                     "commitSha": COMMIT})

    def test_provider_facts_are_server_owned(self):
        captured = []
        with mock.patch.object(deploy, "_provider_request",
                side_effect=lambda config, query, variables:
                captured.append((config, query, variables)) or
                {"serviceInstanceDeployV2": DEPLOYMENT}):
            deploy.start("block-1", "main", COMMIT)
        config, query, variables = captured[0]
        self.assertEqual(config["token"], "server-only-token")
        self.assertEqual(query, deploy.RAILWAY_DEPLOY_MUTATION)
        self.assertEqual(variables, {"serviceId": MAIN_SERVICE,
                                     "environmentId": ENVIRONMENT,
                                     "commitSha": COMMIT})

    def test_bad_provider_configuration_fails_before_dispatch(self):
        for changes in ({"HOSTING_PROVIDER": "invented"},
                        {"RAILWAY_PROJECT_ID": "not-a-uuid"},
                        {"RAILWAY_TOKEN": ""},
                        {"RAILWAY_TOKEN": "bad\nheader"}):
            with self.subTest(changes=changes), mock.patch.dict(
                    os.environ, changes), mock.patch.object(
                    deploy, "_provider_request") as provider:
                with self.assertRaises(deploy.DeployError):
                    deploy.start("block-1", "main", COMMIT)
                provider.assert_not_called()

    def test_start_replay_never_duplicates_provider_mutation(self):
        with self.provider({"serviceInstanceDeployV2": DEPLOYMENT}) as provider:
            first, first_new = deploy.start("block-1", "main", COMMIT)
            second, second_new = deploy.start("block-1", "main", COMMIT)
        self.assertTrue(first_new)
        self.assertFalse(second_new)
        self.assertEqual(first, second)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(stat.S_IMODE(self.state_path().stat().st_mode), 0o600)

    def test_accepted_start_replay_requires_current_provider_binding(self):
        self.start()
        replacement = "66666666-6666-4666-8666-666666666666"
        with mock.patch.dict(os.environ, {"RAILWAY_SERVICE_ID_MAIN": replacement}), \
                mock.patch.object(deploy, "_provider_request") as provider:
            with self.assertRaisesRegex(deploy.DeployError,
                                        "configuration changed"):
                deploy.start("block-1", "main", COMMIT)
        provider.assert_not_called()

    def test_global_lock_is_single_private_and_bounded(self):
        for suffix in ("1", "2", "3"):
            with deploy.tuple_lock(suffix * 64):
                pass
        locks = [name for name in os.listdir(self.tmp.name) if name.endswith(".lock")]
        self.assertEqual(locks, [".deploy-state.lock"])
        lock_path = Path(self.tmp.name) / locks[0]
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)
        descriptor = os.open(lock_path, os.O_RDWR)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with mock.patch.object(deploy, "LOCK_WAIT_SECONDS", 0.05):
                before = deploy.time.monotonic()
                with self.assertRaisesRegex(deploy.DeployError, "timed out"):
                    with deploy.tuple_lock("a" * 64):
                        pass
                self.assertLess(deploy.time.monotonic() - before, 0.5)
        finally:
            os.close(descriptor)

    def test_atomic_state_write_fsyncs_file_and_directory(self):
        self.start()
        with mock.patch.object(deploy.os, "fsync", wraps=os.fsync) as fsync:
            deploy.save_state(self.state())
        self.assertEqual(fsync.call_count, 2)

    def test_persisted_state_timestamps_are_exact_json_integers(self):
        self.start()
        good = self.state()
        self.assertIs(type(good["created_at"]), int)
        self.assertIs(type(good["updated_at"]), int)
        for field in ("created_at", "updated_at"):
            for value in ("1300", 1300.0, True, -1):
                with self.subTest(field=field, value=value):
                    self.state_path().write_text(
                        json.dumps({**good, field: value}), encoding="utf-8")
                    with self.assertRaisesRegex(deploy.DeployError,
                                                "state is corrupt"):
                        deploy.start("block-1", "main", COMMIT)

    def test_crash_window_fails_unknown_without_retry(self):
        real_save = deploy.save_state
        calls = [0]
        def crash_on_second(record):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError("simulated process loss")
            return real_save(record)
        with self.provider({"serviceInstanceDeployV2": DEPLOYMENT}) as provider:
            with mock.patch.object(deploy, "save_state", side_effect=crash_on_second):
                with self.assertRaises(RuntimeError):
                    deploy.start("block-1", "main", COMMIT)
        with mock.patch.object(deploy, "_provider_request") as retry:
            with self.assertRaisesRegex(deploy.DeployError, "reconciliation"):
                deploy.start("block-1", "main", COMMIT)
            retry.assert_not_called()
        self.assertEqual(provider.call_count, 1)

    def test_corrupt_state_log_phase_and_oversize_fail_closed(self):
        self.start()
        good = self.state()
        corruptions = [
            {**good, "schema": True},
            {**good, "schema": 1.0},
            {**good, "terminal": "yes"},
            {**good, "phase": "success", "terminal": False,
             "provider_status": "SUCCESS"},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": -1, "severity_counts": {},
                 "first_timestamp": None, "last_timestamp": None}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": {"bad": 1}},
                 "first_timestamp": None, "last_timestamp": None}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 0, "severity_counts": {},
                 "first_timestamp": "bad\ncontrol", "last_timestamp": None}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": 1},
                 "first_timestamp": None,
                 "last_timestamp": "2026-09-08T10:00:00Z"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 0,
                 "severity_counts": {},
                 "first_timestamp": "2026-09-08T10:00:00Z",
                 "last_timestamp": "2026-09-08T10:00:00Z"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": 1},
                 "first_timestamp": "2026-09-08T10:01:00Z",
                 "last_timestamp": "2026-09-08T10:00:00Z"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": 0},
                 "first_timestamp": "2026-09-08T10:00:00Z",
                 "last_timestamp": "2026-09-08T10:00:00Z"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"provider_message": 1},
                 "first_timestamp": "2026-09-08T10:00:00.000000Z",
                 "last_timestamp": "2026-09-08T10:00:00.000000Z"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": 1},
                 "first_timestamp": "provider said the build failed",
                 "last_timestamp": "provider said the build failed"}},
            {**good, "phase": "failure", "terminal": True,
             "provider_status": "FAILED", "log_summary": {
                 "available": True, "line_count": 1,
                 "severity_counts": {"error": 1},
                 "first_timestamp": "2026-13-08T10:00:00.000000Z",
                 "last_timestamp": "2026-13-08T10:00:00.000000Z"}},
        ]
        for index, record in enumerate(corruptions):
            with self.subTest(index=index):
                self.state_path().write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(deploy.DeployError):
                    deploy.start("block-1", "main", COMMIT)
        self.state_path().write_bytes(b"{" + b"x" * 9000)
        with self.assertRaisesRegex(deploy.DeployError, "exceeds"):
            deploy.start("block-1", "main", COMMIT)

    def test_symlink_and_nonregular_state_objects_fail_closed(self):
        outside = Path(self.tmp.name).parent / "outside-state.json"
        outside.write_text("do not touch", encoding="utf-8")
        try:
            self.state_path().symlink_to(outside)
            with self.assertRaisesRegex(deploy.DeployError, "regular"):
                deploy.start("block-1", "main", COMMIT)
            self.state_path().unlink()
            lock_path = Path(self.tmp.name) / ".deploy-state.lock"
            lock_path.unlink()
            lock_path.mkdir()
            with self.assertRaisesRegex(deploy.DeployError, "regular"):
                deploy.start("block-1", "main", COMMIT)
        finally:
            outside.unlink(missing_ok=True)

    def test_symlink_state_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as parent:
            actual = Path(parent) / "actual"
            actual.mkdir()
            link = Path(parent) / "link"
            link.symlink_to(actual, target_is_directory=True)
            with mock.patch.dict(os.environ, {"ONTINUITY_DEPLOY_STATE_DIR": str(link)}):
                with self.assertRaisesRegex(deploy.DeployError, "regular directory"):
                    deploy.start("block-1", "main", COMMIT)

    def test_status_binds_stored_id_service_commit_and_conflicting_meta(self):
        self.start()
        cases = (
            (self.node(id="66666666-6666-4666-8666-666666666666"), "not found"),
            (self.node(serviceId=FARM_SERVICE), "service binding"),
            (self.node(meta={"commitHash": "b" * 40}), "commit binding"),
            (self.node(meta={"commitHash": COMMIT, "commitSha": "b" * 40}),
             "conflicts"),
        )
        for payload, message in cases:
            with self.subTest(message=message), self.provider(payload):
                with self.assertRaisesRegex(deploy.DeployError, message):
                    deploy.status("block-1", "main", COMMIT)

    def test_malformed_provider_data_is_a_bounded_failure(self):
        self.start()
        for payload in (None, {}, {"deployments": None},
                        {"deployments": {"edges": [None]}}):
            with self.subTest(payload=payload), self.provider(payload):
                with self.assertRaises(deploy.DeployError):
                    deploy.status("block-1", "main", COMMIT)

    def test_pending_success_and_terminal_replay_are_idempotent(self):
        self.start()
        with self.provider(self.node("BUILDING"), self.node("SUCCESS")) as provider:
            first, first_new = deploy.status("block-1", "main", COMMIT)
            second, second_new = deploy.status("block-1", "main", COMMIT)
            third, third_new = deploy.status("block-1", "main", COMMIT)
        self.assertEqual(first["action_state"], "pending")
        self.assertFalse(first_new)
        self.assertEqual(second["action_state"], "success")
        self.assertTrue(second_new)
        self.assertEqual(third, second)
        self.assertFalse(third_new)
        self.assertEqual(provider.call_count, 2)

    def test_terminal_failure_is_durable_before_optional_log_failure(self):
        self.start()
        with self.provider(self.node("FAILED"),
                           deploy.DeployError("logs unavailable", status=502)):
            result, newly_terminal = deploy.status("block-1", "main", COMMIT)
        self.assertTrue(newly_terminal)
        self.assertFalse(result["ok"])
        self.assertFalse(result["build_logs"]["available"])
        with mock.patch.object(deploy, "_provider_request") as provider:
            replay, replay_new = deploy.status("block-1", "main", COMMIT)
            start_replay, start_new = deploy.start("block-1", "main", COMMIT)
        provider.assert_not_called()
        self.assertEqual(replay, result)
        self.assertEqual(start_replay, result)
        self.assertFalse(replay_new)
        self.assertFalse(start_new)

    def test_terminal_start_replay_requires_current_provider_binding(self):
        self.start()
        with self.provider(self.node("SUCCESS")):
            result, newly_terminal = deploy.status(
                "block-1", "main", COMMIT)
        self.assertTrue(newly_terminal)
        self.assertTrue(result["terminal"])
        replacement = "77777777-7777-4777-8777-777777777777"
        with mock.patch.dict(os.environ, {"RAILWAY_PROJECT_ID": replacement}), \
                mock.patch.object(deploy, "_provider_request") as provider:
            with self.assertRaisesRegex(deploy.DeployError,
                                        "configuration changed"):
                deploy.start("block-1", "main", COMMIT)
        provider.assert_not_called()

    def test_failure_logs_return_only_bounded_metadata(self):
        self.start()
        secret = "unlabeled-secret-material-that-must-never-escape"
        logs = {"buildLogs": [
            {"message": secret, "severity": "error",
             "timestamp": "2026-09-08T10:00:00Z"},
            {"message": "ordinary", "severity": "info",
             "timestamp": "2026-09-08T10:01:00Z"}]}
        with self.provider(self.node("FAILED"), logs) as provider:
            result, terminal = deploy.status("block-1", "main", COMMIT)
        self.assertTrue(terminal)
        encoded = json.dumps(result)
        self.assertNotIn(secret, encoded)
        self.assertNotIn("ordinary", encoded)
        self.assertNotIn("hash", encoded)
        self.assertEqual(result["build_logs"]["severity_counts"],
                         {"error": 1, "info": 1})
        self.assertEqual(provider.call_args_list[1].args[1], deploy.RAILWAY_LOGS_QUERY)
        self.assertEqual(provider.call_args_list[1].args[2],
                         {"deploymentId": DEPLOYMENT, "limit": deploy.BUILD_LOG_LIMIT})

    def test_failure_log_severity_is_fixed_and_timestamps_are_canonical_utc(self):
        self.start()
        arbitrary = "provider-message-disguised-as-severity"
        logs = {"buildLogs": [
            {"message": "first", "severity": arbitrary,
             "timestamp": "2026-09-08T05:00:00-05:00"},
            {"message": "second", "severity": "WARN",
             "timestamp": "2026-09-08T10:00:00.250000Z"},
        ]}
        with self.provider(self.node("FAILED"), logs):
            result, terminal = deploy.status("block-1", "main", COMMIT)
        self.assertTrue(terminal)
        summary = result["build_logs"]
        self.assertEqual(summary["severity_counts"],
                         {"unknown": 1, "warning": 1})
        self.assertEqual(summary["first_timestamp"],
                         "2026-09-08T10:00:00.000000Z")
        self.assertEqual(summary["last_timestamp"],
                         "2026-09-08T10:00:00.250000Z")
        encoded = json.dumps({"result": result, "state": self.state()})
        self.assertNotIn(arbitrary, encoded)

    def test_provider_message_disguised_as_timestamp_leaves_unavailable_summary(self):
        self.start()
        disguised = "provider message: build failed"
        logs = {"buildLogs": [
            {"message": "ordinary", "severity": "error",
             "timestamp": disguised},
        ]}
        with self.provider(self.node("FAILED"), logs):
            result, terminal = deploy.status("block-1", "main", COMMIT)
        self.assertTrue(terminal)
        self.assertEqual(result["build_logs"], {
            "available": False, "line_count": 0, "severity_counts": {},
            "first_timestamp": None, "last_timestamp": None,
        })
        encoded = json.dumps({"result": result, "state": self.state()})
        self.assertNotIn(disguised, encoded)

    def test_provider_deadline_budget_fits_outer_relay(self):
        self.assertLess(deploy.PROVIDER_PROCESS_DEADLINE_SECONDS * 2, 25)
        self.assertEqual(deploy.PROVIDER_TIMEOUT_SECONDS, 8)
        self.assertLessEqual(deploy.LOCK_WAIT_SECONDS, 2)

    def test_installed_side_by_side_layout_imports_trusted_adapter(self):
        root = Path(__file__).resolve().parents[1]
        install_dir = Path(self.tmp.name) / "installed-box"
        install_dir.mkdir()
        shutil.copy2(root / "live/box/box_ops.py", install_dir / "box_ops.py")
        shutil.copy2(root / "live/box/trusted_deploy.py", install_dir / "trusted_deploy.py")
        code = ("import importlib.util,sys;"
                f"sys.path.insert(0,{str(install_dir)!r});"
                f"p={str(install_dir / 'box_ops.py')!r};"
                "s=importlib.util.spec_from_file_location('installed_box_ops',p);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "assert m.trusted_deploy.__file__.endswith('trusted_deploy.py')")
        completed = subprocess.run([sys.executable, "-I", "-c", code],
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
