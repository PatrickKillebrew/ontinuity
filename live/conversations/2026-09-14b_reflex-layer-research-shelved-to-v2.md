# 2026-09-14 (session B) — The reflex-layer exploration (small Ontinuity-trained model), researched and SHELVED to V2; focus returned to v1 packaging

Session type: control-seat design exploration + research; no code shipped. FORM: condensed decision-record per CONVENTION.md (rulings verbatim).
REDACTION: clean. LINEAGE: operator (Patrick); agent claude.ai-chat:claude-fable-5.1. Follows 2026-09-14a.
DEPLOY: none. Corpus-only fold (this record, a queue fold, V2_ASPIRATIONS §V2-E, CONTROL_HANDOFF, PUNCH_LIST header).

## HOW THIS SESSION OPENED
The prior chat (the one that produced 2026-09-14a) hit its context limit and was flagged by a platform safety classifier; its content was
redacted from the recall tools. The operator: "I had completed significant work toward the end of that conversation and it looks like it's gone."
VERIFIED against the repo: NOTHING LOST — commits f092f25..1e5d613 all on main (compliance mechanism build, record 2026-09-14a at 8c8aa63,
fold at 1e5d613, pushed one minute before the window closed). The flag reason is not visible to the seat; the session's content was
infrastructure + design work; the only plausible trigger is credential handling (tokens/PATs/auth headers), not operator behavior. Lesson
restated: the close ritual reaching the repo before the window closes is the durable protection.

## RULINGS / DIRECTION (operator, verbatim)
- "The minimal is single seat." (carried from prior session; the v0 single-seat corpus design candidate stands as proposal-to-react-to)
- "No facts in weights is the key to the trained model success. Got it."
- "All we need the Ontinuity trained model to do is make sure all functions or capabilities of Ontinuity are performed as written or documented."
- "The fact that it runs on close means it does nothing to help mid session where the failure occurred. Waiting for accounting of everything
  at the end feels disjointed... Wrapped ops are a solid fix because they eliminate false paths. The checker needs to be impactful in that way."
- "The checking needs to be done against OSHA regs while the training is being built. We can have the system spend time building something
  then give the user a receipt at the end telling them about the errors it caught."
- "If the write is to the corpus, it's already too late."
- On cross-matter retrieval in the same model: asked; seat's answer (facts-in-weights + a second label space -> a retriever's/cartridge's job)
  accepted without objection.
- "Let's store this away as a future aspiration... it's only going to take away from finishing packaging Ontinuity. Let's switch our focus back
  to finishing that after folding this into the corpus, research and all."
- Delegation intent: eval/training-set extraction to GPT-5.6 Sol (Max 5x account; "It already knows Ontinuity and has used the hands").

## THE ARC (what the seat proposed, what the operator rejected, what survived)
1. Seat proposed the checker as a CLOSE-GATE assertion checker (v1 hedge). REJECTED: too late, disjointed, not reflexive.
2. Seat moved it to the COURIER as a response filter (bounce-with-reason before the record write, like railway_set_var's 409). REJECTED by the
   operator's question "do you mean my response to this prompt would be checked before it got delivered?" -> yes, and only possible for
   engine-hosted seats; and the reflex fired at the CHOICE of urllib, before any message. Filtering output is a faster accountant.
3. What survived: the TOKEN-LEVEL version = PROXY-TUNING (a small tuned expert + its untuned anti-expert steering a frozen capable model's
   logits every step). The seat identified it as the mechanical form of the operator's own 2026-09-14a sentence ("a run-time reflex harness...
   the Ontinuity-trained model becomes that layer"). Operator: "That sounds much better. I don't know how confident I am in that approach, but
   it is intriguing."
4. Research grounding (web-verified this session; full trail in V2_ASPIRATIONS §V2-E): the problem is named in the literature
   (context-memory conflict / context faithfulness); Gekhman 2024 + context-parametric inversion argue AGAINST facts-in-weights; TTT-E2E /
   In-Place TTT / SEAL show context->weights at runtime is a live line; Cartridges (ICLR 2026) give facts-in-KV-cache, composable per matter;
   CAD / CK-PLUG give ZERO-TRAINING decode-time knobs for the exact dial; Wang et al. EMNLP 2025 already apply proxy models to this problem;
   ContextFocus / SHIFT give per-session activation steering. Experiment ladder: (1) zero-training knob, (2) proxy expert, (3) activation
   steering, (4) cartridges. Rung 1 is the go/no-go.
5. Hard constraints stated plainly: full-vocab logits needed (self-served open-weight base, vLLM on a rented GPU — the real decision); shared
   tokenizer (Llama-3.1-8B expert / Llama-3.3-70B base); steers, doesn't gate; iPad hosts a demo, not the mixing point, and cannot train.
6. Operator's decision: SHELVE to V2 (§V2-E). Resume v1 packaging.

## CORRECTIONS THIS SESSION (seat errors, operator-caught)
- The seat drifted from the prior session's synthesis (interposed filter) to a close-gate audit and called it a "first prototype"; the operator
  caught it ("I feel like you are missing a big part of context that the prior conversation had"). Corpus (record 2026-09-14a) was right.
- The seat's "courier response filter" was a stretch-to-fit; the operator named it ("stretching this to fit instead of breaking new ground").

## STATE LEFT
main = (this fold's commits). No code, no deploy, no box change. Engine untouched since 1e5d613. V2_ASPIRATIONS gains §V2-E.
The per-project-memory certified-close acceptance test remains pending (needs the fixed Challenger to review).

## NEXT
Resume v1 PACKAGING: execute PROVISIONING_RUNBOOK.md (private repo projects/the-package/) Phase 2 — stand up ONE operator-controlled second
install and boot a Claude seat into it (ROADMAP Phase 2 gate). Phase 3 (non-Claude seat) only after Phase 2 passes. Held-but-not-lost:
V2 aspirations incl. §V2-E; wrapped-op extension to deploy etc.; close-gate assertion enforcer; the Sol extraction hand-off (deferred with V2-E).

CROSS-REF: records 2026-09-13d, 2026-09-14a (8c8aa63); folds 80e44bc, 1e5d613; V2_ASPIRATIONS.md §V2-E; PACKAGING_PLAN.md; CONTROL_HANDOFF.md.
