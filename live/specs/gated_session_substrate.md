# DESIGN NOTE — The Gated-Session Substrate as the Leash for Everything Except the Design Chair

*Status: DESIGN (not built). Authored by control with operator (Patrick), 2026-06-29. Grounded in live source read this session: app.py role-config resolution (get_effective_config / _vault_fallback, per-role <ROLE>_URL/<ROLE>_MODEL env vars), OPERATING_MANUAL.md L37 (single-driver rule), the no-self-poll invariant (OPERATING_RUBRIC/THE_PARADIGM HONEST CEILINGS), and the live-proven close gate (a Researcher session refused control's own ungrounded SESSION_END, 2026-06-29). Supersedes the retrieve-and-answer framing of the Oracle in live/specs/oracle.md §3.1/§3.4 for the answering architecture; the mailbox plumbing (oracle.md §3.2, step 1, SHIPPED) stands.*

## THE PROBLEM, NARROWED TO ITS REAL TARGET

The workers are reliable. Clean context, corpus-grounded, every action through the courier and logged to operations_ledger, peer-reviewed under no-self-sign-off. They catch their own mistakes (observed repeatedly: the Oracle-step-1 chain caught two real defects across multiple author->review->correct->signoff bounces). The Researcher seat is leashed too: the adversarial gates fire on its answers, and the close gate provably refused control's own ungrounded close this session.

So the Oracle's worker-aimed mechanism in oracle.md (the repeated-failure detector watching operations_ledger) is aimed at a target that is already handled. The single unleashed surface in the entire system is the CONTROL DESIGN CONVERSATION: a Claude instance talking to the operator in open chat. Its failure mode is not courier ops (those are gateable). It is three specific moves, all sentences to the operator, none of which pass through any chokepoint:
1. Asserting a settled system-fact from memory/priors instead of reading the corpus.
2. Re-opening or re-deciding something already settled.
3. Inventing a detail (a path, field, op, rule, or seat) to fill an ambiguity.

This note is about that surface. It is not about the workers.

## THE LOAD-BEARING REALIZATION (grounded in app.py)

The engine is a CONFIGURABLE GATED-SESSION SUBSTRATE, not a fixed Tetraform machine. Verified in app.py: each role (model_a, model_b, model_c, parietal) is resolved at runtime through get_effective_config(role) -> runtime_configs override -> _vault_fallback to per-role env vars (<ROLE>_URL, <ROLE>_MODEL, <ROLE>_API_KEY). The session loop references roles by key and pulls config at runtime. Therefore the gated-session machinery (the cycle loop, the adversarial review, the contract criteria, the Parietal close gate) is SEPARABLE from which models or roles fill it. The four Tetraform roles (Researcher/Challenger/Friction/Parietal) are the DEFAULT WORKLOAD poured into a GENERAL substrate.

This is the substrate-vs-workload distinction:
- SUBSTRATE: a live engine instance with a mailbox, courier hands, self-waking poll, and a CLOSE GATE that will not let a session close until its output survives adversarial grounding. A process, not a chat seat — so it has no provider turn budget and does not die between turns. This is what solves liveness.
- WORKLOAD: the specific question poured into the substrate. Tetraform-adversarial-grounding is the first workload; it is not the only one the substrate can run.

## SAME ORANGE, DIFFERENT JUICE — THREE WORKLOADS ON ONE SUBSTRATE

The substrate's adversarial close gate provably grounds output from the corpus (it caught control's own ungrounded close live). Point that same gate at different questions:

1. ORACLE = pour in "is this claim grounded in the corpus?" A grounding answer cannot be returned until it survives the adversarial gate. This is strictly stronger than the retrieve-and-answer Oracle in oracle.md: that one was a seat that PROMISED not to guess; this is a SESSION whose output is STRUCTURALLY GATED against guessing. The thing that makes the engine trustworthy (no claim survives without surviving challenge) is exactly the property wanted in the service whose whole job is refusing to guess.

2. COORDINATOR = pour in "what is the next action, and is it grounded?" A gated loop over the mailbox: claim coordination work, dispatch to workers, route reviews, commit signed-off work. Because it runs on the engine-instance substrate (a process), it polls via you_there WITHOUT a turn budget and stays alive — solving the coordinator-liveness problem that a chat seat cannot solve (you_there does not evade the chat turn budget; only a process achieves true liveness). And because every coordinator action goes through the courier, it is GATEABLE: it cannot act on an ungrounded decision because the gate sits in front of its courier call. A live, self-waking, leashed coordinator.

3. DEEP REVIEW = pour in "is this proposal sound enough to land?" The same adversarial gate aimed at a worker's staged bytes — deeper than a single peer's sign-off when the stakes warrant.

One substrate, one adversarial-gate mechanism, sequenced to different questions. The autonomous workflow is the substrate running different gated sessions back to back, each one's grounded output feeding the next.

## WHAT THIS LEASHES, AND THE ONE THING IT DOES NOT

Leashed by construction (all are processes whose actions pass the courier and/or the close gate):
- Workers (already).
- Researcher seat (already).
- The COORDINATOR (new: farm-substrate engine instance, live, courier-gated).
- The ORACLE (new: adversarial-gated grounding session).

NOT leashed, by nature, and accepted as such:
- The DESIGN CHAIR (control-in-open-conversation with the operator). There is no server-side gate between a model and a sentence to the operator. The design conversation is disciplined by the ASSERTION RULE (below) and BACKSTOPPED BY THE OPERATOR. This is the honest ceiling: it will never be zero-operator until the day it is not a conversation. The plan reduces how often the operator must be the backstop; it does not pretend to eliminate it.

## THE ASSERTION RULE (the design-chair discipline — the part the substrate cannot enforce)

Before control states any load-bearing system-fact in a design conversation — a path, an op, a schema, a settled decision, or a "X is resolved/done/built" claim — it MUST show the read that grounds it IN THE SAME MESSAGE. Not "I recall," not "I believe." A claim without a shown read is a defect, full stop. This is the guessing-squelch principle (precise rule, no gap for priors) turned on the one unleashed surface. It codifies what the operator has been enforcing by hand all along, so the corpus does more of the catching and the operator does less.

## OPEN VERIFICATION QUESTIONS (before any build)

1. INSTANTIABILITY / SINGLE-DRIVER. OPERATING_MANUAL.md L37: "exactly ONE driver owns the farm. A second poller collides... Separate instances need separate mailboxes." So running coordinator + Oracle + a Tetraform session concurrently requires SEPARATE ENGINE INSTANCES with separate mailboxes, not one box time-sliced. CONFIRM how many engine instances can be stood up (MAIN, FARM exist; can N more be provisioned cheaply on Railway usage-based billing?) and that each gets an isolated mailbox. The substrate must be instantiable as MANY, not one.
2. NON-TETRAFORM WORKLOAD ON THE LOOP. app.py confirms roles are config-driven. CONFIRM by reading the actual session-loop body (not just the config resolver) that a session can run with a DIFFERENT objective shape and role set than the 4-role Tetraform — i.e. that the loop, the contract criteria, and the close gate do not hard-assume Researcher/Challenger/Friction/Parietal. The config-resolver evidence is necessary but not sufficient; the loop body must be read.
3. ORACLE-AS-SESSION COST/LATENCY. A Tetraform-gated answer takes multiple cycles (the adversarial floor: cannot close in one cycle). The oracle.md §3.2 contract requires an answer within one you_there window (<=60s) so a chat asker does not hang across a turn boundary. CONFIRM whether a gated grounding session can return inside that window, or whether the Oracle-as-session needs an async contract (answer arrives later, recovered by corr_id) for heavy questions.

## BUILD ORDER (smallest real leverage first; supersedes oracle.md §5 steps 2-5 framing)

1. ASSERTION RULE into the CONTROL boot packet — highest-leverage single thing, shippable now, codifies the rule the operator enforces by hand. (Corpus edit; no engine work.)
2. Resolve the three verification questions above by READING (instances/billing; the session-loop body; gated-session latency). No build until these are answered.
3. ORACLE as an adversarial-gated grounding session on a dedicated engine instance (separate mailbox), replacing the retrieve-and-answer process in oracle.md §3.1. Mailbox plumbing (step 1) already shipped and stands.
4. COORDINATOR as a gated mailbox loop on its own engine instance — the leashed, self-waking coordinator. This is the Part-3 split, RESOLVED: the coordinator is a process on the substrate, not a chat tab the operator babysits.
5. Sequence them: coordinator decides next move -> Oracle grounds a needed fact -> review session gates a worker proposal -> each grounded output feeds the next. The autonomous pipeline is one repeated gated part.

## THE SPINE

The only mechanism that has ever changed control's behavior in the design chair is the operator catching it and forcing a corpus read. This whole design converts that from the operator's manual labor into: (a) leashed processes for everything that is a process, and (b) a written assertion rule plus operator backstop for the one thing that is a conversation. The farm was never "the testing rig." Its substrate IS what a live, gateable coordinator is made of, and its adversarial method IS what a guess-proof Oracle is made of.
