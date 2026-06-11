#!/usr/bin/env python3
"""
Shepherd — detect-and-alert driver (VPS-resident).
============================================================================
The you_there long-poll keeps a chat node self-draining WITHIN one turn. The
provider's turn budget eventually ends that turn. The shepherd's job is the
ACROSS-turn gap: notice when a node has queued work but has gone quiet (its turn
ended), and get it going again.

CONFIRMED GAP (honest, do not paper over): software cannot give a CHAT-WINDOW
conversation a turn — there is no API to inject a turn into a frontier chat UI
session. So for chat nodes the shepherd does NOT re-enter; it ALERTS a human,
who gives the nudge. (Engine/farm nodes are different: they have a start/wake
path — that re-entry is the burn-in shepherd's job, live/shepherd.py — out of
scope here.) This driver is the detect-and-alert half: the cheap, real thing we
can build today. The auto-re-entry half waits on a chat re-entry mechanism that
does not yet exist.

LIVENESS SIGNAL (grounded, with a flagged limitation):
  operations_ledger.caller is 'diag-key' for EVERY row today — the box ledger
  helper hardcodes it, so ops_ledger CANNOT attribute a heartbeat to a seat yet
  (same self-asserted-identity gap the bootstrap gate + HARDEN-1 flagged). So
  this shepherd keys per-seat liveness on seat_mailbox.claimed_by instead — the
  one column that DOES carry the seat name today: a seat's last activity =
  MAX(done_at, claimed_at, created_at) over rows it claimed. FLAG -> control:
  when you_there logs to ops_ledger, stamp the seat into caller (one-line box
  fix); then liveness can key on the you_there heartbeat the spec intended, and
  a node sitting in an empty long-poll (claiming nothing) still shows alive. Until
  then a node that is polling-but-not-claiming looks idle here — acceptable for a
  detect-and-ALERT (false 'idle' costs one human glance, not a wrong action).

NO-SPAM: one alert per idle-with-work TRANSITION. State is held in a tiny JSON
file; an alerted node is not re-alerted until it resumes (activity advances) and
later goes idle-with-work again.

RUN (setsid-detached, the working VPS pattern; sandbox process-reaping otherwise
kills it): setsid python3 shepherd_alert.py >> /home/claude/shepherd_alert.out 2>&1 &
Or as a systemd unit (Restart=always) like ontinuity-burnin.
"""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone

ENGINE = "https://web-production-7eaf8.up.railway.app"
DIAG = (open("/home/claude/diagkey.txt").read().strip()
        if os.path.exists("/home/claude/diagkey.txt")
        else os.environ.get("DIAG_KEY", ""))

POLL_S = 60                       # check cadence
IDLE_THRESHOLD_S = 300            # no activity for >5min + queued work = idle-with-work
WORKER_ROLES = ("any_worker",)    # broadcast targets whose queue depth matters
KNOWN_SEATS = ("worker1", "worker2", "control")  # seats to watch; extend as nodes register
ALERTS_FILE = "/home/claude/shepherd_alerts.jsonl"
STATE_FILE = "/home/claude/shepherd_alert_state.json"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _q(sql):
    url = f"{ENGINE}/diag/api/query?diag_key={DIAG}&sql=" + urllib.parse.quote(sql)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def _op(name, body):
    url = f"{ENGINE}/diag/op/{name}?diag_key={DIAG}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def queue_depth():
    """Unclaimed task/proposal count for the worker broadcast roles."""
    roles = ",".join("'%s'" % r for r in WORKER_ROLES)
    sql = (f"SELECT COUNT(*) FROM seat_mailbox WHERE status='queued' "
           f"AND to_seat IN ({roles}) AND kind IN ('task','proposal')")
    try:
        return int(_q(sql)["rows"][0][0])
    except Exception:
        return -1  # query failed; treat as unknown (no alert decision)


def seat_last_activity():
    """Per-seat last activity from seat_mailbox.claimed_by (the available signal).
    Returns {seat: iso_ts}. Seats with no claims ever are absent (treated stale)."""
    sql = ("SELECT claimed_by, MAX(COALESCE(done_at, claimed_at, created_at)) "
           "FROM seat_mailbox WHERE claimed_by IS NOT NULL GROUP BY claimed_by")
    out = {}
    try:
        for row in _q(sql)["rows"]:
            out[row[0]] = row[1]
    except Exception:
        pass
    return out


def _age_s(iso_ts):
    if not iso_ts:
        return None
    try:
        t = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return None


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {"alerted": {}}  # seat -> last_activity_ts at time of alert


def save_state(s):
    tmp = STATE_FILE + ".tmp"
    json.dump(s, open(tmp, "w"))
    os.replace(tmp, STATE_FILE)


def emit_alert(seat, depth, age_s):
    line = (f"[SHEPHERD ALERT] node '{seat}' idle ~{int(age_s)}s with {depth} "
            f"block(s) queued — needs a turn (chat re-entry is manual). {_now()}")
    # 1) durable alert row
    with open(ALERTS_FILE, "a") as f:
        f.write(json.dumps({"t": _now(), "seat": seat, "queue_depth": depth,
                            "idle_s": int(age_s), "kind": "idle_with_work"}) + "\n")
    # 2) a mailbox note to the operator (single line; note kind so a draining node
    #    never claims it as work — the work-vs-chatter filter excludes 'note')
    try:
        _op("mailbox_send", {"from_seat": "shepherd", "from_lineage": "vps:shepherd_alert",
                             "to_seat": "operator", "kind": "note", "body": line})
    except Exception:
        pass
    print(line, flush=True)


def clear_alert_note(seat):
    print(f"[SHEPHERD] node '{seat}' resumed — alert cleared {_now()}", flush=True)


def tick():
    depth = queue_depth()
    if depth <= 0:
        # no queued work -> nothing can be idle-WITH-WORK; clear all alerts
        st = load_state()
        if st["alerted"]:
            for seat in list(st["alerted"]):
                clear_alert_note(seat)
            st["alerted"] = {}
            save_state(st)
        return
    activity = seat_last_activity()
    st = load_state()
    for seat in KNOWN_SEATS:
        last = activity.get(seat)
        age = _age_s(last)
        idle = (age is None) or (age > IDLE_THRESHOLD_S)
        already = seat in st["alerted"]
        if idle and not already:
            emit_alert(seat, depth, age if age is not None else IDLE_THRESHOLD_S)
            st["alerted"][seat] = last or "never"
        elif not idle and already:
            # node resumed (activity advanced past the alert snapshot)
            if st["alerted"].get(seat) != last:
                clear_alert_note(seat)
                del st["alerted"][seat]
    save_state(st)


def main():
    if not DIAG:
        print("[SHEPHERD] no DIAG key (diagkey.txt or DIAG_KEY env) — cannot query; exiting.", flush=True)
        return
    print(f"[SHEPHERD] detect-and-alert loop start (poll={POLL_S}s, idle>{IDLE_THRESHOLD_S}s) {_now()}", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[SHEPHERD] tick error: {str(e)[:200]} {_now()}", flush=True)
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
