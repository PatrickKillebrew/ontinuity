# Fix Proposal #2 — FOUNDATIONAL: persist the executed result (execution log)

**Status: DESIGN, not deployed. Operator review + sign-off (engine) and VPS hands (db.py + endpoint) required. All investigation read-only.**

## The gap, grounded
`record_execution` writes every real workspace execution into `active_session["execution_log"]` — `{cycle, kind, detail, status, result, at}`, where `result` is the actual output snippet the engine fed back (up to 2000 chars). This list is F.3's ground truth and is re-injected into the Challenger's context. But it is **purely in-memory**: initialized fresh each session (app.py:150, 2184), consumed live (F.3 at 900/1236/1300/1355/1902, Challenger context at 2512/2561), and **never included in `build_session_payload`**. db.py has no execution table. So at session close the log is discarded. That is why audit pass 1 had to reconstruct ground truth at each boundary rather than read the logged result — the "verifiable against its own execution log" credential has no persisted log.

## Design — persist execution_log as a queryable table
Mirror the proven `behavioral_observations` write path exactly (payload list → endpoint loop → db insert). Three coordinated edits:

### db.py (VPS hands) — new table + insert (drafted, syntax-checked)
```sql
CREATE TABLE IF NOT EXISTS session_executions (
    execution_id  TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id),
    user_id       TEXT,
    cycle_number  INTEGER,
    kind          TEXT,    -- db_query | code_test | search | citation
    detail        TEXT,    -- the query/command issued
    status        TEXT,    -- PASSED | FAILED | REFUSED
    result        TEXT,    -- the real output snippet the engine fed back
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_executions_session ON session_executions(session_id);
```
Plus `insert_session_execution(ex)` mirroring `insert_behavioral_observation` (drafted; full text in db_d36_draft).

### app.py engine (sign-off deploy) — payload carries the log
In `build_session_payload`'s return dict, beside `behavioral_observations`:
```python
"executions": [dict(e, session_id=session_id) for e in s.get("execution_log", [])],
```
This stamps `session_id` onto each in-memory entry (which already has cycle/kind/detail/status/result).

### workspace_db_endpoint.py (VPS hands) — insert loop
After the behavioral_observations loop:
```python
for ex in data.get("executions", []):
    ex["user_id"] = user_id
    db.insert_session_execution(ex)
```
and add `"executions_written": len(data.get("executions", []))` to the response.

## How audit pass 2 uses it
```sql
SELECT cycle_number, kind, detail, status, result
FROM session_executions WHERE session_id = ? AND kind='db_query' ORDER BY cycle_number;
```
The auditor reads the actual result the engine fed back and compares the Researcher's claimed integer directly against it — no boundary reconstruction. It also lets the audit verify FAILED/REFUSED executions and detect a claim citing a result never logged (the #117 class) by absence from this table.

## Honest limitation — forward-only
Past sessions' `execution_log`s are already discarded; they cannot be backfilled. This persistence is forward-only: pass 2 reads real logs for sessions run after deploy. For the existing burn-in corpus, the pass-1 reconstruction method remains the only verification path. If a re-run of the counted set under the persisted log is wanted for a fully-logged citation basis, that is a separate decision (re-running burns farm time and is not required to close this gap going forward).

## Choice point for operator
Dedicated table (above) vs. writing executions as `system`-role transcript turns (the schema already documents a `system` role). The table is cleaner for audit (structured `result` column, queryable, distinct from conversation) and is recommended. The system-turn route avoids a new table but embeds the result in free text and mixes execution records with the transcript. Recommend the table.

## Operator action required
1. Review the three edits and the table-vs-system-turn choice.
2. db.py + endpoint: apply on the VPS, restart the workspace endpoint (laptop/VPS copy — repo edit alone does not reach it).
3. app.py: deploy with the `Operator-Signoff` trailer.
4. Order: db.py/endpoint live before the engine starts emitting `executions`, else the endpoint drops the key (no harm, just no persistence) — same safe ordering as deploy 32.
5. Then a controlled verification session confirms a DB_QUERY's result lands in `session_executions`, and audit pass 2 reads it.

No deploy performed. No farm session run.
