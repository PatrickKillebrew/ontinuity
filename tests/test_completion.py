import unittest

from completion import classify_completion, model_failure_outcome


class CompletionMuseum(unittest.TestCase):
    def test_certified_close_is_complete(self):
        self.assertEqual(
            classify_completion("complete", [{"tag": "SESSION_END"}]),
            ("complete", "certified_close"),
        )

    def test_requested_complete_without_close_fails_closed(self):
        self.assertEqual(
            classify_completion("complete", [{"tag": "CONTINUE"}]),
            ("incomplete_no_close", "no_certified_close"),
        )

    def test_missing_status_without_close_fails_closed(self):
        self.assertEqual(
            classify_completion(None, []),
            ("incomplete_no_close", "no_certified_close"),
        )

    def test_challenger_death_overrides_later_close(self):
        self.assertEqual(
            classify_completion(
                "complete", [{"tag": "SESSION_END"}], unreviewed_cycles=[2]
            ),
            ("incomplete_challenger_dead", "challenger_provider_dead"),
        )

    def test_no_review_tag_also_blocks_complete(self):
        self.assertEqual(
            classify_completion(
                "complete", [{"tag": "NO_REVIEW"}, {"tag": "SESSION_END"}]
            ),
            ("incomplete_challenger_dead", "challenger_provider_dead"),
        )

    def test_named_terminal_outcomes_preserve_status_and_reason(self):
        cases = {
            "incomplete_model_dead": "researcher_provider_dead",
            "stopped": "operator_stop",
            "incomplete_timeout": "session_timeout",
            "incomplete_malformed_response": "malformed_model_response",
            "incomplete_missing_extraction": "work_product_extraction_failed",
        }
        for status, reason in cases.items():
            with self.subTest(status=status):
                self.assertEqual(classify_completion(status, []), (status, reason))

    def test_specific_reason_is_not_discarded(self):
        self.assertEqual(
            classify_completion("stopped", [], end_reason="operator_stop:mailbox"),
            ("stopped", "operator_stop:mailbox"),
        )

    def test_researcher_timeout_and_malformed_response_are_distinct(self):
        self.assertEqual(
            model_failure_outcome("model_a", "timeout"),
            ("incomplete_timeout", "researcher_timeout"),
        )
        self.assertEqual(
            model_failure_outcome("model_a", "malformed_response"),
            ("incomplete_malformed_response", "researcher_malformed_response"),
        )

    def test_challenger_failure_keeps_integrity_status_and_specific_reason(self):
        self.assertEqual(
            model_failure_outcome("model_b", "timeout"),
            ("incomplete_challenger_dead", "challenger_timeout"),
        )


if __name__ == "__main__":
    unittest.main()
