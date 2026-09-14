# 2026-09-13 (session C) — Activating per-project memory (Projenius/ERL scoping) (control seat, Fable)

Session type: control-seat build. FORM: condensed decision-record per CONVENTION.md — rulings verbatim,
narration summarized. REDACTION: clean. LINEAGE: operator (Patrick); agent claude.ai-chat:claude-fable-5.1.
Follows 2026-09-13b. DEPLOY: documented single-seat, operator-authorized ("You can do a documented single seat
deploy... Any changes you make can be rolled back").

## WHAT SHIPPED
- Per-project memory scoping ACTIVATED (was dormant/half-wired). Commits 34de6a6 (engine+box), e88a2c5 +
  61b0968 (docs). Engine deployed to app.py blob e46d6264; new_project live in the 20-op allowlist.
- STEP A [keystone] — build_session_payload now sends the session's own project_id/branch (fallback to the
  WORKSPACE_PROJECT global), so DB rows scope per-project like the file layer already did. Was: sent the
  global for every session.
- STEP B — the ERL is no longer write-only: loaded at session start + injected into the Researcher context,
  and fed to Projenius ORIENT with open questions (ORIENT was starved — Knowtext only). Added helper
  get_open_questions_context. This connects the cross-session "start further along than cold" memory.
- STEP C/D — new_project box op (creates projects + main-branch rows AND initializes empty per-project
  Knowtext/ERL files, keyed on the project name-slug to match _scope_slug); installed box-side, TESTED against
  the box before the allowlist landed; added to OP_ALLOWED; seed_tenant marked DEPRECATED.
- STEP E — docs: OPERATING_MANUAL PER-PROJECT WORK section (the conversational trigger for non-tech users) +
  corrected the false seed_tenant claim; CONTROL_QUICKBOOT packet updated (contract-currency 4b).
- STEP F — END-TO-END TEST passed: new_project created the DB rows + both corpus files, keyed consistently
  (file slug == DB name), idempotent (re-call created=false, same project_id). All fixes confirmed in the
  deployed code. Test artifacts tombstoned (no delete op exists; inert ZZ- rows remain).

## RULINGS (operator, verbatim intent)
- On the build: "Your plan looks good. Double check it again... Proceed without stopping for me." + "You can
  replace seed_tenant if you feel that's the best way to build. I'm not attached to any single component."
- On priorities: "I'm sure there's lots of things in the system that could be made better, but we can deal
  with those after we ship the first packaged working product."
- On auditability (a design principle to keep in mind): "Ontinuity is supposed to be auditable and walkable,
  so let's make sure we're keeping that in mind as we work." → every change documented in the record +
  rollback-able; the seam audit itself demonstrated the walkable-corpus differentiator.
- The vision this serves (from 2026-09-13b, the product shape): Cornel (head safety manager, AZZ's 64
  galvanizing plants) works a "matter" per topic — a training program, an incident-report KB, a plant's ops —
  each an accumulating corpus that never goes stale; resumes after days without re-establishing context; a
  completed matter's template lets the next start further along.

## THE DESIGN / FINDINGS (settled against source, verified before building)
- The per-project scoping was ~80% built and DORMANT (Easter-egg wiring), not missing: file paths, structural
  isolation, has_own_project close branch, /agent/start accepting project_id — all present. The 281 "isolated"
  historical sessions were start_fresh/no-project verification runs sealed BY DESIGN (Deploy 26 lineage
  isolation), confirming the operator's read that the wiring was laid in for later.
- SEAM AUDIT (before building) found the file layer writes per-project but the READ side was disconnected: DB
  scoping used the global; the ERL was write-only; ORIENT was starved. Fixed all three. Building new_project
  alone (without these) would have created projects that write files right but DB rows wrong and never read
  their own ERL — the "usually works" failure that undermines the reconstruction differentiator.
- seed_tenant RECONSTRUCTED as never-built: in OP_ALLOWED but zero route defs repo-wide, live 404, zero git
  commits ever touching it; the manual's hands-free claim was wrong; Katie was seeded by the standalone script
  on the box. new_project supersedes it. (This reconstruction — catching a wrong doc via code+git+live cross-
  reference — is the auditable/walkable corpus working, the product's differentiator vs generic AI memory.)

## THE FAILURE (recorded, not hidden)
- Two self-caught errors during the build, both the same class (referencing something without verifying it
  exists): (1) I referenced get_open_questions_context which didn't exist — caught by a syntax/existence check
  before deploy, added the helper. (2) The CONTROL_QUICKBOOT anchor was `<name>` not `<n>`; my first doc edit
  silently no-op'd — caught by checking what actually committed, re-applied. Both caught by verify-before-ship
  discipline, neither shipped broken. The lesson holds: read/verify the actual thing before asserting it.

## STATE LEFT
main = 61b0968. Engine on e46d6264 (5640170 base + per-project activation), 20-op allowlist incl new_project,
diag-key hands work, 328 sessions intact, box congruent (box_ops.py has op_new_project). All changes additive/
fallback-safe: unscoped/legacy sessions behave exactly as before. Per-project memory works end-to-end (proven).
Not done (deferred, noted): a delete/cleanup op for test rows; branching within a project (research-program
depth, not needed for the BIL); tag-based cross-project auto-retrieval (operator-directed works now).

## NEXT
The per-project memory activation is complete and proven. Remaining toward packaging: (1) the conversational
trigger is DOCUMENTED (manual + packet) but should be exercised live (start a real matter, resume it, confirm
the ERL/Knowtext bring back context) as the acceptance test that it matches-or-beats a hand fold; (2) resume
the PROVISIONING_RUNBOOK Phase 2 (stand up the BIL's own instance) — now with working per-project memory to
demo. Then the two-tier methodology/template layer for cross-project leverage (the "start further along" magic).

CROSS-REF: commits 34de6a6, e88a2c5, 61b0968; deploy app.py blob e46d6264; ONTINUITY_TOTAL_INDEX.md (the seam
audit + Easter-egg inventory); OPERATING_MANUAL PER-PROJECT WORK; the-package/PROVISIONING_RUNBOOK (Phase 2).
