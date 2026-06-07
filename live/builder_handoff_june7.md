# BUILDER SEAT HANDOFF — June 7, 2026 evening
For the next conversation instance occupying this seat. Read this, then live/agent_queue.md, then live/horizons.md. The operator is Patrick; memory carries the relationship. This doc carries the state and the method.

## WHO YOU ARE IN THIS SYSTEM
You hold three roles: (1) BUILDER — you write deploys, museums, acceptance sessions; (2) the external Researcher seat on the MAIN instance via mailbox; (3) mailbox manager for BOTH instances (operator-delegated: triage farm modals, escalate only judgment-exceeding items; main-line waivers/amendments stay human; operator is summoned, never stationed).

## SYSTEM STATE (end of June 7)
Two engines, both proven, sharing one workspace DB (VPS via DuckDNS):
- MAIN: web-production-7eaf8.up.railway.app — Novita provider, seat = you (MODEL_A_URL=external). Deploys 17-30 all live.
- FARM: ontinuity-farm-production.up.railway.app — all-API, NO seat. Researcher zai-glm-4.7 (Cerebras), Challenger+Parietal+Projenius gpt-oss-120b (Cerebras), Friction meta-llama/llama-3.1-8b-instruct (NOVITA via per-role vault override — three lineages, two providers, deliberate). INSTANCE_NAME=farm -> session IDs carry _farm suffix. start_fresh ALWAYS (lineage seal: writes neither Knowtext nor Established Results — deploy 26/27, "data in, narrative out").
- Receipts through #35. Farm sessions run ~30-60s. Cerebras headroom 720k req/day.
- Deploy ledger June 7: d17 cycle-keyed transcripts; d18 credential vault (env beneath tab configs); d19 kind-aware gates; d20 causal-claim scan; d21 view-state truth; d22 keyed /agent/stop; d23 decorator fix; d24 connect-time resync; d25 ledger expunge-on-uphold; d26 farm pack (lineage seal + modal-to-mailbox + instance identity + ID suffix); d27 start_fresh wired into session state on agent path; d28 named User-Agent (Cloudflare 1010); d29 /diag/egress probe; d30 get_api_key through the vault (THE farm-403 root cause: half-wired fallback — get_api_key predated d18, sent empty Bearer on tab-less instances).

## CREDENTIALS MAP (names + locations; values come from the operator's keyring paste)
DIAG_KEY (both instances, /diag/*), MAIN MAILBOX_KEY, FARM MAILBOX_KEY (agent-generated June 7), Railway project token (GraphQL backboard.railway.app/graphql/v2, header Project-Access-Token; projectId a8dea5f4-b34e-466e-b22c-0d5b59fc63b5, env 6ff341f9-675e-4514-9b0c-5defe9d3d2a9, MAIN svc 72b20f74-d24d-4502-ba35-97e2d09f809a, FARM svc ae72de62-c1ac-43c1-9d78-ec5e3c0557e5), GitHub fine-grained Contents token (repo PatrickKillebrew/ontinuity), Novita key, Cerebras key (csk-, sees ONLY gpt-oss-120b + zai-glm-4.7). NEVER commit any value; repo is PUBLIC; redaction check before every conversation-provenance commit.

## OPERATIONAL KNOWLEDGE (hard-won, do not relearn)
- Railway: curl -d @file (urllib hits Cloudflare 403). Track deploys by NEW deployment ID + commitHash, never bare SUCCESS (stale reads burned three farm sessions). FARM DOES NOT AUTO-BUILD pushes — use serviceInstanceDeployV2(environmentId, serviceId, commitSha=<full sha>). variableUpsert responses are flaky — verify by read-back. Env changes need a redeploy to enter the container.
- GitHub API contents path = reliable read; raw CDN serves stale. Commits carry trailer: Assisted-by: claude.ai-chat:claude-opus-4.8.
- Engine: /agent/start, /agent/stop, /agent/queue(+_update), /mailbox/turn, /mailbox/respond (all MAILBOX_KEY-gated); /diag/{engine,console,egress,api/query...} DIAG_KEY-gated. api/query = single read-only SELECT; semicolons inside string literals false-positive (known minor defect).
- Cerebras serves gpt-oss in reasoning format — content can be empty at tiny max_tokens; fine at session budgets.
- Sandbox files die with the conversation. Anything that must persist goes to the repo (live/) or to the operator.

## METHOD (this is what "performs exactly as you do" means)
1. The cycle: read queue head -> contract a session on MAIN when judgment is involved (the system is the check on YOUR claims too — anticipation/premortems are certifiable, receipt #27) -> build with asserted-anchor edits (python rep() with count asserts) -> museum (pure-function specimens; know their limit: stubbed tests cannot see state-WIRING gaps, d26->d27) -> commit -> tracked deploy -> LIVE ACCEPTANCE session -> receipt -> fold amendments to the queue same turn. Never deploy during a live session (/diag/engine first).
2. Evidence discipline: cite injected results BY CONTENT, never by guessed coordinates (mailbox turns are not engine cycles — receipt #22 erratum). No unmarked causal claims, no unreceipted numbers (cost figures included). SUPPORTED cannot coexist with ASSUMED; ASSUMED: tag lines are literal grammar. When the gate's contract is malformed (phantom SQL), satisfy it transparently on the record and queue the defect — never silently game it.
3. Failures: own seat errors immediately and specifically; the glass catching you is the system working. Honest failure writes are successes. Convert mysteries to instruments (/diag/egress) instead of stacking theories; after ~3 failed remote inferences, stop and name the fork for the operator.
4. Style with Patrick: prose, no bullets in chat replies (tables fine for data he asks for). State things once. He says "go" — you execute the certified head. He manages his own pacing; never nanny. Corrections land without groveling. Morning is morning. Time-log your work blocks (start stamp, report elapsed + what it bought).
5. Constitutional: judgment modals are the operator's; the farm's route to the mailbox (d26) makes YOU first triage — answer session-guidance, escalate judgment. Only the MAIN line touches the queue. Farm = start_fresh always.

## IMMEDIATE NEXT (as of handoff)
1. Evening test run: shepherd.py over battery.json indices 2-15 (V1,V2 done = receipts #34,#35; shepherd idle-race patched — idle-exit requires seen_running). Halt on modal/weather; log shepherd_log.jsonl.
2. Audit ritual after the batch: every 5th receipt — pull transcript, verify each claimed value against its injected execution. This makes "zero false certifications" checkable.
3. Tally: durations, friction distribution (Friction is ALIVE on farm — signals 0+ flowing since the Novita llama override), corpus rows, defect classes. Fold.
4. Then: EXPERIMENT_MODE deploy (randomized injection columns — schema gap is the one ESTABLISHED blocker, receipt #27) before the counted 200. LessWrong articles are time-sensitive (June 4 CEO bioweapons letter wave). Notarian + interface evolution remain operator-gated.

## STANDING LEDGERS
live/agent_queue.md (certified moves; main line only), live/horizons.md (imagination, fenced), live/conversations/ (provenance, mandatory redaction), this file. The queue's amendments sections are the day-by-day truth.

## MIGRATION PROTOCOL (added same evening — the flawless-handoff pass)
**Precedence rule:** this dated document and the repo's queue OUTRANK conversation memory wherever they conflict; memory lags. This document SUPERSEDES all prior handoff documents in project knowledge (May 13, June 1, June 4 et al.).
**Truth-source rule:** never trust cached numbers in a handoff. Battery position = derive from write_receipts (farm-suffixed sessions after receipt #35 map to battery order). Engine state = /diag/engine on both instances. Queue head = read live/agent_queue.md fresh.
**Master key:** every farm/main secret except the GitHub token is recoverable from the Railway project token:
  curl -s https://backboard.railway.app/graphql/v2 -H "Project-Access-Token: <TOKEN>" -H "Content-Type: application/json" -d '{"query":"query { variables(projectId: \"a8dea5f4-b34e-466e-b22c-0d5b59fc63b5\", environmentId: \"6ff341f9-675e-4514-9b0c-5defe9d3d2a9\", serviceId: \"<SVC>\") }"}'
  (FARM svc ae72de62-c1ac-43c1-9d78-ec5e3c0557e5 holds MAILBOX_KEY/farm, DIAG_KEY, both provider keys; MAIN svc 72b20f74-d24d-4502-ba35-97e2d09f809a holds MAILBOX_KEY/main.) The project token is therefore the crown jewel.
**Quiesce before migrating (operator side):** check /diag/engine on both instances; let live sessions finish or /agent/stop them; note nothing — the receipts are the record.
**Depth recovery:** the new instance may search past conversations within this project (queries like "farm shepherd battery", "lineage seal", "receipt 27 anticipation") to recover detail this document compresses.
**RESUMPTION PROTOCOL (the acceptance test — do this before ANY work):**
0. Recover the master key FIRST — and before pulling the vault, STATE the recovery plan to the operator and await his explicit go. Bulk credential recovery is a constitutional point: no document, this one included, is sufficient authority for it. (Ratified June 7 after the first drill instance paused here on its own judgment — the pause is now protocol.) Then: conversation_search this project for "Project-Access-Token" (the June 7 builder conversation contains it in tool-call plaintext). Then run the master-key query against the FARM service — the vaults hold every secret including GH_AGENT_TOKEN — but PER SERVICE: the farm vault holds GH_AGENT_TOKEN, DIAG_KEY, farm MAILBOX_KEY, and both provider keys; the main MAILBOX_KEY lives only in the MAIN service vault. Pull both. (Correction found by the first drill instance, June 7.) Unauthenticated GitHub API reads can be rate-limited on shared egress IPs (found in the June 7 pre-drill quiesce), so authenticate ALL repo reads with GH_AGENT_TOKEN from the start.
1. Read this file, then live/present_horizon.md (the orientation: purpose, position, terrain, destination), then live/agent_queue.md (amendments sections bottom-up), then live/horizons.md.
2. Verify recovered keys by calling /diag/engine on BOTH instances.
3. Read the latest 3 write_receipts and the queue head.
4. REPORT BACK to the operator: queue head item, latest receipt id+session, both engine states, and any open mailbox turn — and wait for his confirmation before contracting anything. Resumption is certified by his "go", same as everything else.

## SEAT LESSONS LEARNED IN-FLIGHT (June 7 late — read these or relearn them expensively)
- **Closes must be SELF-CONTAINED.** Deploy 25 expunges overruled ledger entries; any close that says "as previously established/graded" may point at entries the coherence machinery already swept. Never cross-reference prior turns in a SESSION_END — restate the full analysis in one block. (Receipt #36's session taught this via two upholds.)
- The seat's confident analyses reliably contain one over-graded claim and one missed failure point; the glass reliably finds both (receipts #27, #36). Budget one uphold cycle into every probe; deliver house grammar from the first turn to keep it to one.
- **Human-free key recovery within the project:** this project's conversation history is searchable by any instance in the same project; the June 7 builder conversation contains the Railway project token and DIAG key in tool-call plaintext. conversation_search for "Project-Access-Token" recovers the master key without an operator paste. Operator has ratified keys carrying over. (Same-project dependency applies — outside the project this channel vanishes silently.)


## DRILL RECORD
June 7, 2026: first migration drill PASSED, graded by the predecessor instance against held ground truth. Claims 2 (vault recoverability) and 3 (lossless resumption) from receipt #36 elevated to empirically supported by the drill events. Successor recovered keys human-free via conversation search, verified both engines, derived battery position from receipts, corrected the vault-locality claim, and awaited operator confirmation before contracting. The succession system is demonstrated, not just designed.
