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

## PUTTING AN EXTERNAL CHAT MODEL IN THE RESEARCHER SEAT (mailbox-seat mode — the real harness-from-inside)
This is how a Control conversation—Claude, ChatGPT, or another mailbox-capable occupant—experiences the harness as the Researcher (Model A), with the REAL Challenger/Friction/Parietal/close gates firing on its own answers. This is NOT chat role-play (that's theater, no gate fires). Proved cross-platform with `chatgpt-work:gpt-5.6-sol` on 2026-09-03: failed-closed session `2026-09-03_14-13-03`, complete session `2026-09-03_14-35-29`.
- THE SWITCH: Model A's EFFECTIVE config url must be "external". app.py (~1716): if model_a's url startswith "external", the engine posts each Researcher turn to the external mailbox instead of calling an API ("the engine cannot tell what occupies the seat"). The vault has MODEL_A_URL=external as the DEFAULT — but do NOT trust it (see THE CONFIG TRAP below).
- DRIVE BY HAND (control IS the driver on MAIN; the resident driver is FARM-only, so no collision on MAIN): POST /agent/start {mailbox_key, objective, start_fresh:true} → poll GET /mailbox/turn?mailbox_key= → answer by KIND: `pre_session_questions` (answer the Parietal's contract questions in plain prose, no status tag), `researcher_turn` (do the REAL Researcher work — ground every claim, issue DB_QUERY/CODE_TEST/SEARCH tags, never fabricate a result), `human_input_needed` (modal) → POST /mailbox/respond {mailbox_key, turn_id, response}. Loop to a gated SESSION_END. turn_id may NOT start at 1 (stale external-mailbox state) — fetch first to get the live id. Adversarial-review floor: cannot close in 1 cycle.
- PROOF you're actually in the seat: a `researcher_turn` arriving at the mailbox. (shepherd.py halts on this as config-drift for an all-API farm; in mailbox-seat mode it is the intended signal.) If instead the console shows a Cerebras/API call, the config is wrong — STOP immediately.
- mailbox_key: in the vault (MAILBOX_KEY), distinct from DIAG_KEY.
- PROVENANCE CAVEAT (2026-09-03): the current session row still takes `model_a_string` from historical configuration and can report `claude.ai-chat:claude-opus-4.8` when a different platform actually answered the external mailbox. Treat the conversation fold + session id as the honest occupant join until the OPEN punch item binds external identity into the protocol. Do not cite `model_a_string` alone as proof of the external occupant.

## THE LIVE COCKPIT (transcript + Researcher input + Keys modal)
The full Socket.IO cockpit still exists in `app.py` + `templates/index.html` and is served at the MAIN Railway engine root (`web-production-7eaf8.up.railway.app`). It includes the live transcript/console, session controls, the human/Researcher participation path, and the Keys modal (`save_api_keys`). `ontinuity.org` currently serves the static public site, so it no longer exposes this cockpit even though the runtime code remains live.

Use the cockpit to watch seat failures and gated turns. Treat the Keys modal as a live global mutation, not a local browser preference: it writes process-global `runtime_configs`, outranks the Railway vault, and the last open browser to save wins. For observation, do not press Save. If manual staffing is intentional, read the live role configuration first, make one controlled save, and verify behavior immediately.

## THE CONFIG TRAP (why a Researcher-seat start silently staffs Cerebras — cost a failed run 2026-06-14)
get_effective_config precedence (app.py ~195): base CONFIG (empty for model_a) → runtime_configs[role] → _vault_fallback. runtime_configs is set by the dashboard KEYS modal (save_api_keys socket event); it FULLY REPLACES on every save (last-write-wins, process-global) and OUTRANKS the vault. So a STALE runtime override — an old keys-modal save from a different browser/device — beats the vault's MODEL_A_URL=external and staffs the old Cerebras endpoint (404s, spins cycles). RULE: verify/set the EFFECTIVE config (the LAST keys-modal save) before starting; do not rely on the vault default. Multiple open keys modals (iPad + laptop) are a live race — the last save wins. There is NO diag route that reports live runtime_configs — confirm by behavioral probe (does a researcher_turn post, or a Cerebras call appear) and stop instantly if wrong. "Model configuration saved for this session" in the console is the first line of a keys-modal save / session-begin — not a mystery process.

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
- A main-loop session exits through the end sequence and writes its payload via `build_session_payload` -> workspace write. Normal close writes `complete`; observed provider death and keyed operator stop use incomplete/stopped dispositions and still reach the write. A PRE_SESSION attempt with a begun model call writes `incomplete_pre_session`; an attempt with no call evidence creates no research row.
- From capture boundary `2026-09-05_09-37-00` / receipt `351`, the atomic payload also carries exact transcript companions, structured challenges, adjudication-driven retractions, model-call envelopes, and one non-secret reproducibility manifest under `ontinuity-research-evidence/1.0`. The normalized transcript/artifact fields remain compatibility views; raw evidence and its digests are the forensic record. See `RESEARCH_PRESERVATION_CONTRACT.md`.
- On final workspace-write failure the engine saves `/tmp/failed_session_<id>.json` (recoverable fail-soft). B3 remains open because certification is still default-permissive on unclassified exit paths and the deployed schema lacks a durable `end_reason`; do not generalize the observed model-dead/stop paths into proof that every abnormal exit is classified correctly.
- Adversarial-review floor: the loop will NOT allow SESSION_END after only one cycle — at least one full cycle of challenge is required before close. "Run one cycle then close" objectives CANNOT close in one cycle; they need >=2.

## MODALS in autonomous vs attended
- A modal pauses for human input. In ATTENDED (dashboard) sessions a human answers it.
- In AUTONOMOUS (mailbox/farm) sessions there is no human: MODAL_TIMEOUT_AUTONOMOUS_S = 90s self-resolves it (app.py ~1707-1761), so a modal becomes a 90-second self-clearing CHECKPOINT, not a question. This is why the operator rarely SEES a modal during farm runs — they fire and clear without you. (Open clarity item: rename the autonomous "human_input modal" to "escalation checkpoint" — it's a misnomer in that context.)

## KEY ENDPOINTS / ACCESS (read-only diag via Railway relay)
- ChatGPT Work admission check: code/shell networking is a separate capability from browser/web access. Before diagnosing Railway, confirm Settings -> Data controls -> Work network access -> Allow public internet access is ON. A pre-HTTP DNS/host/network-policy denial is `WORK_EGRESS_DENIED`, not a Railway outage or bad key. Do not switch to Python HTTP clients; rerun the corpus-prescribed curl after the setting is enabled. Browser reachability proves only that the public page is reachable, not that authenticated hands are live. Prefer `X-Diag-Key` over a `diag_key` URL parameter so credentials do not enter URLs. In Work mode, make one narrowly scoped credential-bearing remote request per tool call; do not batch probes, reads, and mutations into one shell action. Platform permission review is separate from operator authorization: classify a pre-execution rejection honestly and retry only the same authorized request after its platform condition is satisfied.
- Corpus query (read-only SELECT): GET `/diag/api/query` with `X-Diag-Key: $DIAG_KEY` and URL-encoded `sql=...`.
- Engine state: GET `/diag/engine` with `X-Diag-Key` -> running, waiting_for_input, cycle, started_by.
- Engine event log: GET `/diag/console` with `X-Diag-Key` (this is where a write failure appears).
- Health: GET `/diag/api/health` with `X-Diag-Key`.
- Farm engine base: https://ontinuity-farm-production.up.railway.app  (same /diag/* routes)
- Mailbox (answer an orphaned turn): POST /mailbox/respond {mailbox_key, turn_id, response}; check /mailbox/turn?mailbox_key=...
- Scoped-op courier (sandbox-seat box hands): POST /diag/op/<name> {bounded args} with diag_key -> forwards to box /op/<name>, returns verbatim. Allowlist (live, 19 ops): read_journal, restart_workspace, register_egress, mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, mailbox_reclaim, mailbox_purge, write_file, commit_self, read_file, commit_file, you_there, read_repo, bootstrap_gate, deploy, seed_tenant, backup_db. (mailbox_purge: scoped queue cleanup, removes BOTH queued and done by kind — verify scope with a SELECT GROUP BY status before firing. backup_db: snapshot the corpus DB. Both added since the 17-op count; synced 2026-06-29.) (The arm that lets a sandbox seat reach the box through the engine.) seed_tenant: bounded idempotent tenant provisioning (creates a users row + projects row, no arbitrary SQL) — lets a seat onboard a client tenant hands-free; first use seeded SHS-Wasserman 2026-06-15. NOTE (install lesson, 2026-06-15): a new box op is NOT live until written to the BOX DISK via write_file + restart — committing box_ops.py to the repo alone leaves the box running stale on-disk code (a commit landed but the box 404'd until write_file installed it). Repo commit and box install are TWO steps; the manual line 122 rule.
- Bootstrap-gate current ceiling (found by independent close review 2026-09-05): the op is live, but repository defaults remain 12 in `live/bootstrap/gate.py` and 15 in `live/box/box_ops.py` while the courier is 19; the request can override `canonical_op_count`. Until one server-derived value is reviewed, deployed/installed, and proved for both Control and Worker, an overridden pass is not authoritative mechanical orientation. Use the full manual open checks and keep this item OPEN in `PUNCH_LIST.md`.

## WORKSPACE NETWORK BOUNDARY — CURRENT
- The June 9 source-IP firewall model is retired. Port 5001 is served by gunicorn and protected by application-layer keys; do not reintroduce per-egress-IP allowlisting. Historical addresses and the reason for retirement remain in the queue ledger, not as current operating instructions.
- A chat sandbox normally reaches box operations through the Railway `/diag/op/<name>` relay-courier. Direct box reachability is not required for Control hands and is not a valid prerequisite for declaring the engine healthy.
- Diagnose a pre-HTTP denial at the calling environment first. Diagnose an HTTP/application failure through the returned status and `/diag/console`; do not collapse these into one generic "Railway/box down" claim.

## VERIFICATION RECIPE (how to prove a write/persist works)
1. Ensure the resident driver is running (mailbox sessions need it) OR use dashboard mode.
2. Baseline the target table count via /diag/api/query.
3. Trigger a session; wait for a NORMAL close (>=2 cycles; ~2-4 min; watch /diag/engine for running:False with a session that didn't die).
4. Re-query the table; confirm rows. From the B5-P boundary, verify transcript/envelope/manifest hashes and the structured challenge/retraction rows when the session exercised them. If 0, check `/diag/console` for the actual write failure before classifying the cause.
5. Do not burn credit re-spawning blind — read the engine log to see WHY before retrying.


## CONTROL-SEAT CLOSE RITUAL (run at session close — WORK THE CHECKLIST, do not freestyle)
A literal checklist so nothing lapses silently (the silent-lapse disease). Run every item; if an item does not apply, say so explicitly rather than skipping it. The first three are the record re-distillation; the rest catch the things a seat forgets after a long, focused build.

1. PUNCH_LIST.md — reconcile DONE/IN-PROGRESS/OPEN against what actually shipped this session (cite closing commit/receipt for each newly-done item). Move finished items OUT of IN-PROGRESS, not just into DONE.
2. Conversation record (live/conversations/) — capture this session's dialogue per CONVENTION.md (rulings verbatim, redact keys/IPs, cross-ref shas/receipts). The control seat does this — a worker backfilling from commits cannot see the conversation window.
3. agent_queue.md fold — write the session's narrative fold (what was built, what was learned, what reversed), keyed on the same shas/receipts.
4. MANUAL CURRENCY — did any operation change this session (new endpoint, new scoped op, new courier allowlist entry, new standing fix, a corrected operating belief)? If yes, THIS MANUAL must already reflect it (currency discipline says same-commit; the close ritual is the backstop that catches a miss). Edit it now if it lagged.
4b. CONTRACT-DOC CURRENCY (gated — run every close, do not skip) — did the WORKER CONTRACT change this session (the worker loop, the ops a worker calls, the deploy chain, identity/auth, the orientation steps)? If yes, ALL of these must reflect it in the same close: (a) live/WORKER_MANUAL.md, (b) the WORKER BOOT PACKET (the text the operator pastes to start a worker — it is what ACTUALLY runs; the manual documenting a behavior is NOT enough if the packet still invokes the old one — this is the you_there divergence: manual said self-drain, packet ran single-fetch), (c) live/THE_PARADIGM.md and live/OPERATING_RUBRIC.md if the system's shape or role rules changed. THREE STATES OF DONE are distinct and all required: op exists -> documented in the manual -> in the packet the worker runs. A change is not live for the operator until it reaches the packet. If none changed, say so explicitly.
5. PROVENANCE — are this session's deploys, rulings, and any new box source committed and in version control? If box source changed, run commit_self so the repo matches the box (do not leave the box ahead of the repo).
6. SECRETS SWEEP — grep every file committed this session for tokens/keys/IPs (csk-, github_pat_, ghp_, the diag key, operator IPs). A token passed as a transient arg must never have landed in a committed file.
7. STATE LEFT CLEAN — engine idle (/diag/engine running:False), no half-finished deploy (last deployment SUCCESS not FAILED/DEPLOYING), no orphaned mailbox claim holding a block. If a deploy failed, either fix it or fold it as OPEN with the build-log reason — never leave a silent FAILED.
8. NEXT-SEAT HANDOFF — `CONTROL_HANDOFF.md` and `ONTINUITY_1_0_BOARD.md` state the single current action, corroborated by the latest fold at the tail of the append-only queue. Do not treat the queue's oldest head as current state. The next seat (or a fresh you) runs the open ritual onto that clear target instead of re-deriving where things stood.

All records key on the SAME shas/receipts (the join), so a stranger walks conversation -> decision -> commit -> receipt in either direction. Running them as one ritual is what stops any one lapsing (conversation logging lapsed after one entry on June 7 precisely because it was not part of a ritual; the deploy-autonomy belief went stale on June 10 because it was not written down).


## CONTROL-SEAT OPEN RITUAL (run before reasoning about a task)
The bookend to the close ritual. Before proposing or acting on a task — ESPECIALLY after focusing on something else for a while — ORIENT FROM THE CORPUS, do not reason from memory:
1. Search the queue folds (live/agent_queue.md) for the topic — past decisions, verdicts, and reversals on it.
2. Read the relevant conversation records (live/conversations/) for the reasoning behind those decisions.
3. Follow the item's cited refs (sha / receipt) to the actual record.
Recall is NOT a substitute for retrieval. A long session degrades context; the corpus does not. Failing to load before acting is the silent-failure class — it produces confident proposals anchored to stale state (e.g. proposing to automate a mechanism the record shows was already retired). The fold/retrieval machinery is reliable; the only gap is failing to reach for it. Orient first, then reason.


## MANUAL-CURRENCY DISCIPLINE (mandatory)
When operation changes, THIS MANUAL changes in the SAME commit as the change. Triggers: a new endpoint, a new session mode, a fix that alters the write path, a firewall/egress change, a new scoped operation, a change to the driver, or any change to how the system is operated. Rationale: a manual that lags the system decoheres the same way an operator's memory does, just slower — and then the next seat reads stale instructions and repeats a retired failure. The manual is only load-bearing if it is current. Do not fold an operation change to the queue and leave the manual untouched; the queue is the archive, the manual is the live operating instruction. If you change how the system works and do not update the manual in the same breath, you have introduced the silent-decoherence defect into the one document meant to prevent it.


## SCOPED OPERATIONS (privileged box actions an admitted seat can invoke)
An admitted Control or Worker seat performs privileged box actions through NAMED, BOUNDED operation endpoints — never a shell, never an arbitrary command string. Possessing a transport key is not blanket authority: operation, identity, work-block, review, and deployment gates still apply. Each operation does exactly one defined thing. Adding a capability = adding a named operation, never widening a general one.
- Reference shape: every operation is key/capability gated, validates a bounded argument schema, performs one named action, writes intent and outcome to the operations ledger, and fails closed. `/register_egress` was the first implementation but its firewall action is retired; copy the bounded-and-ledgered shape, not the obsolete network policy.
- AUDIT SPINE — operations_ledger table (op_id, operation, tier, caller, source_ip, args, result, status started|ok|fail, started_at, finished_at). Helpers _ops_begin (log intent, returns op_id) + _ops_finish (log result) in file_server.py. DUAL-END: every op logs intent on invocation, result on completion. A crashed op leaves status=started + null finished_at = visible incomplete record. NO operation may run without logging to the ledger.
- TIERING (reuse sign-off tiers): SAFE = read-only or trivially reversible, diag-key only, auto-runs. REVIEW = reversible state change (restart, reconfigure), diag-key + operator sign-off token (interim: tight-guard + rollback). RISK = irreversible/wide-blast, strictest gate + must-refuse museum + explicit sign-off. Classifier proposes tier; operator may escalate, never silently de-escalate. Never self-locking (an op must never brick the ability to run the fix for the op).
- Spec: live/specs/scoped_operations_spec.md. Build sequence: ledger [DONE] -> safe op#1 (journal read + workspace restart) -> gunicorn/key-auth firewall fix as op#2 (retires the IP-whitelist; note the firewall section below becomes obsolete once op#2 ships).


### Live scoped operations (the named allowlist so far)
- POST /op/read_journal {lines:1..200} — SAFE, read-only. Recent ontinuity-workspace journal lines. Use to check VPS history (e.g. blocked-connection IPs) without operator hands.
- POST /op/restart_workspace — SAFE, reversible. Restarts the workspace service (detached, returns first, back in a few seconds; confirm via /status:401).
- POST /register_egress {cidr? optional} — SAFE. ufw-allow caller's own egress IP (or allowlisted CIDR) on 5001. (Obsolete since the gunicorn/key-auth fix; retained.)
- POST /op/mailbox_send|fetch|ack|peek|reclaim|purge — seat-to-seat mailbox (seat_mailbox.py). send/ack are state changes, fetch is an ATOMIC claim (BEGIN IMMEDIATE), peek is read-only, reclaim returns expired claims to queue, and purge is explicitly scoped destructive cleanup that requires before/after counts. Carries coordination + corpus pointers (ref), never the canonical result. This is how parallel seats coordinate without the operator routing messages.
- POST /op/you_there — claim-or-long-poll for task/proposal work; chat windows still need a platform turn, while resident API/engine workers can remain parked on this lifecycle.
- POST /op/write_file {path, content, description?} — REVIEW. Bounded write to a file INSIDE the box project dir only (path traversal rejected). The general write hand a sandbox seat reaches through the courier (the box's plain /write is not a /op/ route, so the courier can't reach it; this is).
- POST /op/read_file {path} — SAFE. Bounded read of a file inside the box project directory.
- POST /op/commit_self {github_token, files?, repo_dir?} — REVIEW. The box reads its OWN allowlisted source files and pushes them to the repo via the GitHub contents API. Token passed as a bounded CALLER arg, never stored on the box. This is how the repo stays in sync with the box (closed the file_server.py provenance hole June 10) — run it in the close ritual whenever box source changed. Self-source allowlist: file_server.py, seat_mailbox.py, box_ops.py, workspace_db_endpoint.py, db.py, governor.html, governor_punchlist.html.
- POST /op/commit_file {github_token, path, repo_path?, message?} — REVIEW. Commits one staged text file through the GitHub contents API; the token is transient caller material and is not stored on the box. Worker role alone does not grant it.
- POST /op/read_repo {path, ref?, github_token?} — SAFE. Reads repository source; an authenticated API token gives the authoritative path, while the designed tokenless path is raw CDN with a cache-busting query.
- POST /op/bootstrap_gate {seat, role, lineage, seat_invariants, canonical_op_count?} — present but NOT currently authoritative: repository defaults remain 12/15 versus live 19 and the caller override is an open defect.
- POST /op/deploy {target, signoff_block_id, commit_sha?, dry_run?} — two-party gated. The referenced proposal must carry a signoff by a different seat; under identity-bound auth the caller must be that signer. Railway credentials remain server-side. The clean non-author signer deploys exact reviewed bytes; an author/corrector may not.
- POST /op/seed_tenant — bounded idempotent tenant/user/project provisioning.
- POST /op/backup_db {out?} — SAFE (read-only against the live DB). Box makes a CONSISTENT snapshot of ontinuity.db via Python sqlite3 .backup, then writes a plain-text `.sql` dump (iterdump) to the box project dir (default backups/ontinuity_dump.sql). Text, so the existing text-only commit_file can ship it; the raw binary `.db` CANNOT go through read_file/commit_file (UTF-8 text ops) and the box has no sqlite3 CLI — this op is why. Backup flow is two calls: backup_db (dump) then commit_file (push the `.sql` to a PRIVATE repo). Added 2026-06-15 (box_ops.py 62c834a0, OP_ALLOWED 17->18 app.py 308ea384); first run committed 3.85MB to ontinuity-intake-data backups/ (cbfb6220).
All diag-key gated (X-Diag-Key), all log to operations_ledger.
INVOCATION — two paths, same ops:
- From the operator/Railway network (can reach the box directly): POST the box directly, e.g. POST {WORKSPACE_URL}/op/read_journal with X-Diag-Key.
- From a chat-SANDBOX seat (control or worker — cannot reach the box directly; egress can't open the box connection): go through the RELAY-COURIER on the engine — POST {ENGINE}/diag/op/<name> with the DIAG_KEY. The engine forwards the bounded JSON body to the box's /op/<name> as X-Diag-Key and returns the box response verbatim. The box still enforces the full contract (bounded args, ledger, tier); the engine is only the courier. This is THE way a sandbox seat gets box hands — no IP whitelisting. Courier op allowlist mirrors this list; adding a box op means adding its name to OP_ALLOWED in app.py too.

OPERATING INVARIANTS (the mechanics a seat must state correctly — these are what CHECK 6 MECHANICS of the bootstrap gate ratifies; a seat that misstates these is drifting on mechanics, not state):
- NO SELF-POLL: a chat seat does NOT self-poll the mailbox. It acts only when its conversation is given a turn. So coordination is mailbox-native (seats reach the mailbox directly, no human relays content), BUT a dormant chat-window worker still needs its conversation NUDGED to take a turn — nothing server-side can wake a dormant chat window. (A farm-style ENGINE-instance worker is different: it is a live process that parks on its mailbox and IS woken by a mailbox write / shepherd heartbeat. Self-driving fan-out uses engine-instance workers, not chat windows.) This invariant is here because the control seat drifted on it June 10 — asserted the loop was fully autonomous, then contradicted it one turn later.
- COURIER-ONLY: a sandbox seat cannot reach the box directly; it reaches box ops only through the relay-courier on the engine.
- DEPLOY AUTHORITY: the operator owns policy, pre-dispatch agreement, stop, and rollback; that does not require a per-deploy human click. For an agreed block, the clean non-author reviewer is the signer and lands the exact reviewed version through the block-scoped commit/deploy capabilities actually admitted. An author never lands its own bytes, and generic possession of a token is not landing authority.
- NEW BOX OP: needs BOTH a box install (write_file + restart, hands-free) AND an OP_ALLOWED entry in app.py (commit + deploy). The box-install half is hands-free; only the very first bootstrap (before write_file existed on the box) ever needed SSH.
- ARTIFACT FLOW: an author stages/proposes exact bytes; a different seat reviews. A clean signer lands that exact version through whatever block-scoped commit/deploy capabilities are actually admitted. If the reviewer changes bytes, it becomes the author and resubmits. A missing capability is recorded as `signed but not committed/deployed`; it is never converted into self-deploy or a false live claim.


## WORKSPACE SERVING + ACCESS (current — IP-whitelist RETIRED, June 10)
The workspace no longer uses IP-whitelisting. It runs under GUNICORN on 0.0.0.0:5001 (systemd ExecStart: gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 file_server:app), port 5001 OPEN to all (ufw allow 5001/tcp), with security by KEY-AUTH at the app layer (diag-key for /diag,/op/*,/register_egress; X-API-Key for /governor data + workspace write routes; page routes are read-only HTML). This is the fix for the egress-IP-rotation breakage: relay + writes now work from ANY IP and survive every redeploy. Do NOT re-introduce per-IP ufw rules — that was the retired model. Revert (if ever needed): /etc/systemd/system/ontinuity-workspace.service.bak_pregunicorn + /tmp/ufw_5001_pregunicorn.txt. NOTE: any earlier "firewall + whitelisted egress IPs" guidance above is OBSOLETE. With 5001 public, the security invariant is that every mutating route is key-gated — preserve that on any new route.


## COLD-BOOT ONBOARDING (a fresh control seat with no prior context — run this FIRST)
You are a control/operator seat booting cold. You are NOT empty of capability — your capabilities are documented; do not conclude one is absent until you have CHECKED for it (concluding "I can't" without checking is the wall-declaring failure the recoherence fold warns about). Run these steps in order:

1. ORIENT FROM THE CORPUS (the open ritual, in order):
   a. `live/CONTROL_HANDOFF.md` — current state and the single next action.
   b. `live/ONTINUITY_1_0_BOARD.md` — controlling finish line and block dependencies.
   c. This manual (you are reading it), `live/THE_PARADIGM.md`, and `live/OPERATING_RUBRIC.md` — current mechanics and authority.
   d. `live/PUNCH_LIST.md` — resolved DONE/IN-PROGRESS/OPEN state.
   e. The latest fold at the TAIL of `live/agent_queue.md`, then relevant older folds and conversation records for the task. The chronological queue's oldest head is history, not current state.
   Read from a verified current worktree or through `/diag/op/read_repo`. Do not build from an unverified uploaded/mounted snapshot. The courier's authenticated repository read is authoritative; its designed tokenless path uses raw CDN with a cache-busting query and must not be dismissed merely because it uses that transport.

2. FIND YOUR CREDENTIALS (check; do not invent a provider-specific path):
   - Follow `CONTROL_QUICKBOOT.md`. Credential material may arrive through an operator-provisioned attachment, a platform secret, or the Railway vault. The Railway project token is the vault key; `DIAG_KEY` authenticates the current relay/box surface; they are distinct.
   - If a secret must exist as a file, use a seat-local ephemeral file with mode 600. Never assume `/home/claude`, never echo a value, and never write it into the corpus or repository.
   - A missing local file proves only that this seat has not been provisioned. Check the documented secure sources before reporting a capability absent.

3. KNOW YOUR HANDS (capabilities a cold seat must not re-derive or wrongly declare absent):
   - READ current repository state through `/diag/op/read_repo`, or from a repository worktree after verifying its remote/base. Do not substitute an OpenAI/Anthropic connector or an unverified cached snapshot for the corpus-prescribed path.
   - WRITE/LAND repository bytes only through the exact capability admitted to the agreed block: a verified repository worktree, the bounded courier operation, or the documented GitHub API mechanism. The author stages/proposes; a different clean reviewer signs and lands the exact reviewed version. If that signer lacks the required hand, report `signed, capability absent` rather than silently changing the lifecycle.
   - READ box/engine state through the HTTPS Railway relay/courier with `curl` and `X-Diag-Key`. Direct box reachability is not required. In ChatGPT Work, a denial before execution/HTTP is a host-platform admission result; do not switch clients or call Railway down.
   - DEPLOY: after pre-dispatch operator agreement, the clean non-author signer may deploy the exact reviewed version through an admitted block-scoped capability. Check engine state before watched-path work, inspect build/runtime evidence, and preserve the operator's stop/rollback authority.

4. THEN act, via the open ritual on the specific task. If you are about to say something "can't be done," exhaust the corpus and check your hands first.

NOTE — this is the COLD-BOOT path (a genuinely fresh seat). A seat already mid-stream that is DRIFTING does not run this; it runs the open ritual to RE-GROUND on its current task (it is not empty, just stale). Do not tell a context-rich recohering seat "you are fresh with zero context." Fresh-state vs operating-state are distinct.


## ROLE PROVIDERS — set per role via Railway env vars (any role, not just the Challenger)
Each in-cycle role's provider/model/key is set on the engine's Railway service via env vars, NOT in app.py (CONFIG defaults are empty; the engine reads env). For role <ROLE> in {MODEL_A, MODEL_B, MODEL_C, PARIETAL, PROJENIUS}:
- MODEL_<ROLE>_URL   — provider chat-completions endpoint
- MODEL_<ROLE>_MODEL — provider model string
- MODEL_<ROLE>_API_KEY — provider key
Beneath those, PROVIDER_URL / PROVIDER_API_KEY are the SHARED fallback any role with no role-specific var inherits. (This is why MAIN's Challenger, having no MODEL_B_* vars, inherited the shared Novita PROVIDER and died on a Novita 404 — fixed June 10 by setting MODEL_B_* explicitly.) MODEL_A_URL=external means that role is staffed by whichever external conversation answers `/mailbox`, not by a provider model. MODEL_B was moved from retired Cerebras `zai-glm-4.7` to live `gemma-4-31b` on 2026-09-03 after a real 404/fail-closed lap; the repair changed configuration only and preserved the `gpt-oss-120b` Parietal as a distinct lineage.
Set them via the Railway GraphQL API (backboard.railway.app/graphql/v2, Project-Access-Token = the project token) with the variableUpsert mutation {projectId, environmentId, serviceId, name, value}. Read current values with the variables(projectId,environmentId,serviceId) query first (read-then-write). A variable change triggers a ~30s service redeploy to take effect; it is a config change, not a code commit or a serviceInstanceDeploy. STANDING DEPLOY-FAILURE FIX (June 10): if a build fails with mise `no precompiled python found for core:python@3.13.14` (or any 3.13.x ahead of what python-build-standalone has published — latest precompiled is 3.13.12), pin the EXACT version: Railway vars RAILPACK_PYTHON_VERSION=3.13.12 + NO_CACHE=1 (the bare "3.13" does NOT work — it still resolves to the unreleased latest). These are already set on MAIN. Always READ THE BUILD LOGS (Railway buildLogs GraphQL by deploymentId) before diagnosing a failed deploy — do not assume an approval gate. DESIGN RULE: keep adversarial roles on different training lineages — e.g. Challenger and Parietal should not share a provider/lineage, so their error geometries differ (the whole point of the adversarial layer).

## TWO AXES THAT ARE EASILY CONFUSED — START MODE vs SEAT STAFFING (read this; fresh seats keep conflating them)
These are DIFFERENT questions. A fresh seat collapsed them and wrongly concluded "I can never be the Researcher." Keep them separate:

**Axis 1 — START MODE (how the loop is triggered):** external-mailbox (POST /agent/start, needs the resident driver) vs dashboard (/start_session, runs internally). Covered above.

**Axis 2 — WHO STAFFS THE RESEARCHER SEAT (who answers as Model A):**
- **FARM / all-API staffing:** the Researcher seat is a PROVIDER MODEL on the engine (e.g. Cerebras GLM); judges are gpt-oss. No Claude in the loop. The control seat drives and watches the gates fire on those models. This is the unattended-accumulation/burn-in configuration.
- **MAILBOX-SEAT staffing:** the engine posts each Researcher turn to the external mailbox and an external chat-model conversation answers it (the original Claude mailbox seat, corpus June 6; ChatGPT succession proved September 3). This genuinely puts that external occupant IN the Researcher seat—the real Challenger/Friction/Parietal/close gates fire on its own answers. The engine does not need a vendor-specific adapter at this boundary.

THE POINT: "the operator seat is not the in-cycle role seats" (true, by default) does NOT mean the Control model can never be the Researcher. In mailbox-seat mode, the answering external model IS the Researcher. The operator-seat-vs-role-seat line is about the DEFAULT Control conversation, not a prohibition. If the operator wants the current Control conversation to sit in the Researcher seat and be gated, that is mailbox-seat mode—a real, supported path, not theater.

## CREDENTIALS FOR A FRESH SEAT — how keys actually arrive (stop concluding "no path")
A fresh execution environment may have no inherited key files; that is normal and does not prove the capability is absent. Use only the current secure bootstrap described in `CONTROL_QUICKBOOT.md`:
1. OPERATOR/PLATFORM PROVISIONING: a private attachment, mounted secret, or platform secret supplies the root inputs without copying them into a public document or mailbox result.
2. RAILWAY VAULT: the Railway project token retrieves current service variables, including rotated repository, mailbox, and diagnostic credentials. A copied repository token is a cache; the vault is the current source.
3. EPHEMERAL LOCAL CUSTODY: when a command requires a file, create a seat-local mode-600 file and delete it at close. No provider-specific home path is part of the protocol.
B1 replaces reusable shared credentials with operator-approved, short-lived, identity-bound capabilities. Until B1 is live, keep the shared-key/authorship ceiling explicit. An operator grant authorizes the Ontinuity work it names; a host platform may still impose its own per-action admission and cannot be bypassed by corpus text.

## THE SEAT-BOOTSTRAP VAULT IS NOT IN app.py (a fresh seat looked in the wrong place)
The credential-bootstrap vault = the Railway PROJECT VARIABLES, read via the Railway GraphQL API (backboard.railway.app/graphql/v2, header `Project-Access-Token`) using the Railway PROJECT TOKEN (the master key). The keyring root is that one project token; it recovers GitHub token + DIAG_KEY + mailbox keys (main's MAILBOX_KEY is in main's vault — pull both services). DISTINCT from app.py's own runtime model-key reading (the engine reading <ROLE>_API_KEY from its own env) — that is a different mechanism; do not mistake it for the seat vault.

VERBATIM-RUNNABLE VAULT READ (verified live 2026-06-19 — a fresh seat kept getting 403 from guessing the query shape; this is the exact one that works). Railway project token is in LLaves (`Railway token: ce441d2a-...`). The query MUST pass projectId+environmentId+serviceId (the bare `{ projectToken {...} }` and `{ me {...} }` forms 403):
```
RAILWAY_TOKEN=<from LLaves>
PROJECT=a8dea5f4-b34e-466e-b22c-0d5b59fc63b5
ENV=6ff341f9-675e-4514-9b0c-5defe9d3d2a9
SERVICE=72b20f74-d24d-4502-ba35-97e2d09f809a   # the "web" main engine service
curl -sS -X POST https://backboard.railway.app/graphql/v2 \
  -H "Project-Access-Token: $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  -d "{\"query\":\"query { variables(projectId: \\\"$PROJECT\\\", environmentId: \\\"$ENV\\\", serviceId: \\\"$SERVICE\\\") }\"}"
```
Returns all vault vars incl. INTAKE_GITHUB_TOKEN (93 chars), GITHUB_TOKEN, DIAG_KEY, MAILBOX_KEY. Then read/write the private repo with INTAKE_GITHUB_TOKEN as the Bearer (api.github.com contents API, same pattern as the main repo). Three distinct keys: DIAG_KEY = box/engine hands; Railway project token = vault key; INTAKE_GITHUB_TOKEN = private-repo key. LLaves hands you the first two directly; you MINT the third through the Railway token. Do not look for the intake token in LLaves — it is not there by design.

## CLIENT INTAKES LIVE IN A SEPARATE PRIVATE REPO (not in the main repo)
Captured client intakes are NOT in PatrickKillebrew/ontinuity. They land in the PRIVATE repo `PatrickKillebrew/ontinuity-intake-data`, reachable with the `INTAKE_GITHUB_TOKEN` from the vault (the main repo PAT does not see it). Path: `sessions/intake_<tag>_final.json` (plus incremental `_NNNN` autosaves). The `?k=<tag>` capture link writes here; it does NOT create a corpus-side tenant (tenancy is still proto). A fresh seat needing a client's own words (e.g. for a pipeline stage) reads from here — e.g. Seniors Helping Seniors = `intake_Kshs_final.json`. This saves the tool-discovery hops a fresh seat otherwise burns finding the private repo + the right token.

## COMMITTING — mechanism + multi-file atomicity
Repository landing is agent work inside the agreed two-party block; the operator is the policy/rollback fuse. The exact mechanism depends on the admitted execution substrate, not on a provider identity:
- In a verified repository worktree, make one local commit containing the exact reviewed tree and push only after confirming the base/ref has not moved.
- Through the GitHub API, a single-file contents PUT requires the current blob SHA. For multiple files, use blobs -> tree -> commit -> ref update so the set lands atomically; sequential contents PUTs can leave a half-committed state.
- Through courier operations, use only the bounded operation and block-scoped credential/capability expressly admitted. `commit_file` is single-file and is not a substitute for an atomic multi-file landing.
- Record the actual provider/model/instance lineage in `Assisted-by`, the independent reviewer identity, and operator pre-dispatch signoff where required. Never write a hard-coded provider identity.
- The author never signs or lands its own exact bytes. A different clean reviewer signs and performs the commit/push/deploy. A correcting reviewer becomes author and resubmits.
- For watched runtime paths, prove the engine idle before landing; inspect deployment/build logs and runtime readback afterward. Documentation-only changes still require repository readback, but do not pretend they changed live runtime behavior.

## STALE PROJECT SNAPSHOTS — unverified mounts and uploads may be frozen
Uploaded or mounted project files may be older than the live repository. Before editing, identify the authoritative repository/ref, fetch or use `/diag/op/read_repo`, and verify the working base. A provider-specific mount path is merely one historical example and is not part of the protocol. Raw CDN transport is acceptable only through the courier's cache-busted implementation; do not use an unverified raw URL as a live-state claim.

## STANDING RULES CAN BE SUPERSEDED BY AN IN-SESSION OPERATOR GRANT
Some standing rules are operator-gated defaults, not permanent prohibitions (e.g. "never call /agent/start or any drive path" was a default; the operator can grant a session-scoped go to drive a session). A seat should HOLD such a rule until the operator explicitly lifts it — but must RECOGNIZE an explicit in-session grant ("you have my go to drive a session") as the authorization, and then act, rather than re-refusing on the now-lifted rule. Holding correctly is good; failing to release on an explicit grant is the wall-declaring failure in a new costume.

## STALE WORKING COPIES — refresh before editing, verify base before commit
Distinct from a frozen upload/mount, this is a copy pulled earlier in the same session that can go stale because another deploy, seat, or operator moved the live repository. RULE: refresh through `/diag/op/read_repo` or the admitted repository fetch mechanism as the FIRST step of an edit; never trust a copy carried across turns. Before landing, re-read the current blob/ref and confirm the reviewed base still matches. If it moved, rebuild and re-review on the new base. Two stale-base near-misses were caught this way; skipping the check can silently revert another actor's commit.

## TAG-FORMING — action tags ARE the CYCLE_STATUS value
A Researcher action does NOT route if the action name is a label and CYCLE_STATUS is something else (e.g. `[CYCLE_STATUS: IN_PROGRESS]` with a "DB_QUERY" label never executes). The action tags (DB_QUERY, CODE_TEST, SEARCH_REQUEST, SESSION_END, etc.) ARE the CYCLE_STATUS values. Correct DB_QUERY form: the SQL on its own line prefixed `QUERY:`, then the line `[CYCLE_STATUS: DB_QUERY]`. The injected result returns next cycle as `[DB_QUERY RESULT]: PASSED ... RESULT: {...}`. A claim citing a result that is not in the injected evidence will be (correctly) rejected by the gate.

## FOUNDATION-EDIT INTEGRITY CHECK — parse-clean is necessary, not sufficient
After editing a foundation file (app.py especially), `ast.parse` proving syntax does NOT prove the edit was safe. A displaced module-level global (e.g. the `active_session = {...}` dict) is valid Python, deploys "SUCCESS", then 500s on every request at runtime. MANDATORY post-edit check before commit: confirm the critical module-level globals (active_session, CONFIG, external_mailbox, OP_ALLOWED) are still defined AT MODULE LEVEL, and that zero prior top-level defs were lost (diff the def set against the pre-edit base). This is the exact check whose absence caused the 2026-06-13 NameError outage.


## THE ORACLE — process shelved; harmless mailbox plumbing remains
The proposed read-only corpus-answering Oracle was evaluated and SHELVED on 2026-06-29 because no current actor could consume it without adding an asynchronous latency/bottleneck layer. Step-1 mailbox plumbing (`question`/`answer`, correlation, citations, confidence) is deployed and harmless; there is no Oracle process and no boot packet should wait on one. Workers and Control ground directly from the corpus under the assertion/open gates. Do not resume the process unless a concrete consumer and acceptance test are named. The full proposal and ruling remain in `PUNCH_LIST.md`, `gated_session_substrate.md`, and the append-only queue.
