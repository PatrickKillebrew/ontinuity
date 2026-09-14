# 2026-09-13 — Fable takes the Control seat; the incomplete rollback is found by the boot and completed

FORM: condensed decision-record per CONVENTION.md. REDACTION: clean — no keys, tokens, or IPs.
PARTICIPANTS: Patrick (operator); claude.ai-chat:claude-fable-5.1 (Control; diag-key courier hands from the sandbox).
LINEAGE: commits `8ef1b91` (rollback reconciliation) and `8e2a7fc` (bootstrap_gate wrapper fix); box installs of
box_ops.py, seat_mailbox.py, live/bootstrap/gate.py via write_file + restart_workspace.

## ARC
The prior seat (Opus) handed off with the engine recovered to `5640170` (pre-GPT + B5-P) and the manual/gate count
rolled back. Fable booted the proper way (probe → five read groups → gate). The boot itself was the audit:
the packet, handoff, paradigm, rubric, punch list, and worker docs on main were still the B1/B-block text; the
gate's CHECK 2 was silently reading a 2026-09-09 B1 fold's NEXT (it only parsed `## FOLD` headers) while reporting
oriented:true; and the BOX was still running the B1 versions of box_ops.py and seat_mailbox.py. The rollback of
code without docs and box had produced a system that boots green onto a stale plan. Operator direction: "restore
the system to its before-GPT/B1 state"; restore real pre-GPT text from GitHub rather than banner it; keep only
genuine bug fixes and security hardening.

## RULINGS (operator)
- Banners on stale docs are noise; restore the documents that existed before the changes from GitHub, and where a
  restored document carries a known defect, fix the text for the next model rather than restore the defect.
- Everything GPT did after 2026-09-03 rolls back EXCEPT bug fixes and security hardening proven independent of B1.
- The B1 direction is stored as a museum piece with its files accessible, not erased.

## WHAT WAS DONE (per-file dispositions in the commit; summary)
- RESTORED from `9a7eac2a` (pre-GPT): THE_PARADIGM, OPERATING_RUBRIC, CONTROL_QUICKBOOT_SNIPPET, CONTROL_HANDOFF
  (state block rewritten to current truth), PUNCH_LIST (base + DONE entries for the KEPT work), verified_bootstrap_gate
  spec (CHECK 2 + count wording), live/control_loop.py, templates/index.html, live/box/laptop_seat.py,
  live/box/box_ops.py, live/box/seat_mailbox.py.
- KEPT the Sept-5 currency fixes (19 ops, X-Diag-Key header) in CONTROL_QUICKBOOT + WORKER docs; B-block references removed.
- KEPT GPT hardening with no B1 dependency: secret-literal removals (push_to_github.py, shepherd.py — reverting would
  have re-committed secrets), header-key + no-redirect openers (shepherd_alert, governor_relay/routes, burnin_resident),
  model_client allow_redirects=False, live/box/file_server.py, the reconciled 19-op gate.
- MUSEUM: B1 code/specs/manifests/tests/tools/evidence → museum/b1/; BOARD + COMPLETION_PLAN → museum/b-blocks/; README.
- GATE: CHECK 2 now parses `## CURRENT-STATE TOUCH POINT` folds with inline/bulleted `**NEXT` (the manual's and the
  pre-GPT spec's convention); OPERATING_MANUAL close-ritual item 3 documents the required fold shape.
- BOX: box_ops.py (pre-GPT) + seat_mailbox.py (pre-GPT) + gate.py (patched) installed, restarted, blobs verified
  equal to the repo. trusted_deploy.py remains on disk, unreferenced (no delete op exists) — recorded, not hidden.

## THE DEFECT THE REVERT REINTRODUCED, AND ITS FIX (specimen)
Reverting box_ops.py to pre-GPT bytes brought back a pre-GPT defect the 2026-09-05 review had named: the box's
bootstrap_gate wrapper overrode the gate's canonical op count with a stale module constant (15) or ANY caller-supplied
number. First post-install gate run: `MANUAL: manual states 19; canonical = 15` → NOT ORIENTED. Fixed as a bounded
edit on the pre-GPT base (commit `8e2a7fc`): the gate module owns its count; the wrapper no longer overrides; a
caller-supplied canonical_op_count is refused with HTTP 400 and ledgered. This is the first "B1 hardening salvage"
item, applied without restoring any B1 module. LESSON: a revert restores old defects too — verify after every install.

## EVIDENCE — before / after (the gate is the proof)
- BEFORE (boot, main `410d69c`, box B1): oriented:true BUT CHECK 2 = "Regenerate both manifests, run the complete
  byte-preserving verifier…" (the 2026-09-09 B1 fold) — a green boot onto a stale plan.
- AFTER (main `8e2a7fc`, box reconciled): oriented:true; MANUAL 19=19 (gate-owned); CHECK 2 = "Finish the read-only
  mapping audit … then execute the private-repo PROVISIONING_RUNBOOK Phase 2"; CORPUS 328≥307; HANDS mailbox_peek ok;
  ENGINE MAIN/FARM idle; MECHANICS 4/4 at 1.0. Override attempt (canonical_op_count=15) → HTTP 400 refused.
- Hands verified through the courier after both restarts: __probe__ (19 ops), mailbox_peek, read_file, read_repo.

## ERRATA / FAILURES DOCUMENTED (kept, not scrubbed)
- Fable's first patch of the wrapper used the wrong `_ledger_finish` call shape; caught by reading the function
  signature before install, fixed before shipping. Small, but the class is "write from recall instead of reading the
  code" — the same class as everything else in this record.
- The prior seat's 2026-09-12 close judged "box files match repo — no rollback needed" because the pre-GPT engine ran
  against the B1 box files. It worked, but it was incongruent, and it hid the wrapper/gate interaction. Recorded so the
  "it works, so it's fine" shortcut is recognizable next time.

## STATE LEFT
MAIN `5640170`, FARM `f9696c49`, box congruent (pre-GPT box_ops/seat_mailbox; hardened file_server/gate/shepherd_alert;
B5-P db/workspace), 19-op diag-key hands, gate oriented:true reading the current next action, 328 sessions. Not touched:
ODS files in the repo (separate cleanup), FARM engine, inert trusted_deploy.py on the box.

## CROSS-REFERENCE
Commits `8ef1b91`, `8e2a7fc`. Fold: agent_queue.md "CURRENT-STATE TOUCH POINT — 2026-09-13". Museum: museum/README.md.
Salvage list: PUNCH_LIST.md OPEN/HIGH "B1 hardening salvage". Maps: live/ONTINUITY_MASTER_SYSTEM_MAP.md §10 (updated).
