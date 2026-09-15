# DEEP-DIVE PASS 2 — Projenius, the ERL wiring, and what is pre-wired in app.py (2026-09-15)
*Every line read this session from prompts/projenius_system.txt, prompts/knowtext_extraction_prompt.txt, app.py, db.py, live/box/workspace_db_endpoint.py, the two vaults. Companion to deep_dive_findings.md and session_contract_receipt.md.*

## 1. PROJENIUS — what it actually is (the prompt)
"Never inside the session loop; called at project boundaries." Four functions:
- DISTILL — the seven Knowtext fields at SESSION_END (Climate Notes, Delta Log, Active Frameworks, Open Questions, Correction History, Valence Mapping, Identity). Rule: every Open Question states what it is, why it matters, what has been tried, and the defined next step — "vague open questions are closed questions in disguise." (= a punch-list item, defined.)
- SYNTHESIZE — after distillation: promote Delta Log results into the Established Results Ledger as ESTABLISHED/PROVISIONAL; mark retractions RETRACTED with RETRACTED_BY + GROUNDS; output the COMPLETE ledger (no compression; permanent record).
- ORIENT — before Parietal PRE_SESSION: PROJECT STATE (2 sentences), BRANCH CONTEXT (1), RELEVANT PRIOR RESULTS (<=5, verbatim with confidence) given the operator's objective. (= a boot report for a matter.)
- LEDGER_QUERY — "what does the project know about X": exact entries, ranked, at most ten, never inferred.
- Plus a parallel-distillation role (Projenius owns Delta Log + Open Questions; Model A/B/C/Parietal own the other fields) and a SEARCH function used for web-claim verification.
"You are the project's long memory. The Parietal remembers today. You remember everything."

## 2. WHAT THE ENGINE WIRES vs LEAVES LOOSE (app.py, read)
| Function | Wired? | Where / note |
|---|---|---|
| ORIENT | YES | session start (4720); fed ERL + Open Questions since 2026-09-13; SKIPPED when start_fresh (F.7 — deliberate no-contamination mode) |
| SYNTHESIZE | YES | session close (3718), after Parietal DISTILL; output written WHOLESALE to erl_<slug>.txt + pushed to GitHub by write_erl_ledger (truncation guard) |
| DISTILL | NO (Projenius) | the engine calls PARIETAL DISTILL (2650); Projenius DISTILL exists only in the prompt's parallel role |
| LEDGER_QUERY | NO | never called anywhere in app.py — but the BOX has GET /api/ledger ("used by Projenius LEDGER_QUERY and ORIENT") waiting for a caller |
| SEARCH | YES | web-claim verification path (3085, 3417) |
- call_projenius fires ONLY when PROJENIUS_URL + PROJENIUS_API_KEY are set. Operator MAIN: SET. Install two: NOT SET (so ORIENT/SYNTHESIZE no-op there today).
- THE ERL DB LAYER IS PRE-WIRED AND NEVER CALLED: db.py has insert_established_result, confirm_result, retract_result, get_active_results, insert_retraction_event, and _log_ledger_operation -> projenius_ledger_operations (operation_type add/confirm/retract/confidence_upgrade/downgrade/notes_update, justification, projenius_model, operation_at). app.py calls NONE of the writers. established_results has 0 rows (erl_decision.md). The box exposes /api/ledger (get_active_results) and the retraction insert. => erl_decision Option A "cheap half" = parse SYNTHESIZE's RESULT blocks into these calls; every ledger change then has its own audited operation row. Pre-wired, one parser away.
- session_ledger (in-memory per-cycle established results) + get_session_ledger_summary feed DISTILL; run_final_synthesis (2793, dormant) is the project-completion document generator — the "final receipt" for a finished matter.

## 3. THE FABRICATION DETECTOR (F.3) — the mechanical assertion rule, already built for the engine
check_execution_claims(text): deterministic, no model judgment. Extracts execution claims (commands, values) from a model's text and checks them against the session's execution_log; verdicts FABRICATED / MISREPORTED / CORROBORATED; v2 also catches FABRICATED FAILURES (denying logged successes). Fires on Researcher output per cycle (3032, 3302) and on the deliverable (2780, "F.3 audits the deliverable itself").
=> DIRECTLY REUSABLE for the design door: a conversation record's claims of the form "committed/wrote/deployed/restarted X" checked against operations_ledger rows in the seat session (op, path, sha, status). That is the assertion rule for OPERATIONS made mechanical without a model — the part of V2-E that does not need the trained checker. Candidate close_gate CHECK 10: record claims vs ledger rows.

## 4. THE ENGINE ALREADY HAS A CERTIFIED-CLOSE GATE (Fix #1, app.py 813)
A research session may be written 'complete' only if a SESSION_END tag appears in the transcript; otherwise 'incomplete_no_close' (or 'incomplete_challenger_dead' if unreviewed cycles). Outcome gated on evidence of certification. Twin of close_gate at the research-session scale.

## 5. HOW IT INTEGRATES (the shape, for the operator's ruling)
- The research door and the design door are the SAME LIFECYCLE with different substrates: ORIENT ~ orient/boot report; the four-model session ~ the seat session; DISTILL/SYNTHESIZE ~ the close ritual + ERL; Fix #1 ~ close_gate; F.3 ~ the assertion rule; Knowtext Open Questions ~ punch-list items; established_results ~ DONE-with-evidence, retractable.
- INTEGRATION PATH (each a small, pre-wired step):
  a. Wire SYNTHESIZE output into established_results via the existing db.py API (erl_decision Option A cheap half). Adds the audited operation rows for free.
  b. Wire LEDGER_QUERY: the box's /api/ledger + the prompt function -> a `ledger_query` op; `orient` returns ERL hits alongside fold/record hits once rows exist.
  c. Configure Projenius on install two (three vault vars) — the continuity doc's second "bring into reality" item, per install.
  d. Give the design door Projenius: at close_gate (closed:true), a `distill` op runs Projenius DISTILL over the seat session's record + ledger rows and SYNTHESIZE into the matter's ERL. The seven fields ARE the receipt; Open Questions with next steps ARE the punch-list carry; Delta Log IS "what got done"; Correction History IS "what was retracted". The user never sees the mechanism; /agent/handoff + the panel show the result.
  e. close_gate CHECK 10 = F.3 over the record (claims vs ledger rows), deterministic.
  f. run_final_synthesis becomes the matter-complete receipt.
- What NOT to invent: a new contract document (the punch list + Knowtext Open Questions already are it); a new "established" concept (established_results is it); a new claims checker (F.3 is it); a new status endpoint (/agent/handoff + /api/ledger are it).
