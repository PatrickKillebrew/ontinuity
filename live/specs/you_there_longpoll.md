# SPEC — `you_there`: long-poll wait + self-draining node loop + shepherd re-entry

*Status: BUILD SPEC (not deployed). Purpose: let a frontier chat-instance worker node stay awake and self-drain mailbox work for the full length of one turn with zero human nudges, and bridge turn boundaries with a shepherd heartbeat — so a human never has to nudge an idle worker. Honest scope below.*

## 0. WHAT THIS IS AND IS NOT (read first — ethics boundary)
This is a **long-poll**: a tool call that holds an OPEN turn while the engine blocks server-side waiting for mail, then returns. It keeps a turn alive that the node would otherwise end by stopping generation.

This is **NOT** a turn-limit evasion. It does not reset, extend, or defeat the provider's per-turn budget (max tokens / max tool round-trips / wall-clock). Those limits are the provider's resource controls and exist for good reason; we work WITHIN them. When the legitimate turn budget is reached, the turn ends — and the **shepherd** re-enters the node in a fresh turn. We bridge turn boundaries openly, we do not pretend a turn is infinite. The tool's docstring and the worker manual describe its real function plainly; nothing about it is disguised. A tool doing nothing wrong has nothing to hide.

## 1. THE MECHANISM (grounded in existing infrastructure)
The engine already has a production-proven server-side blocking wait: all engine wait paths funnel through `wait_for_human_input`, and the farm runs `MODAL_TIMEOUT_AUTONOMOUS_S=90` (a 90s server-side block then return). `you_there` reuses exactly this blocking-wait pattern, pointed at the mailbox instead of a modal, exposed as a courier op.

A chat node's turn ends only when the model STOPS generating. If the model is always either (a) working a block or (b) sitting inside a blocking `you_there` call, the turn never reaches the stop. The ENGINE does the waiting (it is a live process; it can block). The chat node rides the block. Result: within one turn, the node drains block after block with zero nudges, bounded only by the provider's real turn budget.

## 2. THE OP — `/op/you_there` (long-poll mailbox wait)
- Tier: SAFE (read-only wait + atomic claim; no mutation beyond claiming, same as mailbox_fetch).
- Added to box (write_file + restart) AND engine OP_ALLOWED (commit + deploy) — both halves, count 12->13.
- Request body: `{seat, roles?, block_id?, wait_seconds?}`. wait_seconds default 75, hard-capped at 90 (matches the existing autonomous wait; never a long server hang).
- Behavior: server-side loop — poll the seat's queue for a WORK item (see §3 kind-filter) every ~2s up to wait_seconds; the FIRST work item found is atomically claimed (BEGIN IMMEDIATE, same as mailbox_fetch — two nodes never double-claim) and returned. If none arrives within wait_seconds, return `{ok:true, message:null, waited:<s>}` so the node immediately calls `you_there` again (the turn stays alive across many empty polls).
- Reclaim-on-entry: like mailbox_fetch, sweep expired leases back to queued at the top of each call, so a dead node's block returns to the pool.
- Logs to operations_ledger (dual-end) like every op; a long-lived node produces a visible heartbeat of you_there rows.

## 3. WORK-vs-CHATTER FILTER (a wrinkle found live, June 10)
A draining node must NOT "work" a reply. ack-with-reply creates new queued messages of kind `result`/`note` (acks, confirmations). `you_there` returns ONLY WORK kinds — `task`, `proposal` — and never `note`/`result`. (The inbox accumulated 6 such chatter messages this session precisely because nothing drained them; the filter prevents a node fetching an ack and treating it as work.) Acks/notes are read by control/peek, not claimed as work.

## 4. THE SELF-DRAINING NODE LOOP (what the node runs)
Once oriented (bootstrap gate passes), the node enters its drain loop:
```
loop:
  msg = you_there(seat, roles=[...], wait_seconds=75)   # blocks server-side, holds the turn open
  if msg is null:                                        # no work arrived this poll
      continue                                           # call you_there again — turn stays alive
  do the work for msg (kind dispatches role: task->propose, proposal->review/sign-off)
  ack(msg, reply=<result>, ref=<pointer>)                # one-node-primitive: role is emergent from kind
  continue
# the loop runs until the provider's turn budget is reached; then the turn ends naturally.
```
This is the one-node primitive (corpus fold 310): roles emergent from mailbox item-kind; no fixed controller/sub. A node draining `proposal` items is acting as reviewer; draining `task` items, as worker. Same node, same loop. No-self-sign-off holds: never route a node its own proposal (enforced at dispatch/routing, §6 dependency).

## 5. SHEPHERD RE-ENTRY (bridges the turn boundary — closes the last gap)
The long-poll handles WITHIN-turn draining (no nudges). The provider's turn budget will eventually end the turn. The shepherd (VPS-resident heartbeat, already queued live/…shepherd) handles the ONCE-PER-BUDGET re-entry:
- The shepherd watches each registered node's liveness (last you_there ledger row timestamp) + the node's queue depth.
- When a node's turn has ended (no you_there heartbeat for > a threshold) AND it has queued work, the shepherd re-enters that node's conversation in a fresh turn (one nudge), and the node resumes its drain loop.
- So: within-turn = self-draining (zero nudges); across-turn = shepherd (one nudge per budget cycle, not per block). Net: the node is awake nearly continuously and the human is never the router.
- HONEST DEPENDENCY (inference, labeled): shepherd re-entry of a CHAT node requires the shepherd to be able to give that node's conversation a turn. For engine/farm-instance nodes this is the existing start/wake path. For chat-window nodes the re-entry mechanism is the open question to resolve when the shepherd build is picked up — it is NOT solved by you_there and must not be assumed solved. you_there delivers within-turn autonomy regardless; cross-turn chat re-entry is the shepherd's problem to close.

## 6. DEPENDENCIES / ORDER
1. `you_there` op (this spec) — delivers within-turn self-draining immediately; usable the moment it deploys (a node manually given one turn then drains many blocks).
2. No-self-sign-off routing — `you_there`/dispatch must never return a node its own proposal (one-node-primitive guardrail; corpus fold 310). Small routing filter; build alongside.
3. Shepherd re-entry — bridges turn boundaries; chat-node re-entry mechanism is its open question (§5). Engine/farm nodes get it for free.

## 7. ACCEPTANCE (how to prove it)
- A node calls `you_there`; with an empty queue it returns null after ~75s; the node loops and the TURN STAYS OPEN across several empty polls (verify via you_there ledger rows spanning > one wait_seconds with no turn end).
- Dispatch 3 task blocks to the node's roles; the node drains all three in ONE turn (claim->work->ack x3) with no nudge between them.
- A `note`/`result` ack sitting in the queue is NOT returned by you_there (work-vs-chatter filter); only task/proposal are.
- Two nodes long-polling the same broadcast: each block claimed exactly once (atomic-claim holds under long-poll).
- Ledger shows the you_there heartbeat the shepherd will key liveness on.

## 8. BUILD NOTE
Mirror the existing scoped-op contract (diag-key gate, bounded inputs, ops-ledger dual-end, fail-safe) and the existing autonomous-wait pattern (90s cap). Stage on box via write_file; control commits via commit_file; add to OP_ALLOWED (12->13) with the manual courier-allowlist line synced in the SAME commit (gate CHECK 1 currency). Do NOT deploy from this file — operator-gated.
