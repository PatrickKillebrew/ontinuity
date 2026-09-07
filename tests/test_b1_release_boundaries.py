import ast
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".bat", ".css", ".html", ".js", ".json", ".md", ".ps1", ".py",
    ".sh", ".sql", ".toml", ".txt", ".yaml", ".yml",
}


class B1ReleaseBoundaryTests(unittest.TestCase):
    """Regression gates for omissions found during the failed B1 transition."""

    def test_active_repository_has_no_embedded_root_literals(self):
        paths = (
            ROOT / "live" / "shepherd.py",
            ROOT / "live" / "misc" / "push_to_github.py",
            ROOT / "templates" / "kb.html",
        )
        assignment = re.compile(
            r'''(?ix)\b(?:diag(?:_key)?|github_token)\b\s*=\s*["']'''
            r'''(?P<value>[^"']{20,})["']'''
        )
        indirect_diag_assignment = re.compile(
            r'''(?is)\bDIAG\b\s*=.{0,240}?["'][A-Za-z0-9_-]{32,}["']'''
        )
        token_shape = re.compile(
            r"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"
        )
        findings = []
        for path in paths:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if (assignment.search(text) or indirect_diag_assignment.search(text)
                    or token_shape.search(text)):
                findings.append(str(path.relative_to(ROOT)))
        self.assertEqual(findings, [])

    def test_repository_has_no_high_confidence_token_shape(self):
        patterns = {
            "github_pat": re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
            "github_short": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
            "provider_key": re.compile(rb"(?:sk-|csk-|gsk_)[A-Za-z0-9._-]{20,}"),
            "google_key": re.compile(rb"AIza[A-Za-z0-9_-]{25,}"),
        }
        findings = []
        for path in ROOT.rglob("*"):
            if (not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES
                    or any(part in {".git", "__pycache__", "session_artifacts"}
                           for part in path.parts)):
                continue
            data = path.read_bytes()
            for label, pattern in patterns.items():
                if pattern.search(data):
                    findings.append((str(path.relative_to(ROOT)), label))
        self.assertEqual(findings, [])

    def test_active_service_callers_keep_diagnostic_roots_out_of_urls(self):
        client_paths = (
            ROOT / "live" / "bootstrap" / "gate.py",
            ROOT / "live" / "box" / "file_server.py",
            ROOT / "live" / "box" / "box_ops.py",
            ROOT / "live" / "shepherd.py",
            ROOT / "live" / "shepherd_alert.py",
            ROOT / "live" / "experiment" / "burnin_resident.py",
            ROOT / "live" / "control_loop.py",
            ROOT / "live" / "governor" / "governor_relay.py",
            ROOT / "live" / "governor" / "governor_routes.py",
        )
        findings = []
        for path in client_paths:
            text = path.read_text(encoding="utf-8")
            if re.search(r"[?&](?:diag_key|mailbox_key)=", text, re.IGNORECASE):
                findings.append(str(path.relative_to(ROOT)))
            if re.search(
                    r'''params\s*\[["']diag_key["']\]\s*=''',
                    text, re.IGNORECASE):
                findings.append(str(path.relative_to(ROOT)))

        app_text = (ROOT / "app.py").read_text(encoding="utf-8")
        outbound_app_patterns = (
            r'''f["'][^"']*/diag/engine\?diag_key=''',
            r'''params\s*=\s*\{\s*["']diag_key["']\s*:''',
            r'''request\.args\.get\(["']mailbox_key["']''',
        )
        if any(re.search(pattern, app_text, re.IGNORECASE)
               for pattern in outbound_app_patterns):
            findings.append("app.py")
        self.assertEqual(sorted(set(findings)), [])

    def test_credential_bearing_callers_refuse_redirects(self):
        urllib_clients = (
            "live/bootstrap/gate.py",
            "live/box/file_server.py",
            "live/box/box_ops.py",
            "live/shepherd.py",
            "live/shepherd_alert.py",
            "live/experiment/burnin_resident.py",
            "live/control_loop.py",
            "live/governor/governor_relay.py",
            "live/governor/governor_routes.py",
        )
        for relative in urllib_clients:
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("HTTPRedirectHandler", source, relative)
            self.assertIn("build_opener", source, relative)
            self.assertNotRegex(
                source, r"(?:urllib\.request|_ug_req)\.urlopen\(", relative)
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        courier = re.search(
            r"def diag_op_courier\(name\):(?P<body>.*?)(?=\n\n@app\.route)",
            app_source, re.DOTALL)
        self.assertIsNotNone(courier)
        self.assertIn("allow_redirects=False", courier.group("body"))

    def test_active_requests_clients_refuse_authenticated_redirects(self):
        for relative, client_name in (
                ("app.py", "http_requests"),
                ("model_client.py", "_requests")):
            module = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            missing = []
            for node in ast.walk(module):
                if (not isinstance(node, ast.Call)
                        or not isinstance(node.func, ast.Attribute)
                        or not isinstance(node.func.value, ast.Name)
                        or node.func.value.id != client_name
                        or node.func.attr not in {"get", "post", "put", "patch", "delete"}):
                    continue
                # The IP-discovery request is public and carries no credential.
                if (relative == "app.py" and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and "api.ipify.org" in str(node.args[0].value)):
                    continue
                redirect = next(
                    (keyword.value for keyword in node.keywords
                     if keyword.arg == "allow_redirects"), None)
                if not (isinstance(redirect, ast.Constant)
                        and redirect.value is False):
                    missing.append(node.lineno)
            self.assertEqual(missing, [], relative)

        baseline_source = (ROOT / "live" / "tools" / "release_baseline.py").read_text(
            encoding="utf-8")
        request_helper = re.search(
            r"def _request_json\((?P<body>.*?)(?=\n\ndef )",
            baseline_source, re.DOTALL)
        self.assertIsNotNone(request_helper)
        self.assertNotRegex(
            request_helper.group("body"), r'''(?:--location|-L|["']location["'])''')

    def test_model_request_and_repo_response_bounds_do_not_trust_length_header(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        bounded = re.search(
            r"def _bounded_request_json\(max_bytes\):(?P<body>.*?)(?=\n\ndef )",
            app_source, re.DOTALL)
        self.assertIsNotNone(bounded)
        self.assertIn("request.stream.read(max_bytes + 1)", bounded.group("body"))
        self.assertGreaterEqual(app_source.count("_bounded_request_json("), 3)

        box_source = (ROOT / "live" / "box" / "box_ops.py").read_text(
            encoding="utf-8")
        self.assertIn(
            "r.read(_MAX_REPO_API_RESPONSE_BYTES + 1)", box_source)

    def test_resident_mailbox_callers_use_headers_not_urls_or_bodies(self):
        for relative in ("live/shepherd.py", "live/experiment/burnin_resident.py"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("?mailbox_key=", source, relative)
            self.assertNotRegex(source, r'''["']mailbox_key["']\s*:\s*MBKEY''')
            self.assertIn("X-Mailbox-Key", source, relative)
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        auth_helper = re.search(
            r"def _mailbox_auth_ok\(\):(?P<body>.*?)(?=\ndef )",
            app_source, re.DOTALL)
        self.assertIsNotNone(auth_helper)
        self.assertIn("X-Mailbox-Key", auth_helper.group("body"))
        self.assertNotIn("request.args", auth_helper.group("body"))
        self.assertNotIn("request.get_json", auth_helper.group("body"))

    def test_current_boot_packets_request_capabilities_not_master_roots(self):
        paths = (
            ROOT / "live" / "CONTROL_QUICKBOOT.md",
            ROOT / "live" / "CONTROL_QUICKBOOT_SNIPPET.md",
            ROOT / "live" / "WORKER_QUICKBOOT.md",
            ROOT / "live" / "WORKER_BOOT_PACKET.md",
        )
        forbidden = (
            re.compile(r"find and read (?:it|llaves)", re.IGNORECASE),
            re.compile(r"read [`']?llaves", re.IGNORECASE),
            re.compile(r"diag_key\s*:\s*<<", re.IGNORECASE),
            re.compile(r"set (?:it|the .*key).*diag_key", re.IGNORECASE),
        )
        findings = []
        missing_capability_contract = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if any(pattern.search(text) for pattern in forbidden):
                findings.append(str(path.relative_to(ROOT)))
            if "capabil" not in text.lower():
                missing_capability_contract.append(str(path.relative_to(ROOT)))
        self.assertEqual(findings, [])
        self.assertEqual(missing_capability_contract, [])

    def test_initial_model_capability_scope_excludes_high_impact_ops(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        assigned = None
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(target, ast.Name)
                   and target.id == "B1_INITIAL_MODEL_OPS"
                   for target in node.targets):
                assigned = set(ast.literal_eval(node.value))
                break
        self.assertIsNotNone(assigned, "B1_INITIAL_MODEL_OPS is not defined")
        self.assertTrue({"bootstrap_gate", "read_repo"}.issubset(assigned))
        self.assertTrue({"mailbox_send", "mailbox_fetch", "mailbox_ack",
                         "mailbox_peek", "you_there"}.issubset(assigned))
        self.assertTrue(assigned.isdisjoint({
            "backup_db", "commit_file", "commit_self", "deploy",
            "mailbox_purge", "read_file", "register_egress",
            "restart_workspace", "seed_tenant", "write_file",
        }))

    def test_operator_can_inspect_approve_and_revoke_from_main(self):
        app_text = (ROOT / "app.py").read_text(encoding="utf-8")
        for route in (
                "/diag/admission/requests",
                "/diag/admission/approve",
                "/diag/admission/revoke"):
            self.assertTrue(route in app_text, route)
        page = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        for marker in (
                "admission-panel", "admission-pending",
                "approve-admission", "revoke-capability"):
            self.assertTrue(marker in page, marker)
        self.assertNotRegex(
            page,
            r'''(?:localStorage|sessionStorage)\.(?:setItem|getItem)\([^\n]*admission''')
        self.assertIn("document.getElementById('admission-operator-key').value = '';",
                      page)
        self.assertIn("redirect: 'error'", page)

    def test_pending_admission_registry_is_bounded_and_pruned(self):
        path = ROOT / "capability_auth.py"
        self.assertTrue(path.exists(), "capability authority is absent")
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        constants = {}
        for node in ast.walk(module):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Name)
                            and target.id in {
                                "MAX_PENDING_REQUESTS",
                                "PENDING_REQUEST_TTL_SECONDS",
                            }):
                        constants[target.id] = ast.literal_eval(node.value)
        self.assertIn("MAX_PENDING_REQUESTS", constants)
        self.assertIn("PENDING_REQUEST_TTL_SECONDS", constants)
        self.assertGreater(constants["MAX_PENDING_REQUESTS"], 0)
        self.assertLessEqual(constants["MAX_PENDING_REQUESTS"], 500)
        self.assertGreater(constants["PENDING_REQUEST_TTL_SECONDS"], 0)
        self.assertIn("prune", source.lower())

    def test_install_manifest_covers_every_b1_runtime_dependency(self):
        manifest = ROOT / "live" / "B1_INSTALL_MANIFEST.json"
        self.assertTrue(manifest.exists(), "B1 install manifest is absent")
        text = manifest.read_text(encoding="utf-8")
        for relative in (
                "app.py", "capability_auth.py", "live/bootstrap/gate.py",
                "model_client.py",
                "live/box/file_server.py", "live/box/box_ops.py",
                "live/box/seat_mailbox.py",
                "live/shepherd.py", "live/shepherd_alert.py",
                "live/experiment/burnin_resident.py",
                "live/ONTINUITY_1_0_BOARD.md",
                "live/ONTINUITY_1_0_COMPLETION_PLAN.md",
                "live/specs/verified_bootstrap_gate.md"):
            self.assertIn(relative, text)

        data = json.loads(text)
        base = data["candidate_base_commit"]
        self.assertEqual(
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            base,
        )
        rows = []
        rows.extend(data["engine_deploy"]["required"])
        rows.extend(data["box_install"]["required"])
        rows.extend(data["active_service_sources"]["required"])
        rows.extend(data["repository_contract"]["required"])
        rows.extend(data["verification_sources"]["required"])
        rows.extend(data["retire_during_authorized_cutover"])
        for row in rows:
            digest = hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, row["sha256"], row["path"])
            self.assertNotEqual(row["sha256"], "REFRESH", row["path"])
        for row in data["public_removals"]:
            self.assertFalse((ROOT / row["path"]).exists(), row["path"])
            base_bytes = subprocess.check_output(
                ["git", "show", f'{base}:{row["path"]}'], cwd=ROOT)
            self.assertEqual(
                hashlib.sha256(base_bytes).hexdigest(), row["base_sha256"],
                row["path"],
            )

        covered = {row["path"] for row in rows}
        covered.update(row["path"] for row in data["public_removals"])
        covered.update(row["receipt"] for row in data["public_removals"])
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only"], cwd=ROOT, text=True
        ).splitlines())
        untracked = set(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT, text=True,
        ).splitlines())
        relevant = {
            path for path in changed | untracked
            if "__pycache__" not in Path(path).parts
            and not path.endswith(".pyc")
            and path != "live/B1_INSTALL_MANIFEST.json"
        }
        self.assertEqual(relevant - covered, set())
        retirement = data["retire_during_authorized_cutover"]
        self.assertTrue(any(row.get("path") == "live/box/laptop_seat.py"
                            and row.get("action") == "install_tombstone_and_stop"
                            for row in retirement))

    def test_current_roadmap_identity_ceiling_and_cutover_order_are_coherent(self):
        for relative in (
                "live/ONTINUITY_1_0_BOARD.md",
                "live/ONTINUITY_1_0_COMPLETION_PLAN.md"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("codex/b1-corrected", source, relative)
            self.assertIn("3476ed8", source, relative)
            self.assertRegex(
                source,
                r"(?is)superseded.{0,120}codex/b1-scoped-identity|"
                r"codex/b1-scoped-identity.{0,120}(?:superseded|must not)",
                relative,
            )

        paradigm = (ROOT / "live" / "THE_PARADIGM.md").read_text(
            encoding="utf-8")
        rubric = (ROOT / "live" / "OPERATING_RUBRIC.md").read_text(
            encoding="utf-8")
        for source in (paradigm, rubric):
            self.assertIn("capability-authenticated", source)
            self.assertIn("legacy/operator", source)

        manifest = json.loads(
            (ROOT / "live" / "B1_INSTALL_MANIFEST.json").read_text(
                encoding="utf-8"))
        actions = [row["action"] for row in manifest["cutover_order"]]
        self.assertEqual(actions, [
            "preflight", "install_box", "verify_box",
            "install_active_services", "deploy_main", "deploy_farm",
            "prove_capabilities", "retire_laptop",
        ])
        self.assertEqual(
            [row["order"] for row in manifest["cutover_order"]],
            list(range(1, 9)),
        )

    def test_alert_target_preserves_installed_control_behavior(self):
        source = (ROOT / "live" / "shepherd_alert.py").read_text(
            encoding="utf-8")
        self.assertIn('os.environ.get("SHEPHERD_ALERT_TO_SEAT", "control")',
                      source)
        self.assertRegex(source, r'''["']to_seat["']\s*:\s*ALERT_TO_SEAT''')

    def test_keyboard_helper_is_separate_and_legacy_laptop_seat_is_inert(self):
        for relative in (
                "templates/kb.html",
                "live/tools/ipad_keyboard.py",
                "live/tools/ipad_keyboard_CONTRACT.md",
                "live/tools/ipad_keyboard_CORPUS.md"):
            self.assertFalse((ROOT / relative).exists(), relative)
        app_text = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("@app.route('/kb')", app_text)
        laptop = (ROOT / "live" / "box" / "laptop_seat.py").read_text(
            encoding="utf-8")
        for forbidden in (
                "DIAG_KEY", "X-Diag-Key", "urlopen", "subprocess.run",
                "mailbox_fetch", "mailbox_send", "mailbox_ack"):
            self.assertNotIn(forbidden, laptop)

    def test_legacy_sync_helper_fails_closed_without_environment_token(self):
        fake_github = types.ModuleType("github")
        fake_github.Github = object
        fake_github.GithubException = type("GithubException", (Exception,), {})
        script = ROOT / "live" / "misc" / "push_to_github.py"
        with mock.patch.dict(sys.modules, {"github": fake_github}), \
                mock.patch.dict("os.environ", {"GITHUB_TOKEN": ""}), \
                mock.patch.object(sys, "argv", [str(script), "unused.txt"]):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(stopped.exception.code, 1)

    def test_control_loop_entrypoint_fails_cleanly_without_capability(self):
        script = ROOT / "live" / "control_loop.py"
        env = dict(os.environ)
        env.pop("ONTINUITY_CAPABILITY", None)
        completed = subprocess.run(
            [sys.executable, str(script)], cwd=ROOT, env=env,
            text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"error": "ONTINUITY_CAPABILITY is not configured"},
        )
        self.assertNotIn("/home/claude", script.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
