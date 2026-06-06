# AGENT QUEUE — seeded from Punch List v5, June 6 2026
This file is the live work queue for the contract-queue loop (v5 item 2).
Protocol: contract the HEAD ACTIVE ITEM ONLY; close or amend on the record;
fold session learnings back into this file via /agent/queue_update; RE-READ
before contracting the next item. One item at a time — blast radius is one item.
Items 1 (mailbox) and 2's infrastructure (self-start, queue path) are closed
with receipts #5-#7; deploys 10-13 verified.

# Ontinuity Punch List v5 — June 5, 2026 (day end)
Supersedes v4. BUILDER lane document. The day: 9 deploys (all museum-tested pre-commit, fingerprint-verified post), contract system complete (authoring → freeze → amendment → waiver → WP spine), Notarian named/built/demo-passed, KEYS ritual killed, 2 sessions assassinated and autopsied, 5 F.3 false-positive classes cured, receipt #4 landed on a 91-second natural close. Museum: ~18 specimens.

## CLOSED TODAY (since v4)
- **Item 1 — Session contract (deploys 5, 7).** PRE_SESSION freezes ID'd VERIFIABLE/JUDGED criteria; authored against the live workspace whitelist (F.10 probe, 10-min cache); close gate walks the contract deterministically. Amendment machinery: structurally-refused criteria (attempted + 403) escalate to operator WAIVE/UPHOLD, recorded in challenge events, contract injection, and WP. Never-attempted ≠ waivable.
- **Item 2 — WP from contract (deploy 6).** Verified Results spine assembled BY CODE from contract + execution log; extractor reproduces verbatim + narrative only; F.3 audits the extracted WP and annotates flagged claims. Proven tonight: caught the extractor inventing "the environment was queried" — flagged in ink, spine untouched.
- **F.3 maturation (deploys 8, 9).** Five false-positive classes now cured with museum tests: quoted outputs, cross-attribution, version-period sentence splits (v4-era), backticked values (59-cycle soak specimen), temporal narration ("blocked, then passed" ≠ denial; June 4 pure-denial still dies). Museum 15/15 in-harness.
- **Close-deadlock guard (deploys 8, 9).** All THREE refusal paths (F.3, contract, Challenger-incomplete) capped: 3 consecutive refusals → operator modal (STOP runs full end sequence / direction continues). The 59-cycle class is extinct.
- **The judge sees everything (deploy 9).** Datetime injection added to Challenger context — evidence a criterion cites must be IN the judge's context, never vouched for. (Sibling of "the judge reads the contract.")
- **The write survives its author's replacement (deploy 9).** `finalizing` flag gates new_session during end sequence; SIGTERM handler flushes session log + workspace write (model-free steps) inside Railway's grace window.
- **Watch patterns restored AND re-verified by query.** Root cause of both session kills: morning's pattern-set never persisted and was reported as done without re-query — every commit (including the engine's own Knowtext pushes) was live-firing deploys. Now: /app.py, /templates/**, /prompts/**, /model_client.py, /requirements.txt — confirmed present by read-back.
- **localStorage re-arm (index commit 1b08b5bb).** Socket reconnect re-pushes stored configs; server restarts invisible; KEYS→Save ritual dead. Proven by deliberate redeploy + console-visible auto-save 28s into the new container. Onboarding copy corrected ("nothing closes until the evidence agrees").
- **/diag/engine (deploy 8).** Local engine state (running, cycle, waiting, contract size). Pre-REPO check is now mechanical, exercised on deploy 9's commit.
- **Notarian (Tier 0).** notarian.py (497 lines, stdlib CLI: open/run/audit/close/receipt/trailers/hook/mcp) + README. Full demo passed incl. tamper-evident receipt chain and CC hook mode. Staged in outputs, repo not yet created.
- **Receipt #4** — session 2026-06-06_00-31-20, 3 cycles, natural close, all DB layers captured (4 transcript turns, 4 behavioral observations). Five assassination attempts survived. The gauntlet run is the article's closing exhibit.

## STANDING RULES (cumulative, amended)
- Never deploy/commit while a session runs or finalizes. **Mechanical now:** Claude queries /diag/engine before issuing any REPO instruction. (Violated once at 17:59 — killed the soak session; the check exists because of it.)
- **No unreceipted state claims by the BUILDER.** Every "it's set/committed/running" must cite a live read-back (fingerprint diff, API re-query, diag). Root-cause lesson of the day: the watch-patterns assertion.
- Operator never checks diffs; Claude verifies every commit fingerprint + deploy status + health.
- Engine Knowtext/session pushes must never match watch patterns (verified; re-check after any Railway service change).

## ACTIVE — ordered
1. **Deploy 10 — external Researcher mailbox (the confiscator seat).** GET/POST endpoint pair under diag-style auth: engine posts the Researcher turn (objective, conversation, injections, result blocks) and waits (wait_for_human_input pattern, proven 4× today); external agent (Claude) polls, composes, posts back. Mode flag `researcher_external`. Same glass: F.3, contract gate, receipts apply to the external agent's claims. Prereq for item 2.
2. **Contract-queue autonomy (the ratchet).** Punch list = live queue between sessions. Outer loop: read list → contract HEAD ITEM ONLY → run session → close/amend on record → fold breaks+learnings back into list → RE-READ list (it may have changed) → next item. One step at a time; blast radius = one item, forever. ORIENT reads the queue; DISTILL writes amendments back. Founder-lane decisions stay human.
3. **Notarian launch package.** Create PatrickKillebrew/notarian, upload notarian.py + README. Operator decisions pending: license (MIT vs BSL/open-core), private-until-articles vs launch-with-articles ("here's the paper, here's the tool — go break it"). Demo target: Notarian notarizing an agent doing a real punch-list item (duration capture is the natural first).
4. **Website refocus.** Everything outdated; converges with launch — center of gravity becomes thesis / Notarian / receipts. One job with item 3, not two.
5. **Workspace settings hardening (E.1-adjacent).** Tonight's wipe: saving with empty safe-commands textarea silently zeroed the whitelist. Fix: confirmation-on-save, field validation, and config-change receipts — the workspace audits commands but not its own configuration (the only receipt-less writes in the architecture). Plus: announce mid-session whitelist changes into live session context.
6. **Friction validation (first self-directed research task).** Corpus: 99 observations w/ metrics, 133 transcript turns; signal distribution 0×77, 1×19, 4×3. Start: calibration audit of the 77 zeros + the new exhibit (signal sat at 1 through an 80-min deadlock — a 59-cycle no-progress loop scored "nominal"). Full accuracy study starved of positives; Part 2 sigmoid generates its own data.
7. **Duration capture.** Elapsed-ms spans on model calls + executions. AR-001's founding wound; Kaplan-curve feedstock; candidate first self-built item under item 2.
8. **Museum merge.** test_f3.py (laptop-only — single-point-of-loss, proven risk) into repo; fold today's specimens: backticked-value, temporal-narration, June-4 regression pair, soak exhibits. Real museum ~18 specimens. Horizon framing: museum as adjudication precedent (judges cite specimen classes).
9. **Fallback-model routing.** Novita GLM read-timeouts recurred all day (killed throughput; nearly cost the receipt). Per-role fallback endpoint on timeout-exhaustion. Cheap insurance for autonomy.
10. **Environment epoch stamping** (v4 item 3, unchanged) — workspace identity injection; stamp banked results + ledger entries; epoch mismatch → stale flag → re-verify.
11. **Repo cleanup** — delete junk app files; add laptop-only criticals (file_server.py, workspace_db_endpoint.py, test_f3.py).
12. **VPS odds and ends** — BRAVE_API_KEY into systemd unit (SEARCH_REQUEST dead until then); apt install git (for /git rung); Caddy/TLS + ufw tightening.
13. **/git actuation rung 1** per GIT_ACTUATION_SPEC_v0_1.md — closes the commit gap for item 2 (sessions report trustworthily now; acting consequentially unlocked).
14. **F.5 / E.3 / P1.5 / cache-busted dashboard assets** — carried.

## LAYER-2 HORIZON (the institution verifies itself)
- **Lifetime ground truth:** Established Results Ledger design (Research mode) → F.3 v3 checks claims against the PROJECT ledger, not just the session log; cross-session contradiction refused with receipt citation. The retraction-never-deleted DB was built for this.
- **Calibrated judges with case law:** Friction accuracy curve (item 6), Challenger rulings graded against outcomes (challenge_events corpus exists), judgments citing specimen classes as precedent.
- **Autonomous confiscation (break lane):** adversarial contracts — defeat F.3, get a false close certified, make the judge sign falsehood. Every success → specimen → permanent check by morning. Frontier = just past the confiscated set; this makes its growth a design parameter.
- **Hash-chained engine receipts:** port Notarian's tamper-evident chain to the session engine; project history becomes tamper-evident end-to-end.

## EVIDENCE INVENTORY (article feedstock — archive these)
- The June 5 arc: morning 8-cycle deadlock → contract system → 59-cycle soak (zero fabrication under 80 min of pressure to invent `rearm-proof-jun5`; killed by deploy) → evening session (4 murders' worth of jurisprudence: config wipe, temporal-narration false positive, two unguarded loops, blind judge; killed by its own Knowtext push) → 91-second natural close + receipt #4.
- "A Date with AI" resolution: ~24h from documented date-fabrication problem to receipted, adversarially-verified, deterministically-gated date. Article 1 states the problem; session 2026-06-06_00-31-20's log is the resolution.
- WP audit catching the extractor's invented "query" — the architecture's thesis in one artifact.
- Industry positioning (searched June 5): decomposition + checkpoints now mainstream (Augment, Codex Subagents gates, Cursor checkpoints, Bernstein's deterministic Janitor closest cousin); NOBODY audits agent testimony — contracts, claim audits, refusal-to-certify, receipts remain unoccupied. "Early to nothing, alone on testimony."
- Soak/evening DB rows lost to the two kills — screenshots in BUILDER conversation are the only record; archive them.

## DAY'S SCORE
9 deploys, 1 product born (Notarian), 2 sessions assassinated → 2 autopsies → 7 structural fixes, 5 F.3 classes cured, 3 refusal paths guarded, 1 ritual killed (KEYS), 1 root-cause confession (unreceipted watch-patterns claim), 1 receipt that survived five murder attempts. The loop — failure → evidence → located defect → provable fix → verified deploy — ran continuously for twelve hours. Same ensemble of commodity models at 7:30am and 7:30pm; every capability gained came from structure. The next ratchet: the builder goes under the glass (items 1–2).

## LAP 1 AMENDMENTS — June 6, 2026 (session 2026-06-06_15-44-37, receipt #8, stopped honest-incomplete)
Lap 1 ran item 6 (friction calibration audit). Audit delivered in-session (judged criteria); close blocked by two environment defects. Findings folded back per protocol:

**Item 6 partial close — audit findings on the record:**
- Distribution (121 obs / 13 sessions): 0×97, 1×19, 2×2, 4×3, no 3s ever. Signal-1 rows carry 2× the upholds and 3.4× the challenge rate of signal-0 — the 0/1 boundary tracks evidence.
- NEW exhibit: the only signal-2 scores ever recorded (session 13-42-16) cite "two UPHOLD rulings" in their rationale while the same rows count cumulative_uphold_count=0 — scorer narrative contradicts its own features.
- Signal-4 rows: zero upholds, zero challenges — max-alarm with no corroborating adversarial activity (spurious-override confirmation, now in data).
- Data-quality: at least one empty rationale string on a scored row.
- Fix package (item 6b, NEW): feed loop-state counters (consecutive refused closes, no-progress) into Friction input; rationale must cite structured features only; reject empty rationales at write; gate signal-4 on ≥1 actual UPHOLD.

**NEW item — PyGithub missing on VPS (urgent, found by lap 1):** `python push_to_github.py` fails ModuleNotFoundError on every attempt — dead since the Hetzner migration. Fix: pip install PyGithub on the workspace host (operator, 2 minutes).
**NEW item — structural-waiver classifier too narrow:** deterministic environment failures (missing module, exit 1 reproducible) should qualify as waivable-structural alongside whitelist 403s.
**NEW item — in-session corpus evidence channel:** the Parietal UPHELD a challenge against agent-retrieved corpus figures — correctly: labeled provenance is not verification. Add a whitelisted read-only corpus query command (or DB_QUERY tag) so audit sessions get injectable, F.3-checkable evidence.
**NEW item — STOP must wake the mailbox wait:** operator stop during a pending external turn leaves the session zombie until the 15-min timeout (deploy 14: handle_stop fires the mailbox event).
**Cosmetics (one line):** completion-panel view-state stale during agent-started sessions; artifact row accumulates across sessions.
