# 2026-06-13/14 — Tetraform Test Sessions (isotest) — Empirical Backing for the Four-Stage Pipeline

FORM: decision-record / test-log. Compiled by the control seat from the prior control's session report (the June 13–14 thread). The individual CONCLUSIONS are already folded in agent_queue.md (cited per-item below); THIS record is the missing connective piece — the test sessions as a numbered sequence and as the mechanical PROOF of the pipeline's trust claims. Written so the evidence isn't a gap even though its conclusions were folded piecemeal.
PARTICIPANTS: Patrick (operator); HARNESS:claude (prior control seat, ran the sessions); folded by the fresh control seat.
REDACTION: clean.

## Setup (common to all four)
MAIN-engine Tetraform sessions, scoped to project `isotest`, driven by the control seat as the external Researcher via the mailbox (GET /mailbox/turn fetch, POST /mailbox/respond answer). Each objective was a small self-contained verifiable fact (a corpus table COUNT) chosen to exercise the pipeline end-to-end WITHOUT needing a real client problem — the point was the mechanism, not the answer.

## Session 1 — first reliability/injection probe (pre-fixes)
Purpose: shake out what actually worked. Findings: (a) DB_QUERY didn't route — wrong tag form ([CYCLE_STATUS: IN_PROGRESS] + a "DB_QUERY" label instead of the action tag); (b) the gate correctly REJECTED an ungrounded "21" claim because no query result was in evidence — fabrication-detection firing on the CONTROL SEAT ITSELF; (c) no clean close (result never injected). Operator-stopped. Surfaced BOTH the tag-form bug and the reliability bug. (Reliability root cause folded: agent_queue.md "Reliability fix (206de157)".)

## Session 2 — reliability-fix confirmation
After the reasoning-field parse fix (glm-4.7 returns its answer in a `reasoning` field, content empty — the weeks-long "incomplete_model_dead" root cause; it was NEVER a provider outage). Challenger ran clean across 4 cycles on Cerebras glm-4.7 with ZERO content-deaths — proved the fix at the LIVE-SESSION level, not just the parser level. Also proved Projenius DISTILL fires at close (distillation_method: projenius). (Folded: queue "Reliability fix", "Projenius woken from dormancy".)

## Session 3 — DB_QUERY tag-form correction (mid-run, learned live)
Correct form established: SQL on a `QUERY:` line, then `[CYCLE_STATUS: DB_QUERY]`. Once formatted right, the query executed and injected a real result block: `[DB_QUERY RESULT]: PASSED ... RESULT: {"columns":["COUNT(*)"],"rows":[[21]]}`. The gate then ACCEPTED the close because the finding was backed by evidence in context. PROVED THE FULL GROUNDED-CLAIM LOOP: issue query → result injects → cite from evidence → gate accepts. (This is the DB_QUERY-form fact now in OPERATING_MANUAL; the grounding-loop is the mechanical basis of the proposal's confirmed-vs-assumed discipline.)

## Session 4 — ERL behavioral test (clearly-qualifying result)
Ran on the deployed, worker4-verified ERL code (28ba1272), objective written to produce an unambiguously durable architectural result. Session completed clean (status: complete, distillation_method: projenius), query injected [[21]], close accepted — BUT no `erl_*.txt` written. This RULED OUT the benign explanation (Projenius judging the result non-qualifying) and established the open ERL bug: SYNTHESIZE either times out (30s) or returns output lacking a `RESULT:` block. NEXT: capture SYNTHESIZE's actual output. (Folded: queue ERL-bug entry ~line 687. UNCHANGED open thread.)

## What the four sessions collectively PROVE for the pipeline (the connective point — this is why the record exists)
These sessions are the EMPIRICAL BACKING for the four-stage pipeline's trust claims. They demonstrated live that:
1. The gate REJECTS ungrounded claims and requires evidence-in-context before accepting a finding — this is the provenance discipline (confirmed/assumed/open) working MECHANICALLY, enforced on the control seat's own claims, repeatedly.
2. DB_QUERY is the grounding mechanism that turns an ASSERTED number into a VERIFIED one — the mechanical form of "confirmed."
3. Projenius DISTILL runs at close (the mini-corpus write path) — though SYNTHESIZE→ERL persistence is the one UNPROVEN link (Session 4's bug).
In short: the proposal's "shows what's verified vs assumed" is NOT aspirational — the gate enforced exactly that on the seat's own claims in these sessions. The Stage-2/grounding half of the pipeline has live mechanical backing; the ERL persistence link is the one gap.

## Mechanics to DRIVE a session (for the next control)
- START: POST /agent/start with mailbox_key, objective, start_fresh:true, project_id, branch.
- DRIVE: GET /mailbox/turn?mailbox_key= to fetch the pending Researcher turn; POST /mailbox/respond with turn_id + response. turn_id may NOT start at 1 (stale external-mailbox state) — fetch first to get the actual pending turn_id.
- DB_QUERY form: `QUERY:` line + `[CYCLE_STATUS: DB_QUERY]`.
- CLOSE: report the grounded finding + `[CYCLE_STATUS: SESSION_END]`; the gate HOLDS the close until the Challenger agrees the deliverable is complete and evidence-backed; a final work-product synthesis turn follows before the session completes.
