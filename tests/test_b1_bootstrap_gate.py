import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock


def _load_gate():
    path = os.path.join(
        os.path.dirname(__file__), "..", "live", "bootstrap", "gate.py")
    spec = importlib.util.spec_from_file_location("b1_bootstrap_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class B1BootstrapGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = _load_gate()

    def test_redirect_handler_refuses_every_redirect(self):
        handler = self.gate._NoRedirect()
        self.assertIsNone(handler.redirect_request(
            None, None, 302, "moved", {}, "https://elsewhere.invalid"))

    def test_corpus_and_engine_keep_root_in_headers(self):
        with mock.patch.object(
                self.gate, "_get", return_value=(200, '{"rows":[[999]]}')) as get:
            result = self.gate.check_corpus("server-root", engine="https://main.test")
        self.assertTrue(result["pass"])
        self.assertNotIn("server-root", get.call_args.args[0])
        self.assertNotIn("diag_key", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["headers"],
                         {"X-Diag-Key": "server-root"})

        with mock.patch.object(
                self.gate, "_get",
                side_effect=[(200, '{"running":false}'),
                             (200, '{"running":true}')]) as get:
            result = self.gate.check_engine("server-root")
        self.assertTrue(result["pass"])
        for call in get.call_args_list:
            self.assertNotIn("server-root", call.args[0])
            self.assertEqual(call.kwargs["headers"],
                             {"X-Diag-Key": "server-root"})

    def test_engine_rejects_nonboolean_or_non_200_state(self):
        for status, body in ((401, '{}'), (200, '{}'),
                             (200, '{"running":0}')):
            with self.subTest(status=status, body=body), mock.patch.object(
                    self.gate, "_get", return_value=(status, body)):
                self.assertFalse(self.gate.check_engine("server-root")["pass"])

    def test_capability_arrival_is_hands_proof(self):
        identity = {"authenticated": True, "seat": "worker1",
                    "lineage": "openai:test", "capability_id": "grant"}
        with mock.patch.object(self.gate, "_post") as post:
            result = self.gate.check_hands(
                "server-root", "worker1", relay_identity=identity)
        self.assertTrue(result["pass"])
        post.assert_not_called()
        mismatch = dict(identity, seat="control")
        self.assertFalse(self.gate.check_hands(
            "server-root", "worker1", relay_identity=mismatch)["pass"])

    def test_queue_uses_one_bounded_next_from_latest_fold(self):
        queue = """## ACTIVE
1. stale head

## FOLD — old
**NEXT**
- old action

## FOLD — current
**NEXT**
- current B1 action with
  one continued condition
"""
        with mock.patch.object(self.gate, "_get", return_value=(200, queue)):
            result = self.gate.check_queue()
        self.assertTrue(result["pass"])
        self.assertIn("current B1 action with one continued condition",
                      result["returned_fact"])
        self.assertNotIn("stale head", result["returned_fact"])

    def test_queue_rejects_ambiguous_latest_next(self):
        queues = (
            "## FOLD — current\n**NEXT**\n- first\n- second\n",
            "## FOLD — current\n**NEXT**\n",
            "## FOLD — current\n**NEXT**\n- action\nunbound\n",
        )
        for queue in queues:
            with self.subTest(queue=queue), mock.patch.object(
                    self.gate, "_get", return_value=(200, queue)):
                self.assertFalse(self.gate.check_queue()["pass"])

    def test_manual_count_is_checked_against_engine_derived_value(self):
        manual = "Allowlist (live, 19 ops): bounded."
        self.gate.CANONICAL_COURIER_OP_COUNT = 19
        with mock.patch.object(self.gate, "_get", return_value=(200, manual)):
            self.assertTrue(self.gate.check_manual()["pass"])
        self.gate.CANONICAL_COURIER_OP_COUNT = 18
        with mock.patch.object(self.gate, "_get", return_value=(200, manual)):
            self.assertFalse(self.gate.check_manual()["pass"])

    def test_committed_recovery_fallback_is_current(self):
        self.assertEqual(self.gate.CANONICAL_COURIER_OP_COUNT, 19)

    def test_current_candidate_corpus_completes_all_six_checks(self):
        root = Path(__file__).resolve().parents[1]
        manual = (root / "live" / "OPERATING_MANUAL.md").read_text(
            encoding="utf-8")
        queue = (root / "live" / "agent_queue.md").read_text(encoding="utf-8")

        def fake_get(url, timeout=30, headers=None):
            if "OPERATING_MANUAL.md" in url:
                return 200, manual
            if "agent_queue.md" in url:
                return 200, queue
            if "/diag/api/query" in url:
                return 200, json.dumps({"rows": [[999]]})
            if "/diag/engine" in url:
                return 200, json.dumps({"running": False})
            raise AssertionError(url)

        identity = {"authenticated": True, "seat": "worker1",
                    "lineage": "openai:test", "capability_id": "grant"}
        invariants = {
            row["key"]: row["canonical_statement"]
            for row in self.gate.MECHANICS_INVARIANTS
        }
        self.gate.CANONICAL_COURIER_OP_COUNT = 19
        with mock.patch.object(self.gate, "_get", side_effect=fake_get), \
                mock.patch.object(self.gate, "_post") as post:
            result = self.gate.run_gate(
                "worker1", "openai:test", role="worker",
                diag_key="server-root", seat_invariants=invariants,
                relay_identity=identity)
        self.assertTrue(result["oriented"], result)
        self.assertEqual(len(result["checks"]), 6)
        mechanics = result["checks"][-1]["returned_fact"]
        self.assertEqual(mechanics["role"], "worker")
        self.assertEqual(len(mechanics["findings"]), 4)
        self.assertEqual(
            {finding["key"] for finding in mechanics["findings"]},
            {row["key"] for row in self.gate.MECHANICS_INVARIANTS},
        )
        for finding in mechanics["findings"]:
            self.assertTrue(finding["reproduced"])
            self.assertGreaterEqual(finding["coverage"], 0.85)
            self.assertTrue(finding["manual_ratified"])
            self.assertTrue(finding["pass"])
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
