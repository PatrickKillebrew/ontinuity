import hashlib
import json
import os
import tempfile
import unittest
import uuid


DEPLOY_SCOPE = {
    "signoff_block_id": "block-1",
    "commit_sha": "a" * 40,
    "target_scope": "both",
}


class CapabilityAdmissionSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DIAG_KEY"] = "operator-root-for-tests"
        os.environ["MAILBOX_KEY"] = "mailbox-root-for-tests"
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["ONTINUITY_CAPABILITY_REGISTRY"] = os.path.join(
            cls.tmp.name, "capabilities.json")
        import app
        app._capability_authority = None
        app.app.config["TESTING"] = True
        cls.module = app
        cls.client = app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def admission_post(self, body):
        raw_body = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request_id = uuid.uuid4().hex
        canonical = "\n".join((
            "client_version=2",
            "mode=admission",
            "operation=admission_request",
            f"request_id={request_id}",
            f"body_sha256={hashlib.sha256(raw_body).hexdigest()}",
            "credential_sha256=-",
            "",
        )).encode("utf-8")
        return self.client.post(
            "/diag/admission/request",
            headers={
                "Content-Type": "application/json",
                "X-Ontinuity-Client-Version": "2",
                "X-Ontinuity-Request-ID": request_id,
                "X-Ontinuity-Request-SHA256": hashlib.sha256(
                    canonical).hexdigest(),
            },
            data=raw_body,
        )

    def test_public_request_cannot_ask_for_high_impact_operation(self):
        response = self.admission_post({
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["read_repo", "deploy"], "ttl_seconds": 300,
        })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("deploy", response.get_json()["allowed"])
        self.assertRegex(response.headers["X-Ontinuity-Request-ID"],
                         r"^[0-9a-f]{32}$")

    def test_deploy_only_request_is_pending_elevated_and_ttl_bounded(self):
        accepted = self.admission_post({
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["deploy"], "ttl_seconds": 300,
            "deploy_scope": DEPLOY_SCOPE,
        })
        self.assertEqual(accepted.status_code, 202)
        row = accepted.get_json()
        self.assertEqual(row["ops"], ["deploy"])
        self.assertEqual(row["status"], "pending")
        self.assertTrue(row["elevated"])
        self.assertEqual(row["risk_tier"], "high-impact")
        for ttl in (301, 3600, True, 300.9, "300"):
            with self.subTest(ttl=ttl):
                denied = self.admission_post({
                    "seat": "worker1", "lineage": "openai:test",
                    "operations": ["deploy"], "ttl_seconds": ttl,
                    "deploy_scope": DEPLOY_SCOPE,
                })
                self.assertEqual(denied.status_code, 400)

    def test_elevated_approval_requires_explicit_operator_confirmation(self):
        requested = self.admission_post({
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["deploy"], "ttl_seconds": 300,
            "deploy_scope": DEPLOY_SCOPE,
        }).get_json()
        headers = {"X-Diag-Key": "operator-root-for-tests"}
        denied = self.client.post(
            "/diag/admission/approve", headers=headers,
            json={"request_id": requested["request_id"]})
        self.assertEqual(denied.status_code, 400)
        approved = self.client.post(
            "/diag/admission/approve", headers=headers,
            json={"request_id": requested["request_id"],
                  "elevated_confirmed": True})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.get_json()["identity"]["ops"], ["deploy"])
        self.assertEqual(
            approved.get_json()["identity"]["deploy_scope"], DEPLOY_SCOPE)

    def test_deploy_admission_requires_one_exact_immutable_scope(self):
        base = {
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["deploy"], "ttl_seconds": 300,
        }
        cases = (
            base,
            {**base, "deploy_scope": {**DEPLOY_SCOPE, "extra": "yes"}},
            {**base, "deploy_scope": {**DEPLOY_SCOPE, "target_scope": "other"}},
            {**base, "deploy_scope": DEPLOY_SCOPE, "provider": "railway"},
        )
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self.admission_post(body).status_code, 400)

    def test_other_noninitial_operations_remain_rejected(self):
        for operation in ("restart_workspace", "write_file", "commit_self"):
            with self.subTest(operation=operation):
                response = self.admission_post({
                    "seat": "worker1", "lineage": "openai:test",
                    "operations": [operation], "ttl_seconds": 300,
                })
                self.assertEqual(response.status_code, 403)

    def test_admission_routes_reject_malformed_json_shapes(self):
        self.assertEqual(self.admission_post({
            "seat": "worker1", "lineage": "openai:test",
            "operations": [{"name": "read_repo"}],
        }).status_code, 400)
        headers = {"X-Diag-Key": "operator-root-for-tests"}
        self.assertEqual(self.client.post(
            "/diag/admission/approve", headers=headers, json=["bad"]
        ).status_code, 400)
        self.assertEqual(self.client.post(
            "/diag/admission/revoke", headers=headers, json=["bad"]
        ).status_code, 400)

    def test_operator_can_list_approve_and_revoke_without_url_auth(self):
        requested = self.admission_post({
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["read_repo"], "ttl_seconds": 300,
        })
        request_id = requested.get_json()["request_id"]

        self.assertEqual(
            self.client.get("/diag/admission/requests").status_code, 401)
        self.assertEqual(self.client.get(
            "/diag/admission/requests?diag_key=operator-root-for-tests"
        ).status_code, 401)

        headers = {"X-Diag-Key": "operator-root-for-tests"}
        listed = self.client.get("/diag/admission/requests", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertIn(request_id,
                      {row["request_id"] for row in listed.get_json()["requests"]})

        approved = self.client.post(
            "/diag/admission/approve", headers=headers,
            json={"request_id": request_id})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.headers.get("Cache-Control"), "no-store")
        grant = approved.get_json()
        self.assertTrue(grant["capability"])

        listed = self.client.get(
            "/diag/admission/requests", headers=headers).get_json()["requests"]
        row = next(row for row in listed if row["request_id"] == request_id)
        self.assertNotIn("capability", row)
        self.assertEqual(row["status"], "approved")

        revoked = self.client.post(
            "/diag/admission/revoke", headers=headers, json={"jti": row["jti"]})
        self.assertEqual(revoked.status_code, 200)
        listed = self.client.get(
            "/diag/admission/requests", headers=headers).get_json()["requests"]
        row = next(row for row in listed if row["request_id"] == request_id)
        self.assertEqual(row["status"], "revoked")

    def test_public_request_without_compiled_envelope_is_refused(self):
        response = self.client.post("/diag/admission/request", json={
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["read_repo"], "ttl_seconds": 300,
        })
        self.assertEqual(response.status_code, 428)
        self.assertIn("ontinuity_https.sh", response.get_json()["error"])

    def test_diagnostic_root_in_query_string_is_rejected(self):
        response = self.client.get(
            "/diag/engine?diag_key=operator-root-for-tests")
        self.assertEqual(response.status_code, 401)

    def test_mailbox_root_in_query_string_is_rejected(self):
        rejected = self.client.get(
            "/mailbox/turn?mailbox_key=mailbox-root-for-tests")
        self.assertEqual(rejected.status_code, 403)
        body_rejected = self.client.get(
            "/mailbox/turn", json={"mailbox_key": "mailbox-root-for-tests"})
        self.assertEqual(body_rejected.status_code, 403)
        admitted = self.client.get(
            "/mailbox/turn", headers={"X-Mailbox-Key": "mailbox-root-for-tests"})
        self.assertEqual(admitted.status_code, 200)


if __name__ == "__main__":
    unittest.main()
