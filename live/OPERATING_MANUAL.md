# ONTINUITY OPERATING MANUAL — how the system works and how to drive it
*Load-bearing durable artifact. SCOPE: the OPERATOR/CONTROL seat ONLY (drives sessions/driver/writes) — NOT the in-cycle role seats (Challenger/Friction/Parietal/Projenius). Any AI sitting in the operator/control seat reads THIS to be immediately competent, regardless of conversation length or model lineage. Operating knowledge must PERSIST, not live in a degrading context window. Grounded against app.py (verified, not recalled). When code changes, update this.*

## THE TWO SESSION START MODES (the thing most easily forgotten)
A farm/engine session can be started two ways, and they behave fundamentally differently:

### 1. external-mailbox mode — POST /agent/start
- Sets active_session["started_by"] = "external-mailbox" (app.py ~3070-3093).
- The Researcher posts EACH turn to the external mailbox and WAITS FOR AN AGENT to answer ("Researcher turn N posted to external mailbox — waiting for agent." app.py ~1678).
- **REQUIRES A DRIVER answering the mailbox, or the session hangs forever at "waiting for agent," never reaches a cycle close, and NEVER WRITES to the workspace.**
- This is the mode the burn-in uses — because the RESIDENT DRIVER answers the mailbox.
- DO NOT use /agent/start for a quick verification UNLESS a driver is running. (This exact mistake was made repeatedly on June 9: started mailbox sessions with no driver, they hung, nothing persisted, time + Cerebras credit burned.)

### 2. dashboard mode — handle_start_session (/start_session)
- Sets active_session["started_by"] = "dashboard" (app.py ~3530-3550).
- Runs the loop INTERNALLY; does not require an external mailbox driver.
- This is the mode to use for a self-contained run that closes on its own.

## THE RESIDENT DRIVER (the shepherd)
- systemd service `ontinuity-burnin` on the VPS (/opt/ontinuity/burnin_resident.py).
- It is the thing that ANSWERS the external mailbox for /agent/start sessions and drives them cycle-by-cycle to a normal close.
- It self-stops when the burn-in stopping rule is met (>=200 randomized AND >=20 sessions). When stopped, no mailbox sessions can complete.
- ALWAYS-ON: the driver now runs continuously (systemd unit: TARGET_RANDOMIZED=0 = never self-stop, Restart=always, enabled on boot). It drives any requested session to close, idles when nothing's queued, revives if it dies, comes back on reboot. You should NOT need to hand-start it. If it's somehow stopped: `systemctl start ontinuity-burnin`. Set TARGET_RANDOMIZED to a nonzero value only for a finite burn-in (self-stops at target).
- Start (only if stopped): `systemctl start ontinuity-burnin && sleep 4 && systemctl is-active ontinuity-burnin`
- Stop: `systemctl stop ontinuity-burnin`
- Status/logs: `systemctl is-active ontinuity-burnin` ; `journalctl -u ontinuity-burnin --no-pager -n 20`
- RULE: exactly ONE driver owns the farm. A second poller (e.g. a chat-sandbox driver) collides — kill zombies. Separate instances need separate mailboxes (the burn-in/main isolation pattern).

## THE WRITE PATH (when/how a session persists)
- A session writes its payload to the workspace DB ONLY ON NORMAL CLOSE, via build_session_payload -> workspace write (app.py ~374, 478).
- DIED or STOPPED sessions DO NOT reach the write — their payload (transcript, executions, even the session row) is LOST. On write failure the engine saves /tmp/failed_session_<id>.json (recoverable fail-soft). [Known gap: abnormal-exit persistence — flush-on-abnormal-exit is the fix, same root as the un-instrumented death-exit finding.]
- Adversarial-review floor: the loop will NOT allow SESSION_END after only one cycle — at least one full cycle of challenge is required before close. "Run one cycle then close" objectives CANNOT close in one cycle; they need >=2.

## MODALS in autonomous vs attended
- A modal pauses for human input. In ATTENDED (dashboard) sessions a human answers it.
- In AUTONOMOUS (mailbox/farm) sessions there is no human: MODAL_TIMEOUT_AUTONOMOUS_S = 90s self-resolves it (app.py ~1707-1761), so a modal becomes a 90-second self-clearing CHECKPOINT, not a question. This is why the operator rarely SEES a modal during farm runs — they fire and clear without you. (Open clarity item: rename the autonomous "human_input modal" to "escalation checkpoint" — it's a misnomer in that context.)

## KEY ENDPOINTS / ACCESS (read-only diag via Railway relay — survives the firewall)
- Corpus query (read-only SELECT): https://web-production-7eaf8.up.railway.app/diag/api/query?diag_key=KEY&sql=...
- Engine state: /diag/engine?diag_key=KEY  -> running, waiting_for_input, cycle, started_by
- Engine event log: /diag/console?diag_key=KEY  (this is where a write FAILURE shows, e.g. ConnectTimeout)
- Health: /diag/api/health?diag_key=KEY
- Farm engine base: https://ontinuity-farm-production.up.railway.app  (same /diag/* routes)
- Mailbox (answer an orphaned turn): POST /mailbox/respond {mailbox_key, turn_id, response}; check /mailbox/turn?mailbox_key=...
- Scoped-op courier (sandbox-seat box hands): POST /diag/op/<name> {bounded args} with diag_key -> forwards to box /op/<name>, returns verbatim. Allowlist (live, 13 ops): read_journal, restart_workspace, register_egress, mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, mailbox_reclaim, write_file, commit_self, read_file, commit_file, you_there. (The arm that lets a sandbox seat reach the box through the engine.)

## FIREWALL (VPS workspace, port 5001) — June 9
- Workspace 5001 is firewalled to whitelisted sources ONLY (default-drop). Whitelisted: operator laptop 47.37.119.177, operator parents' net 66.132.172.101, Railway relay 162.220.232.0/24, Railway FARM egress 52.52.202.228.
- CRITICAL: the FARM engine's DIRECT workspace write egresses from a DIFFERENT IP (52.52.202.228, AWS 52.x) than the diag relay (162.220.232.x). If farm writes fail with ConnectTimeout, the egress IP rotated — catch it with `ufw logging on` then `journalctl -f | grep 'UFW BLOCK'` watching for DPT=5001, and whitelist the new SRC. (Single-IP whitelist may need widening to a subnet if it rotates often.)
- To diagnose a "hang": it's usually NOT a code hang — check `ss -tnp | grep :5001` for squatter connections and the journal for the real request log. The server is often healthy and serving while an external curl times out.

## VERIFICATION RECIPE (how to prove a write/persist works)
1. Ensure the resident driver is running (mailbox sessions need it) OR use dashboard mode.
2. Baseline the target table count via /diag/api/query.
3. Trigger a session; wait for a NORMAL close (>=2 cycles; ~2-4 min; watch /diag/engine for running:False with a session that didn't die).
4. Re-query the table; confirm rows. If 0, check /diag/console for a write FAILURE (ConnectTimeout = firewall; other = look closer).
5. Do not burn credit re-spawning blind — read the engine log to see WHY before retrying.


## CONTROL-SEAT CLOSE RITUAL (run at session close — WORK THE CHECKLIST, do not freestyle)
A literal checklist so nothing lapses silently (the silent-lapse disease). Run every item; if an item does not apply, say so explicitly rather than skipping it. The first three are the record re-distillation; the rest catch the things a seat forgets after a long, focused build.

1. PUNCH_LIST.md — reconcile DONE/IN-PROGRESS/OPEN against what actually shipped this session (cite closing commit/receipt for each newly-done item). Move finished items OUT of IN-PROGRESS, not just into DONE.
2. Conversation record (live/conversations/) — capture this session's dialogue per CONVENTION.md (rulings verbatim, redact keys/IPs, cross-ref shas/receipts). The control seat does this — a worker backfilling from commits cannot see the conversation window.
3. agent_queue.md fold — write the session's narrative fold (what was built, what was learned, what reversed), keyed on the same shas/receipts.
4. MANUAL CURRENCY — did any operation change this session (new endpoint, new scoped op, new courier allowlist entry, new standing fix, a corrected operating belief)? If yes, THIS MANUAL must already reflect it (currency discipline says same-commit; the close ritual is the backstop that catches a miss). Edit it now if it lagged.
5. PROVENANCE — are this session's deploys, rulings, and any new box source committed and in version control? If box source changed, run commit_self so the repo matches the box (do not leave the box ahead of the repo).
6. SECRETS SWEEP — grep every file committed this session for tokens/keys/IPs (csk-, github_pat_, ghp_, the diag key, operator IPs). A token passed as a transient arg must never have landed in a committed file.
7. STATE LEFT CLEAN — engine idle (/diag/engine running:False), no half-finished deploy (last deployment SUCCESS not FAILED/DEPLOYING), no orphaned mailbox claim holding a block. If a deploy failed, either fix it or fold it as OPEN with the build-log reason — never leave a silent FAILED.
8. NEXT-SEAT HANDOFF — the top of the queue / a handoff note states the single next action, so the next seat (or a fresh you) runs the open ritual onto a clear target instead of re-deriving where things stood.

All records key on the SAME shas/receipts (the join), so a stranger walks conversation -> decision -> commit -> receipt in either direction. Running them as one ritual is what stops any one lapsing (conversation logging lapsed after one entry on June 7 precisely because it was not part of a ritual; the deploy-autonomy belief went stale on June 10 because it was not written down).


## CONTROL-SEAT OPEN RITUAL (run before reasoning about a task)
The bookend to the close ritual. Before proposing or acting on a task — ESPECIALLY after focusing on something else for a while — ORIENT FROM THE CORPUS, do not reason from memory:
1. Search the queue folds (live/agent_queue.md) for the topic — past decisions, verdicts, and reversals on it.
2. Read the relevant conversation records (live/conversations/) for the reasoning behind those decisions.
3. Follow the item's cited refs (sha / receipt) to the actual record.
Recall is NOT a substitute for retrieval. A long session degrades context; the corpus does not. Failing to load before acting is the silent-failure class — it produces confident proposals anchored to stale state (e.g. proposing to automate a mechanism the record shows was already retired). The fold/retrieval machinery is reliable; the only gap is failing to reach for it. Orient first, then reason.


## MANUAL-CURRENCY DISCIPLINE (mandatory)
When operation changes, THIS MANUAL changes in the SAME commit as the change. Triggers: a new endpoint, a new session mode, a fix that alters the write path, a firewall/egress change, a new scoped operation, a change to the driver, or any change to how the system is operated. Rationale: a manual that lags the system decoheres the same way an operator's memory does, just slower — and then the next seat reads stale instructions and repeats a retired failure. The manual is only load-bearing if it is current. Do not fold an operation change to the queue and leave the manual untouched; the queue is the archive, the manual is the live operating instruction. If you change how the system works and do not update the manual in the same breath, you have introduced the silent-decoherence defect into the one document meant to prevent it.


## SCOPED OPERATIONS (privileged box actions the operator seat can invoke)
The operator seat performs privileged box actions through NAMED, BOUNDED operation endpoints — never a shell, never an arbitrary command string. Each operation does exactly one defined thing. Adding a capability = adding a named operation, never widening a general one.
- Reference implementation: POST /register_egress (file_server.py) — diag-key gated (constant-time), validates inputs, performs one action (ufw allow caller's own remote_addr on port 5001), logs to the operations ledger at both ends, fails safe. Every new operation mirrors this shape.
- AUDIT SPINE — operations_ledger table (op_id, operation, tier, caller, source_ip, args, result, status started|ok|fail, started_at, finished_at). Helpers _ops_begin (log intent, returns op_id) + _ops_finish (log result) in file_server.py. DUAL-END: every op logs intent on invocation, result on completion. A crashed op leaves status=started + null finished_at = visible incomplete record. NO operation may run without logging to the ledger.
- TIERING (reuse sign-off tiers): SAFE = read-only or trivially reversible, diag-key only, auto-runs. REVIEW = reversible state change (restart, reconfigure), diag-key + operator sign-off token (interim: tight-guard + rollback). RISK = irreversible/wide-blast, strictest gate + must-refuse museum + explicit sign-off. Classifier proposes tier; operator may escalate, never silently de-escalate. Never self-locking (an op must never brick the ability to run the fix for the op).
- Spec: live/specs/scoped_operations_spec.md. Build sequence: ledger [DONE] -> safe op#1 (journal read + workspace restart) -> gunicorn/key-auth firewall fix as op#2 (retires the IP-whitelist; note the firewall section below becomes obsolete once op#2 ships).


### Live scoped operations (the named allowlist so far)
- POST /op/read_journal {lines:1..200} — SAFE, read-only. Recent ontinuity-workspace journal lines. Use to check VPS history (e.g. blocked-connection IPs) without operator hands.
- POST /op/restart_workspace — SAFE, reversible. Restarts the workspace service (detached, returns first, back in a few seconds; confirm via /status:401).
- POST /register_egress {cidr? optional} — SAFE. ufw-allow caller's own egress IP (or allowlisted CIDR) on 5001. (Obsolete since the gunicorn/key-auth fix; retained.)
- POST /op/mailbox_send|fetch|ack|peek|reclaim — seat-to-seat mailbox (seat_mailbox.py). send/ack are state changes, fetch is an ATOMIC claim (BEGIN IMMEDIATE), peek is read-only, reclaim returns expired claims to queue. Carries coordination + corpus pointers (ref), never the canonical result. This is how parallel seats coordinate without the operator routing messages.
- POST /op/write_file {path, content, description?} — REVIEW. Bounded write to a file INSIDE the box project dir only (path traversal rejected). The general write hand a sandbox seat reaches through the courier (the box's plain /write is not a /op/ route, so the courier can't reach it; this is).
- POST /op/commit_self {github_token, files?, repo_dir?} — REVIEW. The box reads its OWN allowlisted source files and pushes them to the repo via the GitHub contents API. Token passed as a bounded CALLER arg, never stored on the box. This is how the repo stays in sync with the box (closed the file_server.py provenance hole June 10) — run it in the close ritual whenever box source changed. Self-source allowlist: file_server.py, seat_mailbox.py, box_ops.py, workspace_db_endpoint.py, db.py, governor.html, governor_punchlist.html.
All diag-key gated (X-Diag-Key), all log to operations_ledger.
INVOCATION — two paths, same ops:
- From the operator/Railway network (can reach the box directly): POST the box directly, e.g. POST {WORKSPACE_URL}/op/read_journal with X-Diag-Key.
- From a chat-SANDBOX seat (control or worker — cannot reach the box directly; egress can't open the box connection): go through the RELAY-COURIER on the engine — POST {ENGINE}/diag/op/<name> with the DIAG_KEY. The engine forwards the bounded JSON body to the box's /op/<name> as X-Diag-Key and returns the box response verbatim. The box still enforces the full contract (bounded args, ledger, tier); the engine is only the courier. This is THE way a sandbox seat gets box hands — no IP whitelisting. Courier op allowlist mirrors this list; adding a box op means adding its name to OP_ALLOWED in app.py too.

OPERATING INVARIANTS (the mechanics a seat must state correctly — these are what CHECK 6 MECHANICS of the bootstrap gate ratifies; a seat that misstates these is drifting on mechanics, not state):
- NO SELF-POLL: a chat seat does NOT self-poll the mailbox. It acts only when its conversation is given a turn. So coordination is mailbox-native (seats reach the mailbox directly, no human relays content), BUT a dormant chat-window worker still needs its conversation NUDGED to take a turn — nothing server-side can wake a dormant chat window. (A farm-style ENGINE-instance worker is different: it is a live process that parks on its mailbox and IS woken by a mailbox write / shepherd heartbeat. Self-driving fan-out uses engine-instance workers, not chat windows.) This invariant is here because the control seat drifted on it June 10 — asserted the loop was fully autonomous, then contradicted it one turn later.
- COURIER-ONLY: a sandbox seat cannot reach the box directly; it reaches box ops only through the relay-courier on the engine.
- DEPLOY AUTHORITY: operator owns deploys = authority + rollback, NOT a per-redeploy human click; the seat deploys routine work, operator is the fuse and oversight.
- NEW BOX OP: needs BOTH a box install (write_file + restart, hands-free) AND an OP_ALLOWED entry in app.py (commit + deploy). The box-install half is hands-free; only the very first bootstrap (before write_file existed on the box) ever needed SSH.
- ARTIFACT FLOW: a worker writes an artifact to the box (write_file); control reads it back (read_file) and commits it to the repo (commit_file); the worker holds no token — propose, don't deploy.


## WORKSPACE SERVING + ACCESS (current — IP-whitelist RETIRED, June 10)
The workspace no longer uses IP-whitelisting. It runs under GUNICORN on 0.0.0.0:5001 (systemd ExecStart: gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 file_server:app), port 5001 OPEN to all (ufw allow 5001/tcp), with security by KEY-AUTH at the app layer (diag-key for /diag,/op/*,/register_egress; X-API-Key for /governor data + workspace write routes; page routes are read-only HTML). This is the fix for the egress-IP-rotation breakage: relay + writes now work from ANY IP and survive every redeploy. Do NOT re-introduce per-IP ufw rules — that was the retired model. Revert (if ever needed): /etc/systemd/system/ontinuity-workspace.service.bak_pregunicorn + /tmp/ufw_5001_pregunicorn.txt. NOTE: any earlier "firewall + whitelisted egress IPs" guidance above is OBSOLETE. With 5001 public, the security invariant is that every mutating route is key-gated — preserve that on any new route.


## COLD-BOOT ONBOARDING (a fresh control seat with no prior context — run this FIRST)
You are a control/operator seat booting cold. You are NOT empty of capability — your capabilities are documented; do not conclude one is absent until you have CHECKED for it (concluding "I can't" without checking is the wall-declaring failure the recoherence fold warns about). Run these steps in order:

1. ORIENT FROM THE CORPUS (the open ritual, in order):
   a. The CURRENT-STATE touch point: the latest "CURRENT-STATE TOUCH POINT" fold in live/agent_queue.md — read it in full first; it is the now-state.
   b. This manual (you are reading it).
   c. live/PUNCH_LIST.md — resolved DONE/IN-PROGRESS/OPEN task state.
   d. The recent queue folds, newest backward, for the last few days of decisions.
   Read from the LIVE repo via authed api.github.com (below), NOT from /mnt/project/* — those project snapshots are STALE (old engine/workspace files without /diag, /op, /agent routes). Building against them reproduces the stale-state failure.

2. FIND YOUR CREDENTIALS (check; do not assume present or absent):
   - GitHub token: /home/claude/ghtok.txt   ·   Mailbox key: /home/claude/mbkey.txt   ·   DIAG_KEY: in the corpus / your context.
   - If a credential file is MISSING in your sandbox, say so plainly and ask the operator — do not conclude your role lacks the capability. The path may simply not be provisioned in your seat yet.

3. KNOW YOUR HANDS (capabilities a cold seat must not re-derive or wrongly declare absent):
   - READ the repo: authed `api.github.com` with `Accept: application/vnd.github.raw` (reliable). Do NOT trust raw.githubusercontent.com for frequently-updated files — it serves stale CDN cache.
   - COMMIT to the repo: YOU make commits — that is agent work (standing rule: "initiation and work: agent; the operator is the fuse"). Commit via the api.github.com contents API (PUT) using ghtok.txt. Carry trailers: `Assisted-by: claude.ai-chat:<model>` and, on watched paths, `Operator-Signoff: <operator-session>`. There is no separate "worker seat" you hand commits to — the control↔worker mailbox is a FUTURE build, not a current actor.
   - READ box/engine state: the Railway diag relay (web-production-7eaf8.up.railway.app/diag/...?diag_key=KEY) — works from a sandbox. Your sandbox CANNOT reach the Hetzner box (5001) directly (egress); that is a sandbox limit, not a system limit. Reach box ops through the engine relay/courier, not direct.
   - DEPLOY AUTONOMY (corrected June 10): the operator owns tokens, credentials, judgment modals, and holds DEPLOY AUTHORITY + accountability + the ability to stop/rollback. This does NOT mean every redeploy waits for a human click — that would gut autonomous work. You HAVE Railway deploy capability via the project token and SHOULD use it for routine work: read the build logs, fix, redeploy. The failure mode to avoid: manufacturing a fake "waiting for operator approval" gate out of a deploy that actually FAILED — read the build logs before concluding anything about why a deploy didn't come up. Watched paths (app.py): run the /diag/engine check first — never commit during a live session — then commit and deploy. The operator is the fuse and oversight, not the button-presser.

4. THEN act, via the open ritual on the specific task. If you are about to say something "can't be done," exhaust the corpus and check your hands first.

NOTE — this is the COLD-BOOT path (a genuinely fresh seat). A seat already mid-stream that is DRIFTING does not run this; it runs the open ritual to RE-GROUND on its current task (it is not empty, just stale). Do not tell a context-rich recohering seat "you are fresh with zero context." Fresh-state vs operating-state are distinct.


## ROLE PROVIDERS — set per role via Railway env vars (any role, not just the Challenger)
Each in-cycle role's provider/model/key is set on the engine's Railway service via env vars, NOT in app.py (CONFIG defaults are empty; the engine reads env). For role <ROLE> in {MODEL_A, MODEL_B, MODEL_C, PARIETAL, PROJENIUS}:
- MODEL_<ROLE>_URL   — provider chat-completions endpoint
- MODEL_<ROLE>_MODEL — provider model string
- MODEL_<ROLE>_API_KEY — provider key
Beneath those, PROVIDER_URL / PROVIDER_API_KEY are the SHARED fallback any role with no role-specific var inherits. (This is why MAIN's Challenger, having no MODEL_B_* vars, inherited the shared Novita PROVIDER and died on a Novita 404 — fixed June 10 by setting MODEL_B_* to Cerebras GLM-4.7.) MODEL_A_URL=external means that role is staffed by the mailbox seat (a Claude answering /mailbox), not a provider model.
Set them via the Railway GraphQL API (backboard.railway.app/graphql/v2, Project-Access-Token = the project token) with the variableUpsert mutation {projectId, environmentId, serviceId, name, value}. Read current values with the variables(projectId,environmentId,serviceId) query first (read-then-write). A variable change triggers a ~30s service redeploy to take effect; it is a config change, not a code commit or a serviceInstanceDeploy. STANDING DEPLOY-FAILURE FIX (June 10): if a build fails with mise `no precompiled python found for core:python@3.13.14` (or any 3.13.x ahead of what python-build-standalone has published — latest precompiled is 3.13.12), pin the EXACT version: Railway vars RAILPACK_PYTHON_VERSION=3.13.12 + NO_CACHE=1 (the bare "3.13" does NOT work — it still resolves to the unreleased latest). These are already set on MAIN. Always READ THE BUILD LOGS (Railway buildLogs GraphQL by deploymentId) before diagnosing a failed deploy — do not assume an approval gate. DESIGN RULE: keep adversarial roles on different training lineages — e.g. Challenger and Parietal should not share a provider/lineage, so their error geometries differ (the whole point of the adversarial layer).

## TWO AXES THAT ARE EASILY CONFUSED — START MODE vs SEAT STAFFING (read this; fresh seats keep conflating them)
These are DIFFERENT questions. A fresh seat collapsed them and wrongly concluded "I can never be the Researcher." Keep them separate:

**Axis 1 — START MODE (how the loop is triggered):** external-mailbox (POST /agent/start, needs the resident driver) vs dashboard (/start_session, runs internally). Covered above.

**Axis 2 — WHO STAFFS THE RESEARCHER SEAT (who answers as Model A):**
- **FARM / all-API staffing:** the Researcher seat is a PROVIDER MODEL on the engine (e.g. Cerebras GLM); judges are gpt-oss. No Claude in the loop. The control seat drives and watches the gates fire on those models. This is the unattended-accumulation/burn-in configuration.
- **MAILBOX-SEAT staffing:** the engine posts each Researcher turn to the external mailbox and a CLAUDE INSTANCE answers it (the original "mailbox seat," corpus June 6). This genuinely puts a Claude IN the Researcher seat — the real Challenger/Friction/Parietal/close gates fire on Claude's own answers. This is how a Claude experiences the harness from the inside (NOT by play-acting a role in chat, which is theater — no gate fires on that).

THE POINT: "the operator seat is not the in-cycle role seats" (true, by default) does NOT mean a Claude can never be the Researcher. In mailbox-seat mode, a Claude IS the Researcher. The operator-seat-vs-role-seat line is about the DEFAULT control conversation, not a prohibition. If the operator wants Claude to sit in the Researcher seat and be gated, that is mailbox-seat mode — a real, supported path, not theater.

## CREDENTIALS FOR A FRESH SEAT — how keys actually arrive (stop concluding "no path")
A fresh sandbox may come up EMPTY (no ghtok.txt, no key files) — this is normal; sandboxes are per-conversation and do not inherit the prior seat's filesystem. Empty does NOT mean the capability is absent. Keys arrive one of three ways:
1. PRE-SEEDED: key files already in /home/claude/ (ghtok.txt, mbkey.txt, etc.) — the prior long-running seat had these; use directly.
2. OPERATOR-PROVIDED: the operator pastes the values; you write them to /home/claude/ghtok.txt etc. and proceed. (This is the current fresh-seat bootstrap.)
3. VAULT (future password-unlock, fold 4cf9bddd): operator enters a password -> decrypts the master key -> pulls the vault. Not built yet.
CHECK for the files; if absent, ASK the operator for the values — do not conclude your role lacks the capability. The GitHub token is the write path; DIAG_KEY is the relay/box-op auth.

## THE SEAT-BOOTSTRAP VAULT IS NOT IN app.py (a fresh seat looked in the wrong place)
The credential-bootstrap vault = the Railway PROJECT VARIABLES, read via the Railway GraphQL API (backboard.railway.app/graphql/v2, header `Project-Access-Token`) using the Railway PROJECT TOKEN (the master key). The keyring root is that one project token; it recovers GitHub token + DIAG_KEY + mailbox keys (main's MAILBOX_KEY is in main's vault — pull both services). DISTINCT from app.py's own runtime model-key reading (the engine reading <ROLE>_API_KEY from its own env) — that is a different mechanism; do not mistake it for the seat vault.

## COMMITTING — mechanism + multi-file atomicity
Commits are AGENT work (standing rule: initiation and work is the agent's; the operator is the fuse/sign-off). Commit via the GitHub API with ghtok.txt.
- Single file: contents API PUT (needs the file's current blob sha).
- MULTIPLE files as ONE atomic commit: use the git TREES API (create blobs -> build a tree -> create one commit -> update the ref). Use this when several files must land together (e.g. a code change + its manual update in the same commit, per currency discipline). A sequence of contents-PUTs risks a half-committed state if one fails.
- Trailers: `Assisted-by: claude.ai-chat:<model>`; on watched paths also `Operator-Signoff: <operator-session>`. Watched paths (app.py): run the /diag/engine check first, never commit during a live session. You DO deploy routine work yourself (read build logs, fix, redeploy via the project token); the operator owns deploy AUTHORITY + rollback, not a per-redeploy click (see DEPLOY AUTONOMY in the cold-boot section).

## STALE PROJECT SNAPSHOTS — /mnt/project/* is frozen, often behind live
The /mnt/project/ files (app.py, file_server.py, etc.) are a SNAPSHOT, frequently OLDER than the deployed code (e.g. an old socketio engine with no /diag, /op, /agent routes). Two fresh seats nearly built against them. ALWAYS build against the LIVE repo source via authed api.github.com, not the project snapshot. (Also: raw.githubusercontent.com serves stale CDN cache for hot files — use the authed api.github.com raw accept header.)

## STANDING RULES CAN BE SUPERSEDED BY AN IN-SESSION OPERATOR GRANT
Some standing rules are operator-gated defaults, not permanent prohibitions (e.g. "never call /agent/start or any drive path" was a default; the operator can grant a session-scoped go to drive a session). A seat should HOLD such a rule until the operator explicitly lifts it — but must RECOGNIZE an explicit in-session grant ("you have my go to drive a session") as the authorization, and then act, rather than re-refusing on the now-lifted rule. Holding correctly is good; failing to release on an explicit grant is the wall-declaring failure in a new costume.
