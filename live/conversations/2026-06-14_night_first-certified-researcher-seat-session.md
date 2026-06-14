# 2026-06-14 (night) — First Certified Researcher-Seat Session (output-shape reliability demonstrated)

FORM: condensed. Written by the control seat (which also occupied the Researcher seat this session) at close.
PARTICIPANTS: Patrick (operator); HARNESS:claude-opus-4.8 (control seat AND Researcher-seat occupant).
REDACTION: clean.
LINEAGE: session 2026-06-14_22-19-08 (status complete, 5 cycles, challenge_count 3, uphold_count 3, distillation_method parietal, ERL +3 entries). Continues 2026-06-14_evening_button-lockdown-researcher-seat.md.

## Arc
After the public-button lockdown and the fold of the config trap, the seat re-attempted the Researcher-seat run — and succeeded. The cheap-path-first probe (start, watch the first routing signal) confirmed the vault's MODEL_A_URL=external was already effective (no redeploy needed; the stale runtime override had cleared). A `researcher_turn` posted to the mailbox — the proof of mailbox-seat mode — and the seat drove the session to a certified complete close, experiencing the harness from the inside for the first time.

## What was demonstrated (the milestone under the milestone — operator's framing)
The session is the FIRST clean end-to-end proof of the reliability thesis: the architecture took the most capable, most expensive seat occupant (a frontier Claude) and FORCED its output into a predictable, verifiable, PRE-INSTRUCTED shape. Three things landed together:
1. OUTPUT-SHAPE RELIABILITY. The contract was authored from the objective BEFORE the session, frozen (3 criteria), and the gate held the seat to it — THREE upheld challenges — until the deliverable matched the pre-specified shape. The shaping was determined in advance, not improvised. This is the difference between "an impressive answer" and "reliable infrastructure": output conforms to a contract written before the model spoke. THIS is what makes stage-2 (problem-dissolution) outputs reliable, predictably-shaped, and therefore usable as stage-3 (decomposition) inputs. A cheap open-source frontier model under the IDENTICAL gate inherits exactly this reliability — the expensive run proved the gate; the penny-a-cycle run gets it for free. That is the economic + trust thesis, demonstrated.
2. THE SYSTEM PRODUCED 3 EXACT EDITS. Not "roughly fix the docs" — three ready-to-apply, precisely-specified document edits. Usable-shape made concrete: stage 3 could decompose them into commits with zero re-interpretation. "Almost the right shape" is unusable downstream; the gate catches the near-misses (a line number instead of code, an inference instead of a citation, a prose description instead of a formatted edit — exactly the three things the gate caught on this seat).
3. THE ERL WROTE. The day-long open thread (SYNTHESIZE fires but never persists erl_*.txt) did NOT recur: the close committed the ERL to GitHub with 3 result entries. Evidence the ERL write path works on a REAL grounded complete close — narrows the open bug to whatever was different about the isotest test-session closes, not the write path itself.

## The three gate challenges (the harness working on the most expensive seat)
The Challenger/Parietal UPHELD three times; the seat genuinely could not self-certify:
- C1: cited box_ops.py:301 by line + paraphrase, did not QUOTE the code → forced to retrieve and quote the source-order logic verbatim.
- C2: argued from ledger OUTCOMES that the rate-limit was irrelevant → forced to quote the actual code (the docstring naming the shared-egress rate-limit + the _via_raw ?cb cache-bust mitigation), defending the ledger as corroboration not sole basis.
- C3/consolidation: gave prose edit descriptions, then evidence scattered across cycles → forced to format exact insertion blocks and assemble one consolidated deliverable with all 3 criteria inline.
A frontier model left alone would have closed at cycle 2 on a confident paraphrase. The gate forced grounding in quoted code + cited evidence before close. Demonstrated on the most expensive seat — the reliability lives in the ARCHITECTURE, not the model.

## The session's actual content (CDN reconciliation — the objective)
DELIVERABLE (certified): the read_repo "delete raw-CDN" decision (agent_queue ~606) is WRONG. Grounded findings: read_repo lives box-side in box_ops.py op_read_repo (NOT app.py — app.py holds only the OP_ALLOWED relay). Source order: (1) authenticated api.github.com IF github_token passed; (2) raw.githubusercontent + ?cb=<unixtime> cache-bust; (3) unauth api.github.com last resort. Workers hold no token → path 2 (raw-cachebust) is the STRUCTURAL PRIMARY for tokenless callers, not a fallback. operations_ledger corroborates: every tokenless read_repo success served via raw_cdn_cachebust (incl. app.py at 216/220/230 KB), zero staleness failures, the 24 fails are 404s not 403/429 rate-limits. The stale-CDN trap is already mitigated in-code by ?cb. RECOMMENDATION: keep the code, correct the docs (3 exact edits — see below). The contradiction was documentation drift, not a code defect.

## DELIVERABLE'S 3 EDITS (to apply as control-seat commits — pending)
1. agent_queue.md ~606: append a "CDN-DECISION SUPERSEDED" note re-scoping the read_repo source-priority item from "DELETE raw-CDN" to "no code change; correct the docs."
2. WORKER_MANUAL.md read_repo bullet: rewrite the source-order clause to present raw-cachebust as the tokenless PRIMARY (not a fallback), cache-bust prevents staleness, pass github_token only for guaranteed-fresh.
3. WORKER_MANUAL.md persistence-rule 216KB example: append note that for a tokenless seat raw-cachebust is the primary path, not an emergency fallback.

## DRIVING MECHANICS CONFIRMED (refines the manual section added earlier today)
Cheap-path-first works: just start and watch the first routing signal — researcher_turn at the mailbox = in the seat (vault external effective); a Cerebras call = stale override, stop instantly. No redeploy needed if the override already cleared. turn_id started at 8 (stale state). The pre_session_questions turn authors the contract; then researcher_turn cycles; the gate holds SESSION_END until the Challenger agrees; a final synthesis turn (code-assembled VERIFIED RESULTS verbatim first + narrative) writes the work product before complete.

## DECISION: document this in a PAPER
Operator: write a paper so others can understand the process and benefit. The session demonstrated output-shape reliability (not just "a session ran") — the insight that makes the stage-2-feeds-stage-3 automation argument concrete. Paper to be drafted this session.

## CARRIED OPEN
- Apply the 3 CDN doc-edits (control-seat commits) — pending.
- Paper draft — in progress this session.
- ERL write bug: narrowed — writes on a real complete close; what differed in the isotest closes is the remaining question.
- Engine-URL auth gating (now urgent, public site); web-UI socket events not in ledger; mini-corpus; close-ritual gate; KEYS-2-FIX unsigned — unchanged.
