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
            r"def _bounded_request_payload\(max_bytes\):(?P<body>.*?)(?=\n\ndef )",
            app_source, re.DOTALL)
        self.assertIsNotNone(bounded)
        self.assertIn("request.stream.read(max_bytes + 1)", bounded.group("body"))
        self.assertGreaterEqual(app_source.count("_bounded_request_payload("), 3)

        box_source = (ROOT / "live" / "box" / "box_ops.py").read_text(
            encoding="utf-8")
        self.assertIn(
            "r.read(_MAX_REPO_API_RESPONSE_BYTES + 1)", box_source)

    def test_courier_streams_and_bounds_box_responses_before_decoding(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        bounded = re.search(
            r"def _bounded_relay_response\(response, max_bytes\):"
            r"(?P<body>.*?)(?=\n\ndef )",
            app_source, re.DOTALL)
        self.assertIsNotNone(bounded)
        self.assertIn("iter_content", bounded.group("body"))
        self.assertIn("total > max_bytes", bounded.group("body"))
        courier = re.search(
            r"def diag_op_courier\(name\):(?P<body>.*?)(?=\n\n@app\.route)",
            app_source, re.DOTALL)
        self.assertIsNotNone(courier)
        self.assertIn("stream=True", courier.group("body"))
        self.assertIn("MAX_REPLAY_BODY_BYTES if side_effecting",
                      courier.group("body"))
        self.assertNotIn("r.text", courier.group("body"))

    def test_transport_manifest_and_handoff_state_are_not_self_contradictory(self):
        handoff = (ROOT / "live" / "CONTROL_HANDOFF.md").read_text(
            encoding="utf-8")
        self.assertEqual(handoff.count("**SINGLE NEXT ACTION:**"), 1)
        self.assertNotIn("CURRENT CONTROLLING ACTION", handoff)
        self.assertIn("HISTORICAL PREDECESSOR", handoff)
        self.assertIn("SUPERSEDED BY THE CURRENT OVERRIDE", handoff)

        manifest = json.loads(
            (ROOT / "live" / "B1_TRANSPORT_LOCK_MANIFEST.json").read_text(
                encoding="utf-8"))
        checks = "\n".join(manifest["required_checks"])
        self.assertNotIn("private secret equality scan", checks)
        self.assertIn("high-confidence repository secret-pattern scan", checks)

    def test_current_action_surfaces_bind_the_same_transport_and_review_state(self):
        queue = (ROOT / "live" / "agent_queue.md").read_text(encoding="utf-8")
        latest_fold = queue.rsplit("\n## FOLD — ", 1)[-1]
        punch = (ROOT / "live" / "PUNCH_LIST.md").read_text(encoding="utf-8")
        board = (ROOT / "live" / "ONTINUITY_1_0_BOARD.md").read_text(
            encoding="utf-8")
        plan = (ROOT / "live" / "ONTINUITY_1_0_COMPLETION_PLAN.md").read_text(
            encoding="utf-8")
        board_b1 = board.split("### B1 —", 1)[1].split("### B2 —", 1)[0]
        current_board = board.split("## 4. CURRENT SINGLE NEXT ACTION", 1)[1]
        current_board = current_board.split("\n---", 1)[0]
        current_plan = plan.split("## 8. IMMEDIATE NEXT ACTION", 1)[1]
        current_plan = current_plan.split("\n---", 1)[0]
        current_punch = punch.split("## IN-PROGRESS", 1)[1]
        current_punch = current_punch.split("## DONE", 1)[0]

        self.assertIn("exact-object and transport hardening refrozen", latest_fold)
        self.assertIn("curl --disable --config - < REQUEST.curl", latest_fold)
        self.assertIn("accepted local transport base `6f52063`", latest_fold)
        self.assertIn("new clean independent review", latest_fold)
        self.assertIn("Patrick's authorization", latest_fold)
        self.assertNotIn("obtain a second clean independent review", latest_fold.lower())

        roadmap = next(
            line for line in punch.splitlines()
            if "ONTINUITY 1.0 COMPLETION PLAN — controlling roadmap" in line)
        self.assertIn("new independent exact-byte review", roadmap)
        self.assertIn("`6f52063`", roadmap)
        self.assertIn("Patrick's authorization", roadmap)
        self.assertNotIn("second independent exact-byte review", roadmap.lower())

        self.assertIn("new independent review", current_board)
        self.assertIn("`6f52063`", current_board)
        self.assertIn("Patrick's authorization", current_board)
        self.assertNotIn("second independent review", current_board.lower())

        for name, current_surface in (
                ("latest queue fold", latest_fold),
                ("board B1", board_b1),
                ("completion-plan action", current_plan),
                ("punch-list in-progress", current_punch)):
            self.assertIn("complete current", current_surface.lower(), name)
            self.assertNotRegex(
                current_surface.lower(), r"\b\d+[ -]tests?\b", name)

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
            "restart_burnin", "restart_workspace", "seed_tenant", "write_file",
        }))
        elevated = None
        for node in module.body:
            if (isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name)
                            and target.id == "B1_ELEVATED_MODEL_OPS"
                            for target in node.targets)):
                elevated = set(ast.literal_eval(node.value))
                break
        self.assertEqual(elevated, {"deploy"})

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
        self.assertIn("ELEVATED / HIGH-IMPACT", page)
        self.assertIn("elevated_confirmed", page)
        self.assertIn("window.confirm", page)
        for field in ("signoff_block_id", "target_scope", "commit_sha"):
            self.assertIn(field, page)

    def test_deploy_authority_is_bound_to_one_reviewed_object(self):
        authority = (ROOT / "capability_auth.py").read_text(encoding="utf-8")
        courier = (ROOT / "app.py").read_text(encoding="utf-8")
        box = (ROOT / "live" / "box" / "box_ops.py").read_text(
            encoding="utf-8")
        self.assertIn("_clean_deploy_scope", authority)
        self.assertIn('payload["deploy_scope"]', authority)
        self.assertIn('issued.get("deploy_scope") != clean_scope', authority)
        self.assertIn("_validate_deploy_capability_scope(identity, body)", courier)
        self.assertIn("deploy:v1:{target}:{commit_sha}", box)
        self.assertIn("deploy:v1:both:{commit_sha}", box)
        self.assertIn('author["ref"] != signer["ref"]', box)

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
                "live/box/seat_mailbox.py", "live/box/trusted_deploy.py",
                "live/shepherd.py", "live/shepherd_alert.py",
                "live/experiment/burnin_resident.py",
                "live/ONTINUITY_1_0_BOARD.md",
                "live/ONTINUITY_1_0_COMPLETION_PLAN.md",
                "live/specs/trusted_deploy_protocol.md",
                "live/specs/verified_bootstrap_gate.md"):
            self.assertIn(relative, text)

        data = json.loads(text)
        base = data["candidate_base_commit"]
        transport_manifest = ROOT / "live" / "B1_TRANSPORT_LOCK_MANIFEST.json"
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, "HEAD"],
            cwd=ROOT, check=True)
        rows = []
        rows.extend(data["engine_deploy"]["required"])
        rows.extend(data["box_install"]["required"])
        rows.extend(data["active_service_sources"]["required"])
        rows.extend(data["repository_contract"]["required"])
        rows.extend(data["verification_sources"]["required"])
        rows.extend(data["retire_during_authorized_cutover"])
        for row in rows:
            self.assertRegex(row["sha256"], r"\A[0-9a-f]{64}\Z", row["path"])
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
        if transport_manifest.exists():
            overlay = json.loads(transport_manifest.read_text(encoding="utf-8"))
            covered.update(row["path"] for row in overlay["required"])
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
            and path not in {
                "live/B1_INSTALL_MANIFEST.json",
                "live/B1_TRANSPORT_LOCK_MANIFEST.json",
            }
        }
        self.assertEqual(relevant - covered, set())
        retirement = data["retire_during_authorized_cutover"]
        self.assertTrue(any(row.get("path") == "live/box/laptop_seat.py"
                            and row.get("action") == "install_tombstone_and_stop"
                            for row in retirement))

    def test_install_manifest_directly_covers_cumulative_base_diff(self):
        data = json.loads((ROOT / "live" / "B1_INSTALL_MANIFEST.json").read_text(
            encoding="utf-8"))
        rows = []
        for section in ("engine_deploy", "box_install", "active_service_sources",
                        "repository_contract", "verification_sources"):
            rows.extend(data[section]["required"])
        rows.extend(data["retire_during_authorized_cutover"])
        covered = {row["path"] for row in rows}
        covered.update(row["path"] for row in data["public_removals"])
        covered.update(row["receipt"] for row in data["public_removals"])
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", data["candidate_base_commit"], "--"],
            cwd=ROOT, text=True).splitlines())
        changed.update(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT, text=True).splitlines())
        relevant = {path for path in changed
                    if "__pycache__" not in Path(path).parts
                    and not path.endswith(".pyc")
                    and path not in {"live/B1_INSTALL_MANIFEST.json",
                                     "live/B1_TRANSPORT_LOCK_MANIFEST.json"}}
        self.assertEqual(relevant - covered, set())

    def test_trusted_deploy_transport_and_public_protocol_boundary(self):
        adapter = (ROOT / "live" / "box" / "trusted_deploy.py").read_text(
            encoding="utf-8")
        self.assertIn('["curl", "--config", "-"]', adapter)
        self.assertIn("shell=False", adapter)
        self.assertIn('"proto = \\"=https\\""', adapter)
        for forbidden in ("urllib", "requests", "httpx"):
            self.assertNotIn(forbidden, adapter)
        protocol = (ROOT / "live" / "specs" /
                    "trusted_deploy_protocol.md").read_text(encoding="utf-8")
        for provider_literal in ("backboard", "Project-Access-Token",
                                 "serviceInstanceDeployV2", "buildLogs("):
            self.assertNotIn(provider_literal, protocol)

    def test_current_docs_name_the_exact_six_file_box_unit(self):
        for relative in ("live/OPERATING_MANUAL.md", "live/CONTROL_HANDOFF.md"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("six-file", source, relative)
            self.assertIn("trusted_deploy.py", source, relative)
            self.assertNotIn("main|farm|box", source, relative)
            self.assertNotIn("commit_sha?", source, relative)
            self.assertNotIn("dry_run", source, relative)

    def test_rejected_hosting_admin_compiler_has_no_forward_reference(self):
        forward_paths = (
            ROOT / "live" / "B1_INSTALL_MANIFEST.json",
            ROOT / "live" / "B1_TRANSPORT_LOCK_MANIFEST.json",
            ROOT / "live" / "CONTROL_HANDOFF.md",
            ROOT / "live" / "CONTROL_QUICKBOOT.md",
            ROOT / "live" / "CONTROL_QUICKBOOT_SNIPPET.md",
            ROOT / "live" / "OPERATING_MANUAL.md",
            ROOT / "live" / "PUNCH_LIST.md",
            ROOT / "live" / "WORKER_BOOT_PACKET.md",
            ROOT / "live" / "WORKER_MANUAL.md",
        )
        findings = [str(path.relative_to(ROOT)) for path in forward_paths
                    if re.search(r"hosting_admin|HOSTING_ADMIN", path.read_text(
                        encoding="utf-8"))]
        self.assertEqual(findings, [])

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
            "install_active_services", "deploy_main", "restart_active_service",
            "deploy_farm", "prove_capabilities", "retire_laptop",
        ])
        self.assertEqual(
            [row["order"] for row in manifest["cutover_order"]],
            list(range(1, 10)),
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

    def test_control_loop_is_local_only_and_requires_compiled_responses(self):
        script = ROOT / "live" / "control_loop.py"
        completed = subprocess.run(
            [sys.executable, str(script)], cwd=ROOT,
            text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "error": "compiled mailbox_peek and you_there response files are required",
                "transport": "curl --disable --config - < REQUEST.curl",
            },
        )
        source = script.read_text(encoding="utf-8")
        self.assertNotIn("/home/claude", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn("ONTINUITY_CAPABILITY", source)


if __name__ == "__main__":
    unittest.main()
