"""
Ontinuity — Close-Ritual Enforcement Gate (sandbox-local runnable)
==================================================================
BUILD form (a) of live/specs/close_ritual_gate.md, the session-CLOSE sibling of
the Verified Bootstrap Gate (live/bootstrap/gate.py / live/specs/verified_bootstrap_gate.md).
Same comply-or-fail shape, fired on session CLOSE instead of OPEN.

This is a SANDBOX-LOCAL runnable the CONTROL seat calls as the LAST step of its
close. It is NOT the /diag/op/close_gate courier op (form b) — that is the
hardening follow-up and needs a SEPARATE OP_ALLOWED commit+deploy two-step.
NO DEPLOY. NO SECRETS WRITTEN HERE: the diag key and GitHub token are read from
the environment or passed in by the caller; never hardcoded, never committed.

Authored by worker11 (claude:opus-4.8) under the close-ritual-gate BUILD task.
Grounded against live source this session (not the spec's claims):
  - live/specs/close_ritual_gate.md (the 8 checks + return contract)
  - live/bootstrap/gate.py (the runnable contract / _ok/_fail / http-helper style)
  - live/OPERATING_MANUAL.md "CONTROL-SEAT CLOSE RITUAL" (the 8 ritual items;
    spec CHECK 5 == manual item 4b CONTRACT-DOC CURRENCY)
  - live formats: PUNCH_LIST "Last resolved: <date>" header; conversations/
    "YYYY-MM-DD_descriptor.md" naming; agent_queue dated fold tail; CONTROL_HANDOFF
    "# Updated <date>" header; manual "Allowlist (live, N ops)" phrasing.

KEY DIFFERENCES FROM THE BOOTSTRAP GATE (deliberate, per close spec section 3):
  1. Reports ALL failing checks in ONE run (does NOT stop at first failure) — a
     closing seat must see every gap at once. closed == (every check.pass true).
  2. Return key is `closed`, not `oriented`.
  3. All GitHub reads go through authed api.github.com (Accept: vnd.github.raw),
     NOT the raw.githubusercontent CDN (which is dead/stale for this repo — the
     standing read-path rule). The bootstrap gate's raw-CDN reads are the older
     pattern; this gate uses the API path.
  4. CHECK 4 live op count is read from the engine probe endpoint
     (POST /diag/op/__probe__) whose error body returns the live courier
     allowlist verbatim — a deterministic live count with no app.py parsing.

Return contract (spec section 2):
  { "closed": bool, "seat": str, "session_start": str,
    "checks": [ {"name","pass","returned_fact","failure_message"(if fail)} ] }
closed is True iff EVERY check passed. The SESSION WINDOW is passed in via
`session_start` (ISO timestamp or first-commit sha); it is NOT inferred.
"""

from __future__ import annotations
import json, os, re, datetime, urllib.request, urllib.parse, urllib.error

# ---- engine bases ----------------------------------------------------------
ENGINE_MAIN = "https://web-production-7eaf8.up.railway.app"
ENGINE_FARM = "https://ontinuity-farm-production.up.railway.app"

# ---- repo (api.github.com, authed raw) -------------------------------------
REPO = "PatrickKillebrew/ontinuity"
API = f"https://api.github.com/repos/{REPO}"

# CHECK 6 secret patterns (spec section 3 CHECK 6). Token VALUES (diag key,
# Railway token) are injected at call time so they are never hardcoded here.
SECRET_PATTERNS = [
    r"csk-[A-Za-z0-9]{16,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
]


# ---- tiny http helpers (stdlib only, no deps) ------------------------------
def _get(url, timeout=30, headers=None):
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _post(url, body, timeout=40, headers=None):
    data = json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        # the engine probe intentionally returns 403; its body is what we want
        return e.code, e.read().decode("utf-8", "replace")


def _gh_raw(path, token, timeout=30):
    """Read a repo file's raw bytes via the authed contents API (NOT raw CDN)."""
    url = f"{API}/contents/{path}?ref=main"
    h = {"Accept": "application/vnd.github.raw",
         "Authorization": f"Bearer {token}"}
    return _get(url, timeout=timeout, headers=h)


def _gh_json(path, token, timeout=30):
    """Read a repo path listing/metadata via the contents API (JSON)."""
    url = f"{API}/contents/{path}?ref=main"
    h = {"Accept": "application/vnd.github+json",
         "Authorization": f"Bearer {token}"}
    st, body = _get(url, timeout=timeout, headers=h)
    return st, json.loads(body)


def _commits_since(session_start, token, timeout=30):
    """List commits since session_start (ISO ts). Returns list of commit dicts.
    If session_start is a sha (not ISO), falls back to the recent commit page
    and the caller filters by sha presence."""
    params = {"sha": "main", "per_page": "100"}
    if session_start and "T" in session_start:  # looks like an ISO timestamp
        params["since"] = session_start
    url = f"{API}/commits?" + urllib.parse.urlencode(params)
    h = {"Accept": "application/vnd.github+json",
         "Authorization": f"Bearer {token}"}
    st, body = _get(url, timeout=timeout, headers=h)
    return st, json.loads(body)


def _ok(name, returned_fact):
    return {"name": name, "pass": True, "returned_fact": returned_fact}


def _fail(name, returned_fact, message):
    return {"name": name, "pass": False, "returned_fact": returned_fact,
            "failure_message": message}


def _today_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


# ---- the eight checks ------------------------------------------------------
def check_punch_list(token):
    """CHECK 1 — punch list reconciled today."""
    name = "PUNCH-LIST"
    try:
        st, body = _gh_raw("live/PUNCH_LIST.md", token)
    except Exception as e:
        return _fail(name, f"PUNCH_LIST unreachable: {e}",
                     "CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: could not read "
                     "PUNCH_LIST.md to verify reconciliation.")
    # header phrasing: "Last resolved: 2026-06-29 PM (..." — grab the date.
    m = re.search(r"Last resolved:\s*(\d{4}-\d{2}-\d{2})", body)
    last = m.group(1) if m else None
    today = _today_utc()
    fact = f"Last-resolved={last}; today={today}"
    if last is None:
        return _fail(name, "no 'Last resolved: <date>' header found", fact +
                     " — CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: header date "
                     "unparseable; punch list not reconciled this close.")
    if last != today:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: Last-resolved "
                     f"{last} is not today — punch list not reconciled this close.")
    return _ok(name, fact)


def check_conversation(token, session_start):
    """CHECK 2 — a conversation record dated today exists in live/conversations/."""
    name = "CONVERSATION"
    try:
        st, listing = _gh_json("live/conversations", token)
    except Exception as e:
        return _fail(name, f"conversations dir unreachable: {e}",
                     "CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: could not list "
                     "live/conversations/ to verify a record was written.")
    today = _today_utc()
    names = [x.get("name", "") for x in listing if isinstance(x, dict)]
    # naming convention: "YYYY-MM-DD_descriptor.md"
    todays = [n for n in names if n.startswith(today)]
    fact = f"today={today}; matching records={todays or 'none'}"
    if not todays:
        return _fail(name, fact,
                     "CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: no conversation "
                     "record dated today — the dialogue/rulings were not captured "
                     "(only the control seat can; a worker backfilling from "
                     "commits cannot see the window).")
    return _ok(name, fact)


def check_queue_fold(token, session_start):
    """CHECK 3 — a narrative fold referencing this session was appended."""
    name = "QUEUE-FOLD"
    try:
        st, body = _gh_raw("live/agent_queue.md", token)
    except Exception as e:
        return _fail(name, f"agent_queue unreachable: {e}",
                     "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: could not read "
                     "agent_queue.md to verify a fold was appended.")
    today = _today_utc()
    # inspect the tail (last ~4000 chars covers the latest fold block)
    tail = body[-4000:]
    today_in_tail = today in tail
    # session sha reference: if session_start is a sha, look for it (short or full)
    sha_in_tail = False
    sha_token = ""
    if session_start and "T" not in session_start:
        sha_token = session_start.strip()[:7]
        sha_in_tail = sha_token and sha_token in tail
    fact = (f"today={today} in tail={today_in_tail}; "
            f"session_sha={sha_token or 'n/a'} in tail={sha_in_tail}")
    if not (today_in_tail or sha_in_tail):
        return _fail(name, fact,
                     "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: agent_queue tail "
                     "predates this session — no narrative fold appended.")
    return _ok(name, fact)


def check_manual_currency(diag_key, token):
    """CHECK 4 — manual allowlist count == live OP_ALLOWED count."""
    name = "MANUAL"
    # manual count: parse "Allowlist (live, N ops)" from OPERATING_MANUAL.md
    try:
        st, manual = _gh_raw("live/OPERATING_MANUAL.md", token)
    except Exception as e:
        return _fail(name, f"manual unreachable: {e}",
                     "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: OPERATING_MANUAL.md "
                     "unreachable; cannot verify allowlist currency.")
    m = re.search(r"[Aa]llowlist\s*\(live,\s*(\d+)\s*ops?\)", manual)
    manual_count = int(m.group(1)) if m else None
    # live count: the engine probe endpoint returns the live allowlist verbatim
    # in its (intentional 403) error body as {"allowed":[...]}.
    live_count = None
    try:
        url = (f"{ENGINE_MAIN}/diag/op/__probe__?diag_key="
               f"{urllib.parse.quote(diag_key)}")
        st, body = _post(url, {})
        d = json.loads(body)
        if isinstance(d.get("allowed"), list):
            live_count = len(d["allowed"])
    except Exception as e:
        return _fail(name, f"probe error: {e}; manual={manual_count}",
                     "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: could not read live "
                     "OP_ALLOWED count from the engine probe.")
    fact = f"manual_count={manual_count}; live_count={live_count}"
    if manual_count is None or live_count is None:
        return _fail(name, fact,
                     "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: could not parse one "
                     "of the counts (manual phrase or probe body).")
    if manual_count != live_count:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 4 MANUAL]: allowlist "
                     f"manual={manual_count} live={live_count} — manual not "
                     f"synced this close.")
    return _ok(name, fact)


def check_contract_doc(token, session_start, worker_contract_changed):
    """CHECK 5 — IF the WORKER contract changed this session, the worker contract
    docs (WORKER_MANUAL.md + both worker boot docs WORKER_BOOT_PACKET.md and
    WORKER_QUICKBOOT.md) must be committed this session. Scoped to the WORKER
    contract ONLY (a CONTROL-packet change does not trigger this — per the spec
    scoping note)."""
    name = "CONTRACT-DOC"
    if not worker_contract_changed:
        return _ok(name, "worker_contract_changed=false — no contract change "
                         "(pass-with-note; control-packet changes do not apply)")
    # changed: confirm the worker contract docs were committed this session.
    # CHECK 5 DOC-NAME RESOLUTION (worker11, from worker22's non-blocking flag):
    # live/ has BOTH WORKER_QUICKBOOT.md (the short snippet the operator pastes —
    # carries the fetch-path contract) AND WORKER_BOOT_PACKET.md (the full packet
    # the worker actually reads + RUNS — carries the run-behavior contract; its
    # title is literally "you_there self-draining"). Manual 4b's "WORKER BOOT
    # PACKET = the text that ACTUALLY runs" + the you_there-divergence example
    # both point at the BOOT_PACKET as behavior-bearing, while the QUICKBOOT
    # snippet bootstraps the fetch. BOTH are contract-bearing, so a worker-
    # contract change is not shipped until BOTH reflect it (matches 4b's "not
    # live until it reaches the packet the worker runs"). Check all three docs.
    docs = ["live/WORKER_MANUAL.md", "live/WORKER_BOOT_PACKET.md",
            "live/WORKER_QUICKBOOT.md"]
    try:
        st, commits = _commits_since(session_start, token)
    except Exception as e:
        return _fail(name, f"commits API error: {e}",
                     "CLOSE NOT COMPLETE [CHECK 5 CONTRACT-DOC]: could not list "
                     "session commits to verify worker-contract docs.")
    changed_paths = set()
    today = _today_utc()
    for csha in commits:
        cdate = (csha.get("commit", {}).get("committer", {}) or {}).get("date", "")
        in_window = False
        if session_start and "T" in session_start:
            in_window = cdate >= session_start
        else:
            in_window = cdate.startswith(today)
        if not in_window:
            continue
        # fetch per-commit file list
        try:
            st2, detail = _gh_commit_files(csha.get("sha", ""), token)
            changed_paths.update(detail)
        except Exception:
            pass
    missing = [d for d in docs if d not in changed_paths]
    fact = (f"worker_contract_changed=true; committed_this_session="
            f"{sorted(changed_paths & set(docs)) or 'none'}; missing={missing}")
    if missing:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 5 CONTRACT-DOC]: worker contract "
                     f"changed but {missing} not committed this close — the "
                     f"packet the worker RUNS is stale.")
    return _ok(name, fact)


def _gh_commit_files(sha, token, timeout=30):
    """Return the set of file paths changed in a commit."""
    url = f"{API}/commits/{sha}"
    h = {"Accept": "application/vnd.github+json",
         "Authorization": f"Bearer {token}"}
    st, body = _get(url, timeout=timeout, headers=h)
    d = json.loads(body)
    return st, {f.get("filename", "") for f in d.get("files", [])}


def check_secrets(token, session_start, diag_key=None, railway_token=None,
                  operator_ips=None):
    """CHECK 6 — no secret pattern in any file committed this session."""
    name = "SECRETS"
    try:
        st, commits = _commits_since(session_start, token)
    except Exception as e:
        return _fail(name, f"commits API error: {e}",
                     "CLOSE NOT COMPLETE [CHECK 6 SECRETS]: could not list "
                     "session commits to sweep for secrets.")
    today = _today_utc()
    # build the live-value patterns (injected, never hardcoded)
    value_patterns = list(SECRET_PATTERNS)
    for v in (diag_key, railway_token):
        if v:
            value_patterns.append(re.escape(v))
    for ip in (operator_ips or []):
        value_patterns.append(re.escape(ip))
    compiled = [re.compile(p) for p in value_patterns]
    hits = []
    scanned = 0
    for csha in commits:
        cdate = (csha.get("commit", {}).get("committer", {}) or {}).get("date", "")
        in_window = (cdate >= session_start) if (session_start and "T" in session_start) \
            else cdate.startswith(today)
        if not in_window:
            continue
        try:
            st2, paths = _gh_commit_files(csha.get("sha", ""), token)
        except Exception:
            continue
        for p in paths:
            if not p:
                continue
            try:
                st3, blob = _gh_raw(p, token)
            except Exception:
                continue
            scanned += 1
            for ln, line in enumerate(blob.splitlines(), 1):
                for rx in compiled:
                    if rx.search(line):
                        hits.append(f"{p}:{ln}")
                        break
    fact = f"files_scanned={scanned}; hits={hits or 'none'}"
    if hits:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 6 SECRETS]: potential secret in "
                     f"{hits[0]} committed this session — redact + rotate before "
                     f"close. (all hits: {hits})")
    return _ok(name, fact)


def check_state_clean(diag_key):
    """CHECK 7 — both engines idle, zero orphaned claims, no failed deploy."""
    name = "STATE"
    facts = []
    fail_bits = []
    for label, base in (("MAIN", ENGINE_MAIN), ("FARM", ENGINE_FARM)):
        try:
            url = f"{base}/diag/engine?diag_key={urllib.parse.quote(diag_key)}"
            st, body = _get(url)
            d = json.loads(body)
            running = d.get("running")
            facts.append(f"{label}.running={running}")
            if running is True:
                fail_bits.append(f"{label} running")
        except Exception as e:
            facts.append(f"{label} unreachable: {e}")
            fail_bits.append(f"{label} unreachable")
    # orphaned claims
    try:
        sql = "SELECT COUNT(*) FROM seat_mailbox WHERE status='claimed'"
        url = (f"{ENGINE_MAIN}/diag/api/query?diag_key="
               f"{urllib.parse.quote(diag_key)}&sql={urllib.parse.quote(sql)}")
        st, body = _get(url)
        claimed = int(json.loads(body)["rows"][0][0])
        facts.append(f"orphaned_claims={claimed}")
        if claimed != 0:
            fail_bits.append(f"{claimed} orphaned claims")
    except Exception as e:
        facts.append(f"claims query error: {e}")
        fail_bits.append("claims unqueryable")
    fact = "; ".join(facts)
    if fail_bits:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 7 STATE]: {' | '.join(fail_bits)} "
                     f"— state not left clean.")
    return _ok(name, fact)


def check_handoff(token, session_start):
    """CHECK 8 — CONTROL_HANDOFF.md states a single next action AND was updated
    this session. (CONTROL_HANDOFF.md is the canonical handoff surface per the
    manual: its header is '# CONTROL HANDOFF — current state + the single next
    action'; the queue head is the orientation target but the handoff DOC is the
    dedicated surface.)"""
    name = "HANDOFF"
    try:
        st, body = _gh_raw("live/CONTROL_HANDOFF.md", token)
    except Exception as e:
        return _fail(name, f"CONTROL_HANDOFF unreachable: {e}",
                     "CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: CONTROL_HANDOFF.md "
                     "unreachable; next seat has no single next action.")
    today = _today_utc()
    # updated date: "# Updated 2026-06-21 by control seat ..."
    m = re.search(r"Updated\s*(\d{4}-\d{2}-\d{2})", body)
    updated = m.group(1) if m else None
    # single next action: the file's canonical HEADER ("# CONTROL HANDOFF —
    # current state and the single next action") already contains the phrase
    # "single next action", so a phrase-match against the whole body ALWAYS
    # passes and silently disables half of CHECK 8 (worker11 defect, worker22
    # finding). FIX: require a next-action SECTION HEADING FOLLOWED BY a non-empty
    # content line — a populated section, not a phrase the template guarantees.
    # Strip the leading '# ...' comment/header lines first so the L1 header prose
    # cannot satisfy the match. Verified against the live CONTROL_HANDOFF.md whose
    # real section is "## THE SINGLE NEXT ACTION" followed by an actionable line.
    no_header = "\n".join(l for l in body.splitlines()
                          if not l.lstrip().startswith("#") or l.lstrip().startswith("##"))
    # a markdown heading (##...) mentioning NEXT ACTION / NEXT-SEAT / SINGLE NEXT
    # ACTION, immediately followed by at least one non-empty (non-heading) line.
    has_next = bool(re.search(
        r"^#{1,6}\s*[^\n]*(?:SINGLE NEXT ACTION|NEXT ACTION|NEXT[- ]SEAT)[^\n]*\n+\s*\S",
        no_header, re.I | re.M))
    updated_this_session = (updated == today)
    fact = f"updated={updated}; today={today}; has_next_action={has_next}"
    if not has_next:
        return _fail(name, fact,
                     "CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: handoff missing a "
                     "single next-action line — next seat has no clear target.")
    if not updated_this_session:
        return _fail(name, fact,
                     f"CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: handoff stale "
                     f"(updated {updated}, not today) — next seat would orient "
                     f"onto a stale target.")
    return _ok(name, fact)


# ---- the gate --------------------------------------------------------------
def run_gate(seat, session_start, diag_key=None, github_token=None,
             worker_contract_changed=False, railway_token=None,
             operator_ips=None):
    """Run the close-ritual gate. Reports ALL failing checks in one run (does
    NOT stop at first failure). Returns the spec-section-2 structured result.

    session_start : ISO timestamp (preferred) OR the session's first-commit sha.
                    Decides the 'this session' window; NOT inferred.
    diag_key      : arg or env ONTINUITY_DIAG_KEY.
    github_token  : arg or env ONTINUITY_GH_TOKEN (read-scoped is enough).
    worker_contract_changed : the closing seat's 4b judgment (deterministic
                    input; the gate enforces the consequence, scoped to the
                    WORKER contract only).
    """
    diag_key = diag_key or os.environ.get("ONTINUITY_DIAG_KEY")
    github_token = github_token or os.environ.get("ONTINUITY_GH_TOKEN")

    result = {"closed": False, "seat": seat, "session_start": session_start,
              "checks": []}

    if not session_start:
        result["checks"].append(
            _fail("PRECONDITION", "no session_start provided",
                  "CLOSE NOT COMPLETE [PRECONDITION]: no session_start (ISO ts "
                  "or first-commit sha) — the 'this session' window is "
                  "undecidable; pass it in, do not infer."))
        return result
    if not diag_key or not github_token:
        miss = []
        if not diag_key:
            miss.append("diag_key/ONTINUITY_DIAG_KEY")
        if not github_token:
            miss.append("github_token/ONTINUITY_GH_TOKEN")
        result["checks"].append(
            _fail("PRECONDITION", f"missing: {miss}",
                  f"CLOSE NOT COMPLETE [PRECONDITION]: missing {miss} — cannot "
                  f"run the corpus/repo checks."))
        return result

    # ordered checks; run ALL, collect every failure
    checks = [
        check_punch_list(github_token),
        check_conversation(github_token, session_start),
        check_queue_fold(github_token, session_start),
        check_manual_currency(diag_key, github_token),
        check_contract_doc(github_token, session_start, worker_contract_changed),
        check_secrets(github_token, session_start, diag_key, railway_token,
                      operator_ips),
        check_state_clean(diag_key),
        check_handoff(github_token, session_start),
    ]
    result["checks"] = checks
    result["closed"] = all(c["pass"] for c in checks)
    return result


if __name__ == "__main__":
    import sys
    seat = sys.argv[1] if len(sys.argv) > 1 else "control"
    session_start = sys.argv[2] if len(sys.argv) > 2 else None
    out = run_gate(seat, session_start)
    print(json.dumps(out, indent=2))
    sys.exit(0 if out["closed"] else 1)
