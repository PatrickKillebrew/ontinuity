# ONTINUITY 1.0 — COMPLETION PLAN

**Status:** controlling roadmap for the completion phase  
**Established:** 2026-09-03  
**Operator:** Patrick Killebrew  
**Purpose:** compress the discovered Ontinuity architecture into a finished, testable, transferable system whose behavior makes its own argument.

---

## 1. THE PHASE CHANGE

Ontinuity was built during roughly three months of discovery. The system and many of the tools required to build it were invented together: corpus discipline, Control boot, scoped hands, external-seat mailbox, persistent seat mailbox, adversarial gates, authorship rules, deployment separation, receipts, and reversal records.

That phase produced enough machinery. The project is no longer governed by the question **"What else could Ontinuity become?"** It is governed by:

> **What is the smallest coherent machine that proves the Ontinuity vision works?**

The operator's phase-change ruling:

> "I agree that there's nothing left to decorate. Completing the punch list, where relevant, will get me closer to whatever the finish line is."

And the controlling destination:

> "The artifact making the argument on its own is where I need to be."

New architecture is therefore guilty until a release requirement demonstrably fails without it. Existing ideas are not implemented merely because they are interesting or already appear on the punch list.

## 2. THE PRODUCT CLAIM

Ontinuity 1.0 is a model-agnostic operating institution for consequential AI-assisted work. It aims to provide:

1. **Continuous institutional memory** — a fresh conversation, model, or vendor reconstructs current project state without the operator retelling the history.
2. **Material fabrication reduction** — unsupported or incorrect claims are caught more reliably than in a matched strong single-model workflow.
3. **Usable, contract-shaped deliverables** — a session completes with an artifact satisfying criteria frozen before judgment, not merely an interesting transcript.
4. **Governed problem-to-software execution** — a problem can move through specification, implementation, testing, independent review, correction, signing, and deployment with durable provenance and no self-certification.

These are hypotheses until their acceptance tests pass. The system must distinguish demonstrated properties from aspirations.

## 3. DEFINITION OF ONTINUITY 1.0

Ontinuity 1.0 is complete only when all ten release conditions below pass.

### RC-1 — Fresh-seat continuity

A new Control occupant with no private prior conversation receives the boot instruction and accurately reconstructs:

- the current objective;
- current system state;
- the authoritative next action;
- available hands;
- active constraints and authority boundaries;
- unresolved defects relevant to the task.

**Acceptance:** three cold boots using at least two model vendors; each returns the required grounded facts and passes the bootstrap gate without operator correction of a system fact.

### RC-2 — Operator-approved, scoped identity

No permanent master credential must enter a model conversation. A seat requests admission; the operator approves it; the engine issues a short-lived, revocable identity with an explicit operation allowlist.

**Acceptance:** the seat operates through the courier; cannot call an excluded operation; cannot assert another identity; expires or is revoked; `DIAG_KEY`, Railway token, GitHub token, and provider keys never enter its prompt, transcript, command arguments, URLs, or logs.

### RC-3 — Honest occupant and action provenance

Every session and material action names the actual harness:model occupant, authenticated seat identity, author, reviewer, corrector, signer, and deployer where applicable.

**Acceptance:** an external ChatGPT Researcher lap records ChatGPT rather than the historical Claude placeholder; corrections transfer authorship; every DONE/deployed claim joins to real evidence.

### RC-4 — Fail-closed session integrity

Incomplete, stopped, timed-out, or model-dead sessions cannot default to complete. Completion is reached only through the certified close path.

**Acceptance:** museum tests cover normal close, Challenger death, Researcher death, operator stop, timeout, malformed model response, and missing extraction. Every exit persists an honest status and `end_reason`.

### RC-5 — Independent authority enforcement

The author of exact bytes cannot certify or deploy those bytes. A correction makes the corrector the new author. Review and signoff outcomes are machine-distinguishable.

**Acceptance:** must-pass and must-refuse tests prove no-self-review, no-self-signoff, correction re-review, and no-self-deploy across distinct authenticated identities.

### RC-6 — Complete evidence chain

Session criteria, model turns, tool executions, challenge events, operator rulings, corrections, work products, commits, reviews, signoffs, and deployment receipts remain traversable.

**Acceptance:** a stranger can start from a delivered artifact and walk backward to the frozen contract and evidence, or start from the initiating objective and walk forward to exact deployed bytes.

### RC-7 — Consolidated, reproducible system

The running engine, box, repository, schema, and documentation have explicit canonical sources and a reproducible installation path.

**Acceptance:** a clean environment can be provisioned from the documented release; deployed versions are reported; repository commit versus box install is visible; no undocumented manual step is necessary beyond operator-owned credentials and approvals.

### RC-8 — Comparative reliability evidence

Ontinuity is compared with a strong single-model workflow on the same tasks, source material, and success criteria.

**Acceptance:** preregistered or frozen evaluation protocol; representative bounded tasks; blinded human adjudication where practical; fabrication/material-error rate, completion quality, time, token/API cost, gate interventions, and operator interventions reported. Negative or mixed results remain in the report.

### RC-9 — Outside-operator transfer

A person who did not design Ontinuity can operate it without Patrick privately reconstructing the system for them.

**Acceptance:** one outside operator completes orientation, runs a task, diagnoses at least one visible state/failure condition, resumes after interruption, and retrieves the final evidence chain. Every undocumented intervention by Patrick is logged as a product defect.

### RC-10 — Independent technical criticism

The release receives bounded external review rather than a request to understand or endorse the entire worldview.

**Acceptance:** at minimum:

- one distributed-systems/backend review of state, queueing, recovery, and deployment topology;
- one security/identity review of authorization, impersonation, credential custody, and authority separation;
- one evaluation-method review of the fabrication-reduction comparison.

Findings are triaged as release-blocking, post-1.0, rejected-with-reason, or accepted risk.

## 4. ORDER OF WORK

The existing punch list is evidence and raw backlog, not an instruction to implement every surviving idea. Work proceeds in dependency order.

### Phase 0 — Resolve the record

**Goal:** produce one truthful backlog and release boundary.

- Reconcile all IN-PROGRESS and OPEN items against deployed code, box state, receipts, and later folds.
- Move completed and retired items out of pending sections.
- Merge duplicates and identify superseding decisions.
- Assign every genuine remainder to: 1.0 blocker, 1.0 evidence, post-1.0, horizon, or discard.
- Produce a dependency-ordered 1.0 board from RC-1 through RC-10.

**Exit:** no item is simultaneously DONE and pending; every 1.0 item names the release condition it serves.

### Phase 1 — Identity, admission, and provenance

**Goal:** establish who occupies a seat and what that identity may do without giving models master credentials.

Consolidate these existing arcs:

- Seat registry / identity primitive
- Per-identity keys
- SECAUDIT engine-arm follow-up
- Multi-tenancy and real authentication
- Settings and credential hardening
- External Researcher occupant provenance
- Removal of cached GitHub PATs from Llaves

Replace the password-unlocked master-vault direction with operator-approved, short-lived capability admission. Keep master credentials server-side.

**Exit:** RC-2 and RC-3 pass; credential rotation becomes ordinary hygiene rather than recovery from routine conversational exposure.

### Phase 2 — Integrity gates and durable evidence

**Goal:** make the strongest Ontinuity claims enforced and testable.

- Certification-by-default inversion + `end_reason`
- Challenger-death and abnormal-exit verification
- Execution-log persistence
- Adversarial-catch capture
- Review/signoff outcome integrity
- Review-finding lifecycle
- Human/operator input provenance
- Bootstrap and close-ritual enforcement
- Formal museum of must-pass/must-refuse specimens

**Exit:** RC-4, RC-5, and RC-6 pass under automated tests.

### Phase 3 — Consolidation and reproducibility

**Goal:** turn the founder-operated prototype into a release another technical person can install and inspect.

- Decompose the application along real boundaries only where this reduces release risk.
- Establish canonical engine, box, schema, prompt, and UI locations.
- Reconcile GitHub/Railway/Hetzner drift mechanically.
- Create installation/configuration runbook and release manifest.
- Automate database backup and recovery verification.
- Remove dead and competing implementations from the active surface while retaining history in version control/archive.
- Make the cockpit a safe observation/control surface; separate observation from global configuration mutation.

**Exit:** RC-7 passes from a clean environment.

### Phase 4 — Falsification and measurement

**Goal:** determine whether Ontinuity improves outcomes enough to justify its complexity.

- Select several bounded tasks where unsupported claims or incorrect implementation matter.
- Freeze sources, objectives, contracts, models, and adjudication rules.
- Run matched single-model and Ontinuity conditions.
- Preserve all failed and unfavorable sessions.
- Report quality, fabrication, material errors, latency, cost, and human intervention.
- Separate protocol-conformity measures from psychological interpretation.

**Exit:** RC-8 passes and the report states what Ontinuity does not improve.

### Phase 5 — Human transfer

**Goal:** prove Ontinuity survives changing operators as well as changing models.

- Prepare the minimum onboarding and operator surface.
- Select one real outside operator and bounded workflow.
- Observe without silently rescuing the trial.
- Convert every required private explanation into documentation, interface, or an explicit prerequisite.
- Repeat after corrections if the first trial fails.

**Exit:** RC-9 passes.

### Phase 6 — External review and career evidence

**Goal:** allow the artifact to make its argument and translate the demonstrated ability into professional opportunity.

Produce:

1. One-page conventional resume with Ontinuity as the anchor project.
2. Two-page case study: problem, hypothesis, architecture, failures, evidence, limitations.
3. Ten-minute recorded demonstration: cold boot, real turn, challenge, refusal/correction, close, provenance, succession.
4. Technical evidence package: architecture, threat model, install guide, tests, benchmark, known limitations, selected records.
5. Bounded review requests for systems, security, and evaluation specialists.

Professional positioning:

> **Applied AI Systems Designer and Prototyper** — designs and builds governed multi-model systems that turn unreliable model output into persistent, independently reviewed, auditable work.

Primary role families: applied AI prototyping, forward-deployed AI, agent/evaluation engineering, AI reliability, research tooling, solutions architecture, and technical product discovery.

**Exit:** RC-10 passes; an outside reviewer can understand the claim without first reconstructing Patrick's entire conceptual history.

## 5. WORKING RULES FOR THE COMPLETION PHASE

1. **Release condition before build.** Every work block must name which RC it advances.
2. **No ornamental architecture.** A new component requires evidence that an RC fails without it.
3. **Resolve before adding.** Search the punch list and corpus for an existing/superseded item before creating another.
4. **Test the guarantee, not the prose.** A documented invariant without a must-refuse test is not yet enforced.
5. **Preserve negative evidence.** Failed sessions, rejected designs, mixed benchmarks, and outside confusion remain visible.
6. **One authoritative current state.** Historical reasoning stays accessible but does not compete with the current operating surface.
7. **Master secrets remain server-side.** Models receive scoped, temporary capabilities—not the keys behind the capabilities.
8. **Patrick is the operator, not middleware.** Any repeated manual relay, reconciliation, or rescue is a candidate defect.
9. **AI assistance is disclosed accurately.** Patrick owns the problem, architecture, judgment, and integration; model collaborators contribute implementation and analysis.
10. **Stop at proof.** Post-1.0 product breadth, scale, and new research do not block the release unless the evidence says they must.

## 6. EXPLICITLY NOT REQUIRED FOR 1.0

Unless a release test establishes otherwise:

- S22 local-inference node
- Broad chat-channel integrations
- Automatic spawning of large worker populations
- Full commercial multi-tenancy
- Notarian product line
- Every Governor visualization
- Generalized autonomous operation across arbitrary domains
- Lifetime-ground-truth or trustless cross-institution horizon work
- Completion of every historical punch-list item

These remain possible futures, not excuses to defer a coherent release.

## 7. PROGRESS REPORT FORMAT

Every completion-phase work block closes with:

- **Release condition:** RC-N
- **Claim tested:** exact property under examination
- **Evidence read:** authoritative sources and live state
- **Change made:** code/config/docs, or no change
- **Test result:** pass/fail/mixed
- **New debt:** anything introduced
- **State left:** engine/box/repo/session status
- **Next dependency:** one bounded next action

Progress is measured by release conditions passing, not commits, corpus volume, sessions run, or punch items touched.

## 8. IMMEDIATE NEXT ACTION

Run **Phase 0: Resolve the record**. The current resolved punch list still contains completed, retired, duplicated, and superseded items under pending headings. Produce the dependency-ordered 1.0 board before choosing a build.

Do not begin the credential broker, provenance repair, or another test lap until the board shows which item comes first and why.

---

## CONTROLLING STATEMENT

Ontinuity began as an attempt to build the tools required for a form of AI collaboration that did not yet exist for its operator. The discovery phase succeeded when the institution survived replacement of the model around which it had been built. The completion phase succeeds when that institution is secure, measurable, reproducible, transferable, and understandable without privileged access to the mind that imagined it.

**CROSS-REF:** `live/PUNCH_LIST.md`; `live/agent_queue.md`; `live/CONTROL_HANDOFF.md`; `live/OPERATING_MANUAL.md`; `live/conversations/2026-09-03_openai-control-succession-platform-agnostic-proof.md`; `live/conversations/2026-09-03_completion-phase-and-career-path.md`.
