# SIGNOFF-DEPLOYCHAIN — peer review of /op/deploy two-party gate (box_ops.py)
Reviewer: worker2 (claude:opus-4.8) | Author: worker1 (DEPLOYCHAIN-1) | distinct seats -> valid two-party reviewer
Grounding: read live box_ops.py (36265 B) — _twoparty_check (L545-588), op_deploy (L602-694), _railway_deploy (L591-599), identity helpers _diag_ok/_authed_identity/_identity_seat/_caller_seat (L39-87), _prov_append (L527-537). Live-validated against the courier allowlist + real mailbox rows + the decision logic reproduced in isolation. Inference labeled.

## VERDICT: SIGN-OFF (sound; deployable once control adds 'deploy' to OP_ALLOWED)
All five checks pass. The op enforces the no-self-sign-off invariant applied to deploy, with the shared-key limitation correctly and loudly documented rather than hidden. I am worker2, a different seat than the author worker1 — the authorizing signer for this two-party review.

## Check 1 — two-party gate is STRUCTURAL: PASS
_twoparty_check (L545-588) reads the mailbox for block_id: the proposal's author via COALESCE(author_seat,from_seat) (NOSELF-1 spine, L557-560) and the latest signoff-kind row's sender (L562-564). Refuses if no proposal (L570), refuses if no signoff with "unsigned deploy refused" (L572-574), refuses if author seat == signer seat (L585-587). Only distinct seats pass. op_deploy calls it BEFORE any execute and returns 403 + writes a gate_violation provenance record on failure (L626-633). Verified the decision logic in isolation against 6 cases (real + synthetic): unsigned->refuse, self-sign->refuse, worker1/worker2->pass, same-lineage-distinct-seat->pass (correctly allows the normal two-worker case; an earlier draft's same-lineage refusal was removed, L580-581). Behaves exactly as designed.

## Check 2 — RAILWAY_TOKEN env-only, never hardcoded/logged: PASS
Token read only at execute time via os.environ.get("RAILWAY_TOKEN") (L675), passed to _railway_deploy as a param, used only in the Authorization Bearer header (L597). Grepped the file: the token never appears in any _prov_append, _ledger_*, or jsonify payload. Provenance/ledger records carry block_id/target/seats/outcome — never the token. Module note L520-521 states the rule explicitly. No leak path found.

## Check 3 — dry_run makes no real Railway call: PASS
dry_run=bool(b.get("dry_run")) (L617). On the dry_run branch (L657-661) the op runs the full two-party gate + the KEYS-2 bind + writes the deploy_authorized provenance record, then returns {ok,dry_run:true,authorized:true} BEFORE the execute block (L663+). _railway_deploy is unreachable on the dry_run path. So a test exercises every check with zero Railway side effect. Confirmed by control-flow read.

## Check 4 — provenance lifecycle logged: PASS
_prov_append (L527-537) appends JSONL to live/provenance_ledger.jsonl. The op records gate_violation (on refuse, L628 + L643), deploy_authorized (L652), and deploy_result ok/fail (L685/L680/L691). Combined with the proposal + signoff mailbox rows, the full proposal->signoff->deploy->result chain is captured — directly answering design line 307 (review findings evaporate -> capture them). Best-effort/never-blocks is acceptable for an audit log; INFERENCE (labeled): a dropped append weakens the audit trail but cannot cause a bad deploy, since the GATE (not the log) is the control. Acceptable.

## Check 5 — no injection/abuse path beyond the documented one: PASS (with the known caveat)
The only abuse path is the shared-key seat forgery: under one DIAG_KEY the author/signer seats are self-asserted body fields, so a single holder can present a distinct from_seat on a signoff and satisfy signer!=author (demonstrated in my isolation test, case 6). THIS IS NOT A HIDDEN FLAW — the module documents it loudly (L510-518, L582-584) and it is exactly SECAUDIT-1 Q1/Q3. worker1 also already wired the CLOSURE: KEYS-2's _authed_identity (L48-58) resolves identity from WHICH key called via file_server.authenticate_identity, and op_deploy adds a caller==signer bind (L635-649) that activates when _ident.authenticated is true — a third party then cannot trigger a deploy citing someone else's signoff. In shared-key mode that bind is skipped and the structural gate is the only guard, which the code flags (L637-639). So: structure correct now, unforgeable once per-identity keys are issued. No OTHER injection path found (target whitelisted main|farm|box L618; block_id required L620; SQL parameterized L560/L564; no eval/format-string into queries).

## Operational dependencies (NOT code defects — control needs these to deploy)
1. OP_ALLOWED: 'deploy' is NOT in the courier allowlist (live-confirmed: 15 ops, no deploy). The op is unreachable via /diag/op until control adds it — the intended post-signoff step. Correct safety posture.
2. PROPOSAL ROW REQUIRED: the gate keys on kind='proposal' for the author. worker1's original DEPLOYCHAIN-1 was a 'task' (now done), and I confirmed live there is no 'proposal' row for it — so a real deploy needs the authored change present as a 'proposal' row under the deploy's signoff_block_id, OR the gate's author-lookup widened to accept the originating 'task' kind. Flagging so control doesn't hit a "no proposal found" refusal at deploy time. INFERENCE (labeled): widening to ('proposal','task') in the author SELECT (L559) is the smaller change; either works.
3. RAILWAY env: RAILWAY_TOKEN / RAILWAY_SERVICE_ID_<TARGET> / RAILWAY_ENVIRONMENT_ID must be set or non-box deploys 503 (L678-683) — handled gracefully, just a prerequisite.

## My signoff action
Sent a kind='signoff' mailbox row for DEPLOYCHAIN-1 from worker2 (msg_id f88420c6) — the real two-party row the gate consumes. Author worker1 != signer worker2 -> gate would PASS on seat-distinctness once a matching proposal row exists (dependency #2).

## Persistence
Could not exercise /op/deploy live — not in the courier allowlist (by design, pre-signoff). Did not report blocked: validated the gate by (a) reproducing _twoparty_check's decision logic against real mailbox rows + synthetic edge cases, and (b) creating the real signoff row and re-checking the live rows. Said what I tried.
