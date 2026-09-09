"""
BOX SCOPED OPS — write_file + commit_self.
============================================================================
A Flask blueprint for file_server.py, following the same scoped-op contract as
the existing /op/read_journal + /op/restart_workspace (diag-key gate, bounded
inputs, operations_ledger dual-end logging, one action, fail-safe).

Registered like the others:  app.register_blueprint(box_ops_bp)
Reached from sandbox seats via the relay-courier (/diag/op/write_file,
/diag/op/commit_self) once those names are added to the engine OP_ALLOWED.

WHY:
  - write_file: gives sandbox seats real bounded write hands on the box through
    the courier (the box's existing /write is auth-gated but not a /op/ route,
    so the courier can't reach it; this exposes a bounded write as a named op).
  - commit_self: the box reads its OWN running source files and pushes them to
    the repo, closing the "box code not in version control" provenance hole and
    keeping the repo from ever lagging the box. The GitHub token is passed as a
    bounded arg by the calling seat (which holds it) — NOT stored on the box,
    consistent with the no-credentials-on-box posture.
"""

import os, json, base64, subprocess, secrets, re, stat, tempfile, urllib.parse, urllib.request, urllib.error
from flask import Blueprint, request, jsonify

try:
    from live.box import trusted_deploy
except ImportError:  # installed box layout keeps the modules side by side
    import trusted_deploy

box_ops_bp = Blueprint("box_ops", __name__)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_REPO_DEFAULT = "PatrickKillebrew/ontinuity"
GITHUB_BRANCH_DEFAULT = "main"
_MAX_REPO_READ_BYTES = 2_000_000
_MAX_REPO_API_RESPONSE_BYTES = 3_000_000


def _validated_repo_path(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("path required")
    if (len(value) > 500 or value.startswith("/") or "\\" in value
            or any(ord(character) < 32 or ord(character) == 127
                   for character in value)
            or any(segment in ("", ".", "..") for segment in value.split("/"))):
        raise ValueError("path must be a safe repository-relative path")
    return value


def _validated_repo_slug(value):
    value = (value or "").strip()
    if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/"
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise ValueError("repo must be an owner/name slug")
    return value


def _validated_repo_ref(value):
    value = (value or "").strip()
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", value)
            or ".." in value or value.endswith(".") or value.endswith(".lock")):
        raise ValueError("ref must be a safe branch, tag, or commit name")
    return value

# Files the box is allowed to commit of its OWN source (allowlist, not arbitrary).
# These are the live box server files that belong under version control.
_SELF_SOURCE_ALLOW = {"file_server.py", "seat_mailbox.py", "box_ops.py",
                      "workspace_db_endpoint.py", "db.py", "governor.html",
                      "governor_punchlist.html"}


def _diag_ok():
    try:
        import file_server
        dk = file_server.load_config().get("diag_key", "")
    except Exception:
        dk = os.environ.get("DIAG_KEY", "")
    return bool(dk) and secrets.compare_digest(request.headers.get("X-Diag-Key", ""), dk)


def _authed_identity():
    """Resolve authenticated identity from the scoped relay or key registry.

    A capability call arrives with identity claims derived and signed by MAIN;
    a legacy/operator shared-root recovery call remains unattributed unless the
    file-server registry recognizes a distinct identity key.
    """
    try:
        relay_seat = (request.headers.get("X-Ontinuity-Seat") or "").strip()
        relay_lineage = (request.headers.get("X-Ontinuity-Lineage") or "").strip()
        relay_capability = (request.headers.get("X-Ontinuity-Capability") or "").strip()
        if relay_seat and relay_lineage and relay_capability and _diag_ok():
            return {"seat": relay_seat, "lineage": relay_lineage,
                    "authenticated": True, "mode": "scoped_capability",
                    "capability_id": relay_capability}
        import file_server
        presented = request.headers.get("X-Diag-Key", "")
        return file_server.authenticate_identity(presented)
    except Exception:
        return None


def _identity_seat(body_seat=None):
    """The seat to TRUST for this request. Prefer server-authenticated identity;
    otherwise (legacy/operator shared-root mode) fall back to the body-supplied
    seat (honest-but-asserted, CALLER-1 semantics).
    This is the single chokepoint every identity-reading route routes through, so
    the migration is one helper, not N edits."""
    ident = _authed_identity()
    if ident and ident.get("authenticated"):
        return ident.get("seat"), ident.get("lineage"), True   # authenticated, body IGNORED
    # shared-key back-compat: trust the body field, flagged not-authenticated
    return (body_seat or "").strip() or None, None, False


def _caller_seat(default="diag-key"):
    """Seat name for operations_ledger.caller. Prefers server-authenticated
    identity; falls back to the self-asserted body seat only in legacy/operator
    shared-root mode. Falls back to 'diag-key' when
    the op carries no seat (write_file/read_file have none)."""
    try:
        b = request.get_json(silent=True) or {}
        body_seat = (b.get("seat") or b.get("from_seat") or "").strip()
        seat, lineage, authed = _identity_seat(body_seat)
        if seat and authed:
            return "seat:" + seat + " (auth)"
        return ("seat:" + seat) if seat else default
    except Exception:
        return default

def _ledger_begin(op, args):
    try:
        import file_server
        # caller = self-asserted seat (trusted-not-authenticated; see _caller_seat)
        return file_server._ops_begin(op, "REVIEW", _caller_seat(), request.remote_addr, args)
    except Exception:
        return None


def _ledger_finish(op_id, status, result=""):
    try:
        import file_server
        file_server._ops_finish(op_id, status, result)
    except Exception:
        pass


def _safe_box_path(name):
    """Resolve name against the box dir; refuse traversal."""
    if not isinstance(name, str) or not name or os.path.isabs(name):
        return None
    base = os.path.realpath(_BASE_DIR)
    full = os.path.abspath(os.path.join(base, name))
    try:
        if os.path.commonpath((base, full)) != base or full == base:
            return None
        parent = os.path.realpath(os.path.dirname(full))
        if os.path.commonpath((base, parent)) != base:
            return None
        if os.path.lexists(full) and not stat.S_ISREG(os.lstat(full).st_mode):
            return None
    except ValueError:
        return None
    return full


def _read_private_regular(path):
    """Read the prior private config without following or blocking on special files."""
    if not os.path.lexists(path):
        return None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("trusted deploy config target must be a regular file")
        data = os.read(fd, trusted_deploy._MAX_CONFIG_BYTES + 1)
        if len(data) > trusted_deploy._MAX_CONFIG_BYTES:
            raise ValueError("existing trusted deploy config is oversized")
        return data.decode("utf-8")
    finally:
        os.close(fd)


def _write_private_atomic(path, content):
    """Install validated config privately and atomically in its trusted directory."""
    parent = os.path.dirname(path)
    os.makedirs(parent, mode=0o700, exist_ok=True)
    old = _read_private_regular(path)
    fd, temporary = tempfile.mkstemp(prefix=".trusted-deploy-config-", dir=parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        directory_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return old
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


@box_ops_bp.route("/op/write_file", methods=["POST"])
def op_write_file():
    """Bounded write: a file inside the box project dir only. Mirrors /write but
    as a scoped op the courier can forward. Records via the box's own
    record_change if available."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    name = (b.get("path") or "").strip()
    content = b.get("content")
    if not name or content is None:
        return jsonify({"error": "path and content required"}), 400
    full = _safe_box_path(name)
    if not full:
        return jsonify({"error": "path traversal rejected"}), 403
    canonical_name = os.path.relpath(full, os.path.realpath(_BASE_DIR)).replace(os.sep, "/")
    private_trusted_config = (
        os.path.normcase(full)
        == os.path.normcase(os.path.abspath(trusted_deploy.TRUSTED_CONFIG_PATH))
    )
    if private_trusted_config:
        try:
            trusted_deploy.validate_config_document(content)
        except trusted_deploy.DeployError as exc:
            return jsonify({"error": str(exc)}), 400
    op_id = _ledger_begin("write_file", {"path": canonical_name, "bytes": len(str(content))})
    try:
        if private_trusted_config:
            old = _write_private_atomic(full, content)
        else:
            old = None
            if os.path.exists(full):
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    old = f.read()
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
        # record in the box's change history if file_server exposes it
        try:
            import file_server
            file_server.record_change(canonical_name, old, content, b.get("description", "via /op/write_file"))
        except Exception:
            pass
        _ledger_finish(op_id, "ok", f"wrote {len(content)} bytes to {canonical_name}")
        return jsonify({"ok": True, "path": canonical_name, "bytes": len(content)})
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@box_ops_bp.route("/op/commit_self", methods=["POST"])
def op_commit_self():
    """Read the box's own allowlisted source files and commit them to the repo
    via the GitHub contents API. Token passed as a bounded arg (not stored on
    box). Closes the box-code-not-in-VC provenance hole, repeatably."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    token = (b.get("github_token") or "").strip()
    if not token:
        return jsonify({"error": "github_token required (passed by caller; not stored on box)"}), 400
    repo = (b.get("repo") or GITHUB_REPO_DEFAULT).strip()
    branch = (b.get("branch") or GITHUB_BRANCH_DEFAULT).strip()
    repo_dir = (b.get("repo_dir") or "live/box").strip().strip("/")  # where in the repo box files live
    # which files to commit: requested subset (allowlisted) or all present allowlisted
    req_files = b.get("files")
    files = [f for f in (req_files or sorted(_SELF_SOURCE_ALLOW)) if f in _SELF_SOURCE_ALLOW]
    if not files:
        return jsonify({"error": "no allowlisted files to commit", "allowed": sorted(_SELF_SOURCE_ALLOW)}), 400
    op_id = _ledger_begin("commit_self", {"repo": repo, "files": files})
    committed, skipped = [], []
    try:
        for name in files:
            full = _safe_box_path(name)
            if not full or not os.path.exists(full):
                skipped.append(name); continue
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            path_in_repo = f"{repo_dir}/{name}"
            url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
            # get existing sha if present
            sha = None
            try:
                gr = urllib.request.Request(url + f"?ref={branch}", headers={
                    "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
                with _NO_REDIRECT_OPENER.open(gr, timeout=20) as r:
                    sha = json.loads(r.read()).get("sha")
            except Exception:
                pass
            body = {"message": f"commit_self: box source {name} ({path_in_repo})",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": branch}
            if sha:
                body["sha"] = sha
            pr = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                         "Content-Type": "application/json"})
            with _NO_REDIRECT_OPENER.open(pr, timeout=30) as r:
                res = json.loads(r.read())
                committed.append({"file": name, "sha": res.get("content", {}).get("sha", "")[:12]})
        _ledger_finish(op_id, "ok", f"committed {len(committed)}, skipped {len(skipped)}")
        return jsonify({"ok": True, "committed": committed, "skipped": skipped})
    except urllib.error.HTTPError as e:
        _ledger_finish(op_id, "fail", f"github {e.code}")
        return jsonify({"error": f"github {e.code}: {e.read().decode()[:200]}", "committed": committed}), 502
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200], "committed": committed}), 500


@box_ops_bp.route("/op/read_file", methods=["POST"])
def op_read_file():
    """Bounded read: return the content of a file INSIDE the box project dir.
    Mirror of write_file. Closes the retrieval gap — an artifact a sandbox seat
    wrote to the box (via write_file) can now be read back through the courier.
    SAFE (read-only)."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    name = (b.get("path") or "").strip()
    if not name:
        return jsonify({"error": "path required"}), 400
    full = _safe_box_path(name)
    if not full:
        return jsonify({"error": "path traversal rejected"}), 403
    op_id = _ledger_begin("read_file", {"path": name})
    try:
        if not os.path.exists(full):
            _ledger_finish(op_id, "fail", "not found")
            return jsonify({"error": "not found", "path": name}), 404
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        _ledger_finish(op_id, "ok", f"read {len(content)} bytes from {name}")
        return jsonify({"ok": True, "path": name, "bytes": len(content), "content": content})
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@box_ops_bp.route("/op/commit_file", methods=["POST"])
def op_commit_file():
    """Commit an ARBITRARY file from the box project dir to the repo via the
    GitHub contents API. Generalizes commit_self (which is limited to the box's
    own source allowlist) so a worker's artifact staged on the box (e.g. a new
    live/specs/*.md) can be pushed to version control. Token passed as a bounded
    CALLER arg, never stored on the box. The repo path defaults to the same
    relative path as on the box, so a file written to the box at
    live/specs/x.md commits to live/specs/x.md in the repo. REVIEW tier."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    token = (b.get("github_token") or "").strip()
    if not token:
        return jsonify({"error": "github_token required (passed by caller; not stored on box)"}), 400
    name = (b.get("path") or "").strip()
    if not name:
        return jsonify({"error": "path required"}), 400
    full = _safe_box_path(name)
    if not full:
        return jsonify({"error": "path traversal rejected"}), 403
    if not os.path.exists(full):
        return jsonify({"error": "not found on box", "path": name}), 404
    repo = (b.get("repo") or GITHUB_REPO_DEFAULT).strip()
    branch = (b.get("branch") or GITHUB_BRANCH_DEFAULT).strip()
    # repo path defaults to the same relative path the file has on the box
    path_in_repo = (b.get("repo_path") or name).strip().lstrip("/")
    message = (b.get("message") or f"commit_file: {path_in_repo}").strip()
    op_id = _ledger_begin("commit_file", {"path": name, "repo_path": path_in_repo, "repo": repo})
    try:
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
        sha = None
        try:
            gr = urllib.request.Request(url + f"?ref={branch}", headers={
                "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
            with _NO_REDIRECT_OPENER.open(gr, timeout=20) as r:
                sha = json.loads(r.read()).get("sha")
        except Exception:
            pass
        body = {"message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch}
        if sha:
            body["sha"] = sha
        pr = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"})
        with _NO_REDIRECT_OPENER.open(pr, timeout=30) as r:
            res = json.loads(r.read())
            commit_sha = res.get("commit", {}).get("sha", "")
        _ledger_finish(op_id, "ok", f"committed {path_in_repo} {commit_sha[:12]}")
        return jsonify({"ok": True, "repo_path": path_in_repo, "commit_sha": commit_sha})
    except urllib.error.HTTPError as e:
        _ledger_finish(op_id, "fail", f"github {e.code}")
        return jsonify({"error": f"github {e.code}: {e.read().decode()[:200]}"}), 502
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@box_ops_bp.route("/op/backup_db", methods=["POST"])
def op_backup_db():
    """Produce a CONSISTENT plain-text .sql dump of the live ontinuity.db and
    write it to the box project dir, so the existing text-only commit_file can
    ship it to a (private) repo. Solves the binary problem: read_file/commit_file
    are UTF-8 text ops and cannot carry the raw .db; a .sql dump is text, diffs
    in git, and is restore-portable across SQLite versions. Uses sqlite3's
    online .backup first (a consistent snapshot even if the DB is mid-write),
    then .dump on the snapshot. SAFE (read-only against the live DB). Returns the
    box path of the written dump; the caller then commits it via commit_file.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    db_path = os.environ.get("ONTINUITY_DB_PATH",
                             os.path.join(_BASE_DIR, "ontinuity.db"))
    if not os.path.exists(db_path):
        return jsonify({"error": "db not found", "path": db_path}), 404
    out_name = (b.get("out") or "backups/ontinuity_dump.sql").strip().lstrip("/")
    out_full = _safe_box_path(out_name)
    if not out_full:
        return jsonify({"error": "path traversal rejected"}), 403
    op_id = _ledger_begin("backup_db", {"db": db_path, "out": out_name})
    snap = out_full + ".snap"
    try:
        import sqlite3
        os.makedirs(os.path.dirname(out_full) or ".", exist_ok=True)
        # 1) consistent online snapshot via the backup API (safe even mid-write)
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(snap)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        # 2) text dump of the snapshot via iterdump (== sqlite3 .dump output)
        conn = sqlite3.connect(snap)
        dump_bytes = 0
        with open(out_full, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(line + "\n")
                dump_bytes += len(line) + 1
        conn.close()
        try:
            os.remove(snap)
        except Exception:
            pass
        _ledger_finish(op_id, "ok", f"dumped {dump_bytes} bytes to {out_name}")
        return jsonify({"ok": True, "path": out_name, "bytes": dump_bytes,
                        "db": db_path, "note": "commit with commit_file to a PRIVATE repo"})
    except Exception as e:
        try:
            if os.path.exists(snap):
                os.remove(snap)
        except Exception:
            pass
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@box_ops_bp.route("/op/read_repo", methods=["POST"])
def op_read_repo():
    """Read ANY file from the repo and return its content, so a worker can read
    repo files (incl. app.py, which is engine-side and NOT a box file, so read_file
    can't reach it) without depending on sandbox web-fetch (which rate-limits on the
    shared egress IP). SAFE tier, read-only. Bounded input: a repo path (+ optional
    ref/branch, + optional github_token to force the authoritative API read).

    SOURCE ORDER (first success wins; the response says which served it):
      1. If github_token supplied -> GitHub contents API (authoritative, freshest,
         no staleness) from the box egress.
      2. raw.githubusercontent.com with a cache-bust query param (no rate limit;
         cache-bust mitigates the known stale-CDN trap for hot files).
      3. Unauthenticated GitHub contents API (box egress 60/hr bucket) as a last
         resort if raw is unreachable.
    The box stores NO token (no-credentials posture); auth is only ever a caller arg.

    WHY BOX-SIDE (not engine-side): every scoped op is box-side so it logs to the
    operations_ledger natively (_ops_begin/_ops_finish live in file_server on the
    box; app.py has no ledger writer). An engine-local op would have to skip the
    ledger or call back to the box to log. Keeping read_repo box-side preserves the
    uniform contract. Trade-off: without a caller token the box reads via raw-CDN
    (staleness-mitigated by cache-bust) rather than the authenticated API. An
    operator-root recovery call may pass github_token when it needs the
    guaranteed-fresh API read. Capability callers are fixed to the public
    Ontinuity repository, cannot supply repository credentials, and receive at
    most 2 MB.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    if not isinstance(b, dict):
        return jsonify({"error": "request must be a JSON object"}), 400
    if not all(isinstance(b.get(field, ""), str)
               for field in ("path", "repo", "ref", "branch", "github_token")):
        return jsonify({"error": "repository read fields must be strings"}), 400
    try:
        path_in_repo = _validated_repo_path(b.get("path"))
        repo = _validated_repo_slug(b.get("repo") or GITHUB_REPO_DEFAULT)
        branch = _validated_repo_ref(
            b.get("ref") or b.get("branch") or GITHUB_BRANCH_DEFAULT)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    token = (b.get("github_token") or "").strip()
    identity = _authed_identity()
    if identity and identity.get("authenticated"):
        if repo != GITHUB_REPO_DEFAULT:
            return jsonify({"error": "capability repository scope is fixed"}), 403
        if token:
            return jsonify({"error": "capability callers may not supply repository credentials"}), 403
    op_id = _ledger_begin("read_repo", {"path": path_in_repo, "repo": repo, "ref": branch,
                                        "auth": bool(token)})

    quoted_repo = urllib.parse.quote(repo, safe="/")
    quoted_path = urllib.parse.quote(path_in_repo, safe="/")
    quoted_ref = urllib.parse.quote(branch, safe="")

    def _via_api(tok):
        query = urllib.parse.urlencode({"ref": branch})
        url = f"https://api.github.com/repos/{quoted_repo}/contents/{quoted_path}?{query}"
        hdrs = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if tok:
            hdrs["Authorization"] = f"Bearer {tok}"
        req = urllib.request.Request(url, headers=hdrs)
        with _NO_REDIRECT_OPENER.open(req, timeout=30) as r:
            raw_response = r.read(_MAX_REPO_API_RESPONSE_BYTES + 1)
        if len(raw_response) > _MAX_REPO_API_RESPONSE_BYTES:
            raise ValueError("repository API response exceeds read limit")
        data = json.loads(raw_response.decode())
        decoded = base64.b64decode(data["content"])
        if len(decoded) > _MAX_REPO_READ_BYTES:
            raise ValueError("repository file exceeds read limit")
        return decoded.decode("utf-8", "replace")

    def _via_raw():
        import time as _t
        url = (f"https://raw.githubusercontent.com/{quoted_repo}/{quoted_ref}/{quoted_path}"
               f"?cb={int(_t.time())}")
        req = urllib.request.Request(url)
        with _NO_REDIRECT_OPENER.open(req, timeout=30) as r:
            raw = r.read(_MAX_REPO_READ_BYTES + 1)
        if len(raw) > _MAX_REPO_READ_BYTES:
            raise ValueError("repository file exceeds read limit")
        return raw.decode("utf-8", "replace")

    attempts = []
    # 1) authoritative API if a token was supplied
    if token:
        try:
            content = _via_api(token)
            _ledger_finish(op_id, "ok", f"api(auth) {path_in_repo} {len(content)}b")
            return jsonify({"ok": True, "path": path_in_repo, "ref": branch,
                            "source": "github_api_authenticated", "bytes": len(content),
                            "content": content})
        except Exception as e:
            attempts.append(f"api(auth): {str(e)[:80]}")
    # 2) raw CDN with cache-bust
    try:
        content = _via_raw()
        _ledger_finish(op_id, "ok", f"raw {path_in_repo} {len(content)}b")
        return jsonify({"ok": True, "path": path_in_repo, "ref": branch,
                        "source": "raw_cdn_cachebust", "bytes": len(content),
                        "content": content,
                        "note": "cache-busted public read; authenticated repository reads are operator-recovery-only"})
    except Exception as e:
        attempts.append(f"raw: {str(e)[:80]}")
    # 3) unauthenticated API last resort
    try:
        content = _via_api("")
        _ledger_finish(op_id, "ok", f"api(unauth) {path_in_repo} {len(content)}b")
        return jsonify({"ok": True, "path": path_in_repo, "ref": branch,
                        "source": "github_api_unauthenticated", "bytes": len(content),
                        "content": content})
    except Exception as e:
        attempts.append(f"api(unauth): {str(e)[:80]}")

    _ledger_finish(op_id, "fail", "; ".join(attempts)[:200])
    return jsonify({"error": "all sources failed", "attempts": attempts,
                    "path": path_in_repo}), 502


# ---------------------------------------------------------------------------
# bootstrap_gate — verified bootstrap gate, step 2 (the courier op)
# Spec: live/specs/verified_bootstrap_gate.md. Wraps the sandbox-local runnable
# (live/bootstrap/gate.py, BOOTGATE-2) as a SERVER-SIDE op so a seat self-gates
# through the courier and the box LOGS the pass/fail to operations_ledger — the
# audit evidence that an acting seat proved orientation before acting.
# ---------------------------------------------------------------------------
import importlib.util as _ilu

_gate_mod = None
def _load_gate():
    """Import the committed gate runnable from the box's repo checkout.
    Cached. The file lives at live/bootstrap/gate.py on the box (verified present)."""
    global _gate_mod
    if _gate_mod is not None:
        return _gate_mod
    path = os.path.join(_BASE_DIR, "live", "bootstrap", "gate.py")
    if not os.path.exists(path):
        # fallback: some box layouts keep it alongside box_ops.py
        alt = os.path.join(_BASE_DIR, "gate.py")
        path = alt if os.path.exists(alt) else path
    spec = _ilu.spec_from_file_location("ontinuity_bootstrap_gate", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _gate_mod = mod
    return mod


@box_ops_bp.route("/op/bootstrap_gate", methods=["POST"])
def op_bootstrap_gate():
    """Run the verified bootstrap gate server-side for {seat, role} and return the
    structured {oriented, checks, ...} result. SAFE tier (read-only checks). Logs a
    bootstrap_gate row to operations_ledger (dual-end) as the audit evidence that
    a seat proved orientation. Capability issuance happens only at MAIN admission;
    this gate never returns or claims to issue a root or replacement credential.

    Body: {seat (req in shared-key compatibility mode),
           role ('worker'|'control', default 'worker'), lineage (str),
           seat_invariants ({key->text} for CHECK 6 MECHANICS)}.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    asserted_seat = (b.get("seat") or "").strip()
    asserted_lineage = (b.get("lineage") or "").strip()
    identity = _authed_identity()
    if identity and identity.get("authenticated"):
        seat = (identity.get("seat") or "").strip()
        lineage = (identity.get("lineage") or "").strip()
        if asserted_seat and asserted_seat != seat:
            return jsonify({"error": "seat identity mismatch"}), 409
        if asserted_lineage and asserted_lineage != lineage:
            return jsonify({"error": "lineage identity mismatch"}), 409
    else:
        seat = asserted_seat
        lineage = asserted_lineage
    if not seat:
        return jsonify({"error": "seat required"}), 400
    role = (b.get("role") or "worker").strip()
    if role not in ("worker", "control"):
        return jsonify({"error": "role must be 'worker' or 'control'"}), 400
    seat_invariants = b.get("seat_invariants") or {}
    canonical = request.headers.get("X-Ontinuity-Courier-Count", "")
    op_id = _ledger_begin("bootstrap_gate", {"seat": seat, "role": role})
    try:
        gate = _load_gate()
        # MAIN derives the normal value from its actual OP_ALLOWED set. Direct
        # operator recovery uses the committed server fallback; body data never
        # selects the certification standard.
        if canonical:
            derived_count = int(canonical)
            if derived_count < 1:
                raise ValueError("invalid courier operation count")
            gate.CANONICAL_COURIER_OP_COUNT = derived_count
        # The box holds the box diag-key in config; pass it so the gate's corpus/
        # hands/engine checks authenticate through the relay exactly as a seat would.
        try:
            import file_server
            diag_key = file_server.load_config().get("diag_key", "") or os.environ.get("DIAG_KEY", "")
        except Exception:
            diag_key = os.environ.get("DIAG_KEY", "")
        result = gate.run_gate(
            seat, lineage, role=role, diag_key=diag_key,
            seat_invariants=seat_invariants,
            relay_identity=(identity if identity and identity.get("authenticated") else None),
        )

        result["admission"] = {
            "capability_validated": bool(identity and identity.get("authenticated")),
            "bound_to": {"seat": seat, "lineage": lineage},
        }

        status = "ok" if result.get("oriented") else "fail"
        # summarize the failing check (if any) for the ledger
        failed = next((c for c in result.get("checks", []) if not c.get("pass")), None)
        detail = (f"oriented seat={seat} role={role}" if result.get("oriented")
                  else f"NOT ORIENTED seat={seat} role={role} at "
                       f"{failed.get('name') if failed else '?'}")
        _ledger_finish(op_id, status, detail[:200])
        return jsonify(result)
    except Exception as e:
        _ledger_finish(op_id, "fail", f"gate error: {str(e)[:180]}")
        return jsonify({"error": f"bootstrap_gate error: {str(e)[:200]}"}), 500


# ---------------------------------------------------------------------------
# deploy — worker propose->sign-off->DEPLOY chain (operator ruling: a seat that
# SIGNS OFF a peer's proposal may DEPLOY it; stop routing all deploys through
# control). Design corpus 160 (self-enforcing gate) / 244 / 307 (review findings
# evaporate -> capture them) / 412 / 438, + KEYS-1.
# ---------------------------------------------------------------------------
# THE TWO-PARTY RULE, ENFORCED STRUCTURALLY: a deploy is authorized ONLY if the
# referenced block has a `signoff` from a seat DIFFERENT from the `proposal`
# author. A self-signed or unsigned deploy is REFUSED and writes a gate_violation
# record. This reuses NOSELF-1's author_seat/author_lineage — the same authorship
# spine, now gating deploy instead of just review-claim.
#
# LEGACY/OPERATOR SHARED-ROOT CAVEAT:
# the seat identities this rule compares (proposal author, signoff sender) are
# SELF-ASSERTED body fields under one shared DIAG_KEY. So today any diag-key
# holder could forge a distinct from_seat on a signoff and satisfy the two-party
# check. This op enforces the STRUCTURE (signer != author) correctly; the
# STRENGTH of that enforcement is bounded by authentication. Scoped capability
# calls already carry MAIN-derived identity and do not trust these body fields;
# direct legacy/operator recovery calls retain the honest-name assumption. Every
# call is logged.
#
# Hosting credentials and provider protocol remain inside trusted_deploy. The
# caller-facing operation is provider-neutral and accepts only action, target,
# signoff_block_id, and commit_sha.
_PROVENANCE_LEDGER = os.path.join(_BASE_DIR, "live", "provenance_ledger.jsonl")
_DEPLOY_REQUEST_MAX_BYTES = 4096


def _strict_deploy_body():
    """Read the deploy tuple under the exact raw HTTP contract."""
    if request.args or request.mimetype != "application/json":
        raise trusted_deploy.DeployError(
            "deploy requires application/json without query parameters")
    if (request.content_length is not None
            and request.content_length > _DEPLOY_REQUEST_MAX_BYTES):
        raise trusted_deploy.DeployError("deploy request body is too large", 413)
    raw = request.stream.read(_DEPLOY_REQUEST_MAX_BYTES + 1)
    if len(raw) > _DEPLOY_REQUEST_MAX_BYTES:
        raise trusted_deploy.DeployError("deploy request body is too large", 413)
    try:
        def reject_duplicates(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate JSON key")
                value[key] = item
            return value
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise trusted_deploy.DeployError(
            "deploy request body is not valid JSON") from exc


def _prov_append(record):
    """Append one lifecycle record to the JSONL provenance ledger (source of truth;
    DB deferred, per punch-list). Captures proposal->review->signoff->deploy->result
    so review findings stop evaporating (design line 307). Best-effort; never blocks."""
    try:
        os.makedirs(os.path.dirname(_PROVENANCE_LEDGER), exist_ok=True)
        record["logged_at"] = _now_iso()
        with open(_PROVENANCE_LEDGER, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _deploy_authorization_refs(target, commit_sha):
    """Canonical mailbox refs that authorize this logical target and commit."""
    return {
        f"deploy:v1:{target}:{commit_sha}",
        f"deploy:v1:both:{commit_sha}",
    }


def _twoparty_check(block_id, target, commit_sha):
    """Inspect the mailbox for block_id. Returns (ok, detail, author, signer).
    ok=True iff proposal and signoff carry the same canonical deploy ref for the
    requested target+commit and the signer differs from the proposal author.
    Uses seat_mailbox._mb_conn."""
    try:
        import seat_mailbox
        c = seat_mailbox._mb_conn()
    except Exception as e:
        return False, f"cannot reach mailbox: {str(e)[:80]}", None, None
    try:
        # the authored work: prefer the proposal row's author_seat (NOSELF-1),
        # falling back to its from_seat.
        prop = c.execute(
            "SELECT COALESCE(author_seat, from_seat), "
            "COALESCE(author_lineage, from_lineage), ref "
            "FROM seat_mailbox WHERE block_id=? AND kind='proposal' "
            "ORDER BY created_at ASC LIMIT 1", (block_id,)).fetchone()
        # the sign-off: a 'signoff' kind row for this block.
        sign = c.execute(
            "SELECT from_seat, from_lineage, ref FROM seat_mailbox "
            "WHERE block_id=? AND kind='signoff' "
            "ORDER BY created_at DESC LIMIT 1", (block_id,)).fetchone()
        c.close()
    except Exception as e:
        try: c.close()
        except Exception: pass
        return False, f"mailbox query error: {str(e)[:80]}", None, None
    if not prop:
        return False, f"no proposal found for block {block_id}", None, None
    if not sign:
        return False, f"no signoff found for block {block_id} (unsigned deploy refused)", \
               {"seat": prop[0], "lineage": prop[1], "ref": prop[2]}, None
    author = {"seat": prop[0], "lineage": prop[1], "ref": prop[2]}
    signer = {"seat": sign[0], "lineage": sign[1], "ref": sign[2]}
    allowed_refs = _deploy_authorization_refs(target, commit_sha)
    if not author["ref"] or author["ref"] != signer["ref"]:
        return False, (
            "proposal and signoff do not carry the same deploy authorization ref"
        ), author, signer
    if author["ref"] not in allowed_refs:
        return False, (
            "signed deploy authorization ref does not match requested target and commit"
        ), author, signer
    # TWO-PARTY: the signer must be a DIFFERENT SEAT than the author. Two distinct
    # seats are two parties even when they share a model lineage (worker1 and worker2
    # are both claude:opus-4.8 — that is the normal two-worker case and MUST be
    # allowed). We refuse on SAME SEAT only. (An earlier draft also refused on
    # same-lineage, which would wrongly block the legitimate two-worker case.)
    # Scoped capability calls use MAIN-derived seats. In direct legacy/operator
    # shared-root recovery, the seat field remains self-asserted, so a keyholder
    # could present a different from_seat to fake distinctness.
    if (author["seat"] or "") == (signer["seat"] or "") and author["seat"]:
        return False, (f"self-sign-off: author seat={author['seat']} == signer seat "
                       f"{signer['seat']} — two-party rule violated"), author, signer
    return True, (
        "two-party satisfied for exact signed target and commit"
    ), author, signer


@box_ops_bp.route("/op/deploy", methods=["POST"])
def op_deploy():
    """Two-phase exact-commit deploy through the trusted box-side adapter.

    ``start`` performs at most one provider mutation for the deterministic
    block+target+commit tuple. ``status`` recovers that tuple without accepting a
    caller-supplied provider deployment identifier. Both phases retain the
    existing two-party signer gate.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    try:
        body = _strict_deploy_body()
        action, target, block_id, commit_sha = trusted_deploy.validate_request(body)
    except trusted_deploy.DeployError as exc:
        return jsonify({"error": str(exc)}), exc.status

    caller = _caller_seat()
    op_id = _ledger_begin("deploy", {
        "action": action, "target": target, "block": block_id,
        "commit_sha": commit_sha,
    })
    if op_id is None:
        return jsonify({"error": "deploy ledger is unavailable"}), 503

    ledger_status = "fail"
    ledger_result = "deploy failed"
    try:
        ok, detail, author, signer = _twoparty_check(
            block_id, target, commit_sha)
        if not ok:
            _prov_append({
                "kind": "gate_violation", "block_id": block_id,
                "target": target, "caller": caller, "reason": detail,
                "author": author, "signer": signer, "commit_sha": commit_sha,
            })
            ledger_result = "two-party refused"
            return jsonify({
                "error": "deploy refused — two-party rule", "detail": detail,
                "author": author, "signer": signer,
            }), 403

        identity = _authed_identity()
        if (identity and identity.get("authenticated") and signer
                and (identity.get("seat") or "") != (signer.get("seat") or "")):
            _prov_append({
                "kind": "gate_violation", "block_id": block_id,
                "target": target, "caller": "auth:" + str(identity.get("seat")),
                "reason": "authenticated deploy caller differs from signer",
                "author": author, "signer": signer, "commit_sha": commit_sha,
            })
            ledger_result = "caller differs from signer"
            return jsonify({
                "error": "deploy refused — caller is not the signer",
                "caller": identity.get("seat"), "signer": signer,
            }), 403

        if action == "start":
            result, provider_mutated = trusted_deploy.start(
                block_id, target, commit_sha
            )
            _prov_append({
                "kind": "deploy_accepted" if provider_mutated else "deploy_replayed",
                "block_id": block_id, "target": target, "caller": caller,
                "author": author, "signer": signer, "commit_sha": commit_sha,
                "tracking_id": result["tracking_id"],
            })
            ledger_status = "ok" if result["ok"] else "fail"
            ledger_result = ("deploy accepted" if provider_mutated else
                             "deploy replayed " + result["action_state"])
            status_code = 200 if result["ok"] else 502
            return jsonify({**result, "two_party": {
                "author": author, "signer": signer}}), status_code

        result, newly_terminal = trusted_deploy.status(
            block_id, target, commit_sha
        )
        if newly_terminal:
            _prov_append({
                "kind": "deploy_result", "block_id": block_id,
                "target": target, "caller": caller, "author": author,
                "signer": signer, "commit_sha": commit_sha,
                "tracking_id": result["tracking_id"],
                "outcome": result["action_state"],
            })
        ledger_status = "ok" if result["ok"] else "fail"
        ledger_result = "deploy status " + result["action_state"]
        status_code = 200 if result["ok"] else 502
        return jsonify({**result, "two_party": {"author": author, "signer": signer}}), status_code
    except trusted_deploy.DeployError as exc:
        ledger_result = "deploy adapter refused request"
        return jsonify({"error": str(exc)}), exc.status
    except Exception:
        ledger_result = "deploy internal failure"
        return jsonify({"error": "deploy internal failure"}), 500
    finally:
        _ledger_finish(op_id, ledger_status, ledger_result)
