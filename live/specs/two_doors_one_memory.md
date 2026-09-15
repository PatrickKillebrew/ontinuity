# SYNTHESIS — TWO DOORS, ONE MEMORY: where every component belongs and how it fits our goal (2026-09-15)
*Pass 3 over the corpus (TOTAL_INDEX, STATE_OF_ONTINUITY, horizons.md, oracle.md, the Oracle-shelved and Coordinator-retired folds, the map §2-4, the specs, app.py, db.py, the prompts). This is the "make something of it" document. Nothing here reverses a recorded decision; where a recorded recommendation exists it is cited and kept.*

## 1. THE PLACEMENT (what each thing was built to support)
| Component | Door / layer | Built to support | Status |
|---|---|---|---|
| Tetraform 4-model loop, Parietal (PRE_SESSION/NAVIGATE/ADJUDICATE/DISTILL), frozen contract + `contract_criteria`, Fix #1 certified close, F.3 execution-claim detector, EXPERIMENT_MODE, work_product/final_synthesis | RESEARCH door (the VERIFICATION gate a design session calls) | fabrication-free deliverables — the published "gate-and-contract" thesis | LIVE (final_synthesis dormant) |
| Projenius (ORIENT / SYNTHESIZE / LEDGER_QUERY / DISTILL-fallback), Knowtext 7 fields, ERL file, `established_results` + `projenius_ledger_operations` DB API, box `/api/ledger` | RESEARCH door's MEMORY across sessions | "the project's long memory" for research matters; the operator's hunch is correct: Projenius belongs to the adversarial work | ORIENT+SYNTHESIZE live on the operator engine; LEDGER_QUERY never called; DB API never called (0 rows); not configured on install two |
| Folds, PUNCH_LIST, conversation records, handoff, open/close rituals; bootstrap_gate, orient, describe, seat_sessions, per-identity keys, close_gate; /agent/handoff; Governor | DESIGN/BUILD door (the chat seat + corpus) | continuity and reliability for the operator's own building — and the packaged product's memory door | rituals now mechanical on install two (L1-L5) |
| Mailbox, worker manual/packets, no-self-signoff, two-party deploy chain, you_there, PUNCHAUDIT pattern | DESIGN door's BUILD HANDS (the pool) | letting seats build together with peer review; sign-off distinct from authorship | live on the operator install; L4b pending (routes trust body seat) |
| Intake pipeline (Stage 1 live), PROBLEM_DEFINITION, four-stage pipeline, sanitizer, new_project (per-matter Knowtext/ERL) | INTAKE door | turning an outsider's problem into a matter with its own memory | Stage 1 live; per-project scoping wired 09-13 |
| Oracle (shelved: no consumer, too slow for a turn), Coordinator (retired: redundant with the no-self predicate) | museum | — | do not resume (recorded rulings) |

## 2. THE FINDING THAT ORGANIZES IT
The design door re-implemented the research door's memory machinery AS DISCIPLINE: the fold is DISTILL by hand; the punch list is the ERL by hand (erl_decision.md says exactly this); the record's sha cross-refs are F.3 by hand; the close ritual is Fix #1 by hand. This week turned the design door's discipline into gates and ledger rows. The remaining misalignment is that the two doors keep SEPARATE memories of the same matter: research results land in Knowtext/ERL; design outcomes land in folds/punch list. A seat resuming a matter reads one or the other depending on which door it enters by.

## 3. THE ALIGNED SHAPE — one memory, two doors, no model call in the design door's close
Keep Projenius where it belongs (research door; model-driven distillation is its job). Do NOT give the design door a model-driven close (it would put a provider dependency in the packaged remembering seat and contradict "reproduce, don't invent"). Instead align the ARTIFACTS on one substrate:
- `established_results` (with `projenius_ledger_operations` for every change) becomes the shared "what this matter knows" ledger, written from BOTH doors: research door via SYNTHESIZE parsed into the existing db.py API (erl_decision Option A cheap half); design door via close_gate reconciliation (an item DONE-with-sha -> insert_established_result, confidence ESTABLISHED, supporting session = seat_session_id; a REVERSED entry -> retract_result with grounds). Files stay primary (the 09-13 index's recorded recommendation: file-primary, relational as the LEDGER_QUERY substrate) — the table is the audited index, not a replacement for folds or Knowtext.
- The punch list adopts the governor panel spec's format contract + stable item ids (design door); Knowtext Open Questions keep their what/why/tried/next rule (research door); both are "open items with a next step" and both can be rendered by the same panel.
- `orient` (design) returns ERL hits alongside fold/record hits once rows exist; LEDGER_QUERY (research) becomes a `ledger_query` op over the same table (the 09-13 index already recommended this as a courier op).
- close_gate CHECK 10 = F.3 pointed at the conversation record vs the seat session's operations_ledger rows (claims of the form committed/wrote/deployed/restarted checked deterministically). The operations half of the assertion rule, no model.
- `status` = the LIVE /agent/handoff extended with open seat_sessions, the session's contract items, the last close_gate result, and the matter's established results -> the receipt; rendered by the Governor punch-list panel for the operator; returned to a resuming seat as its boot report.
- The user never authors anything: the seat sets the punch-list slice at distillation (`contract_set`), close_gate reconciles, the panel shows the receipt. Exploration sessions close as exploration-only.
- Projenius on install two: configure ONLY when a research matter is opened there (Phase 3/4); the remembering seat does not need it.

## 4. WHAT THIS ADDS TO THE WORK ORDER (proposed; operator rules)
- L6.5 (exists) gains: punch-list format contract + ids; `contract_set`; close_gate CHECK 1 reconciliation; `ledger_record` at close writing DONE/REVERSED items into established_results via db.py (audited rows); /agent/handoff extension; CHECK 10 (F.3 over the ledger).
- L6.6 (new, small): parse SYNTHESIZE's RESULT blocks into the db.py API on the research door (erl_decision Option A cheap half) so both doors write the same table.
- L6.7 (new, small): `ledger_query` op = box /api/ledger + the prompt function; `orient` includes ERL hits.
- Governor punch-list panel: build from its spec, reading the same JSON as /agent/handoff.
- Map: add the worker section and the two-doors-one-memory placement above.

## 5. WHAT NOT TO DO (recorded)
- Do not resume the Oracle or the Coordinator (rulings 06-29, 06-30).
- Do not move the research door's memory out of Projenius or make the design door's close model-driven.
- Do not create a second "contract" document or a second "established" concept; do not build a new claims checker or a new status endpoint.
