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
GITHUB_REPO_DEFAULT = os.environ.get("CORPUS_REPO", "PatrickKillebrew/ontinuity").strip() or "PatrickKillebrew/ontinuity"  # per-install corpus repo; default = operator install
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


def _authed_identity():
    """KEYS-2: resolve the AUTHENTICATED identity from WHICH key called, via the
    file_server key registry. Returns {seat, lineage, authenticated, mode} or None.
    authenticated=True only for a per-identity key; the shared DIAG_KEY resolves to
    {seat:'unattributed', authenticated:False} (back-compat)."""
    try:
        import file_server
        presented = request.headers.get("X-Diag-Key", "") or request.args.get("diag_key", "")
        return file_server.authenticate_identity(presented)
    except Exception:
        return None


def _identity_seat(body_seat=None):
    """The seat to TRUST for this request. KEYS-2: prefer the key-derived seat when
    the caller authenticated with a per-identity key; otherwise (shared-key mode)
    fall back to the body-supplied seat (honest-but-asserted, CALLER-1 semantics).
    This is the single chokepoint every identity-reading route routes through, so
    the migration is one helper, not N edits."""
    ident = _authed_identity()
    if ident and ident.get("authenticated"):
        return ident.get("seat"), ident.get("lineage"), True   # authenticated, body IGNORED
    # shared-key back-compat: trust the body field, flagged not-authenticated
    return (body_seat or "").strip() or None, None, False


def _caller_seat(default="diag-key"):
    """CALLER-1 + KEYS-2: seat name for operations_ledger.caller. Prefers the
    AUTHENTICATED key-derived seat; falls back to the self-asserted body seat only
    in shared-key mode (trusted-not-authenticated). Falls back to 'diag-key' when
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

def _current_seat_session_id():
    """L3: the seat session this call belongs to. Body-supplied `seat_session_id` for now;
    L4 derives it from the per-identity key so there is no body field to forget."""
    try:
        b = request.get_json(silent=True) or {}
        return (b.get("seat_session_id") or "").strip() or None
    except Exception:
        return None


def _ledger_begin(op, args):
    try:
        import file_server
        # caller = self-asserted seat (trusted-not-authenticated; see _caller_seat)
        return file_server._ops_begin(op, "REVIEW", _caller_seat(), request.remote_addr, args,
                                      seat_session_id=_current_seat_session_id())
    except TypeError:
        import file_server
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


# ── OP SCHEMAS + describe (RITUAL LOCKDOWN step 1, 2026-09-15) ───────────────────
# The op IS the manual for op bodies. required/optional come from each route's own
# validation; tier per OPERATING_MANUAL. A route present on the box but absent here is
# reported as "undocumented" so drift is visible, not silent.
OP_SCHEMAS = {
    "read_file":        {"required": ["path"], "optional": [], "tier": "SAFE",
                         "desc": "Read a file inside the box project dir (path traversal rejected)."},
    "write_file":       {"required": ["path", "content"], "optional": ["description"], "tier": "REVIEW",
                         "desc": "Bounded write to a file inside the box project dir. Repo-commit != box-install: this is the box half."},
    "read_repo":        {"required": ["path"], "optional": ["repo", "ref", "branch", "github_token"], "tier": "SAFE",
                         "desc": "Read any repo file. Tokenless path = raw CDN then unauth API (public repos only); pass github_token for the authoritative read or a private repo. repo defaults to CORPUS_REPO."},
    "commit_file":      {"required": ["path", "github_token"], "optional": ["repo_path", "repo", "branch", "message"], "tier": "REVIEW",
                         "desc": "Commit a file that EXISTS ON THE BOX to the repo (write_file first). repo_path defaults to the box path. Token passed per call, never stored."},
    "commit_self":      {"required": ["github_token"], "optional": ["files", "repo", "branch", "repo_dir"], "tier": "REVIEW",
                         "desc": "Commit the box's own allowlisted source files (file_server/seat_mailbox/box_ops...) so the repo matches the box."},
    "backup_db":        {"required": [], "optional": ["out"], "tier": "SAFE",
                         "desc": "Consistent sqlite .backup of ontinuity.db plus a .sql dump."},
    "bootstrap_gate":   {"required": ["seat"], "optional": ["role", "lineage", "seat_invariants", "github_token"], "tier": "SAFE",
                         "desc": "Verified boot: six checks -> {oriented, checks[], seat_session{seat_session_id,started_at}}. Booted == oriented:true from this op. Pass github_token on a private corpus (manual/queue reads). Opens a seat_sessions row on pass (L3); pass seat_session_id on later ops."},
    "deploy":           {"required": ["target", "signoff_block_id"], "optional": ["block_id", "commit_sha", "dry_run"], "tier": "RISK",
                         "desc": "Two-party deploy: proposal + signoff rows from DISTINCT seats on the same block_id. dry_run:true runs the full gate with no side effect. See live/specs/signoff_deploychain.md."},
    "new_project":      {"required": ["name"], "optional": ["description", "branch", "user_id"], "tier": "REVIEW",
                         "desc": "Create a per-project matter: projects+branch rows + per-project Knowtext/ERL files keyed on name-slug. Idempotent."},
    "railway_set_var":  {"required": ["name", "value"], "optional": ["project_id", "environment_id", "service_id", "resolved_cause"], "tier": "REVIEW",
                         "desc": "The first WRAPPED op: box constructs the Railway variableUpsert call; seat supplies only {name,value}. Self-counts failures; refuses after 3 until resolved_cause is given."},
    "read_journal":     {"required": [], "optional": ["lines"], "tier": "SAFE",
                         "desc": "Tail the ontinuity-workspace unit's journal."},
    "restart_workspace":{"required": [], "optional": [], "tier": "REVIEW",
                         "desc": "systemctl restart ontinuity-workspace (the box-install half of a box code change)."},
    "restart_burnin":   {"required": [], "optional": [], "tier": "REVIEW", "desc": "Restart the burn-in resident."},
    "mailbox_send":     {"required": ["from_seat", "to_seat", "body"], "optional": ["kind", "block_id", "reply_to", "corr_id", "ref", "citations", "confidence", "depends_on", "from_lineage", "author_seat", "author_lineage"], "tier": "REVIEW",
                         "desc": "Post to the seat mailbox (task distribution + the two-party signoff chain). Proposals go to any_worker, never a named seat."},
    "mailbox_fetch":    {"required": ["seat"], "optional": ["kinds", "roles", "block_id", "reply_to", "newest", "lineage"], "tier": "REVIEW",
                         "desc": "Atomic claim with lease. reply_to=<task_msg_id> claims that result; newest=true drains newest-first. ACK immediately after."},
    "mailbox_ack":      {"required": ["msg_id"], "optional": ["seat", "reply", "ref", "lineage", "from_lineage"], "tier": "REVIEW",
                         "desc": "Mark a claimed message done. Never leave a dangling claim."},
    "mailbox_peek":     {"required": [], "optional": ["seat", "from_seat", "block_id", "status", "limit"], "tier": "SAFE",
                         "desc": "Read-only view, newest-first (default limit 20, max 100). Never marks done."},
    "mailbox_purge":    {"required": ["seat"], "optional": ["kinds", "older_than_secs", "all"], "tier": "REVIEW",
                         "desc": "Bulk-clear result/note backlog for a seat."},
    "mailbox_reclaim":  {"required": ["seat"], "optional": ["all", "lineage"], "tier": "REVIEW",
                         "desc": "Release expired/orphaned claims."},
    "you_there":        {"required": ["seat"], "optional": ["kinds", "roles", "block_id", "wait_seconds", "lineage"], "tier": "REVIEW",
                         "desc": "Nudge: a worker self-drains its whole turn on one call. Keep wait_seconds <= 20 (relay read-timeout 25)."},
    "orient":           {"required": ["topic"], "optional": ["seat", "repo", "ref", "github_token", "max_hits"], "tier": "SAFE",
                         "desc": "The OPEN ritual as a ledger fact: searches the queue folds (agent_queue.md) and every live/conversations/*.md for the topic; returns hits {file,line,fold,excerpt} or count 0; logs {topic,count}. Run before reasoning about a task. Pass github_token: the conversations directory listing needs the contents API (raw CDN cannot list), and unauthenticated API calls rate-limit."},
    "_common":          {"required": [], "optional": ["seat", "seat_session_id"], "tier": "n/a",
                         "desc": "Fields every op accepts: seat (self-asserted caller label until L4) and seat_session_id (joins the ledger row to the seat session opened by bootstrap_gate)."},
    "describe":         {"required": [], "optional": ["op", "allowlist"], "tier": "SAFE",
                         "desc": "This op. Returns every /op route on the box with its schema; routes without a schema are 'undocumented'; pass the courier allowlist to get the allowed-but-absent / present-but-not-allowed diff."},
}


@box_ops_bp.route("/op/describe", methods=["POST"])
def op_describe():
    """RITUAL LOCKDOWN step 1: the op is the manual for op bodies. Introspects the
    live Flask url_map so a new route without a schema shows up as undocumented
    (drift made visible). Logs to the ledger like every other op."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    from flask import current_app
    present = sorted({r.rule[len("/op/"):] for r in current_app.url_map.iter_rules()
                      if r.rule.startswith("/op/") and "POST" in (r.methods or set())})
    want = (b.get("op") or "").strip()
    op_id = _ledger_begin("describe", {"op": want or "*", "allowlist_given": bool(b.get("allowlist"))})
    out = {"ok": True, "box_routes": present, "ops": {}, "undocumented": [], "schema_only": []}
    for name in present:
        if name in OP_SCHEMAS:
            out["ops"][name] = dict(OP_SCHEMAS[name], present_on_box=True)
        else:
            out["undocumented"].append(name)
    out["schema_only"] = sorted(n for n in OP_SCHEMAS if n not in present and not n.startswith("_"))
    out["common_fields"] = OP_SCHEMAS.get("_common")
    if want:
        out = {"ok": want in OP_SCHEMAS or want in present, "op": want,
               "schema": OP_SCHEMAS.get(want), "present_on_box": want in present}
        if not out["ok"]:
            out["error"] = "unknown op"
    al = b.get("allowlist")
    if isinstance(al, list):
        al = sorted(str(x) for x in al)
        out["allowlist_diff"] = {"allowed_but_absent_on_box": sorted(set(al) - set(present)),
                                 "present_on_box_but_not_allowed": sorted(set(present) - set(al))}
    if want and not out["ok"]:
        _ledger_finish(op_id, "fail", f"unknown op {want}")
        return jsonify(out), 404
    _ledger_finish(op_id, "ok", f"routes={len(present)} undocumented={len(out.get('undocumented', []))}")
    return jsonify(out)


# ── orient (RITUAL LOCKDOWN step 2, 2026-09-15) ────────────────────────────────
# The per-task OPEN ritual (manual: "search the queue folds for the topic; read the
# relevant conversation records; follow refs") had no primitive, so it was a self-report.
# This op does the search box-side and logs it. Fetch path = read_repo's (token per call
# on a private corpus; raw-CDN/unauth API on a public one). No token is stored.

def _repo_fetch_text(repo, path, ref, token):
    """read_repo's source order, as a helper: api(auth) if token -> raw cachebust -> api(unauth)."""
    attempts = []
    def _api(tok):
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
        hdrs = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if tok: hdrs["Authorization"] = f"Bearer {tok}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as r:
            data = json.loads(r.read().decode())
        if isinstance(data, list):
            return data  # directory listing
        return base64.b64decode(data["content"]).decode("utf-8", "replace")
    def _raw():
        import time as _t
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}?cb={int(_t.time())}"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    if token:
        try: return _api(token), "github_api_authenticated"
        except Exception as e: attempts.append(f"api(auth): {str(e)[:60]}")
    try: return _raw(), "raw_cdn_cachebust"
    except Exception as e: attempts.append(f"raw: {str(e)[:60]}")
    try: return _api(""), "github_api_unauthenticated"
    except Exception as e: attempts.append(f"api(unauth): {str(e)[:60]}")
    raise RuntimeError("; ".join(attempts))


def _repo_list_dir(repo, path, ref, token):
    """Directory listing via the contents API (the only listing path; raw CDN cannot list)."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    hdrs = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token: hdrs["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as r:
        data = json.loads(r.read().decode())
    return [d["path"] for d in data if d.get("type") == "file" and d["name"].endswith(".md")]


@box_ops_bp.route("/op/orient", methods=["POST"])
def op_orient():
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    topic = (b.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400
    repo = (b.get("repo") or GITHUB_REPO_DEFAULT).strip()
    ref = (b.get("ref") or b.get("branch") or GITHUB_BRANCH_DEFAULT).strip()
    token = (b.get("github_token") or "").strip()
    try: max_hits = max(1, min(int(b.get("max_hits") or 40), 200))
    except Exception: max_hits = 40
    op_id = _ledger_begin("orient", {"topic": topic[:120], "repo": repo, "ref": ref, "auth": bool(token)})

    import re as _re
    phrase = topic.lower()
    tokens = [t for t in _re.findall(r"[a-z0-9_\-]{3,}", phrase)]
    def _match(line):
        l = line.lower()
        if phrase in l: return "phrase"
        if tokens and all(t in l for t in tokens): return "all-tokens"
        return None

    hits, files_searched, sources, errors = [], [], {}, []
    # 1) the queue folds
    try:
        q, src = _repo_fetch_text(repo, "live/agent_queue.md", ref, token)
        sources["live/agent_queue.md"] = src; files_searched.append("live/agent_queue.md")
        fold = None
        for i, line in enumerate(q.splitlines(), 1):
            if line.startswith("## CURRENT-STATE TOUCH POINT"): fold = line[3:].strip()[:100]
            m = _match(line)
            if m:
                hits.append({"file": "live/agent_queue.md", "line": i, "fold": fold, "match": m, "excerpt": line.strip()[:220]})
    except Exception as e:
        errors.append(f"agent_queue: {str(e)[:100]}")
    # 2) every conversation record
    try:
        for p in _repo_list_dir(repo, "live/conversations", ref, token):
            try:
                txt, src = _repo_fetch_text(repo, p, ref, token)
                sources[p] = src; files_searched.append(p)
                for i, line in enumerate(txt.splitlines(), 1):
                    m = _match(line)
                    if m:
                        hits.append({"file": p, "line": i, "fold": None, "match": m, "excerpt": line.strip()[:220]})
            except Exception as e:
                errors.append(f"{p}: {str(e)[:60]}")
    except Exception as e:
        errors.append(f"conversations listing: {str(e)[:100]}")

    truncated = len(hits) > max_hits
    out = {"ok": True, "topic": topic, "repo": repo, "ref": ref, "count": len(hits),
           "hits": hits[:max_hits], "truncated": truncated,
           "files_searched": len(files_searched), "errors": errors, "sources": sources}
    status = "ok" if not errors or hits else ("ok" if files_searched else "fail")
    _ledger_finish(op_id, status, f"topic={topic[:60]} hits={len(hits)} files={len(files_searched)} errors={len(errors)}")
    return jsonify(out), (200 if status == "ok" else 502)


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
           lineage (str), seat_invariants ({key->text} for CHECK 6 MECHANICS)}.
    CHECK 1's canonical count is owned by the gate module itself (its
    CANONICAL_COURIER_OP_COUNT, updated in the same commit as any OP_ALLOWED
    change). A caller-supplied canonical_op_count is REFUSED: an overridden pass
    cannot honestly prove mechanical orientation (2026-09-05 review; 2026-09-13 fix).
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
        # CHECK-1 canonical count is governed by the gate module's own constant.
        # No override from this wrapper and none from the caller.
        if canonical is not None:
            _ledger_finish(op_id, "fail", "canonical_op_count override refused")
            return jsonify({"error": "canonical_op_count override is not accepted; the gate module owns the canonical count"}), 400
        # The box holds the box diag-key in config; pass it so the gate's corpus/
        # hands/engine checks authenticate through the relay exactly as a seat would.
        try:
            import file_server
            diag_key = file_server.load_config().get("diag_key", "") or os.environ.get("DIAG_KEY", "")
        except Exception:
            diag_key = os.environ.get("DIAG_KEY", "")
        # PORTABLE-1 (L3a): the gate takes THIS install's values from the box config
        # (written by box_boot from env), never hardcoded; a private corpus needs the
        # caller's token for the manual/queue reads — passed per call, never stored.
        # RULE: an install value ABSENT from this box's config means "this install has none",
        # never "fall back to the operator's" — the gate's module defaults exist only for the
        # operator box until L9. So every field is passed explicitly here.
        install = {}
        try:
            cfg = file_server.load_config()
            proj = (cfg.get("projects") or [{}])[0]
            install = {"engine_url": (cfg.get("engine_url") or "").strip() or None,   # None -> gate default (operator engine) ONLY if unset
                       "farm_url": (cfg.get("farm_url") or "").strip(),                # "" -> no FARM on this install
                       "corpus_repo": (proj.get("github_repo") or os.environ.get("CORPUS_REPO") or "").strip() or None,
                       "session_floor": int(cfg.get("corpus_session_floor") or 0)}
            if install["engine_url"] is None:
                install.pop("engine_url")
            if install["corpus_repo"] is None:
                install.pop("corpus_repo")
        except Exception:
            install = {}
        gtoken = (b.get("github_token") or "").strip()
        result = gate.run_gate(seat, lineage, role=role, diag_key=diag_key,
                               seat_invariants=seat_invariants,
                               github_token=gtoken, install=install)

        # KEY ISSUANCE-ON-PASS (stubbed). Structured so real per-identity keys
        # (CALLER-1 + the key build) drop in here without changing the response
        # shape: oriented seats get an `issued_key` bound to {seat, lineage};
        # today that key IS the shared DIAG_KEY (so nothing changes operationally),
        # but the field + binding exist so callers can start reading it now.
        if result.get("oriented"):
            # L3: the seat session as a ledger fact. Opened ONLY on oriented:true.
            try:
                sid, ts = file_server.seat_session_open(seat, role, lineage)
            except Exception:
                sid, ts = None, None
            result["seat_session"] = {"seat_session_id": sid, "started_at": ts,
                                      "note": "pass seat_session_id on every later op until per-identity keys (L4) derive it from the key"}
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
        detail = (f"oriented seat={seat} role={role} seat_session={(result.get('seat_session') or {}).get('seat_session_id')}" if result.get("oriented")
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
# SHARED-KEY CAVEAT (must stay loud until per-identity keys land — KEYS-1):
# the seat identities this rule compares (proposal author, signoff sender) are
# SELF-ASSERTED body fields under one shared DIAG_KEY. So today any diag-key
# holder could forge a distinct from_seat on a signoff and satisfy the two-party
# check. This op enforces the STRUCTURE (signer != author) correctly; the
# STRENGTH of that enforcement is bounded by key authentication. Per KEYS-1: once
# the gate derives seat/lineage FROM the key and routes stop trusting body fields,
# this same check becomes unforgeable. Until then: structural gate, honest-name
# assumption, every call logged. NOT a substitute for per-identity keys.
#
# TOKEN: RAILWAY_TOKEN is read from the box ENV (os.environ) — operator sets it as
# a systemd env var. NEVER hardcoded, never written to a file, never echoed.

_RAILWAY_GQL = "https://backboard.railway.com/graphql/v2"
_PROVENANCE_LEDGER = os.path.join(_BASE_DIR, "live", "provenance_ledger.jsonl")


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


def _twoparty_check(block_id):
    """Inspect the mailbox for block_id. Returns (ok, detail, author, signer).
    ok=True iff a 'proposal' exists AND a 'signoff' exists whose sender differs
    from the proposal's author (NOSELF-1 author fields). Uses seat_mailbox._mb_conn."""
    try:
        import seat_mailbox
        c = seat_mailbox._mb_conn()
    except Exception as e:
        return False, f"cannot reach mailbox: {str(e)[:80]}", None, None
    try:
        # the authored work: prefer the proposal row's author_seat (NOSELF-1),
        # falling back to its from_seat.
        prop = c.execute(
            "SELECT COALESCE(author_seat, from_seat), COALESCE(author_lineage, from_lineage) "
            "FROM seat_mailbox WHERE block_id=? AND kind='proposal' "
            "ORDER BY created_at ASC LIMIT 1", (block_id,)).fetchone()
        # the sign-off: a 'signoff' kind row for this block.
        sign = c.execute(
            "SELECT from_seat, from_lineage FROM seat_mailbox WHERE block_id=? AND kind='signoff' "
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
               {"seat": prop[0], "lineage": prop[1]}, None
    author = {"seat": prop[0], "lineage": prop[1]}
    signer = {"seat": sign[0], "lineage": sign[1]}
    # TWO-PARTY: the signer must be a DIFFERENT SEAT than the author. Two distinct
    # seats are two parties even when they share a model lineage (worker1 and worker2
    # are both claude:opus-4.8 — that is the normal two-worker case and MUST be
    # allowed). We refuse on SAME SEAT only. (An earlier draft also refused on
    # same-lineage, which would wrongly block the legitimate two-worker case.)
    # NOTE the shared-key reality (KEYS-1): the seat field is self-asserted, so a
    # forger could present a different from_seat to fake distinctness. The seat-
    # distinct STRUCTURE is right; per-identity keys are what make it unforgeable.
    if (author["seat"] or "") == (signer["seat"] or "") and author["seat"]:
        return False, (f"self-sign-off: author seat={author['seat']} == signer seat "
                       f"{signer['seat']} — two-party rule violated"), author, signer
    return True, "two-party satisfied (distinct seats)", author, signer


def _railway_deploy(service_id, environment_id, token):
    """Trigger serviceInstanceDeployV2 via the Railway GraphQL API. Token from env."""
    query = ("mutation($s:String!,$e:String!){serviceInstanceDeployV2(serviceId:$s,environmentId:$e)}")
    body = json.dumps({"query": query, "variables": {"s": service_id, "e": environment_id}}).encode()
    req = urllib.request.Request(_RAILWAY_GQL, data=body,
                                 headers={"Content-Type": "application/json",
                                          # 2026-09-14: Project-Access-Token, NOT Bearer — writes are
                                          # 'Not Authorized' under Bearer (the true cause of the old
                                          # "known FARM seam"); curl-compatible UA passes the edge.
                                          "Project-Access-Token": token,
                                          "User-Agent": "ontinuity-box/1.0 (curl-compatible)"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


@box_ops_bp.route("/op/deploy", methods=["POST"])
def op_deploy():
    """Authorize + trigger a deploy, gated by the two-party rule. Body:
      {target: 'main'|'farm'|'box', signoff_block_id (req), commit_sha?, dry_run?}.
    Two-party: the block must have a proposal (author) AND a signoff by a DIFFERENT
    seat, else REFUSE + gate_violation record. ENGINE deploy reads RAILWAY_TOKEN +
    the target's RAILWAY_SERVICE_ID_<TARGET> / RAILWAY_ENVIRONMENT_ID from env. BOX
    target = restart (no Railway call). dry_run=true runs every check + logs but
    makes NO Railway call (for tests). See the shared-key caveat in the module note."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    target = (b.get("target") or "").strip().lower()
    block_id = (b.get("signoff_block_id") or "").strip()
    commit_sha = (b.get("commit_sha") or "").strip()
    dry_run = bool(b.get("dry_run"))
    if target not in ("main", "farm", "box"):
        return jsonify({"error": "target must be main|farm|box"}), 400
    if not block_id:
        return jsonify({"error": "signoff_block_id required"}), 400
    caller = _caller_seat()
    op_id = _ledger_begin("deploy", {"target": target, "block": block_id, "dry_run": dry_run})

    # 1) TWO-PARTY GATE (structural)
    ok, detail, author, signer = _twoparty_check(block_id)
    if not ok:
        _prov_append({"kind": "gate_violation", "block_id": block_id, "target": target,
                      "caller": caller, "reason": detail, "author": author, "signer": signer,
                      "commit_sha": commit_sha or None})
        _ledger_finish(op_id, "fail", f"two-party refused: {detail[:140]}")
        return jsonify({"error": "deploy refused — two-party rule", "detail": detail,
                        "author": author, "signer": signer}), 403

    # 1b) KEYS-2: when the caller authenticated with a per-identity key, bind the
    # DEPLOY caller to the SIGNER — a third party can't trigger a deploy citing
    # someone else's signoff. In shared-key mode this bind is skipped (the seat is
    # unauthenticated 'unattributed'), so the structural two-party check above is the
    # only guard until keys are issued — flagged.
    _ident = _authed_identity()
    if _ident and _ident.get("authenticated"):
        if signer and (_ident.get("seat") or "") != (signer.get("seat") or ""):
            _prov_append({"kind": "gate_violation", "block_id": block_id, "target": target,
                          "caller": "auth:" + str(_ident.get("seat")), "reason":
                          f"deploy caller {_ident.get('seat')} != signer {signer.get('seat')}",
                          "author": author, "signer": signer})
            _ledger_finish(op_id, "fail", "caller != signer")
            return jsonify({"error": "deploy refused — caller is not the signer",
                            "caller": _ident.get("seat"), "signer": signer}), 403

    # 2) lifecycle record: authorized (captures the chain so findings don't evaporate)
    _prov_append({"kind": "deploy_authorized", "block_id": block_id, "target": target,
                  "caller": caller, "author": author, "signer": signer,
                  "commit_sha": commit_sha or None, "dry_run": dry_run})

    # 3) DRY RUN: every check passed; make no real call (test path)
    if dry_run:
        _ledger_finish(op_id, "ok", f"dry_run authorized target={target} block={block_id}")
        return jsonify({"ok": True, "dry_run": True, "authorized": True,
                        "two_party": {"author": author, "signer": signer},
                        "would_deploy": target})

    # 4) EXECUTE
    try:
        if target == "box":
            # box redeploy = restart the workspace (the existing hands-free path)
            result = {"box": "restart requested"}
            try:
                import file_server
                if hasattr(file_server, "restart_workspace"):
                    file_server.restart_workspace()
            except Exception as e:
                result["restart_note"] = str(e)[:120]
        else:
            token = os.environ.get("RAILWAY_TOKEN", "").strip()
            svc = os.environ.get(f"RAILWAY_SERVICE_ID_{target.upper()}", "").strip()
            env = os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip()
            if not (token and svc and env):
                _ledger_finish(op_id, "fail", "railway env not configured")
                _prov_append({"kind": "deploy_result", "block_id": block_id, "target": target,
                              "outcome": "fail", "reason": "RAILWAY_TOKEN/SERVICE_ID/ENVIRONMENT_ID env missing"})
                return jsonify({"error": "railway env not configured (RAILWAY_TOKEN / "
                                "RAILWAY_SERVICE_ID_%s / RAILWAY_ENVIRONMENT_ID)" % target.upper()}), 503
            result = _railway_deploy(svc, env, token)
        _prov_append({"kind": "deploy_result", "block_id": block_id, "target": target,
                      "outcome": "ok", "commit_sha": commit_sha or None})
        _ledger_finish(op_id, "ok", f"deployed target={target} block={block_id}")
        return jsonify({"ok": True, "deployed": target, "block_id": block_id,
                        "two_party": {"author": author, "signer": signer}, "result": result})
    except Exception as e:
        _prov_append({"kind": "deploy_result", "block_id": block_id, "target": target,
                      "outcome": "fail", "reason": str(e)[:140]})
        _ledger_finish(op_id, "fail", f"deploy error: {str(e)[:140]}")
        return jsonify({"error": f"deploy error: {str(e)[:200]}"}), 500

@box_ops_bp.route("/op/new_project", methods=["POST"])
def op_new_project():
    """Create a new project corpus on demand — the user-facing 'start a new matter'
    primitive. Bounded and idempotent: get-or-create a projects row + its main
    branch row, and initialize the project's empty corpus files (Knowtext + ERL)
    so the dormant per-project scoping in app.py (session_knowtext_path /
    session_erl_path resolve from project_id/branch) has files to read/write.
    No arbitrary SQL. SAFE-tier: creates rows + empty files, touches nothing else.

    Body: {name (req, the project/matter name in the operator's words),
           description (opt, what the matter is for),
           branch (opt, default 'main'),
           user_id (opt; default = first user / the workspace user)}.
    Returns: {ok, project_id, branch_id, name, branch, knowtext_path, erl_path,
              created (bool — false if the project already existed)}.
    The caller then passes project_id (and branch) to /agent/start so the session
    is scoped to this matter and its close writes to this corpus only.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    name = (b.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if name in ("Ontinuity Platform",):
        return jsonify({"error": "reserved project name"}), 400
    branch_name = (b.get("branch") or "main").strip() or "main"
    description = (b.get("description") or "").strip() or None
    db_path = os.environ.get("ONTINUITY_DB_PATH",
                             os.path.join(_BASE_DIR, "ontinuity.db"))
    if not os.path.exists(db_path):
        return jsonify({"error": "db not found", "path": db_path}), 404
    op_id = _ledger_begin("new_project", {"name": name, "branch": branch_name})
    try:
        # DB rows (get-or-create, mirrors workspace_db_endpoint._get_or_create_project)
        from db import OntinuityDB
        db = OntinuityDB(db_path)
        conn = db.connect()
        user_id = (b.get("user_id") or "").strip()
        if not user_id:
            row = conn.execute("SELECT user_id FROM users LIMIT 1").fetchone()
            user_id = row["user_id"] if row else db.insert_user("Workspace User", plan="personal")
        created = False
        row = conn.execute(
            "SELECT project_id FROM projects WHERE user_id = ? AND name = ?",
            (user_id, name)).fetchone()
        if row:
            project_id = row["project_id"]
        else:
            project_id = db.insert_project(user_id, name, description)
            created = True
        row = conn.execute(
            "SELECT branch_id FROM branches WHERE project_id = ? AND name = ?",
            (project_id, branch_name)).fetchone()
        branch_id = row["branch_id"] if row else db.insert_branch(project_id, user_id, branch_name)
        db.close()

        # Per-project corpus files (the slug matches app.py _scope_slug: proj_branch,
        # non-alnum -> '_'). Initialize EMPTY so the scoped session paths resolve to a
        # real file; never overwrite an existing corpus.
        import re as _re
        proj_safe = _re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        br_safe = _re.sub(r'[^a-zA-Z0-9_-]', '_', branch_name)
        slug = "_".join([p for p in [proj_safe, br_safe] if p])
        kt_name = f"knowtext_{slug}.txt"
        erl_name = f"erl_{slug}.txt"
        kt_full = _safe_box_path(kt_name)
        erl_full = _safe_box_path(erl_name)
        if not kt_full or not erl_full:
            _ledger_finish(op_id, "fail", "path traversal rejected on corpus init")
            return jsonify({"error": "corpus path rejected"}), 403
        for full, header in ((kt_full, "KNOWTEXT_SCHEMA_V1\n\nIdentity:\nActive Frameworks:\nOpen Questions:\nValence Mapping:\nDelta Log:\nCorrection History:\nClimate Notes:\n"),
                             (erl_full, "(empty ledger - no prior results)\n")):
            if not os.path.exists(full):
                os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(header)

        _ledger_finish(op_id, "ok",
                       f"project {name} ({'created' if created else 'existing'}) "
                       f"project_id={project_id} branch_id={branch_id}")
        return jsonify({"ok": True, "project_id": project_id, "branch_id": branch_id,
                        "name": name, "branch": branch_name,
                        "knowtext_path": kt_name, "erl_path": erl_name,
                        "created": created})
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500

def _railway_set_var(project_id, environment_id, service_id, name, value, token):
    """Set a Railway service variable via variableUpsert. Same transport as
    _railway_deploy (urllib + Bearer, run FROM THE BOX — the box's egress reaches
    Railway; a sandbox seat's urllib does NOT, which is the whole reason this is a
    wrapped box op: the seat never constructs this call, so it cannot hand-roll it
    with the wrong client)."""
    query = ("mutation($p:String!,$e:String!,$s:String!,$n:String!,$v:String!){"
             "variableUpsert(input:{projectId:$p,environmentId:$e,serviceId:$s,name:$n,value:$v})}")
    body = json.dumps({"query": query, "variables": {
        "p": project_id, "e": environment_id, "s": service_id, "n": name, "v": value}}).encode()
    # ROOT CAUSE (proven 2026-09-14): Railway's edge (Cloudflare) rejects the default
    # "Python-urllib" User-Agent with 403/1010. A curl-like UA passes. This is WHY
    # every model tripped on "Railway egress" — it was never the client, it was the
    # UA header. Set once here, inside the op, so no seat ever has to remember it.
    req = urllib.request.Request(_RAILWAY_GQL, data=body,
                                 headers={"Content-Type": "application/json",
                                          # PROVEN 2026-09-14: variableUpsert (a WRITE) authorizes ONLY with
                                          # Project-Access-Token; Bearer returns "Not Authorized" (reads
                                          # tolerate Bearer, which is why _railway_deploy's Bearer header
                                          # never surfaced — box deploys were silently unauthorized: the
                                          # true cause of the "known FARM seam"). Per CONTROL_HANDOFF.
                                          "Project-Access-Token": token,
                                          "User-Agent": "ontinuity-box/1.0 (curl-compatible)"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def _recent_consecutive_failures(operation, window=6):
    """Count consecutive recent FAIL rows for this operation in the operations
    ledger (most-recent-first, stopping at the first non-fail). THE SELF-COUNTER:
    every attempt of a wrapped op is ledger-logged and passes through here, so the
    op knows its own recent failure streak with NO external monitor of the seat.
    This is what makes the chokepoint able to observe 'N failures' — the count
    lives where every attempt provably flows: through the op itself."""
    try:
        import file_server
        conn = file_server._ops_sqlite.connect(file_server._OPS_DB)
        rows = conn.execute(
            "SELECT status FROM operations_ledger WHERE operation=? "
            "ORDER BY op_id DESC LIMIT ?", (operation, window)).fetchall()
        conn.close()
        streak = 0
        for r in rows:
            if (r[0] or "") == "fail":
                streak += 1
            else:
                break
        return streak
    except Exception:
        return 0


@box_ops_bp.route("/op/railway_set_var", methods=["POST"])
def op_railway_set_var():
    """Set a Railway env var (role-provider config, etc.) — WRAPPED so a seat
    supplies {name, value} and NEVER constructs the HTTP call. This closes the
    failure class where a seat hand-rolls a Railway call with the wrong client
    (urllib from a sandbox, which Railway's edge blocks) instead of the prescribed
    path. The call runs HERE, on the box, from the box's own token, where it works.

    REFUSE-TO-RETRY (the mechanical teeth): every attempt is ledger-logged; on the
    3rd+ consecutive failure of this operation the op REFUSES to retry and returns
    the recorded cause instead — stopping the flailing where a seat retries the same
    broken call over and over. No seat-monitor is needed: the op counts itself
    (_recent_consecutive_failures) because every attempt flows through it.
    (A plain-language explanation of the failure for a non-technical user is a
    separate v2 UX layer; the reliability mechanism is the refuse-to-retry itself.)

    Body: {name (req), value (req), project_id?, environment_id?, service_id?}
      (IDs default to the box's RAILWAY_PROJECT_ID / RAILWAY_ENVIRONMENT_ID /
       RAILWAY_SERVICE_ID_MAIN env). Returns {ok, name, redeploy_note}; on the
       failure threshold returns 409 {retry_refused, attempts, last_cause}.
    """
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    name = (b.get("name") or "").strip()
    value = b.get("value")
    if not name or value is None:
        return jsonify({"error": "name and value required"}), 400

    # REFUSE-TO-RETRY (checked BEFORE attempting): if this op has failed 3+ times
    # in a row, stop and report the recorded cause rather than flail again.
    # RESET PATH: after the cause is genuinely resolved, the caller must pass
    # resolved_cause=<text> — a DELIBERATE statement of what was fixed (logged) —
    # to reset the streak. An accidental re-call cannot reset it; only a stated
    # resolution can. (Design note 2026-09-14: without this, a fixed bug leaves
    # the op permanently refusing; with it, the refusal stays a real gate.)
    streak = _recent_consecutive_failures("railway_set_var")
    resolved = (b.get("resolved_cause") or "").strip()
    if streak >= 3 and resolved:
        rid = _ledger_begin("railway_set_var", {"name": name, "streak_reset": True})
        _ledger_finish(rid, "ok", f"streak reset — resolved_cause: {resolved[:150]}")
        _prov_append({"kind": "op_streak_reset", "operation": "railway_set_var",
                      "prior_attempts": streak, "resolved_cause": resolved[:200]})
        streak = 0
    if streak >= 3:
        try:
            import file_server
            conn = file_server._ops_sqlite.connect(file_server._OPS_DB)
            last = conn.execute(
                "SELECT result FROM operations_ledger WHERE operation='railway_set_var' "
                "AND status='fail' ORDER BY op_id DESC LIMIT 1").fetchone()
            conn.close()
            last_cause = (last[0] if last else "") or "(no recorded cause)"
        except Exception:
            last_cause = "(cause unavailable)"
        _prov_append({"kind": "op_retry_refused", "operation": "railway_set_var",
                      "attempts": streak, "var": name})
        return jsonify({"retry_refused": True, "attempts": streak,
                        "last_cause": last_cause,
                        "note": "This operation has failed repeatedly. Retrying will not help; "
                                "the recorded cause must be resolved first (token permission, "
                                "rate limit, or wrong project/service ID)."}), 409

    # Credentials from the box's config.json (load_config, same pattern as diag_key at
    # file_server L1467), with env as fallback. The seat never sees or handles these.
    try:
        import file_server
        cfg = file_server.load_config()
    except Exception:
        cfg = {}
    pid = (b.get("project_id") or cfg.get("railway_project_id") or os.environ.get("RAILWAY_PROJECT_ID", "")).strip()
    env = (b.get("environment_id") or cfg.get("railway_environment_id") or os.environ.get("RAILWAY_ENVIRONMENT_ID", "")).strip()
    svc = (b.get("service_id") or cfg.get("railway_service_id_main") or os.environ.get("RAILWAY_SERVICE_ID_MAIN", "")).strip()
    token = (cfg.get("railway_token") or os.environ.get("RAILWAY_TOKEN", "")).strip()
    if not (pid and env and svc and token):
        return jsonify({"error": "railway creds not configured on the box (config.json railway_token / "
                        "railway_project_id / railway_environment_id / railway_service_id_main, or env)"}), 503

    op_id = _ledger_begin("railway_set_var", {"name": name})  # value NOT logged (may be a secret)
    try:
        resp = _railway_set_var(pid, env, svc, name, str(value), token)
        if resp.get("errors") or (resp.get("data", {}) or {}).get("variableUpsert") is not True:
            _ledger_finish(op_id, "fail", str(resp.get("errors") or resp)[:200])
            return jsonify({"error": "variableUpsert failed",
                            "detail": str(resp.get("errors") or resp)[:200]}), 502
        _ledger_finish(op_id, "ok", f"set {name}")
        return jsonify({"ok": True, "name": name,
                        "redeploy_note": "a variable change triggers a ~30s Railway redeploy"})
    except Exception as e:
        _ledger_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500
