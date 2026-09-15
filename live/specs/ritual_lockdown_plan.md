# SPEC — RITUAL LOCKDOWN: make every ritual step a ledger fact (plan + gap audit of the June close-gate spec)

*Status: PLAN, agreed by the operator 2026-09-15. Grounds: live/OPERATING_MANUAL.md (rituals), live/specs/close_ritual_gate.md (June spec, never built), live/bootstrap/gate.py (the built boot gate), box_ops.py (ledger + wrapped-op pattern), records 2026-09-14a (railway_set_var) and 2026-09-15 (install two; the fresh seat's boot/close). Test bed: install two (ontinuity-two) — every op lands there first, then promotes to the operator install through the two-party chain.*

## THE PRINCIPLE (operator, 2026-09-15)
"Lock down any and every step that allows a model to trivially satisfy." A step is locked when it writes a ledger row a stranger can walk to. If a step cannot leave a row, it is not locked down, it is a habit. Same primitive as wrapped ops (railway_set_var): the seat cannot reach the raw action; the only path is the op; the op logs.

## LIFECYCLE INVENTORY (mechanical / self-reported / un-mechanizable)
| Step | Today | Lock |
|---|---|---|
| Boot: probe | mechanical (403 body cannot be recited) | keep |
| Boot: five reads | reads mechanical (read_repo ledger); "report a real line" self-reported | packet v3 ends with `bootstrap_gate`; booted == `oriented:true` from the gate |
| Open ritual (per task) | self-reported, no primitive | NEW op `orient {topic}` -> hits or "none" + ledger row; close gate checks the row |
| Op contracts | manual text, drifts (commit_file body never documented) | NEW op `describe` -> every route's schema (required/optional/tier); the op IS the manual for op bodies |
| Write path | mechanical (write_file -> commit_file, both logged) | keep |
| Deploy | mechanical (two-party signoff chain) | keep |
| Close ritual (8 items + 4b) | self-reported; spec exists, never built | BUILD `close_gate` op per the June spec with the corrections below |
| Assertion rule ("show the read") | un-mechanizable at this layer | stays discipline until V2-E; close gate narrows it (record must cite ≥1 commit sha) |

## GAP AUDIT OF live/specs/close_ritual_gate.md (June) — what is missing or wrong
1. CHECK 5 takes a seat-supplied boolean `worker_contract_changed` — a self-report inside the enforcement gate. DERIVE it: list commits since session_start; if any touched app.py's OP_ALLOWED, box_ops.py, seat_mailbox.py, file_server.py, or any *QUICKBOOT*/*BOOT_PACKET* file, the contract changed. No opinion input.
2. No check for the OPEN ritual. ADD CHECK 9: an `orient` ledger row exists for this session, timestamped after session_start (and, when the gate is called with a task id, after the task). Absent -> CLOSE NOT COMPLETE [CHECK 9 ORIENT].
3. No check that the conversation record is evidence-bearing. ADD to CHECK 2: the record must contain ≥1 commit sha that exists in this repo since session_start (the join the manual requires). A record with no join FAILS.
4. Install-specific constants are hardcoded (MAIN/FARM diag URLs, "manual==live==19"). PARAMETERIZE: engine URL, corpus repo, allowlist source come from env/config (CORPUS_REPO already exists); the allowlist count is read live, never a literal.
5. CHECK 6 secrets patterns: add the install's own DIAG_KEY and BOX_API_KEY values, the Railway token value, and IPv4 literals; distinguish documented pointers (8-char token prefix, the string "github_pat_" in instructions) from live values — when in doubt FAIL and surface file+line.
6. "Today" is ambiguous across seats/timezones. Use session_start (sha or ISO UTC) for every window; drop "== today".
7. Form: the spec says build the sandbox runnable (a) first, the box op (b) later. REVERSED under the lockdown principle: a sandbox runnable leaves no ledger row a stranger can walk to; build (b), the box op, on install two first. (a) can exist as a convenience wrapper that calls (b).
8. CHECK 7 assumes MAIN+FARM; install two has one engine. Read the engine list from config.
9. No check that the handoff's next-action line is parseable by the gate's own rule (one line beginning `**NEXT` or a "SINGLE NEXT ACTION" heading followed by exactly one line). ADD the parse to CHECK 8.
10. Return shape: keep `{closed, seat, checks[]}`; ADD `session_start`, `ledger_row_id` so the gate's own run is itself a ledger fact.

## BUILD ORDER (cheapest-unlock first; each = repo commit + box install (write_file + restart_workspace) + OP_ALLOWED entry + engine deploy — the documented new-op two-step; install two first)
1. `describe` — small; removes the op-body drift class; the fresh seat's commit_file probe becomes a describe call.
2. `orient` — searches agent_queue.md folds + live/conversations/ for the topic; returns hits with file+line or "none"; logs topic + hit count.
3. `close_gate` — the June spec + gaps 1–10 above.
4. Packet v3 (install two, then operator): boot ends with `bootstrap_gate` (oriented:true is the boot's return); close ends with `close_gate` (closed:true is the close's return). Manual COLD-BOOT gains: "sandbox shell is sh (dash); use python3 for anything beyond a one-liner."
5. Promote to the operator install through the two-party deploy chain once each op has a ledger row on install two.

## ACCEPTANCE
Each op: a ledger row per call; a deliberately-failing call produces the right failure message; a fresh seat on install two completes a boot+task+close where the only evidence consulted is the ledger and the repo (no self-report accepted).
