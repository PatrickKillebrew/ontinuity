# DEEP-DIVE FINDINGS — what already exists that integrates the session-contract / receipt / per-project reconciliation idea (2026-09-15)
*Operator asked for a full look at the corpus: the ERL, the worker system, the map, punch-list OPEN items, specs, horizons. Every item below was READ this session (file named), not recalled. Companion to session_contract_receipt.md.*

## A. THE ERL (Established Results Ledger) — what it is
- Per project+branch: `erl_<slug>.txt` file layer + `established_results` DB table (result_text, confidence PROVISIONAL/ESTABLISHED/RETRACTED, supporting_sessions, confirmation_count, retracted_by_session + grounds). Projenius (the project-memory seat) SYNTHESIZEs it at cycle end; Projenius ORIENT reads Knowtext's Open Questions field (get_open_questions_context). Continuity mechanism doc: "Projenius = project memory across sessions — the ERL."
- erl_decision.md (worker1, PROPOSE-ONLY): established_results has 0 rows; "the folds already function as a working ERL by hand"; recommends phasing Option A (wire structured persistence: parse the already-specified SYNTHESIZE format into rows; fix the misleading 'ledger updated' emit) — cheap half now, provider half later.
- READING: the ERL is the engine-side "done with evidence, retractable" for a matter. The design door's contract/receipt is the seat-side twin. The `established_results` schema (confidence, supporting sessions, retraction grounds) is the right model for a reconciled punch-list item.

## B. THE WORKER SYSTEM — how workers work a punch list and check each other (WORKER_MANUAL.md, seat_mailbox.py, signoff_deploychain.md)
- One-node primitive: roles are emergent from the mailbox item KIND. `task` -> author (stage/propose exact bytes, never sign or deploy own bytes); `proposal` -> reviewer (sign if clean; if changed, you become the author and resubmit). Same node, same loop.
- Control dispatches punch-list work as blocks (block_id, e.g. PUNCHAUDIT-1, ERL-1, KEYS-1, HANDOFF-1) to `any_worker`; `mailbox_fetch` claims atomically with a 15-min lease; `_noself_predicate` keeps a seat from claiming its own proposal; `you_there` self-drains a turn; the ACK carries a POINTER (sha/receipt/path) and IS the worker's handoff. States of done: staged -> signed -> committed -> live.
- punch_reconcile.md (PUNCHAUDIT-1, worker1): a worker audited PUNCH_LIST against commits and proposed moves, each tied to a sha — "every fold reconciled against it, mechanically" ALREADY HAPPENED as a dispatched block, PROPOSE-ONLY, control merges. This is the pattern for periodic reconciliation: a block, not a seat's memory.
- The master map has no section on any of this (measured 2026-09-15: ~2.6k of 78k).

## C. THE RECEIPT SURFACE — designed in June
- governor_punchlist_panel_spec.md (DESIGN ONLY): born from the operator's line "I can't see the punch list, I rely on faith." `/governor/punchlist` returns PUNCH_LIST.md parsed to JSON {resolved_at, done[{title, closed_by}], in_progress[{title, tier, awaiting, ref}], open[{title, tier, cluster}], counts}. Includes a FORMAT CONTRACT for the punch list (exact headers, `- **Title**` bullets, closing ref in DONE bullets, tolerant parser). This is the stable-id / machine-readable punch list the seed needs, already specified.
- agent_handoff.md + app.py: `/agent/handoff` is LIVE (verified on install two 2026-09-15: engines, queue_head, open_turns, latest_receipts in one keyed call). The spec's "PROPOSE-ONLY" status is stale. It is the skeleton of `status`: add open seat_sessions, the session's contract items, and the last close_gate result and it IS the receipt / the resume seat's boot report.

## D. CONTRACT-ADJACENT PIECES
- BOUNDARY_GATE_PRIMITIVE.md: "a session cannot close until output matches the frozen contract" — the engine's Contract-gate; the design-door contract is the same primitive at session scale.
- four_stage_pipeline.md: every finding carries a status (the intake door's evidence discipline); front half = problem -> spec; back half = propose -> build -> peer-review -> deploy.
- PROJECT_CORPUS_RUBRIC.md / continuity mechanism §4: per-project PUNCH_LIST/ROADMAP(locked decisions)/CURRENT_STATE/sessions/fold; engine = shared tool, corpus = workpiece; contamination rule; judgment-not-obedience.
- conversation_fts.md (PROPOSE-ONLY): records into the DB as FTS5 evidence — would make `orient` and the receipt's "why" queryable by SQL instead of file grep.
- signoff_provenance_spec.md (DESIGN ONLY): human sign-off as a ledger row, not a commit-message string — the L9 promotion should use it or at least not contradict it.
- Continuity mechanism §3 "bring into reality": (1) the CLOSE gate [DONE this week as L5 on install two]; (2) Projenius DISTILL configured on the live engine [STILL A GAP] — the automatic Knowtext delta at close. With both, "the circuit fires end-to-end with no human doing the ritual by hand — which IS the product."

## E. L4 RECONCILED AGAINST per_identity_keys.md
Steps 1, 2, 4, 5 of the spec's build order are done (ledger caller, registry+resolver, courier pass-through, real issuance). Step 3 — migrate the MAILBOX routes (send/fetch/ack, the no-self predicate) to the key-derived seat — is NOT done: they still trust the body seat. Step 6 (reject the shared key on identity-sensitive routes) not done. Acceptance Q1/Q2/Q3 in that spec are therefore still open. => NEW ITEM L4b, before L9 (the worker mechanism's guarantees rest on those routes).

## F. WHAT THIS MEANS FOR THE BUILD (proposed reshaping of the seed; operator decides)
1. Punch-list format contract = the governor panel spec's (already written). Adopt it; give items stable ids as a small extension.
2. seat_sessions gains `project`; `contract_set {items[]}` marks items IN-PROGRESS under the session (ledger row); close_gate CHECK 1 reconciles those items (DONE with sha / OPEN with carry).
3. `status` = extend the LIVE /agent/handoff with open seat_sessions + contract items + last close result -> the receipt and the resume boot report. The Governor punch-list panel renders the same JSON for the operator's eyes.
4. Periodic mechanical reconciliation = a dispatched worker block (the PUNCHAUDIT-1 pattern), not a seat's memory; propose-only, control merges.
5. ERL Option A cheap half (parse SYNTHESIZE into established_results) so the engine side keeps its own evidence ledger; and Projenius DISTILL configured on the live engine — the continuity doc's second "bring into reality" item.
6. Map: write the worker section from B above.
