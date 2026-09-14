"""Short-lived, operator-approved capabilities for Ontinuity courier access.

The master secret signs capabilities but is never placed in a capability or in
the registry.  A capability binds seat, lineage, allowed operations, expiry,
and a random identifier. The registry keeps approval, revocation, and bounded
side-effecting transition receipts; it never stores issued bearer tokens.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid


MAX_PENDING_REQUESTS = 200
PENDING_REQUEST_TTL_SECONDS = 3600
MAX_TRANSITION_RECORDS = 200
TRANSITION_TTL_SECONDS = 86400
MAX_REPLAY_BODY_BYTES = 65536


class CapabilityError(ValueError):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class CapabilityAuthority:
    MAX_TTL_SECONDS = 3600
    ELEVATED_MAX_TTL_SECONDS = 300

    def __init__(self, *, secret, registry_path, now=None):
        if not secret:
            raise CapabilityError("capability signing secret is required")
        self._secret = str(secret).encode("utf-8")
        self.registry_path = registry_path
        self.registry_lock_path = f"{registry_path}.lock.sqlite3"
        self._now = now or time.time
        self._lock = threading.Lock()

    @contextmanager
    def _registry_transaction(self):
        """Serialize one JSON load/modify/replace transaction across processes.

        The JSON registry remains human-inspectable and backward compatible.
        A separate SQLite file supplies a provider-neutral, crash-releasing
        interprocess write lock. ``BEGIN IMMEDIATE`` is acquired before the JSON
        load and held through its atomic replacement, so two app processes cannot
        both observe and claim the same transition as new.
        """
        parent = os.path.dirname(os.path.abspath(self.registry_path))
        os.makedirs(parent, exist_ok=True)
        with self._lock:
            connection = None
            try:
                connection = sqlite3.connect(
                    self.registry_lock_path, timeout=30,
                    isolation_level=None)
                os.chmod(self.registry_lock_path, 0o600)
                connection.execute("PRAGMA busy_timeout = 30000")
                connection.execute("BEGIN IMMEDIATE")
                yield
                connection.execute("COMMIT")
            except sqlite3.Error as exc:
                if connection is not None and connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise CapabilityError(
                    "capability registry transaction lock failed") from exc
            except Exception:
                if connection is not None and connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                if connection is not None:
                    connection.close()

    def _load(self):
        try:
            with open(self.registry_path, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return {"requests": {}, "issued": {}, "revoked": {},
                    "transitions": {}}
        except (json.JSONDecodeError, OSError) as exc:
            raise CapabilityError("capability registry is unreadable") from exc
        if (not isinstance(data, dict)
                or not all(isinstance(data.get(key), dict)
                           for key in ("requests", "issued", "revoked"))):
            raise CapabilityError("capability registry has an invalid shape")
        transitions = data.setdefault("transitions", {})
        if not isinstance(transitions, dict):
            raise CapabilityError("capability registry has an invalid shape")
        return data

    def _save(self, data):
        parent = os.path.dirname(os.path.abspath(self.registry_path))
        os.makedirs(parent, exist_ok=True)
        temp_path = f"{self.registry_path}.{uuid.uuid4().hex}.tmp"
        descriptor = os.open(
            temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True, separators=(",", ":"))
            os.replace(temp_path, self.registry_path)
            os.chmod(self.registry_path, 0o600)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _registry_integer(row, field):
        if (not isinstance(row, dict) or type(row.get(field)) is not int
                or row[field] < 0):
            raise CapabilityError("capability registry has an invalid shape")
        return row[field]

    def _prune(self, data, now=None):
        """Bound registry growth and expire requests that were never approved."""
        current = int(self._now() if now is None else now)
        requests = data.setdefault("requests", {})
        issued = data.setdefault("issued", {})
        revoked = data.setdefault("revoked", {})
        transitions = data.setdefault("transitions", {})

        for request_id, row in list(requests.items()):
            created_at = self._registry_integer(row, "created_at")
            if (row.get("status") == "pending"
                    and current - created_at >= PENDING_REQUEST_TTL_SECONDS):
                row["status"] = "expired"
                row["expired_at"] = current

        # Once an issued grant is expired, its registry entry and any matching
        # revocation marker no longer serve an authorization purpose.
        for jti, row in list(issued.items()):
            if current >= self._registry_integer(row, "exp"):
                issued.pop(jti, None)
                revoked.pop(jti, None)

        if any(type(revoked_at) is not int or revoked_at < 0
               for revoked_at in revoked.values()):
            raise CapabilityError("capability registry has an invalid shape")

        # Keep only the newest completed request records. Pending requests are
        # separately bounded at admission time and are never discarded here.
        completed = sorted(
            ((request_id, row) for request_id, row in requests.items()
             if row.get("status") != "pending"),
            key=lambda item: self._registry_integer(item[1], "created_at"),
            reverse=True,
        )
        for request_id, _row in completed[MAX_PENDING_REQUESTS:]:
            requests.pop(request_id, None)

        # Transition receipts are private, bounded replay state for capability
        # operations whose effects must not be repeated after an ambiguous
        # client-side transport result. They expire independently of grants.
        for transition_id, row in list(transitions.items()):
            created_at = self._registry_integer(row, "created_at")
            if current - created_at >= TRANSITION_TTL_SECONDS:
                transitions.pop(transition_id, None)
        protected_count = sum(
            1 for row in transitions.values()
            if row.get("state") != "completed")
        completed_transitions = sorted(
            ((transition_id, row) for transition_id, row in transitions.items()
             if row.get("state") == "completed"),
            key=lambda item: self._registry_integer(item[1], "created_at"),
            reverse=True,
        )
        completed_limit = max(0, MAX_TRANSITION_RECORDS - protected_count)
        for transition_id, _row in completed_transitions[completed_limit:]:
            transitions.pop(transition_id, None)
        return data

    @staticmethod
    def _clean_transition_identity(request_id, fingerprint):
        request_id = str(request_id or "").strip()
        fingerprint = str(fingerprint or "").strip()
        if not re.fullmatch(r"[0-9a-f]{32}", request_id):
            raise CapabilityError("invalid Ontinuity request id")
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise CapabilityError("invalid Ontinuity request fingerprint")
        return request_id, fingerprint

    def begin_transition(self, request_id, fingerprint):
        """Atomically claim a side-effecting capability transition.

        The return state is ``new`` for the sole caller allowed to relay,
        ``completed`` with a cached response for a safe replay, or
        ``in_progress``/``unknown``/``conflict`` for fail-stop outcomes.
        """
        request_id, fingerprint = self._clean_transition_identity(
            request_id, fingerprint)
        current = int(self._now())
        with self._registry_transaction():
            data = self._prune(self._load(), current)
            transitions = data.setdefault("transitions", {})
            row = transitions.get(request_id)
            if row is None:
                if len(transitions) >= MAX_TRANSITION_RECORDS:
                    raise CapabilityError("transition receipt registry is full")
                transitions[request_id] = {
                    "fingerprint": fingerprint,
                    "state": "in_progress",
                    "created_at": current,
                    "updated_at": current,
                }
                self._save(data)
                return {"state": "new"}
            if row.get("fingerprint") != fingerprint:
                return {"state": "conflict"}
            return dict(row)

    def complete_transition(self, request_id, fingerprint, *, status,
                            content_type, response_body):
        request_id, fingerprint = self._clean_transition_identity(
            request_id, fingerprint)
        try:
            status = int(status)
        except (TypeError, ValueError) as exc:
            raise CapabilityError("invalid transition response status") from exc
        content_type = str(content_type or "application/json")[:200]
        if any(ord(character) < 32 or ord(character) == 127
               for character in content_type):
            content_type = "application/json"
        response_body = str(response_body)
        encoded = response_body.encode("utf-8")
        current = int(self._now())
        with self._registry_transaction():
            data = self._prune(self._load(), current)
            row = data.setdefault("transitions", {}).get(request_id)
            if (not row or row.get("fingerprint") != fingerprint
                    or row.get("state") != "in_progress"):
                raise CapabilityError("transition receipt state changed")
            row["updated_at"] = current
            row["status"] = status
            row["content_type"] = content_type
            row["response_sha256"] = hashlib.sha256(encoded).hexdigest()
            if len(encoded) <= MAX_REPLAY_BODY_BYTES:
                row["response_body"] = response_body
                row["state"] = "completed"
            else:
                row["state"] = "unknown"
                row["error"] = "response exceeded replay bound"
            self._save(data)
            return dict(row)

    def abandon_transition(self, request_id, fingerprint, reason="relay outcome unknown"):
        request_id, fingerprint = self._clean_transition_identity(
            request_id, fingerprint)
        current = int(self._now())
        with self._registry_transaction():
            data = self._prune(self._load(), current)
            row = data.setdefault("transitions", {}).get(request_id)
            if (row and row.get("fingerprint") == fingerprint
                    and row.get("state") == "in_progress"):
                row["state"] = "unknown"
                row["updated_at"] = current
                row["error"] = str(reason or "relay outcome unknown")[:200]
                self._save(data)

    @staticmethod
    def _clean_identity(value, field):
        value = str(value or "").strip()
        if not value or len(value) > 160:
            raise CapabilityError(f"valid {field} is required")
        if any(ord(character) < 32 or ord(character) == 127
               for character in value):
            raise CapabilityError(f"valid {field} is required")
        if field == "seat" and not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", value):
            raise CapabilityError("valid seat is required")
        return value

    @staticmethod
    def _clean_operations(operations):
        if not isinstance(operations, (list, tuple, set)) or not operations:
            raise CapabilityError("operations must be an explicit nonempty allowlist")
        if not all(isinstance(op, str) for op in operations):
            raise CapabilityError("operations must be an explicit nonempty allowlist")
        clean = sorted({op.strip() for op in operations if op.strip()})
        if not clean or len(clean) > 32 or any(len(op) > 80 for op in clean):
            raise CapabilityError("operations must be an explicit nonempty allowlist")
        return clean

    @staticmethod
    def _clean_deploy_scope(scope):
        """Return the one immutable object an elevated deploy grant may name."""
        expected = {"signoff_block_id", "commit_sha", "target_scope"}
        if not isinstance(scope, dict) or set(scope) != expected:
            raise CapabilityError(
                "deploy_scope keys must be exactly signoff_block_id, "
                "commit_sha, target_scope")
        if not all(isinstance(scope[key], str) for key in expected):
            raise CapabilityError("deploy_scope fields must be strings")
        block_id = scope["signoff_block_id"]
        commit_sha = scope["commit_sha"]
        target_scope = scope["target_scope"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", block_id):
            raise CapabilityError("deploy_scope signoff_block_id is invalid")
        if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise CapabilityError("deploy_scope commit_sha is invalid")
        if target_scope not in {"main", "farm", "both"}:
            raise CapabilityError("deploy_scope target_scope must be main, farm, or both")
        return {
            "signoff_block_id": block_id,
            "commit_sha": commit_sha,
            "target_scope": target_scope,
        }

    def request(self, *, seat, lineage, operations, ttl_seconds=900,
                deploy_scope=None):
        seat = self._clean_identity(seat, "seat")
        lineage = self._clean_identity(lineage, "lineage")
        operations = self._clean_operations(operations)
        elevated = operations == ["deploy"]
        if "deploy" in operations and not elevated:
            raise CapabilityError("elevated admission is deploy-only")
        if elevated:
            if type(ttl_seconds) is not int:
                raise CapabilityError("ttl_seconds must be an integer")
        else:
            try:
                ttl_seconds = int(ttl_seconds)
            except (TypeError, ValueError):
                raise CapabilityError("ttl_seconds must be an integer")
        if elevated:
            deploy_scope = self._clean_deploy_scope(deploy_scope)
        elif deploy_scope is not None:
            raise CapabilityError("deploy_scope is valid only for deploy admission")
        maximum_ttl = (self.ELEVATED_MAX_TTL_SECONDS if elevated
                       else self.MAX_TTL_SECONDS)
        if ttl_seconds < 1 or ttl_seconds > maximum_ttl:
            if elevated:
                raise CapabilityError(
                    "elevated admission is deploy-only with ttl_seconds 1..300")
            raise CapabilityError(f"ttl_seconds must be 1..{self.MAX_TTL_SECONDS}")
        request_id = uuid.uuid4().hex
        created_at = int(self._now())
        row = {"seat": seat, "lineage": lineage, "ops": operations,
               "ttl": ttl_seconds, "status": "pending", "created_at": created_at,
               "elevated": elevated,
               "risk_tier": "high-impact" if elevated else "initial"}
        if elevated:
            row["deploy_scope"] = deploy_scope
        with self._registry_transaction():
            data = self._prune(self._load(), created_at)
            pending_count = sum(
                1 for request_row in data.setdefault("requests", {}).values()
                if request_row.get("status") == "pending"
            )
            if pending_count >= MAX_PENDING_REQUESTS:
                raise CapabilityError("pending admission queue is full")
            data.setdefault("requests", {})[request_id] = row
            self._save(data)
        return {"request_id": request_id, **row}

    def list_requests(self):
        """Return operator-facing request metadata; bearer tokens are never stored."""
        with self._registry_transaction():
            data = self._prune(self._load())
            self._save(data)
        rows = []
        for request_id, row in data.get("requests", {}).items():
            item = {"request_id": request_id, **row}
            if item.get("jti") in data.get("revoked", {}):
                item["status"] = "revoked"
                item["revoked_at"] = data["revoked"][item["jti"]]
            rows.append(item)
        rows.sort(
            key=lambda row: self._registry_integer(row, "created_at"),
            reverse=True,
        )
        return rows

    def approve(self, request_id, *, elevated_confirmed=False):
        request_id = str(request_id or "").strip()
        with self._registry_transaction():
            data = self._prune(self._load())
            row = data.setdefault("requests", {}).get(request_id)
            if not row or row.get("status") != "pending":
                raise CapabilityError("pending admission request not found")
            try:
                operations = self._clean_operations(row.get("ops"))
                seat = self._clean_identity(row.get("seat"), "seat")
                lineage = self._clean_identity(row.get("lineage"), "lineage")
                ttl = row.get("ttl")
                if (not isinstance(ttl, int) or isinstance(ttl, bool)
                        or ttl < 1 or ttl > self.MAX_TTL_SECONDS):
                    raise CapabilityError("pending admission metadata is inconsistent")
            except CapabilityError as exc:
                raise CapabilityError(
                    "pending admission metadata is inconsistent") from exc
            elevated = operations == ["deploy"]
            if "deploy" in operations and not elevated:
                raise CapabilityError("pending admission metadata is inconsistent")
            if elevated:
                if (ttl > self.ELEVATED_MAX_TTL_SECONDS
                        or row.get("elevated") is not True
                        or row.get("risk_tier") != "high-impact"):
                    raise CapabilityError(
                        "pending deploy elevation metadata is inconsistent")
                try:
                    deploy_scope = self._clean_deploy_scope(
                        row.get("deploy_scope"))
                except CapabilityError as exc:
                    raise CapabilityError(
                        "pending deploy elevation metadata is inconsistent") from exc
            elif (("elevated" in row and row.get("elevated") is not False)
                  or ("risk_tier" in row and row.get("risk_tier") != "initial")):
                raise CapabilityError("pending admission metadata is inconsistent")
            if elevated and elevated_confirmed is not True:
                raise CapabilityError(
                    "explicit elevated-operation confirmation is required")
            issued_at = int(self._now())
            jti = uuid.uuid4().hex
            payload = {"seat": seat, "lineage": lineage,
                       "ops": operations, "iat": issued_at,
                       "exp": issued_at + ttl, "jti": jti}
            if elevated:
                payload["deploy_scope"] = deploy_scope
            token = self._encode(payload)
            row["status"] = "approved"
            row["approved_at"] = issued_at
            row["jti"] = jti
            data.setdefault("issued", {})[jti] = {
                "request_id": request_id, "seat": seat,
                "lineage": lineage, "ops": list(operations),
                "exp": payload["exp"]}
            if elevated:
                data["issued"][jti]["deploy_scope"] = deploy_scope
            self._save(data)
        return {"capability": token, "identity": payload}

    def revoke(self, jti):
        jti = str(jti or "").strip()
        if not jti:
            raise CapabilityError("jti is required")
        with self._registry_transaction():
            data = self._prune(self._load())
            if jti not in data.setdefault("issued", {}):
                raise CapabilityError("issued capability not found")
            revoked_at = int(self._now())
            data.setdefault("revoked", {})[jti] = revoked_at
            for row in data.setdefault("requests", {}).values():
                if row.get("jti") == jti:
                    row["status"] = "revoked"
                    row["revoked_at"] = revoked_at
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
        if not isinstance(payload, dict) or not required.issubset(payload):
            raise CapabilityError("incomplete capability")
        if (not isinstance(payload["seat"], str)
                or not isinstance(payload["lineage"], str)
                or not isinstance(payload["jti"], str)
                or not isinstance(payload["ops"], list)
                or not payload["ops"]
                or not all(isinstance(item, str) for item in payload["ops"])):
            raise CapabilityError("invalid capability claims")
        if type(payload["iat"]) is not int or type(payload["exp"]) is not int:
            raise CapabilityError("invalid capability lifetime")
        try:
            self._clean_identity(payload["seat"], "seat")
            self._clean_identity(payload["lineage"], "lineage")
            clean_ops = self._clean_operations(payload["ops"])
        except CapabilityError as exc:
            raise CapabilityError("invalid capability claims") from exc
        if clean_ops != payload["ops"] or not re.fullmatch(
                r"[0-9a-f]{32}", payload["jti"]):
            raise CapabilityError("invalid capability claims")
        if clean_ops == ["deploy"]:
            try:
                clean_scope = self._clean_deploy_scope(
                    payload.get("deploy_scope"))
            except CapabilityError as exc:
                raise CapabilityError("invalid capability claims") from exc
            if clean_scope != payload.get("deploy_scope"):
                raise CapabilityError("invalid capability claims")
        elif "deploy_scope" in payload:
            raise CapabilityError("invalid capability claims")
        current = int(self._now() if now is None else now)
        if payload["exp"] <= payload["iat"] or current >= payload["exp"]:
            raise CapabilityError("capability expired")
        operation = str(operation or "").strip()
        if operation not in payload["ops"]:
            raise CapabilityError("operation not allowed")
        with self._registry_transaction():
            data = self._prune(self._load(), current)
        issued = data.get("issued", {}).get(payload["jti"])
        if not issued:
            raise CapabilityError("capability is not operator-approved")
        if payload["jti"] in data.get("revoked", {}):
            raise CapabilityError("capability revoked")
        # Bind the signed identity to the approved registry record as a second
        # check against registry substitution or malformed signed payloads.
        if (issued.get("seat") != payload["seat"] or
                issued.get("lineage") != payload["lineage"] or
                issued.get("ops") != payload["ops"] or
                self._registry_integer(issued, "exp") != payload["exp"]):
            raise CapabilityError("capability identity mismatch")
        if clean_ops == ["deploy"] and issued.get("deploy_scope") != clean_scope:
            raise CapabilityError("capability deploy scope mismatch")
        return payload
