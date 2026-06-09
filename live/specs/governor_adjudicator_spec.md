# Design Spec — Governor Adjudicator Workspace

**Status: DESIGN ONLY. No build, no deploy. Operator reviews before any implementation. Read-only investigation basis.**

## Purpose
The operator's review backlog is the system's throughput bottleneck: proposals sit in `live/fixes/`, app.py commits sit awaiting a sign-off deploy, and VPS-hands items (migrations, backfills, endpoint changes) sit waiting. The existing Governor (`live/governor/governor.html`) is a read-only monitor — Instance Health, Burn-in cycles, Outcome Ledger, fetched from `/governor/data` behind an X-API-Key gate. This spec extends it into an **action surface**: one organized queue of everything awaiting the operator, each item actionable, each action recorded as durable provenance (Spec 2).

## Core principle — the gate is TIERED BY RISK
The sign-off gate exists to protect **live mutation**, not to encumber routine work. Every pending item is classified into a risk tier; handling scales to the tier. This is the same SAFE-class logic as the additive-schema-migration amendment: additive/reversible/validated changes are cheap to accept; destructive/irreversible live mutations get full ceremony.

| Tier | Definition | Examples | Handling |
|------|-----------|----------|----------|
| **SAFE** | Additive **and** reversible **and** (no live-behavior change **or** corpus-validated). Idempotent. | `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN`, dead-file deletion (git-revertable), proposal/doc commits, repo-ledger writes | Auto-logged provenance; one-click "acknowledge", or autonomous under the schema-migration amendment. No per-instance ceremony. |
| **REVIEW** | Engine/code change that alters behavior but is reversible by redeploy **and** validated (unit/corpus). | F.3 cmd-ref filter, phantom-row guard, certified-close gate, Challenger-death gate | Single operator sign-off (one confirmation + basis). Provenance recorded. Then deploy. |
| **RISK** | Destructive or hard-to-reverse **live mutation**. | VPS schema DROP / data-loss migration, vault/secret ops, irreversible data writes, changes to the adversarial guarantee, anything touching live session data | Full **per-instance** sign-off (MAIN and FARM separately), typed confirmation + basis, full provenance. |

Classifier derives the **proposed** tier from the item descriptor (files touched, change type, reversibility, validation status). The operator may **escalate** a tier but never silently de-escalate. Tier is shown on every queue item with its rationale.

## Data sources (read)
A new `/governor/queue` route (auth_required, GET) assembles the pending queue from:
1. **Proposals awaiting review** — `live/fixes/*.md` and `live/specs/*.md` via GitHub API. Parse the `Status:` line and any `risk-tier`/`Operator action` block; an item is "pending review" until a matching sign-off provenance record exists (Spec 2).
2. **Commits awaiting sign-off deploy** — repo commits to watched paths (app.py) with an `Assisted-by:` trailer and **no** matching deploy-sign-off provenance, AND whose SHA differs from the instance's running SHA. Surfaces the deploy gap.
3. **VPS-hands items** — proposals whose `Operator action` names db.py/endpoint/migration/backfill steps; tracked until a sign-off marks them applied.
4. **Deploy state** — per instance (MAIN/FARM): running commit SHA (from each engine's `/diag/engine`, extended to report `RAILWAY_GIT_COMMIT_SHA`) vs repo HEAD. The gap is the "undeployed" set.

Each queue item: `{id, source, title, file/sha, proposed_tier, tier_rationale, status, basis_ref, instances_relevant}`.

## Actions (write, provenance-recorded)
A new `/governor/signoff` route (auth_required, POST) records an operator decision and emits a provenance record (Spec 2). Action types:
- **acknowledge** (SAFE) — records that the operator saw/accepted an additive item. No deploy ceremony.
- **approve-review** (REVIEW) — records sign-off for a reversible validated change; marks the commit deploy-eligible.
- **sign-deploy** (REVIEW/RISK) — records a per-instance deploy sign-off (commit SHA + instance). For RISK, requires a typed confirmation token and a basis string.
- **mark-applied** (VPS-hands) — records that a db.py/migration/backfill step was applied on the VPS, with the instance and a result note.

The panel does **not** itself push Railway deploys by default (the operator owns the deploy action via dashboard/GraphQL); it records the human sign-off that the self-enforcing gate then honors. **Open question O1**: optionally allow the panel to trigger the Railway deploy via the project token for REVIEW-tier items once signed — convenience vs. keeping deploy a deliberate separate act.

## UI (fits the existing Governor)
Add one panel, **Adjudication Queue**, below the existing monitor panels, same dark aesthetic and X-API-Key session gate:
- Grouped by tier (SAFE / REVIEW / RISK), each item a row: title, tier badge (color-coded: SAFE green, REVIEW amber, RISK red), source link (to the proposal/commit), status, and a tier-appropriate action control (acknowledge / approve / sign-deploy-per-instance / mark-applied).
- A **Deploy State** strip: MAIN and FARM each showing running SHA vs HEAD and the count of undeployed commits, so the gap is always visible.
- RISK actions expand to a confirmation sub-panel (typed token + basis field) — friction is intentional and proportional.
- Every completed action moves the item to a collapsed "Recently signed" list with its provenance id.

## What this drains
- Proposals → one click to record review/approval, clearing the `live/fixes/` backlog visibly.
- Undeployed commits → per-instance sign-deploy with provenance, so the gate permits the deploy and the gap closes.
- VPS items → mark-applied closes them with a durable record.
- SAFE items stop consuming operator attention at all (auto/one-click), which is most of the routine volume.

## Open questions for operator
- **O1** (above): should the panel trigger Railway deploys for signed REVIEW items, or only record sign-off?
- **O2**: SAFE-tier autonomy — should SAFE items be auto-acknowledged (no operator click) under the schema-migration amendment, or always require a one-click ack for visibility?
- **O3**: where the queue's "pending vs done" truth lives — derived purely from provenance records (Spec 2) each load, or a small cached index? Derived is simpler and stateless; recommend derived.
- **O4**: auth — reuse the single Governor X-API-Key, or introduce an operator identity (key fingerprint) so provenance records a distinct "who"? Spec 2 assumes at least a key fingerprint.
- **O5**: should REVIEW-tier require the basis string too, or only RISK? (Recommend: RISK requires typed token + basis; REVIEW requires basis only.)
