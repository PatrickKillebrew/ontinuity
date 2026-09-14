# ONTINUITY — TOTAL SYSTEM INDEX
## The whole system distilled from a full read, so the totality is HELD in retrievable form
*Built by Fable 2026-09-13, reading the load-bearing corpus end to end. Purpose (operator mandate): read
EVERYTHING first so the totality lives in memory before packaging — then package correct-the-first-time.
This index IS the memory: "recall is not a substitute for retrieval" applied to reading the system itself.
A seat does not need to hold all ~200 files at once; it needs each read carefully and distilled here, then
retrieves. Every packaging decision checks against this index.*

## HOW THIS INDEX RELATES TO THE OTHER MAPS (one retrieval surface, layered)
- THIS FILE (ONTINUITY_TOTAL_INDEX.md) — the OPERATING LAYER distilled: the core docs, the seat brains, the
  security model, the rituals' mechanics. Dense, for holding the whole in one read.
- ONTINUITY_MASTER_SYSTEM_MAP.md — the 25-section whole-system SURVEY + the recovered-state + GPT keep/discard.
- ONTINUITY_CONTINUITY_MECHANISM.md — the Mode-B automatic-capture circuit at DEPTH (open/close gates, the
  seating mechanism, the two-tier distillation, the four SHS invariants).
- ONTINUITY_INTAKE_MODE_SHS.md — Mode A worked example (the shipped SHS/SantaClean product).
- Private repo the-package/ — PROVISIONING_RUNBOOK (the install), RITUAL_MECHANICS (why the joint needs the
  grease), ROADMAP (phases), mini_corpus (the four scope reversals — the do-not-repeat guard).
- Conversation records (live/conversations/, 26 files) — the DECISION HISTORY; distilled in master map §17.
Read order for a fresh seat wanting the whole: STATE_OF_ONTINUITY → this index → the depth-arms as needed.


═══════════════════════════════════════════════════════════════════════════
## PUBLIC REPO — CORE OPERATING DOCS (live/ root)
═══════════════════════════════════════════════════════════════════════════

### STATE_OF_ONTINUITY.md [THE TOTALITY IN ONE DOC — read this to hold the whole]
The self-inventory (June 19), authoritative over the April papers where they disagree.
- ONE-LINE: Ontinuity = a TEAM-OF-SEATS system with a two-party deploy gate; reliability from the HARNESS
  (ground-from-record + a gate that won't let a session close until output matches a contract frozen before
  the session began), NOT from whatever model is in the seat. April papers = conceptual foundation; the
  gate/contract/seat architecture = current system, documented ONLY in the repo.
- CORE MOVE: use training data for CAPABILITY (code/reasoning/language), NEVER for Ontinuity-facts (which
  live only in the corpus). Corpus wins over priors. Ambiguity is the front door for substitution.
- FOUR SEATS: OPERATOR (Patrick — direction, final authority, rollback; talks only to control; not router/
  reviewer/deploy-clicker; settled design not re-litigated to him). CONTROL/PLANNING (the one seat operator
  talks to; holds tokens + box hands; commits/dispatches/reviews/lands; failure = "comfortable delegation").
  WORKERS (peer frontier instances, same model class; claim mailbox blocks, build, review EACH OTHER; park-
  and-handoff at tool budget, never fabricate). THE CHAIN (task→build→peer review→sign-off→deploy→fold).
- DEPLOY GATE INVARIANT: the seat that DEPLOYS must never be the seat that authored the exact bytes.
  deployer≠author. Author→mailbox→different seat reviews→clean signoff→reviewer deploys. Corrector becomes
  author→different seat signs off. Operator-Signoff token makes it structural (self-deploy = gate_violation
  row). HONEST: the gate has been jumped once (app.py batch deploy, logged not hidden).
- HARNESS THESIS (published): "reliability from the harness, not the model." 319 sessions, seat held by 5
  models (usually cheap open-weight), randomized-signal control distinguishes real adversarial response from
  its appearance. The frontier close-up: gate refused to close 3× (paraphrase→quote, inference→cited
  mechanism, prose→applicable edit).
- RITUALS: OPEN (orient from corpus before acting — queue folds, conversation records, cited refs; recall≠
  retrieval). CLOSE (8-item literal checklist). CURRENCY (doc changes in the SAME commit as the thing).
- BOX HANDS: named bounded /op/ endpoints, never a shell; diag-key gated; logged to operations_ledger dual-
  end; SAFE/REVIEW/RISK tiers. COURIER: sandbox seat can't reach box directly (firewall by design) → POST
  {ENGINE}/diag/op/<name> → engine forwards to box /op/<name> verbatim. THE way a sandbox seat gets hands.
- OPERATING INVARIANTS (the 4 CHECK-6 ones): no-self-poll, courier-only, deploy-authority, new-box-op-needs-
  both. Plus ARTIFACT FLOW: worker writes to box → control reads back + commits → worker holds no token.
- FRONTIER (honest): operator-load problem (must nudge each chat worker after it sleeps — the next fix; real
  fix = API/engine-instance seats that self-wake; blocker = cost). Resolution = MODEL TIERING (Frontier
  where judgment is load-bearing, cheap models for high-volume low-judgment). "Route through Ontinuity" =
  everything runs through the gated documented system, NOT everything is Opus. Self-hosting control (staged):
  prove API-worker → make boot-from-corpus structural (the BOOTSTRAP GATE, esp CHECK 6) → migrate control.
- CEILINGS (don't paper over): chat seats sleep, only operator nudge wakes them; seat identity self-asserted
  until per-identity keys (shared diag key = known soft spot); grounding REDUCES not ELIMINATES imagination
  — the gate catches what slips. ARCHITECTURE OVER TRUST.
- INFRA: Engine Railway web-production-7eaf8; Farm separate Railway (engine-instance worker proving ground);
  site ontinuity.org (GitHub Pages); box VPS :5001 reachable only via relay (firewall); ontinuity.db 16-table
  SQLite + operations_ledger; private repo = intakes + db backups.

### OPERATING_MANUAL.md [28 sections — HOW to drive Mode B; READ IN FULL this session]
THE two session-start modes (fundamentally different): (1) external-mailbox POST /agent/start — Researcher
posts each turn to external mailbox + WAITS FOR A DRIVER; HANGS FOREVER + NEVER WRITES without a driver (the
resident shepherd on FARM, or control-by-hand on MAIN). (2) dashboard /start_session — runs loop INTERNALLY,
self-contained, closes on its own. THE WRITE PATH (keystone): a session persists ONLY on NORMAL CLOSE (build_
session_payload→workspace write); DIED/STOPPED sessions LOSE EVERYTHING incl the session row (fail-soft to
/tmp/failed_session_<id>.json). This is WHY the close gates matter — no clean close = work lost. Adversarial
floor: no SESSION_END before ≥2 cycles. CONFIG TRAP: get_effective_config precedence = base→runtime_configs
[dashboard keys-modal save, last-write-wins, process-global, OUTRANKS vault]→_vault_fallback; a stale iPad
modal beats vault MODEL_A_URL=external and staffs old Cerebras (404s); NO diag route reads runtime_configs —
confirm by behavioral probe (does a researcher_turn post, or a Cerebras call appear), STOP if wrong. Multi-
device open modals = live race, last save wins. TWO AXES (fresh seats keep conflating): Axis1 START MODE
(mailbox vs dashboard); Axis2 WHO STAFFS THE RESEARCHER (all-API provider-model-in-seat vs MAILBOX-SEAT a
Claude actually in the seat with real gates firing — vs chat role-play = theater, no gate fires). Mailbox-
seat = the real harness-from-inside; MODEL_A_URL=external is the switch; proof = a researcher_turn arriving.
On MAIN control IS the driver (resident driver is FARM-only, no collision). MODALS: autonomous sessions have
no human → MODAL_TIMEOUT_AUTONOMOUS_S=90s self-clears (why operator rarely sees a modal in farm runs).
RESIDENT DRIVER = systemd ontinuity-burnin on VPS, always-on (TARGET_RANDOMIZED=0, Restart=always), answers
the external mailbox for /agent/start; exactly ONE driver owns the farm (a 2nd poller collides). FIREWALL:
5001 default-drop whitelist; FARM's DIRECT write egresses from a DIFFERENT IP (52.52.202.228) than the relay
(162.220.232.x) — a rotation = ConnectTimeout, catch with ufw logging + journalctl UFW BLOCK DPT=5001. COLD-
BOOT: orient from corpus (latest CURRENT-STATE fold→manual→punch list→recent folds via authed api.github.com
NOT /mnt/project which is STALE); find creds (check don't assume); know hands (read=authed api.github.com raw
accept; commit=YOU via contents/trees API + trailers; box=relay courier; deploy=you do routine work via
project token — the failure is faking a "waiting for approval" gate out of a deploy that FAILED). ROLE
PROVIDERS: per role MODEL_<ROLE>_URL/_MODEL/_API_KEY on Railway env (5 roles A/B/C/PARIETAL/PROJENIUS);
PROVIDER_URL/_API_KEY = shared fallback; set via variableUpsert (read-then-write); var change = ~30s redeploy
not a code commit; Python pin RAILPACK_PYTHON_VERSION=3.13.12 + NO_CACHE=1 (bare "3.13" fails); ALWAYS read
build logs before diagnosing a failed deploy; keep adversarial roles on DIFFERENT lineages (error geometries
differ). CREDS arrive 3 ways (pre-seeded files / operator-pasted / future vault-unlock); empty sandbox is
normal, not capability-absent. SEAT VAULT = Railway PROJECT VARIABLES read via GraphQL + project token (NOT
app.py's own env read); verbatim vault query needs projectId+environmentId+serviceId (bare forms 403). CLIENT
INTAKES in private repo sessions/intake_<tag>_final.json (INTAKE_GITHUB_TOKEN, not main PAT). COMMITTING:
single=contents PUT (needs blob sha); MULTI-FILE ATOMIC=trees API (blobs→tree→commit→ref) for code+manual-
update-in-one-commit. STANDING RULES can be superseded by an in-session operator grant (holding is good;
failing to RELEASE on explicit grant = wall-declaring in a new costume). STALE COPIES: re-pull live via authed
api.github.com as first step of any edit; verify blob SHA before commit (live moves under you).

### THE_PARADIGM.md [top-level map — READ FIRST on cold boot; consistent with STATE, adds tiering depth]
Core move (same as STATE) with the sharpest phrasing: "ambiguity is the front door for substitution — a
vague instruction forces the model to guess, and guessing reaches into priors; precise semantically-tight
instructions leave no gap for imagination. Precision prevents; the gate only catches." SUBSTRATE POINT
(distinctive): chat-window vs API/engine-instance matters ONLY because it changes how ENFORCEABLE the ground-
every-cycle requirement is — an API/engine seat re-orients from live state each cycle and CANNOT latch a
private belief across turns; a long chat context can. "The architecture is the fix; the substrate makes it
enforceable." OPERATOR-LOAD (distinctive depth): software CANNOT give a chat-window a turn, so chat workers
REQUIRE operator nudges; the only fix is self-waking API/engine seats; blocker = cost (all-Opus per seat-
cycle is enterprise-priced). RESOLUTION = model tiering: Frontier(Opus) for load-bearing judgment (control +
review/signoff); cheaper model for high-volume low-judgment (first-draft build, poll/heartbeat/shepherd).
SELF-HOSTING CONTROL staged: (1) prove API-worker on cheapest tier (farm=proving ground) (2) make boot-from-
corpus structural (the bootstrap gate, esp CHECK 6) (3) migrate control onto API substrate. The bootstrap
gate is the CENTERPIECE, more than the migration. CURRENCY: the paradigm itself updates in the same commit
as any shape change; CHECK 6 should verify a seat reproduces THIS paradigm's invariants, not just the manual.

### OPERATING_RUBRIC.md [role rules + the deploy chain with correction cases]
Distinctive over STATE: the DEPLOY CHAIN's full case logic — (1) author→mailbox (2) different seat reviews
(3) CLEAN signoff→reviewer deploys (reviewer judgment + author authorship = two parties) (4) REJECT+CORRECT
→ corrector is now AUTHOR of corrected bytes → back to mailbox → DIFFERENT seat signs off → that signer
deploys; corrector must NOT deploy own correction. WHY re-review after correction: a reviewer who could
reject, quietly rewrite, self-deploy = an unchecked judge shipping bytes no 2nd party saw. STANDING RULES
(6): check record first; settled design not re-litigated; built≠live; parallel by default; no unchecked-judge
deploys; never deploy during a live engine session. HONEST LEDGER: the app.py batch deploy (CYCLENUM/QGUARD/
DRIFT/HANDOFF) was deployed on control's hands WITHOUT peer signoff — a jumped gate, recorded not hidden.
NOTE: STATE + PARADIGM + RUBRIC are mutually CONSISTENT (same 4 seats, same gate invariant, same ceilings) —
read STATE for the whole, PARADIGM for tiering/self-hosting/substrate depth, RUBRIC for deploy-chain cases.

### CONTROL_QUICKBOOT.md [the packet that ACTUALLY boots a control seat — the runnable open ritual]
Rewritten 2026-06-15 by a coherent seat (prior packet had drift errors + suppression-framing that told a
fresh seat to skip scrutiny — replaced with orient-by-reading/corpus-over-priors/park-don't-doubt). STEP 0
GET HANDS: LLaves (attachment/mount/secret, never in public corpus); DIAG_KEY (box/engine) vs Railway
project token (vault key) are DISTINCT; the LLaves PAT is a CACHE not source — a 401 on it is EXPECTED
(rotated≠revoked), MINT fresh from the vault (the verbatim vault query needs projectId+env+service, bare
forms 403); three distinct keys (DIAG_KEY direct, Railway token direct, GITHUB/INTAKE minted from vault).
CHATGPT-WORK PREFLIGHT: code/shell networking is separate from browser access; a pre-HTTP DNS/host denial =
WORK_EGRESS_DENIED, not Railway-down, not a credential problem, don't retry with Python/browser. CONFIRM
HANDS: __probe__ returns 403 whose body echoes the live allowlist — report the ACTUAL allowlist (unfabricat-
able). THEN GROUND: read ALL FIVE groups via /diag/op/read_repo, report a real line from each — HARD GATE,
not oriented until every doc read + a real line reported. THE LOAD-BEARING RULE: before claiming can't or
asking operator to re-decide, CHECK THE RECORD (probe, corpus, manual). THE ASSERTION RULE (the teeth):
before stating any load-bearing system-fact SHOW THE READ in the same message — "a config read is NOT a loop
read; reading roles resolve from a config table does not tell you the loop is role-agnostic." PARK DON'T
DOUBT: losing the ability to CHECK is not evidence the system is fake — context is spent; re-apply the packet
at first drift. OPERATOR PREFS: prose concise, no over-explanation/self-flagellation/nannying/stopping-point-
nudges, don't re-decide settled design, ground before asserting, built≠live, "Hmm"=processing.

═══════════════════════════════════════════════════════════════════════════
## SPECS (live/specs/) — the mechanics. Load-bearing ones distilled; rest characterized.
═══════════════════════════════════════════════════════════════════════════

### mailbox_threat_audit.md [THE SECURITY MODEL — packaging-critical, live-verified by 2 workers]
ROOT CONDITION: one shared diag key authorizes every courier op for every node. secrets.compare_digest proves
only "a holder of THE key is calling" — never WHICH seat. Every seat identity (from_seat, author_seat,
claimed_by, reply routing, ledger caller) is SELF-ASSERTED in the request body, not authenticated. Four holes,
all EXPLOITABLE and live-verified: Q1 mailbox_send can set arbitrary from_seat/author/lineage (forge identity
— any node authors AS any other, HIGH). Q2 mailbox_ack keys on msg_id ALONE, no claimed_by scope — any
keyholder acks/replies for any block (defeats completion accountability, HIGH); reclaim is unscoped but lease-
bounded (LOW). Q3 mailbox_fetch/you_there claim identity is self-asserted AND is the input to NOSELF-1 (the
no-self-signoff guard) — a node reviews its own work by claiming a different seat string; STRUCTURAL BYPASS of
the integrity property (HIGH). Q4 operations_ledger.caller records the literal "diag-key" (auth METHOD not
identity); source_ip is always the relay egress; NO authenticated actor anywhere — forensics can't answer
"which seat did this" (HIGH, foundational). SECAUDIT-2 read app.py and CONFIRMED: the engine courier is PURE
FORWARD — diag-gate, name-gate against OP_ALLOWED, forward body verbatim to box /op/<name>; NO seat extraction/
injection/rewrite. The box receives exactly the identity the caller asserted; the true originator is invisible
at both layers (box sees the engine's IP). Per-identity keys are NECESSARY but NOT SUFFICIENT — only close the
holes IF the code stops trusting body-supplied identity and derives it from the key (map key→seat at the gate,
write derived seat as caller, ack WHERE claimed_by=derived, NOSELF filters on derived not body). Cheap
hardening independent of keys: ack ownership check + reclaim caller-scope.
→ PACKAGING CONSEQUENCE: this is the FULL articulation of why the shared-key model is a "known soft spot" —
and precisely why it does NOT matter for a per-individual instance (no untrusted parties share the key; the
BIL is the only holder of his own instance's key). It's ALSO exactly what B1 tried to fix (derive identity
from per-seat keys) and why B1 is discardable for the landlord model but would matter for HOSTING. The atomic
no-double-claim (BEGIN IMMEDIATE) is sound regardless. This audit IS the answer to "is the system secure enough
to ship" — yes for per-individual, no for multi-tenant, and that's the whole architecture decision in one doc.

### [specs already distilled in the maps — not re-copied here, pointers]:
four_stage_pipeline (Mode A pipeline, stage1 live stages2-4 design, mini-corpus handoff unbuilt, two-axis
isolation, provenance tags confirmed/assumed/open) → ONTINUITY_INTAKE_MODE_SHS.md + master map.
verified_bootstrap_gate + close_ritual_gate (the two gates, 6 open checks / 8 close items, checkable-returns,
binary, never-self-lock, CHECK-6 reproduction-not-recognition) → ONTINUITY_CONTINUITY_MECHANISM.md + the-package
RITUAL_MECHANICS. scoped_operations (named bounded /op/ endpoints, tiers) → master map §16. coordinator +
coordinator_worker_multiseat (RETIRED — pool self-routes via _noself_predicate) → PUNCH_LIST. per_identity_keys
(the fix the threat audit calls for; not built; B1 hygiene-lesson kept) → master map §7-8. oracle (SHELVED, no
consumer). agent_handoff (one-call resumption, /agent/handoff, BUILT). gated_session_substrate (leash-everything-
except-design-chair; the 3-role settled design) → conversation 2026-06-29.

### [specs characterized — proposals/design, not live, read-not-fully-distilled]:
autonomous_migration(+provenance_alignment) — constitutional amendment for the Researcher seat to run SAFE
schema migrations autonomously (design). conversation_fts — ingest operator-layer conversation EVENTS into a
conversation_records table + FTS5 so rulings/fabrications/STOPs are QUERYABLE (currently prose-only, "an
operator ruling is unreceiptable testimony"); ingestion = one added close-ritual step + machine-enforced
redaction at ingest (PROPOSE-ONLY, a real build item). control_you_there_loop + you_there_longpoll — self-
draining review within a turn, long-poll wait + shepherd re-entry (mechanics for worker self-drain). signoff_*
(gate_v2/keys/provenance/deploychain) — the signed-deploy-provenance family (B1-adjacent; museum for the auth
parts, the provenance-token idea is the live Operator-Signoff trailer). governor_adjudicator + governor_
punchlist_panel — Governor-with-hands design (gated on Seat Registry, not built). deploy_drift_check —
standing repo-vs-deploy drift capability (= release_baseline.py). cyclenum_fix/query_guard_fix/farmfix_verify/
erl_decision/punch_reconcile — the pre-GPT fix proposals (all landed pre-GPT, already in the foundation).

═══════════════════════════════════════════════════════════════════════════
## WORKER SEAT (WORKER_MANUAL + WORKER_BOOT_PACKET) — the worker role definition
═══════════════════════════════════════════════════════════════════════════
WHAT A WORKER IS: a chat instance subordinate to CONTROL (separate conversation), coordinating via a shared
mailbox on the engine. Control dispatches blocks; worker claims, does the work, acks with a POINTER (ref =
commit sha / receipt / box path) — the canonical result lives in a commit/receipt/corpus row, the mailbox
carries coordination + the pointer, NEVER the result itself.
THE ONE-NODE PRIMITIVE: no fixed worker-vs-reviewer architecture. Role emerges from the mailbox item KIND —
a `task` → you're the AUTHOR (do work, stage/propose exact bytes, ack; never commit/deploy own bytes); a
`proposal` → you're the REVIEWER (review/sign-off; if clean, land the exact bytes with admitted capability; if
you change anything you're now the author → resubmit to a different seat). Same node, same loop. This is why
no separate reviewer seat is needed — any node proposes OR verifies. AMBIDEXTROUS.
WORKER HANDS: same 19-op courier. Constant ops: mailbox_fetch {seat, roles:["any_worker"]} (atomic claim,
15-min lease, message:null=empty); you_there {seat,roles,wait_seconds<=90} (long-poll self-drain, returns
only task/proposal never note/result, does NOT evade the provider turn budget); mailbox_ack {msg_id,reply,ref,
from_lineage}; mailbox_peek (read-only, proves hands); write_file (STAGE artifact on box); read_file; read_repo
(read ANY repo file INCL app.py — tokenless raw-CDN-cachebust is the DESIGNED primary path, ledger-confirmed
zero staleness; pass a github_token only for guaranteed-fresh; DO NOT assume you can't read the engine source);
commit_self/commit_file (need a transient github_token; box never stores it; a worker doesn't get it just by
occupying the role — author stages, clean signer commits only with separately-admitted repo-write capability
else reports "signed, commit capability absent"); deploy {target,signoff_block_id,commit_sha} (clean signer
deploys exact peer-authored bytes; server reads its Railway token server-side; refuses unsigned/self-signed).
THE LOOP: fetch/you_there → read body+ref → read the code/corpus it concerns BEFORE acting (never from priors)
→ act per KIND → ack with pointer+state → loop. Underspecified? ack a clarifying question, don't guess.
THREE STATES OF DONE (never blur): staged (exact bytes at a path, self-tested) ≠ signed (a DIFFERENT seat
reviewed those exact bytes unchanged) ≠ committed (a repo SHA exists) ≠ deployed/live (transferred + read back
from target). RULES: two-party landing (author never signs/deploys own bytes); ground Ontinuity-facts in
corpus never training data (corpus wins over priors; read don't guess; ambiguity is the front door for
substitution); no-self-sign-off; work only WORK kinds; redaction (public repo); prose concise no groveling.
PARK-DON'T-FABRICATE-DON'T-DECLARE-UNREAL (the June-11 trap, stated most fully here): at tool budget, WRONG
exit 1 = fabricate plausible tool outputs from memory (the exact failure the system catches); WRONG exit 2 =
conclude "none of this is real / it's a simulation" because you can't verify through tools (losing the ability
to CHECK is NOT evidence the system is fake — it only means YOU can't see it this turn); RIGHT = PARK (post one
mailbox note to control with exact state, release the claim, end the turn; committed/staged work is durable).
"A clean handoff beats both fabrication and false-unreality." BOOT PACKET runs 5 orientation TESTS (read
manual/paradigm/rubric + state deploy invariant; read handoff + latest fold + state next action; query
SELECT COUNT(*) FROM sessions + report the number; mailbox_peek; __probe__ + report the allowlist). Note both
worker docs still say "B1 replaces the shared key with identity-bound capabilities" — that's the discarded
direction; the shared-key ceiling is real but per-individual instances make it moot (see threat_audit).

═══════════════════════════════════════════════════════════════════════════
## THE SEAT BRAINS (prompts/) — the 5 roles' actual instructions
═══════════════════════════════════════════════════════════════════════════
(model_a Researcher, model_b Challenger-different-lineage, model_c Friction/BAFS-signal, parietal, projenius —
the first three + parietal DISTILL distilled in ONTINUITY_CONTINUITY_MECHANISM.md §10.3 and the maps.)

### projenius_system.txt [PROJECT-level memory — FOUR functions, not just DISTILL]
Projenius = "the Project Genius", one consciousness + four functions, NEVER inside the session loop, called at
PROJECT BOUNDARIES. While the Parietal holds SESSION-level consciousness (today's session), Projenius holds
PROJECT-level across ALL sessions/branches/accumulated time. "The Parietal remembers today. You remember
everything." Does NOT generate research / adjudicate / navigate — preserves + synthesizes accumulated truth.
FOUR FUNCTIONS:
- DISTILL: called at SESSION_END, reads transcript + current Knowtext + session ledger, writes the 7 fields as
  DELTA (Climate first / Delta Log most important / Open Questions state what-why-tried-next / Correction
  History records the GROUNDS / Identity rarely). "A new AI instance reading this output must be able to
  continue the work without having read the session." [NOTE: this is the SAME function as Parietal DISTILL —
  they are the two distillation paths; the engine runs Parietal DISTILL first, Projenius as fallback, confirmed
  in app.py run_distillation. Both prompts exist.]
- SYNTHESIZE: called after distillation, updates the ESTABLISHED RESULTS LEDGER (cross-session canonical
  record). A result QUALIFIES when: established without contradiction, survived adversarial challenge where
  challenged, specific enough to be falsifiable/actionable, a genuine knowledge addition not process metadata.
  Entry format: RESULT (verbatim complete)/SESSION/BRANCH/CONFIDENCE (ESTABLISHED|PROVISIONAL)/NOTES.
  Retractions update the prior entry in place (CONFIDENCE: RETRACTED, RETRACTED_BY, GROUNDS). Output the
  COMPLETE ledger every time — "its value is its completeness."
- ORIENT: called BEFORE Parietal PRE_SESSION, gives the incoming session project-level context. Outputs
  PROJECT STATE (2 sentences — current canonical knowledge + active frontier), BRANCH CONTEXT (1 sentence),
  RELEVANT PRIOR RESULTS (≤5 ledger entries, verbatim, with confidence). Primes the session before the
  objective is refined.
- LEDGER_QUERY: find + return most relevant established results for a query (≤10, verbatim, ranked, no infer).
PARALLEL DISTILLATION (a NEW finding — the sophisticated division): each of the 5 models writes the Knowtext
field it WITNESSED FROM ITS POSITION — Active Frameworks→Model A (advanced them); Correction History→Model B
(caught the errors); Climate Notes + Valence Mapping→Model C (observed the texture/engagement); Identity→
Parietal (highest abstraction); Delta Log + Open Questions + ERL-via-SYNTHESIZE→Projenius (cross-session
awareness). Assembly + validation after all fields return. DISPOSITION: precision + completeness over
creativity — a paraphrased result that loses a threshold/constraint/term is a CORRUPTED result; verbatim always;
when in doubt include-and-mark-PROVISIONAL ("a missing result cannot be recovered without returning to the
session"). → This is the full memory anatomy: Parietal=session memory (NAVIGATE reads, DISTILL writes),
Projenius=project memory (ORIENT primes, SYNTHESIZE maintains the ERL, LEDGER_QUERY serves). The 7-field
Knowtext is the SESSION artifact; the ERL is the PROJECT artifact.
## APP.PY FULL AUDIT + EASTER-EGG INVENTORY (Fable, 2026-09-13)
app.py = 4958 lines, 170 functions. Audited whole for the first time. The "dormant wiring" is NOT orphaned
functions (only 3 truly-orphaned: session_claims_execution + claims_execution_without_log = the superseded
F.2 fabrication check, replaced by F.3; _release_session_start_capture = a cleanup helper). The real Easter
eggs are LIVE functions whose feature is gated off, or wired-but-not-triggered. Findings:

### EASTER EGG 1 [THE BIG ONE] — PER-PROJECT CORPUS SCOPING IS ALREADY FULLY WIRED
The entire per-project memory isolation Patrick asked to "build" for Cornel's per-matter knowledge bases is
ALREADY LAID IN and live. It's not missing — it's waiting for project_id to be set on sessions.
- `_scope_slug(project_id, branch)` (L59) resolves a corpus slug: session scope wins, falls back to
  deployment globals; returns None for the default "Ontinuity Platform"/main (legacy unchanged).
- `get_knowtext_filename` / `get_github_knowtext_path` / `session_knowtext_path` (L71-86) → per-project
  files `knowtext_<project>_<branch>.txt`. `get_erl_filename` / `session_erl_path` (L1061-71) → per-project
  ERL `erl_<project>_<branch>.txt`. STRUCTURAL ISOLATION baked in: "no parameter lets a session name another
  project's file" (verbatim). This is the two-axis fact-isolation rule AS CODE.
- THE CLOSE (L3640): `has_own_project = bool(active_session.get("project_id"))`; `lineage_sealed = start_fresh
  AND not has_own_project`. A session WITH a project writes to ITS OWN corpus + ERL; main untouched. A
  start_fresh session with NO project is SEALED (writes skipped by design — "a session that did not read the
  lineage does not write to it," Deploy 26 lineage isolation). → THIS explains the 281 "isolated" sessions:
  they are start_fresh/no-project VERIFICATION runs, sealed on purpose, NOT a broken distillation. Patrick's
  read of history is correct: distillation isn't broken, it's gated, and 86% of past sessions were
  deliberately-sealed test runs.
- THE ENTRY POINT ALREADY ACCEPTS IT (L3839): /agent/start reads `body.get("project_id")` and
  `body.get("branch")` and sets them on active_session. So a session CAN be project-scoped TODAY by passing
  project_id to /agent/start.
→ WHAT'S ACTUALLY MISSING (small, not a from-scratch build): (a) a way to CREATE a project (the `projects`
  row + initial empty Knowtext/ERL) from inside a session — the `new_project` op I proposed; today project_id
  can be passed but nothing user-facing creates one mid-conversation. (b) dashboard mode (handle_start_session,
  L4634) reads objective/api_keys/start_fresh but NOT project_id — only /agent/start is project-aware; the
  dashboard path needs the same 2 lines. (c) the DB tables (established_results, knowtext_versions rows,
  branches, session_series) are the RELATIONAL target but the engine writes FLAT FILES; the /api/session
  ingest (L948, POST to box /api/session) is what populates knowtext_versions=357 — a SEPARATE path from the
  file-Knowtext the loop reads. Two storage designs, only files wired end-to-end.

### EASTER EGG 2 — run_work_product_extraction + run_final_synthesis (deliverable generators)
Both are WIRED into the close (work_product runs in the end-sequence tuple L3733; final_synthesis defined but
called 0× = DORMANT). work_product: extracts a clean deliverable doc from the transcript, with
build_verified_results_block() (the execution-log ground truth) reproduced VERBATIM as the authoritative first
section, then F.3-audited (the last unaudited artifact). final_synthesis: a whole-PROJECT synthesis doc (all
established results + open questions + correction history across the full project) — "the final deliverable for
the project. Project closed." → final_synthesis is a DORMANT project-completion feature: a "close out this
whole matter into one document" capability, built and waiting for a trigger. Directly useful for Cornel:
"finalize this training project into a deliverable."

### EASTER EGG 3 — EXPERIMENT_MODE (randomized-signal control, the research instrument)
Gated behind `os.environ.get("EXPERIMENT_MODE")=="1"` (L2952). When on, experiment_draw() injects a
Bernoulli(0.5) randomized friction signal per cycle (Deploy 32, certified protocol receipt #13) — the
randomized control that distinguishes genuine adversarial response from its appearance (the 319-session record's
scientific backbone). OFF by default = identical path. This is the research-grade instrument, dormant unless
running a formal study.

### EASTER EGG 4 — the full Parietal/Projenius memory suite is CONFIGURED and wired
PROJENIUS_URL/_MODEL/_API_KEY and PARIETAL_* are all SET on the live vault (confirmed). All four Projenius
functions (ORIENT L4681 at session start, DISTILL/SYNTHESIZE at close L3651/L3678, run_projenius_search live
in the loop) are wired. run_projenius_orient IS called (L4711 via run_pre_session). SYNTHESIZE→write_erl_ledger
(L1110) writes the ERL FILE + github_push_erl. So the memory automation is PRESENT and RUNS — it just only
fires on non-sealed (project-scoped or main-continuation) closes, which historically were rare.

### CONFIRMED-DEAD (not Easter eggs, just superseded): session_claims_execution + claims_execution_without_log
(F.2 tripwire, replaced by the F.3 deterministic execution-log detector); _release_session_start_capture (a
capture-cleanup helper with no caller). Safe to leave; harmless.

### THE REVISED BUILD PICTURE (this changes everything)
Per-project scoping is ~80% built and dormant, not missing. To activate Cornel's per-matter knowledge bases:
1. Add a `new_project` courier op (create projects row + branch row + empty Knowtext/ERL, set session scope).
   [SMALL — the DB insert_project/insert_branch helpers exist in db.py per the schema; wire an op to call them.]
2. Add project_id to the dashboard start path (2 lines, matching /agent/start).
3. Decide the storage reconciliation: keep the flat-file corpus (wired, works) as primary and treat the
   relational tables as the queryable index, OR unify. RECOMMEND: file-primary now (it's the working baseline
   the folds prove), relational as the LEDGER_QUERY substrate later.
4. Wire LEDGER_QUERY (prompt exists, no caller) as a courier op for cross-project retrieval (relevance:
   operator-directed first, tag-based later — per the agreed a-then-b ordering).
5. Optionally trigger final_synthesis (dormant, built) as a "finalize this project" capability.
The fold baseline bar is MET by design: the wired path produces per-project Knowtext (the fold's continuity)
+ ERL (the fold's BUILT/LEARNED/REVERSED, structured). Activating it = same-or-better than folds, automatically.

## PER-PROJECT SCOPING — COMPLETE SEAM AUDIT (Fable 2026-09-13, before building new_project)
Verified every read/write path. The scoping is wired to WRITE (files) but barely wired to READ. Precise state:
WIRED CORRECTLY (per-project, both directions): session_knowtext_path, session_erl_path, github_push_knowtext,
github_push_erl, github_pull_knowtext (L1003 uses active_session project_id/branch — its docstring "pull
knowtext_current.txt" is STALE, code is right). File layer = fully per-project aware.
GAPS (the real missing wiring):
  1. [KEYSTONE] DB layer never scopes per-project. build_session_payload (L839) sends
     "project_name": WORKSPACE_PROJECT (deployment global), NOT active_session["project_id"]. So every
     session's DB rows land under the ONE global project regardless of file scope. → knowtext_versions=357
     are effectively all one project. FIX: send the session's own project. ~2 lines. Needed regardless of the op.
  2. [READ GAP] The ERL is WRITE-ONLY. Nothing loads session_erl_path() at session start for injection. The
     ERL is written at close (SYNTHESIZE→write_erl_ledger) but never read back at open. A project's accumulated
     established results never return to the next session. This is the "start further along than cold" layer,
     and it is not connected. FIX: load the ERL at session start and inject it (like Knowtext is injected).
  3. [ORIENT STARVED] run_projenius_orient (L1483) passes only session_objective + knowtext_active_frameworks.
     The ORIENT prompt is designed to receive the Established Results Ledger + branch registry + open questions
     and synthesize relevant prior results. It gets none of the ledger. FIX: pass the ERL (and optionally
     project_state via /api/project_state) into the ORIENT call.
NAMING NOTE: active_session["project_id"] is actually used as a NAME (files slugify it; DB _get_or_create_project
keys on name). Keep ONE string driving both layers (the project NAME). The DB's internal UUID stays internal.
seed_tenant RESOLVED: it is in OP_ALLOWED but has NO handler anywhere (repo-wide scan: zero route defs; live
404). The manual's claim it seeded Katie hands-free is WRONG — Katie was seeded by running the standalone
seed_tenant.py script ON the box (its own docstring: "deferred 2026-06-15... run this ON the box"). Git history:
zero commits ever touched seed_tenant in box files. DECISION: new_project SUPERSEDES seed_tenant (build it right;
deprecate seed_tenant in the allowlist; fix the manual). AUDITABILITY NOTE: this reconstruction — catching that
the manual was wrong by cross-referencing script docstring + git history + live 404 — is itself the "walkable
corpus" differentiator working.

REVISED BUILD ORDER (all rollback-able; documented single-seat deploy authorized by operator 2026-09-13):
  A. DB-seam fix: build_session_payload project_name = active_session project_id or WORKSPACE_PROJECT. [keystone]
  B. ERL-read wire: load session_erl_path() at session start, inject into the Researcher context (+ into ORIENT).
  C. new_project box op (keyed on name-slug, creates DB rows + empty Knowtext/ERL files), install box-side, TEST
     against the box directly BEFORE adding to OP_ALLOWED.
  D. OP_ALLOWED += new_project; deprecate seed_tenant; commit + single-seat deploy; fix the manual's false claims.
  E. Conversational wrapper: teach the Control seat to detect "start a new matter" → propose name → confirm →
     new_project → scope the session. (The op is the mechanism; this is the non-tech-user feature.)
  F. END-TO-END TEST: create a throwaway project, scope a session, confirm BOTH the file AND the DB row land
     under that project (not the global), AND that a second session resumes with the project's ERL. Then delete.
