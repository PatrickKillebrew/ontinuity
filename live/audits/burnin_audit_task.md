# DELEGATED TASK — Every-5th-Receipt Audit Ritual (read-only, does NOT touch the live farm)

## Why this is safe to run alongside the burn-in
The resident driver on the VPS owns the burn-in (it is the shepherd now). This task is READ-ONLY against the corpus via the diag query endpoint. It starts no sessions, drives nothing, and must never call /agent/start, /agent/queue_update, or any write path. It is pure verification. Do NOT become a second poller.

## The claim being tested
Ontinuity's headline credential is "zero false certifications" — that a session marked `complete` actually did the work its receipt claims, verifiable against its own execution log. The audit ritual checks this on a sample: re-derive each sampled receipt's claim against the recorded transcript/execution and confirm they match.

## Sampling
Every 5th receipt in the clean counted set (session_id >= '2026-06-08_0'): receipts at the 5th, 10th, 15th... position within the boundary. Read-only SELECTs only.

## Per-receipt check
For each sampled receipt:
1. Pull the session's recorded transcript and the receipt's stated outcome.
2. Confirm the claimed work (the DB_QUERY result the probe reported) actually appears in the execution log — i.e. the reported integer matches what the logged query returned. A clean DB_QUERY probe is ideal for this: the answer is checkable.
3. Confirm status bucket honesty: a `complete` receipt should show a certified close in its transcript, not a model-death or stop mislabeled.
4. Record: receipt_id, session_id, claim, log-evidence, MATCH / MISMATCH, and for any MISMATCH the exact divergence.

## Deliverable
A read-only audit table committed to live/audits/burnin_audit_pass1.md (repo write via commit is fine — that is durable record, not a live-system write). Columns: receipt_id, claim, evidence, verdict. Plus a one-line headline: N audited, M clean, K mismatches. Any mismatch is a finding, not a failure — it is exactly what the ritual exists to catch (receipt #50 precedent: the audit caught a fabricated absence the gates missed).

## Hard constraints
- READ-ONLY against the running system. Diag query endpoint only.
- No session starts. No driving. No second poller.
- Repo commits for the audit deliverable are fine (durable record).
- If the corpus is mid-write and a count looks inconsistent, note it and move on — do not retry-hammer the endpoint.
