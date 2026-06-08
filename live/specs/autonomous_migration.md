# CONSTITUTIONAL AMENDMENT + SPEC: Autonomous Schema Migration for the Researcher Seat
*Drafted June 8 2026 (operator-directed, deliberate, post-coffee). Product-defining: the Researcher seat must be able to evolve its own corpus schema autonomously, or multi-hour unattended runs are throttled by every schema discovery. Three human round-trips in 12h proved the throttle is real and recurring.*

## THE AMENDMENT (supersedes "all schema changes are operator's hands")
Schema changes split into TWO classes with different gates:
- **SAFE class — autonomous-eligible**: purely additive, reversible, idempotent, and non-destructive to existing data. Allowed operations ONLY: ADD COLUMN (nullable, no NOT NULL on populated tables), CREATE TABLE, CREATE INDEX, and backfills that write ONLY to newly-added columns or to NULL cells. These cannot corrupt or lose existing data. The seat may apply these autonomously when (a) operator class-authorization is active and (b) the migration passes the static safety screen and self-verification below.
- **DESTRUCTIVE/AMBIGUOUS class — always human**: DROP COLUMN/TABLE, DELETE, type changes, UPDATE touching existing non-null data, anything the screen cannot prove safe. Per-instance operator sign-off, every time, no exceptions. The seat escalates these; it never applies them.

The old blanket rule was miscalibrated: it gated reviewed-idempotent-additive changes the same as destructive ones. That conflation is the throttle being removed.

## THE MIGRATION RUNNER (keyed workspace endpoint: POST /apply_migration)
The seat does NOT get raw DB access. It gets a receipted, additive-only runner that refuses anything destructive. Inputs: migration script reference by repo COMMIT SHA (immutable, reviewed) + operator authorization token. Sequence:
1. **Backup, untouchable**: take a fresh timestamped backup of the corpus to a retained, append-only location (e.g. backups/ontinuity.db.PRE_<sha>_<ts>). Verify the backup (open it, snapshot row counts of every existing table). REFUSE to proceed if backup or verification fails. Backups are never overwritten, never deleted by the runner — retention/pruning is a separate human/policy decision. The runner only ever WRITES new backups and, on failure, READS the latest to restore.
2. **Static safety screen**: parse the migration; confirm every statement is in the SAFE allowlist. Any DROP/DELETE/type-change/existing-data UPDATE → REFUSE and escalate to operator as a constitutional point. This is the deterministic gate, not a judgment call.
3. **Apply** the migration (idempotent — duplicate-column etc. are the already-applied case).
4. **Self-verify**: run the migration's own assertions AND a post-check that every pre-existing table's row count matches the pre-snapshot and no existing column values mutated (additive-only invariant). 
5. **Rollback on failure**: if verification fails for any reason, AUTO-RESTORE from the backup taken in step 1, log a gate_violation+rollback receipt, escalate. The live corpus is never left half-migrated — this is the keystone that makes autonomous additive migration safe.
6. **Receipt on success**: write a migration receipt carrying the sha, the backup path, the operator token, the screen result, and the verification output. Restart/reload the endpoint schema as needed. The autonomous schema change is now as auditable as every other receipted action.

## APPROVAL MODEL (bench now, product later — same mechanism, different scope)
- **Bench (now)**: operator sets a standing class-authorization for the SAFE class. Once active, the seat applies any screen-passing additive migration without a per-migration human step. THIS is what unblocks overnight runs. Operator can revoke at any time.
- **Product (later)**: tenant-scoped. Each tenant's corpus, each tenant's authorization, each tenant's backups; the runner cannot cross tenants. The backup trail + the migration receipts ARE the auditability that makes autonomous schema evolution a trust feature rather than a liability — directly satisfies the abuse-resistance cluster's "corpus integrity" and "unstrippable provenance" requirements.

## WHAT THIS UNBLOCKS
Multi-hour unattended runs that discover a needed column mid-grind apply it themselves, additively, backed-up, verified, and receipted — and only stop for the operator on a genuinely destructive change. The third schema round-trip becomes the last manual one for the SAFE class.

## STAYS TRUE
Destructive changes remain fully human, every time. The seat proposes (commits reviewed script); the runner enforces the additive-only screen deterministically; the operator authorizes the class; the backup-and-rollback makes failure non-destructive. No raw DB access is ever granted to the seat.

## ASSUMED (untested design — grades when built)
That the static screen can reliably classify SAFE vs destructive (SQLite DDL is simple enough that this is plausible but must be museum-tested with destructive specimens it MUST refuse); that the additive-only post-check (existing row counts + value immutability) catches any screen miss; that backup+restore is atomic enough at corpus scale. Build it behind the same discipline as everything else: museum of must-refuse destructive specimens, acceptance that proves a real autonomous additive apply end-to-end, receipt.
