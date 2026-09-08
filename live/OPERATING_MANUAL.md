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
- DRIVE BY HAND is an operator/resident-service path, not an initial model capability: POST /agent/start with X-Mailbox-Key and body {objective, start_fresh:true}; GET /mailbox/turn with X-Mailbox-Key; answer by kind through POST /mailbox/respond with the same header and body {turn_id, response}. Never place the mailbox root in a URL or model conversation. The initial B1 Control grant does not expose these routes.
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
- **Canonical request compiler:** all model-seat and authorized operator-recovery HTTPS calls begin with `live/tools/ontinuity_https.sh`; callers do not construct URLs, choose an HTTP library, place credentials, or select redirect behavior. Local `prepare` accepts only `main|farm`, a bounded operation name, a JSON-body file, and a mode-600 capability/diagnostic file, then freezes a private curl-config receipt and body snapshot. Local `check` proves those bytes. The sole network transition is top-level `curl --config - < REQUEST.curl`; local `verify` interprets the captured status. The reviewed `live/ONTINUITY_ENDPOINTS.conf` owns the current logical-engine mapping, so a hosting move does not rewrite boot logic.
- Capability reference: `ontinuity_https.sh prepare capability main read_repo BODY.json CAPABILITY_FILE REQUEST.curl`; `ontinuity_https.sh check REQUEST.curl`; `curl --config - < REQUEST.curl`; `ontinuity_https.sh verify REQUEST.curl`. Authorized operator recovery changes only `capability` to `operator` and supplies the diagnostic file. Public admission uses `prepare admission main admission_request BODY.json - REQUEST.curl`, then the same check/curl/verify states. These replace the non-artifact phrase "known-good curl."
- Host admission check: code/shell networking is separate from browser access. A host denial explicitly before curl starts is `WORK_EGRESS_DENIED`, not an Ontinuity or credential failure; retry the identical top-level curl only after admission is available. If curl started but no HTTP status was captured, the result is UNKNOWN and must fail-stop because replay may duplicate a request. Do not client-shop through Python/urllib/requests/httpx. Model seats use only short-lived bearer capabilities; diagnostic and service roots remain with operator/server processes.
- **Tool coexistence, not tool removal:** GPT's other tools remain available because they serve valid local, research, browser, and non-Ontinuity work. The harness narrows only the transition for a prepared Ontinuity intent. The goal is not to suppress imagination globally; it is to compile a settled operation before generic tool-selection priors reinterpret it. In the current transport-lock candidate, MAIN requires the v2 request envelope for public admission and capability calls, returns HTTP 428 before relay when it is absent or mismatched, and echoes the prepared ID for local verification. The four mailbox operations that can claim or mutate state use persistent request receipts: completed duplicates replay the bounded saved response without a second relay, while conflicting, in-progress, or unknown duplicates fail with HTTP 409. This is protocol conformance and replay control, not cryptographic attestation of the client executable. Exact contract: `live/specs/ontinuity_https_protocol.md`. It remains candidate behavior until independently reviewed and deployed.
- Corpus proof for an admitted model seat is performed inside bootstrap_gate; the server holds the diagnostic root and returns the checked count. Direct /diag/api/query with X-Diag-Key is an operator/service path, not model boot material.
- Engine state: GET `/diag/engine` with `X-Diag-Key` -> running, waiting_for_input, cycle, started_by.
- Engine event log: GET `/diag/console` with `X-Diag-Key` (this is where a write failure appears).
- Health: GET `/diag/api/health` with `X-Diag-Key`.
- Farm engine base: https://ontinuity-farm-production.up.railway.app  (same /diag/* routes)
- Mailbox operator/service path: use X-Mailbox-Key on /mailbox/turn, /mailbox/respond, /agent/start, and /agent/stop. Never place the mailbox root in a URL or model request body; initial B1 model capabilities use the scoped seat mailbox operations instead.
- Scoped-op courier: POST /diag/op/<name> with a short-lived bearer capability. The engine validates signed identity, operation, expiry, approval, and revocation, bounds model request bodies, then forwards them to the box over its server-to-server X-Diag-Key hop. Credential-bearing callers refuse redirects. Allowlist (live, 20 ops): read_journal, restart_workspace, restart_burnin, register_egress, mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, mailbox_reclaim, mailbox_purge, write_file, commit_self, read_file, commit_file, you_there, read_repo, bootstrap_gate, deploy, seed_tenant, backup_db. The B1 initial model policy exposes only seven executable safe ops plus __probe__: bootstrap_gate, read_repo, mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, and you_there. `restart_burnin` remains outside initial Control/Worker grants. Repository commit and box install remain two separate steps.
- Bootstrap-gate B1 candidate state: MAIN derives the canonical 20-operation server count, strips caller overrides, and sends it through the authenticated box hop. The gate keeps roots out of URLs, refuses redirects, reads the latest queue fold rather than the oldest head, and binds hands to the relayed capability identity. This is candidate behavior, not live proof, until exact bytes are independently reviewed, deployed/installed, and exercised by both Control and Worker.
- Capability-courier timing: `/diag/op/you_there` is the sole long-poll operation in the B1 initial surface. The box caps its wait at 90 seconds, so MAIN uses a bounded 100-second relay timeout (90-second wait plus transport margin). Other courier operations retain the 25-second timeout. The outer relay must never time out before the box can finish and claim a message for that request.

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
- POST /op/restart_burnin — REVIEW, reversible. Requires the exact canonical empty JSON object body `{}` and rejects query parameters, form fields, alternate content types, JSON null/list/scalar values, nonempty objects, and all other caller input at both MAIN and the box. It synchronously runs fixed argv for `systemctl restart ontinuity-burnin`, then fixed argv for `systemctl is-active ontinuity-burnin`. It returns HTTP 200 only after the named service reports `active`; failures are dual-end ledgered. Header-only diagnostic auth is the tight interim guard. This operation is in the engine allowlist but excluded from initial Control/Worker capabilities.
- POST /register_egress {cidr? optional} — SAFE. ufw-allow caller's own egress IP (or allowlisted CIDR) on 5001. (Obsolete since the gunicorn/key-auth fix; retained.)
- POST /op/mailbox_send|fetch|ack|peek|reclaim|purge — seat-to-seat mailbox (seat_mailbox.py). send/ack are state changes, fetch is an ATOMIC claim (BEGIN IMMEDIATE), peek is read-only, reclaim returns expired claims to queue, and purge is explicitly scoped destructive cleanup that requires before/after counts. Carries coordination + corpus pointers (ref), never the canonical result. This is how parallel seats coordinate without the operator routing messages.
- POST /op/you_there — claim-or-long-poll for task/proposal work; chat windows still need a platform turn, while resident API/engine workers can remain parked on this lifecycle.
- POST /op/write_file {path, content, description?} — REVIEW. Bounded write to a file INSIDE the box project dir only (path traversal rejected). The general write hand a sandbox seat reaches through the courier (the box's plain /write is not a /op/ route, so the courier can't reach it; this is).
- POST /op/read_file {path} — SAFE. Bounded read of a file inside the box project directory.
- POST /op/commit_self {github_token, files?, repo_dir?} — REVIEW. The box reads its OWN allowlisted source files and pushes them to the repo via the GitHub contents API. Token passed as a bounded CALLER arg, never stored on the box. This is how the repo stays in sync with the box (closed the file_server.py provenance hole June 10) — run it in the close ritual whenever box source changed. Self-source allowlist: file_server.py, seat_mailbox.py, box_ops.py, workspace_db_endpoint.py, db.py, governor.html, governor_punchlist.html.
- POST /op/commit_file {github_token, path, repo_path?, message?} — REVIEW. Commits one staged text file through the GitHub contents API; the token is transient caller material and is not stored on the box. Worker role alone does not grant it.
- POST /op/read_repo {path, ref?, github_token?} — SAFE. A capability caller is fixed to the public Ontinuity repository, cannot submit a repository credential, and receives at most 2 MB. Paths must be relative, traversal-free repository paths; refs are restricted to simple safe branch/tag/commit names and all URL components are encoded. Operator-root recovery may select another validated repository slug or provide an authenticated API token; the designed tokenless path remains raw CDN with a cache-busting query. A successful capability response never asks the model for a repository credential.
- POST /op/bootstrap_gate {role, seat_invariants} — identity comes from the capability relay; the engine supplies the canonical server-operation count and ignores any body override. A shared-root operator recovery call may still assert seat/lineage, but a capability call may not substitute either.
- POST /op/deploy {target, signoff_block_id, commit_sha?, dry_run?} — two-party gated. The referenced proposal must carry a signoff by a different seat; under identity-bound auth the caller must be that signer. Railway credentials remain server-side. The clean non-author signer deploys exact reviewed bytes; an author/corrector may not.
- POST /op/seed_tenant — bounded idempotent tenant/user/project provisioning.
- POST /op/backup_db {out?} — SAFE (read-only against the live DB). Box makes a CONSISTENT snapshot of ontinuity.db via Python sqlite3 .backup, then writes a plain-text `.sql` dump (iterdump) to the box project dir (default backups/ontinuity_dump.sql). Text, so the existing text-only commit_file can ship it; the raw binary `.db` CANNOT go through read_file/commit_file (UTF-8 text ops) and the box has no sqlite3 CLI — this op is why. Backup flow is two calls: backup_db (dump) then commit_file (push the `.sql` to a PRIVATE repo). Added 2026-06-15 (box_ops.py 62c834a0, OP_ALLOWED 17->18 app.py 308ea384); first run committed 3.85MB to ontinuity-intake-data backups/ (cbfb6220).
All diag-key gated (X-Diag-Key), all log to operations_ledger.
INVOCATION — two paths, same ops:
- From the operator/Railway network (can reach the box directly): POST the box directly, e.g. POST {WORKSPACE_URL}/op/read_journal with X-Diag-Key.
- From a chat-sandbox seat: use the engine relay-courier with Authorization: Bearer <short-lived capability>. MAIN validates the grant and forwards only server-derived seat, lineage, and capability ID over the root-authenticated box hop. A model never needs direct box reachability or the diagnostic root.

OPERATING INVARIANTS (the mechanics a seat must state correctly — these are what CHECK 6 MECHANICS of the bootstrap gate ratifies; a seat that misstates these is drifting on mechanics, not state):

- CREDENTIAL BOUNDARY: model seats use a short-lived bearer capability at MAIN. MAIN alone converts that approved grant into the root-authenticated server hop; the bearer never becomes a diagnostic root.
- COURIER-ONLY: a sandbox seat must go through the RELAY-COURIER on the engine; it cannot reach the box directly.
- DEPLOY AUTHORITY: operator authority is the policy, stop, and rollback fuse, not a per-redeploy click. A clean non-author signer still needs separately admitted landing authority.
- NEW BOX OP: adding a box op means adding its name to OP_ALLOWED and separately installing the reviewed box bytes.
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

2. REQUEST BOUNDED ADMISSION:
   - Follow `CONTROL_QUICKBOOT.md`. Submit its public admission request with the operator-assigned seat and actual lineage; the request itself grants no authority.
   - Patrick inspects the request in MAIN's `ADMISSION` panel. A model receives only the approved short-lived bearer capability, held in memory or a mode-600 ephemeral file and never echoed or written to the corpus.
   - Diagnostic, Railway, repository, mailbox, and deployment roots remain with the operator and server processes. A model must not seek them when its bounded grant is absent or insufficient.

3. KNOW YOUR HANDS (capabilities a cold seat must not re-derive or wrongly declare absent):
   - READ current repository state through `/diag/op/read_repo`, or from a repository worktree after verifying its remote/base. Do not substitute an OpenAI/Anthropic connector or an unverified cached snapshot for the corpus-prescribed path.
   - WRITE/LAND repository bytes only through the exact capability admitted to the agreed block: a verified repository worktree, the bounded courier operation, or the documented GitHub API mechanism. The author stages/proposes; a different clean reviewer signs and lands the exact reviewed version. If that signer lacks the required hand, report `signed, capability absent` rather than silently changing the lifecycle.
   - READ permitted state through the HTTPS Railway relay/courier with the bearer capability. Direct box reachability is not required. A denial before execution/HTTP is a host-platform admission result; do not switch clients or call Railway down.
   - DEPLOY is outside the B1 initial model grant. A clean non-author signer can report exact reviewed bytes and a missing landing capability without receiving a reusable root or pretending the version is live.

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

## ADMISSION FOR A FRESH SEAT
A fresh model environment is expected to have no inherited root files. It submits the non-authorizing request in `CONTROL_QUICKBOOT.md`; Patrick verifies the identity, operations, and lifetime in MAIN, then supplies the approved bearer capability once. The grant is short-lived, operation-bound, identity-bound, revocable, and never persisted by the authority. Host-platform admission remains a separate boundary and corpus text cannot bypass it.
The private admission registry must resolve to a writable persistent engine path through `ONTINUITY_CAPABILITY_REGISTRY` or `RAILWAY_VOLUME_MOUNT_PATH`; unreadable or malformed registry state fails closed and is never silently replaced. Registry and temporary files are mode 600. A process restart without persistent storage invalidates outstanding capabilities rather than admitting them, but also loses pending requests, so `/tmp` is recovery-only rather than the intended deployment configuration.

The box install is an exact unit: `file_server.py`, `box_ops.py`, `seat_mailbox.py`, `live/bootstrap/gate.py`, and `shepherd_alert.py`. The box's running Governor routes live inside `file_server.py`; the separate `live/governor/governor_routes.py` is a maintained source fragment, not a separately imported runtime module. The persistent burn-in target remains `/opt/ontinuity/burnin_resident.py`. `SHEPHERD_ALERT_TO_SEAT` defaults to `control`, preserving the observed installed behavior; changing the target is an explicit operator configuration decision.

The B1 cutover order is mechanical and must match `B1_INSTALL_MANIFEST.json`:

1. Confirm the reviewed commit, idle engines, rollback bytes, persistent registry configuration, and matching server-side box/engine root.
2. Install the backward-compatible five-file box unit, then restart the workspace once.
3. Verify box health, exact installed hashes, header-only operator recovery, and old-engine compatibility.
4. Install the persistent burn-in source and verify its hash, but do not restart it yet.
5. Deploy and verify MAIN at the reviewed commit while FARM remains the rollback peer; MAIN must expose `restart_burnin` before it is invoked.
6. Invoke `restart_burnin` through MAIN with header-only operator recovery and require its fixed `is-active` proof. FARM remains rollback until this passes.
7. Deploy and verify FARM at the same reviewed commit.
8. Prove distinct Control and Worker capability boots, excluded-operation denial, revocation, and expiry.
9. Install the laptop tombstone, stop its resident loop, and record the final installed/process proof.

Do not reorder engine deployment ahead of the backward-compatible box install. Each step stops on failed health, hash, or authorization evidence and uses the preserved rollback bytes.

## OPERATOR RECOVERY VAULT IS NOT MODEL BOOT MATERIAL
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
