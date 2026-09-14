# ONTINUITY — V2 ASPIRATIONS (captured for future development, not v1 scope)
*Operator's forward-looking design intent, captured 2026-09-13 so it is not lost. These are DELIBERATELY
DEFERRED past v1 (v1 = the packaged per-operator instance with per-project memory + the design front door).
Documented here per operator: "Document these future aspirations in a way that they don't get lost. Then
we'll get back to what we were already doing." Each is grounded in the discussion that produced it.*

## THE FRAME THAT ORGANIZES ALL OF V2 (settled this session)
Ontinuity has TWO front doors + ONE cross-cutting capability (NOT three front doors):
- INTAKE door: an outside person with a problem fills a questionnaire → a structured matter.
- DESIGN/BUILD door: the operator works a matter in the chat window (like this conversation) → accumulating
  knowledge with memory continuity. This is ~90% of a user's day and is v1's core.
- VERIFICATION (the adversarial engine): NOT a third door — a GATE a session ROUTES A SPECIFIC LOAD-BEARING
  OUTPUT THROUGH when fabrication-freeness matters, then returns the certified artifact into the design
  conversation. Watched (optionally) through the Governor cockpit. "Verification is a gate the design session
  calls, not a front door." (Operator confirmed.)
WHEN TO INVOKE THE ADVERSARIAL GATE (the resolved answer): route an output through it when a fabricated claim
in it would cause real harm downstream — software to build, a floor-level/safety-critical procedure, a client
deliverable, a compliance number. Leave drafts/brainstorms/outlines/lists in the design conversation (no gate).
The EXECUTION LOG is the mechanism: it makes "I ran/tested/measured/verified X" un-fakeable — so the gate is
most valuable exactly where the deliverable contains claims of that form. It is a FABRICATION TRIPWIRE (the
operator's original intent — "the adversarial review was meant to be exactly that trip wire").

## V2-A — USER-UPLOADED REFERENCE LIBRARIES (the grounding substrate the gate polls)
THE PROBLEM IT SOLVES: today the adversarial gate verifies INTERNAL consistency (execution log + frozen
contract). To verify a claim against EXTERNAL ground truth (e.g. "OSHA 1910.269(l) requires X"), the gate needs
an authoritative corpus to poll. AIP gets this from a pre-built Ontology; Ontinuity's answer is lighter and
bottom-up: the USER UPLOADS their own ground truth (operator's idea: "make that something the user can upload
themselves — keeps us from having to predict/preload what a user might want").
MECHANISM (additive, reuses the corpus you already have): an uploaded reference library = ANOTHER corpus, but
SHARED/READ-ONLY reference (vs a matter's accumulating isolated corpus). The existing VERIFY_CITATION gate
polls it — a claim gets grounded in, or flagged against, the library. This is the two-tier retrieval already
designed: FACTS isolated per matter; shared REFERENCE (the library) readable across matters (the same
methodology-vs-facts split as the four-stage pipeline's two-axis isolation rule).
WHY IT MATTERS (the gravity): a generic AI drafting a safety procedure reasons from (possibly stale/wrong/
hallucinated) training data. Ontinuity drafting one VERIFIED AGAINST A CITED library produces something
AUDITABLE AND DEFENSIBLE — every safety-critical step cites the regulation it rests on. For a compliance-driven
role, defensible-and-cited IS the job.

## V2-B — AUTO-FETCH FROM AUTHORITATIVE SOURCES (the compounding "magic" version)
Given a matter's topic ("confined-space entry training at Plant 34"), the system FETCHES the exact relevant
public regulations itself (OSHA 1910.146 via eCFR API / OSHA's public standards — public + structured +
retrievable) and populates a reference library automatically, then DRAWS THE TRAINING CONTENT *FROM* the actual
regulation with citations back to the source. Operator: "trainings could be drawn from the exact regulations
that Cornel needs to train people about." This is the killer version — not "AI wrote a training" but "AI built a
training grounded in and citing the live federal regulation, verified before it shipped."
BUILD PATH (clean, additive, no new architecture): (1) upload a reference library → shared read-only corpus;
(2) VERIFY_CITATION gate polls it; (3) later: auto-fetch relevant public regs into a library by matter topic;
(4) generate content FROM the library with source citations. SEQUENCING: user-upload ships first (simplest, no
external deps, ~80% the existing corpus mechanism); auto-fetch is the v2 magic on top.

## V2-C — INTAKE AS A FRONT DOOR FOR MATTERS (closing the loop between the doors)
Operator's "thinking out loud": an employee/manager fills out an intake for an incident/compliance item, and it
BECOMES A MATTER in the operator's punch list. Incidents and compliance updates enter through the INTAKE door
(structured, filled by whoever holds the info), land as MATTERS the operator (e.g. Cornel) then works through
the design door with full memory + verification. This unifies the architecture: INTAKE creates matters →
DESIGN works them → VERIFICATION grounds their load-bearing outputs against reference libraries. Incident
reports / compliance records created or updated through the intake door, surfaced to the operator via the punch
list. (Grounded in: the existing intake pipeline + seed_tenant/new_project + the punch-list mechanism — the
pieces exist; wiring them into this flow is the v2 work.)

## V2-D — ADVERSARIAL SESSION UI / GOVERNOR AS THE WATCH-WINDOW
The design door is the chat window. The adversarial engine needs no separate front-door UI — it needs a TRIGGER
from within a session ("verify this before it ships") and a PLACE TO WATCH it run: the Governor cockpit
(observability into the gates firing). A NAMING MODAL for a new matter belongs at the DESIGN door (a memory
concern — the user names their own matter, with a confirm modal), NOT at the adversarial layer (which inherits
the matter scope from whatever invoked it). (Operator's modal idea, placed correctly: naming = design/memory;
the adversarial gate doesn't create projects, it verifies outputs within one.)

## THE MARKET THESIS (why this is worth building — operator's conviction + the analysis)
Ontinuity's differentiator vs generic AI memory: it stores what was DONE, CHALLENGED, and GROUNDED — with
enough cross-referenced provenance that the record is AUDITABLE and SELF-CORRECTING, not just retrievable (a
stored fact can be wrong; a reconstructable, verified record lets you CATCH the wrong fact — demonstrated live
this session when the corpus reconstructed that a manual claim about seed_tenant was false). vs Palantir AIP:
AIP grounds against a pre-engineered Ontology (enterprise-scale, data-engineering prerequisite); Ontinuity
grounds against an accumulating adversarial-verified RECORD + user-brought reference libraries (useful from the
first session, models nothing up front, no data-engineering prerequisite). Different market: bottom-up,
single-operator, compliance-driven. THE COMPLIANCE ANGLE is the wedge (operator: "the impact on the compliance
world could be game changing"): a fleet safety manager's job IS liability + defensibility across many sites;
"here's the training/procedure, verified fabrication-free, with the OSHA citation for every safety-critical
step" is not a nice-to-have — it is the whole value. The flywheel: each verified matter's established results
become reference for the next (Plant 51 starts from Plant 34's verified template + the same reg library), so
the knowledge base AND the reference libraries compound over time.


## V2-E — THE REFLEX LAYER: a small Ontinuity-trained model that makes corpus-conformance a reflex (captured 2026-09-14, deliberately shelved)
*Operator: "This has been a fun exploration of this possibility, let's store this away as a future aspiration. There's a lot to think
about and learn here and it's only going to take away from finishing packaging Ontinuity." Full reasoning + research trail:
live/conversations/2026-09-14b_reflex-layer-research-shelved-to-v2.md. Design seeds originate in record 2026-09-14a.*

THE PROBLEM IT SOLVES (the priority wall, from records 2026-09-13d / 2026-09-14a): corpus facts live in the model's BELIEFS (information it
reasons about); training data lives in its REFLEXES (the substrate it reasons with); under task load reflex beats belief. Wrapped ops
(railway_set_var, the first) kill this for OPERATIONS by making the raw call unreachable. Nothing yet kills it for the VERBAL space
where fabrication lives ("Path BLOCKED, Cloudflare egress" — 2026-09-13).

THE OPERATOR'S CONSTRAINTS (rulings this session, verbatim):
- "No facts in weights is the key to the trained model success." The small model carries BEHAVIOR/discipline only. Corpus facts stay in
  context (or a cartridge), never in any weights. Currency is therefore a cache refresh, not a retune.
- The model's sole job: "make sure all functions or capabilities of Ontinuity are performed as written or documented." Conformance, not truth.
- It must act MID-SESSION at the reflex level, "impactful in the way wrapped ops are" — eliminating the false path, not reporting on it.
  A checker that runs at close, or on the corpus write, is "already too late" — REJECTED. A response filter after generation is also too late
  (the reflex fired when the seat CHOSE urllib, before any token was written).
- Intake door: checking against OSHA regs happens WHILE the training is being built; the user gets a RECEIPT at the end of what was caught.
  The receipt is a byproduct of the bounce log; the mechanism is the intervention during build.
- One model, one job. Cross-matter retrieval is NOT this model's job (facts-in-weights + a second label space) — that is a retriever's job, or
  one cartridge per matter (composable at inference, per the Stanford result).

THE DESIGN THAT SURVIVED (the reflex-level, token-level version):
- PROXY-TUNING (Liu et al., "Tuning Language Models by Proxy", COLM 2024, arXiv 2401.08565; code github.com/alisawuffles/proxy-tuning).
  Tune a SMALL model (expert M+); keep its untuned twin (anti-expert M-). At every decoding step add (logits(M+) - logits(M-)) to the
  FROZEN capable model's logits. Base weights never touched; only its output distribution is read. The anti-expert cancels the small model's
  generic tendencies so only the DIFFERENCE TUNING MADE is applied. This IS the operator's sentence from 2026-09-14a: "a run-time reflex
  harness that holds per session — makes the info in it the reflexive priority as a LAYER; doesn't touch the model's training data... the
  Ontinuity-trained model becomes that layer between the user and the reasoning/working model." 09-13 replayed: at the token where the seat
  would begin `import urllib`, the expert (tuned on "prescribed method = the op call") shifts probability to the op; the false path loses at the
  sampler. Same shape as wrapped ops: the false path is not selected, rather than blocked after selection.
- THE THREE-BOX COMPOSITION, all at generation time: frozen capable model (capability) + cartridge per matter (corpus FACTS in the KV cache;
  Eyuboglu et al., "Cartridges", ICLR 2026, arXiv 2506.06266; github HazyResearch/cartridges; scale-up arXiv 2606.04557) + proxy expert
  (Ontinuity BEHAVIOR in small weights). No facts in any weights.
- HARD CONSTRAINTS (stated plainly): (1) needs the base model's FULL-VOCABULARY logits every step -> hosted Cerebras/Novita 70B does not
  expose that; a chat seat never will; the engine seats would move to an open-weight capable model served by us (vLLM on a rented GPU). This
  is the real decision. (2) Expert and base must share a tokenizer: Llama-3.1-8B expert steering Llama-3.3-70B (already MODEL_B) is the natural
  first pairing. (3) It STEERS, it does not GATE — probabilistic, a strength knob, not a wall. Wrapped ops remain the hard gate for actions.

THE RESEARCH TRAIL (the operator's problem has a name in the literature: CONTEXT-MEMORY CONFLICT / CONTEXT FAITHFULNESS):
- Against fine-tuning FACTS in: Gekhman et al. "Does Fine-Tuning LLMs on New Knowledge Encourage Hallucinations?" EMNLP 2024, arXiv 2405.05904
  (new-knowledge examples learned slower, then linearly raise hallucination); Goyal et al. "Context-Parametric Inversion" arXiv 2410.10796
  (instruction finetuning may not improve context reliance). => behavior in weights, never facts. SEAL authors' guidance matches: facts in
  external memory, behavior-shaping knowledge in weights.
- Context into weights at runtime (the P4 "leap" — no longer unsolved in principle): TTT-E2E arXiv 2512.23675 (NVIDIA/Stanford); In-Place TTT
  arXiv 2604.06169 (drop-in fast weights for existing LLMs); TTCD arXiv 2608.01672; SEAL arXiv 2506.10943 (NeurIPS 2025; catastrophic
  forgetting still open).
- Decode-time, ZERO-TRAINING knobs for exactly this dial: Context-Aware Decoding (Shi et al. 2024 — contrast with/without context); CK-PLUG
  arXiv 2503.15888 (entropy-shift conflict detection + one tuning parameter; on Llama3-8B moved memory recall ~10%-72% vs 42% baseline).
  Caveat from the conflict-aware line (arXiv 2606.10298): context-aware methods assume context is always right — in Ontinuity that assumption
  is TRUE BY CONSTRUCTION for system-facts (the corpus wins), so this is the easy case for these methods.
- Proxy models applied to THIS problem already: Wang et al. "Continuously Steering LLMs Sensitivity to Contextual Knowledge with Proxy Models",
  EMNLP 2025, arXiv 2508.19720.
- Activation steering (a per-session vector in the residual stream = literally "a runtime reflex harness that holds per session"; needs open
  weights we serve): ContextFocus arXiv 2601.04131; SHIFT arXiv 2606.27786; SAE-based knowledge-selection steering (Zhao et al. NAACL 2025).
  Also Context-DPO, CARE arXiv 2508.15253, and the knowledge-conflicts survey (Xu et al. 2024) for the map of the field.

THE EXPERIMENT LADDER (evidence at each rung before the next — the go/no-go is nearly free):
1. Base model + the eval contexts, CAD or CK-PLUG turned up. Zero training. Does the urllib->op choice move at all? If not, no expert will move it.
2. Proxy-tuned expert on behavior pairs. Does it move further, and hold under load?
3. Activation steering (rung 2 already committed us to open weights we serve).
4. Cartridges for corpus facts.
Three-arm benchmark for any rung: prompted 70B Challenger vs capable-model self-check vs the tuned/steered arm, same eval set. If the prompted
baseline wins, the gate is the product, not the tune.

THE ASSET (why this is worth anyone's time): ~27 conversation records + the agent_queue folds (12 LEARNED blocks, ~92 correction lines) + the
private the-package/mini_corpus.md reversals are LABELED examples of a seated model drifting to priors with the corpus ground truth next to it.
Nobody publishing on TTT/Cartridges/proxy-tuning has a live-failure dataset like that. A result "steered arm catches X% vs Y% self-check vs Z%
prompted Challenger" is a real contribution and the Empirical Session Record method applied to itself.

THE EXTRACTION (deferred with the rest; hand-off target = GPT-5.6 Sol on the operator's Max 5x account — it knows Ontinuity and has used the
hands): EVAL items `(assertion, excerpts_shown, label: grounded|ungrounded|unverifiable, ref = file@commit+lines)`; TRAINING pairs for the
expert `(context the seat had, the CONFORMANT response)` — the records hold both halves of every failure (the wrong turn + the correction).
Positives (assertions that DID trace to the record) are half the set. Two independent labelers (Sol + Claude), disagreements to the operator =
author≠signer applied to the training data; inter-labeler disagreement rate = the noise floor the model must beat.

HARDWARE NOTE: the operator's M4 iPad Pro (16 GB unified) cannot be the mixing point (full-vocab logits per token across a network) and cannot
train; it CAN host an on-device demo (Llama-3.1-8B quantized base + 1-3B expert/anti-expert in one process) once the mechanism is proven on a
rented Linux GPU. Toolchain on iPadOS is thin (custom decoding loop = llama.cpp bindings you build).

STATUS: SHELVED. Not v1. Resume only after v1 packaging (PROVISIONING_RUNBOOK Phase 2) ships.
