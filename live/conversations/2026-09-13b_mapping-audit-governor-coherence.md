# 2026-09-13 (session B) — Mapping audit, front-door coherence, and the multi-tenancy re-decision (control seat, Fable)

Session type: control-seat design + verification. FORM: condensed decision-record per CONVENTION.md —
rulings quoted verbatim, narration summarized. REDACTION: clean, no keys/tokens/IPs. LINEAGE: operator
(Patrick); agent claude.ai-chat:claude-fable-5.1. Follows 2026-09-13_rollback-reconciliation-fable-boot.md.

## WHAT SHIPPED
- Mapping audit of Opus's snippet-level maps COMPLETED. Five gaps closed and folded:
  - Seating mechanism + in-engine close gate -> ONTINUITY_CONTINUITY_MECHANISM.md §10 (commit 2a43da4).
  - NEW depth-arm ONTINUITY_INTAKE_MODE_SHS.md (the shipped SHS/SantaClean product), master map §25 (2a43da4).
  - SHS framing corrected to "worked example of Mode A", not "the packaging template" (f7053b7).
- Deployment rollback VERIFIED complete: Railway MAIN latest-SUCCESS = the reconciliation commit on the
  5640170 engine; FARM = f9696c49; live cockpit serves 0 ADMISSION panel; box files congruent with repo;
  one inert B1 config (trusted_deploy_config.json) neutralized on the box in place (no delete op exists).
- Queue CHECK-2 staleness fixed: a fresh CURRENT-STATE TOUCH POINT fold advanced NEXT from the (now-done)
  mapping audit to Phase 2 (commit 156b37f). Gate re-verified reading the current action.

## RULINGS (operator, verbatim intent)
- On multi-tenancy / reusing B1: re-evaluated at the operator's request ("since B1 is already built... is
  there any advantage?"). DECLINED again on the merits after weighing — it re-walks documented reversal #3
  (the-package mini_corpus): "Cornel will never touch my personal engine... They will be their own landlord.
  That's what makes this portable and private." Advantage of the shared path is small and temporary
  (skip provisioning one box); cost is permanent (shared-key blast radius, cross-customer data guarantee,
  the unsolved per-identity-key ceiling, and it is not handable/ownable). B1 stays museum; only its hygiene
  lessons are kept. Operator confirmed: "Let's stick to the original plan."
- On the second system: fresh infrastructure, landlord model — "It's going to be nice to have a 2nd system
  set up to demo with." Hetzner + Railway are cheap enough to justify. Exercises Mode B (what the BIL uses).
- On the design side (this session's steer): "The whole design side... feels like it has not gotten
  attention. There are opening and closing rituals and folding in between that feels like it's gotten no
  love yet. This is where designing happens and memories get stored away to create future value as a
  corpus." -> mandate to study RITUAL_MECHANICS + real folds/records deeply and document THIS work in form.
- Corpus-write protocol (standing, re-observed): the operator says when to write to the corpus.

## THE DESIGN / FINDINGS (settled against source)
- BOTH FRONT DOORS are now coherent in the maps. MODE B (design/build; operator + Control seat) is FULLY
  LIVE and verified end-to-end this session (boot oriented:true, 19-op hands, 328 sessions, memory persists,
  box congruent). MODE A (intake -> four-stage pipeline -> shipped result) is coherent as a MANUALLY-RUN
  pipeline (SHS is the shipped proof) but has ONE unbuilt automation seam: the intake->Knowtext/mini-corpus
  bridge (four_stage_pipeline.md: stages 2-4 are DESIGN; the mini-corpus handoff "is NOT yet built"). That
  seam is OUT OF SCOPE for a BIL tryout, which is a Mode-B use.
- GOVERNOR STATE (answers the operator's question, grounded in live/governor/ + PUNCH_LIST): the read-only
  3-panel monitor is BUILT + LIVE (/governor, /governor/data, /governor/workers; commits d1a16d4e, 7f185995;
  X-API-Key gated). "Governor-with-hands" is DESIGNED but GATED on the Seat Registry / identity primitive
  (north-star step 3), which is not built. Two governor specs are design-only. So the Governor is
  deliberately unfinished at a recorded gate, not neglected.
- SEATING MECHANISM (the audit's key depth-add, read from app.py): two distinct "mailboxes" — the box
  seat_mailbox (worker claim/lease) vs the engine in-process external_mailbox (turn_id/waiting/event) that
  seats an EXTERNAL model as the Researcher via GET /mailbox/turn + POST /mailbox/respond (auth MAILBOX_KEY,
  not the diag key); the switch is MODEL_A_URL=external; the agent's words re-enter the identical F.3/
  contract glass "because call_model's caller cannot tell the difference." This is how any model sits in
  the seat, and why the Sept-3 cross-vendor succession worked.
- DISTILLATION verified against running code: run_parietal_distill (Parietal DISTILL -> 7 fields, timeout)
  runs FIRST, run_distillation (Projenius + knowtext_extraction_prompt.txt) is the FALLBACK; distillation_
  method records which fired. Corrects the original "Projenius writes Knowtext."

## THE FAILURE (recorded, not hidden)
- The mapping audit's driving cause was, again, priors-over-source: I initially called SHS "the concrete
  packaging template," conflating how a PROJECT'S deliverable ships (SantaClean's PyInstaller/Inno build)
  with how ONTINUITY installs for a new operator (the PROVISIONING_RUNBOOK). The operator corrected it:
  "Is Gap 4 actually the concrete packaging template? It is an example of an item going through the 4
  stages of development to fruition. This is one way that Ontinuity is used." Fixed in the arm + map.
  Same failure-class as the four reversals; caught by the operator, not by me.
- Before this session I had been running the rituals mechanically (writing folds/records) without having
  studied RITUAL_MECHANICS's HOWS AND WHYS. The operator named the gap directly. Studying it is what
  produced this properly-formed record. The lesson: writing the artifact is not the same as understanding
  why the joint needs the grease.

## STATE LEFT
main = (this commit). Engine idle (5640170), 19-op diag-key hands, gate oriented:true reading NEXT=Phase 2,
328 sessions, box congruent with repo, zero B1 residue in any boot doc, museum quarantined. Both front-door
paths coherent in the maps. Nothing half-finished behind the mapping work.

## NEXT
Execute PROVISIONING_RUNBOOK.md (private the-package/) Phase 2: the operator stands up a fresh 2nd install
(own GitHub repo + Railway project + Hetzner box + diag key, landlord model) to demo/hand to the BIL; the
seat prepares the parameterized boot packet + trimmed mechanism docs (§D) + empty-shape corpus (§E) and
verifies the boot gate (ITS __probe__ allowlist, ITS corpus read gate, a close ritual to ITS repo).
Account-creation steps are the operator's console actions (scoped keys can't create new accounts/projects).

CROSS-REF: maps ONTINUITY_MASTER_SYSTEM_MAP.md §25 + ONTINUITY_CONTINUITY_MECHANISM.md §10 +
ONTINUITY_INTAKE_MODE_SHS.md; commits 2a43da4, f7053b7, 156b37f; agent_queue CURRENT-STATE TOUCH POINT
2026-09-13; RITUAL_MECHANICS.md (private the-package/); the four reversals (private the-package/mini_corpus.md).
