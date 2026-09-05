# CONTROL HANDOFF — current state + the single next action
# Updated 2026-09-05 by successor Control (`chatgpt-work:gpt-5.6-sol`) — B0 complete; B5-P raw-evidence boundary operational after challenged live proof.
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the latest fold at the queue tail.

## STATE AT FOLD
- B0 is complete at commit `7abadca`; its authenticated read-only report
  honestly returned `DRIFT`. The original observation remains the baseline even
  where later work repaired part of the observed box divergence.
- B5-P is LIVE at reviewed commit `3326753`. Railway and the separately
  installed box bytes were verified, the 33/33 code suite passed, and challenged
  session `2026-09-05_09-37-00` / receipt `351` satisfied the eleventh acceptance
  item. The database holds six exact transcript companions, fourteen model-call
  envelopes, one structured Challenge/`UPHOLD`, one `EXPUNGED` retraction, one
  reproducibility manifest, three behavioral observations, and two artifacts.
  All 50 stored digests independently reproduced; available credentials were
  absent from the returned evidence payloads.
- B5-P preserves evidence; it does not prove that Ontinuity reduces fabrication
  by any percentage. The deliberately asserted 50-percent inference was caught,
  upheld, retracted, and replaced with a falsifiable paired-control plan at
  `live/experiment/B5P_LIVE_2026-09-05_COMPARATIVE_TEST_PLAN.md`. That plan has
  not been run.
- Preserved candidates remain non-live: B1 branch
  `codex/b1-scoped-identity` at `a31ffe1`; B3 branch
  `codex/b3-fail-closed-completion` at `12dea5e`; Governor branch
  `codex/governor-observability` at `5e3310d`.
- PLATFORM SUCCESSION PROVED: a fresh ChatGPT Work conversation inherited Control through the existing corpus/boot and 19-op HTTPS courier, then occupied the external Researcher seat in the real engine. No OpenAI-specific engine rebuild or bridge was required.
- Evidence pair: `2026-09-03_14-13-03` failed closed as `incomplete_model_dead` (3 cycles) when the retired Cerebras Challenger returned 404; after a staffing-only change to `cerebras:gemma-4-31b`, `2026-09-03_14-35-29` completed in 2 cycles through contract, independent challenge, close review, and extraction.
- MAIN engine healthy and idle after the lap. Challenger remains `cerebras:gemma-4-31b`; Parietal remains `cerebras:gpt-oss-120b` (distinct models; verify lineage constraints before future changes).
- Full live cockpit still exists at the Railway engine root (transcript, Researcher input, Keys modal). `ontinuity.org` is the static public site. Observe freely; do not casually Save the Keys modal—runtime config is process-global, outranks the vault, last-save-wins.
- PROVENANCE DEFECT OPEN: session `model_a_string` still names the historical Claude occupant when ChatGPT answers the external mailbox. Use the September 3 conversation record + session ids as the honest join until identity is carried by the protocol.
- Operator ruling: do not resume punch-list builds merely to keep motion going; this fold documents the milestone. The July 19 portable-tenant roadmap remains durable but is not the present instruction.
- Engine healthy. Box hands LIVE. Courier allowlist now 19 ops (added mailbox_purge this shift).
- MAILBOX RESULT-CHANNEL FIXED end to end this shift (was the night's big blocker — see below).
  Queue healthy (was 419 stale results jammed; purged). Correlated fetch + ack confirmed working.
- Laptop seat (laptop_seat.py on the HP, C:\donkeycar\) ALIVE and processing tasks (done-marking).
- Credentials: LLaves keys live and in use; pre-public risk accepted by operator. Rotation = launch
  hygiene, not a current blocker.
- ChatGPT Work access rule: first admit command networking in Settings -> Data
  controls -> Work network access. Use the documented curl and one narrowly
  scoped credential-bearing remote request per tool call. A DNS/host/policy
  denial before HTTP is `WORK_EGRESS_DENIED`, not evidence about Railway or the
  credential. Browser reachability is observation only, not authenticated hands.
- Independent close review corrected worker-corpus drift: `WORKER_MANUAL.md`,
  both boot packets, and the rubric/paradigm role summaries now match the live
  19-op courier, provider-neutral identity placeholders, header auth,
  latest-fold orientation, and the settled signer-deploys two-party chain. The
  same review found the bootstrap gate's
  repository defaults stale at 12/15 versus live 19 with a caller override;
  that remains OPEN and an overridden pass is not mechanical orientation.

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
**CURRENT CONTROLLING ACTION (2026-09-05): resume B1 and B3 from their
preserved candidates now that B5-P is operational.** First send B1 branch
`codex/b1-scoped-identity` at `a31ffe1` to an independent reviewer against the
mailbox threat audit and B1 acceptance tests, including removal of the
caller-controlled bootstrap canonical-count boundary. In parallel only where review
ownership stays distinct, reconcile B3 branch
`codex/b3-fail-closed-completion` at `12dea5e` onto current `main`, then send the
exact resulting bytes to a non-author reviewer and run the live museum after
signoff. Do not represent either branch as live from local tests or branch
existence. B0's original `DRIFT` record stays immutable; remaining canonical
installation reconciliation belongs to B6.

**HISTORICAL 2026-06-30 NEXT ACTION (superseded first by July 19, then paused September 3):**
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
