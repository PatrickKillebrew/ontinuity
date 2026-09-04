# RELEASE BASELINE, WORKER RECOVERY, AND CHALLENGED RESEARCHER — 2026-09-04

**Form:** condensed decision-record. Operator rulings/directives are quoted verbatim where load-bearing; connective narration is condensed. Full-fidelity conversation remains operator-held in ChatGPT.

**Participants:** Patrick Killebrew (operator); `chatgpt-work:gpt-5.6-sol` (Control conversation and external Researcher occupant); OpenAI agent workers used for bounded B0/B1/B3/Governor work; `cerebras:gemma-4-31b` (Challenger); the standing Parietal and extraction roles configured on MAIN.

**Scope:** recover the whole Ontinuity institution rather than a code-only snapshot; establish the first authenticated Ontinuity 1.0 release baseline; preserve parallel B1, B3, and Governor candidates without confusing them with deployed state; and run a harder external-Researcher lap that produces real adversarial friction.

---

## WHY THE SESSION KEPT RETURNING TO B0

The first inventory was too shallow. It found the visible runtime and release backlog but did not initially carry the full worker doctrine, corpus-writing discipline, intake/design distinction, historical reversals, Shepherd, Governor lineage, and deploy-authority rulings into the baseline. The operator repeatedly rejected completion claims that outran that coverage:

> "The answer is always in the corpus."

> "Please quit blowing smoke up my ass and telling me that you've completed something when anyone can see that that is not the case."

The correction was not another summary pass. B0 was decomposed into exhaustive file coverage, semantic subsystem reviews, foundational-paper extraction, history-and-rulings reconstruction, corpus-continuity review, specifications lineage, and residual-omission closure. The resulting audit accounted for 226 tracked repository files and distinguished current authority, historical evidence, proposal-only material, deployed code, separately installed box code, and unrelated robotics material.

The authenticated B0 reporter then read Git, Railway MAIN/FARM, the box, schema, courier, role assignments, health, and public routes without changing state. Its first committed specimen returned `DRIFT`, not a manufactured clean bill of health. B0 landed on `main` as commit `7abadca` with the baseline report, JSON specimen, read-only reporter, tests, and board/handoff reconciliation. Observed FARM, box-file, and mailbox-lease drift was preserved for later B6 reconciliation rather than silently repaired.

## THE RECOVERED WHOLE

The full pass recovered a system that is complex in extent but simple in constitutional shape:

- **Intake mode:** a business owner describes a problem; the staged pipeline turns that record into a client-approved solution proposal and later implementation work, with a per-project corpus as the handoff mechanism.
- **Design/Control mode:** the operator and Control define a bounded problem and agreed outcome; Control converts it into mailbox work for scoped workers.
- **Worker institution:** workers claim tasks atomically, build within the contract, post proposals to `any_worker`, independently review each other's exact bytes, and preserve authorship transfer after correction.
- **Gated Researcher mode:** Researcher advances the objective inside the adversarial loop; Challenger, Parietal, deterministic execution checks, and the close gate constrain what may certify.
- **Corpus institution:** conversation records preserve operator-layer reasoning; the queue fold preserves built/learned/reversed history; current-state surfaces remain forward-facing; commits, receipts, sessions, mailbox records, and folds form the evidence joins.

The operator clarified that Intake and current Design work should not be collapsed into one flow. Intake remains real but is not the present build focus. Control owns the whole-goal context and creates bounded work; workers receive limited task context so they do not invent architecture from an overactive context.

## WORKER AUTHORITY AND THE MAILBOX

The operator rejected optional conformance language:

> "We are creating 'the way', not providing models different option and then hoping they choose the right one."

Mailbox lifecycle is therefore constitutional, not advisory. Durable work must enter the shared claim/proposal/review/signoff/acknowledgment path if it is to count as Ontinuity work or appear in Governor.

The recovered deploy invariant is:

1. Control and operator agree on what should be built and whether a clean result is authorized to land before dispatch.
2. A worker authors the candidate.
3. A different worker reviews the exact bytes.
4. A clean reviewer/signing seat may commit and deploy those exact signed bytes.
5. If the reviewer corrects the bytes, that reviewer becomes their author; the corrected bytes return to `any_worker` for a different review and signer.
6. No author deploys their own bytes.

This removes human byte-by-byte review as the scaling mechanism without removing operator authority over intent.

Agent workers exposed an observability problem. They could execute bounded parallel work inside the ChatGPT conversation, but their intermediate work was not visible to the operator in the way separate Claude windows had been. Missed checkpoints and apparently dormant workers made valid work feel theatrical. This reconfirmed Governor as justified infrastructure: it must render durable mailbox lifecycle and evidence, not run provider models or charge separate model API calls merely to display work.

Three Governor variants were found. A local candidate on `codex/governor-observability` at `5e3310d` extends the existing Governor rather than creating a provider-specific substitute. It remains a candidate: not reviewed, pushed, installed, or deployed during this close.

## RELEASE WORK PRESERVED WITHOUT OVERCLAIM

Three development lanes now exist beyond B0:

- **B1:** branch `codex/b1-scoped-identity`, tip `a31ffe1`. It contains a scoped capability-admission candidate and mailbox identity/claim enforcement. It is not yet accepted or deployed.
- **B3:** branch `codex/b3-fail-closed-completion`, pre-close tip `1bcea16`. It contains the B0 merge plus fail-closed persistence, structured failure reasons, empty-provider-output rejection, migrations, triggers, and museum tests. It is not independently reviewed, pushed, installed, or deployed.
- **Governor:** branch `codex/governor-observability`, tip `5e3310d`. It exposes worker lifecycle/punch state and improves historical punch parsing. It is not independently reviewed, pushed, installed, or deployed.

Branch existence proves work was preserved. It does not prove Ontinuity's live behavior changed.

## HARDER RESEARCHER LAP — REAL FRICTION

The operator wanted Control to experience the Researcher seat under actual Challenger pressure rather than pass another easy demonstration. Two September 4 sessions resulted.

Session `2026-09-04_18-32-59` ended `incomplete_model_dead` after one cycle. Write receipt `349` proves persistence of the failed attempt; it does not prove semantic success. No Challenge occurred.

Session `2026-09-04_18-55-18` completed after 11 cycles and persisted 13 turns and two artifacts under write receipt `350`. The task forced a recommendation about Ontinuity's deployment authority from live evidence rather than prose. The Researcher initially conflated a source-code conditional with proof of deployed behavior. At cycle 10 the Challenger issued a formal Challenge; Parietal returned `UPHOLD`. The Researcher retracted the unsupported inference, separated target constitutional policy from proven live state, rebuilt the answer, and the Challenger accepted the corrected deliverable at cycle 11.

This was the first OpenAI-seat lap in this arc where the harness materially changed the answer rather than merely accepting it:

`unsupported inference -> Challenge -> UPHOLD -> retraction -> corrected bounded claim -> acceptance`

That supports a narrow statement: in this specimen, Ontinuity produced better epistemic behavior than the Researcher's initial unharnessed answer would have produced. It does not support general superiority over a frontier model. B8 must freeze matched tasks, sources, models, adjudication rules, and metrics; preserve unfavorable results; and use blinded human adjudication where practical.

## DEFECTS REVEALED BY THE LAP

The session's durable record exposed three evidence defects:

- the `challenge_events` row recorded `UPHOLD` but left `challenged_claim` and `grounds` empty;
- the session recorded one Challenge and one uphold while `adversarial_catch_count` remained zero;
- current repository schema defines `end_reason`, but the deployed session table inspected during the run did not contain it.

These belong to existing release work: deployed `end_reason` is B3; adversarial event/content capture and evidence joins are B5. The valid database query also triggered the naive SQL guard because the column name `created_at` contains the substring `create`; this remains a watch item unless a release-relevant failure reproduces it.

## TRAINING PRIORS VERSUS PROJECT PROCEDURE

During live access, Control reached first for a Python HTTP client even though the corpus explicitly documents a working `curl` path through the Railway vault and courier. That deviation caused avoidable failure and repeated an established class: generic technical competence substituted for project-specific operating truth.

The operator identified the broader problem:

> "Overcoming your inclination toward training data is a mountain that we need to overcome for all of the different models that'll use Ontinuity in the future."

The correction is mechanical. A boot/admission gate should require retrieval and reproduction of the exact documented procedure before granting operational authority. Alternative approaches must be labeled experiments and may not silently replace a known project path. Existing B4 bootstrap/must-refuse work and the instruction-wording audit own this requirement.

## WHY THE CORPUS CLOSE MATTERS

The operator restated the load-bearing reason for the corpus: Ontinuity's history is not decorative documentation. It is the durable institutional memory that allowed another provider to inherit the office and reason with decisions, reversals, and failure history unavailable in model weights.

> "Ontinuity is nothing without the history as recorded in its corpus."

This record preserves the repeated B0 corrections and the failed Researcher attempt alongside successful work. Erasing either would make the next seat falsely confident and force it to rediscover why the rules exist.

## STATE LEFT

- `origin/main` contains the authenticated B0 baseline at `7abadca`; its result is `DRIFT`.
- Current worktree was `codex/b3-fail-closed-completion` at `1bcea16` before this close.
- B1, B3, and Governor are separate local candidates; none is represented as live.
- B3 museum suite passes locally but still requires independent exact-byte review, endpoint integration, box installation, controlled deployment, and live acceptance.
- September 4 session `2026-09-04_18-55-18` is a useful Challenge specimen for B3/B5/B8; it is not itself B8.
- No runtime code, role configuration, Railway deployment, box installation, or database was changed by the Researcher lap or this narrative close.
- Manual and worker-contract mechanics did not change in this arc; no packet rewrite is claimed.
- Credentials and operator IP information are omitted.
- Final live-state verification was attempted through the documented authenticated `curl` path, but this ChatGPT execution environment canceled the outbound request before an HTTP exchange and disallowed escalation. MAIN/FARM idle and mailbox-clean state are therefore `UNKNOWN` at close—not inferred from the earlier successful session. The last observed MAIN state after session `2026-09-04_18-55-18` was idle, but it is not substituted for a fresh close check.

## NEXT

First rerun the documented authenticated curl close-state checks from a network-capable seat. If the engines are idle and no orphaned mailbox claim exists, send the exact B3 post-close branch tip to an independent non-author seat for review. If it rejects or edits the bytes, transfer authorship and re-review. If it signs the exact bytes cleanly, that signer may proceed through the already-authorized install/deploy path and run the live B3 museum. Preserve B1 and Governor candidates unchanged until their own independent review blocks.

**Cross-references:** B0 commit `7abadca`; B3 pre-close tip `1bcea16`; B1 candidate `a31ffe1`; Governor candidate `5e3310d`; sessions `2026-09-04_18-32-59` and `2026-09-04_18-55-18`; write receipts `349` and `350`; `live/ONTINUITY_1_0_BASELINE.md`; `live/ONTINUITY_1_0_BOARD.md`; `live/B3_FAIL_CLOSED_COMPLETION.md`; this close's queue fold and commit.
