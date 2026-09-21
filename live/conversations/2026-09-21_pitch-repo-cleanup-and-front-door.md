# 2026-09-21 — Control-seat session: pitch repo cleanup, license, README, a front door for business owners

Form: condensed (operator rulings quoted verbatim; narration summarized). Participants: Patrick (operator); control seat claude.ai-chat:claude-fable-5.1. Seat session 8b42f299, contract project `pitch-repo-cleanup`. Boot: CONTROL_BOOT.md -> CONTROL_QUICKBOOT v3.1, bootstrap_gate oriented:true 7/7 (manual 25 == live 25; sessions 329, floor 307; MAIN and FARM idle; all five roles alive). No contention.

## Why this session happened
The operator is answering a job lead (an introduction to a business-network founder and a solution architect). The repo and the site are what those readers will open. The prior conversation's plan: move the foundational papers off the root, write a README an architect can read in five minutes, and put the four pillars and two stories on the landing page, all through the control seat so the work is itself a receipt.

## Rulings (verbatim) and what each produced
1. "Folder, not new repo. I say we keep anything linked right now and just clean up the other non-relevant items to a single folder for now... lite cleaning for now."
   -> Link audit first (every root file checked against all 19 site pages, app.py, box code, templates, and the rest of the repo). No site page or engine code referenced any paper. 23 files (21 .docx, the arXiv PDF, `ontinuity behavioral data.db`) moved byte-identical to `papers/` with a short papers/README.md. Commit 90ec391. Root 59 -> 36 files. Engine-written knowtext_*/erl_* files, all site pages, and engine files stayed at root.
2. "Let's get rid of the numbered duplicates in prompts."
   -> Ten superseded prompt versions moved byte-identical to `museum/prompts/` (the repo's convention for retired material; outright deletion left as the operator's call). prompts/ now holds exactly the eight files app.py loads. Commit e00a3c6.
3. "Let's add a license." then, after the seat laid out AGPL-3.0 / Apache-2.0 / source-available with the tradeoffs: "Let's use AGPL-3.0".
   -> LICENSE (canonical unmodified AGPL-3.0; GitHub detects it) + NOTICE (Copyright (C) 2026 Patrick Killebrew; license scoped to the software; papers, site content and the name reserved; commercial licensing available). Commit 5efffbd. The reservation paragraph in NOTICE was the seat's call, made in the reversible direction, and flagged to the operator as deletable.
4. "Update the README as to see fit."
   -> Root README rewritten: four pillars, architecture diagram, the two gates, where-to-look table, how an install is stood up, status with limits stated, license. Commit 766d8c9. It deliberately carries no session count and labels live/specs/ as mostly a proposal backlog.
5. "Let's make it a better front door about what Ontinuity is and how it helps connect business people with problems that they can't describe to a process that produces a software solution as the end result." Draft shown as a private preview; "That looks good for now." Then: "Buckyball is a side project and is not relevant here. It should not be a tab at the top either. Let's move its path to a link at the bottom of the main corpus page."
   -> index.html: new hero, new first section The Path (tell it / define it / plan it / build it, with a plain status line), the four pillars in business words, two stories (home care; control systems). The Bet onward unchanged; link and anchor diff showed nothing lost. Buckyball tab removed; corpus.html gained a closing "side project" note linking it. Commit fa3a94f. Verified on the live site after the Pages rebuild.

## Findings worth keeping
- The operator asked why citing "more than 300 sessions" feels like fluff. Read: 329 sessions in the DB, of which 185 carry randomized burn-in observations. It is an activity count, mostly unattended test runs; it answers "how much" when the reader asks "so what". Ruling-in-effect: outcomes, not counts, in pitch material.
- IP framing given to the operator (not legal advice): contract language on pre-existing IP protects most; copyright in AI-written code is thin under the Copyright Office's human-authorship position (cert denied in Thaler v. Perlmutter, 2026-03-02), so the human-authored corpus, specs and arrangement are the solid part; ideas are only patentable, and the repo's first public commit was 2026-04-10, so the US one-year grace period ends 2026-04-10 + 1y; the name has common-law trademark rights from use.
- The four-stage pipeline spec still reads Stage 1 LIVE / Stages 2-4 DESIGN. The new landing page says so in plain words ("run end to end once... as supervised working sessions. It is not yet a push-button product"). If the spec's status is stale, fix the spec and the page together.

## Deviations, stated
- The boot text says to start a control seat in a fresh conversation. This seat booted inside the conversation that had been doing the pitch writing, on the operator's go-ahead. The boot itself ran cold from the packet and the gate; the context carried in was the pitch framing, not system state.
- The five work commits went through the authenticated GitHub git-trees API (manual: COMMITTING, multi-file atomic), not write_file + commit_file, because the courier's file ops are text-only and the moves were binary (.docx/.pdf/.db) and needed to be atomic. The contract, orient and gate rows are in the ledger; the commits carry the contract id and seat session in their messages. The close artifacts (this record, the fold, the punch list, the handoff) go through write_file + commit_file with the seat key.

## Left open (operator said leave for now)
intake11.html, extract_to_db.py and the root copy of intake_system_prompt.txt (unreferenced, not moved); two dated inventories (ONTINUITY_COVERAGE_CHECKLIST.txt, ONTINUITY_MASTER_SYSTEM_MAP.md) still list the old root paths of the moved files, as records of their date; the install runbook is private, so the README describes it without a link.

Cross-refs: commits 90ec391, e00a3c6, 5efffbd, 766d8c9, fa3a94f; contract items papers-move, prompts-dups, license-agpl, readme, front-door (all DONE); receipt at GET /agent/handoff.
