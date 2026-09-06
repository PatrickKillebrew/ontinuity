import os
import tempfile
import unittest

from capability_auth import CapabilityAuthority, CapabilityError


class CapabilityAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.authority = CapabilityAuthority(
            secret="test-master-secret",
            registry_path=os.path.join(self.tmp.name, "capabilities.json"),
            now=lambda: 1_000,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def approve(self, **overrides):
        request = self.authority.request(
            seat=overrides.get("seat", "worker1"),
            lineage=overrides.get("lineage", "openai:test"),
            operations=overrides.get("operations", ["read_repo", "mailbox_fetch"]),
            ttl_seconds=overrides.get("ttl_seconds", 300),
        )
        return self.authority.approve(request["request_id"])["capability"]

    def test_allowed_operation_succeeds_and_identity_is_derived(self):
        token = self.approve()
        identity = self.authority.authorize(token, "read_repo", now=1_001)
        self.assertEqual(identity["seat"], "worker1")
        self.assertEqual(identity["lineage"], "openai:test")
        self.assertNotIn("secret", identity)

    def test_excluded_operation_fails(self):
        token = self.approve()
        with self.assertRaisesRegex(CapabilityError, "operation not allowed"):
            self.authority.authorize(token, "deploy", now=1_001)

    def test_payload_tamper_cannot_change_seat(self):
        token = self.approve()
        header, payload, signature = token.split(".")
        replacement = ("eyJleHAiOjEzMDAsImlhdCI6MTAwMCwianRpIjoieCIsImxpbmVhZ2UiOi"
                       "JvcGVuYWk6dGVzdCIsIm9wcyI6WyJyZWFkX3JlcG8iXSwic2VhdCI6ImNvbnRyb2wifQ")
        with self.assertRaisesRegex(CapabilityError, "invalid signature"):
            self.authority.authorize(".".join((header, replacement, signature)), "read_repo", now=1_001)

    def test_capability_expires(self):
        token = self.approve(ttl_seconds=30)
        with self.assertRaisesRegex(CapabilityError, "expired"):
            self.authority.authorize(token, "read_repo", now=1_031)

    def test_operator_can_revoke(self):
        token = self.approve()
        identity = self.authority.authorize(token, "read_repo", now=1_001)
        self.authority.revoke(identity["jti"])
        with self.assertRaisesRegex(CapabilityError, "revoked"):
            self.authority.authorize(token, "read_repo", now=1_002)

    def test_request_requires_explicit_nonempty_allowlist(self):
        with self.assertRaisesRegex(CapabilityError, "operations"):
            self.approve(operations=[])

    def test_master_secret_is_never_persisted(self):
        token = self.approve()
        with open(self.authority.registry_path, encoding="utf-8") as handle:
            persisted = handle.read()
        self.assertNotIn("test-master-secret", persisted)
        self.assertNotIn(token, persisted)


if __name__ == "__main__":
    unittest.main()
