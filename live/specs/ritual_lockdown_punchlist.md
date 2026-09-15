# RITUAL LOCKDOWN — PUNCH LIST (sequenced; one item per session-of-work; each closes on a ledger fact)
*Companion to live/specs/ritual_lockdown_plan.md (the inventory + gap audit). This file is the WORK ORDER: items are sized to be built,
installed, verified, and folded individually so no seat has to hold the whole program in context. Rule for every item: DONE means a
ledger row a stranger can walk to, a deliberately-failing call that returns the right failure message, and the fold citing both.
Test bed: install two (ontinuity-two). Operator install gets everything in one promotion step (L9) through the two-party chain.
Method: the documented new-op two-step — repo commit (box/ + app.py OP_ALLOWED) -> box install (write_file + restart_workspace) -> engine deploy -> verify through the courier.*

Last resolved: 2026-09-15 (L1, L2 DONE; next L3).

## DONE
- **L2 — `orient` op.** LIVE on install two (64e8722; box install + engine-two deploy; allowlist 23). Verified through its courier and the ledger via /diag/api/query: rows 75/76 = 'manual currency' hits=5, novel topic hits=0, both ok; missing topic -> 400. Found: ledger rows carry no session key — 'by session' is by timestamp until L3 lands. Tokenless public-repo mode returns queue hits but cannot list live/conversations/ (raw CDN cannot list; unauth API rate-limits) — reported in the response, documented in the schema.
- **L1 — `describe` op.** LIVE on install two (6a31203). Every /op route reports its schema; undocumented routes surface; courier-allowlist diff; ledger row per call. Fold: ritual_lockdown_plan PROGRESS.

## SEQUENCE (dependencies in brackets; build in this order)

- **L3 — session rows: `session_open` inside `bootstrap_gate` [none; needed by L5, L6, L8].** The June close-gate spec takes `session_start` as an INPUT — a self-report. Fix at the source: a successful `bootstrap_gate` (oriented:true) writes a `sessions` row `{session_id, seat, caller_identity, started_at, closed_at:null}` and returns `session_id`. Every later op call that carries `session_id` is joined to it. Acceptance: boot -> row; the row's `started_at` is the window every gate check uses; `closed_at` set by L5.

- **L4 — per-identity keys / lineage stamping [none; needed by L5 lineage checks].** The box key registry (`file_server.authenticate_identity`, `ONTINUITY_SEAT_KEYS`) exists but install two runs on the shared DIAG_KEY, so the ledger's `caller` is whatever the body says. Issue a per-seat key on install two (control), have the engine courier forward it, and make `_ledger_begin` record the AUTHENTICATED identity. The record's lineage line is then copied from the ledger (L5 checks it), not typed by the seat. Acceptance: two calls with two keys produce two distinct authenticated callers; a body claiming a different seat than the key is logged under the key's identity.

- **L5 — `close_gate` op [L2, L3, L4].** The June spec (live/specs/close_ritual_gate.md) with the ten gaps from the plan: CHECK 5 derived from commits since `started_at` touching app.py OP_ALLOWED / box source / boot packets (no boolean input); CHECK 9 = an `orient` row exists after `started_at`; CHECK 2 adds "record cites ≥1 commit sha from this session"; CHECK 8 parses the handoff's single next-action line; secrets patterns include the install's own key VALUES; engine list from config (one engine on install two); return `{closed, session_id, checks[], ledger_row_id}`; sets `sessions.closed_at`. Report ALL failing checks in one run. Acceptance per the spec §5: a clean close passes; a close with the record deliberately skipped FAILS CHECK 2 with the right message; a close with no orient row FAILS CHECK 9.

- **L6 — `commit_file` hardening [none].** (a) No-op with `{ok:true, unchanged:true}` when box bytes == repo bytes at ref (the empty commit f86c20d class); (b) `dry_run:true` returns what WOULD change; (c) `message` required (no default "commit_file: path"). Acceptance: unchanged file -> no commit, row says unchanged; dry_run -> no commit, row says dry_run.

- **L7 — one seat per install: contention made mechanical [L3].** `bootstrap_gate` refuses (or warns, operator's call) when a `sessions` row is open with `closed_at:null` from a different caller identity, returning the open session's seat + started_at. The operator can force with `takeover:true`, which closes the stale row with reason `takeover` (logged). Acceptance: second boot while a session is open returns the contention message; takeover produces two rows with the join visible.

- **L8 — packet v3 + manual currency [L3, L5].** Boot ends with `bootstrap_gate` (booted == oriented:true + a session_id); close ends with `close_gate` (closed == closed:true). Manual: COLD-BOOT gains "the sandbox shell is sh (dash); use python3 for anything beyond a one-liner"; SCOPED OPS points to `describe` instead of listing bodies; OPEN ritual names `orient`; CLOSE ritual names `close_gate`. CONTROL_QUICKBOOT v3 stays platform-agnostic (v2.1 is the base). Acceptance: a fresh seat on install two boots and closes with the gates' returns as the only evidence of boot and close.

- **L9 — promote to the operator install [L2–L8 all DONE on install two].** One batch through the two-party chain: box source (live/box/*) + app.py OP_ALLOWED + packet + manual. Proposal by one seat, signoff by a distinct seat, deploy MAIN via `deploy`, box via write_file+restart. Acceptance: the operator install's probe shows the new ops; its next real close runs through `close_gate`.

## PARKED (not lockdown; packaging items tracked in the-package PUNCH_LIST)
- Section D seed must include live/conversations/CONVENTION.md.
- Section D docs platform-agnostic sweep (manual /home/claude + sandbox; paradigm/rubric model names).
- V2-E (assertion rule at the reflex level) — deferred by ruling until v1 ships.
