# ── GOVERNOR CONSOLE ──────────────────────────────────────────────────
# Read-only operator observatory. Page served openly (no secrets in it);
# all DATA goes through /governor/data which reuses auth_required (X-API-Key).
# Data is fetched server-side from the diag endpoints, so the browser only
# ever talks same-origin to this server.
import urllib.request as _ug_req, urllib.parse as _ug_parse

_GOV_MAIN = "https://web-production-7eaf8.up.railway.app"
_GOV_FARM = "https://ontinuity-farm-production.up.railway.app"
_GOV_BOUNDARY = "2026-06-08_0"

def _gov_diag(base, path, params):
    cfg = load_config()
    dk = cfg.get("diag_key", "")
    p = dict(params); p["diag_key"] = dk
    url = f"{base}{path}?{_ug_parse.urlencode(p)}"
    try:
        # short timeout: this server is single-threaded and the Governor polls
        # every 6s; a slow upstream must fail fast or polls stack and saturate it.
        return json.loads(_ug_req.urlopen(url, timeout=4).read().decode())
    except Exception as e:
        return {"error": str(e)}

def _gov_q(sql):
    r = _gov_diag(_GOV_MAIN, "/diag/api/query", {"sql": sql})
    try:
        return r["rows"]
    except Exception:
        return None

@app.route("/governor")
def governor_page():
    try:
        with open(os.path.join(os.path.dirname(__file__), "governor.html")) as fh:
            return fh.read()
    except Exception as e:
        return f"governor.html not found beside file_server.py: {e}", 500

@app.route("/governor/data")
@auth_required
def governor_data():
    out = {"boundary": _GOV_BOUNDARY}
    out["main"] = _gov_diag(_GOV_MAIN, "/diag/engine", {})
    out["farm"] = _gov_diag(_GOV_FARM, "/diag/engine", {})
    rnd = _gov_q(f"SELECT COUNT(*) FROM behavioral_observations WHERE randomized_flag=1 AND session_id >= '{_GOV_BOUNDARY}'")
    ses = _gov_q(f"SELECT COUNT(DISTINCT session_id) FROM behavioral_observations WHERE computed_signal IS NOT NULL AND session_id >= '{_GOV_BOUNDARY}'")
    rec = _gov_q("SELECT MAX(receipt_id) FROM write_receipts")
    bks = _gov_q(f"SELECT status, COUNT(*) FROM sessions WHERE session_id >= '{_GOV_BOUNDARY}' GROUP BY status")
    out["randomized"] = rnd[0][0] if rnd else None
    out["sessions"] = ses[0][0] if ses else None
    out["receipt"] = rec[0][0] if rec else None
    out["buckets"] = {row[0]: row[1] for row in bks} if bks else {}
    return jsonify(out)

# ── WORKER STATUS (Governor Phase 1) ──────────────────────────────────
# Read-only roster + per-seat status derived ENTIRELY from seat_mailbox (no
# schema change; the registry/liveness build comes later). All four dimensions
# verified live 2026-06-30. The point of the panel: at a glance, who is alive,
# what each seat last did, and — the operator's real question — who is
# IDLE-WITH-WORK (holds no claim but has claimable work waiting) = who to nudge.

# Seats that are system/plumbing identities, not named worker/control seats we
# corral on the pane. Kept explicit so a new worker name is never hidden.
_GOV_POOL_SEATS = ("any_worker",)  # the shared pool target, shown as a lane not a seat

# WHO IS SHOWN AS A LIVE SEAT — until the Phase-3 registry gives a real last-poll
# heartbeat, "last mailed" is all we have, and a quietly-polling live worker looks
# identical to a retired one. So two controls, OR'd together (a seat shows if ANY
# holds), with retirement able to override:
#   _GOV_ACTIVE_SEATS  — the seats YOU declare live right now. Always shown, always
#                        treated as active. Edit this when you spin workers up/down.
#   _GOV_ROSTER_WINDOW_H — backstop: a seat that mailed within this window still
#                        shows even if not on the list (catches a new worker you
#                        haven't listed yet). A seat with pending work or a live
#                        claim is ALWAYS shown regardless.
#   _GOV_RETIRED_SEATS — hard override: these never show, even if recently active.
_GOV_ACTIVE_SEATS = ("worker11", "worker22")   # <-- the live workers; edit as you scale
_GOV_RETIRED_SEATS = ("worker2", "worker4", "worker-review", "control-seat",
                      "kb_ipad", "kb_laptop", "operator")
_GOV_ROSTER_WINDOW_H = 48  # backstop window (hours) for an unlisted but recent seat

def _gov_workers_data():
    # 1) roster: every seat that has sent mail, with volume + recency
    roster = _gov_q(
        "SELECT from_seat, COUNT(*) msgs, MAX(created_at) last_seen "
        "FROM seat_mailbox GROUP BY from_seat") or []
    # 2) last thing each seat DID (its most recent message's kind)
    lastkind = _gov_q(
        "SELECT s.from_seat, s.kind FROM seat_mailbox s "
        "JOIN (SELECT from_seat, MAX(created_at) mx FROM seat_mailbox GROUP BY from_seat) m "
        "ON s.from_seat=m.from_seat AND s.created_at=m.mx") or []
    last_by_seat = {r[0]: r[1] for r in lastkind}
    # 3) what each seat is CURRENTLY holding (an active atomic claim + its lease)
    held = _gov_q(
        "SELECT claimed_by, COUNT(*) held, MAX(lease_until) lease "
        "FROM seat_mailbox WHERE status='claimed' AND claimed_by IS NOT NULL "
        "GROUP BY claimed_by") or []
    held_by_seat = {r[0]: {"held": r[1], "lease": r[2]} for r in held}
    # 4) queued work waiting, split by to_seat + kind (who has mail, of what kind)
    waiting = _gov_q(
        "SELECT to_seat, kind, COUNT(*) n FROM seat_mailbox "
        "WHERE status='queued' GROUP BY to_seat, kind") or []
    wait_by_seat = {}
    for to_seat, kind, n in waiting:
        wait_by_seat.setdefault(to_seat, {})[kind] = n
    # the shared pool of claimable build/review work (addressed to any_worker):
    # any worker (except an item's own author) can drain this — this is the lane,
    # not a seat. Reviewable + task kinds are what a draining worker acts on.
    pool = wait_by_seat.get("any_worker", {})
    pool_claimable = sum(v for k, v in pool.items() if k in ("task", "proposal", "review_finding", "signoff"))

    seats = []
    _now = _now_dt()
    for from_seat, msgs, last_seen in roster:
        if from_seat in _GOV_POOL_SEATS:
            continue  # any_worker is a lane, surfaced separately, not a seat row
        my_wait = wait_by_seat.get(from_seat, {})
        # claimable work addressed specifically to this seat (reviewables + tasks)
        direct_claimable = sum(v for k, v in my_wait.items()
                               if k in ("task", "proposal", "review_finding", "signoff"))
        holding = held_by_seat.get(from_seat)
        is_control = from_seat in ("control", "control-seat")
        declared_active = from_seat in _GOV_ACTIVE_SEATS
        pending = direct_claimable + len(my_wait)
        silent_h = _hours_since(last_seen, _now)
        recent = (silent_h is not None) and (silent_h <= _GOV_ROSTER_WINDOW_H)
        # DROP a seat only if: hard-retired, OR (not declared-active AND not control
        # AND no pending work AND not holding AND not recent). Retirement overrides
        # everything except a live claim or pending work you'd need to see.
        keep = (is_control or declared_active or pending > 0
                or holding is not None or recent)
        if from_seat in _GOV_RETIRED_SEATS and holding is None and pending == 0:
            keep = False
        if not keep:
            continue
        # idle-with-work = the nudge signal: not currently holding a claim, but
        # there is claimable work it could take (its own direct queue OR the pool).
        # Control is the operator's OWN seat (this conversation) — never a nudge
        # target; its inbound queue is the review/commit chain, surfaced not armed.
        idle_with_work = (not is_control) and (holding is None) and (direct_claimable + pool_claimable > 0)
        seats.append({
            "seat": from_seat,
            "is_control": is_control,
            "declared_active": declared_active,
            "msgs": msgs,
            "last_seen": last_seen,
            "last_kind": last_by_seat.get(from_seat),
            "holding": holding,                       # {held, lease} or None
            "waiting": my_wait,                       # {kind: n} addressed to this seat
            "direct_claimable": direct_claimable,     # claimable items addressed to it
            "idle_with_work": idle_with_work,
        })
    # newest-active first
    seats.sort(key=lambda s: s["last_seen"] or "", reverse=True)
    return {
        "seats": seats,
        "pool": {"kinds": pool, "claimable": pool_claimable},
        "server_now": _now_iso(),
    }

def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def _now_dt():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

def _hours_since(iso_str, now_dt):
    # hours between an ISO timestamp and now; None if unparseable (never retire on
    # a parse failure — safer to over-show than to silently hide a live seat)
    if not iso_str:
        return None
    try:
        from datetime import datetime
        t = datetime.fromisoformat(iso_str)
        return (now_dt - t).total_seconds() / 3600.0
    except Exception:
        return None

@app.route("/governor/workers")
@auth_required
def governor_workers():
    return jsonify(_gov_workers_data())
