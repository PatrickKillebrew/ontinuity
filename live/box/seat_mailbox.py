"""
SEAT MAILBOX — durable async seat-to-seat coordination channel.
============================================================================
A Flask blueprint for file_server.py. Lets multiple chat-sandbox seats
(control + N workers, any lineage) coordinate through the corpus without the
operator hand-routing messages between conversations.

Registered exactly like db_blueprint:  app.register_blueprint(seat_mailbox_bp)
Reached from sandbox seats through the engine relay-courier (/diag/op/mailbox_*),
which forwards to these /op/mailbox_* routes. Same diag-key gate, same
operations-ledger dual-end logging, same bounded-input contract as the
existing scoped ops in file_server.py.

SCALE-READY (multiseat spec, live/specs/coordinator_worker_multiseat.md):
  - lineage identity on every message (who actually sat there: HARNESS:MODEL)
  - broadcast/role targets (to_seat = a name OR a role like 'any_worker')
  - first-class block_id (the unit of dispatch is a work block)
  - ATOMIC claim (UPDATE ... WHERE status='queued' in one transaction; two
    workers can never claim the same message)
  - lease + reclaim (a claimed-but-never-acked message returns to the queue,
    so a dead worker can't silently swallow a block)
  - ref = corpus pointer (receipt/commit/session id). The mailbox carries
    COORDINATION + POINTERS, never the canonical result itself — the corpus
    stays the one source of truth (avoids a second competing memory).
"""

import os, json, uuid, secrets, sqlite3
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify

seat_mailbox_bp = Blueprint("seat_mailbox", __name__)

# Same DB the operations_ledger + corpus use (file_server.py: _OPS_DB).
_MB_DB = os.environ.get("ONTINUITY_DB_PATH",
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ontinuity.db"))

# Default lease: a claimed message not acked within this window is reclaimable.
_LEASE_SECONDS = int(os.environ.get("MAILBOX_LEASE_SECONDS", "900"))  # 15 min

_KINDS = {"task", "proposal", "review_finding", "signoff", "result", "note"}

# NOSELF-1 — no-self-sign-off (one-node-primitive guardrail, corpus fold 310:
# "verify anyone's work but your own"). Reviewable kinds must never be claimed by
# the node that AUTHORED them, even if a different seat dispatched the mailbox
# message. Authorship is COALESCE(author_seat, from_seat) / COALESCE(author_lineage,
# from_lineage): the explicit author stamp wins; absent it, the sender is the author
# (true for a node self-sending its own proposal).
_REVIEWABLE_KINDS = {"proposal", "review_finding", "signoff"}

def _noself_predicate(seat, lineage):
    """SQL fragment + params that EXCLUDE reviewable items authored by this seat.
    A row is excluded iff: kind is reviewable AND (author_seat==seat OR author_lineage==lineage).
    Non-reviewable items (task/result/note) are never excluded by this filter.
    Returns (sql_fragment, params). lineage may be empty -> only the seat match applies."""
    rk = ",".join("?" for _ in _REVIEWABLE_KINDS)
    # NOT ( reviewable AND own-authored )
    frag = (f" AND NOT ( kind IN ({rk}) AND ( "
            f"COALESCE(author_seat, from_seat) = ? "
            f"OR (? != '' AND COALESCE(author_lineage, from_lineage) = ?) ) )")
    params = list(_REVIEWABLE_KINDS) + [seat, (lineage or ""), (lineage or "")]
    return frag, params


def _now():
    return datetime.now(timezone.utc).isoformat()


def _mb_conn():
    return sqlite3.connect(_MB_DB)


def _mailbox_init():
    """Create the table if absent. Idempotent; called at import."""
    try:
        c = _mb_conn()
        c.execute("""CREATE TABLE IF NOT EXISTS seat_mailbox (
            msg_id        TEXT PRIMARY KEY,
            from_seat     TEXT NOT NULL,
            from_lineage  TEXT,              -- HARNESS:MODEL of the sender (cross-lineage truth signal)
            to_seat       TEXT NOT NULL,     -- a named seat OR a role/broadcast ('any_worker','master')
            kind          TEXT NOT NULL,     -- task|proposal|review_finding|signoff|result|note
            block_id      TEXT,              -- the work block this belongs to (dispatch unit)
            ref           TEXT,              -- corpus pointer: receipt/commit/session id (NOT the result itself)
            depends_on    TEXT,              -- forward-compat: msg_id this is gated on
            body          TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'queued',  -- queued|claimed|done|expired
            created_at    TEXT NOT NULL,
            claimed_at    TEXT,
            claimed_by    TEXT,              -- which seat claimed it
            lease_until   TEXT,              -- claim expiry; past this, reclaimable
            done_at       TEXT,
            reply_to      TEXT               -- msg_id this is a reply to (ack-with-reply)
        )""")
        # NOSELF-1 additive migration (SAFE class: nullable, no rewrite of existing rows).
        # author_seat/author_lineage = who AUTHORED the thing under review, distinct from
        # from_seat (who SENT the mailbox message). Used by the no-self-sign-off filter so a
        # node is never handed its own work to review, even when a different seat dispatched it.
        for _col in ("author_seat", "author_lineage"):
            try:
                c.execute(f"ALTER TABLE seat_mailbox ADD COLUMN {_col} TEXT")
            except Exception:
                pass  # already exists -> idempotent
        c.commit(); c.close()
    except Exception as e:
        print(f"[seat_mailbox] init failed: {e}")


def _diag_ok():
    """Same gate as the scoped ops in file_server.py."""
    from flask import current_app
    # diag_key lives in config.json (load_config); read it the same way file_server does.
    try:
        import file_server
        dk = file_server.load_config().get("diag_key", "")
    except Exception:
        dk = os.environ.get("DIAG_KEY", "")
    if not dk:
        return False
    return secrets.compare_digest(request.headers.get("X-Diag-Key", ""), dk)


# Reuse the operations-ledger helpers from file_server so mailbox ops are
# audited on the SAME spine as every other scoped op (no separate audit path).
def _caller_seat(default="diag-key"):
    """CALLER-1: the seat name to stamp into operations_ledger.caller.
    Pulled from the request body's seat/from_seat field the worker already sends.
    HONESTY CAVEAT: this is a SELF-ASSERTED, TRUSTED-NOT-AUTHENTICATED seat name.
    The shared diag key proves 'a keyholder called', NOT 'this seat called' — any
    keyholder can put any seat string here (see live/specs/mailbox_threat_audit.md,
    SECAUDIT-1 Q1/Q4). It becomes authenticated only when per-identity keys land and
    the gate DERIVES the seat from the key instead of reading it from the body.
    Until then caller is an honest label of who CLAIMS to be acting, not proof.
    Falls back to the auth-method label 'diag-key' when no seat is in the body
    (e.g. box_ops read/write, which carry no seat)."""
    try:
        b = request.get_json(silent=True) or {}
        s = (b.get("seat") or b.get("from_seat") or "").strip()
        return ("seat:" + s) if s else default
    except Exception:
        return default


def _authed_identity():
    """KEYS-2: the AUTHENTICATED identity from WHICH key called (file_server registry).
    Returns {seat, lineage, authenticated, mode} or None. authenticated=True only for a
    per-identity key; the shared DIAG_KEY -> {seat:'unattributed', authenticated:False}."""
    try:
        import file_server
        presented = request.headers.get("X-Diag-Key", "") or request.args.get("diag_key", "")
        return file_server.authenticate_identity(presented)
    except Exception:
        return None


def _trusted_seat(body_seat, body_lineage=None):
    """KEYS-2 chokepoint: the (seat, lineage) to TRUST. Per-identity key -> the
    key-derived identity (body IGNORED). Shared-key mode -> the body field (honest-
    but-asserted, CALLER-1 semantics). Returns (seat, lineage, authenticated)."""
    ident = _authed_identity()
    if ident and ident.get("authenticated"):
        return ident.get("seat"), ident.get("lineage"), True
    return (body_seat or "").strip() or None, (body_lineage or "").strip() or None, False


def _ledger(op, status_or_none, *, begin=False, **kw):
    try:
        import file_server
        if begin:
            # caller = self-asserted seat (trusted-not-authenticated; see _caller_seat)
            return file_server._ops_begin(op, "SAFE", _caller_seat(), request.remote_addr, kw.get("args", {}))
        else:
            file_server._ops_finish(kw.get("op_id"), status_or_none, kw.get("result", ""))
    except Exception:
        return None


@seat_mailbox_bp.route("/op/mailbox_send", methods=["POST"])
def mailbox_send():
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    from_seat = (b.get("from_seat") or "").strip()
    to_seat   = (b.get("to_seat") or "").strip()
    kind      = (b.get("kind") or "note").strip()
    body      = b.get("body")
    if not from_seat or not to_seat or body is None:
        return jsonify({"error": "from_seat, to_seat, body required"}), 400
    if kind not in _KINDS:
        return jsonify({"error": f"kind must be one of {sorted(_KINDS)}"}), 400
    msg_id = str(uuid.uuid4())
    op_id = _ledger("mailbox_send", None, begin=True,
                    args={"from": from_seat, "to": to_seat, "kind": kind})
    try:
        c = _mb_conn()
        c.execute("""INSERT INTO seat_mailbox
            (msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,depends_on,body,status,created_at,reply_to,author_seat,author_lineage)
            VALUES (?,?,?,?,?,?,?,?,?, 'queued', ?, ?, ?, ?)""",
            (msg_id, from_seat, (b.get("from_lineage") or "").strip() or None, to_seat, kind,
             (b.get("block_id") or "").strip() or None, (b.get("ref") or "").strip() or None,
             (b.get("depends_on") or "").strip() or None, str(body), _now(),
             (b.get("reply_to") or "").strip() or None,
             (b.get("author_seat") or from_seat).strip() or None,
             (b.get("author_lineage") or (b.get("from_lineage") or "")).strip() or None))
        c.commit(); c.close()
        _ledger("mailbox_send", "ok", op_id=op_id, result=msg_id)
        return jsonify({"ok": True, "msg_id": msg_id})
    except Exception as e:
        _ledger("mailbox_send", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@seat_mailbox_bp.route("/op/mailbox_fetch", methods=["POST"])
def mailbox_fetch():
    """ATOMICALLY claim the oldest queued message addressed to this seat
    (by exact name OR by a role/broadcast target). Reclaims expired leases
    first so a dead worker's block returns to the queue."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    seat, _lin, _authed = _trusted_seat(b.get("seat"), b.get("lineage"))  # KEYS-2: key-derived if authenticated
    seat = seat or ""
    if not seat:
        return jsonify({"error": "seat required"}), 400
    # roles this seat will accept broadcast on (e.g. a worker accepts 'any_worker')
    roles = b.get("roles") or []
    block = (b.get("block_id") or "").strip()
    # CORRELATED FETCH: if reply_to is given, claim the specific result replying to
    # that task id (lets a requester pull *its own* result directly instead of
    # draining the whole queue oldest-first). If newest=true, claim newest-first.
    reply_to = (b.get("reply_to") or "").strip()
    newest = bool(b.get("newest"))
    targets = [seat] + [str(r) for r in roles]
    op_id = _ledger("mailbox_fetch", None, begin=True, args={"seat": seat, "roles": roles})
    try:
        c = _mb_conn()
        c.execute("BEGIN IMMEDIATE")  # serialize claimers — this is what makes it atomic
        # 1) reclaim expired claims back to queued
        c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                  "WHERE status='claimed' AND lease_until IS NOT NULL AND lease_until < ?", (_now(),))
        # 2) find queued for any of this seat's targets
        ph = ",".join("?" for _ in targets)
        params = list(targets)
        sql = (f"SELECT msg_id FROM seat_mailbox WHERE status='queued' AND to_seat IN ({ph})")
        # NOSELF-1: exclude reviewable items this seat authored (returns null if its own
        # is the only reviewable item -> the node long-polls on rather than self-signing).
        _nf, _np = _noself_predicate(seat, (_lin or b.get("lineage") or "").strip())  # KEYS-2: trusted lineage
        sql += _nf; params += _np
        if block:
            sql += " AND block_id=?"; params.append(block)
        if reply_to:
            sql += " AND reply_to=?"; params.append(reply_to)
        # correlated/newest fetch drains newest-first; default task-claim stays oldest-first (FIFO fairness)
        sql += (" ORDER BY created_at DESC LIMIT 1" if (reply_to or newest)
                else " ORDER BY created_at ASC LIMIT 1")
        row = c.execute(sql, params).fetchone()
        if not row:
            c.execute("COMMIT"); c.close()
            _ledger("mailbox_fetch", "ok", op_id=op_id, result="empty")
            return jsonify({"ok": True, "message": None})
        mid = row[0]
        lease = (datetime.now(timezone.utc) + timedelta(seconds=_LEASE_SECONDS)).isoformat()
        c.execute("UPDATE seat_mailbox SET status='claimed', claimed_by=?, claimed_at=?, lease_until=? "
                  "WHERE msg_id=? AND status='queued'", (seat, _now(), lease, mid))
        c.execute("COMMIT")
        m = c.execute("SELECT msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,depends_on,body,created_at,lease_until "
                      "FROM seat_mailbox WHERE msg_id=?", (mid,)).fetchone()
        c.close()
        cols = ["msg_id","from_seat","from_lineage","to_seat","kind","block_id","ref","depends_on","body","created_at","lease_until"]
        _ledger("mailbox_fetch", "ok", op_id=op_id, result=mid)
        return jsonify({"ok": True, "message": dict(zip(cols, m))})
    except Exception as e:
        try: c.execute("ROLLBACK"); c.close()
        except Exception: pass
        _ledger("mailbox_fetch", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@seat_mailbox_bp.route("/op/mailbox_ack", methods=["POST"])
def mailbox_ack():
    """Mark a claimed message done; optionally post a reply in the same call."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    msg_id = (b.get("msg_id") or "").strip()
    if not msg_id:
        return jsonify({"error": "msg_id required"}), 400
    # HARDEN-1 (SECAUDIT-1 rec): a seat may only ack a block IT claimed. The caller
    # names its seat; we reject acking a block whose claimed_by != that seat. PARTIAL
    # hardening: the seat name in the body is still SELF-ASSERTED (one shared DIAG_KEY),
    # so this assumes honest seat names. The full fix is per-identity keys (then the
    # claimed_by check becomes cryptographically attributable, not name-trust). Until
    # keys land, claimed_by-scoping stops accidental/cross cross-acks, not a forger.
    seat, _lin, _authed = _trusted_seat(b.get("seat"), b.get("lineage"))  # KEYS-2: key-derived if authenticated, else body
    seat = seat or ""
    op_id = _ledger("mailbox_ack", None, begin=True, args={"msg_id": msg_id, "seat": seat})
    try:
        c = _mb_conn()
        # Guard: if a seat is named, the block must have been claimed BY that seat.
        if seat:
            owner = c.execute("SELECT claimed_by, status FROM seat_mailbox WHERE msg_id=?", (msg_id,)).fetchone()
            if owner is None:
                c.close(); _ledger("mailbox_ack", "fail", op_id=op_id, result="no such msg")
                return jsonify({"error": "no such msg_id"}), 404
            if owner[0] is not None and owner[0] != seat:
                c.close(); _ledger("mailbox_ack", "fail", op_id=op_id,
                                   result=f"claimed_by={owner[0]} != seat={seat}")
                return jsonify({"error": "cannot ack a block you did not claim",
                                "claimed_by": owner[0], "seat": seat}), 403
            cur = c.execute("UPDATE seat_mailbox SET status='done', done_at=? "
                            "WHERE msg_id=? AND status!='done' AND (claimed_by=? OR claimed_by IS NULL)",
                            (_now(), msg_id, seat))
        else:
            cur = c.execute("UPDATE seat_mailbox SET status='done', done_at=? WHERE msg_id=? AND status!='done'",
                            (_now(), msg_id))
        acked = cur.rowcount
        reply_id = None
        reply = b.get("reply")
        if reply is not None:
            orig = c.execute("SELECT from_seat,to_seat,block_id,from_lineage FROM seat_mailbox WHERE msg_id=?", (msg_id,)).fetchone()
            if orig:
                reply_id = str(uuid.uuid4())
                # reply goes BACK to the original sender, from the original recipient
                c.execute("""INSERT INTO seat_mailbox
                    (msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,depends_on,body,status,created_at,reply_to)
                    VALUES (?,?,?,?, 'result', ?, ?, NULL, ?, 'queued', ?, ?)""",
                    (reply_id, orig[1], (b.get("from_lineage") or "").strip() or None, orig[0],
                     orig[2], (b.get("ref") or "").strip() or None, str(reply), _now(), msg_id))
        c.commit(); c.close()
        _ledger("mailbox_ack", "ok", op_id=op_id, result=f"acked={acked} reply={reply_id}")
        return jsonify({"ok": True, "acked": acked, "reply_id": reply_id})
    except Exception as e:
        _ledger("mailbox_ack", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@seat_mailbox_bp.route("/op/mailbox_peek", methods=["POST"])
def mailbox_peek():
    """Read-only inspection. No claim, no state change."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    where, params = [], []
    if b.get("seat"):     where.append("to_seat=?");   params.append(b["seat"].strip())
    if b.get("from_seat"):where.append("from_seat=?"); params.append(b["from_seat"].strip())
    if b.get("status"):   where.append("status=?");    params.append(b["status"].strip())
    if b.get("block_id"): where.append("block_id=?");  params.append(b["block_id"].strip())
    limit = max(1, min(int(b.get("limit", 20)), 100))
    sql = "SELECT msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,body,status,created_at,claimed_by,lease_until,done_at FROM seat_mailbox"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
    try:
        c = _mb_conn()
        rows = c.execute(sql, params).fetchall(); c.close()
        cols = ["msg_id","from_seat","from_lineage","to_seat","kind","block_id","ref","body","status","created_at","claimed_by","lease_until","done_at"]
        return jsonify({"ok": True, "count": len(rows), "messages": [dict(zip(cols, r)) for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@seat_mailbox_bp.route("/op/mailbox_purge", methods=["POST"])
def mailbox_purge():
    """Bulk-clear messages for a seat to stop result backlog from jamming the
    queue. By default purges only consumed/old RESULT and NOTE messages addressed
    to the seat (never queued tasks/proposals/reviews). Pass kinds=[...] to scope,
    older_than_secs to keep recent ones, or all=true to clear everything for the
    seat. Returns the count removed."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    seat = (b.get("seat") or "").strip()
    if not seat:
        return jsonify({"error": "seat required"}), 400
    purge_all = bool(b.get("all"))
    kinds = b.get("kinds") or (None if purge_all else ["result", "note"])
    older = b.get("older_than_secs")
    where = ["to_seat=?"]; params = [seat]
    if kinds:
        ph = ",".join("?" for _ in kinds)
        where.append(f"kind IN ({ph})"); params += list(kinds)
    if older is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=int(older))).isoformat()
        where.append("created_at < ?"); params.append(cutoff)
    sql = "DELETE FROM seat_mailbox WHERE " + " AND ".join(where)
    op_id = _ledger("mailbox_purge", None, begin=True, args={"seat": seat, "kinds": kinds, "all": purge_all})
    try:
        c = _mb_conn()
        c.execute("BEGIN IMMEDIATE")
        cur = c.execute(sql, params)
        n = cur.rowcount
        c.execute("COMMIT"); c.close()
        _ledger("mailbox_purge", "ok", op_id=op_id, result=str(n))
        return jsonify({"ok": True, "purged": n, "seat": seat})
    except Exception as e:
        try: c.execute("ROLLBACK"); c.close()
        except Exception: pass
        _ledger("mailbox_purge", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


@seat_mailbox_bp.route("/op/mailbox_reclaim", methods=["POST"])
def mailbox_reclaim():
    """Force-return expired claims to the queue (also runs inside fetch).
    Exposed standalone so a coordinator can sweep stalled blocks explicitly."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    # HARDEN-1 (SECAUDIT-1 rec): scope reclaim like ack. If a seat is named, only that
    # seat's OWN expired claims are returned to the queue. The unscoped global sweep
    # (a coordinator returning ALL stalled blocks) now requires an explicit all=true,
    # so a casual reclaim can't yank another seat's in-flight (if-expired) work by
    # default. PARTIAL: seat name is self-asserted until per-identity keys land —
    # this assumes honest seat names; keys make claimed_by attributable.
    seat, _lin, _authed = _trusted_seat(b.get("seat"), b.get("lineage"))  # KEYS-2
    seat = seat or ""
    sweep_all = bool(b.get("all"))
    op_id = _ledger("mailbox_reclaim", None, begin=True, args={"seat": seat, "all": sweep_all})
    try:
        c = _mb_conn()
        if seat and not sweep_all:
            cur = c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                            "WHERE status='claimed' AND claimed_by=? AND lease_until IS NOT NULL AND lease_until < ?",
                            (seat, _now()))
        elif sweep_all:
            cur = c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                            "WHERE status='claimed' AND lease_until IS NOT NULL AND lease_until < ?", (_now(),))
        else:
            c.close(); _ledger("mailbox_reclaim", "fail", op_id=op_id, result="no seat and not all")
            return jsonify({"error": "provide seat (scope to your own expired claims) or all=true (coordinator global sweep)"}), 400
        n = cur.rowcount; c.commit(); c.close()
        _ledger("mailbox_reclaim", "ok", op_id=op_id, result=f"reclaimed={n} scope={'all' if sweep_all else seat}")
        return jsonify({"ok": True, "reclaimed": n, "scope": "all" if sweep_all else seat})
    except Exception as e:
        _ledger("mailbox_reclaim", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


# ---------------------------------------------------------------------------
# you_there — long-poll mailbox wait (BOOTGATE sibling; spec live/specs/you_there_longpoll.md)
# ---------------------------------------------------------------------------
# WHAT THIS IS: a long-poll. It holds ONE open turn while the engine blocks
# server-side polling the mailbox, then returns the first WORK item (atomically
# claimed) or null after wait_seconds. A draining node calls it in a loop so the
# turn stays alive across many empty polls and the node self-drains blocks with
# zero human nudges.
#
# WHAT THIS IS NOT (ethics boundary, spec section 0): this is NOT turn-limit
# evasion. It does NOT reset, extend, or defeat the provider's per-turn budget
# (max tokens / max tool round-trips / wall-clock). Those are the provider's
# resource controls and we work WITHIN them. When the legitimate turn budget is
# reached, the turn ends; the shepherd re-enters the node in a fresh turn. We
# bridge turn boundaries openly; we do not pretend a turn is infinite. Nothing
# here is disguised.
#
# Placement note (worker1 inference -> control): the build block said box_ops.py,
# but the mailbox table, _mb_conn, the BEGIN IMMEDIATE atomic claim, _LEASE_SECONDS
# and the kind-set all live HERE in seat_mailbox.py. Putting you_there here REUSES
# the proven claim instead of duplicating it into box_ops.py (a second copy of the
# claim would risk drift). It is still a /op/ route reached via the same courier,
# so behavior to the caller is identical. Flagged for review.

_WORK_KINDS = {"task", "proposal"}          # spec section 3: NEVER note/result
_YT_WAIT_DEFAULT = 75
_YT_WAIT_CAP = 90                            # matches MODAL_TIMEOUT_AUTONOMOUS_S
_YT_POLL_INTERVAL = 2.0                      # poll every ~2s


def _yt_try_claim(seat, roles, block, lineage=""):
    """One atomic claim attempt for a WORK-kind item. Mirrors mailbox_fetch's
    BEGIN IMMEDIATE claim, but filters to _WORK_KINDS so a draining node never
    claims an ack (note/result). Returns the claimed message dict or None."""
    targets = [seat] + [str(r) for r in (roles or [])]
    c = _mb_conn()
    try:
        c.execute("BEGIN IMMEDIATE")  # serialize claimers — atomic, no double-claim
        # 1) reclaim expired claims back to queued (dead node's block returns to pool)
        c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                  "WHERE status='claimed' AND lease_until IS NOT NULL AND lease_until < ?", (_now(),))
        # 2) oldest queued WORK item for any of this seat's targets
        ph = ",".join("?" for _ in targets)
        kph = ",".join("?" for _ in _WORK_KINDS)
        params = list(targets) + list(_WORK_KINDS)
        sql = (f"SELECT msg_id FROM seat_mailbox WHERE status='queued' "
               f"AND to_seat IN ({ph}) AND kind IN ({kph})")
        # NOSELF-1: same guardrail on the long-poll claim path.
        _nf, _np = _noself_predicate(seat, lineage)
        sql += _nf; params += _np
        if block:
            sql += " AND block_id=?"; params.append(block)
        sql += " ORDER BY created_at ASC LIMIT 1"
        row = c.execute(sql, params).fetchone()
        if not row:
            c.execute("COMMIT"); c.close()
            return None
        mid = row[0]
        lease = (datetime.now(timezone.utc) + timedelta(seconds=_LEASE_SECONDS)).isoformat()
        c.execute("UPDATE seat_mailbox SET status='claimed', claimed_by=?, claimed_at=?, lease_until=? "
                  "WHERE msg_id=? AND status='queued'", (seat, _now(), lease, mid))
        c.execute("COMMIT")
        m = c.execute("SELECT msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,depends_on,body,created_at,lease_until "
                      "FROM seat_mailbox WHERE msg_id=?", (mid,)).fetchone()
        c.close()
        cols = ["msg_id","from_seat","from_lineage","to_seat","kind","block_id","ref","depends_on","body","created_at","lease_until"]
        return dict(zip(cols, m))
    except Exception:
        try: c.execute("ROLLBACK"); c.close()
        except Exception: pass
        raise


@seat_mailbox_bp.route("/op/you_there", methods=["POST"])
def you_there():
    """Long-poll: block server-side up to wait_seconds, polling every ~2s for a
    WORK item (kind in {task, proposal} ONLY — never note/result), atomically
    claim and return the first one found. Return {message:null, waited} on
    timeout so the node immediately re-polls (turn stays alive across empties).
    SAFE tier (read-only wait + a claim, same mutation class as mailbox_fetch).
    NOT a turn-budget evasion — see module note; the provider's turn budget still
    ends the turn, the shepherd re-enters in a fresh one."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    b = request.get_json(silent=True) or {}
    seat, _ylin, _yauthed = _trusted_seat(b.get("seat"), b.get("lineage"))  # KEYS-2
    seat = seat or ""
    if not seat:
        return jsonify({"error": "seat required"}), 400
    roles = b.get("roles") or []
    block = (b.get("block_id") or "").strip()
    lineage = (_ylin or b.get("lineage") or "").strip()  # KEYS-2: trusted lineage if authenticated
    try:
        wait_seconds = int(b.get("wait_seconds", _YT_WAIT_DEFAULT))
    except (TypeError, ValueError):
        wait_seconds = _YT_WAIT_DEFAULT
    wait_seconds = max(0, min(wait_seconds, _YT_WAIT_CAP))  # hard cap 90, never a long hang
    op_id = _ledger("you_there", None, begin=True,
                    args={"seat": seat, "roles": roles, "wait_seconds": wait_seconds})
    import time as _time
    deadline = _time.monotonic() + wait_seconds
    polls = 0
    try:
        while True:
            polls += 1
            msg = _yt_try_claim(seat, roles, block, lineage)
            if msg is not None:
                _ledger("you_there", "ok", op_id=op_id,
                        result=f"claimed {msg['msg_id']} kind={msg['kind']} polls={polls}")
                return jsonify({"ok": True, "message": msg, "waited": polls})
            if _time.monotonic() >= deadline:
                _ledger("you_there", "ok", op_id=op_id, result=f"timeout polls={polls}")
                return jsonify({"ok": True, "message": None, "waited": wait_seconds})
            # sleep but don't overshoot the deadline
            _time.sleep(min(_YT_POLL_INTERVAL, max(0.0, deadline - _time.monotonic())))
    except Exception as e:
        _ledger("you_there", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500



_mailbox_init()
