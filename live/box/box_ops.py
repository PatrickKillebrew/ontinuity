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

import os, json, base64, subprocess, secrets, urllib.request, urllib.error
from flask import Blueprint, request, jsonify

box_ops_bp = Blueprint("box_ops", __name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_REPO_DEFAULT = "PatrickKillebrew/ontinuity"
GITHUB_BRANCH_DEFAULT = "main"

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


def _ledger_begin(op, args):
    try:
        import file_server
        return file_server._ops_begin(op, "REVIEW", "diag-key", request.remote_addr, args)
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
    full = os.path.normpath(os.path.join(_BASE_DIR, name))
    return full if full.startswith(os.path.normpath(_BASE_DIR)) else None


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
    op_id = _ledger_begin("write_file", {"path": name, "bytes": len(str(content))})
    try:
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
            file_server.record_change(name, old, content, b.get("description", "via /op/write_file"))
        except Exception:
            pass
        _ledger_finish(op_id, "ok", f"wrote {len(content)} bytes to {name}")
        return jsonify({"ok": True, "path": name, "bytes": len(content)})
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
                with urllib.request.urlopen(gr, timeout=20) as r:
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
            with urllib.request.urlopen(pr, timeout=30) as r:
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
            with urllib.request.urlopen(gr, timeout=20) as r:
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
        with urllib.request.urlopen(pr, timeout=30) as r:
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
