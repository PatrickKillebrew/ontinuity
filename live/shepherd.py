#!/usr/bin/env python3
"""Farm shepherd — serial burn-in driver.
One objective at a time: start -> answer pre-session -> watch to completion ->
verify receipt -> pace -> next. Stops the batch on any modal (operator
constitutional point), repeated provider failure, or missing receipt.
Run: python3 shepherd.py <start_index> <count>
"""
import json, os, sys, time, urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)

FARM = "https://ontinuity-farm-production.up.railway.app"
MAIN = "https://web-production-7eaf8.up.railway.app"
DIAG = (open("/home/claude/diagkey.txt").read().strip()
        if os.path.exists("/home/claude/diagkey.txt")
        else os.environ.get("DIAG_KEY", ""))
MBKEY = open("/home/claude/farm_mbkey.txt").read().strip()
PACE_S = 25          # gap between sessions (rate weather)
SESSION_BUDGET_S = 420   # max wall-clock per session before flagging
LOG = "/home/claude/shepherd_log.jsonl"

def http(url, body=None, headers=None):
    request_headers = dict(headers or {})
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
        headers=request_headers)
    return json.loads(_NO_REDIRECT_OPENER.open(req, timeout=40).read().decode())

def log(rec):
    rec["t"] = time.strftime("%H:%M:%S")
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(rec)

def engine():
    return http(f"{FARM}/diag/engine", headers={"X-Diag-Key": DIAG})

def mailbox():
    return http(f"{FARM}/mailbox/turn", headers={"X-Mailbox-Key": MBKEY})

def respond(turn_id, text):
    return http(f"{FARM}/mailbox/respond", {"turn_id": turn_id, "response": text},
                headers={"X-Mailbox-Key": MBKEY})

def latest_receipt():
    d = http(f"{MAIN}/diag/api/query?sql=SELECT%20receipt_id%2C%20session_id%2C%20outcome%20FROM%20write_receipts%20ORDER%20BY%20receipt_id%20DESC%20LIMIT%201",
             headers={"X-Diag-Key": DIAG})
    return d["rows"][0]

def consecutive_provider_failures():
    d = http(f"{FARM}/diag/console", headers={"X-Diag-Key": DIAG})
    ev = d if isinstance(d, list) else []
    tail = [str(e) for e in ev[-10:]]
    return sum(1 for s in tail if "403" in s or "401" in s)

def run_one(obj):
    base_receipt = latest_receipt()[0]
    r = http(f"{FARM}/agent/start", {"objective": obj["objective"], "start_fresh": True},
             headers={"X-Mailbox-Key": MBKEY})
    if not r.get("ok"):
        log({"id": obj["id"], "event": "start_refused", "detail": r}); return "STOP"
    log({"id": obj["id"], "event": "started"})
    t0 = time.time()
    answered_presession = False
    seen_running = False
    while time.time() - t0 < SESSION_BUDGET_S:
        time.sleep(10)
        mb = mailbox()
        if mb.get("waiting"):
            kind, tid = mb.get("kind"), mb.get("turn_id")
            if kind == "pre_session_questions" and not answered_presession:
                respond(tid, obj["presession"]); answered_presession = True
                log({"id": obj["id"], "event": "presession_answered"})
            elif kind == "human_input_needed":
                log({"id": obj["id"], "event": "MODAL", "detail": "operator constitutional point — batch halted",
                     "context": str(mb.get("conversation"))[:300]})
                return "MODAL"
            elif kind == "researcher_turn":
                # All-API farm should never route a researcher turn to the mailbox;
                # if it does, config drifted. Halt honestly.
                log({"id": obj["id"], "event": "SEAT_TURN_UNEXPECTED"}); return "STOP"
        e = engine()
        if e.get("running") or e.get("finalizing"):
            seen_running = True
        if seen_running and not e.get("running") and not e.get("waiting_for_input") and not e.get("finalizing"):
            rec = latest_receipt()
            if rec[0] > base_receipt:
                log({"id": obj["id"], "event": "complete", "receipt": rec[0], "session": rec[1], "outcome": rec[2],
                     "duration_s": int(time.time() - t0)})
                return "OK"
            time.sleep(8)  # write may trail the engine flag
            rec = latest_receipt()
            if rec[0] > base_receipt:
                log({"id": obj["id"], "event": "complete", "receipt": rec[0], "session": rec[1], "outcome": rec[2],
                     "duration_s": int(time.time() - t0)})
                return "OK"
            log({"id": obj["id"], "event": "NO_RECEIPT", "detail": "engine idle but no receipt landed"}); return "STOP"
    log({"id": obj["id"], "event": "BUDGET_EXCEEDED"}); return "STOP"

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    battery = json.load(open("/home/claude/battery.json"))["objectives"]
    for obj in battery[start:start + count]:
        if consecutive_provider_failures() >= 4:
            log({"event": "PROVIDER_WEATHER_HALT"}); break
        status = run_one(obj)
        if status != "OK":
            log({"event": "BATCH_HALTED", "on": obj["id"], "status": status}); break
        time.sleep(PACE_S)
    log({"event": "batch_done"})

if __name__ == "__main__":
    main()
