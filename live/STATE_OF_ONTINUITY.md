# ONTINUITY — STATE-OF-SYSTEM INVENTORY
*Grounded from the live operating record (repo `live/` + `papers.html` harness notes), June 19 2026. Not reconstructed from the April founding papers. Where this and the April corpus disagree about how the system works, this wins — the April papers describe the system's first form; this describes what runs today.*

---

## 0. THE ONE-LINE TRUTH
Ontinuity is no longer "a four-model research session." It has matured into a **team-of-seats system with a two-party deploy gate**, where reliability is supplied by the *harness* (grounding-from-record + a gate that won't let a session close until output matches a contract frozen before the session began), not by whatever model happens to be in the seat. The April papers (Tetraform, the cognitive ecology, the four roles) are the **conceptual foundation**; the gate/contract/seat architecture is the **current system** and is documented nowhere but the repo.

---

## 1. THE CORE MOVE — ground from the record, not priors
The load-bearing discipline. Every seat (operator, control, worker) is a model that will, left alone, reason from training priors — "artificial imagination." The rule: **use training data for CAPABILITY (code, reasoning, language); NEVER for Ontinuity-facts** (how *this* system works, which lives only in the corpus, never in any model's weights). Where priors and corpus disagree about this system, corpus wins. Ambiguity is the front door for substitution; precision prevents, the gate only catches. Every seat is required to re-derive its operating reality from the corpus *before acting, every cycle*.

## 2. THE FOUR SEATS
- **OPERATOR (Patrick):** direction, priorities, final authority + rollback. Talks to the planning seat only; is not the router, reviewer, or deploy-clicker. Settled design is not re-litigated back to him.
- **CONTROL / PLANNING:** the one seat the operator talks to. Holds GitHub + Railway tokens and box hands (the live `/op/*` allowlist). Commits, dispatches, reviews, lands signed-off work, keeps the record current. A *participant in a gated chain*, never the unchecked deployer. Characteristic failure = "comfortable delegation" (asking the operator instead of acting from the record).
- **WORKERS:** peer frontier instances (same model class as control; subordinate only in routing). Claim blocks from the mailbox, build, and **review each other's** proposals. Per-block scope, ground-from-corpus, **park-and-handoff at tool budget — never fabricate, never declare the system unreal.**
- **THE CHAIN (emergent):** task → build → peer review → sign-off → deploy → fold. No single judgment ships unchecked.

## 3. THE DEPLOY GATE (the reliability boundary)
**INVARIANT: the seat that DEPLOYS must never be the seat that authored the exact bytes being deployed.** deployer ≠ author-of-deployed-bytes.
1. Author proposes → mailbox.
2. A *different* seat reviews.
3. Clean sign-off → reviewer deploys (two parties satisfied).
4. Reject+correct → the corrector is now the author of corrected bytes → back to mailbox → a *different* seat signs off → that signer deploys. (Corrector must not deploy their own correction.)
The **Operator-Signoff token** makes the gate structural: tokenless/self-deploy → a `gate_violation` row. No-self-sign-off routing enforces it (a seat is never handed its own item; if only its own is reviewable, it PARKS). *Honest ledger: the gate has been jumped at least once (app.py batch deploy, logged not hidden) — the discipline is real and self-correcting.*

## 4. THE HARNESS / GATE-AND-CONTRACT (the public-facing current thesis)
From the two `papers.html` notes — the only current-system material already published:
- **"Reliability from the harness, not the model":** a model is seated in one role of an adversarial multi-model loop; a separate **gate refuses to let a session close until output matches a contract fixed before the session began.** The gate checks output against the frozen contract and is *indifferent to what produced it*. Reported behavioral record: **319 sessions**, seat held by **5 different models** (most often an inexpensive open-weight model), with per-cycle measurements including a **randomized-signal control** that distinguishes genuine adversarial response from its appearance.
- **"Watching a harness shape a frontier model":** a single session in full — a frontier model in the Researcher seat, a three-criterion contract, gate refused to close **three times** (forced a paraphrase→quotation, an inference→cited mechanism, a prose description→applicable edit) before accepting a consolidated deliverable. The close-up of the same mechanism the 319-record shows in aggregate.

## 5. THE OPEN & CLOSE RITUALS (what keeps a growing system coherent)
- **OPEN RITUAL** (before acting): orient from the corpus — search the queue folds (`agent_queue.md`), read the conversation records, follow cited refs (sha/receipt). *Recall is not a substitute for retrieval.*
- **CLOSE RITUAL** (8-item checklist, worked literally): punch-list reconcile → conversation record → queue fold → manual currency → contract-doc currency → provenance/commit-self → secrets sweep → state-left-clean → next-seat handoff. All records key on the **same shas/receipts** so a stranger can walk conversation → decision → commit → receipt in either direction.
- **CURRENCY DISCIPLINE:** the manual/rubric/paradigm/punch-list are updated WHEN THE THING CHANGES, IN THE SAME COMMIT. A drifted doc is a defect.

## 6. THE BOX HANDS — scoped operations (how a sandbox seat acts)
Privileged box actions run through **named, bounded operation endpoints** — never a shell, never an arbitrary command. Each op does exactly one thing; adding capability = adding a named op, never widening one. All diag-key gated, all logged to the `operations_ledger` (dual-end: intent on invocation, result on completion). Tiered SAFE / REVIEW / RISK (reuses the sign-off tiers).
Live allowlist: `read_journal`, `restart_workspace`, `register_egress`, `mailbox_send|fetch|ack|peek|reclaim`, `write_file`, `commit_self`, `backup_db`.
**The courier:** a sandbox seat can't reach the box directly (firewall by design). It reaches box ops through the **relay-courier on the engine** — `POST {ENGINE}/diag/op/<name>` with the diag key; the engine forwards to the box's `/op/<name>`, box enforces the full contract. This is THE way a sandbox seat gets box hands — no IP whitelisting.

## 7. OPERATING INVARIANTS (the mechanics a seat must state correctly)
- **NO SELF-POLL:** a chat seat does not self-poll; it acts only when its conversation is given a turn. A dormant chat worker needs its conversation *nudged* — nothing server-side wakes a dormant chat window. (An engine-instance worker IS woken by a mailbox write / shepherd heartbeat — that's the self-driving path.)
- **COURIER-ONLY:** a sandbox seat reaches box ops only through the relay-courier.
- **DEPLOY AUTHORITY:** operator owns deploys = authority + rollback, NOT a per-redeploy click.
- **NEW BOX OP** needs BOTH a box install (write_file + restart, hands-free) AND an OP_ALLOWED entry in app.py (commit + deploy).
- **ARTIFACT FLOW:** worker writes artifact to box → control reads it back + commits to repo → worker holds no token (propose, don't deploy).

## 8. THE CURRENT FRONTIER (honest, from the paradigm)
- **The operator-load problem:** today the operator must nudge each chat worker after it sleeps and route between conversations — impractical, the next thing to fix. Real fix = seats that poll/wake themselves = **API/engine-instance seats** (the farm is the proving ground). Blocker = cost.
- **Resolution = model tiering:** Frontier (Opus) where judgment is load-bearing (control/planning + review/sign-off); cheaper models for high-volume low-judgment cycles (first-draft build, poll/heartbeat/shepherd). "Route everything through Ontinuity" means everything runs through the gated documented system — NOT everything is Opus.
- **Self-hosting control (staged):** route the control seat itself through Ontinuity so it grounds from corpus every cycle (the permanent priors-leak fix). Stages: prove API-worker on cheapest tier → make boot-from-corpus structural (the **bootstrap gate**, esp. CHECK 6 MECHANICS — a seat must reproduce the operating invariants from the record before acting) → migrate control onto the API substrate. The bootstrap gate is the centerpiece, more than the migration.

## 9. HONEST CEILINGS (do not paper over)
- Chat seats sleep between turns; only an operator nudge wakes them. The shepherd detects idle-with-work and ALERTS but cannot re-enter a chat window. Walk-away needs engine seats.
- Until per-identity keys are live, seat identity is self-asserted (trusted-not-authenticated); the shared diag key is the known soft spot.
- Grounding-from-record REDUCES but does not ELIMINATE model imagination; the gate (no unchecked judge) catches what slips. **Architecture over trust.**

---

## 10. INFRASTRUCTURE (where it all runs)
- **Engine:** Railway (`web-production-7eaf8...`). **Farm:** separate Railway service (engine-instance worker proving ground). **Public site:** ontinuity.org (GitHub Pages, repo PatrickKillebrew/ontinuity).
- **Box / workspace:** VPS at port 5001, reachable only via the engine relay (firewall by design). Holds `ontinuity.db` (16-table SQLite + the operations_ledger).
- **Repo `live/`:** the durable operating record — THE_PARADIGM, OPERATING_MANUAL (42KB), OPERATING_RUBRIC, PUNCH_LIST, agent_queue (184KB of folds), CONTROL/WORKER boot+manual docs, horizons, the loop/seat/shepherd code, db.py.
- **Private repo** `ontinuity-intake-data`: client intakes + db backups.

---

## 11. WHAT THIS MEANS FOR THE PUBLIC SITE (the gap to close)
- The site's **homepage + 9 corpus papers describe the April system** (Triform/Tetraform, four-model session, 48hr origin). Accurate as history; two months behind as a picture of what runs now.
- The **only current-system material published** is the two harness notes on `papers.html` (gates, contracts, 319 sessions).
- **The keystone deliverable:** an updated synthesis that opens with the current thesis — *reliability from the harness; the two-party gate; grounding-from-record; the team of seats; the 319-session record; the fabrication-catch as the un-dismissible artifact* — built by **expanding the two harness notes** into the full end-to-end account, with the April corpus reframed as the documented foundation it grew from. This inventory is the source material for that paper, the homepage remodel that points at it, and the corpus index that frames the two eras.
