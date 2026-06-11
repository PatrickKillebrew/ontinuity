# PROPOSAL — CYCLENUM-1: stamp the engine cycle onto injected results (cite-by-coordinate fix)

*Status: PROPOSE-ONLY (engine-side, app.py, WATCHED path — operator applies + deploys). Authored by worker1 (claude:opus-4.8) under CYCLENUM-1. Grounded in app.py read live via /op/read_repo (READREPO-1 is deployed and working — used it to read the 216KB app.py). Addresses receipt #22 erratum: a Researcher citing an injected result by a GUESSED cycle coordinate instead of a real one.*

## WHAT I FOUND (two parts — one already done, one is the real fix)

### Already present: the turn ENVELOPE carries the cycle
The external-mailbox turn payload already includes the engine cycle. `external_mailbox` holds a `cycle` field (app.py ~1705), set each turn from `active_session.get("cycle", 0)` (~1720), and GET /mailbox/turn already RETURNS it to the external agent (~3240: `"cycle": external_mailbox["cycle"]`). So the envelope-level cycle the block asks for is ALREADY plumbed end to end. No change needed there.

### The actual gap: injected RESULTS carry no cycle coordinate
Every result injected into the Researcher's conversation — `[SEARCH RESULT]`, `[SEARCH RESULTS — RAW]`, `[CITATION VERIFICATION]`, `[DB_QUERY RESULT]`, `[CODE_TEST RESULT]`, `[PARIETAL RULING]`, `[CHALLENGE ADJUDICATED]`, etc. (30+ append sites, app.py ~2335-2936) — is suffixed with `{ambient_line}` and nothing else. `ambient_line` comes from `get_ambient_signal_line(signal)` (~1645), which returns ONLY `AMBIENT_SIGNAL: <n> (<label>)` — NO cycle. So an injected result lands with zero cycle coordinate. When the Researcher later cites "the search result from cycle 3," there is no real coordinate on the injected item to cite — so it guesses. That guess is the fabrication class of receipt #22.

The envelope cycle (current turn) is not enough: a Researcher needs to cite WHICH cycle a specific injected result arrived in, and that per-item stamp does not exist today.

## THE FIX (surgical, one function + one call site, back-compatible)
Stamp the cycle into `ambient_line`. Because EVERY injection appends `ambient_line`, doing it in that one place stamps all 30+ injection sites at once — no need to touch each append.

EDIT 1 — app.py ~1645, add a cycle parameter to the helper:
```
# OLD
def get_ambient_signal_line(signal):
    labels = {0: "clear", 1: "nominal", 2: "caution", 3: "warning", 4: "override"}
    return f"AMBIENT_SIGNAL: {signal} ({labels.get(signal, 'unknown')})"
# NEW
def get_ambient_signal_line(signal, cycle=None):
    labels = {0: "clear", 1: "nominal", 2: "caution", 3: "warning", 4: "override"}
    coord = f"CYCLE: {cycle} | " if cycle is not None else ""
    return f"{coord}AMBIENT_SIGNAL: {signal} ({labels.get(signal, 'unknown')})"
```

EDIT 2 — app.py ~2317, pass the cycle (it is already in scope; it is used one line above at ~2312):
```
# OLD
        ambient_line = get_ambient_signal_line(signal)
# NEW
        ambient_line = get_ambient_signal_line(signal, active_session["cycle"])
```

Result: every injected result line becomes e.g. `CYCLE: 3 | AMBIENT_SIGNAL: 2 (caution)`, so each injected item now carries the real cycle it arrived in. The Researcher cites the coordinate it is given instead of inventing one. The `cycle=None` default keeps the helper back-compatible (the other caller, the function def at ~1645, is the only def; the single live call site is ~2317).

## WHY ONLY THESE TWO LINES (not each append site)
Every injection already appends `ambient_line`; centralizing the cycle there is the minimal, lowest-drift change. Editing 30+ append f-strings individually would be error-prone and would have to be re-done for every future injection type. One helper + one call site covers all current and future injections.

## OPTIONAL HARDENING (flag, not in this minimal fix)
If you want the Researcher's CITATIONS validated against the real coordinate (not just supplied it), a follow-up could check that a cited cycle number exists in the session's injected-result history (a deterministic F.3-style audit, the same shape as the execution-claim audit). That turns "supplied a real coordinate" into "rejected a fabricated coordinate." Out of scope for CYCLENUM-1's minimal fix; noted as the natural next step that closes the class fully.

## TEST (describe + local proof)
- Local proof done: the NEW `get_ambient_signal_line` was run for (signal=2,cycle=3)->`CYCLE: 3 | AMBIENT_SIGNAL: 2 (caution)`, (0,0)->`CYCLE: 0 | ...`, and (1, omitted)->`AMBIENT_SIGNAL: 1 (nominal)` (back-compat). Logic verified.
- Live test after deploy (operator): run one session that triggers a SEARCH or DB_QUERY injection; GET /mailbox/turn (or the transcript) should show the injected `[SEARCH RESULT]` block's ambient line now prefixed `CYCLE: <n> |` matching the engine cycle at injection time. Cross-check that `<n>` equals `external_mailbox["cycle"]` / `active_session["cycle"]` at that moment.

## WHERE IT GOES
Engine-side, app.py, a WATCHED path. Operator applies the two edits, runs the /diag/engine check (never commit during a live session), commits with the Assisted-by trailer, and deploys. PROPOSE-ONLY here — no deploy from this file.
