# SPEC — Verified Bootstrap Gate (initialization as comply-or-fail)

*Status: BUILD SPEC (not deployed). [Control currency note, post-authoring: courier allowlist moved 10->12 (read_file, commit_file added) right after this spec was authored; CHECK 1 canonical count updated to 12 below. This is exactly the gate-constant-currency obligation §6 close-ritual (a) describes.] Authored by worker1 (claude:opus-4.8) under block BOOTGATE-1, dispatched by control. Grounds: live/PUNCH_LIST.md HIGH item "Verified bootstrap gate"; OPERATING_MANUAL.md (open ritual, close ritual, scoped operations / operations_ledger audit spine, cold-boot onboarding); corpus operations_ledger schema. Do not deploy from this file; it specifies the build for operator sign-off.*

## 1. PROBLEM (grounded)
The open ritual is an INSTRUCTION a seat can skip, and a seat did skip it (June 10): a seat that did not run the full read behaved as if perpetually orienting — asserted capabilities absent / limits present without checking — and cost the operator a morning (PUNCH_LIST.md, this item). The manual itself names this the silent-failure class: "confident proposals anchored to stale state" (OPERATING_MANUAL.md, open ritual). Instructed orientation does not bind; a verified gate removes the choice. This is the Tetraform's comply-or-fail logic turned INWARD on the seat's own init — do not trust the self-report, verify it. It is the PREREQUISITE for trustworthy fractal workers: you cannot safely fan out to N worker seats unless each PROVES it oriented before touching anything.

## 2. WHAT THE GATE IS
A deterministic checklist a seat MUST pass before it is permitted to propose or act. Each step produces a CHECKABLE RESULT (not a self-attestation); a deterministic check ratifies each result. The gate returns one of two states: ORIENTED (all checks PASS -> seat may act) or NOT ORIENTED (any check fails -> seat refuses to act and reports which check failed). There is no partial-credit "mostly oriented" state — the gate is all-or-nothing, mirroring comply-or-fail.

## 3. THE ORDERED CHECKS (each: probe -> deterministic pass condition -> failure message)
Run in order; STOP at the first failure (a later check often depends on an earlier one — corpus/hands checks are meaningless if the relay is down).

### CHECK 1 — MANUAL
- Probe: read live/OPERATING_MANUAL.md via authed api.github.com (Accept: application/vnd.github.raw); fall back to raw CDN only if API rate-limited (raw serves stale cache for hot files — acceptable for the manual, which changes rarely).
- Returned fact (the checkable result): the current courier op-allowlist COUNT parsed from the "SCOPED OPERATIONS" / courier section.
- Deterministic pass condition: parsed count == the canonical allowlist length the gate holds (currently 12: read_journal, restart_workspace, register_egress, mailbox_send, mailbox_fetch, mailbox_ack, mailbox_peek, mailbox_reclaim, write_file, commit_self, read_file, commit_file). The gate stores this canonical number from the same source of truth (OP_ALLOWED in app.py) so a manual/code drift is itself caught.
- Failure message: `NOT ORIENTED [CHECK 1 MANUAL]: courier allowlist count mismatch (manual=<n>, canonical=<m>) — manual may be stale or unreachable; re-sync before acting.`

### CHECK 2 — QUEUE
- Probe: read live/agent_queue.md head (the curated ACTIVE block + latest CURRENT-STATE TOUCH POINT fold).
- Returned fact: the single current NEXT-SEAT action, stated in one line.
- Deterministic pass condition: the head parses to a non-empty ACTIVE head item AND the seat emits exactly one next-action line (the check ratifies non-empty + single-line, not the semantics — a human/control still owns whether it is the RIGHT action). An empty or unparseable queue head FAILS.
- Failure message: `NOT ORIENTED [CHECK 2 QUEUE]: agent_queue head empty or unparseable — no current next action to orient onto.`

### CHECK 3 — CORPUS
- Probe: GET {engine}/diag/api/query for live table counts + an activity arc (e.g. SELECT COUNT(*) FROM sessions; plus most-recent created_at).
- Returned fact: a state summary (session count + latest-activity timestamp).
- Deterministic pass condition: query returns ok with row_count>=1 AND COUNT(sessions) >= a stored floor (monotonic non-decreasing; the floor is the last-known count, today 307+). A count of 0, a query error, or a count BELOW the stored floor FAILS (below-floor = wrong DB / stale snapshot / WAL read-transaction trap — the manual's confirmed diagnostic trap). Mirrors the migration-drill acceptance test.
- Failure message: `NOT ORIENTED [CHECK 3 CORPUS]: sessions count <n> below floor <floor> or query error — wrong DB, stale snapshot, or hands not reaching the corpus.`

### CHECK 4 — HANDS
- Probe: POST {engine}/diag/op/mailbox_peek {seat:<seat>, limit:1} through the relay-courier.
- Returned fact: a clean JSON envelope (ok:true), even if count==0 (empty box still proves the hands).
- Deterministic pass condition: HTTP 200 AND body parses as JSON AND ok==true. A non-200, an HTML/error body, or a courier-forwarding failure FAILS — this is the check that proves the seat actually HAS the hands it thinks it has, rather than assuming them (the exact wrong-declaration failure the gate exists to prevent).
- Failure message: `NOT ORIENTED [CHECK 4 HANDS]: courier mailbox_peek did not return ok JSON — seat lacks working box hands; do not act.`

### CHECK 5 — ENGINE STATE
- Probe: GET {engine}/diag/engine for BOTH engines (MAIN web-production-7eaf8 and FARM ontinuity-farm-production).
- Returned fact: each engine's running / waiting_for_input / cycle / started_by.
- Deterministic pass condition: both endpoints return parseable JSON with the running field present. Reachability + parseability is the pass bar; running:true is NOT a failure (a live session is normal) but is surfaced so the seat knows not to commit a watched path during a live session (standing rule). An unreachable engine FAILS.
- Failure message: `NOT ORIENTED [CHECK 5 ENGINE]: engine <name> unreachable or unparseable — cannot confirm live/idle state; commits to watched paths unsafe.`

## 4. WHERE THE GATE LIVES + HOW IT RETURNS NOT ORIENTED
- Lives as a bootstrap module the seat runs as step zero of coming online — a single callable (proposed: a /diag/op/bootstrap_gate courier op AND a sandbox-local runnable, so a seat can self-gate before it has confirmed hands, then the courier op re-verifies server-side). The courier op is added to OP_ALLOWED in app.py (same allowlist CHECK 1 counts) and logs to operations_ledger like every op.
- Return contract: a structured result `{oriented: bool, checks: [{name, pass, returned_fact, failure_message?}], seat, lineage}`. oriented==true ONLY if every check.pass is true. On any failure the gate returns oriented:false with the first failing check's message; the seat MUST refuse to propose or act and surface `NOT ORIENTED [CHECK x ...]` rather than proceeding on stale state. NOT ORIENTED is a hard stop, not a warning.
- The gate is comply-or-fail and NEVER self-locking: it must not brick the seat's ability to REPORT the failure or to read the manual/queue needed to recover (mirrors the scoped-op "never self-locking" rule).

## 5. HOW IT HOOKS PER-IDENTITY WORKER-KEY ISSUANCE
Grounded in the operations_ledger schema (corpus): the table already carries a `caller` column (op_id, operation, tier, caller, source_ip, args, result, status, started_at, finished_at). TODAY every seat shares ONE DIAG_KEY, so `caller` is self-asserted — a seat writes whatever seat name it likes and the ledger cannot prove key-use belongs to that seat (the same trust gap the gate exists to close, at the credential layer).
- Issuance ON PASS: a worker does not hold a usable per-identity key until it PASSES the gate. The gate, on oriented:true, issues (or unseals) the seat's per-identity worker key bound to its seat name + lineage. A seat that fails the gate gets no key and therefore no privileged hands — comply-or-fail enforced at the credential, not just at conduct.
- Attribution: once keys are per-identity, the courier/box authenticates the specific key and stamps the verified seat identity into operations_ledger.caller (and source path) for EVERY op, so each key-use is attributable to a seat that PROVABLY oriented. This is the move from "instructed + self-named" to "verified + attributed."
- Custody stays operator's: key MATERIAL is issued/unsealed by the operator's vault path (the password-unlocked vault bootstrap, PUNCH_LIST.md #42: KDF-decrypt master key in-memory, pull per-seat keys, write a key-access grant row sibling to operations_ledger). The gate is the GATE on issuance; it does not mint or store secrets itself, and no key material is ever written to a committed file (no-credentials rule).
- Dependency note (inference, labeled): full per-identity attribution depends on the vault bootstrap (#42) landing; until then the gate can still run all five checks and gate CONDUCT, with key-issuance stubbed to the shared DIAG_KEY and `caller` carrying the gate-verified seat name as a best-effort (honest about being unattested). This staging lets the gate ship before the vault without blocking on it.

## 6. HOW OPEN + CLOSE RITUAL REFERENCE IT
- OPEN RITUAL: today the open ritual is the instructed orientation (search queue folds, read conversation records, follow refs). The gate is the VERIFIED, machine-checked floor UNDER it: a seat runs the gate first (proves manual/queue/corpus/hands/engine), THEN runs the human-judgment open ritual (the semantic re-grounding the gate deliberately does not attempt — the gate ratifies that the queue head is non-empty and single-line, it does not decide it is the right action). Pass the gate to earn the right to reason; run the open ritual to reason well. For a cold seat the gate replaces the ad-hoc "find your hands" checks in COLD-BOOT ONBOARDING with a deterministic pass/fail.
- CLOSE RITUAL: the close ritual already verifies STATE LEFT CLEAN (engine idle, no orphaned mailbox claim) and MANUAL CURRENCY. The gate adds two reciprocal obligations: (a) if this session changed an operation that a gate check reads (courier allowlist count for CHECK 1, the corpus floor for CHECK 3, a new engine for CHECK 5), the close ritual MUST update the gate's stored canonical values in the SAME commit (manual-currency discipline extended to the gate's constants) — a stale gate constant would false-FAIL the next seat. (b) the close ritual records, against the session's shas/receipts, that this seat passed the gate at open (the operations_ledger bootstrap_gate rows are the evidence), so the audit chain shows every acting seat proved orientation before it acted.

## 7. BUILD SEQUENCE (proposed, operator-gated — DO NOT deploy from this spec)
1. Sandbox-local gate runnable (the five checks, structured result) — usable by control + workers immediately, no deploy.
2. /diag/op/bootstrap_gate courier op + OP_ALLOWED entry (CHECK 1's canonical count increments by one in the SAME commit as this op lands — manual + gate constant updated together).
3. operations_ledger bootstrap_gate rows (reuse _ops_begin/_ops_finish; dual-end).
4. Per-identity key issuance-on-pass — STUBBED to shared DIAG_KEY until vault bootstrap (#42) lands; then bind real per-seat keys + stamp verified caller.
5. Wire open ritual / cold-boot to require a passing gate; wire close ritual to update gate constants + record the pass.

## 8. ACCEPTANCE (how to prove the gate works)
- A seat with a deliberately-broken hand (wrong DIAG_KEY) FAILS CHECK 4 and refuses to act with `NOT ORIENTED [CHECK 4 HANDS]`.
- A seat pointed at an empty/wrong DB FAILS CHECK 3 (below floor).
- A drifted manual (allowlist count edited) FAILS CHECK 1 until re-synced.
- A clean seat PASSES all five, the gate returns oriented:true, an operations_ledger bootstrap_gate row exists with status ok and the seat's caller, and only THEN does the seat proceed. (Mirrors the VERIFICATION RECIPE shape: baseline -> trigger -> confirm rows.)
