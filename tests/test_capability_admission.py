import os
import json
import stat
import tempfile
import unittest
from unittest import mock

import capability_auth
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

    def test_seat_identity_rejects_control_characters_and_markup(self):
        for seat in ("worker\n2", "<worker2>"):
            with self.subTest(seat=seat), self.assertRaisesRegex(
                    CapabilityError, "seat"):
                self.authority.request(
                    seat=seat, lineage="openai:test",
                    operations=["read_repo"], ttl_seconds=300)

    def test_signed_payload_with_invalid_claim_types_fails_closed(self):
        token = self.authority._encode({
            "seat": "worker1", "lineage": "openai:test",
            "ops": ["read_repo"], "iat": 1_000,
            "exp": "not-an-integer", "jti": "synthetic",
        })
        with self.assertRaisesRegex(CapabilityError, "lifetime"):
            self.authority.authorize(token, "read_repo", now=1_001)

    def test_master_secret_is_never_persisted(self):
        token = self.approve()
        with open(self.authority.registry_path, encoding="utf-8") as handle:
            persisted = handle.read()
        self.assertNotIn("test-master-secret", persisted)
        self.assertNotIn(token, persisted)
        self.assertEqual(stat.S_IMODE(os.stat(self.authority.registry_path).st_mode),
                         0o600)

    def test_corrupt_registry_fails_closed_without_overwrite(self):
        with open(self.authority.registry_path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")
        with self.assertRaisesRegex(CapabilityError, "registry is unreadable"):
            self.authority.request(
                seat="worker1", lineage="openai:test",
                operations=["read_repo"], ttl_seconds=300)
        with open(self.authority.registry_path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{not-json")

    def test_registry_binds_the_approved_operation_set(self):
        token = self.approve(operations=["read_repo"])
        with open(self.authority.registry_path, encoding="utf-8") as handle:
            data = json.load(handle)
        jti = next(iter(data["issued"]))
        data["issued"][jti]["ops"] = ["deploy"]
        with open(self.authority.registry_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        with self.assertRaisesRegex(CapabilityError, "identity mismatch"):
            self.authority.authorize(token, "read_repo", now=1_001)

    def test_expired_pending_request_cannot_be_approved(self):
        clock = [1_000]
        authority = CapabilityAuthority(
            secret="test-master-secret",
            registry_path=os.path.join(self.tmp.name, "expiring.json"),
            now=lambda: clock[0],
        )
        request = authority.request(
            seat="worker1", lineage="openai:test",
            operations=["read_repo"], ttl_seconds=300)
        clock[0] += capability_auth.PENDING_REQUEST_TTL_SECONDS
        with self.assertRaisesRegex(CapabilityError, "pending"):
            authority.approve(request["request_id"])

    def test_pending_queue_is_bounded(self):
        with mock.patch.object(capability_auth, "MAX_PENDING_REQUESTS", 2):
            for seat in ("worker1", "worker2"):
                self.authority.request(
                    seat=seat, lineage="openai:test",
                    operations=["read_repo"], ttl_seconds=300)
            with self.assertRaisesRegex(CapabilityError, "queue is full"):
                self.authority.request(
                    seat="worker3", lineage="openai:test",
                    operations=["read_repo"], ttl_seconds=300)


if __name__ == "__main__":
    unittest.main()
