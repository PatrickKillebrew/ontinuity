import os
import tempfile
import unittest
from unittest import mock


class _Response:
    text = '{"ok":true}'
    status_code = 200
    headers = {"Content-Type": "application/json"}


class CapabilityCourierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DIAG_KEY"] = "server-master-never-given-to-seat"
        # Every relay-capable test mocks requests.post. A loopback discard-port
        # sentinel also makes accidental network escape mechanically harmless.
        os.environ["WORKSPACE_URL"] = "http://127.0.0.1:9"
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["ONTINUITY_CAPABILITY_REGISTRY"] = os.path.join(
            cls.tmp.name, "capabilities.json")
        import app
        app._capability_authority = None
        app.WORKSPACE_URL = os.environ["WORKSPACE_URL"]
        app.app.config["TESTING"] = True
        cls.module = app
        cls.client = app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def issue(self, operations):
        requested = self.client.post("/diag/admission/request", json={
            "seat": "worker1", "lineage": "openai:test",
            "operations": operations, "ttl_seconds": 300})
        self.assertEqual(requested.status_code, 202)
        approved = self.client.post("/diag/admission/approve",
            headers={"X-Diag-Key": os.environ["DIAG_KEY"]},
            json={"request_id": requested.get_json()["request_id"]})
        self.assertEqual(approved.status_code, 200)
        return approved.get_json()

    def test_capability_relay_keeps_master_server_side_and_derives_identity(self):
        grant = self.issue(["mailbox_peek"])
        token = grant["capability"]
        with mock.patch.object(self.module.http_requests, "post", return_value=_Response()) as post:
            response = self.client.post("/diag/op/mailbox_peek",
                headers={"Authorization": "Bearer " + token},
                json={"seat": "forged-control"})
        self.assertEqual(response.status_code, 200)
        forwarded = post.call_args.kwargs
        self.assertEqual(forwarded["headers"]["X-Diag-Key"], os.environ["DIAG_KEY"])
        self.assertEqual(forwarded["headers"]["X-Ontinuity-Seat"], "worker1")
        self.assertEqual(forwarded["headers"]["X-Ontinuity-Lineage"], "openai:test")
        self.assertNotIn(token, repr(forwarded))
        self.assertFalse(forwarded["allow_redirects"])

    def test_excluded_operation_is_denied_before_relay(self):
        token = self.issue(["read_repo"])["capability"]
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.client.post("/diag/op/deploy",
                headers={"Authorization": "Bearer " + token}, json={})
        self.assertEqual(response.status_code, 401)
        post.assert_not_called()

    def test_master_key_in_url_is_not_an_operator_auth_path(self):
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.client.post(
                "/diag/op/read_repo?diag_key=" + os.environ["DIAG_KEY"], json={})
        self.assertEqual(response.status_code, 401)
        post.assert_not_called()

    def test_bootstrap_count_is_derived_by_engine_and_body_value_is_removed(self):
        token = self.issue(["bootstrap_gate"])["capability"]
        with mock.patch.object(
                self.module.http_requests, "post", return_value=_Response()) as post:
            response = self.client.post(
                "/diag/op/bootstrap_gate",
                headers={"Authorization": "Bearer " + token},
                json={"seat": "worker1", "role": "worker",
                      "canonical_op_count": 1})
        self.assertEqual(response.status_code, 200)
        forwarded = post.call_args.kwargs
        self.assertNotIn("canonical_op_count", forwarded["json"])
        self.assertEqual(
            forwarded["headers"]["X-Ontinuity-Courier-Count"],
            str(len(self.module.OP_ALLOWED)))

    def test_you_there_relay_outlives_the_box_long_poll_cap(self):
        token = self.issue(["you_there"])["capability"]
        with mock.patch.object(
                self.module.http_requests, "post", return_value=_Response()) as post:
            response = self.client.post(
                "/diag/op/you_there",
                headers={"Authorization": "Bearer " + token},
                json={"wait_seconds": 90})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_args.kwargs["timeout"], 100)

    def test_non_long_poll_relay_keeps_short_timeout(self):
        token = self.issue(["mailbox_peek"])["capability"]
        with mock.patch.object(
                self.module.http_requests, "post", return_value=_Response()) as post:
            response = self.client.post(
                "/diag/op/mailbox_peek",
                headers={"Authorization": "Bearer " + token}, json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_args.kwargs["timeout"], 25)

    def test_capability_request_body_is_bounded_before_relay(self):
        token = self.issue(["mailbox_send"])["capability"]
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.client.post(
                "/diag/op/mailbox_send",
                headers={"Authorization": "Bearer " + token,
                         "Content-Type": "application/json"},
                data=b" " * 70000)
        self.assertEqual(response.status_code, 413)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
