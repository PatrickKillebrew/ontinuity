# Design Spec — Autonomous Migration ↔ Provenance Alignment (addendum)

**Status: DESIGN ONLY. Addendum to live/specs/autonomous_migration.md, aligning it with the approved sign-off provenance (8aa730c4), gate v2 (97682d2b), and Governor (65214f3a) rulings. No build, no deploy. Does not rewrite the approved migration spec — it pins the integration points the new rulings create.**

## Why this addendum
`autonomous_migration.md` predates the provenance ledger. It specifies a standalone **migration receipt** (sha, backup path, *operator token*, screen result, verification output) and references an *operator token* — the superseded token-in-trailer model. Left as-is, SAFE-class autonomous migrations would write a separate receipt the gate and Governor cannot see, and would carry a token rather than a provenance fingerprint. Three small alignments make the migration runner consistent with the one auditable surface.

## Alignment 1 — the migration runner IS the canonical SAFE/RISK boundary
The runner's static screen already splits exactly along the tiering:
- **Additive-allowlist (CREATE TABLE IF NOT EXISTS, ADD COLUMN, additive index)** → **SAFE tier**. This is the one place where true no-human autonomy is in scope (per the ruling: autonomous SAFE is scoped to the schema-migration class only). Applied by the runner: backup → screen → idempotent apply → self-verify → auto-rollback-on-failure → record.
- **DESTRUCTIVE/AMBIGUOUS (DROP, DELETE, data-loss ALTER, type change, anything the screen cannot prove safe)** → **RISK tier**. Per-instance human sign-off, every time; the runner refuses and escalates, never applies.

So the gate v2 and Governor can treat "the schema-migration class" concretely: SAFE = what the additive screen passes; RISK = what it refuses. No separate tier vocabulary.

## Alignment 2 — replace the standalone receipt with a provenance-ledger record
On a successful autonomous SAFE migration, the runner writes a record into `live/signoffs/ledger.jsonl` (source of truth; DB deferred) instead of a separate receipt:
```json
{
  "signoff_id": "uuid",
  "ts": "ISO8601 UTC",
  "operator": "autonomous-SAFE",          // sentinel — the scoped no-human case, per ruling
  "action": "mark-applied",
  "risk_tier": "SAFE",
  "target_kind": "migration",
  "commit_sha": "<migration script repo SHA>",
  "instance": "main | farm",
  "proposal_ref": "<migration script path>",
  "basis": "additive screen: <screen result>; verify: <post-check result>; backup: <backup path>",
  "confirmation": null,
  "prev_hash": "<chain>"
}
```
The screen result, verification output, and backup path that the original receipt carried now live in `basis` (and the file_server `audit()` mirror keeps the full local copy). The migration becomes "as auditable as every other receipted action" — and now in the *same* ledger the gate and Governor already read, so an autonomous SAFE migration appears in the Governor's "Recently signed" list automatically.

A **DESTRUCTIVE** migration never reaches this path: it escalates and, if the operator chooses to apply it, produces a per-instance `action="sign-deploy"`/`mark-applied`, `risk_tier="RISK"`, human-fingerprint record with `basis` and `confirmation` required.

## Alignment 3 — drop the "operator token" in favor of the fingerprint model
The original "operator authorization token" input is replaced by the provenance model: a SAFE migration needs no human token (it is the scoped-autonomy case, recorded under the `autonomous-SAFE` sentinel). A RISK migration needs an operator decision recorded through the Governor (key fingerprint + typed confirmation), not a token string in a commit. This removes the last forgeable-string dependency and unifies authorization on the ledger.

## Failure path stays as specified
Auto-rollback-on-verification-failure is unchanged and remains the keystone. On rollback, the runner writes a record with `action="mark-applied"`, `basis` noting the rollback + reason, so even a failed-and-rolled-back autonomous migration is durably visible (honest-failure semantics), not silent.

## Net effect
One ledger, one tier vocabulary, no tokens, no separate receipt format. The gate (v2) verifies deploys against the same ledger the migration runner writes to; the Governor surfaces SAFE autonomous migrations and RISK escalations side by side; the additive screen is the concrete definition of the SAFE class the whole sign-off system references.

## Open questions for operator
- **A1**: the `autonomous-SAFE` sentinel `operator` value — acceptable as provenance for a no-human SAFE migration (ruling permits autonomy scoped to this class), or should even SAFE migrations record the operator key fingerprint that armed the runner, so there is always a human root of authority? (Recommend: record the fingerprint of the operator who enabled the runner once, plus the `autonomous-SAFE` action marker — a human root, autonomous per-event.)
- **A2**: should the migration runner write the ledger directly, or hand the record to the file_server (which owns ledger writes per provenance-spec O10) so there is a single writer? (Recommend: single writer = file_server.)
