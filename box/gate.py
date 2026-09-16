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
CANONICAL_COURIER_OP_COUNT = 21   # informational only since PORTABLE-1: CHECK 1 compares the manual to the LIVE probe

# ---- PER-INSTALL CONFIGURATION (PORTABLE-1, 2026-09-15, ritual lockdown L3a) -------------
# The gate used to hardcode the operator install (engine URLs, public raw URLs of the
# operator corpus, a session floor of 307). A second install cannot pass that gate, so
# every install-specific value now comes from configure()/env, with the operator's
# values as defaults so the operator install behaves exactly as before.
INSTALL = {
    "engine_url":   os.environ.get("ONTINUITY_ENGINE_URL", "https://web-production-7eaf8.up.railway.app").rstrip("/"),
    "farm_url":     os.environ.get("ONTINUITY_FARM_URL", "https://ontinuity-farm-production.up.railway.app").rstrip("/"),
    "corpus_repo":  os.environ.get("CORPUS_REPO", "PatrickKillebrew/ontinuity").strip(),
    "corpus_ref":   os.environ.get("CORPUS_REF", "main").strip(),
    "session_floor": int(os.environ.get("ONTINUITY_CORPUS_SESSION_FLOOR", "307") or 0),
    "github_token": "",   # per-call only; never persisted here
}

def configure(**kw):
    """Set per-install values for this process (box_ops passes them from the box config).
    Unknown keys are ignored; None values leave the current value alone."""
    for k, v in kw.items():
        if k in INSTALL and v is not None:
            INSTALL[k] = v.rstrip("/") if isinstance(v, str) and k.endswith("_url") else v
    return dict(INSTALL)

# Back-compat aliases used by older callers/tests (read-only snapshots at import time).
CORPUS_SESSION_FLOOR = INSTALL["session_floor"]
ENGINE_MAIN = INSTALL["engine_url"]
ENGINE_FARM = INSTALL["farm_url"]
MANUAL_RAW = f"https://raw.githubusercontent.com/{INSTALL['corpus_repo']}/{INSTALL['corpus_ref']}/live/OPERATING_MANUAL.md"
QUEUE_RAW = f"https://raw.githubusercontent.com/{INSTALL['corpus_repo']}/{INSTALL['corpus_ref']}/live/agent_queue.md"

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



def _corpus_text(path):
    """Fetch a corpus file for THIS install: contents API with the per-call token when one is
    configured (required for a private corpus; authoritative), else raw CDN with cache-bust."""
    import base64 as _b64
    repo, ref, tok = INSTALL["corpus_repo"], INSTALL["corpus_ref"], INSTALL.get("github_token") or ""
    if tok:
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
        st, body = _get(url, headers={"Accept": "application/vnd.github+json",
                                      "X-GitHub-Api-Version": "2022-11-28",
                                      "Authorization": f"Bearer {tok}"})
        if st != 200:
            return st, ""
        return 200, _b64.b64decode(json.loads(body)["content"]).decode("utf-8", "replace")
    return _get(_fresh_raw(f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"))


def _live_allowlist(diag_key):
    """The courier allowlist as the ENGINE reports it (403 body of __probe__). Cannot be recited."""
    url = f"{INSTALL['engine_url']}/diag/op/__probe__"
    try:
        _post(url, {"seat": "gate"}, headers={"X-Diag-Key": diag_key})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        d = json.loads(body)
        return sorted(d.get("allowed") or [])
    return None



# CHECK 7 STAFFING (2026-09-16, from the first Researcher-seat session on install two): every model role
# the engine will call must answer a one-token completion BEFORE a contract is frozen. Found the hard way:
# the Challenger (Cerebras llama-3.3-70b) and Projenius (Novita deepseek-v3-0324) had both been retired by
# their providers; the engine ran, froze a contract, and could not certify because no review ever happened.
ROLE_VARS = {
    "model_a": ("MODEL_A_URL", "MODEL_A_MODEL", "MODEL_A_API_KEY"),
    "model_b": ("MODEL_B_URL", "MODEL_B_MODEL", "MODEL_B_API_KEY"),
    "model_c": ("MODEL_C_URL", "MODEL_C_MODEL", "MODEL_C_API_KEY"),
    "parietal": ("PARIETAL_URL", "PARIETAL_MODEL", "PARIETAL_API_KEY"),
    "projenius": ("PROJENIUS_URL", "PROJENIUS_MODEL", "PROJENIUS_API_KEY"),
}

def _vault_vars(railway_token, project_id, environment_id, service_id):
    q = {"query": 'query { variables(projectId: "%s", environmentId: "%s", serviceId: "%s") }' % (project_id, environment_id, service_id)}
    # Railway (behind Cloudflare) refuses python-urllib's default User-Agent with 403 (record 2026-09-14a).
    st, body = _post("https://backboard.railway.app/graphql/v2", q, timeout=30,
                     headers={"Project-Access-Token": railway_token, "Content-Type": "application/json", "User-Agent": "ontinuity-gate/1.0"})
    return (json.loads(body).get("data") or {}).get("variables") or {}

def _probe_role(url, model, key):
    """One-token completion. Returns (alive, detail). Never raises."""
    body = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 8, "temperature": 0}
    try:
        st, txt = _post(url, body, timeout=40, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "ontinuity-gate/1.0"})
        return (st == 200), ("200" if st == 200 else "HTTP %s %s" % (st, txt[:80].replace("\n", " ")))
    except urllib.error.HTTPError as e:
        return False, "HTTP %s %s" % (e.code, e.read().decode("utf-8", "replace")[:80].replace("\n", " "))
    except Exception as e:
        return False, str(e)[:80]

def check_staffing(vault=None):
    name = "STAFFING"
    v = vault or {}
    if not v:
        return _ok(name, "no vault access for a staffing probe (box config lacks railway_* keys); skipped")
    configured = {r: (v.get(u, "").strip(), v.get(m, "").strip(), v.get(k, "").strip()) for r, (u, m, k) in ROLE_VARS.items()}
    if not any(url for (url, _, _) in configured.values()):
        return _ok(name, "no model roles configured on this install (v1 remembering seat; sessions cannot run here)")
    facts, dead = [], []
    for role, (url, model, key) in configured.items():
        if not url:
            facts.append("%s: unconfigured" % role); continue
        if url.lower().startswith("external"):
            facts.append("%s: external (a seat answers via the mailbox)" % role); continue
        if not key:
            facts.append("%s: %s (no key)" % (role, model)); dead.append(role); continue
        ok, detail = _probe_role(url, model, key)
        facts.append("%s: %s %s" % (role, model, "alive" if ok else "DEAD " + detail))
        if not ok:
            dead.append(role)
    fact = "; ".join(facts)
    if dead:
        return _fail(name, fact, "NOT ORIENTED [CHECK 7 STAFFING]: dead model role(s) %s - a session would freeze a contract that can never be reviewed or distilled. Fix the provider/model string (railway_set_var) before starting." % dead)
    return _ok(name, fact)

# ---- the six checks --------------------------------------------------------
def check_manual(diag_key=None):
    name = "MANUAL"
    try:
        st, body = _corpus_text("live/OPERATING_MANUAL.md")
    except Exception as e:
        return _fail(name, f"manual unreachable: {e}",
                     "NOT ORIENTED [CHECK 1 MANUAL]: could not read "
                     "OPERATING_MANUAL.md — manual unreachable; re-sync before "
                     "acting.")
    if st != 200:
        return _fail(name, f"manual returned HTTP {st}",
                     "NOT ORIENTED [CHECK 1 MANUAL]: manual did not return HTTP 200.")
    import re
    m = re.search(r"[Aa]llowlist\s*\(live,\s*(\d+)\s*ops?\)", body)
    stated = int(m.group(1)) if m else None
    if stated is None:
        return _fail(name, "no 'Allowlist (live, N ops)' phrase found",
                     "NOT ORIENTED [CHECK 1 MANUAL]: could not parse courier "
                     "allowlist count from manual.")
    live = None
    if diag_key:
        try:
            live = _live_allowlist(diag_key)
        except Exception as e:
            return _fail(name, f"live allowlist unreachable: {e}",
                         "NOT ORIENTED [CHECK 1 MANUAL]: could not read the live courier allowlist from the engine.")
    if live is None:
        return _fail(name, "no diag_key to read the live allowlist",
                     "NOT ORIENTED [CHECK 1 MANUAL]: cannot compare the manual to the live allowlist without a diag key.")
    fact = f"manual states courier allowlist = {stated} ops; live engine allowlist = {len(live)} ops"
    if stated != len(live):
        return _fail(name, fact,
                     f"NOT ORIENTED [CHECK 1 MANUAL]: courier allowlist count "
                     f"mismatch (manual={stated}, live={len(live)}) — manual is stale; "
                     f"re-sync before acting.")
    return _ok(name, fact)


def check_queue():
    name = "QUEUE"
    try:
        st, body = _corpus_text("live/agent_queue.md")
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


def check_corpus(diag_key, engine=None):
    name = "CORPUS"
    engine = engine or INSTALL["engine_url"]
    floor = int(INSTALL.get("session_floor") or 0)
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
    fact = f"sessions count = {count}; floor = {floor}"
    if count < floor:
        return _fail(name, fact,
                     f"NOT ORIENTED [CHECK 3 CORPUS]: sessions count {count} "
                     f"below floor {floor} — wrong DB, stale "
                     f"snapshot, or hands not reaching the corpus.")
    return _ok(name, fact)


def check_hands(diag_key, seat, engine=None, relay_identity=None):
    name = "HANDS"
    engine = engine or INSTALL["engine_url"]
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
    engines = [("MAIN", INSTALL["engine_url"])]
    if INSTALL.get("farm_url"):
        engines.append(("FARM", INSTALL["farm_url"]))
    for label, base in engines:
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
        st, manual = _corpus_text("live/OPERATING_MANUAL.md")
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
             seat_invariants=None, relay_identity=None, github_token=None, install=None, vault_creds=None):
    """Run the verified bootstrap gate. role in {control, worker}.
    The five STATE checks run for BOTH roles. CHECK 6 MECHANICS runs for
    control always, and for worker too (good practice; refinement). diag_key
    is read from arg or env ONTINUITY_DIAG_KEY — never hardcoded.
    Returns the spec-section-4 structured result. Stops at first failing check.
    """
    if role not in ("control", "worker"):
        raise ValueError("role must be 'control' or 'worker'")
    if install:
        configure(**install)
    INSTALL["github_token"] = github_token or ""
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
        lambda: check_manual(diag_key),
        lambda: check_queue(),
        lambda: check_corpus(diag_key),
        lambda: check_hands(diag_key, seat, relay_identity=relay_identity),
        lambda: check_engine(diag_key),
        lambda: check_mechanics(seat_invariants or {}, role),
        lambda: check_staffing(_vault_vars(*vault_creds) if vault_creds else None),
    ]
    for step in steps:
        c = step()
        result["checks"].append(c)
        if not c["pass"]:
            result["oriented"] = False
            INSTALL["github_token"] = ""
            return result
    result["oriented"] = True
    result["install"] = {k: v for k, v in INSTALL.items() if k != "github_token"}
    INSTALL["github_token"] = ""
    return result


if __name__ == "__main__":
    # self-test harness lives in the caller; this module is import-first.
    import sys
    print(json.dumps(run_gate("worker1", "claude:opus-4.8", "worker"),
                     indent=2))
