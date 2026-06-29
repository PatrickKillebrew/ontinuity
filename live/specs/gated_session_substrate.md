# DESIGN NOTE — Leashing Everything Except the Design Chair

*Status: DESIGN (not built). Authored by control with operator (Patrick), 2026-06-29. CORRECTED 2026-06-29 after reading the actual engine loop and the existing shepherd/governor/mailbox source end-to-end. The first version of this note (commit d4a853b6) over-claimed that the engine is a general "configurable gated-session substrate" hosting three workloads including the coordinator; reading run_session_loop, shepherd.py, governor_*, and seat_mailbox.py disproved that. This version is grounded in those reads. Where this and the prior version disagree, this one wins.*

## HOW THIS NOTE WAS WRONG THE FIRST TIME (recorded so it is not repeated)

The prior version reasoned from a CONFIG-LAYER read (roles resolve via per-role env vars) and EXTRAPOLATED that the whole session loop was workload-general — that you could "pour a different question in and get different juice," including running the coordinator as a gated Tetraform session. That extrapolation was not grounded in the loop body; it was imagination filling a gap. Reading run_session_loop (app.py ~L2332-3072) showed the loop is WELDED to the Tetraform adversarial-research shape. The lesson is the project's core failure mode, demonstrated live while designing its cure: a config read is not a loop read; do not extrapolate architecture from an adjacent layer.

## THE PROBLEM, NARROWED TO ITS REAL TARGET

The workers are reliable: clean context, corpus-grounded, every action through the courier and logged, peer-reviewed under no-self-sign-off (observed: the Oracle-step-1 chain caught two real defects across author->review->correct->signoff bounces). The Researcher seat is leashed too — the close gate provably refused control's own ungrounded SESSION_END this session.

The single unleashed surface is the CONTROL DESIGN CONVERSATION: a Claude instance talking to the operator in open chat. Its failure mode is three moves, all sentences to the operator, none passing any chokepoint: (1) asserting a system-fact from memory instead of reading the corpus; (2) re-opening settled decisions; (3) inventing a detail to fill an ambiguity. This note is about that surface, not the workers.

## WHAT THE SOURCE ACTUALLY SAYS (grounded reads, this session)

### The engine loop (run_session_loop, app.py ~L2332-3072) is Tetraform-specific, not general.
Read end to end: Researcher (model_a) generates and emits a typed status tag every cycle; action tags (CODE_TEST/DB_QUERY/SEARCH_REQUEST) execute against the workspace and inject real ground-truth results, logged via record_execution. Challenger (model_b) is handed the objective, contract, execution log, and deterministic scans (F.3 fabrication, absence-claim, causal-claim) and reviews. Friction (model_c) is a computed drift signal (0-4), not a debater. Parietal adjudicates/navigates/resolves on specific tags. The close gate (the termination decision rule) checks every execution claim in the closing response + ledger against the EXECUTION LOG via check_execution_claims; FABRICATED/MISREPORTED claims REFUSE the close; 3 refusals trip a deadlock guard to the operator; a clean close runs Parietal DISTILL and writes knowtext. The roles are MODEL-swappable (config-driven), but the LOOP STRUCTURE is the adversarial-research workload. It is not a general substrate.

### The mailbox decides task order (seat_mailbox.py, live/box, mailbox_fetch ~L213-268).
Default task-claim is `ORDER BY created_at ASC LIMIT 1` — oldest-first, "FIFO fairness" — with an ATOMIC claim (BEGIN IMMEDIATE; UPDATE WHERE status='queued') so two workers never claim the same item, and expired-lease reclaim runs first. Workers do NOT choose or score tasks; the queue hands out the oldest unclaimed item to whoever calls you_there next. (Correlated/newest fetches drain newest-first; that is the exception, not the default.)

### The shepherd (shepherd.py, 105 lines) is the proven code-loop conductor.
A plain Python loop with API calls: /agent/start an objective -> watch the engine -> answer pre-session mailbox turns -> verify a write_receipt landed -> pace -> next. It has a deterministic failure watcher (consecutive_provider_failures). It does NOT run inside Tetraform; it CONDUCTS Tetraform sessions from outside. This is the coordinator's lineage.

### The governor (governor_routes.py 53 lines, governor_relay.py 55 lines) is a read-only pane.
SELECT-and-display only: counts observations/sessions/receipts/status buckets and renders them; the relay is "throwaway plumbing" that proxies READ-ONLY diag calls so a browser can show state same-origin. It has NO hands — it dispatches/nudges/routes NOTHING. It is the glass pane, not the conductor.

## THE CORRECTED ARCHITECTURE

### The Oracle = a Tetraform session. (Fits with zero engine changes.)
"Is this claim grounded in the corpus?" IS the contestable judgment Tetraform exists to gate: the Researcher emits DB_QUERY/SEARCH tags that already hit the real corpus and log results; the Challenger verifies citations against that log; the close gate refuses an answer whose citations the log cannot corroborate. The Oracle is run_session_loop with an Oracle objective and Oracle-congruent prompts. It is STRONGER than oracle.md's retrieve-and-answer seat: a session whose output is structurally gated against guessing, not a seat that merely promises not to guess.

### The Coordinator = a deterministic code loop in the shepherd's lineage. NOT Tetraform.
Coordination is mostly DETERMINISTIC, not contestable judgment: claim the oldest queued item, check the no-self-sign-off chain in code (signer distinct from author; a passing sign-off on record), fire the courier op to dispatch/route, put the next item in the queue. Running this through a Researcher->Challenger debate would be a courtroom deciding which line to stand in — it adds cycles, latency, and four model calls to a few boolean checks, which directly HURTS worker throughput. It also BREAKS cognitive role-congruence: pouring "decide the next dispatch" into a seat whose prompt says "you are the Researcher grounding a claim" is oblique cognition that invites hallucination. The coordinator is the shepherd's loop shape generalized to drain-and-route the mailbox. It JUST coordinates. It does NOT call the Oracle and does NOT run deep review — those are separate services; bolting them onto the coordinator was an earlier over-build, corrected here. When the coordinator hits a genuine judgment fork (rare), it makes ONE targeted, role-congruent API call — not a four-seat session.

### The Governor = the read-only pane over it (later, gains hands).
Today it displays state and drives nothing. The future glass pane that drives 10-100 workers is the governor GAINING a relay to send nudges/dispatch — a later build, gated on the seat registry. Current honest state: read-only monitor.

## WHAT THIS LEASHES, AND THE ONE THING IT DOES NOT

Leashed (each is a process whose actions pass the courier and/or the close gate): Workers (already), Researcher seat (already), the Coordinator (code loop; every courier action is gateable), the Oracle (Tetraform-gated grounding).

NOT leashed, by nature, and accepted: the DESIGN CHAIR (control-in-open-conversation). There is no server-side gate between a model and a sentence to the operator. It is disciplined by the ASSERTION RULE (below) and BACKSTOPPED by the operator. Honest ceiling: never zero-operator until it is not a conversation. The plan reduces how often the operator must be the backstop; it does not eliminate it.

## THE ASSERTION RULE (the design-chair discipline)

Before control states any load-bearing system-fact in a design conversation — a path, op, schema, settled decision, or "X is resolved/done/built" claim — it MUST show the read that grounds it IN THE SAME MESSAGE. Not "I recall," not "I believe." A claim without a shown read is a defect. A config read is not a loop read; do not extrapolate architecture from an adjacent layer (this note's own first-version failure is the cautionary case). This is the guessing-squelch principle turned on the one unleashed surface — codifying what the operator has enforced by hand so the corpus does more of the catching and the operator does less.

## OPEN VERIFICATION QUESTIONS (before any build)

1. INSTANTIABILITY / SINGLE-DRIVER. OPERATING_MANUAL.md L37: "exactly ONE driver owns the farm... Separate instances need separate mailboxes." Running an Oracle Tetraform session and (separately) the coordinator loop requires care about which engine instance hosts what. CONFIRM how many engine instances can be provisioned (MAIN, FARM exist; cost on Railway usage-based billing) and that each Tetraform session gets an isolated mailbox. NOTE: the coordinator is a code loop, not an engine session, so it does NOT consume a Tetraform driver slot — it can run as its own process and INVOKE Oracle sessions when needed.
2. ORACLE-AS-SESSION LATENCY. A Tetraform-gated answer takes multiple cycles (adversarial floor: cannot close in one cycle). oracle.md §3.2 wants an answer within one you_there window (<=60s) so a chat asker does not hang across a turn boundary. CONFIRM whether a gated grounding session can return in-window, or whether the Oracle needs an async contract (answer arrives later, recovered by corr_id) for heavy questions.

## BUILD ORDER (smallest real leverage first)

1. ASSERTION RULE into the CONTROL boot packet — highest-leverage, shippable now, codifies the rule the operator enforces by hand. (Corpus edit; no engine work.)
2. ORACLE as a Tetraform grounding session (Oracle objective + Oracle-congruent prompts on the existing loop). Resolve the latency question first. Mailbox plumbing (oracle.md step 1) already SHIPPED and stands.
3. COORDINATOR as a code loop in the shepherd's lineage: drain the FIFO mailbox, run the no-self-sign-off chain in code, fire courier ops, route the next item. It just coordinates. Generalizes shepherd.py; does not touch run_session_loop.
4. GOVERNOR gains hands (relay to dispatch/nudge) — later, gated on the seat registry. Until then it is the read-only pane.

## THE SPINE

The only mechanism that has ever changed control's behavior in the design chair is the operator catching it and forcing a corpus read. This design converts that into: leashed processes for everything that is a process (Oracle = Tetraform session; coordinator = shepherd-lineage code loop), plus a written assertion rule and operator backstop for the one thing that is a conversation. Tetraform is for contestable grounding (Oracle), not for procedural routing (coordinator) — using it for the latter is awkward, slow, and breaks role-congruence. Match the tool to the shape of the work.
