import hashlib
import json
import os
import tempfile
import unittest
import uuid
from unittest import mock


class _Response:
    def __init__(self, body=b'{"ok":true}', *, status_code=200,
                 content_type="application/json"):
        self.body = body
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.encoding = "utf-8"
        self.closed = False

    def iter_content(self, chunk_size=1):
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset:offset + chunk_size]

    def close(self):
        self.closed = True


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

    @staticmethod
    def compiled_headers(mode, operation, request_id, raw_body, credential=None):
        body_sha256 = hashlib.sha256(raw_body).hexdigest()
        credential_sha256 = "-" if credential is None else hashlib.sha256(
            credential.encode("utf-8")).hexdigest()
        canonical = "\n".join((
            "client_version=2",
            f"mode={mode}",
            f"operation={operation}",
            f"request_id={request_id}",
            f"body_sha256={body_sha256}",
            f"credential_sha256={credential_sha256}",
            "",
        )).encode("utf-8")
        return {
            "X-Ontinuity-Client-Version": "2",
            "X-Ontinuity-Request-ID": request_id,
            "X-Ontinuity-Request-SHA256": hashlib.sha256(canonical).hexdigest(),
        }

    def compiled_post(self, path, *, mode, operation, body, credential=None,
                      request_id=None):
        raw_body = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request_id = request_id or uuid.uuid4().hex
        headers = self.compiled_headers(
            mode, operation, request_id, raw_body, credential)
        if credential is not None:
            headers["Authorization"] = "Bearer " + credential
        headers["Content-Type"] = "application/json"
        return self.client.post(path, headers=headers, data=raw_body)

    def issue(self, operations):
        requested = self.compiled_post(
            "/diag/admission/request", mode="admission",
            operation="admission_request", body={
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
            response = self.compiled_post(
                "/diag/op/mailbox_peek", mode="capability",
                operation="mailbox_peek", credential=token,
                body={"seat": "forged-control"})
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.headers["X-Ontinuity-Request-ID"],
                         r"^[0-9a-f]{32}$")
        forwarded = post.call_args.kwargs
        self.assertEqual(forwarded["headers"]["X-Diag-Key"], os.environ["DIAG_KEY"])
        self.assertEqual(forwarded["headers"]["X-Ontinuity-Seat"], "worker1")
        self.assertEqual(forwarded["headers"]["X-Ontinuity-Lineage"], "openai:test")
        self.assertNotIn(token, repr(forwarded))
        self.assertFalse(forwarded["allow_redirects"])

    def test_excluded_operation_is_denied_before_relay(self):
        token = self.issue(["read_repo"])["capability"]
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.compiled_post(
                "/diag/op/deploy", mode="capability", operation="deploy",
                credential=token, body={})
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
            response = self.compiled_post(
                "/diag/op/bootstrap_gate", mode="capability",
                operation="bootstrap_gate", credential=token,
                body={"seat": "worker1", "role": "worker",
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
            response = self.compiled_post(
                "/diag/op/you_there", mode="capability",
                operation="you_there", credential=token,
                body={"wait_seconds": 90})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_args.kwargs["timeout"], 100)

    def test_non_long_poll_relay_keeps_short_timeout(self):
        token = self.issue(["mailbox_peek"])["capability"]
        with mock.patch.object(
                self.module.http_requests, "post", return_value=_Response()) as post:
            response = self.compiled_post(
                "/diag/op/mailbox_peek", mode="capability",
                operation="mailbox_peek", credential=token, body={})
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

    def test_valid_capability_without_compiled_envelope_is_refused(self):
        token = self.issue(["read_repo"])["capability"]
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.client.post(
                "/diag/op/read_repo",
                headers={"Authorization": "Bearer " + token}, json={})
        self.assertEqual(response.status_code, 428)
        self.assertIn("ontinuity_https.sh", response.get_json()["error"])
        post.assert_not_called()

    def test_probe_without_compiled_envelope_is_refused_before_designed_403(self):
        token = self.issue(["__probe__"])["capability"]
        response = self.client.post(
            "/diag/op/__probe__",
            headers={"Authorization": "Bearer " + token}, json={})
        self.assertEqual(response.status_code, 428)

    def test_compiled_probe_returns_designed_403_and_request_identity(self):
        token = self.issue(["__probe__"])["capability"]
        response = self.compiled_post(
            "/diag/op/__probe__", mode="capability",
            operation="__probe__", credential=token, body={})
        self.assertEqual(response.status_code, 403)
        self.assertRegex(response.headers["X-Ontinuity-Request-ID"],
                         r"^[0-9a-f]{32}$")

    def test_compiled_envelope_is_bound_to_exact_body_and_capability(self):
        token = self.issue(["read_repo"])["capability"]
        raw_body = b'{}'
        request_id = uuid.uuid4().hex
        headers = self.compiled_headers(
            "capability", "read_repo", request_id, raw_body, token)
        headers["Authorization"] = "Bearer " + token
        headers["Content-Type"] = "application/json"
        with mock.patch.object(self.module.http_requests, "post") as post:
            response = self.client.post(
                "/diag/op/read_repo", headers=headers,
                data=b'{"different":true}')
        self.assertEqual(response.status_code, 428)
        post.assert_not_called()

    def test_side_effecting_request_id_replays_once_without_second_relay(self):
        token = self.issue(["mailbox_send"])["capability"]
        request_id = uuid.uuid4().hex
        with mock.patch.object(
                self.module.http_requests, "post", return_value=_Response()) as post:
            first = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
            second = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.headers["X-Ontinuity-Replayed"], "true")
        self.assertEqual(post.call_count, 1)

    def test_ambiguous_side_effecting_outcome_is_not_relayed_again(self):
        token = self.issue(["mailbox_send"])["capability"]
        request_id = uuid.uuid4().hex
        with mock.patch.object(
                self.module.http_requests, "post",
                side_effect=TimeoutError("simulated timeout")) as post:
            first = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
            second = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
        self.assertEqual(first.status_code, 502)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()["state"], "unknown")
        self.assertEqual(post.call_count, 1)

    def test_oversized_chunked_side_effect_response_is_closed_and_not_retried(self):
        token = self.issue(["mailbox_send"])["capability"]
        request_id = uuid.uuid4().hex
        upstream = _Response(
            b"x" * (self.module.MAX_REPLAY_BODY_BYTES + 1),
            content_type="text/plain",
        )
        with mock.patch.object(
                self.module.http_requests, "post", return_value=upstream) as post:
            first = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
            second = self.compiled_post(
                "/diag/op/mailbox_send", mode="capability",
                operation="mailbox_send", credential=token,
                request_id=request_id, body={"to": "control", "body": "hi"})
        self.assertEqual(first.status_code, 502)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()["state"], "unknown")
        self.assertEqual(post.call_count, 1)
        self.assertTrue(upstream.closed)

    def test_oversized_chunked_read_response_is_closed_and_refused(self):
        token = self.issue(["read_repo"])["capability"]
        upstream = _Response(
            b"x" * (self.module.MAX_COURIER_READ_RESPONSE_BYTES + 1),
            content_type="text/plain",
        )
        with mock.patch.object(
                self.module.http_requests, "post", return_value=upstream) as post:
            response = self.compiled_post(
                "/diag/op/read_repo", mode="capability",
                operation="read_repo", credential=token, body={"path": "README.md"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(post.call_count, 1)
        self.assertTrue(upstream.closed)
        self.assertIn("response body is too large", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
