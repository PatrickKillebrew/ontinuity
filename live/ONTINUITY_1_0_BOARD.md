# ONTINUITY 1.0 — DEPENDENCY-ORDERED RELEASE BOARD

**Status:** authoritative execution board for the completion phase  
**Established:** 2026-09-03  
**Source:** reconciled from `ONTINUITY_1_0_COMPLETION_PLAN.md`, `PUNCH_LIST.md`, `agent_queue.md`, later folds, current repository source, and the September 3 cross-platform succession record.  
**Rule:** this board selects work. The historical punch list remains evidence and lineage; an item appearing there does not make it a release requirement.

---

## 0. RELEASE POSITION

| Release condition | Current disposition | Evidence still required |
|---|---|---|
| RC-1 Fresh-seat continuity | PARTIAL | One OpenAI Control succession passed without system-fact correction. Run two additional cold boots so the set contains three boots and at least two vendors. |
| RC-2 Scoped identity | FAIL / BLOCKER | Models still receive permanent shared roots. Build operator-approved short-lived admission and prove denial, expiry, revocation, and non-impersonation. |
| RC-3 Honest provenance | PARTIAL / BLOCKER | Authorship/deploy lineage exists, but external Researcher sessions retain the historical Claude occupant string. Bind actual occupant to authenticated identity. |
| RC-4 Fail-closed integrity | PARTIAL / BLOCKER | September model-death lap persisted incomplete, but certification-by-default and complete abnormal-exit museum coverage remain unresolved. |
| RC-5 Independent authority | PARTIAL / BLOCKER | No-self routing and deploy gate exist. Authenticated identities and must-refuse tests across correction/review/signoff/deploy remain required. |
| RC-6 Complete evidence chain | PARTIAL / BLOCKER | Commits, receipts, folds, session records, and operations ledger exist, but execution, operator-input, review-finding, and external-occupant seams remain. |
| RC-7 Reproducible system | FAIL / BLOCKER | Repo, Railway, and box can drift; no clean-install proof or canonical release manifest exists. |
| RC-8 Comparative evidence | NOT STARTED | Freeze protocol and run matched single-model/Ontinuity evaluation after integrity instrumentation is trustworthy. |
| RC-9 Outside-operator transfer | NOT STARTED | Run only after a reproducible installation and minimum operator surface exist. |
| RC-10 Independent criticism | NOT STARTED | Request bounded reviews after the technical evidence package exists. |

No DONE claim above is inferred from prose alone. `PARTIAL` means a real mechanism or specimen exists but the release acceptance test has not passed in full.

---

## 1. CRITICAL PATH

Work proceeds top to bottom. A later block may begin early only when it cannot change or obscure evidence needed by an earlier block.

### B0 — Establish the live release baseline

**Serves:** RC-7; prerequisite to every build  
**State:** PARTIAL — repository/public baseline recorded in `live/ONTINUITY_1_0_BASELINE.md`; authenticated live fields remain

Create a machine-readable and human-readable manifest of:

- GitHub `main` SHA;
- Railway MAIN and FARM deployed revisions;
- box hashes for separately installed operational files;
- schema version/table inventory;
- courier allowlist;
- role provider/model assignments;
- engine and mailbox health;
- public site and cockpit routes;
- canonical location for each engine, box, schema, prompt, UI, and operating document.

**Acceptance:** one command or bounded operation reports drift without changing state. Any unreachable fact is `UNKNOWN`, never inferred. The first observed baseline is committed before corrective deployment.

### B1 — Operator-approved capability admission

**Serves:** RC-2; prerequisite to authenticated RC-3 and RC-5  
**State:** READY AFTER B0

Supersedes and consolidates:

- per-identity keys;
- seat registry / auto-naming;
- settings and credential hardening;
- password-unlocked vault bootstrap;
- public/multi-user authentication insofar as required for one outside operator;
- removal of cached PATs and routine exposure of `DIAG_KEY`.

Build the smallest admission flow: a seat requests entry; the operator approves; the engine issues a short-lived identity-bound capability with an operation allowlist. Master credentials remain server-side. Seat and lineage are derived from the capability, not accepted from request bodies.

**Acceptance:** allowed read succeeds; excluded operation fails; altered seat identity fails; capability expires; operator can revoke it; no master credential appears in transcript, URL, command argument, application log, or receipt.

Full commercial multi-tenancy is POST-1.0 unless the outside-operator test proves it necessary.

### B2 — Bind occupant and action provenance

**Serves:** RC-3; prerequisite to trustworthy authority tests  
**State:** BLOCKED BY B1

- Bind external Researcher `harness:model` identity to the admitted capability.
- Persist authenticated actor identity for author, reviewer, corrector, signer, and deployer.
- Preserve legacy labels as historical metadata rather than current occupant truth.
- Require DONE/deployed claims to cite the actual evidence row or receipt.

**Acceptance:** a new external lap records its real occupant; body-field impersonation fails; correction transfers authorship; every action in the specimen chain joins to an authenticated actor.

### B3 — Make session completion fail closed

**Serves:** RC-4  
**State:** READY AFTER B0; may run alongside B1 design

Consolidates:

- certification-by-default inversion;
- persisted `end_reason`;
- Challenger-death integrity fix;
- honest stopped-session behavior;
- timeout, malformed-response, and missing-extraction exits;
- product silent-failure findings that can falsely imply completion.

**Acceptance:** only the certified close path writes `complete`. Museum specimens cover normal close, Researcher death, Challenger death, operator stop, timeout, malformed response, and missing extraction; every case persists an honest status and `end_reason` without waiting unnecessarily for an absent external seat.

### B4 — Formalize the museum and authority tests

**Serves:** RC-4 and RC-5  
**State:** BLOCKED BY B1-B3

Create a durable specimen store and runner. Consolidate:

- no-self-review/signoff/deploy tests;
- correction-makes-corrector-author test;
- review-event signoff-versus-reject guard;
- deploy-token and actor-provenance tests;
- bootstrap admission and close-gate must-refuse cases;
- malicious or ambiguous boot-instruction specimen.

**Acceptance:** reproducible must-pass and must-refuse suite, preserved in the repo, fails on each historical defect it is intended to prevent.

### B5 — Close the evidence-chain seams

**Serves:** RC-6; prerequisite to measurement  
**State:** BLOCKED BY B2-B4

Build only the missing joins required to traverse one complete artifact chain:

- session execution persistence;
- adversarial-catch event and content capture;
- operator rulings as attributed transcript/evidence rows;
- review findings through correction, signoff, and deployment;
- mailbox turn cycle identifiers;
- conversation-to-session/commit/receipt correlation;
- optional session annotation only if the chain cannot be expressed without it.

The previous standalone JSONL human-signoff-ledger proposal is superseded unless the existing database/receipt chain cannot satisfy RC-6.

**Acceptance:** an unfamiliar reviewer can walk objective -> frozen contract -> turns/tools/rulings -> work product -> implementation -> review/correction -> signoff -> exact deployed bytes, and reverse the path from artifact to objective.

### B6 — Reconcile and reproduce the installation

**Serves:** RC-7  
**State:** BLOCKED BY B0; final proof follows B1-B5

Consolidates:

- portable Ontinuity tenant;
- The Package as continuity/runbook source material;
- repo/Railway/box drift detection;
- canonical file locations;
- database backup and restore verification;
- installer/provisioning runbook;
- separation of cockpit observation from global configuration mutation;
- removal of competing active implementations.

Decompose `app.py` only where a measured test, ownership boundary, or reproducibility failure requires it.

**Acceptance:** provision a clean environment from a tagged release using only documented operator-owned credential and approval steps. It reports its own versions and detects repo-versus-box-versus-deployment drift.

### B7 — Complete three cold boots

**Serves:** RC-1  
**State:** ONE OF THREE EVIDENCED; final runs follow B1 and B6

Run three boots across at least two vendors. Each must retrieve objective, state, next action, hands, authority boundaries, and relevant defects; pass the bootstrap gate; and require no operator correction of a system fact.

The September 3 OpenAI succession is specimen 1 if its evidence satisfies the final protocol. Re-run rather than grandfather it if authenticated admission becomes a material part of the boot contract.

### B8 — Comparative reliability evaluation

**Serves:** RC-8  
**State:** BLOCKED BY B3-B5

Freeze tasks, sources, contracts, models, adjudication rules, and metrics before running. Compare a strong single-model workflow with Ontinuity on identical bounded tasks. Preserve unfavorable results. Measure material fabrication/error, contract completion, time, cost, gate interventions, and operator interventions.

**Acceptance:** reproducible report with blinded human adjudication where practical and an explicit account of what Ontinuity does not improve.

### B9 — Outside-operator transfer

**Serves:** RC-9  
**State:** BLOCKED BY B6-B8

An outside operator installs or receives the reproducible system, orients, runs a task, diagnoses one visible condition, resumes after interruption, and retrieves the evidence chain. Patrick observes but does not privately reconstruct missing context.

**Acceptance:** all rescues and explanations are logged; the run passes without undocumented intervention, or failures are converted into bounded defects and the test repeats.

### B10 — Independent bounded review

**Serves:** RC-10  
**State:** BLOCKED BY B6-B9

Package three review requests rather than asking anyone to evaluate the entire worldview:

- distributed systems: state, queueing, recovery, and deployment topology;
- security: identity, credential custody, impersonation, authorization, and separation of duties;
- evaluation: comparative protocol and fabrication-reduction claims.

**Acceptance:** findings are recorded and dispositioned as release-blocking, post-1.0, rejected-with-reason, or accepted risk.

---

## 2. RECONCILIATION OF HISTORICAL PENDING ITEMS

### Completed or already installed — remove from pending selection

- `you_there` long-poll / within-turn self-drain;
- no-self-sign-off routing predicate;
- box source recovery into version control;
- `commit_self`, `read_file`, `write_file`, and closed worker artifact loop;
- courier wrapper for `bootstrap_gate` and its allowlist entry;
- mailbox result-channel correlation and purge;
- current Parietal configuration and September Challenger replacement;
- public current-system synthesis and homepage modernization;
- Governor worker-status read route and page deployment, subject to B0 live verification.

### Retired, rejected, or superseded — do not build

- Coordinator loop: redundant with mailbox atomic claim and no-self predicate.
- Oracle process beyond its harmless schema plumbing: no consumer.
- Deleting raw-CDN `read_repo` fallback: disproven; retain cache-busted tokenless path.
- Password-unlocked master vault: superseded by B1 short-lived operator-approved capabilities.
- Standalone Project Corpus Standard as the whole product: retained as documentation material under B6.
- Global master Keys modal as the credential architecture: may remain for local recovery during transition, but is not the 1.0 identity solution.
- Self-enforcing deploy proposal that depends on a separate JSONL provenance source: re-evaluate under B4/B5; do not create a competing source of truth by default.

### Absorbed into release blocks

| Historical item | Release block |
|---|---|
| Per-identity keys; seat registry; credential hardening; auth | B1 |
| External occupant metadata; authorship identity | B2 |
| Certification default; Challenger death; stopped/timeout exits | B3 |
| Museum formalization; close/open gates; signoff/reject guard | B4 |
| Execution log; catches; operator inputs; review lifecycle; cycle IDs | B5 |
| Portable tenant; The Package; drift; backup; active-surface cleanup | B6 |
| Worker boot tuning and cross-vendor boot tests | B7 |
| Friction/behavioral comparison and burn-in evidence | B8 |
| Minimum onboarding and operator surface | B9 |
| Synthesis/case study/evidence package | B10 deliverables |

---

## 3. POST-1.0, HORIZON, AND WATCH LIST

### Post-1.0 unless promoted by a failed acceptance test

- S22 local inference node;
- large worker auto-spawn and broad chat-channel front doors;
- Dweller-as-standing-service and generalized queue ranking;
- branch-threaded multi-client farm;
- full commercial multi-tenancy;
- broad Governor visualization and convenience controls;
- Notarian product line;
- generalized autonomous operation across arbitrary domains;
- standalone Gemini corpus-standard validation;
- wide interface polish unrelated to B9 transfer.

### Watch during release tests; repair only if reproduced or release-relevant

- query-guard semicolons in literals;
- empty modal resume;
- console re-arm noise;
- farm model-string drift;
- billing-lapse error language;
- intake transient `Thinking...` state;
- optional session notes field;
- history-retention policy beyond normal Git history;
- VPS convenience items such as BRAVE key, apt Git, and direct TLS.

### Horizon — explicitly not 1.0

- lifetime ground truth;
- calibrated judges;
- break lane;
- cross-institution trustless verification;
- multi-lineage parallel seat ecology as a general platform.

---

## 4. CURRENT SINGLE NEXT ACTION

Finish the authenticated observations for **B0 — Establish the live release baseline**.

The repository/public half is recorded in `live/ONTINUITY_1_0_BASELINE.md`. Public `ontinuity.org` serves the current gate-and-contract homepage and Boundary De-Identifier. Railway MAIN/FARM revisions, box installed-file hashes, schema state, and live courier/model configuration still require authenticated evidence. The present ChatGPT Work surface could reach GitHub and the public site but not the Railway hostname/API; that limitation is recorded rather than treated as an Ontinuity outage. Run the already-existing reads from an allowed network surface and append the results; do not infer them from July documentation.

When B0 closes, select B1 and B3 as the first two build lanes. No other historical punch item outranks them.

---

## 5. WORK-BLOCK CLOSE FORMAT

Every block closes with:

- **Release condition**
- **Claim tested**
- **Evidence read**
- **Change made**
- **Test result**
- **New debt**
- **State left**
- **Next dependency**

This board is updated when evidence changes a dependency or disposition. It does not accumulate narrative folds; those remain in `agent_queue.md` and conversation records.
