# CONTROL HANDOFF — current state + the single next action
# Updated 2026-09-15 by Control (claude.ai-chat:claude-fable-5.1) — INSTALL TWO PROVISIONED (runbook Phase 2 executed; C6 first boot pending). Prior 2026-09-14: reflex-layer research shelved to V2-E. Prior update 2026-09-13 (post-GPT rollback reconciliation; B1 to museum/).
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the latest CURRENT-STATE TOUCH POINT fold at the queue tail.

## STATE AT FOLD
- LIVE ENGINE: MAIN = commit `5640170` (app.py blob `35502fd0` = pre-GPT `9a7eac2a` + the kept B5-P raw-evidence layer; ZERO B1). FARM = `f9696c49`. Courier allowlist 19 ops, diag-key (`X-Diag-Key` header or `diag_key` query). Full Control boot returns oriented:true. 328 sessions intact.
- THE B-BLOCK / B1 DIRECTION (GPT-driven, 2026-09-03..11) IS DISCARDED. Its code, specs, manifests, tests, and plan docs are preserved under `museum/b1/` and `museum/b-blocks/` (git history + bundle `e15f5f46`) — history, not the live path. KEPT from that period: B5-P raw-evidence preservation (live, `live/RESEARCH_PRESERVATION_CONTRACT.md`), the B0 baseline (evidence, `live/baselines/`), and GPT's security hardening (no hardcoded secrets in `push_to_github.py`/`shepherd.py`; `X-Diag-Key` header + no-redirect openers in shepherd_alert/governor/burnin_resident/model_client; `live/box/file_server.py`; the 19-op reconciled `live/bootstrap/gate.py`).
- BOX: `box_ops.py` + `seat_mailbox.py` installed at the pre-GPT bytes (write_file + restart); `file_server.py`, `gate.py`, `shepherd_alert.py`, `db.py`, `workspace_db_endpoint.py` at the kept versions; `trusted_deploy.py` remains on disk but is unreferenced (inert; no delete op exists).
- DOCS: THE_PARADIGM, OPERATING_RUBRIC, OPERATING_MANUAL, CONTROL_QUICKBOOT (+SNIPPET), CONTROL_HANDOFF, PUNCH_LIST restored to pre-GPT/pre-B1 text; WORKER_MANUAL/BOOT_PACKET/QUICKBOOT keep the Sept-5 currency fixes (19 ops, header key) with B-block references removed.
- Recovery + mapping record: `live/conversations/2026-09-12_recovery-mapping-two-product-packaging.md`; maps: `live/ONTINUITY_MASTER_SYSTEM_MAP.md`, `live/ONTINUITY_CONTINUITY_MECHANISM.md`, `live/ONTINUITY_PACKAGING_PLAN.md`; the packaging project itself lives in the PRIVATE repo `projects/the-package/` (runbook, roadmap, punch list, ritual mechanics).

## SINGLE NEXT ACTION
C6 FIRST BOOT of install two (operator step): in the "Ontinuity 2" Claude project with LLaves.txt attached, paste the parameterized CONTROL_QUICKBOOT from `ontinuity-two/live/`; the seat must report the REAL allowlist from `__probe__` (engine-two), a REAL line from each of the five doc groups, and the one-line next action; then run its close ritual so a record/fold/handoff land in `ontinuity-two` (Section G check 5). Phase 2 gate = all five Section G checks. Then ROADMAP Phase 3 (non-Claude seat).
STATE OF INSTALL TWO (2026-09-15): corpus `PatrickKillebrew/ontinuity-two` seeded fcfcfd0; Railway `engine-two` (this repo @89fa24a); Hetzner box `ontinuity-two-box` (new Hetzner project `ontinuity-two`; IP in engine-two's vault WORKSPACE_URL). Section G 1/3/4/5 PASS through its own courier. Record: `live/conversations/2026-09-15_install-two-provisioned.md`. Runbook corrections: private repo PROVISIONING_RUNBOOK.md §J. Idle Railway `box-two` awaits operator deletion.

## WHAT SHIPPED THIS SHIFT — THE MAILBOX FIX (root-cause, deployed, proven)
THE BUG (fully diagnosed): the seat_mailbox is a TASK-DISTRIBUTION queue (atomic claim + lease so
two workers never grab the same job) that was being USED AS A RESULT CHANNEL. The claim/lease
semantics that make task-distribution safe are exactly what jammed result-retrieval:
  1. Results (kind=result, to_seat=control) piled up 'queued' because the requester reads via PEEK
     (read-only, never marks done) — nothing drained them. 419 accumulated.
  2. mailbox_fetch claims OLDEST-first (ASC); peek shows NEWEST-first (DESC). Opposite directions,
     so new results were always buried behind the old backlog wall.
  3. peek default limit=20 (max 100) — only ever showed the oldest 20 stuck ones.
  4. Blind drain loops claimed-without-acking, locking messages under ~13-min leases (final jam).

THE FIX (3 surgical changes, backward-compatible — default task-claim path UNCHANGED):
  - seat_mailbox.py (commit 08364cbe): mailbox_fetch now accepts reply_to=<task_msg_id> -> claims
    THAT specific result (correlated fetch), and newest=true -> drains newest-first. New
    mailbox_purge endpoint: bulk-clears result/note backlog for a seat (params: kinds=[],
    older_than_secs, all=true).
  - app.py (commit 6acd4cfe): added "mailbox_purge" to OP_ALLOWED courier allowlist (line 3587).

OPERATIONAL DISCIPLINE (load-bearing, fold into all result-reading): fetch-by-reply_to, then ACK
IMMEDIATELY. Never leave a dangling claim. That is what keeps the channel from re-jamming.

## DEPLOY TOPOLOGY LEARNED THIS SHIFT (was the confusing part — write it down)
There are TWO surfaces and they update DIFFERENTLY:
  - ENGINE (Railway, web-production-7eaf8): updated by Railway deploy. serviceInstanceRedeploy
    rebuilds the PINNED commit (stale!). Use serviceInstanceDeploy(environmentId, serviceId,
    commitSha=<latest main>) to pull the CURRENT commit. Project token uses header
    `Project-Access-Token:` NOT Bearer. Service "web" id 72b20f74..., env 6ff341f9..., project a8dea5f4...
  - BOX (Hetzner VPS, behind {WORKSPACE_URL}): the courier at app.py:3589 forwards /diag/op/<name>
    to {WORKSPACE_URL}/op/<name> on the BOX. Mailbox ops RUN ON THE BOX, not the engine. The box
    runs its OWN copy of seat_mailbox.py on disk. Railway deploys DO NOT touch it. To update the box:
    /diag/op/write_file (path=seat_mailbox.py, content=...) THEN /diag/op/restart_workspace.
  RULE (corpus-confirmed): repo-commit != box-install. They are separate steps. A mailbox/box-op
  change needs BOTH the commit AND write_file+restart on the box.

## TWO-PARTY DEPLOY GATE — RAN IT THIS SHIFT, IT WORKS
The gate (signoff_deploychain.md) needs a 'proposal' row (author) + a 'signoff' row from a DISTINCT
seat, same block_id. /op/deploy: target main|farm|box, requires block_id + signoff_block_id.
dry_run:true runs the full gate with ZERO Railway side-effect — use it first. We ran MAILBOXFIX-1
(author=control, signer=operator): dry-run authorized:true, real deploy authorized but stopped at
"railway env not configured" on the ENGINE (engine lacks RAILWAY_TOKEN/service IDs — known FARM
seam). The actual deploy was done control-side via Railway GraphQL (serviceInstanceDeploy) for the
engine + write_file/restart for the box, under direct operator instruction (system-building, not
autonomous worker work).

## THE SINGLE NEXT ACTION
GOVERNOR PHASE 1 — build the WORKER STATUS PANEL (the single-pane goal, step 1).
  - GOAL: one page (served by the existing governor relay, OUTSIDE the Claude UI) that shows every
    worker seat's status at a glance. Largest visible win toward "see and interact with >2 workers."
  - BUILD: a new read route `/governor/workers` in the live governor_routes.py pattern (server-side
    diag fetch, X-API-Key gated, same-origin) + a Workers panel in governor.html (existing dark
    aesthetic). The roster is DERIVABLE FROM seat_mailbox TODAY — no schema change:
    `SELECT from_seat, MAX(created_at) last_seen, COUNT(*) msgs FROM seat_mailbox GROUP BY from_seat`
    (verified live 2026-06-30: 11 seats). Enrich per-seat with last message kind + claimed/idle +
    whether unacked work is addressed to it. SAFE tier, read-only.
  - PATTERN TO COPY: live/governor/governor_routes.py (the /governor/data route) + governor_relay.py
    (the local same-origin server that runs it outside the Claude UI).
  - THEN (same arc): a per-worker NUDGE affordance (you_there already self-drains a worker's whole
    turn on one nudge). HONEST CEILING — no software gives a dormant CHAT window a turn; the panel
    makes the nudge one tap + surfaces idle-with-work; hands-free wake needs API workers (later).
  - Full grounded plan + the retired-Coordinator reasoning: agent_queue fold 12c97d16;
    gated_session_substrate.md superseding banner (d4dc6bed); PUNCH_LIST DONE entry (8a02cf9c).

## BACKGROUND INFRA THREAD (not the next action — do not front-load over the Governor)
S22 ULTRA local-LLM node — staged at the wireless-ADB connect step, still OPEN as a background thread
(a future local inference provider / second worker). Resume path if picked up: ten-second cable flip
-> `adb tcpip 5555` over USB (fixed port) -> unplug -> `adb connect 192.168.1.141:5555` -> `adb install
termux.apk` -> push+run build_cpu.sh (staged C:\donkeycar\, pinned llama.cpp b5027, disable Phantom
Process Killer). Full detail in PUNCH_LIST OPEN (S22 node). Parked in favor of the Governor build.

## STANDING LESSON (still load-bearing, from prior shift)
Every in-cycle role MUST carry explicit *_URL/*_MODEL/*_API_KEY. A role configured "by omission"
silently inherits the shared PROVIDER_* fallback; null PROVIDER_MODEL -> 404. Web-verify provider
models are still live before wiring them.
