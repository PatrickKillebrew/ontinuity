#!/usr/bin/env python3
"""
Control-seat local triage helper.
============================================================================
Transforms response files already captured by the canonical Ontinuity HTTPS
receipt flow. It performs no network access and holds no capability material.
The model-facing transition remains visibly and exclusively:

    curl --config - < REQUEST.curl

WHAT IT AUTOMATES (the routing): within one turn, the control seat gives this the
two verified response files. It filters pending worker acks, preserves their refs,
and produces a single ranked review queue without another network transition.

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
the turn ends; software cannot give a chat window a turn. The shepherd can surface
work, but the next model turn must prepare and execute a new canonical receipt.

RUN: prepare, check, send, and verify separate mailbox_peek and you_there receipts,
then pass their captured response JSON paths to this helper. It is not a detached
daemon and cannot create an alternate transport path.
"""
import argparse
import json
import os
from datetime import datetime, timezone

SEEN_FILE = os.environ.get(
    "ONTINUITY_CONTROL_SEEN_FILE",
    os.path.join(os.environ.get("XDG_STATE_HOME", "/tmp"),
                 "ontinuity_control_loop_seen.json"),
)


def _read_response(path):
    with open(path, encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict):
        raise ValueError("captured response must be a JSON object")
    return result


def _load_seen():
    try:
        return set(json.load(open(SEEN_FILE)))
    except Exception:
        return set()


def _save_seen(seen):
    tmp = SEEN_FILE + ".tmp"
    json.dump(sorted(seen), open(tmp, "w"))
    os.replace(tmp, SEEN_FILE)


def collect_pending_acks(peek):
    """READ-ONLY: peek control's inbox for result/note acks not yet surfaced.
    Returns a list of {msg_id, block_id, from_seat, ref, summary} ranked oldest-first
    (oldest pending review first). Does NOT claim — acks are pointers, not work."""
    if not isinstance(peek, dict) or peek.get("ok") is not True:
        raise ValueError("mailbox_peek response is not a successful object")
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


def triage(peek, review_response, mark_surfaced=True):
    """One triage pass for the control seat. Returns the review queue the seat then
    acts on with its own judgment + token. Marks surfaced acks as seen so they are
    not re-surfaced (the seat clears them by acting; re-running won't spam)."""
    acks = collect_pending_acks(peek)
    if not isinstance(review_response, dict):
        raise ValueError("you_there response must be a JSON object")
    review = review_response.get("message")
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
        "boundary": "local triage automated; transport, commit, and judgment remain explicit.",
    }
    return out


def reset_seen():
    """Clear the surfaced-set (e.g. at the start of a fresh session arc)."""
    try:
        os.remove(SEEN_FILE)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Triage canonical Ontinuity response files locally")
    parser.add_argument("--peek-response")
    parser.add_argument("--review-response")
    args = parser.parse_args()
    if not args.peek_response or not args.review_response:
        print(json.dumps({
            "error": "compiled mailbox_peek and you_there response files are required",
            "transport": "curl --config - < REQUEST.curl",
        }))
    else:
        print(json.dumps(triage(
            _read_response(args.peek_response),
            _read_response(args.review_response),
            mark_surfaced=False,
        ), indent=2))
