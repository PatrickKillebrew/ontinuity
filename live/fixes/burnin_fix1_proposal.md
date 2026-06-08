# Fix Proposal #1 — Citation Blocker: uncertified sessions writing `complete`

**Status: PROPOSED, not deployed. Operator review + sign-off trailer required before deploy. No live-system writes were made; all investigation read-only via the diag endpoint.**

## What the audit flagged vs what it actually is
Audit pass 1 flagged #87 and #147 as `complete` sessions that shouldn't be. Investigation refined this:
- **#87 (02:56) is pre-d34** — it ran before the status-bucket mechanism existed, when `complete` was hardcoded. Not an uncovered live path; a pre-fix artifact.
- **SIGTERM hypothesis tested and rejected as the cause.** A deploy-killed session flushes via the SIGTERM handler, which writes without setting `end_status` → would land `complete`. But a SIGTERM kill skips the end-sequence, so its signature is `complete` with zero knowtext/artifacts. **Zero** sessions in the corpus match that signature — so the SIGTERM path, though a real latent gap, did not contaminate this run.
- **The real class:** post-d34, **5 of 74** `complete` sessions carry **no SESSION_END tag from either model** anywhere in the transcript. They exit the loop on ALIGNMENT_NEEDED, a lone DB_QUERY, or an untagged turn, yet write `complete`. These are uncertified completions — the adversarial pair never certified the close — and they pollute the burn-in outcome ratio, blocking citation.

The 5: `2026-06-08_16-01-17`, `16-01-23`, `16-24-43`, `17-19-31`, `17-26-35`. The other 69 all carry a SESSION_END signal (legitimate, including F.1 closes on the Challenger's assessment).

## The fix (two parts)

### Part A — certified-close outcome gate (the actual #1 fix)
In `build_session_payload`, a session may be written `complete` only if its transcript contains a certified-close signal (a `SESSION_END` tag from Researcher or Challenger). Otherwise it writes the honest bucket `incomplete_no_close`. Death/stopped/terminated statuses are left untouched. This gates the **outcome** on evidence of certification, so it catches all 5 regardless of how the loop exited — no need to pin every upstream exit path.

```python
"status": (
    s.get("end_status", "complete")
    if s.get("end_status", "complete") != "complete"
    or any(extract_tag(t.get("content", "")) == "SESSION_END"
           for t in s.get("transcript", []))
    else "incomplete_no_close"
),
```

**Corpus validation:** applied to the 74 post-d34 `complete` sessions, the gate reclassifies exactly the 5 uncertified ones and passes the 69 certified ones — (5 reclassify, 69 pass), matching the manual finding to the digit.

### Part B — SIGTERM flush status (defensive; latent gap, did not fire this run)
The SIGTERM graceful-shutdown handler flushes a mid-flight session without setting `end_status`. It didn't fire in this corpus, but it is a real hole: a deploy that lands while a farm session is running would write `complete`. Mark a running, non-finalizing SIGTERM kill as `incomplete_terminated` before flushing (don't overwrite a status the end-sequence already set):

```python
if active_session.get("running") and not active_session.get("finalizing") \
   and active_session.get("end_status", "complete") == "complete":
    active_session["end_status"] = "incomplete_terminated"
```

## Backfill for the 5 already-written rows (operator hands)
The 5 existing rows still read `complete` and pollute the ratio until reclassified. Deterministic, derived read-only from the corpus:
```sql
UPDATE sessions SET status='incomplete_no_close'
WHERE status='complete' AND session_id >= '2026-06-08_12-53'
AND (SELECT COUNT(*) FROM session_transcripts t
     WHERE t.session_id=sessions.session_id AND t.tag='SESSION_END')=0;
-- expected: 5 rows
```

## Verification plan
- Pre-deploy: corpus validation above (done — 5/69).
- Post-deploy (operator): a controlled verification session on the free farm (logged as verification, not burn-in) confirms a normal SESSION_END close still writes `complete` (no regression). Reproducing `incomplete_no_close` live requires an uncertified exit, which is non-deterministic; the gate is validated by corpus + inspection.

## Operator action required
1. Review Parts A and B.
2. Deploy app.py with the `Operator-Signoff` trailer (self-enforcing gate still queued).
3. Run the backfill SQL on the VPS (expected 5 rows).
4. Re-run audit pass 2 against the cleaned corpus.

## Notes toward #2
`record_execution` already captures the real executed query result into `active_session["execution_log"]` in memory (it feeds F.3). The persistence gap in #2 is that this list is not written to the DB — there is no execution-log table and no `system`/result transcript turn. Persisting `execution_log` (a new table or as system turns) is the natural #2 design; drafting separately.
