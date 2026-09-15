# DESIGN SEED — SESSION CONTRACT + RECEIPT (per-project reconciliation as a ledger fact)
*Captured 2026-09-15 from operator/control exploration after L5 shipped. Status: DESIGN SEED, not built. Grounds: BOUNDARY_GATE_PRIMITIVE.md ("a session cannot close until output matches the frozen contract"), PROJECT_CORPUS_RUBRIC.md (per-project PUNCH_LIST/ROADMAP/CURRENT_STATE; engine = shared tool, corpus = workpiece), the intake door's PROBLEM_DEFINITION as ground-truth authority, seat_sessions (L3) and close_gate (L5). Operator: "This really resonates."*

## THE OBSERVATION (operator)
The grounding summary is valuable and only appears when the user asks. The adversarial engine has a frozen contract per cycle; the intake door has a problem statement per matter; the design/build door — where 90% of the work happens — has neither. A seat session now has a WINDOW but no statement of what it is for. close_gate checks the ritual was performed, not that the session did what it set out to do.

## THE SHAPE (agreed in exploration)
- ONE PRIMITIVE, THREE SCALES: state the goal before the work; judge the output against it; nothing closes until they match. Intake = per matter (outsider states the problem). Engine = per cycle (frozen contract). Design door = per SESSION of work on a matter (this seed).
- THE CONTRACT IS NOT A NEW DOCUMENT. The project's ROADMAP + PUNCH_LIST with acceptance per item ARE the contract (rubric). A session's contract is the SLICE: which of the project's items this session takes on. `contract_set` points at punch-list items and marks them in-progress under the seat session id — a ledger row, no authoring.
- TIMING = DISTILLATION. Exploration has no contract and must not be forced to have one. The SEAT sets the contract when it judges the work is distilled ("a good contractor writes the scope after the walkthrough, not the homeowner"). The packet teaches the reflex; the user just keeps talking. No contract -> the close notes "exploration only"; nothing is blocked.
- RECONCILIATION AS A FACT. close_gate CHECK 1 becomes: every item this session took on is DONE citing a sha, or OPEN with a carry note. This is also protection against orphaned mid-session detours (the Easter-egg pattern: explore, file, resume) — the close brings lingering work back into focus.
- THE RECEIPT. The user never sees a contract; they see a receipt: what you asked for, what got done (with links), what is still open. `status` = diff(contract, ledger). It doubles as the resume seat's boot report and replaces the ask-for-it summary.
- PER PROJECT. seat_sessions must carry a project (from the handoff's active matter; default = the install's own corpus). Punch-list items need stable ids (today: bold titles). The lockdown work this week is NOT a separate project: it is the main system's evolution toward packaging, and its work order (ritual_lockdown_punchlist.md) is the main corpus's punch-list slice for that evolution.
- FOLD TIMING. If the main work is contracted behind the scenes, a mid-session detour costs nothing that a fold cannot restore — so folding at the right moment (before a detour, at distillation) matters more than fold frequency.

## OPEN (operator asked; not decided)
- Is mechanical fold-reconciliation ("every fold reconciled against the contract") overkill? The user knows whether the work is done.
- Must any session that COMMITS work have a contract, or may it close as exploration-only?
- Where the seed sits in the lockdown order: after L6, before packet v3 (the packet teaches the reflex).

## DEEP-DIVE TARGETS (operator request 2026-09-15): the ERL, the worker system (how workers work a punch list and check each other's work), the master map, punch-list OPEN items, horizons/aspirations, specs and notes — find the half-built pieces that integrate with this.
