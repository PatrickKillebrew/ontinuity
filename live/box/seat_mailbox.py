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
def _ledger(op, status_or_none, *, begin=False, **kw):
    try:
        import file_server
        if begin:
            return file_server._ops_begin(op, "SAFE", "diag-key", request.remote_addr, kw.get("args", {}))
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
            (msg_id,from_seat,from_lineage,to_seat,kind,block_id,ref,depends_on,body,status,created_at,reply_to)
            VALUES (?,?,?,?,?,?,?,?,?, 'queued', ?, ?)""",
            (msg_id, from_seat, (b.get("from_lineage") or "").strip() or None, to_seat, kind,
             (b.get("block_id") or "").strip() or None, (b.get("ref") or "").strip() or None,
             (b.get("depends_on") or "").strip() or None, str(body), _now(),
             (b.get("reply_to") or "").strip() or None))
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
    seat = (b.get("seat") or "").strip()
    if not seat:
        return jsonify({"error": "seat required"}), 400
    # roles this seat will accept broadcast on (e.g. a worker accepts 'any_worker')
    roles = b.get("roles") or []
    block = (b.get("block_id") or "").strip()
    targets = [seat] + [str(r) for r in roles]
    op_id = _ledger("mailbox_fetch", None, begin=True, args={"seat": seat, "roles": roles})
    try:
        c = _mb_conn()
        c.execute("BEGIN IMMEDIATE")  # serialize claimers — this is what makes it atomic
        # 1) reclaim expired claims back to queued
        c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                  "WHERE status='claimed' AND lease_until IS NOT NULL AND lease_until < ?", (_now(),))
        # 2) find oldest queued for any of this seat's targets
        ph = ",".join("?" for _ in targets)
        params = list(targets)
        sql = (f"SELECT msg_id FROM seat_mailbox WHERE status='queued' AND to_seat IN ({ph})")
        if block:
            sql += " AND block_id=?"; params.append(block)
        sql += " ORDER BY created_at ASC LIMIT 1"
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
    op_id = _ledger("mailbox_ack", None, begin=True, args={"msg_id": msg_id})
    try:
        c = _mb_conn()
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


@seat_mailbox_bp.route("/op/mailbox_reclaim", methods=["POST"])
def mailbox_reclaim():
    """Force-return expired claims to the queue (also runs inside fetch).
    Exposed standalone so a coordinator can sweep stalled blocks explicitly."""
    if not _diag_ok():
        return jsonify({"error": "unauthorized"}), 401
    op_id = _ledger("mailbox_reclaim", None, begin=True, args={})
    try:
        c = _mb_conn()
        cur = c.execute("UPDATE seat_mailbox SET status='queued', claimed_by=NULL, claimed_at=NULL, lease_until=NULL "
                        "WHERE status='claimed' AND lease_until IS NOT NULL AND lease_until < ?", (_now(),))
        n = cur.rowcount; c.commit(); c.close()
        _ledger("mailbox_reclaim", "ok", op_id=op_id, result=f"reclaimed={n}")
        return jsonify({"ok": True, "reclaimed": n})
    except Exception as e:
        _ledger("mailbox_reclaim", "fail", op_id=op_id, result=str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


_mailbox_init()
