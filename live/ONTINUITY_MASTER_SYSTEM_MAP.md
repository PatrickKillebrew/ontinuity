# ONTINUITY — MASTER SYSTEM MAP
*The single comprehensive skeleton. Built from exhaustive corpus reads + live DB/engine inspection.
Living document — every discovery goes HERE, not in scattered files. Status of each part marked:
[BUILT+LIVE] / [BUILT] / [PARTIAL] / [OPEN].*

════════════════════════════════════════════════════════════════
## 0. WHAT ONTINUITY IS (one paragraph)
A per-operator system where reliability comes from the HARNESS, not the model. A model in a seat must
RETRIEVE from the record (never recall from weights), grounds every claim in the corpus, and cannot close
a session until output matches a contract frozen before work began. Memory persists across sessions and
platforms so re-entering complex work needs no reconstruction. It runs as ONE engine (Railway) + ONE box
(Hetzner) per operator, serving that operator's many isolated projects.

════════════════════════════════════════════════════════════════
## 1. THE TWO FRONT DOORS (input modes) — THIS IS THE TOP-LEVEL STRUCTURE

### MODE A — INTAKE / DISCOVERY MODE  [BUILT+LIVE]  (Katie's path)
**Front door:** the intake website (`intake.html` / `intake11.html`), an AI-driven questionnaire.
**Purpose:** onboard a NEW problem/client — turn a person's business problem into structured data → solution.
**Who:** a client/respondent who has a problem, not the operator. (Katie = Seniors Helping Seniors.)
**Mechanics:**
- `/intake_chat` — runs a 4-phase discovery interview (`prompts/intake_system.txt`, own provider key):
  - PHASE 1 ORIENTATION: understand the business first (no assumptions), 2-3 exchanges, warm/natural.
  - PHASE 2 STRUCTURED INTERVIEW: 6 areas (organization / information / finding / connections /
    people+tools / where-it-hurts). One question per response. Reflect back. One follow-up per thread.
    ~18-22 exchanges, ~15 min. Examples fitted to THEIR business (galvanizing plant ≠ home-care franchise).
  - PHASE 3 REVIEW: read back 5-8 points, let them correct (their corrections are authoritative).
  - PHASE 4 CLOSE: emit `[WORKSPACE_STATE]` JSON block (business/information/finding/connections/
    people_and_tools/pain/additional_context/intake_quality).
- `/intake_capture` — append-only checkpoint of transcript → PRIVATE repo `ontinuity-intake-data`
  (via `INTAKE_GITHUB_TOKEN`). Server-authoritative completion: presence of [WORKSPACE_STATE] = closed.
- `/intake_resume` — returning participant resumes exact transcript.
- Then `seed_tenant` creates the user+project rows; project memory accumulates from there.
**OPEN SEAM:** the bridge from captured intake WORKSPACE_STATE → the seeded project's FIRST Knowtext
is the one piece not yet traced. (Next read.)

### MODE B — DIRECT SESSION MODE  (personal / design-planning mode)  (what operator+Claude do now)
**Front door:** `/agent/start` (mailbox-key auth) OR the operator working directly with a seat.
**Purpose:** the operator does ongoing work — design, planning, building, thinking — WITH memory continuity.
**Who:** the operator (you), working with a Control/Researcher seat.
**Mechanics:**
- `/agent/start` {objective, project_id, branch, start_fresh} — mailbox-key auth ("initiating work and
  doing work are the same trust grade; judging work is NOT — the agent may start what it's audited on,
  never certify itself"). Spawns `pre_session_then_start`.
- Session runs the adversarial cycle (§3), accumulates transcript/challenges/results.
- `/agent/queue` + `/agent/queue_update` — the contract-queue loop: sessions amend the work queue ON THE
  RECORD (GitHub commit w/ provenance); next contract authored against amended list. (AGENT_QUEUE_PATH is
  UNWATCHED so a queue commit never triggers a deploy that kills its own session.)
- At close: Knowtext extraction → persisted (§2).

**KEY DISTINCTION (operator's framing, 2026):** Mode A's ONLY front door is the intake. Mode B is the
conversational/design door. Both feed the SAME memory system but enter differently.

════════════════════════════════════════════════════════════════
## 2. THE MEMORY SYSTEM  [BUILT+LIVE: 357 knowtext_versions, 328 sessions, 3 projects, 2 users]

### Layers (store → holds → retrieval):
1. **Git corpus** (`live/`) — the system's operating record (paradigm/manual/specs). Via `read_repo`,
   AUTHORITATIVE source (not raw CDN — stale). [BUILT+LIVE]
2. **Relational DB** (24 tables, on box) — structured per-user memory. Via `/api/query` through courier. [BUILT+LIVE]
   - `users` (plan: personal/free/pro/team, feature_flags) — product tiers schematized
   - `projects` (per user) → `branches` → `session_series` → `sessions` → `session_transcripts`
   - `knowtext_versions` — Knowtext IN the DB, versioned, 7 fields as columns
   - `established_results` (ESTABLISHED/PROVISIONAL) — provenance
   - `intake_sessions` — the Mode-A entry
   - `storage_configs` — per-user backend: local_workspace/s3/r2/supabase/postgres/custom [schema BUILT, 0 rows]
   - B5-P evidence: challenge_events, retraction_events, model_call_envelopes, session_reproducibility_manifests
   - write_receipts, operations_ledger, model_registry, artifacts
3. **Knowtext (distilled)** — 7 fields (Identity, Active Frameworks, Open Questions, Valence Mapping,
   Delta Log, Correction History, Climate Notes) + 4 modes (Research/Creative/Business/Personal).
   Update = extraction prompt at close ("write only what CHANGED; if restating, delete"). Test of good
   memory: a NEW instance reading it continues without the transcript. [BUILT+LIVE]

### ISOLATION (the answer to per-user vs multi-tenant):
`session_knowtext_path()` — STRUCTURAL isolation, verbatim comment: "no parameter lets a session name
another project's file." A session can ONLY write its own project/branch Knowtext. Cross-project write is
MECHANICALLY IMPOSSIBLE. → Multi-PROJECT-on-one-box is safe for one trusted operator. [BUILT+LIVE]

════════════════════════════════════════════════════════════════
## 3. THE COGNITIVE / ADVERSARIAL ENGINE (the "reliable output" pillar)  [BUILT+LIVE]
**Five model roles** (pluggable, provider auto-detected from URL: anthropic/gemini/openai-compatible):
model_a, model_b, model_c, **projenius** (project-level synthesis), **parietal** (navigate/adjudicate).
Config: dashboard override → vault env (`<ROLE>_API_KEY/_URL/_MODEL`) → shared PROVIDER_API_KEY. Keys are
operator-provisioned env, NEVER in repo. (= the "bring your own keys" path.)

**The cycle** (from active_session): frozen_contract set before work; Researcher produces; challenge_events
tracked; rejected_claims INJECTED into Researcher system prompt each cycle (can't repeat a ruled-against
claim); execution_log = ground truth for fabrication detection (FABRICATED = no entry exists; MISREPORTED =
entry exists, result misreported). no_progress/malformed/claim_warning counters guard loops.
This is Tetraform. Predictable output feeds the 4-stage solution machine.

════════════════════════════════════════════════════════════════
## 4. RETRIEVAL MECHANICS (why the box+hands are essential)  [BUILT+LIVE]
- A seat CANNOT recall memory from weights (fabrication). It must RETRIEVE.
- Path: seat → engine relay-courier (POST {ENGINE}/diag/op/<name> + diag key) → box /op/<name> (verbatim).
  Sandbox seats can't reach box directly (firewall by design); courier is the ONLY path.
- 19-op allowlist: read_journal, restart_workspace, register_egress, mailbox_send/fetch/ack/peek/reclaim/
  purge, write_file, commit_self, read_file, commit_file, you_there, read_repo, bootstrap_gate, deploy,
  seed_tenant, backup_db.
- **bootstrap gate** forces retrieval: a seat must reproduce operating invariants FROM THE RECORD before
  acting (CHECK 6 MECHANICS). Retrieval-not-recall is MECHANICALLY ENFORCED. (5 more checks: MANUAL, QUEUE,
  CORPUS, HANDS, ENGINE.)

════════════════════════════════════════════════════════════════
## 5. INFRASTRUCTURE (per operator)  [BUILT+LIVE for operator's instance]
- **ENGINE** (Railway): hosts courier/relay + role-provider env vars. 2 services: web(MAIN), ontinuity-farm(FARM).
- **BOX** (Hetzner): gunicorn 0.0.0.0:5001, key-auth at app layer. Where mailbox + every /op/* RUNS.
- Repo-commit ≠ box-install (TWO steps: write_file + restart). Per-tenant this stays true.
- Current recovered state: MAIN=5640170 (pre-GPT+B5-P, no B1), FARM=f9696c49, 19-op diag-key, boots oriented:true.

════════════════════════════════════════════════════════════════
## 6. PROVISIONING (onboarding a user)  [BUILT+LIVE — proven with Katie]
- `seed_tenant` op: bounded, idempotent get-or-create user+project, ledgered, NO arbitrary SQL.
- PROVEN: Katie Wasserman (pro) seeded 2026-06-15, project "SHS Emergency Shift-Coverage Tool", idempotency verified.

════════════════════════════════════════════════════════════════
## 7. THE PRODUCT SPEC (already written — PUNCH_LIST line 138, operator ruling 2026-07-19)
"PORTABLE ONTINUITY TENANT — package the whole engine so another operator gets their own instance."
- Target: Cornel (AZZ safety leader). Value: "resuming without re-establishing context."
- "His version has to use the exact same engine... My engine is THE ENGINE. We have to duplicate that."
- THE MAGIC: "the BOOT SEQUENCE with unfabricatable returns" (not the documents). 4 load-bearing parts:
  fetch-and-verify framing / __probe__ hands test (403 echoes live allowlist, unrecitable) / hard gate on
  5 reads requiring a real line back / failure paths documented upstream.
- HONEST CEILING: boot conditions but doesn't permanently hold (seat drifts hours later). Needs OPEN gate
  + CLOSE gate + assertion rule in between.
- Model: PER-INDIVIDUAL instance (own Railway+VPS+key). Keep multi-PROJECT schema. Discard B1 multi-tenant AUTH.

════════════════════════════════════════════════════════════════
## 8. OPEN ITEMS (genuinely unresolved — from the corpus, not invented)
- [OPEN] Intake WORKSPACE_STATE → first Knowtext bridge (Mode A onboarding seam). NEXT READ.
- [OPEN] Per-tenant credential provisioning (shared-diag-key ceiling worsens with N tenants). The ONE B1
  hygiene lesson worth keeping: per-instance keys.
- [OPEN] What a tenant's __probe__ returns before their allowlist exists (bootstrap chicken-egg).
- [OPEN] Corpus repo: theirs vs a directory in a shared one (isolation model for the git layer).
- [OPEN] The configuration/install runbook (operator-named deliverable).
- [PARTIAL] storage_configs + established_results wiring (schema exists, 0 rows — fresh-install provisioning may be partial).

════════════════════════════════════════════════════════════════
## 9. STILL TO MAP (before packaging — do not skip)
- [ ] The intake→Knowtext bridge (§1 Mode A seam, §8)
- [ ] The 4-stage solution machine (how Mode A intake data → solution proposal) — read four_stage_pipeline
- [ ] Projenius (project-level consciousness) — what it does, §3
- [ ] Parietal (navigate/adjudicate) — the adjudication role
- [ ] The close ritual / session persistence full path (transcript+knowtext+established_results write)
- [ ] The prompts/ set (18 files — the seat brains: model_a/b/c, projenius, parietal, intake)
- [ ] project-corpus-standard/template — the per-project corpus structure
- [ ] Governor (observability) — what the operator sees

════════════════════════════════════════════════════════════════
## 10. CURRENT SYSTEM STATE (folded from recovery work — was a stray doc)
**Recovered to pre-GPT + B5-P hybrid, verified boots oriented:true.**
- MAIN engine = commit `5640170` (pre-GPT `9a7eac2a` + B5-P evidence layer, ZERO B1). blob 35502fd0.
- FARM engine = commit `f9696c49` (pre-GPT worker engine).
- 19-op diag-key hands work; 328 sessions intact; Control boots oriented:true (all 6 checks pass).
- Box files match repo (`0ef62d7:live/box/`); box gate reconciled to 19 ops (installed via write_file+restart).
- Manual rolled back to 19-op pre-GPT version.
- B1 authorization machinery DISCARDED but preserved in bundle `e15f5f46` + git commits for reference.
- ipad_keyboard tool restored (GPT had deleted it).

**Recovery mechanism (reusable):** Railway GraphQL `serviceInstanceDeploy` mutation, endpoint
`https://backboard.railway.com/graphql/v2`, header `Project-Access-Token:` (NOT Bearer), project
`a8dea5f4-...`, env `6ff341f9-...`, MAIN service `72b20f74-...`, FARM service `ae72de62-...`. Deploy pulls
the specified commit. Verify via /diag/version blob match + diag-key __probe__ returning 19 ops.

════════════════════════════════════════════════════════════════
## 11. GPT B-WORK: KEEP / DISCARD (folded from evaluation — was a stray doc)
**KEEP:** B5-P evidence preservation (auditability spine, now live on MAIN via 5640170); db.py transactions;
control_loop response-validation hardening; release_baseline.py (drift-audit tool); B0 baseline (historical);
the 2026-09-03 cross-vendor succession record (proves engine is model-agnostic); egress/curl discipline (as docs).
**RESTORE (GPT deleted):** ipad_keyboard.py + CONTRACT + CORPUS + templates/kb.html [DONE].
**DISCARD (multi-tenant AUTH machinery, wrong for per-individual):** capability_auth.py, trusted_deploy.py,
B1 transport envelope, v2 HTTPS protocol, capability/b1 test suites, both B1 manifests, restart_burnin op,
20-op manual language, the ONTINUITY_1_0_BOARD/COMPLETION_PLAN (keep as history not active).
**Net:** ~30% of the week was genuine value (matches GPT's own estimate); most is additive, cherry-picked onto clean base.
**Prior fix-specs (cyclenum/query_guard/deploy_drift/farmfix/erl/signoff) are PRE-GPT — already yours, already in foundation.**

════════════════════════════════════════════════════════════════
## 12. FILE COVERAGE CHECKLIST (the "done" instrument) — see companion COVERAGE file
Mapping is DONE when: every file SUMMARIZED or READ-not-skeletal; §9 all checked; every [OPEN] resolved
or confirmed-open; both front-door flows trace end-to-end with no [OPEN] critical-path seam; a cold reader
could understand the system without the source.
**Running total updated each stage. Start: 26/252 (10%).**

STAGE PLAN:
- S0 Consolidate + instrument [THIS STAGE — DONE]
- S1 Core doctrine (live/ root, 38) — paradigm/rubric/manual/state/handoff/board/punch/queue
- S2 Prompts (18) — seat brains
- S3 Specs (30) — mechanics
- S4 Engine+box code (12) — app.py, box, db, governor, control_loop, shepherd
- S5 Conversations (21) + Sessions (18) — historical record, load-bearing decisions only
- S6 Everything else (fixes/tools/corpus-std/templates/misc/audits/archive/experiment/tests/root-other)
- SFINAL Verify done: trace both flows, resolve [OPEN]s, final coverage report

════════════════════════════════════════════════════════════════
## 13. STAGE 1 FINDINGS — CORE DOCTRINE (packaging-relevant only)

### [PACKAGING-CRITICAL] Worker docs are STALE (B1-era)
`WORKER_MANUAL.md` (12 B1 markers), `WORKER_BOOT_PACKET.md` (10), `WORKER_QUICKBOOT.md` (2) all describe
the DISCARDED B1 admission flow (ADMISSION panel, signed capability, HTTP 428, bearer grant). The recovered
pre-GPT engine uses the DIRECT DIAG-KEY path, not capability admission. → These docs describe a system a
new user WON'T have. For packaging: roll worker docs back to pre-GPT (`9a7eac2a` versions exist) OR mark
B1-era. SAME issue class as the manual/gate we already fixed. [ACTION ITEM for packaging, not now]

### [PACKAGING-CRITICAL] PROJECT_CORPUS_RUBRIC.md — the per-project corpus standard
THE answer to "how does a new user's project get structured." Generalizes Ontinuity's own conventions to
ANY project, MINUS the engine machinery. Key content:
- **SEPARATION RULE:** engine = SHARED infrastructure (any project uses it to do work); corpus = PER-PROJECT.
  Building project X with the engine lands X's record in X's corpus, NEVER in Ontinuity's. "The engine is the
  tool; the project corpus is the workpiece." → This is the isolation model for the PRODUCT: one shared engine
  per operator, many per-project corpora.
- **STANDARD FILE TAXONOMY** (every project corpus has from day 1): CURRENT_STATE.md (boot doc, no dead history),
  PROBLEM_DEFINITION.md (user's own words from intake — the ground-truth authority), ROADMAP.md (with LOCKED
  DECISIONS fenced), PUNCH_LIST.md, TOOL_DESIGN_STATE.md, sessions/ (PROCESS record — the slot SHS lacked),
  mini_corpus/agent_queue (fold: built/learned/REVERSED).
- **TWO RITUALS generalized:** OPEN (read CURRENT_STATE → PROBLEM_DEFINITION → search fold → follow refs;
  "recall is not retrieval"); CLOSE (reconcile punch list → capture reasoning arc → write fold → update CURRENT_STATE).
- Names the SHS/Katie pain as WHY it exists: "a corpus that grew ad hoc... current-state reconstructed mid-session."
- Introduces **Dynacology** [future]: project corpora as callable specialists in a registry; requires shared shape.

### [CONFIRMS] ONTINUITY_1_0_BASELINE.md = the B0 human-readable baseline (RC-7). Already have B0 JSON. DRIFT confirmed.

### [DEFER to their stages] db.py, workspace_db_endpoint.py, ontinuity_loop.py, ods_phase1_v5.py, camera_cte.py,
shepherd.py, control_loop.py, mission_state.py, shepherd_alert.py = S4 code. B1 manifests = discarded (§11).
horizons.md/present_horizon.md/POST_1_0_COURIER_EVOLUTION.md = future-horizon, not v1-packaging-relevant [READ-not-skeletal candidates].
builder_handoff_latest/june7 = handoff snapshots, historical.

════════════════════════════════════════════════════════════════
## 14. STAGE 2 FINDINGS — THE SEAT BRAINS (prompts/)

### The FIVE ROLES, precisely (all pluggable models, config'd per role):
1. **Model A — RESEARCHER** (model_a_system.txt): primary work toward objective. Must tag ASSUMED vs
   established; causal claims are highest-risk (need cited evidence or ASSUMED marker). Ends every response
   with exactly one [CYCLE_STATUS] tag (CONTINUE/ALIGNMENT_NEEDED/CHECKPOINT/SESSION_END/SEARCH_REQUEST/
   CODE_TEST/DB_QUERY). **Tag fabrication forbidden** — a tag only fires when it literally appears; claiming
   an un-injected result = fabrication = Signal 4 override. This is the anti-fabrication core.
2. **Model B — CHALLENGER** (model_b_system.txt): adversarial review of A each cycle. **DELIBERATELY A
   DIFFERENT TRAINING LINEAGE than A** — "you share different blind spots... it is your primary value."
   THE reliability mechanism, in one line. Verifies A's tool-results are actually injected blocks, not prose.
   Reports structured session-state assessment (engine reads it to continue/end/escalate).
3. **Model C — FRICTION** (model_c_system.txt): out-of-band health signal 0-4 (BAFS) + one-line reason.
   Never enters the A/B conversation — ambient background signal in their context. Signal 4 = override.
4. **PARIETAL** (parietal_system.txt): session-level consciousness, watches from OUTSIDE the working
   conversation. Navigates, adjudicates B's CHALLENGE tags, distills results. [role read; resolve variant = parietal_resolve.txt]
5. **PROJENIUS** (projenius_system.txt): **THE MEMORY ENGINE.** Project-level consciousness across ALL
   sessions/branches/time. Called at project BOUNDARIES (before/after sessions), never inside the loop.
   4 functions incl. **ORIENT** (reviews established results, feeds Parietal before session) and **DISTILL**
   (= the Knowtext extraction: reads transcript + current Knowtext + ledger, writes DELTA into the 7 fields).

### [PACKAGING-CRITICAL] Memory-writing is a MODEL ROLE, not a script.
Knowtext extraction = Projenius DISTILL. So a new user's install needs Projenius configured (a model +
key) for memory to self-update. Memory continuity depends on the Projenius seat, not just a text template.
The 5 roles each need a model+key at install → the "bring your own keys" config has FIVE slots
(model_a/b/c/projenius/parietal), and B SHOULD be a different lineage than A for the reliability to hold.

### [PACKAGING NOTE] Minimal-memory-only product could run FEWER roles:
Pure memory continuity = Projenius (DISTILL/ORIENT) + one working model. The full adversarial board
(A+B+C+Parietal) is the RELIABILITY layer. Confirms earlier: memory-first product needs Projenius + a
working seat; the board is the next layer up. (But operator said full board non-negotiable for predictable
4-stage output — so that's a v1.1 decision, noted.)

### Prompt file versions: canonical = un-suffixed (model_a_system.txt, parietal_system.txt, projenius_system.txt).
Suffixed (11/222/1/2/ORIGINAL) are version history [READ-not-skeletal]. knowtext_extraction_prompt.txt =
the standalone extraction (matches Projenius DISTILL). intake_system.txt already covered (§1 Mode A).

════════════════════════════════════════════════════════════════
## 15. STAGE 3 FINDINGS — SPECS (live/specs/)

### [PACKAGING-CRITICAL INSIGHT] Most specs are PROPOSE-ONLY / DESIGN-ONLY — NOT live features.
A fresh reader (or a packaged user) must NOT mistake these for built capabilities. The specs folder is
largely a PROPOSAL BACKLOG, not a feature list. This matters for packaging: the "system" a new user gets
is the LIVE engine + the BUILT ops, NOT the specs' aspirations. Classification:

**DISCARDED (B1 machinery — do not ship):** trusted_deploy_protocol, signoff_gate_v2_spec, signoff_keys,
signoff_provenance_spec, per_identity_keys, gated_session_substrate, ontinuity_https_protocol,
scoped_operations_spec, signoff_deploychain. (The credential-hygiene IDEA from per_identity_keys is the one
lesson worth keeping — see §7 open items.)

**PRE-GPT FIXES (already in foundation, already live):** deploy_drift_check, farmfix_verify, query_guard_fix,
cyclenum_fix. (These are yours, pre-GPT. Confirmed earlier.)

**PROPOSE-ONLY / not built (future, not v1):** oracle.md (a standing corpus-grounded retrieval SERVICE —
guessing-squelch as a pollable seat; would need a 3rd Railway process; PROPOSE-ONLY), coordinator.md,
you_there_longpoll, control_you_there_loop, punch_reconcile, autonomous_migration(+provenance),
governor_adjudicator_spec, governor_punchlist_panel_spec, mailbox_threat_audit (an audit, not a build).

**BUILT despite spec saying propose-only (status lag):** agent_handoff.md — the route IS wired in app.py
(/agent/handoff). One-call resumption snapshot: engines(main+farm active_session) + queue_head + open_turns
in ONE keyed call. Reuses diag-key auth. PACKAGING-RELEVANT: a new user's cold-boot uses this for one-call orientation.

### [PACKAGING-CRITICAL] ERL (established_results) is EMPTY and needs Projenius — confirms §14.
erl_decision.md diagnoses: established_results = 0 rows because (1) Projenius unconfigured on live engine
(has_projenius=False, SYNTHESIZE no-ops) and (2) no persist path (zero INSERT refs in app.py — the "ledger
updated" socket emit is a silent-success illusion). THE FOLDS (agent_queue + PUNCH_LIST) are the WORKING ERL
by hand today. → For packaging: structured cross-session memory (confidence, confirmation_count, retraction
provenance) requires Projenius configured + a parser/INSERT spliced. Until then, memory = the prose folds
(which DO work). DECISION for packaging: Option A (wire structured persistence, needs Projenius provider) vs
Option B (keep fold-carried). [OPEN — packaging decision]

### Already-covered specs (§ earlier): verified_bootstrap_gate, close_ritual_gate, conversation_fts,
four_stage_pipeline, coordinator_worker_multiseat.

════════════════════════════════════════════════════════════════
## 16. STAGE 4 FINDINGS — ENGINE + BOX CODE

### THE BOX SURFACE (two files serve everything on Hetzner):
**file_server.py** (70KB) — the box's main HTTP server. Beyond the courier, it IS the workspace:
- Workspace filesystem: /read /write /run /rollback /history /manifest /search /audit /log
- Projects: /projects (GET/POST), /projects/switch — the box tracks the active project
- /settings, /status, /register_egress, and the Governor (/governor, /governor/data, /governor/punchlist)
- The /op/ courier ops it natively serves: read_journal, restart_workspace, restart_burnin
- Has its OWN /rollback + /history (change-tracked file edits) — the workspace is versioned.
**box_ops.py** (44KB) — the blueprint adding the rest of the /op/ courier handlers: write_file, commit_self,
read_file, commit_file, backup_db, read_repo, bootstrap_gate, deploy. (op_deploy here is the B1 version —
requires trusted_deploy.validate_request; the pre-GPT engine deploys control-side via Railway GraphQL instead.)
**seat_mailbox.py** (42KB) — the coordination layer: mailbox_send/fetch/ack/peek/purge/reclaim + you_there
(long-poll). Atomic claim+lease. `_noself_predicate` (a seat can't claim/review its own work), `_authed_identity`,
`_trusted_seat`, ledger. THE multi-seat coordination substrate. (mailbox = SQLite table on the box.)

### THE ENGINE DB SURFACE (workspace_db_endpoint.py, 26KB):
Routes: /api/query (SQL SELECT), /api/session (POST — receives a completed session's data), /api/ledger,
/api/project_state, /api/behavioral_corpus, /api/health.

### [RESOLVES OPEN ITEM] Fresh-user auto-provisioning IS BUILT.
`_get_or_create_user(db)` — returns first user OR creates default "Workspace User" (personal plan).
`_get_or_create_project(db, user_id, name, branch)` — find-or-create project + branch.
These fire automatically in /api/session when a session's data arrives. → A fresh install auto-creates the
user + project on first session; NO manual step. (Earlier §8 flagged this as maybe-partial; it is BUILT.)
`_register_models` auto-maps model strings → providers (anthropic/openai/meta/alibaba/google/etc).

### [PACKAGING NOTE — repo hygiene] The repo contains NON-Ontinuity code:
- **ontinuity_loop.py** (16KB) is NOT the cognitive loop — it's the **ODS (Ontinuity Driving System)**
  autonomous-driving loop (EventState/lidar/deep+near horizon). A DIFFERENT project living in the repo.
- **ods_phase1_v5.py, camera_cte.py, mission_state.py, battery.json** — also ODS.
- **laptop_seat.py** — RETIRED stub ("Keyboard Helper transferred to separate private project before B1").
→ For a clean packaged product, the ODS files + retired stubs should be excluded (they're separate projects
sharing the repo). PACKAGING: define what's Ontinuity-platform vs what's other-projects-in-the-same-repo.

### control_loop.py / shepherd.py / shepherd_alert.py — worker orchestration helpers (control-side loop,
worker heartbeat/alerting). control_loop got GPT's response-validation hardening (kept, §11).

════════════════════════════════════════════════════════════════
## 17. STAGE 5 FINDINGS — CONVERSATIONS + SESSIONS
(These records are FAR more than process narrative — they are the primary source for architectural
decisions, operator rulings, and system genesis. Many load-bearing facts exist ONLY here.)

### CONVENTION.md: the meta-rule for how records work
Four rules: (1) REDACTION MANDATORY (public repo, no keys ever); (2) FORM DECLARED (verbatim/condensed/
decision-record); (3) LINEAGE HONEST (operator name; agent as HARNESS:MODEL); (4) CROSS-REFERENCE
(conversation → decision → commit → receipt). The conversation record is the "operator layer" — where
direction is set, fabrications are caught, STOPs authorized, errata originate. Receipts capture the work;
conversation records close the provenance loop.

### CHRONOLOGICAL RECORD OF KEY DISCOVERIES / RULINGS (what the system IS grounded here)

**2026-06-07 — The Morning Proof Cycles.** GENESIS RECORD. Five autonomous break/fix cycles in 2 hours
(vs 5-6 cycles/12hrs two days prior). Proven: vault, gate kind-matching, causal-claim discipline, deadlock-
escape endpoint, view-state truthfulness. The session proved the deadlock was UNSTOPPABLE (no bounce
escalation, no STOP control); resolved by operator-authorized restart. The system deciding its own queue
head ("Dweller lap 3") established the precedent. The operator closed the provenance loop with this record.

**2026-06-08 — Burn-in, audit, break/fix.** Constitutional amendment: SAFE-class schema changes =
autonomous-eligible; DESTRUCTIVE/AMBIGUOUS = operator per-instance always. 203-cycle counted burn-in
complete. Governor monitor went live. Wait-orphan ROOT fix (90s autonomous modal timeout). First AUDIT:
21 receipts, 18 clean, 3 findings — un-instrumented death-exit writing 'complete', execution-log never
persisted, adversarial-catch left no durable mark. Fix #2 (execution persistence) and Fix #3 (catch marker)
produced but not deployed yet. A seat JUMPED a review gate (deployed ahead of review) — origin of the
self-enforcing sign-off gate item.

**2026-06-09 — Deploys + design block.** HARNESS THESIS stated verbatim, now canonical: "The harness
does not ask a model to comply — it makes compliance the only path through. Gates are deterministic
geometry; a model cannot talk or assert its way past them. Failure is legible, not silent... Trust stops
being a property of the model and becomes a property of having passed the harness (alignment-by-architecture)."
Governor: records sign-off, does NOT trigger deploys. Tiering: classifier PROPOSES, operator may escalate
never silently de-escalate. SEPARATION OF DUTIES: PREMATURE as a blanket solo-operator rule ("no untrusted
party yet = pure overhead"). PUBLIC EXPOSURE FOUND: ontinuity.org "Begin Session" button wired directly
to unauthenticated MAIN since April — anyone could start sessions, burn credits, write corpus, all UNLOGGED.
Fixed by disabling CTAs (7477ce5d). RESIDUAL: the engine URL itself was still public.

**2026-06-10 — Migration, courier, first mailbox seat.** Relay courier built (f295e2f). First mailbox-seat
session — the harness gated the CONTROL SEAT'S OWN CLAIMS (forced a real DB_QUERY; causal-claim discipline
held). FABRICATIONS CAUGHT this session: proposed FARM deploy for box hands (FARM is burn-in, not a seat);
declared "no authenticated write path" without checking credential files; invented a "separate worker seat";
found hardcoded PAT in push_to_github.py. Key lesson: FARM ≠ operator seat.

**2026-06-11/12 — Roster hygiene, demo tenancy.** WORKER BOOT PACKET DESIGN RULE: packet contains ZERO
task content — work comes from mailbox at STEP 4, never the boot text. Keys travel via LLaves file.
CLOSE-RITUAL GATE first named: "a discipline that's established then silently stops = the same class as
every silent-failure defect." INDEPENDENTLY ARRIVED AT TWICE (here + 06-14) — the strongest-supported
conclusion in the corpus. STILL BANKED at this point. DEMO STRATEGY: show the worker pipeline + adversarial
loop output on a SHAPED problem; one airtight path, dry run first, want information not applause.
PROTO-TENANCY: the ?k= capture link captures to the private intake-data repo but creates NO corpus-side
tenant — tenancy still proto. ORIGIN OF SHS PROJECT: operator "We can create a link for my sister to
test though. Her business is Seniors Helping Seniors." → Katie becomes the first product test.

**2026-06-13 — Isotest sessions (empirical backing for the pipeline).** Four self-contained sessions
proving the pipeline end-to-end: (1) gate REJECTED an ungrounded "21" claim — fabrication-detection
firing on the control seat itself; (2) DB_QUERY correct form established (SQL on QUERY: line → result
injects → cite from evidence → gate accepts — THE GROUNDED CLAIM LOOP); (3) Projenius DISTILL fires
at close (proved); (4) ERL bug isolated — Projenius fires but output lacks RESULT: block, so table
never writes. These sessions are the empirical backing for the four-stage pipeline's trust claims.

**2026-06-13/14 — Senior-care product design + pipeline.** THE FIRST PRODUCT OFF THE ONTINUITY FACTORY.
SHS emergency-coverage matcher: availability by ASKING, not storing. Two code layers: foundation snapshot
(scheduled availability-poll texts; non-reply = signal) + emergency matcher (code search → text top N →
who replies resolves). AI only upstream (the worker pipeline builds it; drift-repair heals it) and in year-two
insight layer — NEVER in live coverage decisions (human-in-the-loop). Self-healing via drift-detect + worker
build + peer review + control deploy (same pipeline as software). FOUR-STAGE PIPELINE STITCHED THIS SESSION:
intake→problem-def→decompose→proposal, each a Tetraform session writing provenance-tagged output to a
per-project mini-corpus; final stage composes from the chain. CROSS-CUTTING GAP (critical for packaging):
the whole pipeline ran WITHOUT the mini-corpus instantiated — handoffs happened via seat memory. "The
mini-corpus is the handoff mechanism the spec is built around and is NOT yet built — the single biggest
gap between this manual run and the automatable version." STRATEGIC FRAME: AIP (Palantir) independently
converged on the same thesis — VALIDATION not threat. Difference: AIP grounds against a curated DATA
MODEL (Ontology); Ontinuity grounds against an adversarial EPISTEMIC PROCESS that works BEFORE the
ontology exists. Pricing: value anchor $600/month problem cost; don't lock until 2-3 more intakes.

**2026-06-14 day — First solution proposal DELIVERED.** GROUNDING CHAIN SPECIMEN (the session's spine):
the seat reached for training priors repeatedly; operator redirected to corpus each time. Key catches:
vault auth (Bearer wrong → Project-Access-Token in corpus); intake location (private repo, not main);
business name fabrication (seat wrote "Senior Home Services" — the intake says "Seniors Helping Seniors");
logo geometry (hexagons, not octagons). THE WITNESS STEP experiment: a prior-conversation witness earns
its keep only for sandbox-local facts the corpus can't hold; corpus wins every conflict; grounding MUST
precede the witness query. BUILT-NOT-FOLDED catch: the prior seat's design path lived only in the
unfoldable conversation window; the close-ritual's conversation-record step had lapsed. MINI-CORPUS:
"The load-bearing unbuilt piece. Build the mini-corpus first." CLOSE RITUAL GATE: independently arrived
at again — "twice independently confirmed = prioritize."

**2026-06-14 evening — Researcher seat mechanism discovered + public button locked.**
RESEARCHER SEAT MECHANISM: the switch is MODEL_A_URL=external in effective config → engine posts each
Researcher turn to external mailbox → seat drives by fetching /mailbox/turn and answering via /mailbox/respond.
CONFIG TRAP: runtime_configs (dashboard keys modal save) OUTRANKS vault (last-write-wins, process-global);
a stale iPad modal override silently staffed Cerebras instead of external. Verify effective config by
behavioral probe before start. PACKAGING NOTE: this trap recurs for any multi-device operator; config-
verification before session start is load-bearing.

**2026-06-14 night — First certified Researcher seat session.** MILESTONE: first end-to-end proof of
the reliability thesis. The gate forced a frontier Claude into a PRE-SPECIFIED shape BEFORE it spoke —
three upheld challenges, output conforms to the frozen contract, not improvised. "A cheap open-source
frontier model under the IDENTICAL gate inherits exactly this reliability — the expensive run proved
the gate; the penny-a-cycle run gets it for free." THREE EXACT EDITS produced (not "roughly fix") —
showing usable downstream shape. ERL wrote for the first time on a real grounded complete close.

**2026-06-15 morning — seed_tenant + first client tenant.** BOX-INSTALL VS COMMIT (the recurring lesson,
recorded verbatim): commit_file wrote new seed_tenant op to the REPO but not the BOX DISK; the restart
reloaded stale on-disk code → 404. Manual line 122 already said this. "Control spent ~an hour declaring
Railway egress throttle blocks the redeploy. The real cause was the box running the OLD on-disk code."
Lesson: when something "can't" be done, re-ground in corpus BEFORE declaring a blocker. Katie Wasserman
(pro) seeded: user 07f75d61, project SHS (eecb5348). Idempotency verified.

**2026-06-15 afternoon — Boot packet fix + boot cold test.** BOOT PACKET REWRITE — structural fix:
decohering seat never authors the boot artifact. A FIXED SNIPPET points at CONTROL_QUICKBOOT.md (authored
by coherent seat) and tells it FETCH-AND-VERIFY, not obey. Hard gate on all-five-doc reads. Cold test:
seat deferred the manual ("next action doesn't depend on it") — fixed by the gate. LESSON: the boot
is not a ceremony; it is a hard gate; soft reads must fail.

**2026-06-20 — Control orientation, researcher lap, Parietal provider trace.** THE DWELLER corrected:
NOT standing software. A recurring SESSION TYPE — the mechanism by which the system ranks its own queue
by evidence and outputs the single defended next item, gate-adjudicated. Not a build. THE RELIABILITY
HANG traced: Parietal + Model C had NO role-specific provider config → fell through to shared PROVIDER_MODEL
(null) → 404 on every Novita call → finalize hung indefinitely. MODEL B (Challenger) worked because it
had explicit Cerebras config. "A session that catches real errors then fails to write them down — the
certification is exactly what breaks." [PACKAGING NOTE: Parietal MUST have an explicit provider config.
Parietal must NOT share Challenger's lineage (adversarial error-geometry separation is a design rule).]
IN-SESSION PRIORS CATCH: seat claimed "last lap June 7" from chat-side memory; Challenger sustained the
challenge precisely — "not in the injected results"; retracted and regrounded. Architecture caught it,
not the model.

**2026-06-29 — Oracle step 1 + leash architecture.** SETTLED DESIGN (read against source):
- Oracle = a Tetraform SESSION (grounding is contestable judgment; the close gate exists to gate it).
- Coordinator = a deterministic code loop in shepherd's lineage (FIFO mailbox drain, no-self-sign-off
  in code, courier ops). NOT the Oracle.
- Governor = read-only pane; gains hands later gated on the seat registry.
- TWO WORKERS sign off EACH OTHER'S work. No phantom third seat.
- The ONE unleashed surface = control DESIGN CONVERSATION; its failure mode = assert-from-memory.
Oracle step 1 shipped (mailbox schema/contract, corr_id, question/answer kinds).

**2026-07-19 — Songbook design + corpus-standard failure.** THE BOOT AS PRODUCT: operator, watching
a fresh seat snap from an unoriented instance to a harnessed one via the boot snippet: "Think about
how I took you from an un-oriented, free thinking instance to one that was quickly snapped into a context
by a boot packet snippet. That's part of the nuts and bolts of how this sausage is made." CREDENTIAL
RULE: a credential cache that can go stale is WORSE than no cache — "it does not save a lookup, it
teaches a wrong conclusion." LLaves item inverted to REMOVE the PATs, not refresh.

**2026-07-20 — The Package / hands resolved.** OPERATOR'S OPENING POSITION (proved correct):
"Build Cornel's system to use the components that mine already uses, with the idea that he'd have his
own Railway and VPS setup." HANDS RESEARCH (operator-forced): Gemini consumer chat = no network from
code sandbox; Custom MCP requires Google AI Ultra ($100-200/mo, US-only, rules out Cornel's work account);
Gems read Google Drive natively; Drive writes = duplicate-file failure mode. CONCLUSION: a separate
Railway+VPS is the right call, not engineering around it. PROVISIONING_RUNBOOK.md (735c42bd in private
repo) written this session. The session's documented failure: control drifted away from the correct
answer and had to be dragged back repeatedly.

**2026-09-03 — Cross-vendor succession proof.** OPERATIONALLY PROVED: a non-Anthropic model (gpt-5.6-sol)
inherited the Control office through the existing corpus + HTTPS hands without rewriting the engine. The
control boot transferred: corpus-before-priors orientation, authenticated courier access, live 19-op
allowlist, Tetraform session gating. "The consumer chat application is not the harness; the ENGINE is.
Seating another model should be configuration plus a boot, not a new bridge." This is the single most
important packaging confirmation in the record.

**2026-09-03 — Completion phase + career path.** OPERATOR'S SELF-CHARACTERIZATION: "My building style
looks the way it does because my mind dreams up the end result first then finds a way to implement it."
PHASE CHANGE: "There's nothing left to decorate. Completing the punch list, where relevant, will get
me closer to whatever the finish line is." → This session initiated the B-blocks completion phase.

**2026-09-05 — B5-P + challenged live proof.** B5-P installed, challenged deliberately, retracted,
recoverable from the database without model memory. The session manifest records the external occupant
as UNVERIFIED_PENDING_B1_B2 (honest about the identity gap). Proved: evidence-preservation layer works
end-to-end; an unsupported inference, challenged and upheld, leaves a durable retraction record.

### sessions/ folder: ODS (Ontinuity Driving System) data only
All 18 session files + push_test.txt are UTF-16 encoded ODS sensor/track logs
("[ODS] Ontinuity Driving System - Phase 1 Brainstem v5") — a DIFFERENT project.
[READ-not-skeletal for the Ontinuity platform map; document as "ODS artifacts in platform repo."]

════════════════════════════════════════════════════════════════
## 17b. STAGE 5 VERIFICATION PASS — content missed on first read (now folded)

**backup_db op (full mechanism, from 06-15 afternoon):** sqlite3 `.backup` + `iterdump()` → a `.sql`
TEXT file (ships through commit_file, diffs in git). 3.85MB dump committed to the PRIVATE repo at
backups/ontinuity_dump.sql. Repeatable: backup_db → commit_file, two calls. THIS is the product's
DB-backup path. Backup is INDEPENDENT of the live keys (survives credential revocation).

**[PACKAGING + META] The VERBOSITY GATE (named, banked design item — 06-15, 06-19):** operator made it
a PRIORITY: "Let you elaborate in a box somewhere else and then have something return the consolidated
version." Same architectural shape as the fabrication gate (draft out of sight → contract-shaped output
to the operator). Standing operator preference throughout: terse prose, no nannying, no time estimates,
one step at a time. [Directly relevant to the model-drift/over-verbosity problem; unbuilt.]

**[GROUNDING RULE for this whole map] operator, 06-19:** "There is no documentation of the components or
system beyond what you've read. If you don't see it in the repo — it doesn't exist." The STATE_OF_ONTINUITY
inventory exists BECAUSE "the system matured past its own paper trail; the gate/contract/seat architecture
is documented nowhere but the repo — until this inventory." → This master map is the continuation of that
same effort: the system's shape lives in the repo + these records, nowhere else.

**Credential exposure/revocation history (06-15):** three exposed credentials (diag key, GitHub PAT,
Railway project token) were REVOKED at end of that session (rotation deferred). Once revoked the system
goes fully dark until rotation — a safe idle state. Standing rule reaffirmed: credentials travel
out-of-band, NEVER committed. [Same class as the exposure flagged this session — recurring risk;
credential hygiene is a live concern for packaging N instances.]

**Oracle FAILURE (06-29, recorded not hidden):** design-note v1 over-claimed a general substrate hosting
the coordinator as a Tetraform session — extrapolated from the CONFIG layer without reading the LOOP body.
Reading the loop disproved it; v2 corrected it. "The cost was hours the operator paid for, building the
leash while demonstrating why it is needed. The fix is the structural gate, not a promise to do better."
The recurring failure-class specimen: assert-from-adjacent-layer instead of reading source.

════════════════════════════════════════════════════════════════
## 18. STAGE 6 FINDINGS — EVERYTHING ELSE

### [PACKAGING-CRITICAL] project-corpus-standard/ = the memory discipline as a NO-INSTALL product
"Platform-neutral. Works with Claude, Gemini, ChatGPT, a local model, or a mix. No software to install.
It is a folder shape and two checklists." THIS IS THE SIMPLEST PACKAGEABLE VERSION of the memory product —
Knowtext's discipline reduced to a Drive/git folder + open ritual + close ritual, usable by anyone TODAY.
- SIX template files: CURRENT_STATE.md (boot doc, forward-only, SINGLE next action, LOCKED DECISIONS
  fenced), PROBLEM_DEFINITION.md (ground truth, [U]=user-said vs [I]=inferred, quote don't paraphrase),
  ROADMAP.md (phased, GATES are conditions not dates, name the failure branch), PUNCH_LIST.md,
  mini_corpus.md (append-only fold: BUILT/LEARNED/REVERSED — "reversals are the most valuable part"),
  sessions/SESSION_TEMPLATE.md.
- GEMINI_QUICKSTART.md: Option A = Drive folder (Gemini reads live); Option B = a Gem with the discipline baked in.
- CORE IDEA (verbatim): "use the model for capability. Never for project-facts. Where priors and your
  record disagree about YOUR project, the record wins. Ambiguity is the doorway for priors. Structure
  prevents; review only catches."
→ THE MEMORY-FIRST PRODUCT for a non-technical user (BIL/Cornel) may be THIS, not the engine. No Railway,
  no box, no keys. The engine version adds the adversarial reliability + automation ON TOP. Two product tiers:
  (T1) the corpus-standard folder discipline [zero-install, ships today]; (T2) the full engine instance.

### [DEEPEST "WHAT ONTINUITY IS"] live/notes/BOUNDARY_GATE_PRIMITIVE.md
The single design primitive under ALL the operator's systems across a decade: "A CHECKPOINT AT A TRUST
BOUNDARY THAT DEFAULTS TO NO UNTIL A SAFETY PROPERTY IS PROVEN." Gate-and-prove, not trust-and-monitor.
Recurs in: SYNAPSE (10-yr-old cybersecurity concept — pre-execution isolation, micro-VM vetting of ingress),
RUST (compile-time memory safety — nothing unprovable compiles), and ONTINUITY (contract-gate, sanitizer
membrane, SMS classifier gate, boot-packet gate, the firewall-by-design box). Same primitive the rigorous
corner of CS converged on (capability security, zero-trust). → THIS is the credibility narrative + the
philosophical spine. Ontinuity is one instance of the operator's native design instinct, applied consistently.
Synapse papers (White, Investor) are in the repo root as PDFs — conceptual stage, not technical-deep.

### [THE FACTORY PATTERN] live/integrations/senior-care/FOLD.md
The first Ontinuity-built external product AND the template for the integration rhythm (each gets
live/integrations/<name>/). Full SHS design: per-account SMS-native emergency-coverage matcher, availability
by ASKING not storing, code-first (AI only upstream in the factory + year-two insight layer, NEVER in the
live coverage decision). ClearCare/WellSky data access = the load-bearing unknown (FHIR Connect API exists
but licensing a solo agency is unresolved; sanctioned surface only, no scraping — HIPAA/HITRUST).

### live/fixes/ — 5 proposal docs (burnin_fix1-4 + signoff_gate, all PRE-GPT, ~1:1 the deploy candidates)
+ 5 one-line STATUS-MARKER stubs (BOOTTUNE-1, BOOTTUNE-COMPARE, ERL-REBUILD, KEYS-2-FIX, POISON-DETECT-1).
[READ-not-skeletal — historical proposals, mostly landed pre-GPT.]

### live/tools/ — b1_verify.sh (B1, discarded), ipad_keyboard.py (RESTORED tool),
ontinuity_https.sh (the courier compiler — covered), release_baseline.py (drift tool, KEEP — covered).

### live/misc/ — push_to_github.py (⚠ historically had a hardcoded PAT — the exposure caught 06-10;
verify clean before shipping), museum_absence.py + museum_experiment.py (the "museum" = specimen store
for gate-failure test cases; B3/B4 territory), migrate_experiment_mode.py, run_ods.bat (ODS — not platform).

### live/experiment/ — burnin_resident.py (the FARM burn-in driver), B5P test plan + acc logs (B5-P
evidence), migrate_modal_touched.py. live/audits/ — burnin audit pass1 + task (the 06-08 audit). 
live/archive/ — boot_extreme_REFUSE_worker3 (a boot-poison refusal specimen), mailbox laptop results.
live/tests/ — courier_smoke_test.sh. live/evidence/ — B1_IPAD_PRIVATE_TRANSFER (B1-era).

════════════════════════════════════════════════════════════════
## 19. STAGE 6 FINDINGS — ROOT FILES + TESTS

### root README.md (the repo's one-line self-description):
"Persistent cognitive infrastructure for AI-assisted work. Implements Tetraform (4-model adversarial
collaboration), Knowtext (portable session memory), and the Teaching Leash (runtime resistance as an AI
safety architecture). First documented cognitive ecology running four models from four companies."
→ The THREE named pillars: Tetraform (reliability), Knowtext (memory), Teaching Leash (safety).

### LIVE MEMORY DATA (on disk, confirms the schema works):
- knowtext_main_main.txt — MAIN project's live Knowtext, schema v1.1, 7 fields, "NO CHANGE" for unchanged,
  Delta Log + Correction History populated from real session 2026-06-14_22-19-08. THE SCHEMA WORKS AS DESIGNED.
- knowtext_isotest_main.txt — isotest project memory.
- erl_main_main.txt — the ERL as FLAT TEXT (RESULT/SESSION/BRANCH/CONFIDENCE=ESTABLISHED). So the ERL
  DOES persist file-side even though the DB table is empty — the file-based ERL is the working one. (Refines
  §15: structured DB ERL needs Projenius; the file ERL already works.)

### PUBLIC WEBSITE (18 .html) — the concept papers, live at ontinuity.org:
index, reliability ("Reliability Without Trust"), tetraform, knowtext, teaching-leash, cognitive-ecology,
artificialware, dynacology, trust ("Security & Trust"), synthesis, growth-vector, moip, buckyball, papers,
corpus, session-record, deidentifier, intake/intake11 (the Mode-A intake questionnaire pages).
→ The public marketing/education layer. Carries the living-mark logo. [READ-not-skeletal for platform mechanics.]

### RESEARCH PAPERS (21 .docx) — the SOURCE documents behind the .html pages:
Tetraform, Knowtext, Teaching Leash, Cognitive Ecology (+Cybersecurity/Robotics/Swarm/Meta), Artificialware,
Dynacology, Triform v1/v2, Adversarial Development, Growth Vector, MoIP, Routing Client, Psychology of AI,
research/safety summaries, Project Outline, Ontinuity v1 final. [The intellectual corpus; READ-not-skeletal.]
Plus "Psychology of AI Data arXiv.pdf", Synapse PDFs (§18). "ontinuity behavioral data.db" = the committed
behavioral capture DB (sessions/challenges/signals).

### root .py (6): box_ops.py, db.py, workspace_db_endpoint.py = ROOT COPIES of the live/ code (already mapped).
capability_auth.py = B1 (DISCARDED). extract_to_db.py + model_client.py = engine helpers (transcript→DB
extraction; model API client). requirements.txt, Procfile, CNAME = deploy infra.

### tests/ (11) — almost all B1 (DISCARDED machinery):
test_b1_bootstrap_gate, test_b1_burnin_restart, test_b1_release_boundaries, test_capability_admission(+surface),
test_capability_box_identity, test_capability_courier, test_ontinuity_https_client, test_trusted_deploy =
ALL B1 test suites (test the discarded capability/admission/trusted-deploy machinery). KEEP: 
test_research_preservation.py (B5-P — the auditability layer we kept), test_release_baseline.py (drift tool).
→ PACKAGING: when B1 is excluded, its test suites go too. Keep the 2 non-B1 tests.

════════════════════════════════════════════════════════════════
## 20. SFINAL — OPEN ITEMS RESOLVED/CONFIRMED + END-TO-END FLOW TRACES

### RESOLUTION OF EVERY [OPEN] / [PARTIAL] ITEM:

**[OPEN #1] Intake WORKSPACE_STATE → first Knowtext bridge — CONFIRMED GENUINELY OPEN (unbuilt).**
Traced in code: /intake_capture writes workspace_state to a JSON FILE in the private intake-data repo
(sessions/intake_<id>_final.json). It is NOT bridged to a project knowtext_version or DB row. Turning an
intake into a project's first Knowtext is a MANUAL step today. This is THE SAME GAP as the mini-corpus
("the pipeline ran without the mini-corpus instantiated", 06-14). → BUILD ITEM: an intake→project bridge
that seeds the first Knowtext + mini-corpus from the captured WORKSPACE_STATE. Bounded, well-specified.

**[PARTIAL→RESOLVED] storage_configs + established_results wiring.** Live confirmed: storage_configs=0,
established_results=0, BUT knowtext_versions=357 (memory writes fine), users=2, projects=3.
- storage_configs empty = the pluggable-backend SCHEMA exists but no install has SET one; the default is
  implicit (local box). For a single-operator install, the default local path works without a row.
  → Not a blocker; a per-tenant install optionally writes one storage_config row to point elsewhere.
- established_results empty (DB) BUT erl_main_main.txt EXISTS and works (file-based ERL:
  RESULT/SESSION/BRANCH/CONFIDENCE=ESTABLISHED). → The FILE ERL is the working memory-of-record; the DB
  ERL table needs Projenius configured + a persist path. NOT a blocker for memory; a refinement for
  structured cross-session queries. CONFIRMED: memory works file-side; DB structuring is the open refinement.

**[OPEN #2] Per-tenant credentials (shared-diag-key ceiling) — CONFIRMED OPEN, and it's THE ONE REAL
SECURITY ITEM.** Today one shared diag key gates the box. With N per-operator INSTANCES this is actually
FINE — each instance has its own box + its own key (isolation by separate deployment, not shared-key
partitioning). The ceiling only bit when contemplating many tenants on ONE box (which we've discarded).
→ RESOLUTION: per-individual instances make this a NON-issue by construction; each install generates its
own diag key at provision time. The one B1 hygiene lesson to keep: never put the key in the boot packet
(use the LLaves-file / vault pattern). NO capability machinery needed.

**[OPEN #3] Tenant __probe__ before allowlist exists — RESOLVED (not actually a problem).** The pre-GPT
engine's __probe__ returns the FIXED 19-op OP_ALLOWED (compiled into app.py), not a per-tenant list. A
fresh instance running the same app.py returns the same 19 ops immediately. There is no per-tenant
allowlist to bootstrap — the allowlist is engine-code-level, identical across instances. → NON-issue for
the per-instance model. (Was only a question under the discarded per-tenant-capability model.)

**[OPEN #4] Corpus repo: theirs vs shared directory — RESOLVED by PROJECT_CORPUS_RUBRIC + isolation code.**
The rubric's separation rule + session_knowtext_path structural isolation answer it: the ENGINE is shared
infrastructure (per operator); each PROJECT's corpus is separate (own knowtext file, own DB rows, own
git location). For a per-operator install, THE OPERATOR OWNS THEIR CORPUS REPO. Their projects are
directories/rows within it, structurally isolated from each other. → Each operator = own repo; projects
isolated within. Settled.

**[OPEN #5] Configuration/install runbook — EXISTS but not in the public corpus.** PROVISIONING_RUNBOOK.md
(735c42bd) was written 2026-07-20 and lives in the PRIVATE intake-data repo (not readable with the public
token). → The runbook EXISTS; it needs to be retrieved from the private repo, updated to the recovered
pre-GPT+B5-P state (post-recovery: no B1 admission, 19-op diag-key, MAIN=5640170), and validated. This is
the concrete packaging deliverable. STATUS: exists, needs update + validation.

### END-TO-END FLOW TRACE #1 — MODE A (INTAKE → SOLUTION), no [OPEN] seam except the named bridge:
website intake page (intake.html) → /intake_chat (4-phase discovery, INTAKE_PROVIDER key) → emits
[WORKSPACE_STATE] → /intake_capture (append-only JSON to private intake-data repo) → [SEAM: manual/unbuilt
bridge to first Knowtext] → seed_tenant (user+project rows) → four-stage pipeline (Tetraform sessions,
provenance-tagged, per-project mini-corpus) → solution proposal (docx). 
LIVE: intake (stage 1), capture, seed_tenant. UNBUILT: the WORKSPACE_STATE→Knowtext bridge + the
mini-corpus that stages 2-4 hand off through (= the single automation gap, well-specified).

### END-TO-END FLOW TRACE #2 — MODE B (DIRECT SESSION), no [OPEN] seam:
operator + seat → boot (CONTROL_QUICKBOOT snippet → fetch-verify CONTROL_QUICKBOOT.md → 5 grounding reads
→ __probe__ 19 ops → bootstrap_gate oriented:true) → /agent/start {objective, project, branch} → adversarial
cycle (Model A researcher / Model B challenger-different-lineage / Model C friction / Parietal adjudicate,
frozen contract, fabrication detection) → /agent/queue amend on record → close: Projenius DISTILL → Knowtext
delta written (knowtext_versions +1) + file ERL → next session reads Knowtext and continues.
FULLY LIVE end-to-end (verified this session: boot oriented:true, hands work, 357 knowtext_versions, memory persists).

### DONE-CRITERIA CHECK (the falsifiable test set):
1. Every file SUMMARIZED or READ-not-skeletal — ✅ 252/252, 0 unread.
2. §9 Still-to-Map all checked — ✅ (intake→knowtext bridge, pipeline, Projenius, Parietal, close ritual,
   prompts, corpus template, governor — all mapped).
3. Every [OPEN] resolved or confirmed-open — ✅ (5 resolved as non-issues/settled; 1 confirmed genuinely
   open = the intake→Knowtext/mini-corpus bridge; runbook exists-needs-update).
4. Both front-door flows traced end-to-end — ✅ Mode B fully live; Mode A live except the one named,
   well-specified bridge seam (not a mystery — a bounded build item).
5. Cold reader could understand the system without source — ✅ (this map).

### THE SINGLE REMAINING BUILD GAP (everything else is built or is per-instance packaging):
The **intake→Knowtext/mini-corpus bridge** — the one automation seam. Mode B (direct session) is fully
built and live. Mode A (intake→solution) is built except turning captured intake data into the project's
first durable memory + the mini-corpus that pipeline stages 2-4 hand off through. This is THE build item
that separates "manual pipeline run" from "automated product." Bounded and well-specified.

═══ MAPPING COMPLETE. The map now enables the packaging plan (next: test that claim by writing it). ═══

════════════════════════════════════════════════════════════════
## 21. THE CONTINUITY MECHANISM (Mode B) — DEPTH-ARM ANCHOR
The general map (§2 memory, §3 engine, §14 roles, §17 rituals) treats the AUTOMATIC MECHANICAL CAPTURE
— the thing that lets a cold model pick up where the last left off — as scattered nodes. It is actually a
single coupled CIRCUIT (open→run→close→next-open), with the CURRENCY DISCIPLINE as its heartbeat.
→ FULL ANATOMY + PHYSIOLOGY: see companion depth-map **ONTINUITY_CONTINUITY_MECHANISM.md**.
This anchor exists so a cold reader hits the survey here and can DRILL into the mechanism without mistaking
the survey ("Projenius writes Knowtext at close") for the whole truth. The mechanism is the PRODUCT'S CORE:
it is the part that must be brought into reality so it fires automatically, with the user never doing
technical work by hand. Anchored Sept-3 (the cross-vendor succession proved the full circuit fired: a cold
non-Anthropic model booted and picked up the office through the corpus alone).

════════════════════════════════════════════════════════════════
## 22. PRIVATE REPO ACCESS + THE PRIVATE CORPUS (ontinuity-intake-data)
[HOW-TO, indexed for retrieval — a fresh seat needing the private repo reads THIS section first]

### HOW TO REACH THE PRIVATE REPO (verbatim, verified this session — do NOT rediscover)
The intake token is NOT in LLaves by design. MINT it from the Railway vault:
1. Railway project token is in LLaves. Vault-read via Railway GraphQL (the EXACT query that works — bare
   forms 403): POST https://backboard.railway.app/graphql/v2, header `Project-Access-Token: <railway token>`,
   body query `variables(projectId:"a8dea5f4-b34e-466e-b22c-0d5b59fc63b5", environmentId:
   "6ff341f9-675e-4514-9b0c-5defe9d3d2a9", serviceId:"72b20f74-d24d-4502-ba35-97e2d09f809a")`.
2. Returns 40 vars incl. `INTAKE_GITHUB_TOKEN` (93 chars). Use it as Bearer on api.github.com contents API
   for repo `PatrickKillebrew/ontinuity-intake-data` (same pattern as the main repo).
Three distinct keys: DIAG_KEY = box/engine hands; Railway project token = vault key (in LLaves);
INTAKE_GITHUB_TOKEN = private-repo key (MINTED via the Railway token, never in LLaves).
FAILURE-CLASS NOTE: a 404 on the private repo with the MAIN PAT is EXPECTED (main PAT is scoped to public
repo + trophyclubpainting only). Do NOT report "no access" — mint the intake token first. (This seat hit
that exact wall and gave up until pushed; recorded so the next seat doesn't.)

### PRIVATE REPO CONTENTS (the layer-1/layer-3 corpus the public repo lacks)
- **LAPTOP_HANDS_RUNBOOK.md** — how a conversation gets EXECUTION-hands on a physical laptop (see §23).
- **projects/shs-wasserman/** — the COMPLETE real SHS/Katie project corpus (30+ files): CURRENT_STATE,
  SHS_PROBLEM_DEFINITION, ROADMAP, PUNCH_LIST, mini_corpus, design/session folds, compliance verdicts,
  FROZEN_PRODUCT_SHAPE, W5_PACKAGING, sanitizer/ (the layer-3 identity membrane, W1-W5 build notes + generic
  SANTA_CLEAN). This is the memory discipline IN PRODUCTION — the real specimen of what a packaged project
  corpus looks like. [DEEP-MAP TARGET — the three-layer topology (§8.4 depth-map) made concrete.]
- **projects/azz-galvanizing/SEED.md** — Cornel/AZZ (the target user's origin project).
- **projects/ipad-keyboard*/** — the ipad keyboard helper project corpus (the tool GPT deleted, its home).
- **backups/** — the DB .sql dumps (backup_db output; e.g. ontinuity_dump.sql).
- **sessions/** — captured intake JSONs (intake_<tag>_final.json; Katie = intake_Kshs_final.json).
- **synapse/** — the Synapse (cybersecurity) project material.

════════════════════════════════════════════════════════════════
## 23. LAPTOP EXECUTION-HANDS (LAPTOP_HANDS_RUNBOOK.md) — the build-hands mechanism
[Fills the "how does a build get executed" gap. Distinct from box/engine hands.]

### THE METHOD: the laptop runs file_server.py (Flask, C:\donkeycar) with a `/run` endpoint that executes
whitelisted commands via subprocess.run(shell=True). Endpoints: /status /read /write(auth) /run(auth)
/settings(auth) /log. config.json holds api_key, duckdns creds, safe_commands (EXACT-STRING whitelist),
active_project (sets /run cwd). This drove the S22-over-ADB build at the operator's sister's house.

### REACHABILITY (the operator's ONLY manual steps — everything else the conversation drives):
1. Start server: `cd C:\donkeycar && python file_server.py` (binds 0.0.0.0:5001).
2. DuckDNS current: if public IP changed, `python duckdns_update.py` (ontinuityws.duckdns.org).
3. Port-forward TCP 5001 -> laptop:5001 (router) OR Caddy 443->localhost:5001. Operator disables between
   sessions for safety; re-enabling is deliberate operator-only. NO tunnel tool in the corpus (no
   cloudflared/ngrok/tailscale); an outbound cloudflared tunnel is the correct build if a persistent
   no-port-forward channel is ever wanted — NOT yet built.

### THE 30-SECOND-TIMEOUT PATTERN (critical): /run kills anything >30s. For PyInstaller/Inno/pip: launch
DETACHED (`start "" cmd /c BUILD.bat > build.log 2>&1`) — returns immediately — then POLL via /read?path=
build.log until DONE/[STOP]. A wrapper BUILD.bat reduces a multi-step build to ONE whitelisted string.

### THE DECISIVE 2026-07-02 CORRECTION (two run-paths, traced to live app.py):
1. **Engine session path** (what drove the S22): WORKSPACE_URL -> laptop DuckDNS; the Railway SESSION ENGINE,
   inside the session loop, calls call_workspace_run (app.py ~2559) POSTing to {WORKSPACE_URL}/run. RAILWAY
   dials the laptop (cloud egress IP), not the sandbox. call_workspace_run is reachable ONLY from the session
   loop — NOT from any diag/courier/public route.
2. **Courier path** (/diag/op/<name> -> box /op/<name>): the laptop's file_server has /run /read /write
   /settings, NOT /op/*, so the courier CANNOT drive the laptop even if WORKSPACE_URL is repointed.
→ A CHAT-SANDBOX CONVERSATION CANNOT drive the laptop's /run via the courier. To reproduce laptop run-hands:
unfreeze Railway -> repoint WORKSPACE_URL to laptop (dashboard, no deploy) -> RESTART engine (WORKSPACE_URL
cached at import, app.py:52) -> open laptop port -> run a session. WITH ENGINE FROZEN a sandbox has read-hands
(diag) + repo-hands (PATs), NOT laptop-run-hands.
→ THE MOST PROMISING UNBLOCKED PATH: sandbox -> http://<laptop-public>:5001/run DIRECTLY with X-API-Key,
bypassing the engine — IF the laptop port is open. Tested 2026-07-02, FAILED (HTTP 000) only because the
port-forward was OFF; worth re-testing when the port is open (blocked by the port, not the protocol).

### SECURITY REALITY: /run with shell=True on the public internet, protected by one API key = real attack
surface. Acceptable for a bounded operator-present build session; never left open persistently. Re-open,
build, close. (The boundary-gate primitive applied: the port IS the gate; default closed.)

### PACKAGING RELEVANCE: this is BUILD-hands (how the product's own artifacts get compiled/packaged, e.g.
the W5 installer for SHS), distinct from the per-operator INSTANCE hands (box/engine). For packaging Product
2, the installer build uses this laptop-hands path; the per-operator RUNTIME uses the box/engine courier.

════════════════════════════════════════════════════════════════
## 24. THE PROVISIONING RUNBOOK — per-operator install (zero to a booted seat)
[Source: private repo projects/the-package/PROVISIONING_RUNBOOK.md, commit 735c42bd, 2026-07-19.
This is THE per-operator install procedure. Reach it via §22. Method rule: DUPLICATE the operator's
install; "same as Ontinuity" = copy the working thing, do not redesign. Audience: a competent IT
person or the operator — THE END USER DOES NOT RUN THIS (confirms the corrected single-product model:
the user only does the two rituals in §F; everything else is one-time setup).]

### THE USER OWNS FOUR THINGS (nothing shared with any other install):
- A1 REPO — a PRIVATE GitHub repo. Holds the corpus. THIS IS THE MEMORY.
- A2 ENGINE — a Railway service. Hosts the courier so the user's AI reaches the box; holds secrets as env.
- A3 BOX — a small VPS. Runs the ops; the mailbox + every /op/* execute here; the DB lives here.
- A4 BOOT PACKET — a text block the user pastes. Seats their AI: gives hands, then grounds it.
WHY BOTH ENGINE+BOX (not optional): engine = reachable public relay surface; box = where ops run + DB.
A commit to the repo does NOT install on the box — two separate steps, THE most common install mistake.

### PREREQUISITES (§B): user GitHub acct (private repo); Railway PAID tier (trial expiry kills the engine);
VPS 2GB Ubuntu (Hetzner CX22-class proven); domain/DDNS or static IP for the box; user's AI platform + API
key; a password manager for generated keys (never in a repo file).

### STEP-BY-STEP (§C):
- C1 PRIVATE REPO: create it; make `live/`; seed with MECHANISM docs (§D) + EMPTY TEMPLATES (§E); make a
  PAT (contents r/w THIS repo only) → goes in the vault at C3, not a file. Check: GET contents/live returns files.
- C2 BOX: VPS Ubuntu 2GB; Python3+gunicorn; copy file_server.py + box_ops.py from operator install; ops
  needed for a REMEMBERING seat = read_repo, read_file, write_file, commit_file, read_journal (mailbox ops
  only if multiple seats); generate DIAG_KEY (40 alnum) → password manager + box env; gunicorn 0.0.0.0:5001
  as systemd. AUTH = APPLICATION-LAYER KEY, never IP whitelist (retired 2026-06-10, pooled cloud egress IPs
  lock out legit seats). Check: box-local curl localhost:5001/health responds.
- C3 ENGINE: Railway project+service, Hobby+ (trial expiry kills it); deploy the courier — MINIMUM two
  routes: GET /diag/<endpoint> (read-through) + POST /diag/op/<name> (forwards to box /op/<name>). (Operator
  app.py has 17 routes; only these two carry the seat; the rest is session runtime, not needed for context
  mgmt.) Env: DIAG_KEY (same as box), WORKSPACE_URL=http://<box-ip>:5001, GITHUB_TOKEN (the PAT), user model
  key. Note PROJECT/ENV/SERVICE IDs. Make a Railway PROJECT TOKEN (the vault key) → password manager.
  THE KEY CHECK: POST {engine}/diag/op/__probe__?diag_key=<DIAG_KEY> body {"seat":"control"} → expect a 403
  whose body ECHOES THE LIVE ALLOWLIST. If the allowlist comes back, THE WHOLE CHAIN WORKS. Don't proceed on
  a broken probe.
- C4 PARAMETERIZE THE BOOT PACKET: take operator CONTROL_QUICKBOOT.md, replace EXACTLY SEVEN values (engine
  URL, repo owner/repo, Railway PROJECT/ENV/SERVICE IDs, Railway token prefix as pointer, client/project
  name). CHANGE NOTHING ELSE — the discipline sections (fetch-and-verify, assertion rule, hard read gate,
  park-don't-doubt) make the boot work and are not install-specific.
- C5 CREDENTIAL FILE: create `LLaves` in the user's AI project space (Gemini attached files / Claude project
  files) with TWO things: DIAG_KEY + Railway token. NOT the GitHub PAT (a cached credential goes stale on
  rotation and teaches the seat it has no write path — the PAT lives in the vault, minted at boot; a stale
  cache is worse than no cache).
- C6 FIRST BOOT: fresh conversation in the project with LLaves attached; paste the packet; watch THREE things:
  (1) it reports the REAL allowlist from the probe (not an expected list — that means no connection);
  (2) a REAL LINE from each required doc (not a summary); (3) the single next action in one line. All three land = live.

### §D MECHANISM docs into live/ (~25k, copy w/ light edits): THE_PARADIGM (trim self-hosting roadmap, keep
corpus-over-priors), OPERATING_RUBRIC (trim incident note, keep roles+honest-ceiling), OPERATING_MANUAL
(copy the ~14k that is RITUALS+COMMITTING+CREDENTIALS; leave behind session-start-modes/config-trap/shepherd/
role-providers/Oracle = Tetraform runtime), CONTROL_QUICKBOOT (parameterized, 7 values).
### §E SHIPS EMPTY (state, install-specific, SHAPE not content): CONTROL_HANDOFF (headings + "no prior
session" + blank next-action), PUNCH_LIST (DONE/IN-PROGRESS/OPEN empty + evidence-citation rule), agent_queue
(head structure only: read-the-manual banner + STANDING RULES + empty ACTIVE). DO NOT copy operator content
(Ontinuity's punch list=61k, queue=206k of another company's history — would teach the seat wrong facts).

### §F THE TWO RITUALS (what the END USER actually does — the ONLY user-facing part):
- RESUME (start of a session, after any gap): paste the boot packet into a fresh conversation → AI reads the
  corpus and reports where things stand. BOOT AND RESUME ARE THE SAME ACT.
- GROUND (mid-session): when a component reaches fruition OR the AI asserts without showing reads → "Ground
  yourself against the corpus before continuing."
- CLOSE (when stopping): "Run the close ritual." AI must: reconcile punch list vs shipped (cite evidence),
  write the session record (THE REASONING not just outcomes), fold the queue, fix stale, sweep secrets,
  update handoff with the single next action. THE CLOSE CARRIES THE WHOLE BURDEN (the instance that did the
  work is the only witness to WHY). Make the AI report PASS/FAIL per item WITH THE ACTUAL VALUE IT READ (not
  "I updated everything" — a hand-run close had two checks silently failing, caught only by demanding a real
  date from a real file).

### §G VERIFICATION (done when all 5 pass): __probe__ returns live allowlist; fresh boot reports a real line
from each doc; seat read_repo's a file through the courier; seat commits a file; a close ritual writes to the
repo and the commit is visible on GitHub.

### §H KNOWN TRAPS (each cost the operator real time — do not rediscover):
repo-commit≠box-install (needs write_file+restart, TWO steps) · direct :5001 timeout (by design, use courier)
· stale CDN reads (use api.github.com raw, never raw.githubusercontent.com) · cached PAT 401 (mint from vault
— why C5 keeps PAT out of LLaves) · Railway trial expiry (paid day one) · IP whitelist (pooled egress, use
key-auth) · long-poll timeout (wait param ≤20s; relay read-timeout 25).

### §I OPEN, resolve during FIRST install (honest gaps): (1) can the target chat surface make OUTBOUND calls?
Claude's sandbox runs curl; other platforms UNTESTED — test FIRST. (2) will a non-Claude model hold the seat?
The read gate demands several long docs + cross-reasoning; failure is SILENT (reports oriented, reasons from
priors) — the close gate is the backstop (another reason close matters more than open). (3) cost per install
(Railway+VPS, unpriced). (4) automation: deliberately manual — prove the sequence by hand before scripting.

### PACKAGING STATUS: this runbook IS the Product-2 install procedure, COMPLETE and actionable, written
against the operator's proven install. It needs: (a) update to the recovered 5640170 state (no B1 admission;
19-op diag-key — the runbook predates B1 so it already assumes the diag-key model, GOOD); (b) resolve §I gaps
on a real first install (Cornel = the outside-operator transfer test). The runbook already assumes the
CORRECT (per-individual, diag-key, user-does-only-rituals) model — it was right before B1 and remains right.
