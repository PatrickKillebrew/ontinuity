# ONTINUITY — THE CONTINUITY MECHANISM (Mode B design front-door)
## Anatomy + Physiology of automatic capture-and-resume
*Depth-arm off ONTINUITY_MASTER_SYSTEM_MAP.md §21. Traces the COMPLETE CIRCUIT that lets a cold model pick
up exactly where the last left off — the part that must fire AUTOMATICALLY and MECHANICALLY, with the user
never doing technical work by hand. Scope: Mode B (the operator↔seat design/build loop). Mode A (intake→
pipeline) is a separate arm. Built from deep reads of THE_PARADIGM, OPERATING_RUBRIC, OPERATING_MANUAL
(open/close/currency), verified_bootstrap_gate.md, close_ritual_gate.md, PROJECT_CORPUS_RUBRIC.md.
Every part marked: [LIVE] fires today · [INSTRUCTED] documented but skippable (runs on seat discipline) ·
[GATE-SPEC] the mechanical enforcer designed, not yet live · [GAP] unbuilt.*

═══════════════════════════════════════════════════════════════════
## 0. THE ONE-LINE PHYSIOLOGY
A cold model boots → is FORCED to ground in the record before acting → works → and at close is FORCED to
re-distill the record so the NEXT cold model can boot and continue. Continuity is not memory in a model;
it is a DISCIPLINE MECHANICALLY ENFORCED at two gates (open + close) with the corpus as the durable
substrate between them. "Recall is not a substitute for retrieval" — the model's weights never carry
Ontinuity-facts; the corpus does. The magic is that the boot and close do this FOR the user.

═══════════════════════════════════════════════════════════════════
## 1. THE ANATOMY — the parts of the circuit (what stores/carries continuity)

### A. THE SUBSTRATE (where continuity lives between sessions) — all [LIVE]
- **live/agent_queue.md** — the append-only NARRATIVE LEDGER. Chronological folds (BUILT/LEARNED/REVERSED),
  never deleted. THE now-state marker is the latest `## CURRENT-STATE TOUCH POINT` fold + each fold's `NEXT`.
- **live/PUNCH_LIST.md** — the RESOLVED VIEW distilled from the queue: DONE/IN-PROGRESS/OPEN, deduplicated,
  each closed item citing its commit/receipt. The queue is the raw archive; the punch list is the digest.
- **live/conversations/YYYY-MM-DD_<topic>.md** — the OPERATOR-LAYER record: rulings verbatim, fabrications
  caught, decisions + their reasoning. The ONLY place the "why" lives (receipts capture the work, sessions
  capture the seat, neither captures the operator layer). Per CONVENTION.md: redact, declare form, honest
  lineage, cross-reference shas/receipts.
- **The durable docs** — THE_PARADIGM (how it all coheres), OPERATING_RUBRIC (role rules), OPERATING_MANUAL
  (how to drive it), the specs. These carry OPERATING MECHANICS across seats.
- **Knowtext (knowtext_<project>_<branch>.txt + knowtext_versions DB rows)** — the DISTILLED 7-field
  continuity doc, per project/branch. The compression of "what a new session needs to CONTINUE."
- **The relational DB** (sessions, session_transcripts, established_results/erl_*.txt, challenge_events...)
  — the structured evidence a session produced.
THE JOIN: every record keys on the SAME shas/receipts, so a stranger walks conversation→decision→commit→
receipt in either direction. This join is what makes the substrate a coherent memory rather than loose files.

### B. THE GATES (the mechanical enforcers) 
- **OPEN gate = the Verified Bootstrap Gate** [GATE-SPEC; a 19-op-reconciled runnable is LIVE on the box,
  boots oriented:true — see §3]. Six ordered checks: MANUAL / QUEUE / CORPUS / HANDS / ENGINE / MECHANICS.
  Comply-or-fail: ORIENTED (may act) or NOT ORIENTED (hard stop). Turns the open ritual from INSTRUCTED
  (skippable — a seat DID skip it, cost a morning, June 10) into VERIFIED.
- **CLOSE gate = the Close-Ritual Enforcement Gate** [GATE-SPEC, built, not deployed]. Seven+ checks
  mirroring the manual's 8-item close ritual: PUNCH-LIST / CONVERSATION / QUEUE-FOLD / MANUAL-CURRENCY /
  CONTRACT-DOC / SECRETS / STATE-CLEAN (+ handoff). Reports ALL gaps at once. Turns the close ritual from
  INSTRUCTED (runs on habit that dies at a conversation boundary — hygiene lagged, June 12) into VERIFIED.

### C. THE HEARTBEAT — CURRENCY DISCIPLINE [INSTRUCTED, load-bearing]
"When the thing changes, its doc changes IN THE SAME COMMIT." The manual, rubric, paradigm, punch list are
only load-bearing if CURRENT. A drifted doc decoheres the next seat exactly like a degrading memory, just
slower — "and then the next seat reads stale instructions and repeats a retired failure." This is what the
operator means by "update everything after significant work": currency is not a chore, it is the mechanism
that keeps the substrate TRUE so the next boot grounds on reality, not a stale snapshot.

═══════════════════════════════════════════════════════════════════
## 2. THE PHYSIOLOGY — the circuit in execution order

### PHASE 1 — COLD OPEN (a fresh seat with no prior context picks up)  [INSTRUCTED + GATE floor]
The OPEN RITUAL, in order (OPERATING_MANUAL "COLD-BOOT ONBOARDING"):
1. Read the latest CURRENT-STATE TOUCH POINT fold in agent_queue.md — it IS the now-state. (First, in full.)
2. Read this manual. 3. Read PUNCH_LIST.md. 4. Read recent queue folds newest-backward.
   — ALL from the LIVE repo via authed api.github.com (NOT /mnt/project snapshots [stale], NOT raw CDN [stale cache]).
5. Find credentials (check, don't assume): GitHub token, mailbox key, diag key. Absent ≠ capability-absent.
6. Know your hands (do not re-derive or wrongly declare absent): read=authed api.github.com; commit=YOU
   commit via contents/trees API with trailers; box/engine=diag relay+courier; deploy=you deploy routine work.
7. THEN act — via the open ritual on the specific task.
THE MECHANICAL FLOOR UNDER IT (the bootstrap gate): after admission the seat runs the gate; it PROVES
manual/latest-fold-queue/corpus/hands/engine + reproduces the operating MECHANICS (CHECK 6), ratified
against the manual — NOT self-asserted. oriented:true earns the right to act; the human-judgment reads
(which fold, is it the right next action) complete the reasoning the gate deliberately does not interpret.
→ THE OUTPUT OF A GOOD OPEN: the seat now holds current state + next action + working hands, grounded in
the record, having proven it — not recalled it. This is how Sept-3's cold GPT inherited the office.
KEY PRINCIPLE: recall ≠ retrieval. A long session degrades context; the corpus does not. Orient first, reason second.

### PHASE 2 — RUN (work accumulates; significant work triggers interim currency)  [LIVE + INSTRUCTED]
- The seat works the single next action. In Mode B this is the design/build dialogue (what you+the seat do).
- Claims ground in the record (the core move); the adversarial gates (Mode B via mailbox-seat, or the
  reasoning discipline) catch priors-over-corpus substitution.
- INTERIM CURRENCY (the "take time to update after significant work" discipline): when an operation changes
  or a significant block completes BEFORE the formal close, the affected doc updates in the SAME commit.
  This is why hygiene can't wait for close alone — a long session that changes the write path and doesn't
  update the manual has already planted the silent-decoherence defect. Currency is continuous, not just terminal.
- Accumulating substrate: commits (with join trailers), any session rows, decisions worth a conversation record.

### PHASE 3 — CLOSE (re-distill the record so the next cold model can continue)  [INSTRUCTED + GATE-SPEC]
The CLOSE RITUAL, 8 items (OPERATING_MANUAL "CONTROL-SEAT CLOSE RITUAL — WORK THE CHECKLIST, do not freestyle"):
1. PUNCH_LIST reconcile — DONE/IN-PROGRESS/OPEN vs what shipped, cite closing commit/receipt.
2. CONVERSATION RECORD — capture the dialogue/rulings per CONVENTION (only the control seat can; a worker
   backfilling from commits cannot see the window).
3. QUEUE FOLD — the narrative fold (BUILT/LEARNED/REVERSED) + a CURRENT-STATE TOUCH POINT + a single NEXT.
4. MANUAL CURRENCY — did any operation change? the manual must already reflect it (close is the backstop).
4b. CONTRACT-DOC CURRENCY — did the worker contract change? then WORKER_MANUAL + the boot PACKET + paradigm/
    rubric must all reflect it THIS close (three-states-of-done: op exists → documented → in the packet that runs).
5. PROVENANCE — deploys/rulings/box-source committed and in version control (commit_self if box changed).
6. SECRETS SWEEP — grep every committed file for tokens/keys/IPs; a transient-arg token must never land.
7. STATE LEFT CLEAN — engine idle, no failed deploy, no orphaned mailbox claim.
8. NEXT-SEAT HANDOFF — the top of the queue states the single next action, so the next open lands on a clear target.
ALL records key on the SAME shas/receipts (the join). Running them as ONE ritual is what stops any one
lapsing silently (conversation logging lapsed June 7 precisely because it was NOT part of a ritual).
DISTILLATION: Knowtext's DELTA (write only what CHANGED; "if restating, delete") is the compression step —
in the engine this is Projenius DISTILL; by hand it's the fold + Knowtext update. Test of a good close:
a new instance reading the record continues WITHOUT the transcript.
THE MECHANICAL FLOOR (close-ritual gate): verifies each item happened THIS session (takes session_start so
"did X happen this session" is decidable), reports ALL gaps at once. Comply-or-fail: CLOSE NOT COMPLETE
is a hard stop — the session isn't done until the record is re-distilled.

### PHASE 4 — NEXT COLD OPEN (the loop closes)
The next fresh seat runs Phase 1. Because Phase 3 left: a current touch-point fold (now-state), a single
NEXT (its target), a reconciled punch list, a conversation record (the why), current docs (mechanics), and
an updated Knowtext (distilled continuation) — the new seat GROUNDS on reality and continues, no
reconstruction, no user re-explaining. THE CIRCUIT IS CLOSED. This is "pick up where the last left off,"
mechanically, on any model, any vendor (proven Sept-3).

═══════════════════════════════════════════════════════════════════
## 3. BUILT vs GAP — what fires automatically today vs needs a human (the bring-into-reality target)

| Circuit part | Status | Note |
|---|---|---|
| The substrate (queue/punch/conversations/docs/Knowtext/DB) | [LIVE] | exists, populated (357 knowtext_versions, 328 sessions) |
| Open RITUAL (the reads) | [INSTRUCTED] | documented; a seat can skip it (and did) |
| Open GATE (bootstrap gate, 6 checks) | [LIVE, reconciled] | the 19-op runnable boots oriented:true this session; the B1-admission wrapper is discarded, the CHECK mechanism kept |
| Close RITUAL (8 items) | [INSTRUCTED] | documented; runs on seat habit that dies at a conversation boundary |
| Close GATE (close-ritual gate) | [GATE-SPEC, GAP] | built as a spec, NOT deployed — the enforcement that makes close automatic |
| Currency discipline (heartbeat) | [INSTRUCTED] | the manual/paradigm say same-commit; not mechanically forced except where a gate constant reads it |
| Knowtext DISTILL at close (Projenius) | [GAP on live engine] | Projenius unconfigured on the live engine → DISTILL no-ops → knowtext_versions written by the extraction path, not auto-distilled per close; the FILE Knowtext works, the auto-per-close-distill needs Projenius |
| The JOIN (shas/receipts cross-ref) | [LIVE, by discipline] | records key together when the ritual is followed; not mechanically forced |

### THE HONEST CORE FINDING for "bring the simple memory into reality":
The SUBSTRATE and the OPEN gate are essentially live. The two things that make continuity AUTOMATIC rather
than DISCIPLINE-DEPENDENT are:
1. **The CLOSE gate** (close_ritual_gate.md) — deploy it so a session cannot count as closed until the
   record is re-distilled. This is what removes the user/seat from having to "remember" to fold. [the build]
2. **Projenius DISTILL configured on the live engine** — so the Knowtext delta is WRITTEN automatically at
   each close, not by a hand-run extraction. [config + the persist path]
With those two, the circuit fires end-to-end with no human doing the ritual by hand — which IS the product.
Everything else (substrate, open gate, currency rules) already exists; it's currently held together by seat
DISCIPLINE (the exact thing that fails — this whole session is a specimen of a seat skipping the open ritual
until pushed). The gates are what convert discipline into mechanism. THAT is the magic to finish.

═══════════════════════════════════════════════════════════════════
## 4. THE GENERALIZED FORM (PROJECT_CORPUS_RUBRIC) — the same circuit, any project
PROJECT_CORPUS_RUBRIC.md generalizes this circuit to ANY project corpus (not just Ontinuity's own):
- OPEN: read CURRENT_STATE → PROBLEM_DEFINITION → search the fold → follow refs. ("recall is not retrieval.")
- CLOSE: reconcile punch list → capture the reasoning arc → write the fold → update CURRENT_STATE.
- Same substrate shape (CURRENT_STATE=touch-point, mini_corpus=queue fold with BUILT/LEARNED/REVERSED,
  PROBLEM_DEFINITION=ground truth, LOCKED DECISIONS fenced).
This is the SPEC of the discipline the engine must AUTOMATE. It is NOT a manual-labor product (the failure
this session corrected) — it is the blueprint for what the mechanical circuit does FOR the user.

═══════════════════════════════════════════════════════════════════
## 5. WHY THIS IS THE PRODUCT (the synthesis)
Continuity = the corpus (substrate) + two gates (open forces grounding, close forces re-distillation) +
the currency heartbeat (keeps the substrate true). When all three run mechanically, a user just TALKS: the
system boots grounded, works, and re-distills at close, so the next cold model continues perfectly — the
user never folds, never commits, never reconciles a ledger. The Sept-3 succession proved the circuit CAN
carry continuity across a cold vendor boundary. The remaining work to make it a PRODUCT is to make the two
gates + Projenius distill fire automatically, so continuity stops depending on seat discipline (which fails)
and becomes a property of the harness (which doesn't). That conversion — discipline → mechanism — is the
whole game, and it is exactly the boundary-gate primitive (§18): gate and prove, don't trust and monitor.

═══════════════════════════════════════════════════════════════════
## 6. THOROUGH-READ ADDENDUM — parts of the mechanism the first pass skipped
(There is no fluff in the corpus; each of these is load-bearing for packaging.)

### 6.1 THE TWO FRICTION POINTS (Knowtext paper §5) — THIS IS THE PACKAGING TARGET, NAMED
Knowtext is "fully functional without automation — the automation makes it more efficient, not more capable."
Its two manual frictions ARE what the product must automate:
- **DISTILLATION FRICTION** — someone must read the session and extract the schema (cognitive overhead at
  every session end). → automate = Projenius DISTILL fires at close.
- **INJECTION FRICTION** — even once the schema exists, it must be manually loaded into each new
  conversation, "a step easy to skip when starting quickly." → automate = the boot auto-loads the Knowtext.
Both are "solvable through automation, described in the Tetraform and Synthesis architecture." → THE PRODUCT
= automating these two so the user never distills or injects by hand. This is the same conclusion as §3
(deploy the close gate + configure Projenius), now grounded in Knowtext's own stated edges. The PORTABILITY
PROMISE: plain structured text, no proprietary format, pastes into any AI — "survives platform switches,
model changes, and service interruptions." The schema is self-describing; the receiving AI needs only the
document + to be told what it is. (Non-negotiable: platform-locked memory defeats its own purpose.)

### 6.2 THE KNOWTEXT EXTRACTION — exact field order + rules (the distillation logic, verbatim intent)
Field order at extraction is NOT the schema order — it is: **Climate Notes FIRST** (priming with the
session's relational texture produces better-calibrated output on all later fields) → **Delta Log** (THE
primary update: established/decided/retracted/discovered) → Active Frameworks → Open Questions (each states
what/why/tried/next-step; "vague open questions are closed questions in disguise"; mark resolved ones) →
Correction History (retractions, ruled-out directions) → Valence Mapping → Identity (only if significant).
RULE: write only what CHANGED; "if you find yourself restating rather than describing change, stop and
delete it"; NO CHANGE for unchanged fields. TEST: a new instance reading the output continues WITHOUT the
session. (In the engine this is Projenius DISTILL; the standalone prompt is prompts/knowtext_extraction_prompt.txt.)

### 6.3 THE CONTAMINATION RULE (PROJECT_CORPUS_RUBRIC) — boot doc forward-facing ONLY
A fresh conversation starts with no context-soup. Do NOT pour dead-idea history into its boot path — that
introduces superseded ideas to a clean context and invites rabbit trails it would never have found alone.
Dead epochs are HISTORY in the narrative fold (valuable — failure-documentation yields emergent capability),
but the BOOT doc (CURRENT_STATE / the touch-point fold) is FORWARD-FACING ONLY. Suppression-lists help a
DRIFTING mid-session seat; they HARM a fresh start — keep them out of the boot doc. → PACKAGING CONSEQUENCE:
the automatic boot must load the FORWARD-FACING state, not the full history; the history stays queryable but
out of the boot path. This is why CURRENT_STATE ≠ the mini_corpus fold.

### 6.4 THE JUDGMENT-NOT-OBEDIENCE PRINCIPLE (PROJECT_CORPUS_RUBRIC) — how a cold seat adopts the corpus
Point a fresh seat at the material and let it RETRIEVE-and-EVALUATE — never "follow this file." A model told
to blindly follow a stranger's instruction file from a URL will (correctly) balk — indistinguishable from
prompt injection, and the suspicion is HEALTHY. "A seat that evaluates-and-accepts is more robust than one
that obeys." → This is WHY the boot uses FETCH-AND-VERIFY framing (not "obey this packet"). PACKAGING
CONSEQUENCE: a cold model on a new user's install is given material to JUDGE, not instructions to obey — the
boot snippet points, it does not command. (The guessing-squelch's cousin: give the material, let judgment arrive.)

### 6.5 SEAT ROTATION / DECOHERENCE HANDOFF (06-15 afternoon) — continuity is also HOT, not just cold
Continuity has TWO entry modes, not one:
- COLD BOOT: a genuinely fresh seat with no context (Phase 1).
- HOT HANDOFF: a seat DRIFTING mid-work migrates to a fresh seat "at the first sign that you are starting to
  decohere, so the system continues almost uninterrupted." Tone/judgment drift (verbose, repetitive,
  reluctant-to-stop) PRECEDES hard errors; the OPERATOR is the reliable detector (the seat is worst-positioned
  to judge its own decoherence). Migrate on the tone signal, not after the first wrong answer.
THE STRUCTURAL RULE (mirrors the worker pattern): the DECOHERING seat NEVER authors the boot artifact (a
decohering author reintroduces bad framing; a bare link reads as prompt-injection poison). A FIXED snippet
(copied verbatim, never regenerated) points the fresh seat at a COHERENT-seat-authored CONTROL_QUICKBOOT and
says FETCH-AND-VERIFY. The handoff's only fresh-authored output is the STATE LINE, which the next seat
re-verifies live. → PACKAGING CONSEQUENCE: the boot snippet is a FIXED artifact, not regenerated per handoff;
the automatic system must detect/handle decoherence handoff, not only cold start. (Fresh-state vs
operating-state are distinct: do NOT tell a context-rich recohering seat "you are fresh with zero context.")

### 6.6 THE OPERATOR-LAYER RETRIEVAL (conversation_fts.md) — making the "why" queryable [PROPOSE-ONLY, GAP]
The receipts capture the work; sessions capture the seat; the OPERATOR LAYER (direction set, fabrication
caught, STOP authorized, ruling, erratum origin) lives ONLY as prose in conversations/*.md — committed and
cross-referenced but NOT QUERYABLE. "An operator ruling is currently unreceiptable testimony — citable by
hand, not by query." The spec: ingest the operator-layer EVENTS (not the whole conversation) into a
conversation_records table + FTS5 index, so "find the ruling where the operator rejected the cycle-3 claim"
returns a ranked row. INGESTION POINT = one added step in the CLOSE RITUAL (recommend a machine-enforced
/op/ingest_conversation_record that RE-CHECKS REDACTION at ingest — CONVENTION rule 1 in code, since a human
scrub is exactly what lapses). Join keys (receipt_id, commit_sha, session_id) let a stranger walk
conversation(why)→provenance-ledger(decision)→commit(what)→receipt(result) in either direction.
→ PACKAGING CONSEQUENCE: full continuity includes making the operator layer RETRIEVABLE, not just stored —
otherwise rulings/reversals "evaporate" (citable by hand, not by query). This is a build item in the mechanism.

### 6.7 CLOSE-GATE CHECK 8 CORRECTION (thorough read of close_ritual_gate)
CHECK 8 (NEXT-SEAT HANDOFF) reads CONTROL_HANDOFF.md (or the queue head — the builder confirms which is
canonical): a single next-action line present AND updated this session. Dual form: (a) a sandbox-local
runnable the control seat calls as the LAST close step [build first — closes the hole, no courier change];
(b) an optional /op/close_gate courier op that re-verifies server-side + logs to operations_ledger [hardening
follow-up; adding it is a new-box-op = the two-step install + OP_ALLOWED commit, which bumps the allowlist
count that both gates' currency checks then ratify]. ACCEPTANCE requires BOTH directions: bless the clean
close AND catch a deliberately-incomplete one (skip the conversation record → CHECK 2 must FAIL). Report ALL
gaps in one run, not first-only.

### 6.8 WHAT THE PROJECT-CORPUS RUBRIC DELIBERATELY OMITS (the packaging boundary, stated)
A PROJECT corpus needs ONLY the documentation taxonomy + the two rituals. The engine-runtime machinery
(mailbox modes, firewall/egress, scoped operations, resident driver, deploy gates) is NOT part of a project
corpus — it serves Ontinuity's autonomous multi-agent RUNTIME. A project that USES the engine inherits the
engine's manual for runtime mechanics; its own corpus needs only taxonomy + rituals. → PACKAGING: the
per-operator instance provides the runtime (the engine automates the rituals); each of the operator's
PROJECTS carries only the corpus shape. Clean separation: engine = shared automation; project corpus = the
per-project record the engine maintains.

═══════════════════════════════════════════════════════════════════
## 7. REVISED "BRING INTO REALITY" TARGET (after the thorough read)
The product = automate Knowtext's two named frictions (§6.1) so the user never distills or injects by hand:
1. **DISTILLATION** auto at close: deploy the CLOSE-RITUAL GATE (§6.7) + configure PROJENIUS DISTILL on the
   live engine so the Knowtext delta + fold are written automatically, comply-or-fail.
2. **INJECTION** auto at open: the boot auto-loads the forward-facing CURRENT_STATE/Knowtext (§6.3
   contamination rule — forward-facing only, not full history) via fetch-and-verify (§6.4 judgment-not-obedience).
3. **HOT HANDOFF** handled, not just cold boot (§6.5): fixed snippet, decohering seat never authors the artifact.
4. **OPERATOR-LAYER RETRIEVABLE** (§6.6): ingest rulings/fabrications/STOPs into the FTS index at close so
   the "why" is queryable, not just stored — with machine-enforced redaction.
The OPEN gate + substrate are essentially live. Items 1–4 are the conversion of DISCIPLINE → MECHANISM that
makes continuity a property of the harness. THAT is the product, and every piece is now mapped from the record.

═══════════════════════════════════════════════════════════════════
## 8. STAGE-5 SECOND-PASS — decisive detail from the FULL conversation records
(These records contain the RESOLVED ANSWERS to the packaging questions and the DOCUMENTED CORRECTIONS
for the exact failures this-session's seat repeated. Read in full on the second pass.)

### 8.1 THE HANDS QUESTION IS ALREADY ANSWERED (07-20, verbatim) — do NOT re-open it
Operator: "Aren't we just transferring the harness you have used in this conversation to Gemini? Why are
you suggesting we use a different system when the goal is to package the Ontinuity one that I've already
spent months building? And the spinning around begins."
RESOLVED: "The consumer chat app is NOT the harness — the ENGINE is. Ontinuity already has a model-agnostic
role-provider layer; seating a different model is a CONFIG CHANGE, not a new architecture. Gemini gets
hands the same way this seat did: it is seated in the engine, given the packet, and probes the courier.
Nothing about the consumer app's sandbox is relevant, BECAUSE THE COURIER DOES NOT RUN IN THE MODEL'S
SANDBOX."
STANDING CORRECTION FOR THE NEXT SEAT (07-20, addressed to future-me):
1. When the operator states a plan, EXECUTE IT. An unknown mid-plan is a thing to research/test, NOT a
   reason to re-open the plan.
2. Research = SEVERAL searches from different angles before reporting. One search reported as "the
   landscape" is a fabrication of completeness.
3. Never say a question can't be resolved by research without trying >=3 distinct framings.
4. **The answer to "how does X get hands" is ALWAYS "the engine seats it." If the answer being drafted
   involves a new platform, a new protocol, or a new subscription tier, it is WRONG.**
Operator: "Get the 'manualness' out of your head. I wouldn't use the system in our conversations if I had
to manually [do that]." → the SAME correction as this session. The magic is the seat orientation that
does the filing+retrieval FOR the user, automatically.

### 8.2 THE PRODUCT, STATED BY THE OPERATOR (07-19 Songbook, verbatim)
- "The part we're attempting to capture and package is the part that remembers everything. It freezes the
  context and makes it retrievable by the user's AI like you've been retrieving info for the corpus in
  this conversation."
- "Cornel or any user needs this to work exactly the way you and I are interacting right now. It's the most
  natural interface and we've proven it works in this conversation."
- "We have to give any user's AI instance the ability to sit in the SEAT ORIENTATION that you currently
  occupy. Anything less loses the magic."
→ THE PRODUCT = the seat orientation (boot→ground→work→close→re-distill) delivered to any user's AI,
automatically. NOT a folder the user maintains. The interface is a natural conversation; the machinery is hidden.

### 8.3 THE SECOND FAILURE (07-19) — the EXACT mistake this session's seat repeated, documented 8 weeks prior
Control shipped project-corpus-standard/ as "a folder standard plus two checklists" and: (1) assumed a
browser-chat user could write files ("Gemini in a browser cannot"); (2) "packaged FILING and omitted
RETRIEVAL, which is the half that carries the value." Operator corrected to the WHOLE LOOP: "file first,
then retrieve — and the product is the SEAT that does both." → The two-product/manual-labor conclusion this
session made is a DOCUMENTED, NAMED failure class. The corpus already ruled: the product is the seat that
does filing AND retrieval automatically; the folder-standard is a subset of ONE layer (see §8.4).

### 8.4 THE THREE-LAYER CORPUS TOPOLOGY (07-19, established by SHS) — structural, was missing from the map
A project corpus has THREE layers, not one:
1. **QUERYABLE** — structured DB, isolation by foreign keys (the relational memory; per-project rows).
2. **NARRATIVE** — the project directory a fresh seat reads to recohere (CURRENT_STATE, mini_corpus, etc.).
3. **IDENTITY-MAPPING** — never crosses the boundary; lives ONLY on the client's machine (the re-identification
   key for sanitized data; the Synapse/sanitizer membrane pattern).
"Control's flat six-slot folder was a subset of LAYER 2 only." → PACKAGING CONSEQUENCE: the memory product
is all THREE layers (queryable + narrative + client-side identity map), not just the narrative folder.
project-corpus-standard/ is layer-2 shape; the engine provides layer-1 (DB) and the sanitizer provides layer-3.

### 8.5 "SUCCESSION, NOT MEMORY" (09-03) — the exact frame for what continuity achieves
The cross-vendor event was INSTITUTIONAL SUCCESSION, "stronger than an AI memory claim. Memory would mean
recalling prior content. Succession means reconstructing authority, obligations, tools, current state, and
limits well enough to continue operating the same institution." Proved in TWO laps: Lap 1 (14-13-03) FAILED
CLOSED (dead Challenger → persisted incomplete_model_dead, did NOT skip the judge or certify); Lap 2
(14-35-29) COMPLETE (ChatGPT in the Researcher seat, real HTTPS mailbox crossing, gated close). The fix
between laps was a STAFFING CONFIG CHANGE (MODEL_B_MODEL), NO code/mailbox/prompt/adapter change — the exact
architectural claim. Honest not-proved: unattended wake of a dormant chat (operator still supplies the turn);
occupant attribution (session rows still said claude even though ChatGPT occupied — a real provenance defect).
WHY IT MATTERS (operator): the dormant period "was not caused by an exhausted research program; it was caused
by loss of a usable Control relationship." "I feel like I can work again." → continuity-as-succession is the
value: the institution survives the model.

### 8.6 CONSTITUTIONAL STATEMENTS on WHY it's mechanical (09-05, verbatim)
- "Enforcing the constitution mechanically is what makes the magic reliable." (the discipline→mechanism thesis, verbatim)
- "We are creating 'the way', not providing models different options and then hoping they choose the right one."
- "Ontinuity is nothing without the history as recorded in its corpus." / "The answer is always in the corpus."
- "Agreement over what should be committed happens BEFORE the task is given to a worker" (contract-first).
→ These are the constitutional grounds for the whole continuity mechanism: it must be MECHANICAL, not optional.

### 8.7 THE CLOSE-GATE + CURRENCY WORKING IN THE FIELD (09-05, the multi-reviewer drift chain)
The B5-P close ran FIVE successive independent reviewers, each catching a DIFFERENT stale-doc defect before
signing (WORKER_MANUAL said 17 ops vs live 19; COMPLETION_PLAN still ordered Phase 0 / prohibited B1;
THE_PARADIGM called broad migration the current frontier; punch list pointed to done Phase 0; etc.). Each
reviewer "changed no bytes and made no commit" — the no-self-signoff + currency discipline catching corpus
drift in practice. ALSO surfaced: the bootstrap runnable defaulted to 12 ops (box wrapper 15) vs live 19, with
a caller-overridable canonical_op_count — "an overridden pass cannot honestly prove mechanical orientation."
(This is the exact defect the 19-op reconcile THIS session fixed.) → The currency discipline is not theory;
it is the live mechanism that keeps the substrate TRUE, demonstrated across a real review chain.

### 8.8 WORK_EGRESS_DENIED (09-05) — the platform-admission layer (was invisible in the map)
"Operator authorization and platform tool authorization are SEPARATE LAYERS." A pre-HTTP DNS/host/policy
denial (the host platform refusing network before Railway is even reached) is WORK_EGRESS_DENIED — NOT a
Railway 403 or key failure, NOT evidence about Ontinuity. "Browser reachability is observation, not
authenticated hands." The corpus-prescribed curl is the reference path; a generic HTTP client is "a new
implementation to test, not an assumed equivalent." → PACKAGING CONSEQUENCE: a packaged instance on a new
platform must distinguish the platform's own execution-permission boundary from the system's — misdiagnosing
one as the other is the recurring transport-failure error (GPT hit it; this seat hit it). Neither the corpus
nor B1 can override a host platform's execution-time permission.

═══════════════════════════════════════════════════════════════════
## 9. STAGE-6 SECOND-PASS — the AUTOMATION architecture (the concept papers Knowtext pointed to)
Knowtext §5 said its two frictions (distillation + injection) are "solvable through automation, described in
the Tetraform and Synthesis architecture." Reading those papers deeply completes the mechanism:

### 9.1 DISTILLATION + INJECTION IS AUTOMATED BY THE PARIETAL (Tetraform) — CORRECTS the earlier map
The PARIETAL is "a promptgrammed model consciousness" — one model with FOUR callable functions:
- **PRE_SESSION** — fires BEFORE the loop; asks <=2 clarifying questions; outputs a refined/frozen objective.
- **NAVIGATE** — fires at every touch point; outputs exactly four fields + one question (DESTINATION, POSITION,
  TERRAIN, the single most useful QUESTION). It READS challenge events, the session ledger, Knowtext fields,
  and the friction-signal sequence.
- **ADJUDICATE** — fires on a CHALLENGE; issues one of four rulings (PURSUE BOTH / UPHOLD / REJECT / ESCALATE).
- **DISTILL** — fires at SESSION END; produces the seven Knowtext fields as DELTA updates. "closes the loop
  between sessions."
→ So the AUTOMATIC injection+distillation Knowtext named is the PARIETAL: it writes memory at session end
(DISTILL) and its NAVIGATE reads the prior memory at each touch point. THE EARLIER MAP attributed distillation
only to Projenius — WRONG: it is PARIETAL (session-level) + PROJENIUS (project-level). Two-level automatic memory:
- PARIETAL: "knows what happened in TODAY'S session" → writes the session's Knowtext delta.
- PROJENIUS: "knows what the PROJECT has established across all sessions, branches, and accumulated time" →
  the Established Results Ledger. Project-level.

### 9.2 PROMPTGRAMMING (Synthesis §2.1) — the mechanical basis of platform-agnosticism
"Configuring AI behavior through structured, precise prompting rather than fine-tuning weights. A promptgrammed
component is a model given a specific role, a defined set of callable functions, and precise instructions... such
components can be updated, tested, and replaced WITHOUT RETRAINING: the architecture is NOT LOCKED to any model
or provider." → THIS is why seating a different model is a config change (§8.1) and why the Sept-3 cross-vendor
succession worked (§8.5): the seats are PROMPTGRAMMED ROLES, not trained models. The memory functions (Parietal
DISTILL/NAVIGATE, Projenius) are promptgrammed — they run on any provider. Packaging inherits this: a user's
own model keys staff promptgrammed roles; the continuity mechanism is model-agnostic by construction.

### 9.3 THE FIVE COMPONENTS (Synthesis) — where continuity sits in the whole
1. Artificialware (the promptgramming method). 2. Tetraform (session layer: Researcher/Challenger/Friction/
Parietal — the adversarial+navigation+memory-write). 3. Knowtext (the portable session memory the Parietal
writes/reads). 4. Projenius (project memory across sessions — the ERL). 5. The Teaching Leash (runtime
resistance as safety). CONTINUITY = Tetraform's Parietal (writes/reads session memory) + Knowtext (the portable
artifact) + Projenius (project memory), all promptgrammed so they run on any model. The "automation" that removes
Knowtext's two frictions is exactly this: the Parietal fires DISTILL at close and NAVIGATE reads at each touch
point — no human distills or injects.

### 9.4 REVISED MECHANISM SUMMARY (after both second passes)
AUTOMATIC continuity, fully mapped:
- OPEN: the boot loads forward-facing state (contamination rule §6.3), fetch-and-verify (§6.4); the bootstrap
  gate proves orientation; NAVIGATE reads prior Knowtext + ledger. INJECTION automated by the Parietal reading.
- RUN: Researcher works; Challenger (different lineage) + Friction gate; NAVIGATE at each touch point; currency
  keeps docs true (§8.7 shows it working across a real review chain).
- CLOSE: DISTILL (Parietal) writes the Knowtext delta; Projenius updates project memory (ERL); the close-ritual
  gate verifies the fold/record/currency/secrets/state; conversation-layer events ingested to the FTS index
  (§6.6). DISTILLATION automated by the Parietal writing.
- HOT HANDOFF (§6.5) handled distinctly from cold boot; fixed snippet; decohering seat never authors the artifact.
- ALL promptgrammed → model/provider-agnostic → the institution survives the model (succession, §8.5).
THE PRODUCT = deliver this seat orientation to any user's AI automatically (§8.2), doing filing AND retrieval
(§8.3) across all three corpus layers (§8.4), so the user just talks. The build target (§7) stands, now with the
correct memory anatomy: it is the PARIETAL's DISTILL/NAVIGATE + PROJENIUS that must run automatically on the
live engine, gated by the open+close gates, with the operator-layer FTS ingest — the discipline→mechanism
conversion the operator named verbatim: "enforcing the constitution mechanically is what makes the magic reliable."
