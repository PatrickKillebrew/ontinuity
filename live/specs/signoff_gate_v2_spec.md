# Design Spec — Self-Enforcing Deploy Sign-off Gate, v2 (provenance-verified, tiered)

**Status: DESIGN ONLY. Supersedes the v1 gate proposal (live/fixes/burnin_signoff_gate_proposal.md, commit 3a0f3a56). No build, no deploy. Read-only basis.**

## What changes from v1
v1 checked the commit **message** for the `Operator-Signoff:` substring and hard-locked session starts on an unsigned engine deploy. Two problems: a message substring is forgeable by anything that commits, and a blanket lock risks bricking the engine (self-bootstrap). v2, per the approved rulings:
1. Verifies against the **provenance ledger** `live/signoffs/ledger.jsonl` (spec 8aa730c4) — a real `sign-deploy` record, not a string.
2. Is **advisory by default, never self-locking**. The only hard-block is a positively-detected **RISK-tier** live mutation lacking a record.
3. Integrates tiering: classifier proposes, operator may escalate, never silently de-escalate.

## Data contract with the ledger
The gate reads `live/signoffs/ledger.jsonl` (JSONL, source of truth; DB deferred). It looks for a record:
```
action == "sign-deploy"  AND  commit_sha == <running SHA>  AND  instance in (<this instance>, "both")
```
The matching record's `risk_tier`, `operator`, `ts`, `basis` are authoritative for "signed" status. The `prev_hash` integrity chain is checked **advisory only** — a break emits a loud warning and is surfaced in `/diag/engine`, but **never locks** (a malformed historical line must not brick the engine; consistent with fail-safe).

## Tier determination (prevents silent de-escalation)
- **Signed commit** → tier comes from the record (authoritative).
- **Unsigned commit** → the gate must decide whether to block. It classifies the running commit's diff for **positively-detectable RISK patterns** (destructive/irreversible live mutation: migration files with DROP/ALTER-data-loss, vault/secret surface, live-data writes). Tier is **not** taken from any commit-message trailer for the blocking decision — a trailer could silently de-escalate a RISK change to SAFE, which the rulings forbid. Classification can only *find* RISK, never hide it; if it detects no RISK pattern, the commit is treated as REVIEW/SAFE → advisory.

## Decision matrix (startup, per instance)
| Running commit | sign-deploy record? | Gate action |
|---|---|---|
| app.py / engine change (REVIEW), or no RISK pattern detected | yes | `signoff_status=signed`; **no block** |
| app.py / engine change (REVIEW), or no RISK pattern detected | no | `signoff_status=unsigned-advisory`; **no block**; loud console + diag surfacing |
| **positively-detected RISK pattern** | yes | `signoff_status=signed-risk`; **no block** |
| **positively-detected RISK pattern** | no | `signoff_status=unsigned-RISK`; **BLOCK** session starts (the one hard case) |
| missing `RAILWAY_GIT_COMMIT_SHA`, ledger unreadable, classification error, broken chain | any | `signoff_status=unknown`; **no block** (fail-safe); surface loudly |

SAFE-tier items never reach the engine-startup gate (they are repo/doc/additive-migration changes, not app.py deploys); their handling is one-tap-with-fingerprint in the Governor (autonomy stays scoped to the schema-migration class). REVIEW is advisory here — reversible by redeploy, so not worth bricking over; the operator's single sign-off is recorded in the ledger and surfaced as `signed`, but its absence does not stop the engine.

## Self-bootstrap wrinkle — resolved by tiering
v1's blanket lock meant the gate's own first deploy could lock itself if unsigned. v2 removes that: the gate's own deploy is an **app.py code change = REVIEW-tier**, which is **advisory, never blocking**. So the gate cannot self-lock on its own deploy. The only self-lock path is if the gate's deploy bundled a positively-detected RISK change with no record — which it does not. Explicitly: **a pure engine deploy of the gate is advisory and safe to ship without a pre-existing record.** (It will report `unsigned-advisory` until a `sign-deploy` record is recorded for its commit — expected and harmless.)

## Flow end-to-end
1. Operator reviews an item in the Governor Adjudicator panel; taps sign-off (records-only, no deploy button per ruling). A `sign-deploy` provenance record is written to the ledger (file_server owns the write — O10 from spec 8aa730c4).
2. Operator deploys via Railway (separate, deliberate act).
3. Engine starts → `verify_deploy_signoff()` reads its SHA + the ledger → sets `signoff_status` per the matrix → blocks only on `unsigned-RISK`.
4. `/diag/engine` reports `signoff_status`, the matched record (operator/ts/tier) or its absence, and any integrity-chain warning — so the Governor's Deploy-State strip shows signed vs unsigned-advisory vs unsigned-RISK at a glance.

## Pseudocode (verify only — illustrative, not for build)
```
def verify_deploy_signoff():
    sha = env("RAILWAY_GIT_COMMIT_SHA"); inst = this_instance()
    if not sha: return advisory("unknown")            # fail-safe
    ledger = fetch_ledger_jsonl()                       # GitHub API; on error -> advisory("unknown")
    rec = find(ledger, action="sign-deploy", commit_sha=sha, instance in {inst,"both"})
    chain_ok = verify_prev_hash_chain(ledger)           # advisory only
    if rec: return status("signed", tier=rec.risk_tier, by=rec.operator, chain_ok=chain_ok)  # no block
    tier = classify_commit_risk(sha)                    # positively detect RISK only; uncertain -> not-RISK
    if tier == "RISK": return block("unsigned-RISK", chain_ok=chain_ok)
    return advisory("unsigned-advisory", chain_ok=chain_ok)
```
`signoff_blocked()` (guarding session-start paths) returns a refusal **only** when `signoff_status == "unsigned-RISK"` and no `SIGNOFF_OVERRIDE`. Every other status is advisory.

## Open questions for operator
- **G1**: the RISK classifier — should it live in the engine (fetch+inspect its own diff at startup) or read a tier the Governor recorded at sign-off time? Since the blocking case is *unsigned* (no record exists), the engine must self-classify for that case. Recommend a minimal pattern-based self-classifier (DROP / data-loss ALTER / vault paths) scoped only to *finding* RISK, since engine deploys are essentially never RISK and the block is a backstop.
- **G2**: should `unsigned-RISK` block be per-instance (lock only the instance lacking a record) — yes, since records are per-instance; confirm.
- **G3**: ledger fetch at startup uses the authenticated GitHub API (shared-egress rate limits noted) — acceptable as a single startup read, or should the gate read a VPS-local mirror of the ledger (file_server already keeps an `audit()` copy) to avoid the API entirely? Recommend VPS-local mirror read with GitHub as fallback.
- **G4**: confirm REVIEW absence stays advisory (no block) — the rulings imply yes; flagging because it means an unsigned reversible engine deploy runs and merely reports `unsigned-advisory`. That is the intended proportional behavior.
