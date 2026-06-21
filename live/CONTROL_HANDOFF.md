# CONTROL HANDOFF — current state + the single next action
# Updated 2026-06-21 by control seat (claude.ai-chat:opus-4.8) at fold.
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the queue head.

## STATE AT FOLD
- Engine healthy. Box hands LIVE. Courier allowlist now 19 ops (added mailbox_purge this shift).
- MAILBOX RESULT-CHANNEL FIXED end to end this shift (was the night's big blocker — see below).
  Queue healthy (was 419 stale results jammed; purged). Correlated fetch + ack confirmed working.
- Laptop seat (laptop_seat.py on the HP, C:\donkeycar\) ALIVE and processing tasks (done-marking).
- Credentials: LLaves keys live and in use; pre-public risk accepted by operator. Rotation = launch
  hygiene, not a current blocker.

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
S22 ULTRA NODE BUILD — resume at the wireless-ADB connect step (staging is DONE):
  - Staged on laptop C:\donkeycar\: termux.apk (113.8MB, F-Droid 0.118.3 — NOT Play Store),
    build_cpu.sh (2460b, pinned llama.cpp b5027, OpenBLAS, pre-copies Adreno OpenCL libs, pulls
    Llama 3.2 3B Q4_0, benchmarks w/ perf-core affinity + ctx 2048).
  - Phone: wireless debugging ON, laptop ALREADY PAIRED (kille@LAPTOP-UEJLM2PL). Connect addr was
    192.168.1.141:39917 but the wireless-debugging PORT ROTATES — that caused the connect pain.
  - BULLETPROOF PATH: ten-second cable flip -> `adb tcpip 5555` over USB (fixed port, never rotates)
    -> unplug -> `adb connect 192.168.1.141:5555`. Then `adb install termux.apk`, push+run build_cpu.sh.
  - adb at C:\Users\kille\AppData\Local\Android\Sdk\platform-tools\adb.exe. Operator was plugging in
    the USB cable at fold.
BUILD TREE (the plan): CPU llama.cpp (branch 1, may be FASTEST on 8 Gen 1 — forum: GPU offload can be
40% SLOWER due to immature OpenCL driver) -> Vulkan + OpenCL-Adreno benchmark (branch 2) -> GENIE on
Hexagon NPU (branch 3, the endgame: ~10 tok/s sipping watts). FORUM GOTCHAS baked into build_cpu.sh:
pin pre-b5028 (newer segfaults on Adreno); disable Phantom Process Killer
(`adb shell device_config put activity_manager max_phantom_processes 2147483647`) or Android silently
kills the inference server; keep RAM >400MB. Note 9 (SD845, no usable LLM-NPU) = second worker/test bench.

## STANDING LESSON (still load-bearing, from prior shift)
Every in-cycle role MUST carry explicit *_URL/*_MODEL/*_API_KEY. A role configured "by omission"
silently inherits the shared PROVIDER_* fallback; null PROVIDER_MODEL -> 404. Web-verify provider
models are still live before wiring them.
