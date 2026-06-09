# Design Spec — Human Sign-off Provenance

**Status: DESIGN ONLY. No build, no deploy. Operator reviews before implementation. Complements the self-enforcing deploy sign-off gate and the Governor Adjudicator workspace (Spec 1).**

## Problem
`Operator-Signoff:` is a static string in a commit message. It records nothing about who signed, when, against which commit, at what risk tier, or on what basis — and a string in a message can be written by anyone/anything that commits. There is no queryable record and nothing the self-enforcing gate can verify beyond "the substring is present." This designs a durable, queryable, tamper-evident provenance record for every operator decision.

## Record schema
One JSON object per line, append-only, in a git-committed ledger `live/signoffs/ledger.jsonl`:
```json
{
  "signoff_id": "uuid",
  "ts": "ISO8601 UTC",
  "operator": "key-fingerprint (sha256(api_key)[:12]) — WHO, without storing the key",
  "action": "acknowledge | approve-review | sign-deploy | mark-applied",
  "risk_tier": "SAFE | REVIEW | RISK",
  "target_kind": "proposal | commit | migration | backfill",
  "commit_sha": "full SHA for commit/deploy actions, else null",
  "instance": "main | farm | both | null",
  "proposal_ref": "live/fixes/xxx.md | live/specs/xxx.md | null",
  "basis": "free-text reason — REQUIRED for RISK, recommended for REVIEW",
  "confirmation": "for RISK: sha256 of the typed-back token (proof of deliberate act), else null",
  "prev_hash": "sha256 of the previous ledger line — append-only integrity chain"
}
```

## Storage — three layers, one source of truth
1. **Git ledger** (`live/signoffs/ledger.jsonl`) — the authoritative, durable, queryable record. Git-durable like Knowtext provenance; readable by the self-enforcing gate via the GitHub API it already uses. The `prev_hash` chain makes the append-only ledger tamper-evident (a rewritten line breaks the chain).
2. **file_server `audit()`** — the existing append-only JSONL audit log already records every write/command; a sign-off action also calls `audit("signoff", ..., extra=record)` so the VPS has an independent local copy (defense in depth; detects a ledger that diverges from what the box saw).
3. **Optional workspace DB mirror** — a `signoffs` table mirroring the ledger for fast SQL queries from the diag endpoint. **Open question O6**: needed, or is the JSONL ledger enough (parse on read)? For current volume the ledger alone is enough; recommend deferring the DB table until query volume warrants it.

## How the self-enforcing gate uses it (upgrade)
The gate proposal currently checks the commit **message** for the trailer. This upgrades it to verify a **provenance record**:
- At startup the gate reads its running `RAILWAY_GIT_COMMIT_SHA`, fetches `live/signoffs/ledger.jsonl`, and looks for a `sign-deploy` record matching `commit_sha` **and** this `instance` (main/farm).
- If the running commit touched app.py and **no** matching `sign-deploy` record exists → `PRODUCTION_LOCKED`. The trailer string becomes a convenience pointer, not the authority.
- Fails safe exactly as before: missing SHA, API error, or non-app.py commit → unlocked. The chain check is advisory at startup (a broken chain is surfaced loudly, not a hard lock, to avoid bricking on a malformed historical line).

This closes the forgeability gap: a deploy is permitted only when a real operator sign-off — through the Governor, with their key fingerprint, at the recorded risk tier — exists for that exact commit and instance.

## Tier-conditioned required fields
- **SAFE**: `action=acknowledge`, no `basis`/`confirmation` required; may be auto-generated under the schema-migration amendment (operator key fingerprint = "autonomous-SAFE" sentinel if no human click — **Open question O7**: is an autonomous SAFE acknowledgment acceptable provenance, or must SAFE still carry a human fingerprint?).
- **REVIEW**: `basis` recommended; single `approve-review` then `sign-deploy` per the relevant instance(s).
- **RISK**: `basis` REQUIRED, `confirmation` REQUIRED (hash of typed token), `sign-deploy` recorded **per instance** (separate records for main and farm).

## Query surface
- "Is commit X signed for instance Y?" → scan ledger for `sign-deploy` with matching `commit_sha`+`instance`. (Gate + Governer deploy-state both use this.)
- "What has the operator signed, when, at what tier?" → the ledger is the audit trail; the Governor "Recently signed" list and any future report read it directly.
- Integrity check → walk `prev_hash` chain; a break flags tampering or a malformed append.

## Open questions for operator
- **O6**: workspace DB `signoffs` table now, or JSONL ledger alone until volume warrants? (Recommend: ledger alone for now.)
- **O7**: may SAFE-tier acknowledgments be autonomous (sentinel operator id) under the schema-migration amendment, or must every record carry a human key fingerprint?
- **O8**: operator identity granularity — single Governor key fingerprint (one operator today), or room for multiple named operators now? (Recommend: fingerprint field accommodates both; no multi-user work needed yet.)
- **O9**: should the gate treat a broken `prev_hash` chain as advisory (loud warning, not locked) or as a hard lock? (Recommend advisory, to avoid a malformed historical line bricking the engine — consistent with fail-safe.)
- **O10**: ledger write path — does the Governor action route write+commit the ledger via the same GitHub API path the agent uses, or does the VPS file_server own ledger writes (it already pushes files to GitHub)? (Recommend: file_server owns it, since it already has the push pipeline and the local `audit()` mirror.)
