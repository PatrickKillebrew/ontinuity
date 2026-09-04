import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from flask import Flask

import app as engine
import db as root_db
import workspace_db_endpoint as endpoint


ROOT = Path(__file__).parents[1]


def load_live_db():
    path = ROOT / "live" / "db.py"
    spec = importlib.util.spec_from_file_location("ontinuity_live_db", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


LIVE_DB = load_live_db()


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


class EngineCaptureTests(unittest.TestCase):
    def setUp(self):
        self.runtime = dict(engine.runtime_configs)
        self.session = dict(engine.active_session)
        engine._reset_research_capture()
        engine.active_session["cycle"] = 7
        engine.active_session["errors"] = []

    def tearDown(self):
        engine.runtime_configs.clear()
        engine.runtime_configs.update(self.runtime)
        engine.active_session.clear()
        engine.active_session.update(self.session)

    def test_model_call_envelope_is_exact_and_excludes_credentials_and_url(self):
        api_secret = "api-secret-canary"
        query_secret = "query-secret-canary"
        engine.runtime_configs["model_b"] = {
            "key": api_secret,
            "url": (
                "https://models.example.test/v1/chat/completions?token="
                + query_secret),
            "model": "provider/model-v1",
        }
        system_prompt = "exact system prompt — unicode retained"
        messages = [{"role": "user", "content": "exact message"}]
        response = "exact full response " + ("r" * 900)

        with mock.patch.object(engine, "call_openai_format",
                               return_value=response):
            self.assertEqual(
                engine.call_model("model_b", messages,
                                  system_override=system_prompt),
                response,
            )

        envelope = engine.active_session["model_call_envelopes"][0]
        self.assertEqual(envelope["cycle_number"], 7)
        self.assertEqual(envelope["provider_format"], "openai")
        self.assertEqual(envelope["endpoint_host"], "models.example.test")
        self.assertEqual(envelope["system_prompt"], system_prompt)
        self.assertEqual(envelope["messages"], messages)
        self.assertEqual(envelope["response"], response)
        self.assertEqual(envelope["system_prompt_sha256"], digest(system_prompt))
        self.assertEqual(envelope["messages_sha256"], digest(canonical(messages)))
        self.assertEqual(envelope["response_sha256"], digest(response))
        self.assertEqual(envelope["status"], "succeeded")
        serialized = canonical(envelope)
        self.assertNotIn(api_secret, serialized)
        self.assertNotIn(query_secret, serialized)
        self.assertNotIn("/v1/chat/completions", serialized)

    def test_raising_adapter_terminalizes_envelope_without_exception_text(self):
        engine.runtime_configs["model_b"] = {
            "key": "never-store-this-key",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/model-v1",
        }
        sensitive_exception = "adapter failed Authorization: Bearer secret"
        with mock.patch.object(
                engine, "call_openai_format",
                side_effect=RuntimeError(sensitive_exception)):
            with self.assertRaisesRegex(RuntimeError, "adapter failed"):
                engine.call_model("model_b", [{"role": "user",
                                                "content": "request"}],
                                  system_override="system")
        envelope = engine.active_session["model_call_envelopes"][0]
        self.assertEqual(envelope["status"], "failed_exception")
        self.assertIsNotNone(envelope["ended_at"])
        self.assertIsNone(envelope["response"])
        self.assertNotIn(sensitive_exception, canonical(envelope))

    def test_empty_adapter_response_is_preserved_and_marked_failed(self):
        engine.runtime_configs["model_b"] = {
            "key": "empty-response-test-key",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/model-v1",
        }
        with mock.patch.object(engine, "call_openai_format", return_value=""):
            response = engine.call_model(
                "model_b", [{"role": "user", "content": "request"}],
                system_override="system")
        self.assertEqual(response, "")
        envelope = engine.active_session["model_call_envelopes"][0]
        self.assertEqual(envelope["status"], "failed_empty_response")
        self.assertEqual(envelope["response"], "")
        self.assertEqual(envelope["response_sha256"], digest(""))
        self.assertIsNotNone(envelope["ended_at"])

    def test_snapshot_closes_still_running_call_as_bounded_incomplete(self):
        engine.active_session["model_call_envelopes"] = [{
            "sequence_number": 1,
            "status": "started",
            "ended_at": None,
            "response": None,
        }]
        snapshot = engine._snapshot_model_call_envelopes("session-snapshot")
        self.assertEqual(snapshot[0]["status"], "incomplete_at_snapshot")
        self.assertIsNotNone(snapshot[0]["ended_at"])
        self.assertEqual(snapshot[0]["session_id"], "session-snapshot")
        self.assertEqual(
            engine.active_session["model_call_envelopes"][0]["status"],
            "started",
        )

    def test_cycle_zero_pre_session_mailbox_exchange_is_captured(self):
        engine.active_session["cycle"] = 0
        system = "questions system"
        messages = [{"role": "user", "content": "original objective"}]
        with mock.patch.object(engine, "mailbox_researcher_turn",
                               return_value="normalized answer") as mailbox:
            response = engine.captured_mailbox_researcher_turn(
                system, messages, kind="pre_session_questions")
        self.assertEqual(response, "normalized answer")
        mailbox.assert_called_once_with(
            system, messages, kind="pre_session_questions")
        envelope = engine.active_session["model_call_envelopes"][0]
        self.assertEqual(envelope["cycle_number"], 0)
        self.assertEqual(envelope["provider_format"], "external")
        self.assertEqual(envelope["system_prompt"], system)
        self.assertEqual(envelope["messages"], messages)
        self.assertEqual(envelope["response"], "normalized answer")

    def test_mailbox_outer_whitespace_boundary_is_explicit(self):
        prior = dict(engine.external_mailbox)
        event_was_set = engine.external_mailbox["event"].is_set()
        try:
            engine.external_mailbox["waiting"] = True
            engine.external_mailbox["turn_id"] = 42
            ok, error = engine.mailbox_deliver(
                42, "  \n engine-visible answer \t\n")
            self.assertTrue(ok, error)
            self.assertEqual(engine.external_mailbox["response"],
                             "engine-visible answer")
        finally:
            engine.external_mailbox.update(prior)
            if event_was_set:
                engine.external_mailbox["event"].set()
            else:
                engine.external_mailbox["event"].clear()

    def test_start_token_prevents_interleaved_capture_handoff(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        first = engine._begin_session_start_capture("dashboard")
        self.assertIsNotNone(first)
        engine.active_session["model_call_envelopes"] = [
            {"sequence_number": 1, "response": "first-start"}]
        self.assertIsNone(
            engine._begin_session_start_capture("external-mailbox"))
        self.assertIsNone(engine._claim_session_start_capture("wrong-token"))
        self.assertEqual(
            engine.active_session["_start_context"]["token"], first)
        preserved = engine._claim_session_start_capture(first)
        self.assertEqual(preserved[0]["response"], "first-start")
        self.assertTrue(engine.active_session["running"])
        self.assertIsNone(engine.active_session["_start_context"])

    def test_raised_pre_session_persists_failed_envelope_and_releases_token(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        engine.runtime_configs["parietal"] = {
            "key": "pre-session-test-key",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/parietal",
        }
        token = engine._begin_session_start_capture("external-mailbox")
        session_id_before_call = engine.active_session["start_time"]
        captured = []

        def preserve_payload_once():
            captured.append(engine.build_session_payload())
            return True

        with mock.patch.object(
                engine, "call_openai_format",
                side_effect=RuntimeError("Authorization: Bearer do-not-store")), \
             mock.patch.object(engine, "write_session_to_workspace",
                               side_effect=preserve_payload_once) as writer:
            engine.pre_session_then_start(
                "objective", start_fresh=True, start_token=token)

        writer.assert_called_once_with()
        self.assertIsNone(engine.active_session["_start_context"])
        self.assertFalse(engine.active_session["finalizing"])
        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertEqual(payload["session_id"], session_id_before_call)
        self.assertEqual(payload["status"], "incomplete_pre_session")
        self.assertEqual(payload["total_cycles"], 0)
        self.assertEqual(payload["transcript_turns"], [])
        self.assertEqual(len(payload["model_call_envelopes"]), 1)
        self.assertEqual(payload["model_call_envelopes"][0]["status"],
                         "failed_exception")
        self.assertNotIn("do-not-store", canonical(payload))
        next_token = engine._begin_session_start_capture("dashboard")
        self.assertIsNotNone(next_token)
        self.assertTrue(engine._release_session_start_capture(next_token))

    def test_aborted_start_cannot_inherit_any_prior_payload_field(self):
        old = "OLD_SESSION_MARKER_SHOULD_NOT_SURVIVE"
        engine.active_session.update({
            "running": False,
            "finalizing": False,
            "_start_context": None,
            "start_time": old,
            "end_time": old,
            "objective": old,
            "knowtext_version": old,
            "end_status": old,
            "started_by": old,
            "project_id": old,
            "branch": old,
            "cycle": 99,
            "distillation_method": old,
            "transcript": [{"cycle": 99, "role": "model_a",
                            "content": old}],
            "tag_sequence": [old],
            "signal_sequence": [old],
            "challenge_events": [old],
            "challenge_records": [{"grounds": old}],
            "model_call_envelopes": [{"response": old}],
            "model_call_sequence": 99,
            "expunged_ledger": [{"claim_text": old}],
            "frozen_contract": [{"text": old}],
            "reproducibility_manifest": {"old": old},
            "unreviewed_cycles": [old],
            "errors": [old],
            "artifacts": [{"label": old, "content": old}],
            "session_ledger": [{"cycle": 99, "summary": old}],
            "rejected_claims": [{"claim": old}],
            "results_board": [{"value": old}],
            "execution_log": [{"detail": old}],
            "experiment_sequence": [{"cycle": 99, "computed": old}],
            "modal_touched_cycles": [99],
            "modal_timeouts": [{"context": old}],
            "parietal_navigate_outputs": [old],
            "parietal_adjudicate_rulings": [old],
            "contract": [{"text": old}],
        })
        engine.runtime_configs["parietal"] = {
            "key": "isolation-test-key",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/parietal",
        }
        captured = []
        captured_scope = []
        with mock.patch.object(engine, "WORKSPACE_PROJECT", "CURRENT_PROJECT"), \
             mock.patch.object(engine, "WORKSPACE_BRANCH", "CURRENT_BRANCH"):
            token = engine._begin_session_start_capture("external-mailbox")
            session_id = engine.active_session["start_time"]
            # This is the scope assignment performed by /agent/start after the
            # reservation is made and before PRE_SESSION begins.
            engine.active_session["project_id"] = "CURRENT_PROJECT"
            engine.active_session["branch"] = "CURRENT_BRANCH"

            def preserve_payload_once():
                captured_scope.append((engine.active_session["project_id"],
                                       engine.active_session["branch"]))
                captured.append(engine.build_session_payload())
                return True

            with mock.patch.object(
                    engine, "call_openai_format",
                    side_effect=RuntimeError("forced isolation failure")), \
                 mock.patch.object(engine, "write_session_to_workspace",
                                   side_effect=preserve_payload_once):
                engine.pre_session_then_start(
                    "CURRENT_OBJECTIVE", start_fresh=True,
                    start_token=token)

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertNotIn(old, canonical(payload))
        self.assertEqual(payload["session_id"], session_id)
        self.assertEqual(payload["start_time"], session_id)
        self.assertEqual(payload["objective"], "CURRENT_OBJECTIVE")
        self.assertEqual(payload["project_name"], "CURRENT_PROJECT")
        self.assertEqual(payload["branch_name"], "CURRENT_BRANCH")
        self.assertEqual(payload["status"], "incomplete_pre_session")
        self.assertEqual(payload["total_cycles"], 0)
        self.assertEqual(payload["transcript_turns"], [])
        self.assertEqual(payload["modal_timeouts"], [])
        self.assertIsNone(payload["knowtext_version"])
        self.assertEqual(payload["reproducibility_manifest"]["started_by"],
                         "external-mailbox")
        self.assertEqual(captured_scope,
                         [("CURRENT_PROJECT", "CURRENT_BRANCH")])
        self.assertEqual(len(payload["model_call_envelopes"]), 1)
        self.assertEqual(payload["model_call_envelopes"][0]["cycle_number"],
                         0)
        self.assertEqual(payload["model_call_envelopes"][0]["status"],
                         "failed_exception")
        engine.active_session["modal_timeouts"] = [{"context": old}]
        engine.active_session["knowtext_version"] = old
        with engine._start_context_lock:
            engine._reset_idle_session_state()
        self.assertEqual(engine.active_session["modal_timeouts"], [])
        self.assertIsNone(engine.active_session["knowtext_version"])
        self.assertIsNone(engine.active_session["project_id"])
        self.assertIsNone(engine.active_session["branch"])

    def test_unanswered_external_pre_session_releases_and_preserves_once(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        engine.runtime_configs["parietal"] = {
            "key": "configured",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/parietal",
        }
        token = engine._begin_session_start_capture("external-mailbox")
        captured = []

        def preserve_payload_once():
            captured.append(engine.build_session_payload())
            return True

        with mock.patch.object(engine, "run_pre_session",
                               return_value=("objective", True, [])), \
             mock.patch.object(engine, "mailbox_researcher_turn",
                               return_value=None), \
             mock.patch.object(engine, "write_session_to_workspace",
                               side_effect=preserve_payload_once) as writer:
            engine.pre_session_then_start(
                "objective", start_fresh=True, start_token=token)
            # A stale terminal callback/retry cannot write the attempt again.
            self.assertFalse(engine._abort_pre_session_start(token, "retry"))

        writer.assert_called_once_with()
        self.assertIsNone(engine.active_session["_start_context"])
        self.assertEqual(captured[0]["status"], "incomplete_pre_session")
        self.assertEqual(captured[0]["transcript_turns"], [])
        envelope = captured[0]["model_call_envelopes"][0]
        self.assertEqual(envelope["cycle_number"], 0)
        self.assertEqual(envelope["status"], "failed")
        self.assertIsNone(envelope["response"])

    def test_dashboard_question_wait_retains_then_single_continuation_consumes(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        engine.runtime_configs["parietal"] = {
            "key": "configured",
            "url": "https://models.example.test/v1/chat/completions",
            "model": "provider/parietal",
        }
        token = engine._begin_session_start_capture("dashboard")
        with mock.patch.object(engine, "run_pre_session",
                               return_value=("objective", True, [])), \
             mock.patch.object(engine, "write_session_to_workspace") as writer:
            engine.pre_session_then_start(
                "objective", start_fresh=True, start_token=token)
        writer.assert_not_called()
        context = engine.active_session["_start_context"]
        self.assertEqual(context["token"], token)
        self.assertEqual(context["state"], "awaiting_dashboard_answers")
        continuation = engine._consume_dashboard_start(token)
        self.assertEqual(continuation["objective"], "objective")
        self.assertEqual(
            engine.active_session["_start_context"]["state"], "continuing")
        self.assertIsNone(engine._consume_dashboard_start(token))
        preserved = engine._claim_session_start_capture(token)
        self.assertEqual(preserved, [])
        self.assertIsNone(engine.active_session["_start_context"])
        engine.active_session["running"] = False

    def test_dashboard_question_wait_can_be_cancelled_without_evidence_write(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        token = engine._begin_session_start_capture("dashboard")
        self.assertTrue(engine._mark_dashboard_start_waiting(
            token, "objective", False))
        with mock.patch.object(engine, "write_session_to_workspace") as writer:
            self.assertTrue(engine._release_session_start_capture(token))
        writer.assert_not_called()
        self.assertIsNone(engine.active_session["_start_context"])

    def test_dashboard_cancel_preserves_existing_cycle_zero_evidence_then_resets(self):
        engine.active_session["running"] = False
        engine.active_session["finalizing"] = False
        engine.active_session["_start_context"] = None
        token = engine._begin_session_start_capture("dashboard")
        self.assertTrue(engine._mark_dashboard_start_waiting(
            token, "objective", False))
        engine.active_session["model_call_envelopes"] = [{
            "sequence_number": 1,
            "cycle_number": 0,
            "status": "succeeded",
            "response": "questions",
            "ended_at": "2026-09-04T00:00:01+00:00",
        }]
        captured = []

        def preserve_payload_once():
            captured.append(engine.build_session_payload())
            return True

        with mock.patch.object(engine, "write_session_to_workspace",
                               side_effect=preserve_payload_once) as writer:
            engine._abort_pre_session_start(
                token, "dashboard_cancelled", reset_after=True)
        writer.assert_called_once_with()
        self.assertEqual(captured[0]["status"], "incomplete_pre_session")
        self.assertEqual(captured[0]["transcript_turns"], [])
        self.assertIsNone(engine.active_session["_start_context"])
        self.assertIsNone(engine.active_session["start_time"])
        self.assertEqual(engine.active_session["model_call_envelopes"], [])

    def test_retraction_preserves_exact_removed_ledger_entry(self):
        source = {
            "cycle": 3,
            "summary": ("exact “claim” — with punctuation and enough detail "
                        "to match the challenged response"),
            "provenance": {"kind": "test", "ordinal": 7},
        }
        engine.active_session["session_ledger"] = [source]
        count = engine.expunge_overruled_ledger(source["summary"], 4)
        self.assertEqual(count, 1)
        self.assertEqual(engine.active_session["session_ledger"], [])
        audit = engine.active_session["expunged_ledger"][0]
        self.assertEqual(audit["source_entry"], source)
        self.assertEqual(audit["source_cycle"], 3)
        self.assertEqual(audit["ruling_cycle"], 4)
        self.assertEqual(audit["claim_text"], source["summary"])
        self.assertEqual(audit["disposition"], "EXPUNGED")
        self.assertEqual(Path(engine.__file__).read_text(encoding="utf-8").count(
            "apply_upheld_challenge("), 4)

    def test_payload_carries_full_exact_transcript_alongside_legacy_content(self):
        raw = "  \n“Unicode” — " + ("Ω" * 5200) + "\t\n  "
        engine.active_session["start_time"] = "transcript-payload-session"
        engine.active_session["transcript"] = [{
            "cycle": 1, "role": "model_a", "content": raw}]
        engine.active_session["signal_sequence"] = []
        engine.active_session["tag_sequence"] = []
        engine.active_session["challenge_events"] = []
        engine.active_session["experiment_sequence"] = []
        engine.active_session["modal_touched_cycles"] = []
        payload = engine.build_session_payload()
        turn = payload["transcript_turns"][0]
        self.assertEqual(turn["content"], engine.sanitize_content(raw))
        self.assertEqual(turn["raw_content"], raw)
        self.assertEqual(turn["raw_content_sha256"], digest(raw))

    def test_external_manifest_does_not_promote_configured_label_to_identity(self):
        engine.runtime_configs["model_a"] = {
            "url": "external-mailbox",
            "model": "historical-occupant-label",
        }
        manifest = engine._build_reproducibility_manifest(
            "session-test", [{"id": "C1", "kind": "JUDGED"}])
        self.assertIsNone(manifest["external_occupant_identity"])
        self.assertEqual(
            manifest["external_occupant_status"],
            "UNVERIFIED_PENDING_B1_B2",
        )
        self.assertNotEqual(
            manifest["external_occupant_identity"],
            manifest["role_config"]["model_a"]["model"],
        )

    def test_capture_reset_prevents_cross_session_retraction_inheritance(self):
        engine.active_session["expunged_ledger"] = [{"summary": "old"}]
        engine.active_session["challenge_records"] = [{"grounds": "old"}]
        engine.active_session["model_call_envelopes"] = [{"sequence_number": 9}]
        engine._reset_research_capture()
        self.assertEqual(engine.active_session["expunged_ledger"], [])
        self.assertEqual(engine.active_session["challenge_records"], [])
        self.assertEqual(engine.active_session["model_call_envelopes"], [])
        self.assertEqual(engine.active_session["model_call_sequence"], 0)


class AdditiveMigrationTests(unittest.TestCase):
    def _exercise(self, module):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "existing.db"
            conn = sqlite3.connect(path)
            conn.execute(
                """CREATE TABLE challenge_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    challenged_claim TEXT,
                    grounds TEXT,
                    ruling TEXT NOT NULL,
                    ruling_justification TEXT,
                    ruling_model TEXT,
                    resolution_cycles INTEGER,
                    fork_branch_created TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """INSERT INTO challenge_events (
                    event_id, session_id, user_id, cycle_number,
                    challenged_claim, grounds, ruling, ruling_justification,
                    created_at
                ) VALUES ('old', 's', 'u', 1, 'claim', 'grounds',
                          'UPHOLD', 'original bytes', 'then')"""
            )
            conn.execute(
                """CREATE TABLE session_transcripts (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    turn_number INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tag TEXT,
                    friction_signal INTEGER,
                    word_count INTEGER,
                    token_estimate INTEGER,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """INSERT INTO session_transcripts (
                    turn_id, session_id, cycle_number, turn_number, role,
                    content, created_at
                ) VALUES ('old-turn', 's', 1, 1, 'model_a',
                          'legacy content', 'then')"""
            )
            conn.commit()
            conn.close()

            database = module.OntinuityDB(str(path))
            database.init()
            database.init()  # idempotency proof
            columns = {
                row["name"] for row in database.connect().execute(
                    "PRAGMA table_info(challenge_events)").fetchall()
            }
            self.assertTrue({
                "sequence_number", "adjudication_channel", "raw_event",
                "capture_version",
            }.issubset(columns))
            row = database.connect().execute(
                "SELECT * FROM challenge_events WHERE event_id='old'"
            ).fetchone()
            self.assertEqual(row["ruling_justification"], "original bytes")
            self.assertIsNone(row["adjudication_channel"])
            transcript_columns = {
                row["name"] for row in database.connect().execute(
                    "PRAGMA table_info(session_transcripts)").fetchall()
            }
            self.assertTrue({"raw_content", "raw_content_sha256"}.issubset(
                transcript_columns))
            old_turn = database.connect().execute(
                "SELECT * FROM session_transcripts WHERE turn_id='old-turn'"
            ).fetchone()
            self.assertEqual(old_turn["content"], "legacy content")
            self.assertIsNone(old_turn["raw_content"])
            self.assertIsNone(old_turn["raw_content_sha256"])
            tables = {
                row[0] for row in database.connect().execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertTrue({
                "model_call_envelopes",
                "session_reproducibility_manifests",
                "retraction_events",
            }.issubset(tables))
            database.close()

    def test_root_database_migrates_existing_schema_without_rewriting_rows(self):
        self._exercise(root_db)

    def test_live_database_migrates_existing_schema_without_rewriting_rows(self):
        self._exercise(LIVE_DB)


class EndpointPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        endpoint._db = root_db.OntinuityDB(
            str(Path(self.tmp.name) / "endpoint.db"))
        endpoint._db.init()
        endpoint.WORKSPACE_TOKEN = ""
        flask_app = Flask(__name__)
        flask_app.register_blueprint(endpoint.db_blueprint)
        self.client = flask_app.test_client()

    def tearDown(self):
        endpoint._db.close()
        endpoint._db = None
        self.tmp.cleanup()

    def _base_payload(self, session_id):
        return {
            "session_id": session_id,
            "project_name": "Ontinuity Platform",
            "branch_name": "main",
            "objective": "preserve evidence",
            "status": "complete",
            "models": {},
            "transcript_turns": [],
            "artifacts": [],
            "behavioral_observations": [],
        }

    def test_structured_challenge_manifest_model_call_and_retraction_persist(self):
        claim = "researcher exact “curly” — " + ("c" * 900)
        grounds = "challenger exact ‘grounds’ – " + ("g" * 900)
        justification = "[RULING: UPHOLD] … " + ("j" * 1200)
        raw = "Cycle 4: [RULING: UPHOLD] legacy display"
        messages = [{"role": "user", "content": "full message"}]
        system = "full system"
        response = "full response"
        contract = [{"id": "C1", "kind": "VERIFIABLE", "text": "proof"}]
        prompt_files = [{"path": "prompts/model_a_system.txt",
                         "content": "prompt bytes", "sha256": digest("prompt bytes"),
                         "status": "CAPTURED"}]
        role_config = {"model_a": {"model": "configured-model",
                                    "endpoint_host": None,
                                    "provider_format": "external"}}

        payload = self._base_payload("structured-session")
        payload.update({
            "transcript_turns": [{
                "cycle_number": 4,
                "turn_number": 1,
                "role": "model_a",
                "content": "legacy normalized transcript",
                "raw_content": "legacy normalized transcript",
                "raw_content_sha256": digest("legacy normalized transcript"),
            }],
            "challenge_events": [{
                "sequence_number": 1,
                "cycle_number": 4,
                "challenged_claim": claim,
                "grounds": grounds,
                "ruling": "UPHOLD",
                "ruling_justification": justification,
                "adjudication_channel": "parietal",
                "raw_event": raw,
                "capture_version": engine.RESEARCH_CAPTURE_VERSION,
            }],
            "challenge_events_raw": [raw],
            "model_call_envelopes": [{
                "sequence_number": 1,
                "cycle_number": 4,
                "role": "model_b",
                "model": "configured-model",
                "provider_format": "openai",
                "endpoint_host": "models.example.test",
                "system_prompt": system,
                "system_prompt_sha256": digest(system),
                "messages": messages,
                "messages_sha256": digest(canonical(messages)),
                "response": response,
                "response_sha256": digest(response),
                "status": "succeeded",
                "started_at": "2026-09-04T00:00:00+00:00",
                "ended_at": "2026-09-04T00:00:01+00:00",
                "capture_version": engine.RESEARCH_CAPTURE_VERSION,
            }],
            "reproducibility_manifest": {
                "capture_version": engine.RESEARCH_CAPTURE_VERSION,
                "schema_version": "1.1.0",
                "started_by": "external-mailbox",
                "instance": "main",
                "code_revision": {"status": "UNKNOWN", "value": None,
                                  "source_env": None},
                "frozen_contract": contract,
                "frozen_contract_sha256": digest(canonical(contract)),
                "prompt_files": prompt_files,
                "prompt_files_sha256": digest(canonical(prompt_files)),
                "role_config": role_config,
                "external_occupant_identity": None,
                "external_occupant_status": "UNVERIFIED_PENDING_B1_B2",
            },
            "expunged_ledger": [{
                "source_entry": {
                    "cycle": 3,
                    "summary": "exact “retracted” claim — retained",
                    "provenance": {"source": "session-ledger"},
                },
                "source_cycle": 3,
                "claim_text": "exact “retracted” claim — retained",
                "ruling_cycle": 4,
                "disposition": "EXPUNGED",
            }],
        })

        response_obj = self.client.post("/api/session", json=payload)
        self.assertEqual(response_obj.status_code, 200, response_obj.get_json())
        self.assertEqual(response_obj.get_json()["challenge_records_written"], 1)
        conn = endpoint._db.connect()

        challenges = conn.execute(
            "SELECT * FROM challenge_events WHERE session_id=? "
            "ORDER BY cycle_number", (payload["session_id"],)
        ).fetchall()
        self.assertEqual(len(challenges), 1)
        self.assertEqual(challenges[0]["challenged_claim"], claim)
        self.assertEqual(challenges[0]["grounds"], grounds)
        self.assertEqual(challenges[0]["ruling_justification"], justification)
        self.assertEqual(challenges[0]["adjudication_channel"], "parietal")

        call = conn.execute(
            "SELECT * FROM model_call_envelopes WHERE session_id=?",
            (payload["session_id"],)
        ).fetchone()
        self.assertEqual(call["system_prompt"], system)
        self.assertEqual(call["messages_json"], canonical(messages))
        self.assertEqual(call["response_text"], response)
        self.assertEqual(call["system_prompt_sha256"], digest(system))
        self.assertEqual(call["messages_sha256"], digest(canonical(messages)))
        self.assertEqual(call["response_sha256"], digest(response))

        manifest = conn.execute(
            "SELECT * FROM session_reproducibility_manifests WHERE session_id=?",
            (payload["session_id"],)
        ).fetchone()
        self.assertEqual(manifest["code_revision_status"], "UNKNOWN")
        self.assertIsNone(manifest["external_occupant_identity"])
        self.assertEqual(manifest["external_occupant_status"],
                         "UNVERIFIED_PENDING_B1_B2")
        self.assertEqual(manifest["frozen_contract_json"], canonical(contract))
        self.assertEqual(manifest["frozen_contract_sha256"],
                         digest(canonical(contract)))
        self.assertEqual(manifest["prompt_files_json"], canonical(prompt_files))
        self.assertEqual(manifest["prompt_files_sha256"],
                         digest(canonical(prompt_files)))

        retraction = conn.execute(
            "SELECT * FROM retraction_events WHERE session_id=?",
            (payload["session_id"],)
        ).fetchone()
        self.assertEqual(retraction["claim_text"],
                         "exact “retracted” claim — retained")
        self.assertEqual(retraction["source_cycle"], 3)
        self.assertEqual(retraction["ruling_cycle"], 4)
        self.assertEqual(retraction["disposition"], "EXPUNGED")
        self.assertEqual(
            json.loads(retraction["source_entry_json"]),
            payload["expunged_ledger"][0]["source_entry"],
        )

        replay = self.client.post("/api/session", json=payload)
        self.assertEqual(replay.status_code, 200, replay.get_json())
        self.assertEqual(replay.get_json()["status"], "already_recorded")
        self.assertTrue(replay.get_json()["idempotent_replay"])
        for table in ("session_transcripts", "challenge_events",
                      "model_call_envelopes",
                      "session_reproducibility_manifests",
                      "retraction_events"):
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE session_id=?",
                (payload["session_id"],),
            ).fetchone()[0]
            self.assertEqual(count, 1, table)
        unchanged = conn.execute(
            "SELECT challenged_claim, grounds, ruling_justification "
            "FROM challenge_events WHERE session_id=?",
            (payload["session_id"],),
        ).fetchone()
        self.assertEqual(tuple(unchanged), (claim, grounds, justification))

    def test_failed_ingest_rolls_back_then_clean_retry_succeeds(self):
        payload = self._base_payload("rollback-session")
        payload.update({
            "challenge_events": [{
                "sequence_number": 1,
                "cycle_number": 1,
                "challenged_claim": "claim",
                "grounds": "grounds",
                "ruling": "UPHOLD",
                "adjudication_channel": "parietal",
                "capture_version": engine.RESEARCH_CAPTURE_VERSION,
            }],
            "model_call_envelopes": [{
                "sequence_number": 1,
                "cycle_number": 1,
                "role": "model_b",
                "system_prompt": "system",
                "system_prompt_sha256": digest("system"),
                "messages": [],
                "messages_sha256": digest(canonical([])),
                "status": "failed",
                "started_at": "2026-09-04T00:00:00+00:00",
                "ended_at": "2026-09-04T00:00:01+00:00",
                "capture_version": engine.RESEARCH_CAPTURE_VERSION,
            }],
        })
        with mock.patch.object(endpoint._db, "insert_model_call_envelope",
                               side_effect=RuntimeError("forced failure")):
            failed = self.client.post("/api/session", json=payload)
        self.assertEqual(failed.status_code, 500)
        conn = endpoint._db.connect()
        for table in ("sessions", "challenge_events", "model_call_envelopes"):
            self.assertEqual(conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE session_id=?",
                (payload["session_id"],)).fetchone()[0], 0, table)
        retry = self.client.post("/api/session", json=payload)
        self.assertEqual(retry.status_code, 200, retry.get_json())

    def test_long_unicode_transcript_round_trip_preserves_raw_and_digest(self):
        raw = " \n“Engine-visible” — " + ("Ω" * 5200) + "\t\n "
        payload = self._base_payload("raw-transcript-session")
        payload["transcript_turns"] = [{
            "cycle_number": 1,
            "turn_number": 1,
            "role": "model_a",
            "content": engine.sanitize_content(raw),
            "raw_content": raw,
            "raw_content_sha256": digest(raw),
        }]
        response_obj = self.client.post("/api/session", json=payload)
        self.assertEqual(response_obj.status_code, 200, response_obj.get_json())
        row = endpoint._db.connect().execute(
            "SELECT content, raw_content, raw_content_sha256 "
            "FROM session_transcripts WHERE session_id=?",
            (payload["session_id"],),
        ).fetchone()
        self.assertEqual(row["content"], engine.sanitize_content(raw))
        self.assertEqual(row["raw_content"], raw)
        self.assertEqual(row["raw_content_sha256"], digest(raw))

    def test_legacy_challenge_payload_remains_accepted_and_untruncated(self):
        raw = "Cycle 8: UPHOLD " + ("legacy" * 180)
        payload = self._base_payload("legacy-session")
        payload["challenge_events_raw"] = [raw]
        response_obj = self.client.post("/api/session", json=payload)
        self.assertEqual(response_obj.status_code, 200, response_obj.get_json())
        row = endpoint._db.connect().execute(
            "SELECT * FROM challenge_events WHERE session_id=?",
            (payload["session_id"],)
        ).fetchone()
        self.assertEqual(row["ruling_justification"], raw)
        self.assertEqual(row["raw_event"], raw)
        self.assertEqual(row["capture_version"], "legacy")
        self.assertEqual(row["challenged_claim"], "")
        self.assertEqual(row["grounds"], "")

    def test_root_and_live_endpoint_copies_remain_logically_identical(self):
        self.assertEqual(
            (ROOT / "workspace_db_endpoint.py").read_text(encoding="utf-8"),
            (ROOT / "live" / "workspace_db_endpoint.py").read_text(
                encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
