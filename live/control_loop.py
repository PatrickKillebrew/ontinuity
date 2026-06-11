#!/usr/bin/env python3
"""
Control-seat self-draining triage loop.
============================================================================
Lets the CONTROL seat process worker acks WITHIN one turn instead of waiting on
a per-ack human nudge — the operator is not the router. Spec: SHEP-1 doc
live/specs/control_you_there_loop.md.

WHAT IT AUTOMATES (the routing): within one turn, the control seat calls this to
DRAIN AND TRIAGE — collect every pending worker ack (kind=result/note addressed
to control), follow each ref to see what's staged, and produce a single ranked
review queue. No per-ack nudge; no human routing.

WHAT IT DOES NOT AUTOMATE (the judgment): it does NOT commit. Committing a staged
artifact needs the GitHub token the control seat holds IN-CONTEXT, and a worker
must never hold that token. So this loop COLLECTS + SUMMARIZES; the review and the
commit_file decision stay with the control seat, made by the seat each turn. The
loop removes the routing, not the judgment.

THE KIND PROBLEM (flagged in the block, solved here without breaking the worker filter):
you_there returns ONLY work kinds {task, proposal} — correct, because a draining
WORKER must never claim an ack. But CONTROL needs visibility of result/note acks.
The clean answer is NOT to change you_there's filter (that would let workers claim
acks as work). It is to use TWO channels:
  - you_there(seat=control, roles=[control, any_reviewer]) -> claimable REVIEW work
    (a worker's proposal awaiting sign-off IS a work kind; control claims + reviews it).
  - mailbox_peek(seat=control) -> READ-ONLY view of result/note acks. Acks are
    POINTERS, not claimable work, so they are peeked + triaged, never claimed. peek
    already returns all kinds, so control gets full ack visibility with zero change
    to the worker-facing filter.

ACROSS-TURN LIMIT (honest): control is a chat node too. When its turn budget ends,
the turn ends; software can't give a chat window a turn. So across turn budgets
control needs the SHEP-1 shepherd-alert + one human nudge per budget, exactly like
any worker node. Within a turn: self-draining. Across turns: shepherd-surfaced nudge.

RUN: this is a control-seat helper. The control seat calls triage() each turn to
get its review queue, acts on it (read_file the staged artifact, review, commit_file,
fold), then loops. It is NOT a detached daemon — it runs inside the control seat's
live turn so the seat can exercise judgment on what it surfaces.
"""
import json, os, urllib.request, urllib.parse
from datetime import datetime, timezone

ENGINE = "https://web-production-7eaf8.up.railway.app"
DIAG = (open("/home/claude/diagkey.txt").read().strip()
        if os.path.exists("/home/claude/diagkey.txt")
        else os.environ.get("DIAG_KEY", ""))

SEEN_FILE = "/home/claude/control_loop_seen.json"   # msg_ids already surfaced this arc


def _op(name, body):
    url = f"{ENGINE}/diag/op/{name}?diag_key={DIAG}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:   # 90 = you_there cap
        return json.loads(r.read().decode())


def _load_seen():
    try:
        return set(json.load(open(SEEN_FILE)))
    except Exception:
        return set()


def _save_seen(seen):
    tmp = SEEN_FILE + ".tmp"
    json.dump(sorted(seen), open(tmp, "w"))
    os.replace(tmp, SEEN_FILE)


def collect_pending_acks():
    """READ-ONLY: peek control's inbox for result/note acks not yet surfaced.
    Returns a list of {msg_id, block_id, from_seat, ref, summary} ranked oldest-first
    (oldest pending review first). Does NOT claim — acks are pointers, not work."""
    peek = _op("mailbox_peek", {"seat": "control", "limit": 50})
    seen = _load_seen()
    pending = []
    for m in peek.get("messages", []):
        if m.get("kind") not in ("result", "note"):
            continue
        if m.get("status") == "done":
            continue
        mid = m.get("msg_id")
        if mid in seen:
            continue
        pending.append({
            "msg_id": mid,
            "block_id": m.get("block_id"),
            "from_seat": m.get("from_seat"),
            "from_lineage": m.get("from_lineage"),
            "ref": m.get("ref"),                 # the pointer: what's staged + where
            "summary": (m.get("body") or "")[:400],
            "created_at": m.get("created_at"),
        })
    pending.sort(key=lambda x: x.get("created_at") or "")
    return pending


def claim_review_work(wait_seconds=75):
    """you_there for a claimable REVIEW item (proposal awaiting sign-off) addressed
    to control. Returns the claimed message or None. NOSELF-1 guarantees control is
    never handed its own proposal."""
    return _op("you_there", {"seat": "control",
                             "roles": ["control", "any_reviewer"],
                             "wait_seconds": min(wait_seconds, 90)}).get("message")


def triage(mark_surfaced=True):
    """One triage pass for the control seat. Returns the review queue the seat then
    acts on with its own judgment + token. Marks surfaced acks as seen so they are
    not re-surfaced (the seat clears them by acting; re-running won't spam)."""
    acks = collect_pending_acks()
    review = claim_review_work(wait_seconds=5)   # short poll; don't block triage long
    if mark_surfaced and acks:
        seen = _load_seen()
        seen.update(a["msg_id"] for a in acks)
        _save_seen(seen)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending_acks": acks,                    # result/note pointers to review+commit
        "pending_ack_count": len(acks),
        "claimed_review_item": review,           # a proposal control must sign off, or None
        "next_for_control_seat": (
            "For each pending_ack: follow ref -> read_file the staged artifact -> "
            "review -> commit_file (with your token) -> fold the queue. The COMMIT is "
            "yours; this loop only routed + summarized. If claimed_review_item is set, "
            "review/sign-off that proposal too."),
        "boundary": "drain-and-triage automated; commit + judgment stay with the control seat.",
    }
    return out


def reset_seen():
    """Clear the surfaced-set (e.g. at the start of a fresh session arc)."""
    try:
        os.remove(SEEN_FILE)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    if not DIAG:
        print(json.dumps({"error": "no DIAG key (diagkey.txt or DIAG_KEY env)"}))
    else:
        print(json.dumps(triage(mark_surfaced=False), indent=2))
