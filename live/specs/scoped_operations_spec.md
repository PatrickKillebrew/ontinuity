# Spec — Scoped Operations (the autonomous-operator capability foundation)

**Status: DRAFT for operator review. The capability that lets the operator/control seat perform privileged, bounded actions on the box itself — killing the "human is the router" bottleneck. Designed carefully because this is real authority delegation.**

## What this is — and what it deliberately is NOT
- **NOT a terminal / shell.** No endpoint ever accepts an arbitrary command string. "Terminal capabilities" here means an **allowlist of named, scoped operations**, each a defined endpoint that does exactly one bounded thing and nothing else.
- The proof-of-pattern already exists: `/register_egress` (built June 9) takes no command — it performs one defined action (allow an IP on port 5001), validates inputs, and refuses anything outside its scope.
- The capability surface is exactly the set of named operations. Each is auditable, bounded, and individually reasoned about. Adding a capability = adding a named operation, never widening a general one. This keeps the comply-or-fail property: a seat (or a leaked key) can only ever invoke the named operations, never arbitrary execution.

## Component 1 — the Operations Ledger (BUILD FIRST, before any operation)
An append-only audit record on the workspace. **Every** scoped operation writes to it — no privileged action exists without an audit trail. This is the spine; it goes in before operation #1 so the very first operation is already audited.
- Storage: a dedicated table `operations_ledger` (mirrors the write-receipts pattern already in file_server.py) OR an append-only JSONL file. Recommend the table (queryable, joins to receipts).
- Schema: `op_id` (PK), `operation` (the named op), `caller` (auth principal — which key/seat), `source_ip` (remote_addr), `args` (the bounded inputs, JSON), `result` (ok/fail + summary), `started_at`, `finished_at`.
- Written at BOTH ends: an entry on invocation (intent) updated with the result on completion, so a crashed/hung operation leaves a visible incomplete record (no fail-quiet).
- Read-only exposure via the diag relay so the operator seat can audit the operation history without box access.

## Component 2 — the scoped-operation contract (the pattern every op follows)
Each operation endpoint:
1. **Auth**: diag-key gated (constant-time compare), the same gate as `/register_egress`. Only seats holding the secret can invoke. (Tiering note below for riskier ops.)
2. **Bounded inputs**: validates every input against a strict schema; rejects anything outside it (e.g. an IP must be valid IPv4; a CIDR must be inside the cloud allowlist and never broader than /16).
3. **One action**: performs exactly one defined thing. Never branches into "also do X."
4. **Logs to the ledger** at invocation and completion.
5. **Fail-safe**: on any uncertainty, refuses and logs — never proceeds on a guess. Never self-locking (an operation must never be able to brick the operator's ability to run the fix for the operation).
6. **Reversible where possible**: prefer operations that can be undone; for irreversible ones, require a higher tier (below).

## Component 3 — tiering (reuse the sign-off tiers already designed)
Operations carry a risk tier, consistent with the sign-off rulings (SAFE / REVIEW / RISK):
- **SAFE**: read-only or trivially reversible (read a log, report health, whitelist an IP). Key-gated, auto-runs, logged.
- **REVIEW**: changes operational state reversibly (restart a service, reconfigure a server). Key-gated + logged + (in the mature system) an operator sign-off token, OR a tight guard + easy rollback.
- **RISK**: irreversible or wide-blast (delete data, schema-destructive). Behind the strictest gate, a must-refuse museum, explicit operator sign-off. Most operations should never be this tier.
- Classifier proposes a tier; operator may escalate, never silently de-escalate (the standing rule).

## Operation #1 — the SAFE, reversible proof (NOT the gunicorn fix)
**Decision (Option B): prove the pattern + ledger on a SAFE, reversible operation first; do the riskier gunicorn/key-auth firewall fix as operation #2 once the pattern is proven. Don't make the pattern's debut the highest-stakes action.**

Candidate for operation #1 — OPEN QUESTION for operator:
- **(i) Read-only workspace journal/connection-log read** — zero risk, already a wanted item. BUT read-only, so it does not exercise the *mutation* path that is the whole point.
- **(ii) Scoped workspace-service restart** — a real privileged mutation, reversible (it comes back up), proves the mutation pattern. Small risk: a restart briefly drops the service. Recommend THIS as op #1 — it proves the mutation+ledger pattern on something real but recoverable, and it is independently useful (the operator seat can restart the workspace after a change without operator hands).
- **(iii) Both** — ship the read-only journal read (SAFE, immediately useful for the firewall-IP-history gap) AND the restart (proves mutation). Recommend (iii) if appetite allows: one read op + one mutate op covers both halves of the pattern.

## Operation #2 — retire the IP firewall (the real fix, from the record)
Per the firewall verdict (queue line 288): reconfigure the workspace to run behind **gunicorn on an open port with key-auth**, removing the IP-whitelist dependency entirely and killing the redeploy time-bomb. This is REVIEW/RISK tier (reconfigures how the service serves; a botched reconfigure could take the workspace down). Done as operation #2 *after* the pattern is proven on op #1, with rollback ready (keep the working Flask config; the operation swaps to gunicorn and verifies health before committing, reverts on failure).

## Why this is the foundation (not convenience)
Tonight hit the same wall from every angle — firewall, driver start, IP whitelisting, read-only relay — all one missing capability: the operator seat cannot perform privileged, scoped actions on its own. Scoped operations dissolve all of them and **unblock delegation itself**: once the worker can invoke scoped operations, the worker can do the corpus-join chores, the firewall self-heals, driver work goes hands-free, and the human stops being the router. Pairs with the fractal-coordination foundation (the worker army needs exactly this capability to act).

## Operator rulings (resolved)
- **Q1 = (iii) both**: operation #1 is a read-only journal/connection-log read AND a scoped workspace-service restart — one read op + one mutate op, covering both halves of the pattern.
- **Q2 = table**: the ledger is a queryable `operations_ledger` table (joins to receipts).
- **Q3 = mature**: SAFE ops = diag-key only; REVIEW/RISK ops = diag-key + operator sign-off token (the mature model), with tight-guard + rollback as the interim until the sign-off ledger exists.

## Original open questions (now resolved above)
- **Q1**: operation #1 choice — (i) read-only journal, (ii) service restart, or (iii) both? (Recommend iii, or ii if picking one.)
- **Q2**: ledger as a table (queryable, joins to receipts) vs JSONL file? (Recommend table.)
- **Q3**: auth — keep diag-key for SAFE ops, but should REVIEW/RISK ops require a *second* factor (an operator sign-off token, per the sign-off gate design) even when a seat invokes them? (Recommend: SAFE = key only; REVIEW/RISK = key + sign-off token in the mature system, tight-guard + rollback until the sign-off ledger exists.)
