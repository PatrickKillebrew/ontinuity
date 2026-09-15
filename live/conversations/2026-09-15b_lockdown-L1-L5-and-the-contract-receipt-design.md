# 2026-09-15 (session B) — RITUAL LOCKDOWN L1–L5 live on install two; the session-contract/receipt design; three corpus deep dives and the prose-to-code walk

FORM: condensed decision-record per CONVENTION.md. LINEAGE: operator (Patrick); agent claude.ai-chat:claude-fable-5.1. REDACTION: clean (no keys, no box IP). Follows 2026-09-15_install-two-provisioned (same day, morning close 7af2ee8).

## WHAT SHIPPED (operator repo, install two as the test bed; MAIN/FARM/operator box untouched)
- L1 `describe` (6a31203) — op schemas as an op; undocumented-route detection; allowlist diff.
- L2 `orient` (64e8722) — the per-task open ritual as a ledger row.
- L3a portable `gate.py` + L3 `seat_sessions` (3b71fb1) — gate values per install ("absent = this install has none"); CHECK 1 manual vs LIVE probe; a seat session row opened on oriented:true.
- L4 per-identity keys end to end (39de9ad) — real issuance bound to the session; courier forwards X-Seat-Key; authenticated ledger caller; revocation + auditable refusal rows.
- L5 `close_gate` (9b3fd4b) — derived from staging/close_gate.py (worker11/worker22, June; preserved in museum/staging/); nine checks, window from seat_sessions, CHECK 5 derived from commit paths, CHECK 2 record cites a session commit, CHECK 9 orient row; closes the session and revokes its key. Proven both directions on install two (session 1e9cdf0a: 9/9, closed, key revoked; negative: five named failures).
- Design/record docs: session_contract_receipt.md (seed), deep_dive_findings.md, deep_dive_findings_pass2.md, two_doors_one_memory.md (with a recorded CORRECTION), prose_to_code_walk.md (+§6), ritual_lockdown_plan/punchlist (L4b, L6.5, L6.6, L6.7 added). the-package: runbook §J additions (check 2 pass, test drive closed, Product 2 C3 requirements), PUNCH_LIST updates.

## RULINGS (operator, verbatim or near)
- "Lock down any and every step that allows a model to trivially satisfy." (the lockdown principle: a step is locked when it writes a ledger row a stranger can walk to)
- Item 4 handled correctly by the install-two seat (flag + defer a contract-doc edit); "Let's fix this... let the new convo take care of it."
- Testing rule: give a seat only the goal and scope, never the mechanics; failures are the window.
- "Always look at what exists in the corpus. A lot of items have already been pre-built and have been waiting for their moment."
- Everything important must be auditable.
- The lockdown work is the main system's evolution toward packaging, not a separate project.
- The contract must not be jarring for a non-tech user; it happens in the background; the user sees a receipt.
- "Make sure you're not just seeing the parts and then stringing them together in any old way." -> the ERL correction (§3 of two_doors_one_memory.md); then "read the prose next to the code" -> prose_to_code_walk.md.
- The adversarial engine's place: "intake makes the matter, design sessions draft the training, the gate runs it against the regulation library before it goes to a plant floor, and the receipt is what he shows the auditor" — "the most basic framework for now."

## FINDINGS THAT CHANGE THE PLAN (all in the specs named)
- Pre-built and reused: the key registry/resolver, the June close-gate code, /agent/handoff (live), the governor punch-list panel spec, PUNCHAUDIT-1 (mechanical reconciliation as a worker block), the ERL DB API (never called), F.3 as the deterministic assertion rule, Fix #1 certified close, agent_queue.md shared by engine queue_update and seat folds.
- Corrections to my own proposals: design-door items must NOT be written into established_results (ESTABLISHED is earned in the loop); the design door in the map is a Mode B SESSION, the chat window is the control seat; mailbox-seat mode is how a user's AI sits in the Researcher seat with real gates.
- L4 vs per_identity_keys.md: step 3 (mailbox routes on key-derived identity) not done -> L4b before L9.
- Seat errors this session: two cloud-init-class bugs earlier; two ERL/design-door mis-framings caught by the operator's "double check" — both recorded with evidence.

## STATE LEFT
Engine idle. Operator install unchanged. Install two: 24-op allowlist; L1–L5 live; its own corpus closed by seat C (session 1e9cdf0a). Operator secrets: none in any commit (sweep at each step).

## NEXT
Operator to read walk §6 points 3–4 (Product 2 requirements; v1 vs Product 2 reconciliation) after the break. Then L6 (`commit_file` hardening) -> L4b -> L6.5 (the seat contract, mirroring the engine's PRE_SESSION/contract_close_check/queue_update) -> L7 -> L8 -> L9 (two-party promotion, worker signs).
