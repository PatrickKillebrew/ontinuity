"""Short-lived, operator-approved capabilities for Ontinuity courier access.

The master secret signs capabilities but is never placed in a capability or in
the registry.  A capability binds seat, lineage, allowed operations, expiry,
and a random identifier.  The registry keeps approval and revocation state;
it never stores issued bearer tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid


class CapabilityError(ValueError):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class CapabilityAuthority:
    MAX_TTL_SECONDS = 3600

    def __init__(self, *, secret, registry_path, now=None):
        if not secret:
            raise CapabilityError("capability signing secret is required")
        self._secret = str(secret).encode("utf-8")
        self.registry_path = registry_path
        self._now = now or time.time
        self._lock = threading.Lock()

    def _load(self):
        try:
            with open(self.registry_path, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {"requests": {}, "issued": {}, "revoked": {}}

    def _save(self, data):
        parent = os.path.dirname(os.path.abspath(self.registry_path))
        os.makedirs(parent, exist_ok=True)
        temp_path = f"{self.registry_path}.{uuid.uuid4().hex}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, separators=(",", ":"))
        os.replace(temp_path, self.registry_path)

    @staticmethod
    def _clean_identity(value, field):
        value = str(value or "").strip()
        if not value or len(value) > 160:
            raise CapabilityError(f"valid {field} is required")
        return value

    @staticmethod
    def _clean_operations(operations):
        if not isinstance(operations, (list, tuple, set)) or not operations:
            raise CapabilityError("operations must be an explicit nonempty allowlist")
        clean = sorted({str(op).strip() for op in operations if str(op).strip()})
        if not clean or any(len(op) > 80 for op in clean):
            raise CapabilityError("operations must be an explicit nonempty allowlist")
        return clean

    def request(self, *, seat, lineage, operations, ttl_seconds=900):
        seat = self._clean_identity(seat, "seat")
        lineage = self._clean_identity(lineage, "lineage")
        operations = self._clean_operations(operations)
        try:
            ttl_seconds = int(ttl_seconds)
        except (TypeError, ValueError):
            raise CapabilityError("ttl_seconds must be an integer")
        if ttl_seconds < 1 or ttl_seconds > self.MAX_TTL_SECONDS:
            raise CapabilityError(f"ttl_seconds must be 1..{self.MAX_TTL_SECONDS}")
        request_id = uuid.uuid4().hex
        created_at = int(self._now())
        row = {"seat": seat, "lineage": lineage, "ops": operations,
               "ttl": ttl_seconds, "status": "pending", "created_at": created_at}
        with self._lock:
            data = self._load()
            data.setdefault("requests", {})[request_id] = row
            self._save(data)
        return {"request_id": request_id, **row}

    def approve(self, request_id):
        request_id = str(request_id or "").strip()
        with self._lock:
            data = self._load()
            row = data.setdefault("requests", {}).get(request_id)
            if not row or row.get("status") != "pending":
                raise CapabilityError("pending admission request not found")
            issued_at = int(self._now())
            jti = uuid.uuid4().hex
            payload = {"seat": row["seat"], "lineage": row["lineage"],
                       "ops": row["ops"], "iat": issued_at,
                       "exp": issued_at + int(row["ttl"]), "jti": jti}
            token = self._encode(payload)
            row["status"] = "approved"
            row["approved_at"] = issued_at
            row["jti"] = jti
            data.setdefault("issued", {})[jti] = {
                "request_id": request_id, "seat": row["seat"],
                "lineage": row["lineage"], "exp": payload["exp"]}
            self._save(data)
        return {"capability": token, "identity": payload}

    def revoke(self, jti):
        jti = str(jti or "").strip()
        if not jti:
            raise CapabilityError("jti is required")
        with self._lock:
            data = self._load()
            if jti not in data.setdefault("issued", {}):
                raise CapabilityError("issued capability not found")
            data.setdefault("revoked", {})[jti] = int(self._now())
            self._save(data)
        return {"revoked": True, "jti": jti}

    def _encode(self, payload):
        header = _b64encode(b'{"alg":"HS256","typ":"OCAP"}')
        body = _b64encode(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header}.{body}".encode("ascii")
        signature = _b64encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        return f"{header}.{body}.{signature}"

    def authorize(self, token, operation, *, now=None):
        try:
            header, body, signature = str(token or "").split(".")
        except ValueError:
            raise CapabilityError("malformed capability")
        signing_input = f"{header}.{body}".encode("ascii")
        expected = _b64encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        if not secrets.compare_digest(signature, expected):
            raise CapabilityError("invalid signature")
        try:
            header_data = json.loads(_b64decode(header))
            payload = json.loads(_b64decode(body))
        except Exception:
            raise CapabilityError("malformed capability")
        if header_data != {"alg": "HS256", "typ": "OCAP"}:
            raise CapabilityError("invalid capability header")
        required = {"seat", "lineage", "ops", "iat", "exp", "jti"}
        if not required.issubset(payload):
            raise CapabilityError("incomplete capability")
        current = int(self._now() if now is None else now)
        if current >= int(payload["exp"]):
            raise CapabilityError("capability expired")
        operation = str(operation or "").strip()
        if operation not in payload["ops"]:
            raise CapabilityError("operation not allowed")
        with self._lock:
            data = self._load()
        issued = data.get("issued", {}).get(payload["jti"])
        if not issued:
            raise CapabilityError("capability is not operator-approved")
        if payload["jti"] in data.get("revoked", {}):
            raise CapabilityError("capability revoked")
        # Bind the signed identity to the approved registry record as a second
        # check against registry substitution or malformed signed payloads.
        if (issued.get("seat") != payload["seat"] or
                issued.get("lineage") != payload["lineage"] or
                int(issued.get("exp", -1)) != int(payload["exp"])):
            raise CapabilityError("capability identity mismatch")
        return payload
