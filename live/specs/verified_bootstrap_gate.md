# SPEC — Verified Bootstrap Gate (initialization as comply-or-fail)

*Status: CORRECTED B1 CANDIDATE SPEC (uncommitted, rejected three times in independent review, corrected again, not live), 2026-09-08. The original BOOTGATE-1 design was authored by worker1 (claude:opus-4.8). This revision describes the candidate runnable exactly: the current 20-operation courier, latest-fold queue orientation, capability-before-gate admission, and no shared-key issuance stub. Grounds: live/PUNCH_LIST.md HIGH item "Verified bootstrap gate"; OPERATING_MANUAL.md (open ritual, close ritual, scoped operations / operations_ledger audit spine, cold-boot onboarding); corpus operations_ledger schema. Do not deploy from this file; exact runtime bytes are controlled by B1_INSTALL_MANIFEST.json and require a clean independent review.*

## 1. PROBLEM (grounded)
The open ritual is an INSTRUCTION a seat can skip, and a seat did skip it (June 10): a seat that did not run the full read behaved as if perpetually orienting — asserted capabilities absent / limits present without checking — and cost the operator a morning (PUNCH_LIST.md, this item). The manual itself names this the silent-failure class: "confident proposals anchored to stale state" (OPERATING_MANUAL.md, open ritual). Instructed orientation does not bind; a verified gate removes the choice. This is the Tetraform's comply-or-fail logic turned INWARD on the seat's own init — do not trust the self-report, verify it. It is the PREREQUISITE for trustworthy fractal workers: you cannot safely fan out to N worker seats unless each PROVES it oriented before touching anything.

## 2. WHAT THE GATE IS
A deterministic checklist a seat MUST pass before it is permitted to propose or act. Each step produces a CHECKABLE RESULT (not a self-attestation); a deterministic check ratifies each result. The gate returns one of two states: ORIENTED (all checks PASS -> seat may act) or NOT ORIENTED (any check fails -> seat refuses to act and reports which check failed). There is no partial-credit "mostly oriented" state — the gate is all-or-nothing, mirroring comply-or-fail.

## 3. THE ORDERED CHECKS (each: probe -> deterministic pass condition -> failure message)
Run in order; STOP at the first failure (a later check often depends on an earlier one — corpus/hands checks are meaningless if the relay is down).

SEAT-ROLE PARAMETERIZED (operator ruling, June 10): the gate is NOT worker-only — it MUST also gate the CONTROL seat, which is the bigger hole (control holds the token and dispatches/reviews/commits, so its drift contaminates everything downstream). The runnable takes role in {control, worker}. CHECKS 1-5 (the STATE checks) run for BOTH roles. CHECK 6 (MECHANICS) runs for the control role always, and is run for workers too (good practice).

### CHECK 1 — MANUAL
- Probe: read live/OPERATING_MANUAL.md from the public repository with a cache-busting query. Refuse redirects so no server-held authentication can be carried to another origin.
- Returned fact (the checkable result): the current courier op-allowlist COUNT parsed from the "SCOPED OPERATIONS" / courier section.
- Deterministic pass condition: parsed count == the courier count MAIN derives from its actual `OP_ALLOWED` set and supplies over the authenticated server hop (currently 20). A committed fallback of 20 exists only for direct operator/recovery execution and moves in the same reviewed change as `OP_ALLOWED`; request-body data never selects this standard.
- Failure message: `NOT ORIENTED [CHECK 1 MANUAL]: courier allowlist count mismatch (manual=<n>, canonical=<m>) — manual may be stale or unreachable; re-sync before acting.`

### CHECK 2 — QUEUE
- Probe: read the complete append-only live/agent_queue.md and select its latest canonical `## FOLD` section.
- Returned fact: the one bounded bullet beneath that fold's single `**NEXT**` marker.
- Deterministic pass condition: the latest fold contains exactly one NEXT marker and exactly one complete bullet (indented continuation lines are part of that bullet). The historical queue head and older folds cannot satisfy the check.
- Failure message: `NOT ORIENTED [CHECK 2 QUEUE]: latest FOLD lacks exactly one bounded NEXT bullet.`

### CHECK 3 — CORPUS
- Probe: GET `{engine}/diag/api/query` with the single query `SELECT COUNT(*) FROM sessions`.
- Returned fact: `sessions count = <count>; floor = <stored floor>`.
- Deterministic pass condition: the endpoint returns HTTP 200 and a JSON object whose first row/first column parses as an integer at or above the stored floor (currently 307). A missing or malformed row, query error, or count below the floor FAILS. The runnable does not claim to retrieve a latest-activity timestamp.
- Failure message: `NOT ORIENTED [CHECK 3 CORPUS]: sessions count <n> below floor <floor> or query error — wrong DB, stale snapshot, or hands not reaching the corpus.`

### CHECK 4 — HANDS
- Probe: reach `/diag/op/bootstrap_gate` with the approved capability. MAIN validates the signed seat, lineage, operation, expiry, approval, and revocation before forwarding a server-derived identity to the box. Arrival of that authenticated identity at this gate proves the courier hands. Direct shared-root operator recovery instead performs a header-authenticated `mailbox_peek`.
- Returned fact for a capability call: `authenticated capability reached the box through the courier`. For direct operator recovery: `mailbox_peek ok (count=<n>)`.
- Deterministic pass condition: a capability call's authenticated relay identity exists and its derived seat matches the gate seat. Direct operator recovery instead requires `mailbox_peek` to return HTTP 200, JSON, and `ok:true`. A mismatch or failed direct probe FAILS.
- Failure message: `NOT ORIENTED [CHECK 4 HANDS]: courier mailbox_peek did not return ok JSON — seat lacks working box hands; do not act.`

### CHECK 5 — ENGINE STATE
- Probe: GET {engine}/diag/engine for BOTH engines (MAIN web-production-7eaf8 and FARM ontinuity-farm-production).
- Returned fact: `MAIN: running=<bool>; FARM: running=<bool>`.
- Deterministic pass condition: both endpoints return HTTP 200 JSON objects whose `running` field is a real boolean. Reachability + parseability is the pass bar; `running:true` is not itself a gate failure. The runnable does not claim to return `waiting_for_input`, `cycle`, or `started_by`.
- Failure message: `NOT ORIENTED [CHECK 5 ENGINE]: engine <name> unreachable or unparseable — cannot confirm live/idle state; commits to watched paths unsafe.`

### CHECK 6 — MECHANICS (operator ruling, June 10; runs for CONTROL always, workers too)
The five STATE checks catch stale STATE. CHECK 6 catches stale operating MECHANICS — the seat correctly REPRODUCING the system's operating invariants, ratified against the manual, NOT self-asserted. Rationale is a live receipt: the control seat drifted on invariant (a) THIS session — asserted the loop was fully autonomous, then one turn later forgot chat seats do not self-poll. That is exactly the error class STATE checks do not cover.
- Probe: the seat states the operating invariants; the runnable matches its reproduction against the canonical statements AND ratifies each against a distinctive manual substring (manual ratification, not self-assertion). Minimum invariants: (a) a chat seat does NOT self-poll the mailbox — it acts only when its conversation is given a turn (coordination is mailbox-native, but a worker still needs its conversation nudged); (b) what the relay-courier does and that sandbox seats reach the box ONLY through it; (c) "operator owns deploys" = authority + rollback, NOT a per-redeploy human click; (d) a new box op needs BOTH a box install (write_file + restart, hands-free) AND an OP_ALLOWED entry (commit + deploy).
- Returned fact: a JSON object with `role`, a summary on success, and a `findings` array. Each processed invariant has stable fields `key`, `reproduced`, `coverage`, `manual_ratified`, and `pass`. The successful path returns all four findings; a failure returns the findings processed through the first failure.
- Deterministic pass condition: for every invariant, the seat's reproduction covers >=85% of the canonical statement's tokens (deterministic token-subset match, NOT semantics) AND the manual carries the invariant's probe substring. Any invariant failing either condition FAILS the check.
- Failure message: `NOT ORIENTED [CHECK 6 MECHANICS]: invariant '<key>' not reproduced (token coverage <c> < 0.85)` or `... reproduced but NOT ratified by manual (probe absent) — manual/seat incoherent; re-sync.`
- Manual ratification is implemented for all four invariants. In particular, the manual contains the exact no-self-poll probe `a chat seat does NOT self-poll the mailbox`; absence of that text makes CHECK 6 fail.

## 4. WHERE THE GATE LIVES + HOW IT RETURNS NOT ORIENTED
- In this candidate, the runnable is `live/bootstrap/gate.py` and the box exposes it through `/op/bootstrap_gate`; MAIN exposes the allowlisted `/diag/op/bootstrap_gate` courier route. The box route logs the result to `operations_ledger`. These bytes are local candidate bytes, not a claim about the live installation.
- Return contract: a structured result `{oriented: bool, seat, role, lineage, checks: [{name, pass, returned_fact, failure_message?}]}` (role in {control, worker}). oriented==true ONLY if every run check.pass is true. On any failure the gate returns oriented:false with the first failing check's message; the seat MUST refuse to propose or act and surface `NOT ORIENTED [CHECK x ...]` rather than proceeding on stale state. NOT ORIENTED is a hard stop, not a warning.
- The gate is comply-or-fail and NEVER self-locking: it must not brick the seat's ability to REPORT the failure or to read the manual/queue needed to recover (mirrors the scoped-op "never self-locking" rule).

## 5. HOW IT HOOKS CAPABILITY ADMISSION
The gate does not mint, unseal, or return a root. A seat first submits a public, non-authorizing request. The operator inspects the requested seat, lineage, operations, and lifetime in MAIN and, if appropriate, issues a short-lived capability. That signed grant is what permits the seat to call the gate.
- MAIN validates the capability and forwards only its derived seat, lineage, and capability ID over the server-to-server root-authenticated hop. Request-body identity cannot replace those claims.
- The box stamps that derived identity into the operations ledger and records the gate result. A failed gate leaves the capability cryptographically valid but the operating contract requires the seat to stop; the initial grant exposes no write, commit, deploy, restart, purge, seed, backup, egress, or arbitrary-box-read operation.
- Approval and revocation remain operator actions. The authority persists request/grant metadata but never bearer material. The gate never returns the diagnostic root or a replacement credential.

## 6. HOW OPEN + CLOSE RITUAL REFERENCE IT
- OPEN RITUAL: today the open ritual is the instructed orientation (search queue folds, read conversation records, follow refs). The gate is the VERIFIED, machine-checked floor UNDER it: after admission a seat runs the gate (proves manual/latest-fold queue/corpus/hands/engine + mechanics), THEN completes the human-judgment reads the deterministic gate deliberately does not interpret. The gate ratifies that the latest fold has one bounded next action; a human/control still owns whether it is the right action. Pass the gate to earn the right to act; complete the reads to reason well.
- CONTROL SEAT runs the gate at open too (operator ruling, June 10): the control open ritual and the cold-boot onboarding both require a passing gate (role=control, so CHECK 6 MECHANICS runs) before control may dispatch, review, or commit. An unverified control seat is the bigger hole — it must prove it can reproduce the operating mechanics, not just that its state is fresh.
- CLOSE RITUAL: the close ritual already verifies STATE LEFT CLEAN (engine idle, no orphaned mailbox claim) and MANUAL CURRENCY. The gate adds two reciprocal obligations: (a) if this session changed an operation that a gate check reads (courier allowlist count for CHECK 1, the corpus floor for CHECK 3, a new engine for CHECK 5), the close ritual MUST update the gate's stored canonical values in the SAME commit (manual-currency discipline extended to the gate's constants) — a stale gate constant would false-FAIL the next seat. (b) the close ritual records, against the session's shas/receipts, that this seat passed the gate at open (the operations_ledger bootstrap_gate rows are the evidence), so the audit chain shows every acting seat proved orientation before it acted.

## 7. CANDIDATE IMPLEMENTATION STATUS (operator-gated — DO NOT deploy from this spec)
1. The six-check, seat-role-parameterized runnable exists at `live/bootstrap/gate.py`.
2. `/diag/op/bootstrap_gate` is in MAIN's `OP_ALLOWED`; MAIN derives the canonical operation count and removes any caller-supplied override.
3. The box route writes begin/end `operations_ledger` evidence.
4. Operator-approved short-lived capability admission precedes a capability gate call; the gate does not issue credentials.
5. Current Control and Worker boot packets require a passing gate. None of these candidate bytes are live until an authorized exact-manifest transition.

## 8. ACCEPTANCE (how to prove the gate works)
- An invalid capability is rejected by MAIN before the box gate runs. A direct operator-recovery gate with a wrong diagnostic root fails at the first authenticated remote probe (normally CHECK 3 because checks stop at the first failure); a deliberately failed direct `mailbox_peek` reaches the CHECK 4 failure path.
- A seat pointed at an empty/wrong DB FAILS CHECK 3 (below floor).
- A drifted manual (allowlist count edited) FAILS CHECK 1 until re-synced.
- A clean seat PASSES all six checks, the gate returns oriented:true, an operations_ledger bootstrap_gate row exists with status ok and the capability-derived caller, and only THEN does the seat proceed. (Mirrors the VERIFICATION RECIPE shape: baseline -> trigger -> confirm rows.)
