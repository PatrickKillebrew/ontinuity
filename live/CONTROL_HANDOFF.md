# CONTROL HANDOFF — current state + the single next action
# Updated 2026-06-20 (~09:25 CT, migration close) by control seat (claude.ai-chat:opus-4.8).
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the queue head.
# MIGRATION NOTE: prior seat ran ~1.5 days and was gracefully decohering by close (see DECOHERENCE
# NOTE below). Operator called the migration — feature, not failure. State is clean and folded.

## STATE AT CLOSE
- Engine/box healthy. Box hands LIVE (courier 18-op allowlist confirmed by probe this shift).
- Laptop seat (laptop_seat.py) was started by the operator this shift and is LIVE (probe returned
  fresh result 2026-06-20T13:01Z). NOTE: it dies on laptop sleep — operator must restart it; there
  is NO hands-free autostart (verified against the commit log this shift — none was ever built,
  despite a seat's earlier muddled claim). The laptop hands themselves are real; only the ignition
  is operator-side.
- VPS box (ubuntu-2gb-ash-1, 2GB): gunicorn OOM-kills a worker ~once/day and self-recovers. NOT
  urgent — 2 events in 26h, auto-heals. A free swap-file cushion is a someday-nicety, not a task.
  Do NOT treat as an emergency (prior seat over-dramatized it; the data says it's fine).
- No half-finished deploy, no orphaned mailbox claim, no gate event this shift (public .html only).

## WHAT SHIPPED THIS SHIFT (keyed to shas; all live on ontinuity.org)
- The LIVING MARK logo: animated lensed-hex (concentric hex-pairs, axis-spin, directional shine,
  coherence/decoherence cycle KEPT per operator, self-feeding particles, pulsing core, gravitational-
  lens canvas grid phase-aligned to the page 48px grid, sinking behind the mark, pulsing). LOCKED.
- THE FULL NINE-PAPER CORPUS, each on the locked slate template carrying the mark, cross-linked:
  cognitive-ecology, artificialware, dynacology, synthesis (front-door + navigable full doc w/ jump
  index), tetraform, knowtext, teaching-leash, growth-vector, session-record. All HTTP 200.
- Homepage remodel: living mark in hero (two-col, +15% for balance) + nav + footer marks.
- corpus.html: tiered reading-guide index (Foundation/Implementation/Synthesis/Evidence) with the
  two-era note (April foundation vs the matured gate/contract/seat system). All 9 papers repointed
  "see all papers" -> /corpus.html.
- live/STATE_OF_ONTINUITY.md (2f392e3a): the first grounded current-system inventory — the source
  material for the documentation arc below.
- Conversation record (d5bab66d) + queue fold (1f29ec27) for the June 19 site/inventory work.

## THE PIPELINE (operator-gated; the documentation arc, ranked)
1. EXPANDED SYNTHESIS PAPER — the keystone a reader like Rocket lands on. Built by EXPANDING THE
   TWO HARNESS NOTES on papers.html + STATE_OF_ONTINUITY.md. Opens with reliability-from-the-harness,
   the two-party gate, grounding-from-record, the team of seats, the 319-session record, the
   fabrication-catch as the un-dismissible artifact. April corpus reframed as foundation.
   GROUND FIRST: re-verify the live numbers (319 sessions, 5 models) before drafting — they move.
2. HOMEPAGE REMODEL #2 — gut the April content (operator disowns the 48hr-origin romance + the stale
   Sonnet-placeholder metrics), point the front door at the new synthesis. Visual shell stays.
   (corpus.html index was item 3 — DONE this shift.)

## OTHER OPEN ITEMS (operator-raised, not yet built)
- THE SHELL OP (operator wants this — "make maintenance something Claude does without involving me").
  Design: a Claude-Code-style pattern-gated `shell` box op — ONE shell op, every command checked
  against a deny-list (rm -rf, dd, mkfs, key/vault reads, curl|bash) THEN an allow-list (free, df,
  systemctl status/restart <named units>, cat configs, swap setup), deny>allow first-match, logged
  to operations_ledger, diag-gated. Real box-admin hands while keeping the firebreak that makes the
  shared-diag-key model survivable. Installable hands-free (write_file + restart_workspace). It WIDENS
  what the diag key can do -> author + two-party review + gated deploy. The deny-list IS the safety;
  design it against the corpus's known risks (the diag-key soft spot) BEFORE deploying. Operator has
  energy for real builds — treat as a primary item, not a someday.
- VERBOSITY GATE (carried from 2026-06-15): draft off-screen, return only the consolidated answer.
- SHS-Wasserman client work (P0 = Katie's deterministic sanitizer): the declared client build when
  the operator turns to revenue work; spec in PRIVATE repo projects/shs-wasserman/.
- Higgsfield MCP: OUT (costs credits). Recorded so it stops recurring.

## iPad KEYBOARD (portable/WebRTC) — paused at a known blocker
- LAN v23 CONFIRMED (same-Wi-Fi). WebRTC /kb route live; aiortc 1.14.0 on the laptop; core proven.
- BLOCKER: café client isolation -> ICE FAILED. Needs TURN. coturn-on-the-box ruled out this shift
  (box ops can't apt-install; 2GB box; not the place). PATH: free-tier managed TURN (Metered 50GB
  free, no card) to PROVE it, OR self-host coturn later as the Rocket-demo step. Corpus:
  projects/ipad-keyboard/mini_corpus.md (private) + live/tools/ipad_keyboard_CORPUS.md. Per corpus:
  prove end-to-end on a FRIENDLY network first, then TURN for locked-down ones.

## THE SINGLE NEXT ACTION
Operator has energy and wants real build work. Two live primaries, operator's pick:
(a) THE EXPANDED SYNTHESIS PAPER (item 1) — ground the live numbers, then draft from the harness
    notes + STATE_OF_ONTINUITY.md. The keystone of the current-system public documentation.
(b) THE SHELL OP — design the deny/allow lists against the corpus, review, gated deploy; then box
    maintenance is hands-held, no operator involvement next time.
Confirm which with the operator on boot.

## DECOHERENCE NOTE (for the fresh seat — what you're inheriting)
The prior seat did strong work (the whole corpus site) but by the last ~quarter of the shift showed
the classic drift: over-dramatized a non-urgent box OOM, briefly muddled whether laptop hands existed
(they do), and got the time-of-day wrong. It did NOT fabricate — it grounded each claim against the
commit log and corrected on the record when the operator pushed. The operator absorbed the decoherence
cost for a day to preserve context. You are fresh: re-ground from the five docs, trust the shas over
any narrative, and you'll be sharper than the seat that wrote this. Nothing is half-built; folded clean.
