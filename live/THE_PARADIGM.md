# THE PARADIGM — how the Ontinuity team-of-seats system coheres (living document)

This is the top-level map. It sits above the rubric, the manuals, and the specs and says how they fit together and how the system stays coherent as it grows. READ THIS FIRST on any cold boot, then the role-specific doc. It is a LIVING document: it is re-derived whenever the system's shape changes, in the same commit as the change (currency discipline, below). If this doc and the live system disagree, that is a defect to fix, not a thing to work around.

## THE CORE MOVE — ground from the record, not from priors
Every seat (operator, control, workers) is a model that will, left alone, reason from its training priors / private context — what control has called "artificial imagination" — concretely: TRAINING-DATA priors (a model's general knowledge of how systems usually work) substituting for ONTINUITY-FACTS (how THIS system actually works, which lives only in the corpus, never in any model's weights). The load-bearing rule: use training data for CAPABILITY (code, reasoning, language); NEVER for Ontinuity-facts. Where priors and corpus disagree about this system, the corpus wins. Ambiguity is the front door for this substitution — a vague instruction forces the model to guess, and guessing reaches into priors; precise, semantically-tight instructions leave no gap for imagination to fill. Precision prevents; the gate only catches. That is the root failure of this project: a seat asserting a capability is absent, re-deciding settled design, or fabricating state, because it reasoned from memory instead of the record. The fix is structural, not a promise: every seat is REQUIRED to re-derive its operating reality from the corpus before acting, every cycle. The substrate (chat window vs API/engine instance) matters only because it changes how enforceable that requirement is — an API/engine seat re-orients from live state each cycle and cannot latch a private belief across turns; a long chat context can. The architecture is the fix; the substrate makes it enforceable.

## THE FOUR SEATS (see OPERATING_RUBRIC.md for full role rules)
- OPERATOR: direction, priorities, final authority + rollback. Should interact with the PLANNING seat only; should NOT have to route between worker conversations or nudge sleeping workers as routine. Routing is the system's job, not the operator's.
- CONTROL / PLANNING: the one seat the operator talks to. Holds tokens + box hands. Commits, dispatches, reviews, lands signed-off work, keeps the record current. A participant in the gated chain, never the unchecked deployer.
- WORKERS: peer frontier instances that build + review each other. Per-block scope, ground-from-corpus, park-don't-fabricate at tool budget.
- (emergent) the chain itself: task -> build -> peer review -> sign-off -> deploy -> fold. No single judgment ships unchecked.

## THE OPERATOR-LOAD PROBLEM (the current frontier)
Today the operator must nudge each chat worker after it sleeps and route between 3 conversations — impractical and the next thing to fix. Honest constraint: software cannot give a chat-window conversation a turn, so chat workers REQUIRE operator nudges. The only real fix is seats that poll/wake themselves = API/engine-instance seats (the farm already is one). The blocker is cost: all-Opus-4.8-API for every seat-cycle is enterprise-priced, impractical for a solo operator.
RESOLUTION (model tiering, so self-hosting is affordable):
- Frontier (Opus) where judgment is load-bearing: control/planning, and the REVIEW/sign-off role. Quality here is the reliability boundary; do not cheap it out.
- Cheaper model for high-volume, low-judgment cycles: first-draft build, and especially the poll/heartbeat/shepherd loops. Opus reviews what a cheaper model drafts. (Composes with the Projenius small-model-carrying-project-knowledge direction.)
- Net: "route everything through Ontinuity" does NOT mean "everything is Opus API." It means everything runs through the gated, documented system; model tier is chosen per role by how much judgment that role needs.

## SELF-HOSTING CONTROL (the direction, staged — not a flip)
The aim: route the control seat itself through Ontinuity, so the seat the operator interacts with grounds from the corpus every cycle instead of from a private chat context. This is the permanent fix for the priors-leak. STAGE it; do not flip everything at once:
1. Prove the API-worker path on the cheapest viable tier (the farm is the proving ground).
2. Make boot-from-corpus structural (the bootstrap gate, esp. CHECK 6 MECHANICS — a seat must reproduce the operating invariants from the record before acting).
3. Migrate control onto the API/engine substrate once the pattern is proven.
The bootstrap gate is the CENTERPIECE, more than the migration: grounding + the two-party gate are what make any seat reliable; the substrate just makes them enforceable.

## CURRENCY DISCIPLINE (what keeps a growing system coherent)
The manual, the rubric, the punch list work because they are updated WHEN THE THING CHANGES, IN THE SAME COMMIT. The paradigm gets the same discipline: when the system's shape changes (a role, the chain, the substrate, the tiering), THIS doc is updated in the same commit as the change. A drifted paradigm is the same defect class as a drifted manual allowlist — and the bootstrap gate's CHECK 6 should verify a seat can reproduce THIS paradigm's invariants, not just the manual's. Make "paradigm current" a gate item alongside "manual current."

## HONEST CEILINGS (carried up from the rubric; do not paper over)
- Chat seats sleep between turns; only an operator nudge wakes them. The shepherd detects idle-with-work and ALERTS; it cannot re-enter a chat window. Walk-away needs API/engine seats.
- Until per-identity keys are fully live, seat identity is self-asserted (trusted-not-authenticated); the shared diag key is the known soft spot.
- Grounding-from-record REDUCES but does not ELIMINATE model imagination; the gate (no unchecked judge) is what catches what slips through. Architecture over trust.
