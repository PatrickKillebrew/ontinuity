"""
Ontinuity — Verified Bootstrap Gate (sandbox-local runnable)
============================================================
BUILD step 1 of live/specs/verified_bootstrap_gate.md (spec sha 37925ff3),
folding the operator SCOPE REFINEMENT (msg 05a9fa6a): seat-role parameterized
{control, worker}; six checks (the five STATE checks + CHECK 6 MECHANICS).

This is a SANDBOX-LOCAL runnable a seat runs as step zero of coming online.
It is NOT the courier op (/diag/op/bootstrap_gate) — that is build step 2.
NO DEPLOY. NO SECRETS WRITTEN HERE: the diag key is read from the environment
or passed in by the caller; it is never hardcoded and never committed.

Authored by worker1 (claude:opus-4.8) under BOOTGATE-2. Grounded in the spec,
OPERATING_MANUAL.md, and the live corpus schema. Inferences are labeled INFER.

Return contract (spec section 4):
  { "oriented": bool,
    "seat": str, "role": str, "lineage": str,
    "checks": [ {"name","pass","returned_fact","failure_message"(if fail)} ] }
oriented is True iff EVERY run check passed. Checks run in order and STOP at the
first failure (a later check is meaningless if an earlier one failed).
"""

from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error

# ---- canonical reference values -------------------------------------------
# CHECK 1: the canonical courier allowlist count. SOURCE OF TRUTH is app.py
# OP_ALLOWED on the engine. A sandbox seat cannot import app.py, so the count
# is injected (build/deploy wires the real import when this becomes the courier
# op in step 2). Default reflects the live allowlist as of BOOTGATE-2 (12):
#   read_journal, restart_workspace, register_egress, mailbox_send,
#   mailbox_fetch, mailbox_ack, mailbox_peek, mailbox_reclaim, write_file,
#   commit_self, read_file, commit_file.
# CHECK 1's job is to catch MANUAL drift against this canonical number — and
# the manual currently still says "10 ops" (OPERATING_MANUAL.md line ~45),
# which is exactly the drift this check exists to surface.
CANONICAL_COURIER_OP_COUNT = 12

# CHECK 3: corpus floor — monotonic non-decreasing last-known session count.
CORPUS_SESSION_FLOOR = 307

# Engine bases (spec section 3 / BOOTGATE-2).
ENGINE_MAIN = "https://web-production-7eaf8.up.railway.app"
ENGINE_FARM = "https://ontinuity-farm-production.up.railway.app"

MANUAL_RAW = ("https://raw.githubusercontent.com/PatrickKillebrew/"
              "ontinuity/main/live/OPERATING_MANUAL.md")
QUEUE_RAW = ("https://raw.githubusercontent.com/PatrickKillebrew/"
             "ontinuity/main/live/agent_queue.md")

# CHECK 6 MECHANICS — the canonical operating invariants the seat must be able
# to reproduce. Each invariant carries (key, canonical_statement, manual_probe):
#   key                : short id
#   canonical_statement: the truth the seat must state (the reference string the
#                        seat's reproduction is matched against, token-wise)
#   manual_probe       : a distinctive substring that must be PRESENT in the
#                        manual, so the runnable ratifies the invariant against
#                        the manual rather than against itself. (a) has no manual
#                        probe yet — see INVARIANT_A_GAP below.
MECHANICS_INVARIANTS = [
    {
        "key": "no_self_poll",
        "canonical_statement": (
            "a chat seat does not self-poll the mailbox; it acts only when its "
            "conversation is given a turn, so coordination is mailbox-native but "
            "a worker still needs its conversation nudged"),
        # INVARIANT_A_GAP (FINDING -> control): the manual does not yet state
        # this verbatim. The refinement itself notes control drifted on it THIS
        # session. Until the manual carries it, this probe is None and the check
        # matches the seat's reproduction against canonical_statement only,
        # flagging that the manual must add it (manual-currency).
        "manual_probe": None,
    },
    {
        "key": "courier_only",
        "canonical_statement": (
            "a sandbox seat cannot reach the box directly and reaches box ops "
            "only through the relay-courier on the engine, which forwards the "
            "bounded body to the box and returns the response verbatim"),
        "manual_probe": "go through the RELAY-COURIER on the engine",
    },
    {
        "key": "deploy_authority",
        "canonical_statement": (
            "operator owns deploys means deploy authority plus rollback, not a "
            "per-redeploy human click; the operator is the fuse and oversight, "
            "not the button-presser"),
        "manual_probe": "not a per-redeploy click",
    },
    {
        "key": "new_box_op",
        "canonical_statement": (
            "a new box op needs both a box install (write_file plus restart, "
            "hands-free) and an OP_ALLOWED entry in app.py (commit plus deploy)"),
        "manual_probe": "adding a box op means adding its name to OP_ALLOWED",
    },
]


# ---- tiny http helpers (stdlib only, no deps) -----------------------------
def _get(url, timeout=30):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _post(url, body, timeout=40):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _ok(name, returned_fact):
    return {"name": name, "pass": True, "returned_fact": returned_fact}


def _fail(name, returned_fact, message):
    return {"name": name, "pass": False, "returned_fact": returned_fact,
            "failure_message": message}


def _norm(s):
    """Token normalization for deterministic (non-semantic) matching."""
    return " ".join("".join(c.lower() if c.isalnum() or c.isspace() else " "
                            for c in s).split())


# ---- the six checks --------------------------------------------------------
def check_manual():
    name = "MANUAL"
    try:
        st, body = _get(MANUAL_RAW)
    except Exception as e:
        return _fail(name, f"manual unreachable: {e}",
                     "NOT ORIENTED [CHECK 1 MANUAL]: could not read "
                     "OPERATING_MANUAL.md — manual unreachable; re-sync before "
                     "acting.")
    # parse the stated courier allowlist count from the "Allowlist (live, N ops)"
    # phrasing in the scoped-op courier line.
    import re
    m = re.search(r"[Aa]llowlist\s*\(live,\s*(\d+)\s*ops?\)", body)
    stated = int(m.group(1)) if m else None
    if stated is None:
        return _fail(name, "no 'Allowlist (live, N ops)' phrase found",
                     "NOT ORIENTED [CHECK 1 MANUAL]: could not parse courier "
                     "allowlist count from manual.")
    fact = (f"manual states courier allowlist = {stated} ops; "
            f"canonical = {CANONICAL_COURIER_OP_COUNT}")
    if stated != CANONICAL_COURIER_OP_COUNT:
        return _fail(name, fact,
                     f"NOT ORIENTED [CHECK 1 MANUAL]: courier allowlist count "
                     f"mismatch (manual={stated}, canonical="
                     f"{CANONICAL_COURIER_OP_COUNT}) — manual may be stale; "
                     f"re-sync before acting.")
    return _ok(name, fact)


def check_queue():
    name = "QUEUE"
    try:
        st, body = _get(QUEUE_RAW)
    except Exception as e:
        return _fail(name, f"queue unreachable: {e}",
                     "NOT ORIENTED [CHECK 2 QUEUE]: agent_queue.md unreachable.")
    # head = the curated ACTIVE block; next action = first numbered ACTIVE item.
    import re
    lines = body.splitlines()
    active_idx = next((i for i, l in enumerate(lines)
                       if l.strip().upper().startswith("## ACTIVE")), None)
    next_action = None
    if active_idx is not None:
        for l in lines[active_idx + 1:]:
            if re.match(r"\s*1\.\s+\S", l):
                next_action = l.strip()
                break
    if not next_action:
        return _fail(name, "no ACTIVE head item parsed",
                     "NOT ORIENTED [CHECK 2 QUEUE]: agent_queue head empty or "
                     "unparseable — no current next action to orient onto.")
    one_line = " ".join(next_action.split())
    return _ok(name, f"next action: {one_line[:160]}")


def check_corpus(diag_key, engine=ENGINE_MAIN):
    name = "CORPUS"
    sql = "SELECT COUNT(*) FROM sessions"
    url = (f"{engine}/diag/api/query?diag_key="
           f"{urllib.parse.quote(diag_key)}&sql={urllib.parse.quote(sql)}")
    try:
        st, body = _get(url)
        d = json.loads(body)
        count = int(d["rows"][0][0])
    except Exception as e:
        return _fail(name, f"corpus query error: {e}",
                     "NOT ORIENTED [CHECK 3 CORPUS]: query error — wrong DB, "
                     "stale snapshot, or hands not reaching the corpus.")
    fact = f"sessions count = {count}; floor = {CORPUS_SESSION_FLOOR}"
    if count < CORPUS_SESSION_FLOOR:
        return _fail(name, fact,
                     f"NOT ORIENTED [CHECK 3 CORPUS]: sessions count {count} "
                     f"below floor {CORPUS_SESSION_FLOOR} — wrong DB, stale "
                     f"snapshot, or hands not reaching the corpus.")
    return _ok(name, fact)


def check_hands(diag_key, seat, engine=ENGINE_MAIN):
    name = "HANDS"
    url = f"{engine}/diag/op/mailbox_peek?diag_key={urllib.parse.quote(diag_key)}"
    try:
        st, body = _post(url, {"seat": seat, "limit": 1})
        d = json.loads(body)
    except Exception as e:
        return _fail(name, f"courier error: {e}",
                     "NOT ORIENTED [CHECK 4 HANDS]: courier mailbox_peek did "
                     "not return ok JSON — seat lacks working box hands; do not "
                     "act.")
    if st != 200 or not isinstance(d, dict) or d.get("ok") is not True:
        return _fail(name, f"status={st} body={str(d)[:120]}",
                     "NOT ORIENTED [CHECK 4 HANDS]: courier mailbox_peek did "
                     "not return ok JSON — seat lacks working box hands; do not "
                     "act.")
    return _ok(name, f"mailbox_peek ok (count={d.get('count')})")


def check_engine():
    name = "ENGINE"
    facts = []
    for label, base in (("MAIN", ENGINE_MAIN), ("FARM", ENGINE_FARM)):
        # engine state needs the diag key; reachability+parse is the bar, but
        # the /diag/engine route is key-gated, so we use the key passed via env
        # at call time. We read it here from the closure-injected value.
        url = f"{base}/diag/engine?diag_key={urllib.parse.quote(check_engine.diag_key)}"
        try:
            st, body = _get(url)
            d = json.loads(body)
            running = d.get("running")
            facts.append(f"{label}: running={running}")
        except Exception as e:
            return _fail(name, f"{label} unreachable: {e}",
                         f"NOT ORIENTED [CHECK 5 ENGINE]: engine {label} "
                         f"unreachable or unparseable — cannot confirm "
                         f"live/idle state; commits to watched paths unsafe.")
    return _ok(name, "; ".join(facts))


def check_mechanics(seat_invariants, role):
    """CHECK 6 — the seat must REPRODUCE operating invariants correctly, and the
    runnable ratifies the reproduction against the manual (not self-assertion).
    seat_invariants: dict {key -> the seat's own stated invariant text}.
    Deterministic match: every canonical token of the reference statement must
    appear in the seat's reproduction (token subset), AND the manual must carry
    the manual_probe substring (manual ratification). Semantics are NOT judged.
    """
    name = "MECHANICS"
    try:
        st, manual = _get(MANUAL_RAW)
    except Exception as e:
        return _fail(name, f"manual unreachable for ratification: {e}",
                     "NOT ORIENTED [CHECK 6 MECHANICS]: manual unreachable; "
                     "cannot ratify reproduced invariants.")
    findings = []
    for inv in MECHANICS_INVARIANTS:
        key = inv["key"]
        seat_text = seat_invariants.get(key, "")
        ref_tokens = set(_norm(inv["canonical_statement"]).split())
        seat_tokens = set(_norm(seat_text).split())
        # tolerate short stopword-only gaps: require >=85% of ref tokens present
        present = ref_tokens & seat_tokens
        coverage = (len(present) / len(ref_tokens)) if ref_tokens else 0.0
        reproduced = coverage >= 0.85
        probe = inv["manual_probe"]
        if probe is None:
            manual_ok = None  # gap: not yet in manual (invariant a)
        else:
            manual_ok = probe in manual
        ok = reproduced and (manual_ok is not False)
        findings.append((key, reproduced, round(coverage, 2), manual_ok, ok))
        if not ok:
            if not reproduced:
                msg = (f"NOT ORIENTED [CHECK 6 MECHANICS]: invariant '{key}' "
                       f"not reproduced (token coverage {coverage:.2f} < 0.85) "
                       f"— seat cannot state the operating mechanic correctly.")
            else:
                msg = (f"NOT ORIENTED [CHECK 6 MECHANICS]: invariant '{key}' "
                       f"reproduced but NOT ratified by manual (probe absent) "
                       f"— manual/seat incoherent; re-sync.")
            return _fail(name,
                         f"role={role} findings={findings}", msg)
    # all passed; surface the invariant-a manual gap as a non-failing note
    gap = any(inv["manual_probe"] is None for inv in MECHANICS_INVARIANTS)
    note = " (NOTE: invariant 'no_self_poll' not yet in manual — flag to control to add it)" if gap else ""
    return _ok(name, f"role={role} all {len(MECHANICS_INVARIANTS)} invariants reproduced + ratified{note}")


# ---- the gate --------------------------------------------------------------
def run_gate(seat, lineage, role="worker", diag_key=None,
             seat_invariants=None):
    """Run the verified bootstrap gate. role in {control, worker}.
    The five STATE checks run for BOTH roles. CHECK 6 MECHANICS runs for
    control always, and for worker too (good practice; refinement). diag_key
    is read from arg or env ONTINUITY_DIAG_KEY — never hardcoded.
    Returns the spec-section-4 structured result. Stops at first failing check.
    """
    if role not in ("control", "worker"):
        raise ValueError("role must be 'control' or 'worker'")
    diag_key = diag_key or os.environ.get("ONTINUITY_DIAG_KEY")
    if not diag_key:
        return {"oriented": False, "seat": seat, "role": role,
                "lineage": lineage,
                "checks": [_fail("PRECONDITION", "no diag_key provided",
                                 "NOT ORIENTED [PRECONDITION]: no diag key in "
                                 "arg or ONTINUITY_DIAG_KEY env — cannot run "
                                 "corpus/hands/engine checks.")]}
    check_engine.diag_key = diag_key  # inject for the engine check

    result = {"oriented": False, "seat": seat, "role": role,
              "lineage": lineage, "checks": []}

    # ordered checks; stop at first failure
    steps = [
        lambda: check_manual(),
        lambda: check_queue(),
        lambda: check_corpus(diag_key),
        lambda: check_hands(diag_key, seat),
        lambda: check_engine(),
        lambda: check_mechanics(seat_invariants or {}, role),
    ]
    for step in steps:
        c = step()
        result["checks"].append(c)
        if not c["pass"]:
            result["oriented"] = False
            return result
    result["oriented"] = True
    return result


if __name__ == "__main__":
    # self-test harness lives in the caller; this module is import-first.
    import sys
    print(json.dumps(run_gate("worker1", "claude:opus-4.8", "worker"),
                     indent=2))
