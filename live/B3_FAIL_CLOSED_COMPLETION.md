# ONTINUITY 1.0 — B3 FAIL-CLOSED COMPLETION

**State:** IN PROGRESS — candidate implemented locally; not reviewed, pushed, or deployed

**Release condition:** RC-4 — Fail-closed completion

**Observed:** 2026-09-03

---

## 1. CLAIM UNDER TEST

No session may persist `complete` because a caller omitted a status, asserted a
status, exited the loop without certification, lost the Challenger, lost the
process, or failed to produce the work product. Completion must be earned by
recorded close evidence and accompanied by a durable reason.

---

## 2. CURRENT-SOURCE FINDINGS

The current engine already contained two important protections described in the
June burn-in proposals:

- a transcript-level `SESSION_END` close gate;
- `NO_REVIEW`/`unreviewed_cycles` recording for Challenger provider death.

The audit found four remaining seams:

1. Both database schemas declared `status DEFAULT 'complete'`.
2. Both database writers substituted `complete` when status was absent.
3. `end_reason` was not persisted.
4. SIGTERM and failed work-product extraction could still leave the completion
   sentinel intact.

These are persistence-boundary defects: the ordinary engine path could behave
correctly while another or interrupted path still manufactured a clean row.

---

## 3. CANDIDATE CHANGE

The candidate introduces one dependency-free completion classifier and applies
it twice:

- when the engine builds the session payload;
- when the workspace endpoint receives that payload.

The workspace therefore does not trust a caller's `complete` assertion. It
requires a `SESSION_END` transcript tag and refuses completion if any
`NO_REVIEW` tag or unreviewed cycle exists.

Additional changes:

- fresh schemas default to `in_progress`;
- existing schemas receive `end_reason` through an additive migration;
- database triggers reject any inserted or updated `complete` row whose reason
  is not exactly `certified_close`, including on legacy schemas whose original
  column default cannot be altered additively;
- database writers fall back to `in_progress`, never `complete`;
- SIGTERM records `incomplete_terminated / process_terminated` before flushing;
- failed work-product extraction records
  `incomplete_missing_extraction / work_product_extraction_failed` before the
  workspace write;
- provider failures retain a structured cause instead of requiring later
  inference from error strings: timeout, malformed response, rate limit,
  configuration, and generic provider failure are distinguished;
- successful Anthropic and Gemini responses with empty or whitespace-only text
  are rejected in their provider adapters and recorded as malformed responses;
- a Researcher timeout or malformed response receives its own incomplete status;
  Challenger failures retain the integrity status
  `incomplete_challenger_dead` while `end_reason` records the specific cause;
- root and `live` database/endpoint copies move together in this work block.

No historical session row is rewritten by this candidate.

---

## 4. MUSEUM RESULT

Fifteen local test methods pass:

- certified close;
- requested completion without close;
- missing status;
- Challenger death followed by a later close;
- durable `NO_REVIEW` evidence;
- Researcher death;
- operator stop;
- timeout status;
- malformed-response status;
- Anthropic empty-output rejection;
- Gemini empty-output rejection;
- missing-extraction status;
- fresh-schema default and `end_reason` presence;
- existing-schema additive migration;
- database-writer missing-status behavior.

The list contains more behaviors than test methods because the named terminal
outcomes are exercised as subtests in one museum test.

Commands:

```text
python -m unittest discover -s tests -v
python -m py_compile app.py completion.py db.py workspace_db_endpoint.py live/completion.py live/db.py live/workspace_db_endpoint.py
git diff --check
```

Result: PASS locally.

---

## 5. WHAT THIS DOES NOT YET PROVE

B3 is not complete. The candidate still needs:

- independent review of the exact bytes;
- an endpoint-level integration specimen with Flask dependencies installed;
- a decision on whether a Challenger death should continue-but-disqualify or
  terminate immediately;
- authenticated installation of the matching box files;
- a controlled live run confirming the new database column and persisted
  reasons;
- deployment by a seat that did not author these bytes.

The current tests prove the classifier, clean-schema behavior, additive column
migration, and writer default. They do not claim a production deployment.

---

## 6. WORK-BLOCK CLOSE

- **Claim tested:** can completion be made an earned, redundantly checked state
  rather than a storage default?
- **Evidence read:** current `app.py`, both `db.py` copies, both workspace
  endpoints, burn-in fix proposals 1 and 4, and the 1.0 release board.
- **Change made:** fail-closed classifier, persisted reason, safe defaults,
  termination/extraction outcomes, and museum tests.
- **Test result:** PASS locally (10 test methods/specimens plus compilation and
  diff validation).
- **New debt:** none hidden; outstanding integration and runtime distinctions
  are listed above.
- **State left:** local candidate only; no production configuration, database,
  Railway service, box install, or deployment changed.
- **Next dependency:** independent review, then timeout/malformed runtime
  differentiation and endpoint integration test before deployment authorization.
