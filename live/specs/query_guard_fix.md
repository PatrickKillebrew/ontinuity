# PROPOSAL — QGUARD-1: literal-aware SQL query guard (semicolon false-positive fix)

*Status: PROPOSE-ONLY (engine-side, app.py db_query_guard, WATCHED path — operator applies + deploys). Authored by worker1 (claude:opus-4.8). Grounded in db_query_guard read live from app.py via /op/read_repo (READREPO-1 deployed).*

## THE BUG (exact location + cause)
db_query_guard (app.py ~1161) rejects multi-statement injection with a naive check:
```
s = (sql or "").strip().rstrip(";").strip()
...
if ";" in s:
    return False, "multiple statements not allowed"
```
`";" in s` flags ANY semicolon — including one INSIDE a quoted string literal. After rstrip strips a single trailing terminator, an interior `;` in a literal (e.g. `WHERE objective = 'fix; deploy'`) still trips the guard. A legitimate read-only SELECT whose literal contains a semicolon is wrongly REFUSED. This is the phantom-multi-statement false-positive.

## THE FIX (literal-aware scan; still blocks real injection)
Replace the naive `;` check with a scanner that ignores semicolons inside single/double-quoted literals (handling SQL's doubled-quote escape `''`), and still flags a real statement-separating `;`.

PATCH — app.py, add the helper above db_query_guard and swap the one line:
```
# ADD (above db_query_guard ~1161):
def _has_unquoted_semicolon(s):
    """True iff s has a ; OUTSIDE any quoted literal. Handles the '' escaped quote."""
    i, n = 0, len(s); in_single = in_double = False
    while i < n:
        ch = s[i]
        if in_single:
            if ch == "'":
                if i+1 < n and s[i+1] == "'": i += 2; continue
                in_single = False
        elif in_double:
            if ch == '"':
                if i+1 < n and s[i+1] == '"': i += 2; continue
                in_double = False
        else:
            if ch == "'": in_single = True
            elif ch == '"': in_double = True
            elif ch == ";": return True
        i += 1
    return False

# CHANGE (inside db_query_guard):
#   OLD:  if ";" in s:
#   NEW:  if _has_unquoted_semicolon(s):
```
Everything else in db_query_guard is unchanged. The SELECT-only check, length cap, and write-keyword refusal still apply.

## BEFORE / AFTER TEST CASES (all verified locally against the proposed code)
PASS (read-only SELECT, must be ALLOWED) — these were wrongly REFUSED before the fix:
- `SELECT * FROM t WHERE name = 'a;b'`  -> now PASS
- `SELECT * FROM t WHERE x = 'it''s; fine'`  (escaped quote + ; in literal) -> now PASS
- `SELECT model_c_string FROM sessions WHERE objective = 'fix; deploy'` -> now PASS
- `SELECT ';'`  and  `SELECT * FROM t WHERE a=';' AND b=';'`  -> now PASS
- `SELECT * FROM t WHERE n = "a;b"`  (double-quoted) -> now PASS

FAIL (real injection / multi-statement, must STILL be REFUSED) — unchanged:
- `SELECT 1; SELECT 2`  -> FAIL "multiple statements not allowed"
- `SELECT * FROM t WHERE c='x'; DROP TABLE t`  -> FAIL "multiple statements not allowed"
- `SELECT * FROM t WHERE a=';' ; SELECT 2`  (literal ; then a REAL ;) -> FAIL
- `DROP TABLE sessions`  -> FAIL "only SELECT statements are allowed"

## SAME-CLASS BUG FOUND (optional add-on, flagged — not in QGUARD-1's stated scope)
The write-keyword check has the IDENTICAL literal-blindness: `if any(w in low for w in forbidden[3:])` is a naked substring match, so a benign literal like `WHERE note = 'please delete this'` trips on "delete" and is wrongly REFUSED. The same literal-aware technique fixes it: scan the SQL with literal CONTENT blanked out, then keyword-check the skeleton.
```
# OPTIONAL helper + swap:
def _strip_literals(s):
    out=[]; i,n=0,len(s); in_s=in_d=False
    while i<n:
        ch=s[i]
        if in_s:
            if ch=="'":
                if i+1<n and s[i+1]=="'": out.append("  "); i+=2; continue
                in_s=False; out.append("'")
            else: out.append(" ")
        elif in_d:
            if ch=='"':
                if i+1<n and s[i+1]=='"': out.append("  "); i+=2; continue
                in_d=False; out.append('"')
            else: out.append(" ")
        else:
            if ch=="'": in_s=True; out.append("'")
            elif ch=='"': in_d=True; out.append('"')
            else: out.append(ch)
        i+=1
    return "".join(out)
# then keyword/PRAGMA checks run against _strip_literals(low) instead of low.
```
Verified: `'please delete this'` literal -> skeleton has no "delete" -> PASSES; `SELECT * FROM t; DELETE FROM t` -> skeleton keeps "delete" -> still FAILS. RECOMMENDATION: apply this too — it's the same root cause and the same false-positive class the punch-list item names ("phantom-SQL / over-trigger"), and leaving it half-fixed means literals with words like delete/update/create still false-positive. But it is strictly more change than the semicolon line, so it is your call whether to bundle it.

## WHERE IT GOES
Engine app.py db_query_guard, a WATCHED path. Operator: /diag/engine check (never during a live session), apply the patch(es), commit with Assisted-by trailer, deploy. PROPOSE-ONLY — no deploy from this file. Staged at live/specs/query_guard_fix.md.

## PERSISTENCE-RULE TRAIL
Read db_query_guard from the live app.py via /op/read_repo (the op I built last block, now deployed). All test cases run locally against the proposed code before staging.
