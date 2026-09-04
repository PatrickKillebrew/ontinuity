#!/usr/bin/env python3
"""Read-only Ontinuity 1.0 release-baseline and drift report.

The command composes existing GitHub, Railway, engine, courier, box, and
workspace-database read surfaces.  It never mutates remote state and never
prints credential values.

Credential input (first match wins):
  ONTINUITY_RAILWAY_TOKEN environment variable
  --llaves PATH containing a ``Railway token: ...`` line

Exit status:
  0  all required observations were obtained and no drift was found
  1  one or more observed values drift from repository ``main``
  2  one or more required observations remain unknown
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ID = "a8dea5f4-b34e-466e-b22c-0d5b59fc63b5"
ENVIRONMENT_ID = "6ff341f9-675e-4514-9b0c-5defe9d3d2a9"
SERVICES = {
    "main": "72b20f74-d24d-4502-ba35-97e2d09f809a",
    "farm": "ae72de62-c1ac-43c1-9d78-ec5e3c0557e5",
}
REPOSITORY = "PatrickKillebrew/ontinuity"
REPOSITORY_BRANCH = "main"
BOX_FILES = (
    "file_server.py",
    "seat_mailbox.py",
    "box_ops.py",
    "db.py",
    "workspace_db_endpoint.py",
)
BOX_REPO_PATHS = {
    "file_server.py": "live/box/file_server.py",
    "seat_mailbox.py": "live/box/seat_mailbox.py",
    "box_ops.py": "live/box/box_ops.py",
    "db.py": "live/db.py",
    "workspace_db_endpoint.py": "live/workspace_db_endpoint.py",
}
ROLE_FIELDS = (
    "MODEL_A_URL", "MODEL_A_MODEL", "MODEL_B_URL", "MODEL_B_MODEL",
    "MODEL_C_URL", "MODEL_C_MODEL", "PARIETAL_URL", "PARIETAL_MODEL",
    "PROJENIUS_URL", "PROJENIUS_MODEL", "PROVIDER_URL", "PROVIDER_MODEL",
)


class ReadFailure(RuntimeError):
    pass


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 25,
    allow_http_error: bool = False,
) -> tuple[int, Any]:
    def quote(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    config = [
        "silent",
        "show-error",
        f"connect-timeout = {min(timeout, 15)}",
        f"max-time = {timeout}",
        f'request = "{quote(method)}"',
        f'url = "{quote(url)}"',
    ]
    for key, value in (headers or {}).items():
        config.append(f'header = "{quote(key + ": " + value)}"')
    if payload is not None:
        config.append('header = "Content-Type: application/json"')
        config.append(f'data-binary = "{quote(json.dumps(payload, separators=(",", ":")))}"')
    config.append('write-out = "\\n%{http_code}"')
    process = None
    transport_detail = ""
    for _attempt in range(2):
        try:
            process = subprocess.run(
                ["curl", "--config", "-"],
                input="\n".join(config) + "\n",
                text=True,
                capture_output=True,
                timeout=timeout + 5,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            transport_detail = str(exc)
            continue
        if process.returncode == 0:
            break
        transport_detail = (
            process.stderr.strip().splitlines()[-1]
            if process.stderr.strip()
            else f"curl exit {process.returncode}"
        )
    if process is None or process.returncode != 0:
        raise ReadFailure(
            f"transport failure to {urllib.parse.urlsplit(url).netloc}: {transport_detail[:180]}"
        )
    try:
        body_text, status_text = process.stdout.rsplit("\n", 1)
        status = int(status_text)
    except (ValueError, TypeError) as exc:
        raise ReadFailure(f"malformed curl receipt from {urllib.parse.urlsplit(url).netloc}") from exc
    raw = body_text.encode("utf-8")
    if status >= 400 and not allow_http_error:
        raise ReadFailure(f"HTTP {status} from {urllib.parse.urlsplit(url).netloc}")
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadFailure(
            f"non-JSON response from {urllib.parse.urlsplit(url).netloc} (HTTP {status})"
        ) from exc


def _graphql(token: str, query: str) -> dict[str, Any]:
    _, response = _request_json(
        "https://backboard.railway.app/graphql/v2",
        method="POST",
        headers={"Project-Access-Token": token},
        payload={"query": query},
    )
    if response.get("errors"):
        messages = [str(item.get("message", "GraphQL error")) for item in response["errors"]]
        raise ReadFailure("Railway GraphQL: " + "; ".join(messages))
    return response.get("data") or {}


def _vault(token: str, service_id: str) -> dict[str, str]:
    query = (
        "query { variables("
        f'projectId: "{PROJECT_ID}", '
        f'environmentId: "{ENVIRONMENT_ID}", '
        f'serviceId: "{service_id}"'
        ") }"
    )
    variables = _graphql(token, query).get("variables")
    if not isinstance(variables, dict):
        raise ReadFailure("Railway vault response omitted variables")
    return {str(key): str(value) for key, value in variables.items()}


def _deployments(token: str, service_id: str) -> list[dict[str, Any]]:
    query = (
        "query { deployments(first: 5, input: {"
        f'projectId: "{PROJECT_ID}", '
        f'environmentId: "{ENVIRONMENT_ID}", '
        f'serviceId: "{service_id}"'
        "}) { edges { node { id status createdAt updatedAt statusUpdatedAt serviceId meta } } } }"
    )
    edges = ((_graphql(token, query).get("deployments") or {}).get("edges") or [])
    return [edge.get("node") or {} for edge in edges]


def _latest_deployment(
    rows: list[dict[str, Any]], status: str | None = None
) -> dict[str, Any] | None:
    candidates = rows if status is None else [row for row in rows if row.get("status") == status]
    if not candidates:
        return None
    return max(candidates, key=lambda row: str(row.get("createdAt") or ""))


def _deployment_summary(deployment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": deployment.get("id"),
        "status": deployment.get("status"),
        "created_at": deployment.get("createdAt"),
        "updated_at": deployment.get("updatedAt"),
        "status_updated_at": deployment.get("statusUpdatedAt"),
        "commit_sha": _commit_from_meta(deployment.get("meta")),
    }


def _commit_from_meta(meta: Any) -> str | None:
    if not isinstance(meta, dict):
        return None
    for key in ("commitHash", "commitSha", "repoCommit"):
        value = meta.get(key)
        if value:
            return str(value)
    return None


def _github_json(token: str, path: str) -> Any:
    _, value = _request_json(
        "https://api.github.com" + path,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ontinuity-B0/1.0",
        },
    )
    return value


def _git_blob(data: bytes) -> str:
    prefix = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def _engine_get(base: str, path: str, diag_key: str, *, allow_error: bool = False) -> tuple[int, Any]:
    return _request_json(
        f"{base.rstrip('/')}{path}",
        headers={"X-Diag-Key": diag_key},
        allow_http_error=allow_error,
    )


def _courier(base: str, op: str, diag_key: str, payload: dict[str, Any]) -> tuple[int, Any]:
    return _request_json(
        f"{base.rstrip('/')}/diag/op/{op}",
        method="POST",
        headers={"X-Diag-Key": diag_key},
        payload=payload,
        allow_http_error=True,
    )


def _workspace_query(base: str, diag_key: str, sql: str) -> Any:
    query = urllib.parse.urlencode({"sql": sql})
    _, result = _request_json(
        f"{base.rstrip('/')}/diag/api/query?{query}",
        headers={"X-Diag-Key": diag_key},
    )
    return result


def _read_railway_token(args: argparse.Namespace) -> str:
    env = os.environ.get("ONTINUITY_RAILWAY_TOKEN", "").strip()
    if env:
        return env
    if not args.llaves:
        raise ReadFailure("set ONTINUITY_RAILWAY_TOKEN or pass --llaves")
    for line in Path(args.llaves).read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("railway token:"):
            token = line.split(":", 1)[1].strip()
            if token:
                return token
    raise ReadFailure("Railway token was not found in the supplied Llaves file")


def _safe_roles(vault: dict[str, str]) -> dict[str, str | None]:
    return {field: vault.get(field) or None for field in ROLE_FIELDS}


def _record_unknown(report: dict[str, Any], field: str, exc: Exception | str) -> None:
    report["unknowns"].append({"field": field, "reason": str(exc)[:240]})


def collect(args: argparse.Namespace) -> dict[str, Any]:
    token = _read_railway_token(args)
    report: dict[str, Any] = {
        "format": "ontinuity-release-baseline/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "repository": {"name": REPOSITORY, "branch": REPOSITORY_BRANCH},
        "services": {},
        "box": {"files": {}},
        "database": {},
        "mailbox": {},
        "public_routes": {},
        "drift": [],
        "unknowns": [],
    }

    vaults: dict[str, dict[str, str]] = {}
    for name, service_id in SERVICES.items():
        try:
            vaults[name] = _vault(token, service_id)
        except Exception as exc:
            _record_unknown(report, f"services.{name}.vault", exc)

    github_token = (vaults.get("main") or {}).get("GITHUB_TOKEN", "")
    repo_blobs: dict[str, str] = {}
    if github_token:
        try:
            user = _github_json(github_token, "/user")
            report["repository"]["authenticated_login"] = user.get("login")
        except Exception as exc:
            _record_unknown(report, "repository.authenticated_login", exc)
        try:
            ref = _github_json(github_token, f"/repos/{REPOSITORY}/git/ref/heads/{REPOSITORY_BRANCH}")
            report["repository"]["main_sha"] = ((ref.get("object") or {}).get("sha"))
        except Exception as exc:
            _record_unknown(report, "repository.main_sha", exc)
        for repo_path in ("app.py", *BOX_REPO_PATHS.values()):
            try:
                item = _github_json(
                    github_token,
                    f"/repos/{REPOSITORY}/contents/{urllib.parse.quote(repo_path)}?ref={REPOSITORY_BRANCH}",
                )
                repo_blobs[repo_path] = str(item.get("sha") or "")
            except Exception as exc:
                _record_unknown(report, f"repository.blobs.{repo_path}", exc)
        report["repository"]["blob_shas"] = repo_blobs
    else:
        _record_unknown(report, "repository.current", "GITHUB_TOKEN absent from MAIN vault")

    for name, service_id in SERVICES.items():
        service: dict[str, Any] = {"service_id": service_id}
        report["services"][name] = service
        vault = vaults.get(name) or {}
        service["roles_from_vault"] = _safe_roles(vault)
        domain = vault.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
        diag_key = vault.get("DIAG_KEY", "").strip()
        if not domain or not diag_key:
            _record_unknown(report, f"services.{name}.engine", "public domain or DIAG_KEY absent")
            continue
        base = domain if domain.startswith("http") else f"https://{domain}"
        service["public_base"] = base
        try:
            deployment_rows = _deployments(token, service_id)
            latest_event = _latest_deployment(deployment_rows)
            latest_success = _latest_deployment(deployment_rows, "SUCCESS")
            if latest_event:
                service["latest_deployment_event"] = _deployment_summary(latest_event)
            if latest_success:
                service["latest_successful_deployment"] = _deployment_summary(latest_success)
            else:
                _record_unknown(report, f"services.{name}.deployment", "no successful deployment rows")
        except Exception as exc:
            _record_unknown(report, f"services.{name}.deployment", exc)
        for label, path in (
            ("version", "/diag/version"),
            ("engine", "/diag/engine"),
            ("health", "/diag/api/health"),
        ):
            try:
                status, value = _engine_get(base, path, diag_key, allow_error=True)
                service[label] = {"http_status": status, "body": value}
                if label == "version" and status == 403:
                    report["drift"].append({
                        "surface": f"{name}.diag.version",
                        "expected": "HTTP 200 with app_py_blob_sha",
                        "observed": "HTTP 403 endpoint not in deployed whitelist",
                    })
                elif status != 200:
                    _record_unknown(report, f"services.{name}.{label}", f"HTTP {status}")
            except Exception as exc:
                _record_unknown(report, f"services.{name}.{label}", exc)
        version = ((service.get("version") or {}).get("body") or {})
        repo_app = repo_blobs.get("app.py")
        live_app = version.get("app_py_blob_sha") if isinstance(version, dict) else None
        if repo_app and live_app and repo_app != live_app:
            report["drift"].append({
                "surface": f"{name}.app.py",
                "repository_blob": repo_app,
                "installed_blob": live_app,
            })

    main = report["services"].get("main") or {}
    main_base = main.get("public_base")
    main_key = (vaults.get("main") or {}).get("DIAG_KEY", "")
    if main_base and main_key:
        try:
            _, handoff = _engine_get(main_base, "/agent/handoff", main_key)
            report["services"]["main"]["handoff"] = handoff
        except Exception as exc:
            _record_unknown(report, "services.main.handoff", exc)

        for filename in BOX_FILES:
            try:
                status, value = _courier(main_base, "read_file", main_key, {"path": filename})
                content = value.get("content") if isinstance(value, dict) else None
                if content is None and isinstance(value, dict):
                    nested = value.get("result")
                    if isinstance(nested, dict):
                        content = nested.get("content")
                if status != 200 or not isinstance(content, str):
                    raise ReadFailure(f"read_file returned HTTP {status} without content")
                raw = content.encode("utf-8")
                installed = _git_blob(raw)
                repo_path = BOX_REPO_PATHS[filename]
                expected = repo_blobs.get(repo_path)
                report["box"]["files"][filename] = {
                    "bytes": len(raw),
                    "git_blob_sha": installed,
                    "repository_path": repo_path,
                    "repository_blob_sha": expected,
                    "state": "MATCH" if expected == installed else "DRIFT" if expected else "UNKNOWN",
                }
                if expected and expected != installed:
                    report["drift"].append({
                        "surface": f"box.{filename}",
                        "repository_blob": expected,
                        "installed_blob": installed,
                    })
            except Exception as exc:
                _record_unknown(report, f"box.files.{filename}", exc)

        queries = {
            "tables": "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            "schema_versions": "SELECT * FROM schema_versions ORDER BY applied_at DESC",
            "session_statuses": "SELECT status, COUNT(*) AS count FROM sessions GROUP BY status ORDER BY status",
            "mailbox_statuses": "SELECT status, kind, COUNT(*) AS count FROM seat_mailbox GROUP BY status, kind ORDER BY status, kind",
            "expired_claims": "SELECT COUNT(*) AS count FROM seat_mailbox WHERE status='claimed' AND lease_until < CURRENT_TIMESTAMP",
        }
        for label, sql in queries.items():
            try:
                result = _workspace_query(main_base, main_key, sql)
                target = report["mailbox"] if label in ("mailbox_statuses", "expired_claims") else report["database"]
                target[label] = result
            except Exception as exc:
                _record_unknown(report, f"database.{label}", exc)

        try:
            status, probe = _courier(main_base, "__probe__", main_key, {"seat": "control"})
            report["services"]["main"]["courier_probe"] = {
                "http_status": status,
                "allowed": probe.get("allowed") if isinstance(probe, dict) else None,
            }
        except Exception as exc:
            _record_unknown(report, "services.main.courier_probe", exc)

    for label, url in {
        "public_site": "https://ontinuity.org/",
        "main_cockpit": (report["services"].get("main") or {}).get("public_base"),
        "farm_root": (report["services"].get("farm") or {}).get("public_base"),
    }.items():
        if not url:
            _record_unknown(report, f"public_routes.{label}", "URL unavailable")
            continue
        try:
            status, _ = _request_json(url, allow_http_error=True)
            report["public_routes"][label] = {"url": url, "http_status": status}
        except ReadFailure:
            # HTML is expected. Re-probe without attempting to parse the body.
            try:
                config = (
                    'silent\nshow-error\nmax-time = 25\nrequest = "GET"\n'
                    f'url = "{url}"\noutput = "/dev/null"\nwrite-out = "%{{http_code}}"\n'
                )
                process = subprocess.run(
                    ["curl", "--config", "-"], input=config, text=True,
                    capture_output=True, timeout=30, check=False,
                )
                if process.returncode != 0:
                    raise ReadFailure(f"curl exit {process.returncode}")
                report["public_routes"][label] = {
                    "url": url,
                    "http_status": int(process.stdout.strip()),
                }
            except Exception as inner:
                _record_unknown(report, f"public_routes.{label}", inner)

    report["result"] = "DRIFT" if report["drift"] else "UNKNOWN" if report["unknowns"] else "MATCH"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llaves", help="credential file containing the Railway project token")
    parser.add_argument("--output", help="also write the redacted JSON report to this path")
    args = parser.parse_args(argv)
    try:
        report = collect(args)
    except Exception as exc:
        report = {
            "format": "ontinuity-release-baseline/v1",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "result": "UNKNOWN",
            "drift": [],
            "unknowns": [{"field": "bootstrap", "reason": str(exc)[:240]}],
        }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(rendered)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    if report.get("drift"):
        return 1
    if report.get("unknowns"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
