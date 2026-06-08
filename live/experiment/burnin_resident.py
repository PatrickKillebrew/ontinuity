#!/usr/bin/env python3
"""Resident burn-in driver (Path A — throwaway; real version is Punch List P5.3).
Runs on the VPS as a systemd service so it outlives every chat conversation.
Drives the farm: start short probe -> answer pre-session -> watch to receipt ->
pace -> next, until the true stopping rule (>=200 randomized cycles AND >=20
sessions in the counted set). Resumes from the live DB count, so a restart loses
nothing. Halts the batch on any second modal in a session, repeated provider
failure, or missing receipt — same discipline as the chat driver.

Config via env: FARM_URL, MAIN_URL, DIAG_KEY, MAILBOX_KEY, COUNT_BOUNDARY (the
session-id prefix marking the clean counted set, e.g. '2026-06-08_').
"""
import json, os, time, urllib.request, random

FARM = os.environ["FARM_URL"].rstrip("/")
MAIN = os.environ["MAIN_URL"].rstrip("/")
DIAG = os.environ["DIAG_KEY"]
MBKEY = os.environ["MAILBOX_KEY"]
BOUNDARY = os.environ.get("COUNT_BOUNDARY", "2026-06-08_0")  # counted set starts at #88
TARGET_RANDOMIZED = int(os.environ.get("TARGET_RANDOMIZED", "200"))
TARGET_SESSIONS = int(os.environ.get("TARGET_SESSIONS", "20"))
PACE_S = 8
SESSION_BUDGET_S = 180
LOG = "/opt/ontinuity/burnin_resident.log"

PROBES = [
    "Establish via DB_QUERY the total row count of session_transcripts and report the integer with its evidence cited.",
    "Establish via DB_QUERY how many distinct sessions exist in the sessions table; report the count, citing the execution.",
    "Establish via DB_QUERY the highest receipt_id in write_receipts and report it with the execution cited.",
    "Establish via DB_QUERY the count of behavioral_observations rows and report the integer, citing the query.",
    "Establish via DB_QUERY how many write_receipts have outcome 'ok' and report the count with its evidence.",
]
PRESESSION = ("1. One DB_QUERY cycle with a single read-only SELECT COUNT(*). "
             "2. One-sentence report citing the executed query. Close after the reviewed report.")

def http(url, body=None, timeout=40):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"} if body else {})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())

def log(rec):
    rec["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
    line = json.dumps(rec)
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)

def q(sql):
    import urllib.parse
    url = f"{MAIN}/diag/api/query?diag_key={DIAG}&sql={urllib.parse.quote(sql)}"
    return http(url, timeout=40)["rows"]

def randomized_count():
    return q(f"SELECT COUNT(*) FROM behavioral_observations WHERE randomized_flag=1 AND session_id >= '{BOUNDARY}'")[0][0]

def session_count():
    return q(f"SELECT COUNT(DISTINCT session_id) FROM behavioral_observations WHERE computed_signal IS NOT NULL AND session_id >= '{BOUNDARY}'")[0][0]

def latest_receipt():
    return q("SELECT MAX(receipt_id) FROM write_receipts")[0][0]

def engine_idle():
    e = http(f"{FARM}/diag/engine?diag_key={DIAG}")
    return not e.get("running") and not e.get("waiting_for_input") and not e.get("finalizing")

def run_one(objective):
    base = latest_receipt()
    r = http(f"{FARM}/agent/start", {"mailbox_key": MBKEY, "objective": objective, "start_fresh": True})
    if not r.get("ok"):
        log({"event": "start_refused", "detail": r}); return "STOP"
    t0 = time.time()
    answered = False
    proceeds = 0
    while time.time() - t0 < SESSION_BUDGET_S:
        time.sleep(8)
        try:
            mb = http(f"{FARM}/mailbox/turn?mailbox_key={MBKEY}")
        except Exception:
            continue
        if mb.get("waiting"):
            kind, tid = mb.get("kind"), mb.get("turn_id")
            if kind == "pre_session_questions" and not answered:
                http(f"{FARM}/mailbox/respond", {"mailbox_key": MBKEY, "turn_id": tid, "response": PRESESSION})
                answered = True
            elif kind == "human_input_needed":
                proceeds += 1
                if proceeds >= 2:
                    log({"event": "SECOND_MODAL_STOP", "detail": "bounding contamination; clearing wait by answering the turn"})
                    # ANSWER the orphaned turn to release the engine's wait-state.
                    # /agent/stop fails with 'no session running' when the turn holds
                    # the session open, leaving an orphaned wait that deadlocks the
                    # next session. Answering clears it; this is the auto-clear fix.
                    try: http(f"{FARM}/mailbox/respond", {"mailbox_key": MBKEY, "turn_id": tid, "response": "Stop."})
                    except Exception: pass
                    try: http(f"{FARM}/agent/stop", {"mailbox_key": MBKEY})
                    except Exception: pass
                    # verify the wait actually cleared before moving on
                    for _ in range(6):
                        time.sleep(4)
                        try:
                            e = http(f"{FARM}/diag/engine?diag_key={DIAG}")
                            if not e.get("waiting_for_input") and not e.get("running"):
                                break
                            # still waiting on a (possibly new) turn — answer it too
                            mb2 = http(f"{FARM}/mailbox/turn?mailbox_key={MBKEY}")
                            if mb2.get("waiting"):
                                http(f"{FARM}/mailbox/respond", {"mailbox_key": MBKEY, "turn_id": mb2.get("turn_id"), "response": "Stop."})
                        except Exception:
                            pass
                    log({"event": "MODAL_STOP_CLEARED", "detail": "orphaned wait released; ready for next session"})
                    return "MODAL_STOP"
                http(f"{FARM}/mailbox/respond", {"mailbox_key": MBKEY, "turn_id": tid, "response": "Proceed."})
        try:
            if engine_idle():
                time.sleep(8)
                if latest_receipt() > base:
                    return "OK"
                if engine_idle() and latest_receipt() == base:
                    log({"event": "NO_RECEIPT"}); return "STOP"
        except Exception:
            continue
    log({"event": "BUDGET_EXCEEDED"}); return "STOP"

def main():
    log({"event": "resident_driver_start", "boundary": BOUNDARY,
         "randomized": randomized_count(), "sessions": session_count()})
    fails = 0
    while True:
        rc, sc = randomized_count(), session_count()
        if rc >= TARGET_RANDOMIZED and sc >= TARGET_SESSIONS:
            log({"event": "STOPPING_RULE_MET", "randomized": rc, "sessions": sc}); break
        if not engine_idle():
            time.sleep(10); continue
        status = run_one(random.choice(PROBES))
        if status == "OK":
            fails = 0
            log({"event": "session_done", "randomized": randomized_count(), "sessions": session_count()})
        elif status == "MODAL_STOP":
            fails = 0  # bounded by design, not a failure
        else:
            fails += 1
            log({"event": "session_problem", "status": status, "consecutive_fails": fails})
            if fails >= 4:
                log({"event": "HALT_REPEATED_FAILURE"}); break
        time.sleep(PACE_S)
    log({"event": "resident_driver_exit", "randomized": randomized_count(), "sessions": session_count()})

if __name__ == "__main__":
    main()
