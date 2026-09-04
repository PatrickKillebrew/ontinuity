import unittest
from unittest.mock import patch

import app


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class ProviderAdapterMuseum(unittest.TestCase):
    def setUp(self):
        app.active_session["errors"] = []
        app.active_session["last_model_failure"] = {}

    def assert_malformed(self, role):
        self.assertEqual(
            app.active_session["last_model_failure"][role]["kind"],
            "malformed_response",
        )

    @patch.object(app, "get_api_key", return_value="test-key")
    @patch.object(app.http_requests, "post")
    def test_anthropic_empty_content_array_is_malformed(self, post, _key):
        post.return_value = FakeResponse({"content": []})

        result = app.call_anthropic_format(
            {"url": "https://provider.invalid", "model": "test"},
            "system",
            [{"role": "user", "content": "question"}],
            "model_a",
        )

        self.assertIsNone(result)
        self.assert_malformed("model_a")

    @patch.object(app, "get_api_key", return_value="test-key")
    @patch.object(app.http_requests, "post")
    def test_gemini_empty_candidates_array_is_malformed(self, post, _key):
        post.return_value = FakeResponse({"candidates": []})

        result = app.call_gemini_native(
            {"model": "test"},
            "system",
            [{"role": "user", "content": "question"}],
            "model_a",
        )

        self.assertIsNone(result)
        self.assert_malformed("model_a")

    @patch.object(app, "get_api_key", return_value="test-key")
    @patch.object(app.http_requests, "post")
    def test_gemini_empty_parts_array_is_malformed(self, post, _key):
        post.return_value = FakeResponse({
            "candidates": [{"content": {"parts": []}}]
        })

        result = app.call_gemini_native(
            {"model": "test"},
            "system",
            [{"role": "user", "content": "question"}],
            "model_a",
        )

        self.assertIsNone(result)
        self.assert_malformed("model_a")


if __name__ == "__main__":
    unittest.main()
