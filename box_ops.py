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
    (staleness-mitigated by cache-bust) rather than the authenticated API. Pass
    github_token when you need the guaranteed-fresh authoritative read.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    path_in_repo = (b.get("path") or "").strip().lstrip("/")
    if not path_in_repo:
        return jsonify({"error": "path required"}), 400
    repo = (b.get("repo") or GITHUB_REPO_DEFAULT).strip()
    branch = (b.get("ref") or b.get("branch") or GITHUB_BRANCH_DEFAULT).strip()
    token = (b.get("github_token") or "").strip()
    op_id = _ledger_begin("read_repo", {"path": path_in_repo, "repo": repo, "ref": branch,
                                        "auth": bool(token)})

    def _via_api(tok):
        url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}?ref={branch}"
        hdrs = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if tok:
            hdrs["Authorization"] = f"Bearer {tok}"
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return base64.b64decode(data["content"]).decode("utf-8", "replace")

    def _via_raw():
        import time as _t
        url = (f"https://raw.githubusercontent.com/{repo}/{branch}/{path_in_repo}"
               f"?cb={int(_t.time())}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")

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
                        "note": "raw CDN; pass github_token for the guaranteed-fresh authoritative read"})
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

# Canonical CHECK-1 courier-allowlist count. SOURCE OF TRUTH is app.py OP_ALLOWED.
# 14 entries now; becomes 15 when THIS op (bootstrap_gate) is added to OP_ALLOWED.
# The op accepts an override in the body so control can bump it in the same commit
# that lands the OP_ALLOWED entry (gate CHECK-1 currency); default tracks the
# post-this-op value so a fresh seat checks against the right number once deployed.
_GATE_CANONICAL_OP_COUNT = 15

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
    structured {oriented, checks, ...} result. SAFE tier (read-only checks + a
    mailbox_peek hand-probe; same mutation class as mailbox_peek — none). Logs a
    bootstrap_gate row to operations_ledger (dual-end) as the audit evidence that
    a seat proved orientation. On oriented:true, issues a per-identity key —
    STUBBED to the shared DIAG_KEY for now (real per-seat keys arrive with the key
    build); the issuance block is structured so real keys hook in without changing
    the contract.

    Body: {seat (req), role ('worker'|'control', default 'worker'),
           lineage (str), seat_invariants ({key->text} for CHECK 6 MECHANICS),
           canonical_op_count (int, optional override for CHECK 1)}.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    seat = (b.get("seat") or "").strip()
    if not seat:
        return jsonify({"error": "seat required"}), 400
    role = (b.get("role") or "worker").strip()
    if role not in ("worker", "control"):
        return jsonify({"error": "role must be 'worker' or 'control'"}), 400
    lineage = (b.get("lineage") or "").strip()
    seat_invariants = b.get("seat_invariants") or {}
    canonical = b.get("canonical_op_count")
    op_id = _ledger_begin("bootstrap_gate", {"seat": seat, "role": role})
    try:
        gate = _load_gate()
        # Set CHECK-1 canonical to the current courier-allowlist length. Override
        # from the body wins; else the post-this-op default (15).
        gate.CANONICAL_COURIER_OP_COUNT = int(canonical) if canonical is not None else _GATE_CANONICAL_OP_COUNT
        # The box holds the box diag-key in config; pass it so the gate's corpus/
        # hands/engine checks authenticate through the relay exactly as a seat would.
        try:
            import file_server
            diag_key = file_server.load_config().get("diag_key", "") or os.environ.get("DIAG_KEY", "")
        except Exception:
            diag_key = os.environ.get("DIAG_KEY", "")
        result = gate.run_gate(seat, lineage, role=role, diag_key=diag_key,
                               seat_invariants=seat_invariants)

        # KEY ISSUANCE-ON-PASS (stubbed). Structured so real per-identity keys
        # (CALLER-1 + the key build) drop in here without changing the response
        # shape: oriented seats get an `issued_key` bound to {seat, lineage};
        # today that key IS the shared DIAG_KEY (so nothing changes operationally),
        # but the field + binding exist so callers can start reading it now.
        if result.get("oriented"):
            result["key_issuance"] = {
                "issued": True,
                "bound_to": {"seat": seat, "lineage": lineage},
                "key_kind": "shared_diag_key_stub",   # -> 'per_identity' when the key build lands
                "note": "stubbed to shared DIAG_KEY until per-identity key issuance ships",
            }
        else:
            result["key_issuance"] = {"issued": False,
                                      "reason": "gate not passed — no key issued"}

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

