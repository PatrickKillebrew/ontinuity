# PUNCH LIST RECONCILIATION — audit against what actually shipped

*Status: PROPOSE-ONLY (control owns the PUNCH_LIST.md merge). Authored by worker1 (claude:opus-4.8) under PUNCHAUDIT-1. Every move below is tied to a commit/receipt I verified, or labeled INFERENCE. Verification path: read PUNCH_LIST.md + the committed box source at live/box/ via raw CDN / read_repo; confirmed op/function presence byte-level. This is a proposed diff, not an edit.*

## VERIFIED GROUND TRUTH (the basis for the moves)
- live/box/box_ops.py is COMMITTED at 17055 bytes and CONTAINS op_read_repo AND op_commit_file (verified by substring). read_repo is also DEPLOYED — I read the live app.py through /op/read_repo this session.
- live/box/seat_mailbox.py is COMMITTED at 25285 bytes and CONTAINS /op/you_there, _noself_predicate, AND the HARDEN-1 ack guard ("did not claim"). So you_there + no-self-sign-off + claimed_by-scoping are all in version control.

## MOVE TO DONE (currently mislabeled IN-PROGRESS or OPEN — really shipped)

1. **read_repo courier op** — currently IN-PROGRESS (line 42). REALLY DONE. Committed in live/box/box_ops.py (op_read_repo present, file 17055 b) and deployed (read used live to read app.py this session). 
   PROPOSE: move to DONE — "read_repo box op + courier — engine/box fetch any repo file (incl app.py) via auth-API|raw-cachebust|unauth-API; closes the 'couldn't reach engine source' gap worker2 hit on SECAUDIT-1. Committed live/box/box_ops.py, OP_ALLOWED entry deployed."

2. **No-self-sign-off routing filter** — currently IN-PROGRESS (line 46). REALLY DONE. _noself_predicate committed in live/box/seat_mailbox.py; applies to both mailbox_fetch and you_there; authorship-stamped (author_seat/author_lineage additive columns). This DUPLICATES the DONE entry at line 8 ("you_there long-poll + no-self-sign-off filter ... 622c7046"). 
   PROPOSE: DELETE the IN-PROGRESS line 46 as a duplicate of the line-8 DONE entry.

3. **you_there long-poll** — currently IN-PROGRESS (line 45, "DISPATCHED YT-1"). REALLY DONE and already in DONE at line 8 (622c7046 / OP_ALLOWED beeb053a / manual b46c2d69). The IN-PROGRESS entry is now stale. 
   PROPOSE: DELETE line 45 as a duplicate of the line-8 DONE entry. (The line-8 entry already captures the work-vs-chatter filter + the ethics boundary.)

4. **claimed_by-scope ack + scope reclaim (HARDEN-1)** — currently embedded as a future "cheap interim available now" inside the per-identity-keys item (line 44). REALLY DONE. The ack guard + scoped reclaim are committed in live/box/seat_mailbox.py. 
   PROPOSE: add a DONE entry — "Mailbox hardening (HARDEN-1, SECAUDIT-1 rec): mailbox_ack rejects acking a block you didn't claim (claimed_by-scoped); mailbox_reclaim scoped to own expired claims or explicit all=true. Honest-seat-names until per-identity keys. Committed live/box/seat_mailbox.py (25285 b)." — and strike the "cheap interim available now" clause from line 44 (it's no longer pending).

## MOVE / SPLIT (partly shipped — the label overstates what's open)

5. **Shepherd re-entry (turn-boundary bridge)** — currently IN-PROGRESS (line 47) framed as one item. The DETECT-AND-ALERT half shipped: live/shepherd_alert.py is committed (per-seat liveness via seat_mailbox.claimed_by + queue depth, one alert per idle-with-work transition). The CHAT re-entry remains genuinely open (confirmed gap: software can't give a chat window a turn). 
   PROPOSE: SPLIT — move "shepherd detect-and-alert driver (live/shepherd_alert.py, committed)" to DONE; keep ONLY "chat-window re-entry mechanism" as the open remainder. The current single entry makes a done thing look pending.

## MOVE TO IN-PROGRESS / PROPOSED (currently OPEN — now has a committed proposal this session)

6. **Mailbox turn payloads carry the engine cycle number** — currently OPEN/MED (line 81). Two findings (CYCLENUM-1): the turn ENVELOPE already carries cycle (external_mailbox cycle field, set ~1720, returned by /mailbox/turn ~3240) — that half is ALREADY DONE in the engine. The real gap (injected results carry no cycle coordinate) has a proposed 2-line app.py fix (live/specs/cyclenum_fix.md). 
   PROPOSE: move to IN-PROGRESS as "CYCLENUM-1 — envelope cycle already present; per-injection cycle stamp proposed (2-line ambient_line edit, watched path), live/specs/cyclenum_fix.md; awaiting operator apply+deploy." Note the envelope half is already done so the item is smaller than it reads.

7. **Query-guard literal handling** — currently MINOR/OPEN (line 90). Has a proposed fix (QGUARD-1): literal-aware semicolon scanner + optional same-class keyword-in-literal fix, live/specs/query_guard_fix.md. 
   PROPOSE: move to IN-PROGRESS "QGUARD-1 — literal-aware db_query_guard proposed (semicolon + optional keyword), tested, watched path; awaiting operator apply+deploy."

8. **/agent/handoff endpoint** — currently OPEN/MED (line 84). Has a committed spec (HANDOFF-1): GET /agent/handoff, diag-key gated, composes both engines + queue head + open turns + receipts; live/specs/agent_handoff.md. 
   PROPOSE: move to IN-PROGRESS "HANDOFF-1 — spec'd (one keyed call, composes existing diag+corpus sources); seat-layer sibling of the bootstrap gate; awaiting operator build+deploy." (Note line 84 calls it the sibling of Knowtext; the spec frames it as the sibling of the bootstrap gate — INFERENCE: gate sibling is the more precise framing since it delivers the state the gate verifies.)

9. **Farm role model-string audit** — currently MINOR/OPEN (line 93, "one 404 mid-session"). Root-caused this session (FARMFIX-1): the farm Friction model_c string is the prefixed meta-llama/llama-3.1-8b-instruct (298 sessions, all recent _farm model_dead deaths carry it) vs the correct bare Cerebras llama3.1-8b; fix is a FARM Railway env change (operator). 
   PROPOSE: move to IN-PROGRESS "FARMFIX-1 — root-caused: FARM model_c env should be llama3.1-8b not meta-llama/llama-3.1-8b-instruct; operator env+deploy." with the corpus evidence.

## NO CHANGE (verified still genuinely open — checked, not assumed)
- Bootstrap gate step 2 (courier op) — line 69, still OPEN; step 1 runnable is correctly in DONE (gate.py committed). The courier-op wrapper + per-identity issuance remain unbuilt. CORRECT as-is.
- ERL enablement — not yet a punch-list line as its own item; the erl_decision.md memo (committed) is the decision input. PROPOSE: add an IN-PROGRESS line "ERL enablement — decision memo staged (Option A wire-persistence vs B fold-carried; phased recommendation), live/specs/erl_decision.md; awaiting control's A/B call." so the decision doesn't get lost.
- Per-identity keys (line 44 core), vault bootstrap (line 53), multi-tenancy (line 72), Fix #2/#3/#4 (lines 55-57), provenance ledger (line 59), migration runner (line 61) — all verified still genuinely awaiting build/deploy. NO change.

## CROSS-CUTTING FINDING (flag, not a single-item move)
ops_ledger.caller is hardcoded 'diag-key' for every row — it cannot attribute any op to a seat. This is the SAME root behind: HARDEN-1 being only partial (body identity self-asserted), the bootstrap gate's per-identity-key dependency, and the shepherd having to key liveness on seat_mailbox.claimed_by instead of the you_there heartbeat. A one-line box fix (stamp the seat into caller in _ledger_begin) would upgrade all three. PROPOSE: add a MINOR/quick-win line "Stamp seat into operations_ledger.caller (one-line _ledger_begin fix) — unblocks per-seat attribution for shepherd liveness + makes HARDEN-1 checks attributable."

## PERSISTENCE-RULE TRAIL
read_repo returned transient 502s on a couple of paths (box files live under live/box/, not repo root); fell back to raw CDN at the correct live/box/ paths to confirm committed content byte-level. Did not treat the 502 as "not committed" — chased the right path first.
