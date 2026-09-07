import os
import tempfile
import unittest


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

    def test_public_request_cannot_ask_for_high_impact_operation(self):
        response = self.client.post("/diag/admission/request", json={
            "seat": "worker1", "lineage": "openai:test",
            "operations": ["read_repo", "deploy"], "ttl_seconds": 300,
        })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("deploy", response.get_json()["allowed"])

    def test_admission_routes_reject_malformed_json_shapes(self):
        self.assertEqual(self.client.post(
            "/diag/admission/request",
            json={"seat": "worker1", "lineage": "openai:test",
                  "operations": [{"name": "read_repo"}]},
        ).status_code, 400)
        headers = {"X-Diag-Key": "operator-root-for-tests"}
        self.assertEqual(self.client.post(
            "/diag/admission/approve", headers=headers, json=["bad"]
        ).status_code, 400)
        self.assertEqual(self.client.post(
            "/diag/admission/revoke", headers=headers, json=["bad"]
        ).status_code, 400)

    def test_operator_can_list_approve_and_revoke_without_url_auth(self):
        requested = self.client.post("/diag/admission/request", json={
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
