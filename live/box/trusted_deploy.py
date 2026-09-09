"""Trusted, exact-commit deployment adapter for the B1 box boundary.

The public caller supplies only an action, target, sign-off block, and commit.
All provider facts and the only provider credential stay in this module and the
box environment.  Provider I/O has one mechanical implementation: a trusted
``curl --config -`` child with its private config on stdin.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
import re
import selectors
import stat
import subprocess
import tempfile
import time
import uuid


class DeployError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


RAILWAY_ENDPOINT = "https://backboard.railway.app/graphql/v2"
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRUSTED_CONFIG_PATH = os.path.join(_BASE_DIR, "trusted_deploy_config.json")
DEFAULT_STATE_DIR = os.path.join(_BASE_DIR, ".workspace", "deploy-state")
_MAX_CONFIG_BYTES = 4096
_TRUSTED_CONFIG_KEYS = {
    "railway_project_id", "railway_environment_id",
    "railway_service_id_main", "railway_service_id_farm",
}
RAILWAY_DEPLOY_MUTATION = (
    "mutation B1Deploy($serviceId:String!,$environmentId:String!,"
    "$commitSha:String!){serviceInstanceDeployV2(serviceId:$serviceId,"
    "environmentId:$environmentId,commitSha:$commitSha)}"
)
RAILWAY_STATUS_QUERY = (
    "query B1Status($serviceId:String!,$environmentId:String!){"
    "deployments(first:20,input:{serviceId:$serviceId,environmentId:"
    "$environmentId}){edges{node{id status serviceId meta}}}}"
)
RAILWAY_LOGS_QUERY = (
    "query B1Logs($deploymentId:String!,$limit:Int!){buildLogs("
    "deploymentId:$deploymentId,limit:$limit){message severity timestamp}}"
)
PROVIDER_TIMEOUT_SECONDS = 8
PROVIDER_PROCESS_DEADLINE_SECONDS = 9
PROVIDER_RESPONSE_MAX_BYTES = 256 * 1024
LOCK_WAIT_SECONDS = 2
BUILD_LOG_LIMIT = 50
STATE_SCHEMA = 1
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_BLOCK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SAFE_TEXT_RE = re.compile(r"[\x20-\x7e]{1,64}")
_RFC3339_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
_CANONICAL_TIMESTAMP_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"\.[0-9]{6}Z"
)
_LOG_SEVERITIES = frozenset({
    "debug", "info", "warning", "error", "critical", "unknown",
})
_SEVERITY_ALIASES = {
    "trace": "debug", "debug": "debug",
    "info": "info", "information": "info", "notice": "info",
    "warn": "warning", "warning": "warning",
    "err": "error", "error": "error",
    "fatal": "critical", "critical": "critical",
}
_PENDING_STATUSES = {"ACCEPTED", "INITIALIZING", "QUEUED", "BUILDING", "DEPLOYING"}
_FAILURE_STATUSES = {"FAILED", "CRASHED", "REMOVED", "CANCELED", "CANCELLED"}
_STATE_KEYS = {
    "schema", "tracking_id", "block_id", "target", "commit_sha", "provider",
    "provider_deployment_id", "service_id", "environment_id", "project_id",
    "phase", "provider_status", "terminal", "log_summary", "created_at",
    "updated_at",
}
_PHASES = {"mutation_pending", "mutation_unknown", "accepted", "pending", "success", "failure"}


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _strict_json(raw):
    try:
        text = raw.decode("utf-8", "strict") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DeployError("invalid provider response", status=502) from exc


def validate_request(body):
    if not isinstance(body, dict):
        raise DeployError("request must be a JSON object")
    expected = {"action", "target", "signoff_block_id", "commit_sha"}
    if set(body) != expected:
        raise DeployError("request keys must be exactly action, target, signoff_block_id, commit_sha")
    if not all(isinstance(body[key], str) for key in expected):
        raise DeployError("all deploy request fields must be strings")
    action = body["action"]
    target = body["target"]
    block_id = body["signoff_block_id"]
    commit_sha = body["commit_sha"]
    if action not in {"start", "status"}:
        raise DeployError("action must be start or status")
    if target not in {"main", "farm"}:
        raise DeployError("target must be main or farm")
    if not _BLOCK_RE.fullmatch(block_id):
        raise DeployError("signoff_block_id is invalid")
    if not _COMMIT_RE.fullmatch(commit_sha):
        raise DeployError("commit_sha must be 40 lowercase hexadecimal characters")
    return action, target, block_id, commit_sha


def tracking_id(block_id, target, commit_sha):
    value = "\n".join(("b1-deploy-v1", block_id, target, commit_sha, ""))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_uuid(value, label):
    if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
        raise DeployError(f"{label} must be a canonical UUID", status=503)
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except ValueError as exc:
        raise DeployError(f"{label} must be a canonical UUID", status=503) from exc
    return value


def validate_config_document(raw):
    """Validate the dedicated non-secret box configuration exactly."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, bytes) or len(raw) > _MAX_CONFIG_BYTES:
        raise DeployError("trusted deploy configuration is invalid", status=503)
    value = _strict_json(raw)
    if not isinstance(value, dict) or set(value) != _TRUSTED_CONFIG_KEYS:
        raise DeployError("trusted deploy configuration is invalid", status=503)
    return {
        key: _canonical_uuid(item, key.replace("_", " "))
        for key, item in value.items()
    }


def _file_provider_ids():
    try:
        info = os.lstat(TRUSTED_CONFIG_PATH)
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise DeployError(
                "trusted deploy configuration is not a private regular file",
                status=503,
            )
        descriptor = os.open(
            TRUSTED_CONFIG_PATH,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            raw = os.read(descriptor, 4097)
        finally:
            os.close(descriptor)
    except FileNotFoundError as exc:
        raise DeployError(
            "trusted deploy configuration is unavailable", status=503,
        ) from exc
    return validate_config_document(raw)


def _provider_config(target):
    provider = os.environ.get("HOSTING_PROVIDER", "railway").strip().lower()
    if provider != "railway":
        raise DeployError("configured hosting provider is unsupported", status=503)
    token = os.environ.get("RAILWAY_TOKEN", "").strip()
    if (not token or len(token) > 4096
            or any(ord(char) < 33 or ord(char) == 127 for char in token)):
        raise DeployError("trusted provider credential is unavailable or invalid", status=503)
    env_ids = {
        "railway_project_id": os.environ.get("RAILWAY_PROJECT_ID", "").strip(),
        "railway_environment_id": os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip(),
        "railway_service_id_main": os.environ.get("RAILWAY_SERVICE_ID_MAIN", "").strip(),
        "railway_service_id_farm": os.environ.get("RAILWAY_SERVICE_ID_FARM", "").strip(),
    }
    if all(env_ids.values()):
        provider_ids = {
            key: _canonical_uuid(value, key.replace("_", " "))
            for key, value in env_ids.items()
        }
    elif any(env_ids.values()):
        raise DeployError(
            "trusted provider environment identifiers are incomplete",
            status=503,
        )
    else:
        provider_ids = _file_provider_ids()
    config = {
        "token": token,
        "project_id": provider_ids["railway_project_id"],
        "environment_id": provider_ids["railway_environment_id"],
        "service_id": provider_ids["railway_service_id_" + target],
    }
    return provider, config


def _state_dir():
    path = os.environ.get(
        "ONTINUITY_DEPLOY_STATE_DIR", DEFAULT_STATE_DIR).strip()
    if not path or not os.path.isabs(path):
        raise DeployError("ONTINUITY_DEPLOY_STATE_DIR must be an absolute persistent path", status=503)
    try:
        existing = os.lstat(path)
    except FileNotFoundError:
        parent = os.path.dirname(path)
        parent_stat = os.lstat(parent)
        if not stat.S_ISDIR(parent_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode):
            raise DeployError("deploy state parent is not a regular directory", status=503)
        os.mkdir(path, 0o700)
        existing = os.lstat(path)
    if not stat.S_ISDIR(existing.st_mode) or stat.S_ISLNK(existing.st_mode):
        raise DeployError("deploy state path is not a regular directory", status=503)
    os.chmod(path, 0o700)
    return path


def _regular_or_absent(path, label):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise DeployError(f"{label} is not a regular file", status=503)


@contextmanager
def tuple_lock(_tracking):
    directory = _state_dir()
    lock_path = os.path.join(directory, ".deploy-state.lock")
    _regular_or_absent(lock_path, "deploy lock")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DeployError("deploy lock is unavailable", status=503) from exc
    try:
        os.fchmod(descriptor, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise DeployError("deploy lock is not a regular file", status=503)
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise DeployError("deploy state lock timed out", status=503) from exc
                time.sleep(0.02)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _valid_time(value):
    return type(value) is int and value >= 0


def _now():
    return int(time.time())


def _canonical_provider_timestamp(value):
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        raise DeployError("invalid provider log response", status=502)
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ")
    except (OverflowError, ValueError) as exc:
        raise DeployError("invalid provider log response", status=502) from exc


def _valid_canonical_timestamp(value):
    if not isinstance(value, str) or not _CANONICAL_TIMESTAMP_RE.fullmatch(value):
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ") == value


def _validate_log_summary(value):
    if not isinstance(value, dict) or set(value) != {
            "available", "line_count", "severity_counts",
            "first_timestamp", "last_timestamp"}:
        raise DeployError("deploy state log summary is corrupt", status=503)
    if not isinstance(value["available"], bool):
        raise DeployError("deploy state log summary is corrupt", status=503)
    count = value["line_count"]
    severities = value["severity_counts"]
    if (not isinstance(count, int) or isinstance(count, bool)
            or count < 0 or count > BUILD_LOG_LIMIT or not isinstance(severities, dict)):
        raise DeployError("deploy state log summary is corrupt", status=503)
    total = 0
    for key, item in severities.items():
        if (key not in _LOG_SEVERITIES
                or not isinstance(item, int) or isinstance(item, bool) or item <= 0
                or item > BUILD_LOG_LIMIT):
            raise DeployError("deploy state log summary is corrupt", status=503)
        total += item
    for key in ("first_timestamp", "last_timestamp"):
        item = value[key]
        if item is not None and not _valid_canonical_timestamp(item):
            raise DeployError("deploy state log summary is corrupt", status=503)
    first = value["first_timestamp"]
    last = value["last_timestamp"]
    unavailable_invalid = (not value["available"] and (
        count != 0 or severities != {} or first is not None or last is not None))
    empty_available_invalid = (value["available"] and count == 0 and (
        severities != {} or first is not None or last is not None))
    positive_available_invalid = (value["available"] and count > 0 and (
        not severities or first is None or last is None or first > last))
    if (total != count or unavailable_invalid or empty_available_invalid
            or positive_available_invalid):
        raise DeployError("deploy state log summary is corrupt", status=503)


def _validate_state(record, expected=None):
    if not isinstance(record, dict) or set(record) != _STATE_KEYS:
        raise DeployError("deploy state is corrupt", status=503)
    if type(record["schema"]) is not int or record["schema"] != STATE_SCHEMA:
        raise DeployError("deploy state schema is unsupported", status=503)
    string_fields = ("tracking_id", "block_id", "target", "commit_sha", "provider",
                     "service_id", "environment_id", "project_id", "phase", "provider_status")
    if not all(isinstance(record[key], str) for key in string_fields):
        raise DeployError("deploy state is corrupt", status=503)
    if (not re.fullmatch(r"[0-9a-f]{64}", record["tracking_id"])
            or not _BLOCK_RE.fullmatch(record["block_id"])
            or record["target"] not in {"main", "farm"}
            or not _COMMIT_RE.fullmatch(record["commit_sha"])
            or record["provider"] != "railway"
            or record["phase"] not in _PHASES
            or not _SAFE_TEXT_RE.fullmatch(record["provider_status"])
            or not isinstance(record["terminal"], bool)
            or not _valid_time(record["created_at"])
            or not _valid_time(record["updated_at"])
            or record["updated_at"] < record["created_at"]):
        raise DeployError("deploy state is corrupt", status=503)
    for field in ("service_id", "environment_id", "project_id"):
        _canonical_uuid(record[field], field.replace("_", " "))
    deployment_id = record["provider_deployment_id"]
    if deployment_id is not None:
        _canonical_uuid(deployment_id, "provider deployment id")
    phase = record["phase"]
    expected_shape = {
        "mutation_pending": (None, "PENDING", False, False),
        "mutation_unknown": (None, "UNKNOWN", False, False),
        "accepted": ("id", "ACCEPTED", False, False),
        "pending": ("id", "pending", False, False),
        "success": ("id", "SUCCESS", True, False),
        "failure": ("id", "failure", True, True),
    }[phase]
    if ((expected_shape[0] is None and deployment_id is not None)
            or (expected_shape[0] == "id" and deployment_id is None)
            or record["terminal"] is not expected_shape[2]):
        raise DeployError("deploy state phase is inconsistent", status=503)
    status_value = record["provider_status"]
    if ((expected_shape[1] == "pending" and status_value not in _PENDING_STATUSES)
            or (expected_shape[1] == "failure" and status_value not in _FAILURE_STATUSES)
            or (expected_shape[1] not in {"pending", "failure"}
                and status_value != expected_shape[1])):
        raise DeployError("deploy state phase is inconsistent", status=503)
    if expected_shape[3]:
        _validate_log_summary(record["log_summary"])
    elif record["log_summary"] is not None:
        raise DeployError("deploy state phase is inconsistent", status=503)
    if expected:
        block_id, target, commit_sha = expected
        if (record["block_id"], record["target"], record["commit_sha"]) != expected:
            raise DeployError("deploy state tuple mismatch", status=409)
        if record["tracking_id"] != tracking_id(block_id, target, commit_sha):
            raise DeployError("deploy state tracking mismatch", status=503)
    return record


def _state_path(track):
    if not re.fullmatch(r"[0-9a-f]{64}", track):
        raise DeployError("tracking id is invalid", status=400)
    return os.path.join(_state_dir(), track + ".json")


def save_state(record):
    _validate_state(record)
    directory = _state_dir()
    path = os.path.join(directory, record["tracking_id"] + ".json")
    _regular_or_absent(path, "deploy state file")
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 8192:
        raise DeployError("deploy state exceeds bound", status=503)
    descriptor, temporary = tempfile.mkstemp(prefix=".state-", dir=directory)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_state(track, block_id, target, commit_sha):
    path = _state_path(track)
    _regular_or_absent(path, "deploy state file")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise DeployError("deploy state file is not regular", status=503)
        raw = os.read(descriptor, 8193)
    finally:
        os.close(descriptor)
    if len(raw) > 8192:
        raise DeployError("deploy state exceeds bound", status=503)
    try:
        record = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DeployError("deploy state is corrupt", status=503) from exc
    return _validate_state(record, (block_id, target, commit_sha))


def _curl_quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'


def _curl_config(token, body):
    body_text = json.dumps(body, sort_keys=True, separators=(",", ":"))
    lines = [
        "silent", "show-error", "request = \"POST\"",
        "url = " + _curl_quote(RAILWAY_ENDPOINT),
        "header = \"Content-Type: application/json\"",
        "header = " + _curl_quote("Project-Access-Token: " + token),
        "data-binary = " + _curl_quote(body_text),
        "proto = \"=https\"", "location = false", "max-redirs = 0",
        "connect-timeout = 3", f"max-time = {PROVIDER_TIMEOUT_SECONDS}",
        "output = \"-\"", "write-out = \"%{http_code}\"",
        "fail = true", "",
    ]
    return "\n".join(lines).encode("utf-8")


def _provider_request(config, query, variables):
    request_body = {"query": query, "variables": variables}
    private_config = _curl_config(config["token"], request_body)
    try:
        process = subprocess.Popen(
            ["curl", "--config", "-"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": os.defpath, "LC_ALL": "C",
                 "CURL_HOME": "/dev/null"},
            shell=False,
        )
    except OSError as exc:
        raise DeployError("trusted provider transport is unavailable", status=503) from exc
    deadline = time.monotonic() + PROVIDER_PROCESS_DEADLINE_SECONDS
    output = bytearray()
    selector = selectors.DefaultSelector()
    try:
        process.stdin.write(private_config)
        process.stdin.close()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                raise DeployError("trusted provider request timed out", status=502)
            events = selector.select(min(remaining, 0.1))
            for key, _mask in events:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if chunk:
                    output.extend(chunk)
                    if len(output) > PROVIDER_RESPONSE_MAX_BYTES + 3:
                        process.kill()
                        raise DeployError("provider response exceeded bound", status=502)
                else:
                    selector.unregister(key.fileobj)
            code = process.poll()
            if code is not None and not selector.get_map():
                break
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=1)
        if process.stdout is not None:
            process.stdout.close()
    raw_output = bytes(output)
    if len(raw_output) < 3 or not re.fullmatch(rb"[0-9]{3}", raw_output[-3:]):
        if code != 0:
            raise DeployError("trusted provider request failed", status=502)
        raise DeployError("provider HTTP status is invalid", status=502)
    http_status = int(raw_output[-3:])
    response_body = raw_output[:-3]
    if http_status < 200 or http_status > 299:
        raise DeployError("provider HTTP status was not successful", status=502)
    if code != 0:
        raise DeployError("trusted provider request failed", status=502)
    if len(response_body) > PROVIDER_RESPONSE_MAX_BYTES:
        raise DeployError("provider response exceeded bound", status=502)
    payload = _strict_json(response_body)
    if not isinstance(payload, dict) or set(payload).difference({"data", "errors", "extensions"}):
        raise DeployError("invalid provider response", status=502)
    if payload.get("errors"):
        raise DeployError("provider refused request", status=502)
    if not isinstance(payload.get("data"), dict):
        raise DeployError("invalid provider response", status=502)
    return payload["data"]


def _base_record(block_id, target, commit_sha, provider, config):
    now = _now()
    return {
        "schema": STATE_SCHEMA,
        "tracking_id": tracking_id(block_id, target, commit_sha),
        "block_id": block_id, "target": target, "commit_sha": commit_sha,
        "provider": provider, "provider_deployment_id": None,
        "service_id": config["service_id"],
        "environment_id": config["environment_id"],
        "project_id": config["project_id"], "phase": "mutation_pending",
        "provider_status": "PENDING", "terminal": False,
        "log_summary": None, "created_at": now, "updated_at": now,
    }


def _require_provider_binding(record, provider, config):
    if (record["provider"] != provider
            or record["service_id"] != config["service_id"]
            or record["environment_id"] != config["environment_id"]
            or record["project_id"] != config["project_id"]):
        raise DeployError("trusted provider configuration changed", status=503)


def _public(record):
    result = {
        "ok": record["phase"] != "failure",
        "tracking_id": record["tracking_id"],
        "action_state": record["phase"], "target": record["target"],
        "commit_sha": record["commit_sha"], "terminal": record["terminal"],
    }
    if record["phase"] == "failure":
        result["build_logs"] = record["log_summary"]
    return result


def start(block_id, target, commit_sha):
    validate_request({"action": "start", "target": target,
                      "signoff_block_id": block_id, "commit_sha": commit_sha})
    provider, config = _provider_config(target)
    track = tracking_id(block_id, target, commit_sha)
    with tuple_lock(track):
        record = load_state(track, block_id, target, commit_sha)
        if record is not None:
            _require_provider_binding(record, provider, config)
            if record["phase"] in {"mutation_pending", "mutation_unknown"}:
                raise DeployError("deployment mutation requires operator reconciliation", status=409)
            return _public(record), False
        record = _base_record(block_id, target, commit_sha, provider, config)
        save_state(record)
        try:
            data = _provider_request(config, RAILWAY_DEPLOY_MUTATION, {
                "serviceId": config["service_id"],
                "environmentId": config["environment_id"],
                "commitSha": commit_sha,
            })
            deployment_id = _canonical_uuid(data.get("serviceInstanceDeployV2"), "provider deployment id")
            record.update({"provider_deployment_id": deployment_id,
                           "phase": "accepted", "provider_status": "ACCEPTED",
                           "updated_at": _now()})
            save_state(record)
        except Exception:
            record.update({"phase": "mutation_unknown", "provider_status": "UNKNOWN",
                           "updated_at": _now()})
            try:
                save_state(record)
            except Exception:
                pass
            raise
        return _public(record), True


def _deployment_node(data, record):
    if not isinstance(data, dict):
        raise DeployError("invalid provider status response", status=502)
    deployments = data.get("deployments")
    if not isinstance(deployments, dict) or not isinstance(deployments.get("edges"), list):
        raise DeployError("invalid provider status response", status=502)
    matches = []
    for edge in deployments["edges"]:
        if not isinstance(edge, dict) or not isinstance(edge.get("node"), dict):
            raise DeployError("invalid provider status response", status=502)
        node = edge["node"]
        if node.get("id") == record["provider_deployment_id"]:
            matches.append(node)
    if len(matches) != 1:
        raise DeployError("tracked deployment not found uniquely", status=502)
    node = matches[0]
    if node.get("serviceId") != record["service_id"]:
        raise DeployError("provider service binding mismatch", status=502)
    meta = node.get("meta")
    if not isinstance(meta, dict):
        raise DeployError("provider commit binding is absent", status=502)
    commit_hash = meta.get("commitHash")
    commit_sha = meta.get("commitSha")
    if commit_hash is not None and commit_sha is not None and commit_hash != commit_sha:
        raise DeployError("provider commit metadata conflicts", status=502)
    observed = commit_hash if commit_hash is not None else commit_sha
    if observed != record["commit_sha"]:
        raise DeployError("provider commit binding mismatch", status=502)
    status_value = node.get("status")
    if not isinstance(status_value, str) or not _SAFE_TEXT_RE.fullmatch(status_value):
        raise DeployError("provider status is invalid", status=502)
    status_value = status_value.upper()
    if status_value not in _PENDING_STATUSES | _FAILURE_STATUSES | {"SUCCESS"}:
        raise DeployError("provider status is unsupported", status=502)
    return status_value


def _unavailable_logs():
    return {"available": False, "line_count": 0, "severity_counts": {},
            "first_timestamp": None, "last_timestamp": None}


def _log_summary(data):
    rows = data.get("buildLogs")
    if not isinstance(rows, list) or len(rows) > BUILD_LOG_LIMIT:
        raise DeployError("invalid provider log response", status=502)
    counts = {}
    timestamps = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("message"), str):
            raise DeployError("invalid provider log response", status=502)
        severity = row.get("severity")
        timestamp = row.get("timestamp")
        if not isinstance(severity, str):
            raise DeployError("invalid provider log response", status=502)
        severity = _SEVERITY_ALIASES.get(severity.casefold(), "unknown")
        timestamp = _canonical_provider_timestamp(timestamp)
        counts[severity] = counts.get(severity, 0) + 1
        timestamps.append(timestamp)
    return {"available": True, "line_count": len(rows),
            "severity_counts": counts,
            "first_timestamp": min(timestamps) if timestamps else None,
            "last_timestamp": max(timestamps) if timestamps else None}


def status(block_id, target, commit_sha):
    validate_request({"action": "status", "target": target,
                      "signoff_block_id": block_id, "commit_sha": commit_sha})
    provider, config = _provider_config(target)
    track = tracking_id(block_id, target, commit_sha)
    with tuple_lock(track):
        record = load_state(track, block_id, target, commit_sha)
        if record is None:
            raise DeployError("deployment state was not found", status=404)
        _require_provider_binding(record, provider, config)
        if record["phase"] in {"mutation_pending", "mutation_unknown"}:
            raise DeployError("deployment mutation requires operator reconciliation", status=409)
        if record["terminal"]:
            return _public(record), False
        data = _provider_request(config, RAILWAY_STATUS_QUERY, {
            "serviceId": record["service_id"],
            "environmentId": record["environment_id"],
        })
        provider_status = _deployment_node(data, record)
        record["provider_status"] = provider_status
        record["updated_at"] = _now()
        if provider_status == "SUCCESS":
            record.update({"phase": "success", "terminal": True})
            save_state(record)
            return _public(record), True
        if provider_status in _FAILURE_STATUSES:
            record.update({"phase": "failure", "terminal": True,
                           "log_summary": _unavailable_logs()})
            save_state(record)
            try:
                log_data = _provider_request(config, RAILWAY_LOGS_QUERY, {
                    "deploymentId": record["provider_deployment_id"],
                    "limit": BUILD_LOG_LIMIT,
                })
                record["log_summary"] = _log_summary(log_data)
                record["updated_at"] = _now()
                save_state(record)
            except DeployError:
                pass
            return _public(record), True
        record["phase"] = "pending"
        save_state(record)
        return _public(record), False
