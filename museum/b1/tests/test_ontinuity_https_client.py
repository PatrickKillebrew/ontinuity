import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "live" / "tools" / "ontinuity_https.sh"
ENDPOINTS = ROOT / "live" / "ONTINUITY_ENDPOINTS.conf"
VERIFY_B1 = ROOT / "live" / "tools" / "b1_verify.sh"


class OntinuityHttpsClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.args = self.root / "curl.args"
        self.config = self.root / "curl.config"
        fake = self.bin / "curl"
        fake.write_text(textwrap.dedent(f"""\
            #!/bin/sh
            printf '%s\\n' "$@" > {self.args}
            cat > {self.config}
            [ "${{FAKE_CURL_EXIT:-0}}" -eq 0 ] || exit "$FAKE_CURL_EXIT"
            output=$(sed -n 's/^output = "\\(.*\\)"/\\1/p' {self.config})
            headers=$(sed -n 's/^dump-header = "\\(.*\\)"/\\1/p' {self.config})
            printf '%s' "${{FAKE_BODY:-{{\"ok\":true}}}}" > "$output"
            printf 'HTTP/1.1 %s Test\\r\\n\\r\\n' "${{FAKE_STATUS:-200}}" > "$headers"
            printf 'ONTINUITY_HTTP_STATUS=%s\\n' "${{FAKE_STATUS:-200}}"
        """), encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.body = self.root / "body.json"
        self.body.write_text("{}", encoding="utf-8")
        self.capability = self.root / "capability"
        self.capability.write_text("private-capability", encoding="utf-8")
        self.capability.chmod(0o600)

    def tearDown(self):
        self.temp.cleanup()

    def run_client(self, *args):
        return subprocess.run(
            [str(CLIENT), *map(str, args)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_curl(
            self, receipt, status="200", body='{"ok":true}', curl_exit="0"):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["FAKE_STATUS"] = status
        env["FAKE_BODY"] = body
        env["FAKE_CURL_EXIT"] = curl_exit
        with receipt.open("r", encoding="utf-8") as config_input:
            completed = subprocess.run(
                ["curl", "--disable", "--config", "-"],
                cwd=ROOT,
                env=env,
                stdin=config_input,
                text=True,
                capture_output=True,
                check=False,
            )
        if completed.returncode == 0:
            config = receipt.read_text(encoding="utf-8")
            request_id = re.search(
                r'X-Ontinuity-Request-ID: ([0-9a-f]{32})', config).group(1)
            headers = Path(f"{receipt}.d") / "response.headers"
            captured = headers.read_text(encoding="utf-8")
            headers.write_text(
                captured.replace(
                    "\n\n", f"\nX-Ontinuity-Request-ID: {request_id}\n\n"),
                encoding="utf-8",
            )
        return completed

    def prepare(self, mode, engine, operation, credential=None, name="request"):
        receipt = self.root / f"{name}.curl"
        credential_arg = credential if credential is not None else "-"
        result = self.run_client(
            "prepare", mode, engine, operation, self.body,
            credential_arg, receipt,
        )
        return receipt, result

    def test_prepare_is_local_private_and_binds_exact_inputs(self):
        receipt, result = self.prepare(
            "capability", "main", "read_repo", self.capability)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.args.exists(), "prepare unexpectedly invoked curl")
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)
        bundle = Path(f"{receipt}.d")
        meta = (bundle / "request.meta").read_text(encoding="utf-8")
        self.assertIn("client_version=2", meta)
        self.assertIn("engine=main", meta)
        self.assertIn("operation=read_repo", meta)
        self.assertIn(
            f"body_sha256={hashlib.sha256(self.body.read_bytes()).hexdigest()}",
            meta,
        )
        self.assertIn(
            "credential_sha256="
            f"{hashlib.sha256(self.capability.read_bytes()).hexdigest()}",
            meta,
        )
        self.assertNotIn("private-capability", meta)
        self.assertIn(
            f"ONTINUITY_SEND_EXACT=curl --disable --config - < {receipt}",
            result.stdout,
        )
        config = receipt.read_text(encoding="utf-8")
        request_id = re.search(
            r'X-Ontinuity-Request-ID: ([0-9a-f]{32})', config).group(1)
        request_sha256 = re.search(
            r'X-Ontinuity-Request-SHA256: ([0-9a-f]{64})', config).group(1)
        canonical = "\n".join((
            "client_version=2",
            "mode=capability",
            "operation=read_repo",
            f"request_id={request_id}",
            f"body_sha256={hashlib.sha256(self.body.read_bytes()).hexdigest()}",
            "credential_sha256="
            f"{hashlib.sha256(b'private-capability').hexdigest()}",
            "",
        )).encode("utf-8")
        self.assertEqual(request_sha256, hashlib.sha256(canonical).hexdigest())

    def test_repeated_prepare_gets_a_distinct_request_identity(self):
        first, result = self.prepare(
            "capability", "main", "read_repo", self.capability, "first")
        self.assertEqual(result.returncode, 0, result.stderr)
        second, result = self.prepare(
            "capability", "main", "read_repo", self.capability, "second")
        self.assertEqual(result.returncode, 0, result.stderr)
        pattern = re.compile(r'X-Ontinuity-Request-ID: ([0-9a-f]{32})')
        first_id = pattern.search(first.read_text(encoding="utf-8")).group(1)
        second_id = pattern.search(second.read_text(encoding="utf-8")).group(1)
        self.assertNotEqual(first_id, second_id)

    def test_credential_hash_uses_token_bytes_not_file_newline(self):
        self.capability.write_text("private-capability\n", encoding="utf-8")
        receipt, result = self.prepare(
            "capability", "main", "read_repo", self.capability, "newline")
        self.assertEqual(result.returncode, 0, result.stderr)
        meta = Path(f"{receipt}.d/request.meta").read_text(encoding="utf-8")
        self.assertIn(
            "credential_sha256="
            f"{hashlib.sha256(b'private-capability').hexdigest()}", meta)

    def test_direct_curl_owns_transport_choices_and_secret_is_not_argument(self):
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        checked = self.run_client("check", receipt)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        sent = self.run_curl(receipt)
        self.assertEqual(sent.returncode, 0, sent.stderr)
        config = self.config.read_text(encoding="utf-8")
        args = self.args.read_text(encoding="utf-8")
        self.assertIn(
            'url = "https://web-production-7eaf8.up.railway.app/diag/op/read_repo"',
            config,
        )
        self.assertIn('header = "Authorization: Bearer private-capability"', config)
        self.assertIn('request = "POST"', config)
        self.assertIn('max-redirs = 0', config)
        self.assertIn('proto = "=https"', config)
        self.assertEqual(args.splitlines(), ["--disable", "--config", "-"])
        self.assertNotIn("private-capability", args)
        verified = self.run_client("verify", receipt)
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_operator_request_uses_header_not_query(self):
        receipt, prepared = self.prepare(
            "operator", "farm", "write_file", self.capability)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        config = receipt.read_text(encoding="utf-8")
        self.assertIn(
            'url = "https://ontinuity-farm-production.up.railway.app/diag/op/write_file"',
            config,
        )
        self.assertIn('header = "X-Diag-Key: private-capability"', config)
        self.assertNotIn("diag_key=", config)

    def test_admission_is_unauthenticated_and_main_only(self):
        receipt, prepared = self.prepare(
            "admission", "main", "admission_request")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        config = receipt.read_text(encoding="utf-8")
        self.assertIn("/diag/admission/request", config)
        self.assertNotIn("Authorization:", config)
        self.assertNotIn("X-Diag-Key:", config)
        _, denied = self.prepare(
            "admission", "farm", "admission_request", name="denied")
        self.assertEqual(denied.returncode, 64)

    def test_arbitrary_route_and_loose_credentials_fail_during_prepare(self):
        _, bad_engine = self.prepare(
            "capability", "https://example.invalid", "read_repo",
            self.capability, "bad-engine",
        )
        self.assertEqual(bad_engine.returncode, 64)
        _, bad_operation = self.prepare(
            "capability", "main", "../read_repo", self.capability,
            "bad-operation",
        )
        self.assertEqual(bad_operation.returncode, 64)
        self.capability.chmod(0o644)
        _, loose = self.prepare(
            "capability", "main", "read_repo", self.capability, "loose")
        self.assertEqual(loose.returncode, 64)

        self.capability.write_text('unsafe"credential', encoding="utf-8")
        self.capability.chmod(0o600)
        _, unsafe = self.prepare(
            "capability", "main", "read_repo", self.capability, "unsafe")
        self.assertEqual(unsafe.returncode, 64)

    def test_prepare_enforces_server_body_bounds_before_network(self):
        self.body.write_bytes(b" " * 65537)
        _, capability = self.prepare(
            "capability", "main", "mailbox_send", self.capability,
            "capability-too-large")
        self.assertEqual(capability.returncode, 64)
        self.assertIn("capability request bound", capability.stderr)

        self.body.write_bytes(b" " * 16385)
        _, admission = self.prepare(
            "admission", "main", "admission_request", name="admission-too-large")
        self.assertEqual(admission.returncode, 64)
        self.assertIn("admission request bound", admission.stderr)

    def test_check_refuses_receipt_or_frozen_body_changes(self):
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability, "config-change")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        receipt.write_text(receipt.read_text(encoding="utf-8") + "verbose\n",
                           encoding="utf-8")
        self.assertEqual(self.run_client("check", receipt).returncode, 64)

        body_receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability, "body-change")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        frozen_body = Path(f"{body_receipt}.d") / "body.json"
        frozen_body.chmod(0o600)
        frozen_body.write_text('{"changed":true}', encoding="utf-8")
        self.assertEqual(self.run_client("check", body_receipt).returncode, 64)

    def test_source_changes_cannot_rewrite_prepared_request(self):
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        before = receipt.read_bytes()
        self.body.write_text('{"changed":true}', encoding="utf-8")
        self.capability.write_text("different-capability", encoding="utf-8")
        self.assertEqual(self.run_client("check", receipt).returncode, 0)
        self.assertEqual(receipt.read_bytes(), before)

    def test_receipt_survives_preexecution_or_transport_failure_for_same_command(self):
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        before = receipt.read_bytes()
        failed = self.run_curl(receipt, curl_exit="6")
        self.assertEqual(failed.returncode, 6)
        self.assertEqual(receipt.read_bytes(), before)
        retried = self.run_curl(receipt)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(self.args.read_text(encoding="utf-8").splitlines(),
                         ["--disable", "--config", "-"])

    def test_probe_treats_designed_403_as_success_but_other_403_as_failure(self):
        probe_receipt, prepared = self.prepare(
            "capability", "main", "__probe__", self.capability, "probe")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(self.run_curl(
            probe_receipt, status="403", body='{"allowed":["read_repo"]}',
        ).returncode, 0)
        probe = self.run_client("verify", probe_receipt)
        self.assertEqual(probe.returncode, 0, probe.stderr)

        denied_receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability, "denied")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(self.run_curl(
            denied_receipt, status="403", body='{"error":"denied"}',
        ).returncode, 0)
        denied = self.run_client("verify", denied_receipt)
        self.assertEqual(denied.returncode, 22)

    def test_verify_refuses_a_response_for_another_request_id(self):
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability, "wrong-response")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(self.run_curl(receipt).returncode, 0)
        headers = Path(f"{receipt}.d") / "response.headers"
        source = headers.read_text(encoding="utf-8")
        headers.write_text(re.sub(
            r"X-Ontinuity-Request-ID: [0-9a-f]{32}",
            "X-Ontinuity-Request-ID: " + "f" * 32,
            source,
        ), encoding="utf-8")
        verified = self.run_client("verify", receipt)
        self.assertEqual(verified.returncode, 75)
        self.assertIn("ONTINUITY_RESPONSE_ID_MISMATCH", verified.stderr)

    def test_client_has_no_network_wrapper_or_alternate_http_implementation(self):
        source = CLIENT.read_text(encoding="utf-8").lower()
        self.assertNotIn("python", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("command -v curl", source)
        self.assertNotIn("| curl", source)
        self.assertNotIn("$curl", source)
        self.assertIn("curl --disable --config - < request.curl", source)

    def test_logical_endpoint_registry_decouples_compiler_from_host_provider(self):
        source = CLIENT.read_text(encoding="utf-8").lower()
        for provider in ("railway", "openai", "anthropic", "claude", "chatgpt"):
            self.assertNotIn(provider, source)
        endpoints = ENDPOINTS.read_text(encoding="utf-8")
        self.assertRegex(endpoints, r"(?m)^main=https://")
        self.assertRegex(endpoints, r"(?m)^farm=https://")

    def test_real_curl_parser_accepts_compiled_stdin_without_network(self):
        curl = shutil.which("curl")
        if curl is None:
            self.skipTest("curl is not installed")
        receipt, prepared = self.prepare(
            "capability", "main", "read_repo", self.capability, "real-parser")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        headers = Path(f"{receipt}.d") / "response.headers"
        with receipt.open("r", encoding="utf-8") as config_input:
            parsed = subprocess.run(
                [curl, "--disable", "--config", "-", "--version"],
                stdin=config_input,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn("curl ", parsed.stdout)
        self.assertEqual(headers.read_bytes(), b"", "parser check made a request")

    def test_disable_is_first_and_blocks_user_curlrc_without_network(self):
        curl = shutil.which("curl")
        if curl is None:
            self.skipTest("curl is not installed")
        home = self.root / "curl-home"
        home.mkdir()
        marker = self.root / "default-config-output"
        source = self.root / "local-source"
        source.write_text("local-only", encoding="utf-8")
        (home / ".curlrc").write_text(
            f'output = "{marker}"\n', encoding="utf-8")
        env = os.environ.copy()
        env["HOME"] = str(home)
        parsed = subprocess.run(
            [curl, "--disable", "--config", "-"],
            input=f'url = "{source.as_uri()}"\nproto = "=file"\n',
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(parsed.stdout, "local-only")
        self.assertFalse(marker.exists(), ".curlrc influenced the request")

    def test_current_boot_packets_preserve_exact_direct_curl_transition(self):
        for relative in (
            "live/CONTROL_QUICKBOOT.md",
            "live/WORKER_BOOT_PACKET.md",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("live/tools/ontinuity_https.sh", source, relative)
            self.assertIn("curl --disable --config - <", source, relative)
            self.assertNotRegex(source, re.compile(r"\bcurl\s+-X"), relative)
            self.assertNotRegex(
                source,
                re.compile(r"\b(?:urllib|requests|httpx)\b", re.IGNORECASE),
                relative,
            )

    def test_b1_verifier_preflights_project_runtime_before_suites(self):
        source = VERIFY_B1.read_text(encoding="utf-8")
        dependency_probe = source.index(
            "import flask, flask_socketio, requests")
        first_suite = source.index("-m unittest")
        self.assertLess(dependency_probe, first_suite)
        self.assertIn("B1_TEST_PYTHON", source)
        self.assertIn("B1_VERIFY_REFUSED", source)
        self.assertIn("export PYTHONDONTWRITEBYTECODE=1", source)
        self.assertNotIn("-m py_compile", source)
        self.assertIn('compile(path.read_bytes(), str(path), "exec")', source)

    def test_transport_overlay_manifest_covers_exact_delta(self):
        manifest_path = ROOT / "live" / "B1_TRANSPORT_LOCK_MANIFEST.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        base = data["base_commit"]
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, "HEAD"],
            cwd=ROOT,
            check=True,
        )
        expected = {row["path"] for row in data["required"]}
        for row in data["required"]:
            digest = hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, row["sha256"], row["path"])
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", base], cwd=ROOT, text=True
        ).splitlines())
        changed.update(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        ).splitlines())
        relevant = {
            path for path in changed
            if "__pycache__" not in Path(path).parts
            and not path.endswith(".pyc")
            and path != "live/B1_TRANSPORT_LOCK_MANIFEST.json"
        }
        self.assertEqual(relevant, expected)


if __name__ == "__main__":
    unittest.main()
