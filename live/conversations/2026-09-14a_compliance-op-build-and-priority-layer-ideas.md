# 2026-09-14 (session A) — The compliance chokepoint op (built+proven) + the corpus-vs-training-data leap (design seeds)

Session type: control-seat build + design brainstorm. FORM: condensed decision-record per CONVENTION.md.
REDACTION: clean. LINEAGE: operator (Patrick); agent claude.ai-chat:claude-fable-5.1. Follows 2026-09-13d.
DEPLOY: documented single-seat, operator-authorized.

## WHAT SHIPPED (the compliance mechanism v1 — built AND proven this session)
railway_set_var: the first WRAPPED OP implementing the "make every prescribed operation an op so the seat
supplies args and never constructs the call" fix (kills failure #1: method-invention). Commits c16115a,
eb475d1. Live in the 21-op allowlist (now 22 w/ railway_set_var... see NOTE). Proven end-to-end: the seat
supplied {name,value}, the op set a real Railway var. Mechanism verified: SELF-COUNTS failures from the
operations_ledger (no seat-monitor needed — every attempt flows through the op); REFUSES-TO-RETRY after 3
consecutive failures (proven: plain re-call -> 409); DELIBERATE RESET only via resolved_cause=<text> (proven:
stated cause -> 200, value landed). Box config.json now holds the Railway creds (read via load_config, the
diag_key pattern — the corpus method the seat had to be pushed 3x to use instead of inventing).

## THREE ROOT CAUSES FOUND BY BUILDING (proven empirically, correcting session-long wrong assumptions)
1. THE REAL "Railway egress" TRAP: not "curl vs Python". Railway's Cloudflare edge REJECTS the default
   "Python-urllib" User-Agent with 403/1010; a curl-like UA passes. This is why every model (GPT every turn,
   this seat 4x) tripped — it was the UA header all along. Now set once inside the op; no seat needs to know.
2. variableUpsert (a WRITE) authorizes ONLY with the Project-Access-Token header; Bearer returns "Not
   Authorized". READS tolerate Bearer (which misled the seat via a read-query test). The corpus
   (CONTROL_HANDOFF) had this right; the seat mistrusted it and drifted.
3. LATENT BUG uncovered: the box's _railway_deploy used Bearer -> box-side deploys were SILENTLY UNAUTHORIZED.
   This is the true mechanism behind the corpus's mysterious "known FARM seam". Fixed (eb475d1).

## RULINGS / DIRECTION (operator)
- "It's ok to make changes to the system when current setup blocks progress." (Authorized giving the box
  Railway creds; the seat's "trust model" objection was invented, not a real operator constraint.)
- On the meta-failure: "The problem boils down to training data vs. corpus." The seat repeatedly drifted from
  the record to its priors and had to be pulled back; every time, the record was right.
- On the Challenger-here: overkill; a TRANSLATOR of the failure for a non-tech user would be better than
  adversarial review (a v2 UX layer, not a reliability mechanism). The real adversarial Challenger-for-Control
  belongs at the close gate on VERBAL assertions (failure #2), a separate build.

## THE CORPUS-vs-TRAINING-DATA PROBLEM (the deep finding — design seeds, NOT yet built)
WHY "just prioritize the corpus" fails (mechanism, from watching the live failure): the corpus lives in the
model's BELIEFS (information it reasons ABOUT); training data lives in its REFLEXES (the substrate it reasons
WITH). Under task load, reflex beats belief — you cannot out-believe a reflex. Training data is not a dataset
the model consults; it is the SHAPE of the reflexes. So corpus and training are not competing data sources at
the same level — they are different LEVELS, and information cannot be raised to substrate-priority by asking.
Both Palantir (Ontology) and Ontinuity (harness/wrapping) did NOT solve this at the reasoning layer — they
ROUTED AROUND it: make the authoritative layer the ONLY PATH THROUGH to a real action, so the model's priors
can't reach the raw operation. That is the boundary-gate primitive; railway_set_var is its micro-instance.

FOUR PATHS to "add data sets reasoned from as if they were training data" (crossing the weights/context
priority wall):
- P1 FINE-TUNE / continued pretraining: literally put the corpus+discipline IN the weights -> compliance
  becomes REFLEX. (This is why Researcher-seated models "come out trained to follow the corpus" — a full
  harnessed session is lightweight in-context shaping; a real tune makes it permanent.) Solves PRIORITY;
  fails CURRENCY (frozen; doesn't absorb new corpus without re-tuning). AVAILABLE NOW.
- P2 FORCED RETRIEVAL (the harness, current best): don't make the model prioritize the corpus — make it
  mechanically unable to act without retrieving it (wrapped ops, CHECK-6 reproduce-from-record). Works where
  there's an OPERATION to wrap; fails for pure verbal reasoning (the "it's Cloudflare" fabrication had no op).
- P3 CORPUS-NATIVE CHECKER MODEL (the honest "enforcer"): a SMALL model fine-tuned EXCLUSIVELY on the corpus+
  discipline (no general capability) runs as the gate. The capable model reasons; the corpus-native model
  CHECKS. Its reflexes ARE the corpus (that's all it was trained on), so it flags the fabrication reflexively
  (it has no "Cloudflare is plausible" prior competing). Splits capability-box from compliance-reflex-box and
  COMPOSES them. Buildable now; attacks the exact failure wrapping can't reach.
- P4 THE ACTUAL LEAP (unsolved): promote CONTEXT into REFLEX-PRIORITY AT RUNTIME — hand a model a corpus and
  have it treat it as weights FOR THIS DOMAIN/SESSION, no fine-tune, no decay to "just information". Current
  models have a hard wall: weights=reflex/frozen/high-priority vs context=information/fluid/low-priority. The
  leap dissolves or bridges that wall at runtime. Nothing does this cleanly today.

OPERATOR'S "THINKING OUT LOUD" (the seeds to develop — captured verbatim intent):
- "A run-time reflex harness that holds per session — makes the info in it the reflexive priority as a LAYER;
  doesn't touch the model's training data. A priority layer as a FILTER — of ops maybe? Responses can only be
  ops that create expected outcomes based on corpus data."
- "Maybe the Ontinuity-trained model becomes that LAYER that filters between the user and the reasoning/working
  model."
=> This is a concrete architecture for P3+P4 combined: a corpus-native model as an INTERPOSED FILTER between
the user and the capable model, through which responses must pass — and the filter only permits responses that
resolve to corpus-grounded ops/expected-outcomes. The capable model keeps its full training-box for CAPABILITY;
the filter enforces corpus-priority WITHOUT modifying the capable model. "Grow the box by adding a box in
front." This is the most promising synthesis and the next thing to develop.

## THE COMPOSED DEFENSE (where the build is heading)
No single fix crosses the priority wall for everything. Compose three, each crossing it differently, covering
each other's gaps: (a) wrapped ops = mechanical compliance for OPERATIONS [BUILDING NOW, railway_set_var is #1];
(b) a corpus-native filter/checker model = reflex+judgment compliance for RESPONSES/ASSERTIONS [P3, next];
(c) optionally a discipline-fine-tuned base for general POSTURE [P1, later]. Defense-in-depth against the wall.

## STATE LEFT
main = (this commit). railway_set_var live+proven (22 ops); _railway_deploy header fixed; box config holds
Railway creds; box==repo. Per-project memory built+unit-proven (acceptance test still pending a certified
close, which needs the fixed Challenger to actually review). Engine on the per-project + MODEL_B=llama-3.3-70b code.

## NEXT
Two tracks, operator to choose ordering: (1) PROTOTYPE the corpus-native filter model (P3 / the operator's
interposed-layer idea) — the concrete path to the "leap" and the fix for failure #2 that wrapping can't reach;
(2) continue wrapping prescribed ops (extend railway_set_var's pattern to deploy etc.) and the close-gate
assertion enforcer. Held-but-not-lost: v1 packaging (PROVISIONING_RUNBOOK Phase 2), v2 aspirations (V2_ASPIRATIONS.md).

CROSS-REF: commits c16115a, eb475d1; box config.json (railway creds); V2_ASPIRATIONS.md; the compliance-failure
record 2026-09-13d; ONTINUITY_TOTAL_INDEX.md.
