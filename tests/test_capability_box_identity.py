import importlib.util
import os
import sys
import tempfile
import types
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from flask import Flask


class CapabilityBoxIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["ONTINUITY_DB_PATH"] = os.path.join(cls.tmp.name, "mailbox.db")
        fake_file_server = types.ModuleType("file_server")
        fake_file_server.load_config = lambda: {"diag_key": "box-master"}
        fake_file_server._ops_begin = lambda *args, **kwargs: 1
        fake_file_server._ops_finish = lambda *args, **kwargs: None
        sys.modules["file_server"] = fake_file_server
        path = os.path.join(os.path.dirname(__file__), "..", "live", "box", "seat_mailbox.py")
        spec = importlib.util.spec_from_file_location("b1_seat_mailbox", path)
        cls.mailbox = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mailbox)
        box_ops_path = os.path.join(
            os.path.dirname(__file__), "..", "live", "box", "box_ops.py")
        box_ops_spec = importlib.util.spec_from_file_location(
            "b1_box_ops", box_ops_path)
        cls.box_ops = importlib.util.module_from_spec(box_ops_spec)
        box_ops_spec.loader.exec_module(cls.box_ops)
        app = Flask(__name__)
        app.register_blueprint(cls.mailbox.seat_mailbox_bp)
        app.register_blueprint(cls.box_ops.box_ops_bp)
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.headers = {
            "X-Diag-Key": "box-master",
            "X-Ontinuity-Seat": "worker1",
            "X-Ontinuity-Lineage": "openai:test",
            "X-Ontinuity-Capability": "grant-id",
        }

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        conn = self.mailbox._mb_conn()
        conn.execute("DELETE FROM seat_mailbox")
        conn.commit()
        conn.close()

    def send(self, **changes):
        body = {"from_seat": "worker1", "to_seat": "control", "kind": "note",
                "body": "bounded result"}
        body.update(changes)
        return self.client.post("/op/mailbox_send", headers=self.headers, json=body)

    def insert_message(self, *, to_seat="worker1", from_seat="control",
                       kind="note", status="queued", claimed_by=None,
                       lease_until=None):
        msg_id = str(uuid.uuid4())
        conn = self.mailbox._mb_conn()
        conn.execute("""INSERT INTO seat_mailbox
            (msg_id,from_seat,to_seat,kind,body,status,created_at,claimed_by,lease_until)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (msg_id, from_seat, to_seat, kind, "fixture", status,
             datetime.now(timezone.utc).isoformat(), claimed_by, lease_until))
        conn.commit()
        conn.close()
        return msg_id

    def test_altered_sender_is_denied(self):
        response = self.send(from_seat="control")
        self.assertEqual(response.status_code, 409)

    def test_mailbox_send_body_is_bounded(self):
        response = self.send(body="x" * 32769)
        self.assertEqual(response.status_code, 413)

    def test_model_mailbox_routes_reject_nonobject_json(self):
        for route in ("mailbox_send", "mailbox_fetch", "mailbox_ack",
                      "mailbox_peek", "you_there"):
            with self.subTest(route=route):
                response = self.client.post(
                    "/op/" + route, headers=self.headers, json=["bad"])
                self.assertEqual(response.status_code, 400)

    def test_mailbox_peek_rejects_invalid_limit(self):
        response = self.client.post(
            "/op/mailbox_peek", headers=self.headers,
            json={"limit": "not-an-integer"})
        self.assertEqual(response.status_code, 400)

    def test_reviewable_author_impersonation_is_denied(self):
        response = self.send(kind="signoff", author_seat="worker2")
        self.assertEqual(response.status_code, 409)

    def test_nonreviewable_author_impersonation_is_denied(self):
        response = self.send(kind="task", author_seat="worker2")
        self.assertEqual(response.status_code, 409)

    def test_author_lineage_impersonation_is_denied(self):
        response = self.send(author_lineage="forged:lineage")
        self.assertEqual(response.status_code, 409)

    def test_authenticated_sender_and_lineage_are_persisted(self):
        response = self.send(from_lineage="forged:lineage")
        self.assertEqual(response.status_code, 200)
        msg_id = response.get_json()["msg_id"]
        conn = self.mailbox._mb_conn()
        row = conn.execute(
            "SELECT from_seat,from_lineage,author_seat,author_lineage FROM seat_mailbox WHERE msg_id=?",
            (msg_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("worker1", "openai:test", "worker1", "openai:test"))

    def test_peek_defaults_to_authenticated_inbox(self):
        own_id = self.insert_message(to_seat="worker1")
        other_id = self.insert_message(to_seat="worker2")
        response = self.client.post("/op/mailbox_peek", headers=self.headers, json={})
        self.assertEqual(response.status_code, 200)
        ids = {row["msg_id"] for row in response.get_json()["messages"]}
        self.assertIn(own_id, ids)
        self.assertNotIn(other_id, ids)

    def test_cross_seat_peek_is_denied(self):
        response = self.client.post("/op/mailbox_peek", headers=self.headers,
                                    json={"seat": "worker2"})
        self.assertEqual(response.status_code, 403)

    def test_sender_wide_peek_is_denied(self):
        response = self.client.post("/op/mailbox_peek", headers=self.headers,
                                    json={"from_seat": "control"})
        self.assertEqual(response.status_code, 403)

    def test_cross_seat_purge_is_denied(self):
        response = self.client.post("/op/mailbox_purge", headers=self.headers,
                                    json={"seat": "worker2"})
        self.assertEqual(response.status_code, 403)

    def test_authenticated_purge_all_is_denied(self):
        response = self.client.post("/op/mailbox_purge", headers=self.headers,
                                    json={"seat": "worker1", "all": True})
        self.assertEqual(response.status_code, 403)

    def test_legitimate_own_purge_remains_available(self):
        own_id = self.insert_message(to_seat="worker1")
        response = self.client.post("/op/mailbox_purge", headers=self.headers,
                                    json={"seat": "worker1", "kinds": ["note"]})
        self.assertEqual(response.status_code, 200)
        conn = self.mailbox._mb_conn()
        self.assertIsNone(conn.execute("SELECT msg_id FROM seat_mailbox WHERE msg_id=?",
                                       (own_id,)).fetchone())
        conn.close()

    def test_authenticated_reclaim_all_is_denied(self):
        response = self.client.post("/op/mailbox_reclaim", headers=self.headers,
                                    json={"seat": "worker1", "all": True})
        self.assertEqual(response.status_code, 403)

    def test_cross_seat_reclaim_is_denied(self):
        response = self.client.post("/op/mailbox_reclaim", headers=self.headers,
                                    json={"seat": "worker2"})
        self.assertEqual(response.status_code, 403)

    def test_legitimate_own_expired_reclaim_remains_available(self):
        expired = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        msg_id = self.insert_message(to_seat="worker1", status="claimed",
                                     claimed_by="worker1", lease_until=expired)
        response = self.client.post("/op/mailbox_reclaim", headers=self.headers,
                                    json={"seat": "worker1"})
        self.assertEqual(response.status_code, 200)
        conn = self.mailbox._mb_conn()
        row = conn.execute("SELECT status,claimed_by FROM seat_mailbox WHERE msg_id=?",
                           (msg_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("queued", None))

    def test_ack_reply_uses_authenticated_sender_and_lineage(self):
        msg_id = self.insert_message(to_seat="any_worker", status="claimed",
                                     claimed_by="worker1")
        response = self.client.post("/op/mailbox_ack", headers=self.headers, json={
            "msg_id": msg_id, "seat": "worker1", "from_lineage": "forged:lineage",
            "reply": "done", "ref": "commit:test"})
        self.assertEqual(response.status_code, 200)
        reply_id = response.get_json()["reply_id"]
        conn = self.mailbox._mb_conn()
        row = conn.execute("SELECT from_seat,from_lineage,to_seat FROM seat_mailbox WHERE msg_id=?",
                           (reply_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("worker1", "openai:test", "control"))

    def test_ack_reply_persists_authenticated_authorship(self):
        msg_id = self.insert_message(to_seat="worker1", status="claimed",
                                     claimed_by="worker1")
        response = self.client.post("/op/mailbox_ack", headers=self.headers, json={
            "msg_id": msg_id, "reply": "done"})
        self.assertEqual(response.status_code, 200)
        reply_id = response.get_json()["reply_id"]
        conn = self.mailbox._mb_conn()
        row = conn.execute(
            "SELECT author_seat,author_lineage FROM seat_mailbox WHERE msg_id=?",
            (reply_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("worker1", "openai:test"))

    def test_oversized_ack_reply_does_not_mark_message_done(self):
        msg_id = self.insert_message(to_seat="worker1", status="claimed",
                                     claimed_by="worker1")
        response = self.client.post("/op/mailbox_ack", headers=self.headers, json={
            "msg_id": msg_id, "reply": "x" * 32769})
        self.assertEqual(response.status_code, 413)
        conn = self.mailbox._mb_conn()
        row = conn.execute(
            "SELECT status,done_at FROM seat_mailbox WHERE msg_id=?", (msg_id,)
        ).fetchone()
        reply_count = conn.execute(
            "SELECT COUNT(*) FROM seat_mailbox WHERE reply_to=?", (msg_id,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(row, ("claimed", None))
        self.assertEqual(reply_count, 0)

    def test_fetch_rejects_authenticated_role_escalation(self):
        control_id = self.insert_message(to_seat="control", kind="task")
        response = self.client.post("/op/mailbox_fetch", headers=self.headers,
                                    json={"seat": "worker1", "roles": ["control"],
                                          "kinds": ["task"]})
        self.assertEqual(response.status_code, 403)
        conn = self.mailbox._mb_conn()
        row = conn.execute("SELECT status,claimed_by FROM seat_mailbox WHERE msg_id=?",
                           (control_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("queued", None))

    def test_you_there_rejects_authenticated_role_escalation(self):
        control_id = self.insert_message(to_seat="control", kind="task")
        response = self.client.post("/op/you_there", headers=self.headers,
                                    json={"seat": "worker1", "roles": ["control"],
                                          "kinds": ["task"], "wait_seconds": 0})
        self.assertEqual(response.status_code, 403)
        conn = self.mailbox._mb_conn()
        row = conn.execute("SELECT status,claimed_by FROM seat_mailbox WHERE msg_id=?",
                           (control_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("queued", None))

    def test_authenticated_worker_can_claim_any_worker_role(self):
        task_id = self.insert_message(to_seat="any_worker", kind="task")
        response = self.client.post("/op/mailbox_fetch", headers=self.headers,
                                    json={"seat": "worker1", "roles": ["any_worker"],
                                          "kinds": ["task"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"]["msg_id"], task_id)

    def test_distinct_seat_can_claim_reviewable_item_from_same_lineage(self):
        response = self.client.post("/op/mailbox_send", headers={
            **self.headers,
            "X-Ontinuity-Seat": "worker2",
        }, json={
            "from_seat": "worker2", "to_seat": "any_worker",
            "kind": "proposal", "body": "review me",
        })
        self.assertEqual(response.status_code, 200)
        proposal_id = response.get_json()["msg_id"]
        claimed = self.client.post(
            "/op/mailbox_fetch", headers=self.headers,
            json={"roles": ["any_worker"], "kinds": ["proposal"]})
        self.assertEqual(claimed.status_code, 200)
        self.assertEqual(claimed.get_json()["message"]["msg_id"], proposal_id)

    def test_authenticated_ack_rejects_unclaimed_message(self):
        msg_id = self.insert_message(to_seat="worker1", kind="task")
        response = self.client.post("/op/mailbox_ack", headers=self.headers,
                                    json={"msg_id": msg_id, "seat": "worker1"})
        self.assertEqual(response.status_code, 403)
        conn = self.mailbox._mb_conn()
        row = conn.execute("SELECT status,claimed_by FROM seat_mailbox WHERE msg_id=?",
                           (msg_id,)).fetchone()
        conn.close()
        self.assertEqual(row, ("queued", None))

    def test_bootstrap_rejects_authenticated_body_identity_substitution(self):
        response = self.client.post(
            "/op/bootstrap_gate", headers=self.headers,
            json={"seat": "control", "lineage": "forged:lineage",
                  "role": "worker"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("identity mismatch", response.get_json()["error"])

    def test_bootstrap_uses_server_header_not_body_for_canonical_count(self):
        gate = types.SimpleNamespace(CANONICAL_COURIER_OP_COUNT=None)
        gate.run_gate = mock.Mock(return_value={
            "oriented": False,
            "checks": [{"name": "MANUAL", "pass": False}],
        })
        headers = dict(self.headers)
        headers["X-Ontinuity-Courier-Count"] = "19"
        with mock.patch.object(self.box_ops, "_load_gate", return_value=gate):
            response = self.client.post(
                "/op/bootstrap_gate", headers=headers,
                json={"seat": "worker1", "lineage": "openai:test",
                      "role": "worker", "canonical_op_count": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(gate.CANONICAL_COURIER_OP_COUNT, 19)
        gate.run_gate.assert_called_once()

    def test_capability_read_repo_cannot_expand_repo_or_add_token(self):
        other_repo = self.client.post(
            "/op/read_repo", headers=self.headers,
            json={"path": "README.md", "repo": "someone/else"})
        self.assertEqual(other_repo.status_code, 403)
        with_token = self.client.post(
            "/op/read_repo", headers=self.headers,
            json={"path": "README.md", "github_token": "caller-secret"})
        self.assertEqual(with_token.status_code, 403)

    def test_capability_read_repo_rejects_unsafe_paths_and_refs(self):
        for body in (
                {"path": "../private"},
                {"path": "live/../private"},
                {"path": "/absolute"},
                {"path": "live//manual.md"},
                {"path": "live\\manual.md"},
                {"path": "live/manual.md", "ref": "../../other"},
                {"path": "live/manual.md", "ref": "main?redirect=x"},
                {"path": "README.md", "repo": "../name"}):
            with self.subTest(body=body):
                response = self.client.post(
                    "/op/read_repo", headers=self.headers, json=body)
                self.assertEqual(response.status_code, 400)

    def test_capability_read_repo_encodes_path_and_never_requests_token(self):
        upstream = mock.MagicMock()
        upstream.__enter__.return_value = upstream
        upstream.read.return_value = b"bounded public content"
        with mock.patch.object(
                self.box_ops._NO_REDIRECT_OPENER, "open",
                return_value=upstream) as opened:
            response = self.client.post(
                "/op/read_repo", headers=self.headers,
                json={"path": "live/a file.md", "ref": "main"})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertNotIn("pass github_token", result["note"])
        self.assertIn("operator-recovery-only", result["note"])
        request_url = opened.call_args.args[0].full_url
        self.assertIn("/PatrickKillebrew/ontinuity/main/live/a%20file.md", request_url)


if __name__ == "__main__":
    unittest.main()
