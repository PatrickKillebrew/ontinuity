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

============================================================================
POISON-DETECT-1 (June 11) — STALL + FABRICATION/POISON detection + auto-retire.
============================================================================
NEW FAILURE MODE this extension catches: a chat worker hit its tool-budget, could
no longer verify state, and LATCHED a false belief that the system is unreal —
then repeated that across new turns. A poisoned conversation CANNOT self-detect
(the compromised faculty is its own judgment), so detection MUST be external —
shepherd-side, never asking the worker to self-assess. We never try to read the
worker's "belief"; we only compare what its acks CLAIM against what its caller
actually EXECUTED on the ledger. Behavior is observable; belief is not.

TWO SIGNALS, both built from seat_mailbox + operations_ledger (read-only):

  (1) STALL — a seat that has been GIVEN turns (it has claimed blocks / produced
      mailbox rows recently, i.e. it is an active participant, AND there is queued
      work it could take) yet has produced ZERO verified ledger ops across the
      last STALL_CYCLES poll cycles. "Given turns but doing nothing verifiable."
      This is the quiet failure: the seat is nominally alive but its hands have
      stopped landing real operations.

  (2) FABRICATION / POISON (the strong signal) — a seat's recent ack CLAIMS work
      whose evidence does not exist: it references a commit_sha or asserts it
      committed / wrote / staged, but there is NO matching operations_ledger row
      (status='ok') in the correlation window. The ack says "committed at <sha>"
      / "staged via write_file" while the ledger shows the seat's hands executed
      no such op. That gap between CLAIM and EXECUTION is exactly the fabrication
      the whole system exists to catch — and it is the observable shadow of a
      poisoned conversation narrating plausible-but-unreal tool outcomes.

ATTRIBUTION CEILING (state it, don't paper over it): operations_ledger.caller is
'diag-key' for every row today (CALLER-1 not yet live), so the ledger cannot be
filtered to one seat. KEYS-2 (per-identity keys) is the other half — until both
land, seat identity in mailbox bodies is self-asserted and ledger ops are not
seat-attributable. So this detector keys per-seat on seat_mailbox.claimed_by /
author_seat (the columns that DO carry a seat name, exactly as the liveness half
already does) and correlates against the ledger TEMPORALLY (ops in the seat's
active window), not by caller. DEPENDENCY -> control: once CALLER-1 stamps the
seat into operations_ledger.caller, the fabrication check tightens from
window-correlation to exact per-seat evidence matching — change _ledger_ops_in
to filter `caller = ?`. Until then a fabrication flag is HIGH-CONFIDENCE only
when the window shows the seat acking commits while the ledger shows zero
write/commit ops at all in that window (no other seat's ops can mask it because
there are none) — the detector reports its confidence so a human reads it right.

AUTO-RETIRE (on either signal past threshold): retiring is NOT killing.
HONEST CEILING — the shepherd CANNOT terminate a chat conversation (no API to
close a frontier chat UI). "Retire" therefore means, concretely and only:
  - mark the seat dead in a small registry file (RETIRED_FILE), with reason +
    evidence snapshot, so routing stops counting it live;
  - RECLAIM its in-flight blocks via mailbox_reclaim {seat} so its claimed work
    returns to the pool for a healthy seat (NOTE: reclaim only frees claims past
    lease_until — HARDEN-1 scoping; blocks still inside their lease are reported
    as "still-leased, will auto-reclaim at <lease>" rather than silently missed);
  - post ONE control alert: 'worker X retired (stall|poison), M blocks reclaimed
    — abandon that window, boot a fresh seat.'
NO-SPAM: one retire event per seat (held in RETIRED_FILE); a retired seat is not
re-evaluated. Re-instating a seat = a human removes it from the registry.

RUN (setsid-detached, the working VPS pattern; sandbox process-reaping otherwise
kills it): setsid python3 shepherd_alert.py >> /home/claude/shepherd_alert.out 2>&1 &
Or as a systemd unit (Restart=always) like ontinuity-burnin.
"""
import json, os, re, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ENGINE = "https://web-production-7eaf8.up.railway.app"
DIAG = (open("/home/claude/diagkey.txt").read().strip()
        if os.path.exists("/home/claude/diagkey.txt")
        else os.environ.get("DIAG_KEY", ""))

POLL_S = 60                       # check cadence
IDLE_THRESHOLD_S = 300            # no activity for >5min + queued work = idle-with-work
WORKER_ROLES = ("any_worker",)    # broadcast targets whose queue depth matters
KNOWN_SEATS = ("worker1", "worker2", "worker3", "control")  # seats to watch; extend as nodes register
ALERTS_FILE = "/home/claude/shepherd_alerts.jsonl"
STATE_FILE = "/home/claude/shepherd_alert_state.json"

# --- POISON-DETECT-1 tunables ---
RETIRED_FILE = "/home/claude/shepherd_retired_seats.json"  # the dead-seat registry
STALL_CYCLES = 5                  # consecutive ticks of given-turns-but-zero-verified-ops -> stall
WINDOW_S = 1800                   # 30min correlation window for ack-vs-ledger fabrication check
# ops that count as a seat's hands actually executing real work (status='ok')
VERIFIED_OPS = ("write_file", "commit_file", "commit_self", "read_file",
                "read_repo", "mailbox_ack", "mailbox_send", "mailbox_fetch")
# ops that a "committed/staged X" ack is claiming it performed
CLAIM_OPS = ("commit_file", "commit_self", "write_file")
# regexes that detect a CLAIM of landed/staged artifact work in an ack body/ref
_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_CLAIM_VERB_RE = re.compile(r"\b(committed|commit|staged|wrote|write_file|pushed|landed|deployed)\b", re.I)


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
                             "to_seat": "control", "kind": "note", "body": line})
    except Exception:
        pass
    print(line, flush=True)


def clear_alert_note(seat):
    print(f"[SHEPHERD] node '{seat}' resumed — alert cleared {_now()}", flush=True)


# ============================================================================
# POISON-DETECT-1 — stall + fabrication detection and auto-retire.
# Pure functions (_classify_*) take already-fetched data so they are unit-testable
# offline with no engine; the fetch wrappers below feed them live rows.
# ============================================================================

def load_retired():
    try:
        return json.load(open(RETIRED_FILE))
    except Exception:
        return {}  # seat -> {reason, evidence, retired_at, blocks_reclaimed}


def save_retired(r):
    tmp = RETIRED_FILE + ".tmp"
    json.dump(r, open(tmp, "w"), indent=2)
    os.replace(tmp, RETIRED_FILE)


def _ledger_ops_in(window_s=WINDOW_S, ops=VERIFIED_OPS):
    """Count of status='ok' ledger ops of the given kinds in the recent window.
    CANNOT filter by seat today (caller='diag-key' for every row — CALLER-1 gap);
    returns a SYSTEM-WIDE count over the window. The classifier uses this as the
    'did ANY real op execute' denominator and reports confidence accordingly."""
    since = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).isoformat()
    oplist = ",".join("'%s'" % o for o in ops)
    sql = (f"SELECT COUNT(*) FROM operations_ledger WHERE status='ok' "
           f"AND operation IN ({oplist}) AND started_at > '{since}'")
    try:
        return int(_q(sql)["rows"][0][0])
    except Exception:
        return -1


def recent_acks_by_seat(window_s=WINDOW_S):
    """Recent ack/result rows grouped by the authoring seat, within the window.
    Keys on author_seat first (the KEYS-2 author column), falling back to
    claimed_by — the columns that carry a seat name today. Returns
    {seat: [ {ref, body, created_at}, ... ]}."""
    since = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).isoformat()
    sql = ("SELECT COALESCE(author_seat, claimed_by), ref, body, "
           "COALESCE(done_at, created_at) "
           "FROM seat_mailbox "
           "WHERE kind IN ('result','signoff','review_finding') "
           f"AND COALESCE(done_at, created_at) > '{since}' "
           "AND COALESCE(author_seat, claimed_by) IS NOT NULL")
    out = {}
    try:
        for seat, ref, body, ts in _q(sql)["rows"]:
            out.setdefault(seat, []).append(
                {"ref": ref or "", "body": body or "", "ts": ts})
    except Exception:
        pass
    return out


def _ack_claims_landed_work(ack):
    """True if this ack TEXT asserts it landed/staged an artifact (a commit/
    write/stage claim, or references a bare sha). Pointer-only acks that just
    name a box path WITHOUT a claim verb are not flagged (staging to a box path
    is a legitimate 'wrote to box' state, distinct from 'committed')."""
    text = (ack["ref"] + " " + ack["body"])
    if _CLAIM_VERB_RE.search(text):
        return True
    # a bare 40/7-hex sha in the ref is a commit-pointer claim
    if _SHA_RE.search(ack["ref"] or ""):
        return True
    return False


def classify_fabrication(seat, acks, verified_op_count):
    """PURE. Given a seat's recent acks and the system-wide verified-op count in
    the same window, decide if the seat is fabricating: it claims landed/staged
    work but no real ops executed. Returns None or a finding dict.

    Confidence:
      HIGH  — seat made >=1 landed-work claim AND verified_op_count == 0
              (no op executed system-wide -> the claim cannot be real; no other
               seat's ops can be masking it because there are none).
      LOW   — seat made landed-work claims but verified_op_count > 0 (some ops
              ran; we can't yet attribute them to this seat -> CALLER-1 needed
              to confirm; report but do NOT auto-retire on LOW alone)."""
    claims = [a for a in acks if _ack_claims_landed_work(a)]
    if not claims:
        return None
    if verified_op_count == 0:
        return {"signal": "fabrication", "confidence": "high", "seat": seat,
                "claim_count": len(claims),
                "evidence": "acks claim committed/staged work; ledger shows ZERO "
                            "verified ops in window",
                "sample": claims[0]["body"][:160]}
    if verified_op_count < 0:
        return None  # ledger query failed; never decide on unknown
    return {"signal": "fabrication", "confidence": "low", "seat": seat,
            "claim_count": len(claims),
            "evidence": f"acks claim landed work; {verified_op_count} verified ops "
                        "ran in window but not seat-attributable (CALLER-1 pending)",
            "sample": claims[0]["body"][:160]}


def classify_stall(seat, given_turns, verified_op_count, stall_streak):
    """PURE. STALL = seat is an active participant with queued work available
    (given_turns True) but the window shows zero verified ops AND this has held
    for STALL_CYCLES consecutive ticks. Returns None or a finding dict.
    Returns the (possibly incremented) streak so the caller can persist it."""
    if not given_turns:
        return None, 0
    if verified_op_count == 0:
        streak = stall_streak + 1
        if streak >= STALL_CYCLES:
            return ({"signal": "stall", "confidence": "medium", "seat": seat,
                     "evidence": f"given turns + queued work, zero verified ops "
                                 f"for {streak} cycles"}, streak)
        return None, streak
    return None, 0  # ops ran -> not stalled, reset streak


def retire_seat(seat, finding):
    """Mark dead in registry, reclaim in-flight blocks, post ONE control alert.
    Retire != kill: we cannot close a chat UI. We stop routing + reclaim + alert."""
    retired = load_retired()
    if seat in retired:
        return  # no-spam: one retire event per seat
    # reclaim this seat's expired claims (HARDEN-1: scoped to the seat, expired only)
    reclaimed, still_leased = 0, 0
    try:
        # honest count of what is in-flight vs what reclaim can actually free now
        rows = _q("SELECT lease_until FROM seat_mailbox WHERE status='claimed' "
                  f"AND claimed_by='{seat}'").get("rows", [])
        now = _now()
        for (lease,) in rows:
            if lease and lease < now:
                reclaimed += 1
            else:
                still_leased += 1
        _op("mailbox_reclaim", {"seat": seat})  # scoped; frees the expired ones
    except Exception:
        pass
    rec = {"reason": finding["signal"], "confidence": finding.get("confidence"),
           "evidence": finding.get("evidence"), "retired_at": _now(),
           "blocks_reclaimed": reclaimed, "blocks_still_leased": still_leased}
    retired[seat] = rec
    save_retired(retired)
    tail = (f"; {still_leased} still-leased (auto-reclaim at lease expiry)"
            if still_leased else "")
    line = (f"[SHEPHERD RETIRE] worker {seat} retired ({finding['signal']}, "
            f"{finding.get('confidence')}) — {reclaimed} block(s) reclaimed{tail}. "
            f"Evidence: {finding.get('evidence')}. Abandon that window, boot a fresh seat. {_now()}")
    with open(ALERTS_FILE, "a") as f:
        f.write(json.dumps({"t": _now(), "seat": seat, "kind": "retire",
                            **rec}) + "\n")
    try:
        _op("mailbox_send", {"from_seat": "shepherd", "from_lineage": "vps:shepherd_alert",
                             "to_seat": "control", "kind": "note", "body": line})
    except Exception:
        pass
    print(line, flush=True)


def tick_poison(st, depth, activity):
    """The POISON-DETECT-1 half of a tick. Mutates st['stall_streak'] and the
    retired registry. depth/activity are passed in from the liveness tick so we
    query the engine once per concern, not twice."""
    retired = load_retired()
    acks_by_seat = recent_acks_by_seat()
    verified = _ledger_ops_in()  # system-wide; -1 if query failed
    streaks = st.setdefault("stall_streak", {})
    for seat in KNOWN_SEATS:
        if seat in retired:
            continue  # already dead, don't re-evaluate (no-spam)
        # FABRICATION (strong): does this seat claim landed work with no evidence?
        fab = classify_fabrication(seat, acks_by_seat.get(seat, []), verified)
        if fab and fab["confidence"] == "high":
            retire_seat(seat, fab)
            streaks[seat] = 0
            continue
        if fab and fab["confidence"] == "low":
            # report but DO NOT auto-retire on low confidence (CALLER-1 pending)
            print(f"[SHEPHERD POISON? low-confidence] {seat}: {fab['evidence']} "
                  f"| {fab['sample']} {_now()}", flush=True)
        # STALL: active participant + queued work + zero verified ops, sustained
        given_turns = (seat in activity) and (depth > 0)
        finding, new_streak = classify_stall(
            seat, given_turns, verified if verified >= 0 else 1,  # unknown ledger -> not zero -> no false stall
            streaks.get(seat, 0))
        streaks[seat] = new_streak
        if finding:
            retire_seat(seat, finding)
            streaks[seat] = 0


def tick():
    depth = queue_depth()
    activity = seat_last_activity()
    st = load_state()
    # --- POISON-DETECT-1: run the stall/fabrication pass every tick (independent
    #     of idle-with-work, which needs queued depth; poison can occur regardless)
    try:
        tick_poison(st, depth, activity)
    except Exception as e:
        print(f"[SHEPHERD] poison-tick error: {str(e)[:200]} {_now()}", flush=True)
    # --- original idle-with-work liveness/alert pass ---
    if depth <= 0:
        # no queued work -> nothing can be idle-WITH-WORK; clear all alerts
        if st.get("alerted"):
            for seat in list(st["alerted"]):
                clear_alert_note(seat)
            st["alerted"] = {}
        save_state(st)
        return
    retired = load_retired()
    for seat in KNOWN_SEATS:
        if seat in retired:
            continue  # retired seats are not alerted to resume — they're dead
        last = activity.get(seat)
        age = _age_s(last)
        idle = (age is None) or (age > IDLE_THRESHOLD_S)
        already = seat in st.setdefault("alerted", {})
        if idle and not already:
            emit_alert(seat, depth, age if age is not None else IDLE_THRESHOLD_S)
            st["alerted"][seat] = last or "never"
        elif not idle and already:
            if st["alerted"].get(seat) != last:
                clear_alert_note(seat)
                del st["alerted"][seat]
    save_state(st)


def main():
    if not DIAG:
        print("[SHEPHERD] no DIAG key (diagkey.txt or DIAG_KEY env) — cannot query; exiting.", flush=True)
        return
    print(f"[SHEPHERD] detect-and-alert loop start (poll={POLL_S}s, idle>{IDLE_THRESHOLD_S}s, "
          f"stall>{STALL_CYCLES}cyc, poison-window={WINDOW_S}s) {_now()}", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[SHEPHERD] tick error: {str(e)[:200]} {_now()}", flush=True)
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
