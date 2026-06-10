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


## CONTROL-SEAT CLOSE RITUAL (run at session close)
Re-distill the three records together so none lapses silently (the silent-lapse disease):
1. PUNCH_LIST.md — reconcile DONE/IN-PROGRESS/OPEN against what actually shipped this session (cite closing commit/receipt for newly-done items).
2. Conversation record (live/conversations/) — capture this session's dialogue per CONVENTION.md (rulings verbatim, redact keys/IPs, cross-ref shas/receipts). The control seat does this — a worker backfilling from commits cannot see the conversation window.
3. Sign-off / provenance ledger — ensure rulings + deploys this session are recorded.
All three key on the SAME shas/receipts (the join), so a stranger walks conversation -> decision -> commit -> receipt in either direction. Running all three in one ritual is what stops any one of them lapsing (conversation logging lapsed after one entry on June 7 precisely because it was not part of a ritual).


## CONTROL-SEAT OPEN RITUAL (run before reasoning about a task)
The bookend to the close ritual. Before proposing or acting on a task — ESPECIALLY after focusing on something else for a while — ORIENT FROM THE CORPUS, do not reason from memory:
1. Search the queue folds (live/agent_queue.md) for the topic — past decisions, verdicts, and reversals on it.
2. Read the relevant conversation records (live/conversations/) for the reasoning behind those decisions.
3. Follow the item's cited refs (sha / receipt) to the actual record.
Recall is NOT a substitute for retrieval. A long session degrades context; the corpus does not. Failing to load before acting is the silent-failure class — it produces confident proposals anchored to stale state (e.g. proposing to automate a mechanism the record shows was already retired). The fold/retrieval machinery is reliable; the only gap is failing to reach for it. Orient first, then reason.
