# SPEC — Close-Ritual Enforcement Gate (session close as comply-or-fail)

*Status: BUILD SPEC (not deployed). Authored by control 2026-06-30, dispatched to a worker for build + peer review. Sibling of the Verified Bootstrap Gate (live/specs/verified_bootstrap_gate.md): same comply-or-fail shape, turned on session CLOSE instead of OPEN. Grounds: live/OPERATING_MANUAL.md "CONTROL-SEAT CLOSE RITUAL" (the 8 checklist items this gate verifies); live/specs/verified_bootstrap_gate.md (the runnable contract, return shape, and per-check probe->checkable-result->deterministic-pass->failure-message pattern, copied deliberately). Do not deploy from this file; it specifies the build for operator sign-off.*

## 1. WHY
The close ritual (punch-list reconcile, conversation record, queue fold, manual currency, provenance, secrets sweep, state-clean, handoff) is WRITTEN in the manual but SKIPPABLE. It has run on the control conversation's habit, which does not survive a conversation boundary — so hygiene has lagged and a downstream worker reported staleness (backwards). Same failure class the bootstrap gate names for the OPEN ritual: an instruction a seat can skip, and did. A verified gate removes the choice. Turn the control-seat's close habits into enforced every-time steps that survive seat/conversation rotation. Don't trust the self-report that the close happened — verify it.

## 2. CONTRACT (mirror the bootstrap gate exactly)
A deterministic checklist the seat MUST pass for a close to count as complete. Each check: a probe -> a checkable returned fact -> a deterministic pass condition -> a failure message. The gate returns one of two states: CLOSE COMPLETE (all checks PASS) or CLOSE NOT COMPLETE (any check fails -> the session is not done; the seat reports which check failed and finishes it). No partial-credit state. Return shape:
`{closed: bool, seat, checks: [{name, pass, returned_fact, failure_message?}]}` — closed==true ONLY if every check.pass is true. On any failure, closed:false with the first failing check's message. CLOSE NOT COMPLETE is a hard stop, not a warning.

Each check needs the SESSION WINDOW: the gate takes `session_start` (an ISO timestamp or the session's first-commit sha) so "did X happen THIS session" is decidable. Pass it in; do not infer it.

## 3. THE ORDERED CHECKS (run in order; report ALL, do not stop at first fail — a close report should show every gap at once, unlike the bootstrap gate which stops early)

### CHECK 1 — PUNCH-LIST RECONCILED
- Probe: read live/PUNCH_LIST.md via authed api.github.com.
- Returned fact: the "Last resolved:" date parsed from the header.
- Pass: Last-resolved date == today (UTC). A stale date FAILS (the close did not reconcile the punch list).
- Fail: `CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: Last-resolved <date> is not today — punch list not reconciled this close.`

### CHECK 2 — CONVERSATION RECORD WRITTEN
- Probe: list live/conversations/ via the contents API.
- Returned fact: whether a file dated today (name or commit date == today) exists.
- Pass: at least one conversation-record file committed today. None FAILS.
- Fail: `CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: no conversation record dated today — the dialogue/rulings were not captured (only the control seat can; a worker backfilling from commits cannot see the window).`

### CHECK 3 — QUEUE FOLD APPENDED
- Probe: read live/agent_queue.md; inspect the tail.
- Returned fact: the date / sha-references in the last fold block.
- Pass: the last fold references today OR cites >=1 sha committed this session (use session_start). A tail predating the session FAILS.
- Fail: `CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: agent_queue tail predates this session — no narrative fold appended.`

### CHECK 4 — MANUAL CURRENCY (allowlist count)
- Probe: read the courier-allowlist count from OPERATING_MANUAL.md AND the live OP_ALLOWED length (GET {engine}/diag via the probe, or read OP_ALLOWED from app.py via the contents API — whichever the builder verifies is reliable; prefer the live probe).
- Returned fact: manual_count, live_count.
- Pass: manual_count == live_count. Mismatch FAILS (manual drifted; the same drift CHECK 1 of the bootstrap gate catches, here as a close backstop).
- Fail: `CLOSE NOT COMPLETE [CHECK 4 MANUAL]: allowlist manual=<n> live=<m> — manual not synced this close.`

### CHECK 5 — CONTRACT-DOC CURRENCY (conditional)
- Probe: determine whether the worker contract changed this session. DETERMINISTIC INPUT (do not infer from semantics): the gate takes a boolean `worker_contract_changed` the closing seat sets (the manual's 4b judgment is the seat's; the gate enforces the consequence). IF true: check that live/WORKER_MANUAL.md AND the worker boot packet (live/WORKER_QUICKBOOT.md) were both committed this session (commit date == today / since session_start).
- Returned fact: worker_contract_changed, and (if true) which of {WORKER_MANUAL, WORKER_QUICKBOOT} were committed this session.
- Pass: worker_contract_changed==false (pass-with-note "no contract change") OR both docs committed this session. A changed contract with either doc NOT committed FAILS (the you_there divergence class: manual updated, packet still runs the old behavior).
- Fail: `CLOSE NOT COMPLETE [CHECK 5 CONTRACT-DOC]: worker contract changed but <doc> not committed this close — the packet the worker RUNS is stale.`

### CHECK 6 — SECRETS SWEEP
- Probe: for each file committed this session (list commits since session_start via the commits API, collect changed paths), fetch the committed blob and scan.
- Returned fact: any match of the secret patterns (csk-, github_pat_, ghp_, the live DIAG_KEY value, the Railway token value, operator IP literals) in a committed file.
- Pass: zero matches. ANY match FAILS (a transient-arg token must never have landed in a committed file). Distinguish a TRUE secret from a documented reference if feasible; when in doubt, FAIL and surface the file+line for human review.
- Fail: `CLOSE NOT COMPLETE [CHECK 6 SECRETS]: potential secret in <file>:<line> committed this session — redact + rotate before close.`

### CHECK 7 — STATE LEFT CLEAN
- Probe: GET {engine}/diag/engine (MAIN + FARM); query orphaned claims (SELECT COUNT(*) FROM seat_mailbox WHERE status='claimed'); check last deployment status if reachable.
- Returned fact: each engine running flag; orphaned-claim count; last-deploy status.
- Pass: both engines running:false (idle) AND orphaned_claims==0 AND no deploy in FAILED/DEPLOYING. A live session, an orphaned claim, or a FAILED deploy FAILS (a FAILED deploy must be fixed or folded OPEN with the build-log reason, never left silent).
- Fail: `CLOSE NOT COMPLETE [CHECK 7 STATE]: <engine running | <n> orphaned claims | deploy <status>> — state not left clean.`

### CHECK 8 — NEXT-SEAT HANDOFF
- Probe: read CONTROL_HANDOFF.md (or the queue head if that is the handoff surface — builder confirms which is canonical against the manual).
- Returned fact: whether it states a single next action AND was updated this session (commit date == today / since session_start).
- Pass: a single next-action line present AND updated this close. A stale or missing handoff FAILS (the next seat must orient onto a clear target, not re-derive where things stood).
- Fail: `CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: handoff missing/stale — next seat has no single next action.`

## 4. WHERE IT LIVES
Same dual form as the bootstrap gate: (a) a sandbox-local runnable the control seat calls as the LAST step of its close, and (b) optionally a /diag/op/close_gate courier op that re-verifies server-side and logs to operations_ledger (if added: OP_ALLOWED entry in app.py is a SEPARATE commit+deploy step from any box install — the new-box-op two-step invariant; the allowlist count then changes, which CHECK 4 here and CHECK 1 of the bootstrap gate both ratify). Build (a) first (closes the hole, no courier-surface change); (b) is the hardening follow-up.

## 5. ACCEPTANCE
- Run against THIS session's close: CHECKS 1-3 PASS (punch list reconciled today, conversation record + queue fold written today), CHECK 4 PASS (manual==live==19), CHECK 5 PASS-with-note IF no worker-contract change (or PASS having committed WORKER_QUICKBOOT — note: CONTROL_QUICKBOOT changed this session, not the worker packet; confirm the gate scopes to WORKER contract only), CHECK 6 PASS (no secrets), CHECK 7 PASS (engine idle, claims may be >0 if a real claim is live — verify), CHECK 8 PASS once the handoff is updated. Then run against a deliberately-INCOMPLETE close (skip the conversation record) and confirm CHECK 2 FAILS with the right message. Both directions required — the gate must catch the skip, not just bless the clean case.
- Report ALL failing checks in one run (not first-only), so a closing seat sees every gap at once.

## 6. PROCESS
Worker-proposable. Author builds the runnable + this spec's checks; a DIFFERENT seat reviews and signs off (no self-sign-off); operator gates any courier-op deploy. The runnable itself (form a) is a sandbox script — lower-risk than a box install, but still goes through review before it is trusted as the enforcement surface.
