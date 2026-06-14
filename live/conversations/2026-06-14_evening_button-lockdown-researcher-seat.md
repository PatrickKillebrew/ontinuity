# 2026-06-14 (evening) — Public-Button Lockdown + Researcher-Seat Mechanism Discovered

FORM: condensed (operator directives quoted close; seat actions summarized). Written by the control seat at close.
PARTICIPANTS: Patrick (operator); HARNESS:claude-opus-4.8 (control seat).
REDACTION: clean — no credentials.
LINEAGE: site commit 7477ce5d (disable public Begin Session). Continues the same conversation as 2026-06-14_first-solution-proposal-delivered.md (proposal delivery earlier in the day).

## Arc
After delivering the first Solution Proposal, the seat oriented into the WORKER half of Ontinuity (it had only read the control corpus), then attempted to put itself in the RESEARCHER seat (mailbox-seat mode) for the first time. The attempt failed on a config trap, the diagnosis surfaced a live public-exposure risk (ontinuity.org's Begin Session button wired to the unauthed MAIN engine), and the session pivoted to lock that down as priority before the operator's break.

## RESEARCHER-SEAT MECHANISM (the durable discovery — was a manual hole)
To put a Claude in the Researcher seat (mailbox-seat mode, the real harness-from-inside, NOT chat role-play):
- The switch is Model A's EFFECTIVE config = url "external" (app.py ~line 1716: `if role=="model_a" and config url startswith "external": return mailbox_researcher_turn(...)` — comment: "the engine cannot tell what occupies the seat"). Then the engine posts each Researcher turn to the external mailbox (kind=researcher_turn) and waits for the seat to answer via /mailbox/respond.
- DRIVE LOOP (by hand, control seat IS the driver on MAIN — no resident driver on MAIN, that's FARM): POST /agent/start {mailbox_key, objective, start_fresh} → poll GET /mailbox/turn?mailbox_key= → answer by KIND: pre_session_questions (answer the Parietal's contract questions, plain, no tag), researcher_turn (do the real Researcher work — ground claims, issue DB_QUERY/CODE_TEST tags, never fabricate a result), human_input_needed (modal) → POST /mailbox/respond {mailbox_key, turn_id, response}. Repeat to a gated SESSION_END (adversarial-review floor: cannot close in 1 cycle). turn_id may not start at 1 (stale external-mailbox state) — fetch first.
- PROOF you're actually in the seat (per shepherd.py's own logic): a `researcher_turn` arriving at the mailbox. On an all-API farm that means config DRIFT (shepherd halts on it); in mailbox-seat mode it's the intended state.

## THE CONFIG TRAP (why the first attempt failed — fold so the next seat doesn't repeat it)
get_effective_config precedence (app.py ~195): base CONFIG (empty for model_a) → runtime_configs[role] (set by the dashboard KEYS modal via save_api_keys socket event, FULLY REPLACES on each save, last-write-wins, process-global) → _vault_fallback (vault MODEL_A_URL=external). So a stale runtime override from an OLD keys-modal save (a different device/browser, weeks old) OUTRANKS the vault's external default and silently staffs Cerebras. The first start got Cerebras → 404 every cycle → spun to cycle 23 → stopped. LESSON: do NOT trust the vault MODEL_A_URL=external default; verify/set the EFFECTIVE config (the last keys-modal save) before starting. Multiple browsers/devices each holding a keys modal is a live race — the operator had iPad (stale Cerebras) + laptop (correct external) configs; whichever saved LAST wins. There is NO diag route reporting live runtime_configs — confirm by behavioral probe (does a researcher_turn post, or does the console show a Cerebras call) and stop instantly if wrong.

## ERRORS THE SEAT MADE (logged honestly — same inference-as-fact class flagged all day)
- Asserted MODEL_A_URL=external (vault) would be the EFFECTIVE config without checking the runtime override. Cost a failed run.
- Asserted "nothing persisted" after the stop; the console showed "Session written to workspace database" — it wrote a correctly-labeled `stopped` row (status not laundered to complete). Corrected.
- Invented a "mystery process re-setting MAIN config at 20:59" rather than reading that "Model configuration saved" is the FIRST console line of a keys-modal save / session-begin; the events were the operator's own modal saves (6 total: 1 stale pre-session at 18:30, then operator's iPad+laptop saves). Operator's hint ("Model configuration saved is usually the first phrase as a session begins") corrected it.

## PUBLIC EXPOSURE FOUND + LOCKED (the priority pivot)
ontinuity.org (GitHub Pages, served from repo index.html) had a public "Begin Session" button (x2: hero + try-it) AND a footer "Live System" link, all wired directly to the unauthenticated MAIN engine (web-production-7eaf8). Live since April — it WAS the original manual session-starter before the rest was built. Anyone could start a session on MAIN, burn Cerebras credits, write to the corpus — and the operations_ledger does NOT capture web-UI socket events (save_api_keys / agent/start), only courier/box ops, so a stranger session would be UNLOGGED. Ledger audit confirmed: no unauthorized BOX-op activity, only one MAIN session today (the seat's stopped one). FIX (commit 7477ce5d): both Begin Session CTAs → disabled coming-soon spans, footer link neutralized; verified live (engine-links 3→0, coming-soon 0→3, GitHub Pages republished ~40s). RESIDUAL: the engine URL itself is still public + unauthed — the button is gone but the door isn't locked. That is the multi-tenancy/auth punch-list blocker; tonight's need (stop a family click) is handled.

## WORKER-HALF ORIENTATION (the seat read it this session — was a gap)
Read WORKER_MANUAL, WORKER_BOOT_PACKET, WORKER_QUICKBOOT in full. Confirmed: courier op allowlist is FLAT not seat-gated (a worker seat sees the same 16 ops), but the policy boundary is the CREDENTIAL — workers hold no github_token, so they read (read_repo incl. app.py)/reason/stage (write_file to box) but never commit/deploy. So Fix #2/#3 marked "needs VPS/db hands we lack" was WRONG: a worker CAN build+stage them (read_repo the code, write_file a candidate); only the commit+deploy half is control's. Quickboot snippet triggers injection-poison refusal (BOOTTUNE sweet-spot fix still unbuilt) — operator pastes the full packet per worker. No API spawn (cost) — operator hand-starts each worker.

## CDN-RECONCILIATION (the intended session objective — NOT yet run, the config trap blocked it)
The objective for the Researcher-seat session: reconcile agent_queue line ~606 (CDN KILLED / delete the raw-CDN path from read_repo) against WORKER_MANUAL (raw-CDN-cachebust fallback that grounded a real 216KB app.py read when API rate-limited on shared egress). The corpus CONFLICTS with itself; a blind delete could reintroduce the rate-limit blindspot. This is the live unresolved question waiting for the (re-attempted) session.

## CARRIED OPEN
- Researcher-seat session: re-run after confirming laptop external config is the LAST keys-modal save. Objective = CDN reconciliation.
- Engine-URL auth gating (multi-tenancy blocker) — the door behind the disabled button. Now urgent given the public site.
- web-UI socket events (save_api_keys, agent/start) not in operations_ledger — audit-spine gap for the public front door.
- Mini-corpus build (pipeline automation), close-ritual gate, KEYS-2-FIX unsigned — unchanged from earlier today.
