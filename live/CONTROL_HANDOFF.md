# CONTROL HANDOFF — current state + the single next action
# Updated 2026-06-15 (afternoon close) by control seat (claude.ai-chat:opus-4.8).
# Orient from the corpus, not from memory. Read this, then PUNCH_LIST.md + the queue head.

## STATE AT CLOSE
- Engine IDLE (running:false, cycle 0). Last deploy healthy (SKIPPED label = Railway dedup of an identical redeploy; engine live, 18-op allowlist serving). No half-finished deploy, no orphaned mailbox claim.
- Repo == box: box_ops.py reconciled via commit_self (1ff93529) — the repo had a STALE subprocess version of backup_db; the box ran the corrected python-sqlite3 version; close-ritual provenance check caught it and pushed the box's version to the repo. A fresh seat rebuilding from the repo now gets the working version.

## ⚠️ CREDENTIALS — READ BEFORE BOOTING
The operator was REVOKING the three exposed credentials at end of session 2026-06-15: DIAG_KEY, GitHub PAT, Railway project token. If that happened, the system is DARK — boot/ops/deploys will all fail until rotation. This is expected, not a breakage. Rotation (issue new keys + set in Railway vault + update LLaves) is a dedicated future session and is the likely FIRST action when the operator returns. Vault secrets (INTAKE token, mailbox key, provider keys) were NOT revoked (no evidence of vault-value exposure). The committed DB backup is independent of all these keys.

## WHAT SHIPPED THIS SESSION (all on the record, keyed to shas)
- Boot-packet permanence: CONTROL_QUICKBOOT_SNIPPET.md (e2267613, the fixed verbatim pointer — NEVER regenerate it; a decohering seat must not author the boot artifact) + CONTROL_QUICKBOOT.md rewrite (9c2edb0b) + hard-gate on five-doc orientation (d3999e66). Cold-tested clean.
- backup_db op (62c834a0 / app.py 308ea384, repo reconciled 1ff93529) + first DB backup committed to PRIVATE repo ontinuity-intake-data backups/ontinuity_dump.sql (cbfb6220). Repeatable: backup_db -> commit_file.
- Website: /papers.html live (959a85f5) + index.html logo fix & Papers tab (88a0304f). Operator made site + TikTok outreach comment public.
- Fabrication question grounded on the record: session 2026-06-14_22-19-08 shows the gate catching a fabricated completion-claim (Opus Researcher seat, C1 asserted-without-citation, challenged + close refused, real close cycle 5). Early-build fabrication examples are PRIOR-state; do not cite as current.

## THE SINGLE NEXT ACTION
If credentials were rotated/are available: the declared next build is the SHS-Wasserman client work (P0 = Katie's deterministic sanitizer/de-identifier, plain code no model, parameterized to her declared columns; spec in the PRIVATE repo projects/shs-wasserman/). It gates everything downstream.
If credentials are still revoked: the FIRST action is credential rotation (a dedicated session) — nothing live runs until then.
NEW operator-priority item now in the queue: the VERBOSITY GATE (draft off-screen, return only the consolidated contract-shaped answer) — operator named it a priority this session.
