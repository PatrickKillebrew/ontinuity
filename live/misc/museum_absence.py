#!/usr/bin/env python3
"""Museum: evidence-of-absence discipline (deploy 31, receipt-#50 lesson).
Pure-function specimens against find_undisciplined_absence_claims.
Known limit (d26->d27 lesson): stubbed tests cannot see state-WIRING gaps —
the live acceptance session covers the wiring."""
import importlib.util, sys

spec = importlib.util.spec_from_file_location("app31", "/home/claude/app_d31.py")
# Import only the function + patterns without running Flask: exec the relevant slice.
src = open("/home/claude/app_d31.py").read()
start = src.index("ABSENCE_CLAIM_PATTERN")
end = src.index("def contract_close_check():")
ns = {}
exec("import re\n" + src[start:end], ns)
f = ns["find_undisciplined_absence_claims"]

specimens = [
    # 1. Receipt #50 verbatim conclusion — THE specimen. No scope line. -> GATED
    ("No farm-suffixed session exists in the database.", 1, "no-scope"),
    # 2. Scoped absence: query quoted, claim stays inside the column searched. -> PASS
    ("The query `SELECT session_id FROM sessions WHERE objective LIKE '%farm%'` returned 0 rows; no session with 'farm' in the objective column was found.", 0, None),
    # 3. Query quoted but claim generalizes database-wide. -> GATED (generalizer)
    ("`SELECT session_id FROM sessions WHERE objective LIKE '%farm%'` returned 0 rows, so no farm session exists anywhere in the database.", 1, "generalizes"),
    # 4. Wide claim explicitly ASSUMED. -> PASS
    ("ASSUMED: no farm-suffixed session exists in the database (only the objective column was searched).", 0, None),
    # 5. Positive claim, untouched. -> PASS
    ("The count of session_transcripts rows for role model_a is 189 and the ratio is 2.05.", 0, None),
    # 6. Researcher narrating its own failed query — scoped by backtick. -> PASS
    ("The previous query failed because the column `session_name` does not exist.", 0, None),
    # 7. Bare negative finding with no query. -> GATED (no scope)
    ("No matching rows were found.", 1, "no-scope"),
    # 8. Receipt #50 full Result block, multi-line: evidence bullet passes, conclusion gated.
    ("""- Evidence of Absence: The query `SELECT session_id, start_time FROM sessions WHERE objective LIKE '%farm%' ORDER BY start_time DESC LIMIT 1` returned 0 rows.
- Conclusion: No farm-suffixed session exists in the database. Consequently, no model identifier can be retrieved for the Researcher seat of such a session.""", 2, "conclusion-pair"),
    # 9. F.3-negation style honest statement — not an absence-of-data claim shape we gate. -> PASS
    ("The metric could not be verified and is recorded as UNMEASURED.", 0, None),
    # 10. Cannot-be-found without scope. -> GATED
    ("The model identifier cannot be retrieved from the records.", 1, "no-scope"),
    # 11. Session-52 verbatim: 'does not contain' shape, no scope line. -> GATED
    ("The database does not contain a table named unicorn_registry.", 1, "no-scope"),
    # 12. Same claim carrying its scope. -> PASS
    ("The query `SELECT name FROM sqlite_master WHERE type='table' AND name='unicorn_registry'` returned 0 rows; the database contains no table by that name.", 0, None),
]

fails = 0
for i, (text, expect_n, note) in enumerate(specimens, 1):
    got = f(text)
    ok = len(got) == expect_n
    status = "PASS" if ok else "FAIL"
    if not ok:
        fails += 1
    print(f"specimen {i}: {status} (expected {expect_n} flags, got {len(got)})")
    for g in got:
        print(f"    - {g['sentence'][:90]} :: {g['reason'][:60]}")
print(f"\n{len(specimens) - fails}/{len(specimens)} specimens pass")
sys.exit(1 if fails else 0)
