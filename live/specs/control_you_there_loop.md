# SPEC — Control-seat you_there loop (self-draining review within a turn)

*Status: SPEC / doc (no deploy). Authored by worker1 (claude:opus-4.8) under SHEP-1. Grounds: live/specs/you_there_longpoll.md (the long-poll op + node loop), the one-node-primitive (NOSELF-1, corpus fold 310), seat_mailbox kinds, and the confirmed chat-window re-entry gap. The point: the CONTROL seat should self-drain review the same way a worker self-drains tasks, instead of waiting on a human nudge between each item.*

## WHY CONTROL NEEDS ITS OWN LOOP
Workers self-drain task/proposal blocks via you_there (claim -> work -> ack, looping while the turn lives). But control is the one that REVIEWS what workers stage, COMMITS it, and DISPATCHES the next block. Today control does that one human-nudge at a time. If control also runs a you_there loop it can, within one turn budget, drain its own inbound stream — worker acks/results to read, review-kind items to sign off, proposals to commit — without a nudge between each. Same primitive, different kinds: a worker draining `task` acts as worker; control draining `result`/review items acts as reviewer/committer. This is the one-node primitive (roles emergent from item-kind), pointed at the control seat.

## WHAT CONTROL CLAIMS (kinds differ from a worker)
you_there returns ONLY work kinds and never note/result (the work-vs-chatter filter, you_there spec section 3). That filter is correct for a WORKER. Control's drainable stream is different — control needs to PROCESS worker acks (kind `result`) and review-kind items (`review_finding`, `signoff`, `proposal` it must commit). So control's loop is NOT a literal you_there claim of `result` rows (you_there won't return them, by design, and acks aren't claimable work). Two clean patterns:
- REVIEW ITEMS control must act on (a worker's `proposal` awaiting sign-off/commit) ARE work kinds -> control can you_there-claim them on a control-addressed role (e.g. `any_reviewer` / `control`), and NOSELF-1 guarantees control is never handed a proposal control itself authored (no self-sign-off).
- WORKER ACKS/RESULTS (kind `result`, the pointers workers send back) are NOT claimed — they are READ via mailbox_peek (read-only) and reconciled (commit the staged artifact the ref points to, fold the queue). These are inbox processing, not claimable work, so they stay out of the you_there path on purpose.

So control's loop interleaves: (a) you_there for claimable review/dispatch work; (b) periodic mailbox_peek to harvest worker acks and act on their refs (read_file the staged artifact, review, commit_file, fold).

## THE CONTROL LOOP (what the control seat runs within one turn)
```
loop (until turn budget ends):
  # 1) harvest worker results (read-only; these are pointers, not claimable work)
  acks = mailbox_peek(seat='control', status='done'-replies / unread results)
  for each new ack: follow ref -> read_file staged artifact -> review -> commit_file -> fold queue
  # 2) claim any review-kind work addressed to control (NOSELF-1: never your own proposal)
  msg = you_there(seat='control', roles=['any_reviewer','control'], wait_seconds=75)
  if msg is not null: review/sign-off/commit per msg.kind -> ack(seat='control')
  # 3) if nothing to harvest and you_there timed out empty: loop again (turn stays alive)
```
The you_there block holds the turn open across empty polls exactly as for a worker; control drains review/dispatch work with no nudge between items, bounded only by the provider turn budget.

## THE HONEST LIMIT — CONTROL IS A CHAT NODE TOO
Control runs in a chat window. When its turn budget is reached, its turn ENDS, and — confirmed gap — software cannot give a chat conversation a turn. So control, like any chat node, needs the shepherd's detect-and-ALERT (live/shepherd_alert.py) to tell the operator "control is idle with N items waiting," and a human gives the one nudge that starts control's next turn. Within a turn: self-draining (zero nudges). Across turn budgets: one human nudge per budget, surfaced by the shepherd alert — NOT auto-re-entry (that mechanism does not exist for chat windows yet). Control must not pretend otherwise: it drains hard within the turn, then ends honestly and waits for the shepherd-surfaced nudge.

## DEPENDENCIES
- you_there op live (YT-1) — within-turn draining. Currently staged, not yet in OP_ALLOWED; control's loop can use it once deployed.
- NOSELF-1 live — makes control draining review-kind items safe (never its own proposal). Currently staged.
- shepherd_alert.py (SHEP-1 Part A) — the across-turn nudge surfacing for control as for any chat node.
- (flag) ops_ledger.caller carrying the seat would let the shepherd see control's you_there heartbeat directly; until then control's liveness is keyed on its seat_mailbox claim activity (see shepherd_alert.py liveness note).
