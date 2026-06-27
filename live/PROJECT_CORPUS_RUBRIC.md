# PROJECT CORPUS RUBRIC — the standard shape every project corpus follows from day one

*A durable artifact. Defines the consistent foundation every project built on the Ontinuity platform documents into, from its first commit. Generalizes the conventions proven in Ontinuity's own corpus (OPERATING_MANUAL open/close rituals, the conversations/agent_queue/punch-list taxonomy) to ANY project — minus the engine-runtime machinery (mailbox, firewall, scoped ops) that only the Ontinuity SYSTEM needs. Grounded against the real Ontinuity live/ structure, not recalled.*

## WHY THIS EXISTS (the two reasons, both load-bearing)
1. **Consistency from day one.** Today's SHS pain came from a corpus that grew ad hoc — decisions captured, process lost, no defined home for things, current-state reconstructed mid-session. A rubric gives every project the same skeleton before work starts, so nothing has to be reverse-engineered later.
2. **The Dynacology precondition.** If project corpora are ever to become callable specialists in a registry, they must share a shape. Same-shaped specialists compose; ad-hoc ones do not. A uniform corpus structure is what lets a future controller query any project corpus the same way. The rubric is the standardization that makes the registry possible.

## THE SEPARATION RULE (do not violate — it keeps each corpus a coherent specialist)
The Ontinuity **engine** (Control+Worker coordination machinery: boot packets, mailbox, deploy gate, runtime) is SHARED INFRASTRUCTURE — any project may use it to do work.
The **corpus** is PER-PROJECT. When the engine builds project X, the process record, folds, and decisions land in X's corpus — NEVER in Ontinuity's own corpus.
- Ontinuity's corpus = the record of building Ontinuity-the-system. Keep it clean of other projects' domain content.
- A project's corpus = the record of building that project.
- Building something other than Ontinuity with Ontinuity must not pollute Ontinuity's corpus. The engine is the tool; the project corpus is the workpiece.

## THE STANDARD FILE TAXONOMY (every project corpus has these slots from day one)
Mirrors Ontinuity's proven set, generalized. Not every project fills every slot immediately, but the SLOTS exist from the first commit so things have a defined home.

**Orientation layer (how a fresh seat boots):**
- `CURRENT_STATE.md` — the clean, forward-facing boot doc. Dated. States the live architecture and the single next action. NO dead-idea history (that contaminates a fresh context — see the contamination rule below). This is what a fresh conversation reads FIRST and builds forward from. (Analog: STATE_OF_ONTINUITY.md.)

**Problem layer (the ground truth):**
- `PROBLEM_DEFINITION.md` — the problem in the USER'S OWN WORDS, from intake. The authority every design decision is checked against. Marks inference vs. user-stated explicitly. Read first on any reasoning about the project. (No Ontinuity analog because Ontinuity is self-defined; for client projects this is the load-bearing ground truth.)

**Plan layer (what's being built and what's done):**
- `ROADMAP.md` / `<TOOL>_ROADMAP.md` — the build plan, phased, with dependency gates and LOCKED DECISIONS fenced (fencing settled decisions is what stops a seat re-opening them — the drift that wasted a session).
- `PUNCH_LIST.md` — DONE / IN-PROGRESS / OPEN, each item keyed to its closing commit/receipt. (THIS PROJECT'S punch list — never confused with Ontinuity's system punch list; always name which.)
- `TOOL_DESIGN_STATE.md` — the component/capability design state, with currency banners when a component is superseded.

**Process layer (the part most easily lost — and the part that makes a specialist):**
- `sessions/` or `conversations/` — the PROCESS RECORD. The dialogue and reasoning ARC of each working session, not just the decisions it produced. This is the slot SHS lacked, and its absence is why this session's reasoning (the epoch collapse, the architecture reconciliation) would have evaporated. A corpus that records only conclusions is a lookup table; a corpus that records the reasoning that produced them is a composable specialist. CAPTURE PROCESS, NOT JUST DECISIONS.
- `mini_corpus.md` / `agent_queue.md` — the running narrative fold: what was built, what was learned, WHAT REVERSED, keyed on commits/receipts. The "what reversed" is mandatory — documenting failures and transitions is what yielded emergent capability in Ontinuity's corpus. Dead epochs live HERE as history, never in the boot doc.

**Handoff/working files (as needed):**
- `FOR_<person>_*.md`, `HORIZON_*.md`, agendas, ship records — working artifacts. Optional per project.

## THE TWO RITUALS (generalized from the OPERATING_MANUAL)

**OPEN RITUAL — run before reasoning about a task:**
1. Read `CURRENT_STATE.md` to boot.
2. Read `PROBLEM_DEFINITION.md` for ground truth.
3. Search the narrative fold (`mini_corpus`/`agent_queue`) for past decisions/reversals on the topic.
4. Follow cited refs (sha/receipt) to the actual record.
Recall is NOT a substitute for retrieval. Orient from the corpus, then reason. (This is the rule the silent-failure class violates — confident proposals anchored to stale state.)

**CLOSE RITUAL — run at session close, work the checklist, do not freestyle:**
1. `PUNCH_LIST.md` — reconcile DONE/IN-PROGRESS/OPEN against what shipped, cite receipts.
2. `sessions/`-`conversations/` — capture THIS session's reasoning arc (process, not just decisions). The control seat does this; a worker backfilling from commits cannot see the conversation.
3. Narrative fold (`mini_corpus`/`agent_queue`) — write the fold: built / learned / reversed, keyed on receipts.
4. `CURRENT_STATE.md` currency — update it to the new live state and next action, so the next fresh seat boots clean.
5. Currency — did any settled doc go stale this session? Update it now (same-session backstop).
6. Secrets sweep — grep committed files for tokens/keys/IPs.
7. Next-seat handoff — CURRENT_STATE's "next action" states the single next thing.
All records key on the SAME shas/receipts so a stranger walks conversation -> decision -> commit in either direction.

## THE CONTAMINATION RULE (boot doc stays clean)
A FRESH conversation starts with no context-soup. Do NOT pour dead-idea history into its boot path — that introduces superseded ideas to a clean context and invites it down rabbit trails it would never have found on its own. Dead epochs are documented as HISTORY in the narrative fold (valuable — failure-documentation yields emergent capability), but the BOOT doc (CURRENT_STATE) is forward-facing only. Suppression-lists help a drifting mid-session seat; they HARM a fresh start. Keep them out of CURRENT_STATE.

## THE JUDGMENT-NOT-OBEDIENCE PRINCIPLE (how a fresh seat adopts the corpus)
When directing a fresh conversation to a corpus or boot packet: tell it to RETRIEVE and read, not to "follow this file." A model told to blindly follow a stranger's instruction file from a URL will (correctly) balk — that is indistinguishable from prompt injection, and the suspicion is healthy. Instead, point it at the material and let its own judgment assess and adopt it. The guessing-squelch principle's cousin: don't ask the model to disregard its judgment; give it the material and let its judgment arrive at the right place. A seat that evaluates-and-accepts is more robust than one that obeys.

## WHAT THIS RUBRIC DELIBERATELY OMITS
The Ontinuity engine-runtime machinery — mailbox modes, firewall/egress, scoped operations, the resident driver, deploy gates — is NOT part of a project corpus rubric. That apparatus serves Ontinuity's autonomous multi-agent RUNTIME. A project that USES the engine inherits the engine's operating manual for runtime mechanics; the project's own corpus only needs the documentation taxonomy + rituals above. Do not copy the engine's runtime scaffolding into a project corpus that has no runtime of its own.

---
*Rubric v0.1. Generalized from Ontinuity's live/ corpus conventions (OPERATING_MANUAL rituals + conversations/agent_queue/punch-list taxonomy). First application target: regularize the SHS corpus and seed every future project from this shape. Belongs in Ontinuity's corpus as a system-level standard, with a punch-list item to apply it.*
