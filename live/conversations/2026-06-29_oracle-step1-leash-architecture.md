# 2026-06-29 — Oracle Step 1 + the Leash Architecture (control seat)

Session type: control-seat build + design. Public-site polish, the Oracle step-1 mailbox surgery (deployed live), and an extended architecture-design arc that settled the three-role leash AGAINST SOURCE — and exposed, live, the very failure mode the leash exists to stop.

## WHAT SHIPPED
- Website: buckyball essay reweight (907901f5); MoIP v0.2 docx (cf23a9df) + moip.html (0219bae8); buckyball/moip logos -> canonical liveMark SVG (8559024362, 78b64756); index nav fix (ad7438ee); HTTPS Enforce toggled on by operator.
- Oracle spec committed (9f2e4b22). Oracle STEP 1 (mailbox schema/contract) built, peer-reviewed, signed off, and DEPLOYED LIVE to seat_mailbox.py (verified: corr_id persists + round-trips, question/answer kinds, no regression). Pre-install full DB dump to PRIVATE repo (8c2bda80). Box->repo sync via commit_self (c58e4cb0).
- Housekeeping: read_repo RESOLVED do-not-delete (a28a9bec); manual 17->19 ops (10b1f233); bootstrap-gate step 2 reconciled, courier op LIVE (91dffd48).
- Design spec gated_session_substrate.md committed (d4a853b6) then CORRECTED (912973a7).

## RULINGS (operator, verbatim intent)
- "Ground in the corpus to get the answers that you need from the corpus." (Said more than once; the session's refrain.) Control repeatedly reasoned from memory/adjacent-layer reads instead of reading source; the operator forced each read. The read_repo resolution, the deploy-chain two-party rule, the engine-loop separability, and the shepherd/governor facts were all readable in single fetches and were reached for from memory first.
- read_repo: do NOT delete raw-CDN. Proven by the 06-14 Researcher ledger evidence — raw-cachebust is the tokenless workers' structural primary; deleting it breaks worker grounding (Control unaffected because it holds the token, but "Control is not the system; the workers are").
- The workers do not need the Oracle — they are reliable instruction-followers with clean context that catch their own mistakes. The Oracle / the leash is for CONTROL in a design conversation specifically, not for workers or farm sessions (those are already leashed).
- Two workers exist so they sign off EACH OTHER'S work — no invented third seat. The deploy-chain invariant is two parties: deployer != author-of-deployed-bytes. (Control invented a phantom third-seat requirement; corrected against the rubric.)
- The coordinator JUST coordinates — do not bolt the Oracle or deep-review onto it.
- Corpus-write protocol: the operator will say when to write to the corpus; control must not write or ask-about-writing unprompted (saves tokens/context).
- Don't ask permission for things both are waiting on (e.g. checking the mailbox) — just do it.

## THE DESIGN (settled against source)
- The one unleashed surface is the control DESIGN CONVERSATION; its failure mode is assert-from-memory / re-decide-settled / invent-a-detail.
- Oracle = a Tetraform session (grounding is the contestable judgment the close gate exists to gate). Coordinator = a deterministic code loop in the shepherd's lineage (drains the FIFO mailbox, runs the no-self-sign-off chain in code, fires courier ops; nothing bolted on). Governor = read-only pane, gains hands later (gated on the seat registry). Verified by reading run_session_loop (Tetraform-welded), shepherd.py (the code-loop conductor), seat_mailbox.py (FIFO atomic claim), governor_* (read-only).
- The ASSERTION RULE: before stating a load-bearing system-fact, show the grounding read in the same message; a config read is not a loop read.

## THE FAILURE (recorded, not hidden)
The design note v1 (d4a853b6) over-claimed a general substrate hosting the coordinator as a Tetraform session — extrapolated from the config layer without reading the loop body. Reading the loop disproved it; v2 (912973a7) corrected it and folded the lesson into the assertion rule. The cost was hours the operator paid for, building the leash while demonstrating why it is needed. The fix is the structural gate, not a promise to do better.

## STATE LEFT
Engine idle (running:False), no orphaned mailbox claims, DB backup independent of the live keys. One harmless VERIFY-INSTALL-1 question queued to "oracle" (clears at Oracle stand-up).

## NEXT
Oracle as a Tetraform grounding session (resolve gated-session latency vs the 60s window first). Then coordinator (shepherd-lineage code loop), then governor gains hands (gated on the seat registry). Roadmap: finish Oracle -> seat registry -> Governor glass pane.

CROSS-REF: agent_queue fold (this session); gated_session_substrate.md (912973a7); oracle.md (9f2e4b22).
