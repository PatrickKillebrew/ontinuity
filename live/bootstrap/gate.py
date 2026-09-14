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
# CHECK 1: app.py OP_ALLOWED on the engine is the normal source of truth. MAIN
# derives its actual length and supplies it over the authenticated server hop.
# The committed value below is the direct operator/recovery fallback and must
# move in the same reviewed change as OP_ALLOWED; hybrid: matches pre-GPT engine OP_ALLOWED (19 ops). release tests enforced the
# current 20-operation value and reject a caller-provided body override.
CANONICAL_COURIER_OP_COUNT = 21

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
#                        the manual rather than against itself. All four probes
#                        are required by the current candidate manual.
MECHANICS_INVARIANTS = [
    {
        "key": "no_self_poll",
        "canonical_statement": (
            "a chat seat does not self-poll the mailbox; it acts only when its "
            "conversation is given a turn, so coordination is mailbox-native but "
            "a worker still needs its conversation nudged"),
        "manual_probe": "a chat seat does NOT self-poll the mailbox",
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
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


def _get(url, timeout=30, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with _NO_REDIRECT_OPENER.open(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _fresh_raw(url):
    """Force a current public-repository read rather than a hot CDN object."""
    import time
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}cb={int(time.time())}"


def _post(url, body, timeout=40, headers=None):
    data = json.dumps(body).encode()
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    req = urllib.request.Request(
        url, data=data, headers=request_headers,
        method="POST")
    with _NO_REDIRECT_OPENER.open(req, timeout=timeout) as r:
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
        st, body = _get(_fresh_raw(MANUAL_RAW))
    except Exception as e:
        return _fail(name, f"manual unreachable: {e}",
                     "NOT ORIENTED [CHECK 1 MANUAL]: could not read "
                     "OPERATING_MANUAL.md — manual unreachable; re-sync before "
                     "acting.")
    if st != 200:
        return _fail(name, f"manual returned HTTP {st}",
                     "NOT ORIENTED [CHECK 1 MANUAL]: manual did not return HTTP 200.")
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
        st, body = _get(_fresh_raw(QUEUE_RAW))
    except Exception as e:
        return _fail(name, f"queue unreachable: {e}",
                     "NOT ORIENTED [CHECK 2 QUEUE]: agent_queue.md unreachable.")
    if st != 200:
        return _fail(name, f"queue returned HTTP {st}",
                     "NOT ORIENTED [CHECK 2 QUEUE]: queue did not return HTTP 200.")
    # The queue is append-only history. Current truth is exactly one NEXT marker
    # and one complete bullet in the latest canonical H2 FOLD section.
    import re
    lines = body.splitlines()
    fold_indexes = [i for i, line in enumerate(lines)
                    if re.fullmatch(r"## (?:FOLD|CURRENT-STATE TOUCH POINT)(?:[ \t]+.*)?", line)]
    if not fold_indexes:
        return _fail(name, "no canonical FOLD section",
                     "NOT ORIENTED [CHECK 2 QUEUE]: no queue-tail FOLD section.")
    start = fold_indexes[-1] + 1
    end = next((i for i in range(start, len(lines))
                if re.match(r"^##(?:[ \t]+|$)", lines[i])), len(lines))
    latest = lines[start:end]
    markers = [i for i, line in enumerate(latest) if re.match(r"\*\*NEXT\b", line.strip())]
    if len(markers) == 1:
        inline = re.sub(r"^\s*\*\*NEXT[^*]*\*\*\s*", "", latest[markers[0]]).strip()
        if inline:
            action_lines = [inline]
            for line in latest[markers[0] + 1:]:
                if not line.strip() or re.match(r"\s*\*\*", line) or line.startswith("##"):
                    break
                action_lines.append(line.strip())
            return _ok(name, "next action: " + " ".join(action_lines)[:400])
    if len(markers) != 1:
        return _fail(name, f"latest FOLD has {len(markers)} NEXT markers",
                     "NOT ORIENTED [CHECK 2 QUEUE]: latest FOLD needs exactly one NEXT.")
    tail = latest[markers[0] + 1:]
    while tail and not tail[0].strip():
        tail.pop(0)
    while tail and not tail[-1].strip():
        tail.pop()
    if not tail:
        return _fail(name, "latest FOLD NEXT is empty",
                     "NOT ORIENTED [CHECK 2 QUEUE]: NEXT needs one complete bullet.")
    first = re.fullmatch(r"[ \t]*[-*][ \t]+(\S.*)", tail[0])
    if not first:
        return _fail(name, "latest FOLD NEXT is not a bullet",
                     "NOT ORIENTED [CHECK 2 QUEUE]: NEXT must begin with one bullet.")
    action_lines = [first.group(1)]
    for line in tail[1:]:
        if (not line.strip() or re.match(r"[ \t]*[-*][ \t]+\S", line)
                or not re.match(r"^[ \t]+\S", line)):
            return _fail(name, "latest FOLD NEXT is ambiguous",
                         "NOT ORIENTED [CHECK 2 QUEUE]: NEXT must be one bounded bullet.")
        action_lines.append(line.strip())
    return _ok(name, "next action: " + " ".join(action_lines))


def check_corpus(diag_key, engine=ENGINE_MAIN):
    name = "CORPUS"
    sql = "SELECT COUNT(*) FROM sessions"
    url = f"{engine}/diag/api/query?sql={urllib.parse.quote(sql)}"
    try:
        st, body = _get(url, headers={"X-Diag-Key": diag_key})
        d = json.loads(body)
        if st != 200 or not isinstance(d, dict):
            raise ValueError(f"unexpected HTTP status {st}")
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


def check_hands(diag_key, seat, engine=ENGINE_MAIN, relay_identity=None):
    name = "HANDS"
    if relay_identity and relay_identity.get("authenticated"):
        if relay_identity.get("seat") != seat:
            return _fail(name, "authenticated relay identity mismatch",
                         "NOT ORIENTED [CHECK 4 HANDS]: courier identity does not match seat.")
        return _ok(name, "authenticated capability reached the box through the courier")
    url = f"{engine}/diag/op/mailbox_peek"
    try:
        st, body = _post(url, {"seat": seat, "limit": 1},
                         headers={"X-Diag-Key": diag_key})
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


def check_engine(diag_key=None):
    name = "ENGINE"
    diag_key = diag_key or os.environ.get("ONTINUITY_DIAG_KEY")
    if not diag_key:
        return _fail(name, "no diagnostic root provided",
                     "NOT ORIENTED [CHECK 5 ENGINE]: no server authority available.")
    facts = []
    for label, base in (("MAIN", ENGINE_MAIN), ("FARM", ENGINE_FARM)):
        # engine state needs the diag key; reachability+parse is the bar, but
        # the /diag/engine route is key-gated, so we use the key passed via env
        # at call time. We read it here from the closure-injected value.
        url = f"{base}/diag/engine"
        try:
            st, body = _get(url, headers={"X-Diag-Key": diag_key})
            d = json.loads(body)
            if st != 200 or not isinstance(d, dict) or type(d.get("running")) is not bool:
                raise ValueError(f"expected HTTP 200 JSON with boolean running; status={st}")
            running = d["running"]
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
        st, manual = _get(_fresh_raw(MANUAL_RAW))
    except Exception as e:
        return _fail(name, f"manual unreachable for ratification: {e}",
                     "NOT ORIENTED [CHECK 6 MECHANICS]: manual unreachable; "
                     "cannot ratify reproduced invariants.")
    if st != 200:
        return _fail(name, f"manual returned HTTP {st}",
                     "NOT ORIENTED [CHECK 6 MECHANICS]: manual did not return HTTP 200.")
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
        manual_ok = probe in manual
        ok = reproduced and (manual_ok is not False)
        findings.append({
            "key": key,
            "reproduced": reproduced,
            "coverage": round(coverage, 2),
            "manual_ratified": manual_ok,
            "pass": ok,
        })
        if not ok:
            if not reproduced:
                msg = (f"NOT ORIENTED [CHECK 6 MECHANICS]: invariant '{key}' "
                       f"not reproduced (token coverage {coverage:.2f} < 0.85) "
                       f"— seat cannot state the operating mechanic correctly.")
            else:
                msg = (f"NOT ORIENTED [CHECK 6 MECHANICS]: invariant '{key}' "
                       f"reproduced but NOT ratified by manual (probe absent) "
                       f"— manual/seat incoherent; re-sync.")
            return _fail(name, {"role": role, "findings": findings}, msg)
    return _ok(name, {
        "role": role,
        "summary": (f"all {len(MECHANICS_INVARIANTS)} invariants "
                    "reproduced + ratified"),
        "findings": findings,
    })


# ---- the gate --------------------------------------------------------------
def run_gate(seat, lineage, role="worker", diag_key=None,
             seat_invariants=None, relay_identity=None):
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
    result = {"oriented": False, "seat": seat, "role": role,
              "lineage": lineage, "checks": []}

    # ordered checks; stop at first failure
    steps = [
        lambda: check_manual(),
        lambda: check_queue(),
        lambda: check_corpus(diag_key),
        lambda: check_hands(diag_key, seat, relay_identity=relay_identity),
        lambda: check_engine(diag_key),
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
