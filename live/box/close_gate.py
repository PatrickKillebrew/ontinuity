"""
Ontinuity — Close-Ritual Enforcement Gate, form (b): the box op runnable
=========================================================================
LINEAGE: derived from staging/close_gate.py (authored worker11, signed worker22, June 2026;
the sandbox-local form (a); original bytes preserved at museum/staging/close_gate_2026-06.py).
Spec: live/specs/close_ritual_gate.md. Gap audit + this rewrite: live/specs/ritual_lockdown_plan.md
(RITUAL LOCKDOWN L5, 2026-09-15). Same check names, same failure messages, same report-ALL
semantics. What changed, each traceable to a numbered gap in the plan:
  - the SESSION WINDOW is the `seat_sessions` row opened by bootstrap_gate (L3): `started_at`
    replaces every "today" / seat-typed date; "updated this session" == committed since started_at
  - CHECK 5 is DERIVED from the commits in the window (paths touched), no seat-supplied boolean
  - CHECK 2 also requires the record to cite >=1 commit sha from this session (the join)
  - CHECK 9 ORIENT: an `orient` ledger row belongs to this session (the open ritual as a fact)
  - install values (engine, farm, corpus repo, box DB path) come from configure(); ABSENT = none
  - diag key travels in the X-Diag-Key HEADER, never the URL (security hardening rule)
  - secrets sweep adds the install's own key VALUES + IPv4 literals; documented 8-char prefixes pass
  - return adds seat_session_id, session_start, and (in the op wrapper) ledger_row_id
The box op wrapper (box_ops.op_close_gate) closes the seat session and revokes its key on closed:true.
"""
import json, os, re, datetime, sqlite3, urllib.request, urllib.parse, urllib.error

INSTALL = {
    "engine_url":  os.environ.get("ONTINUITY_ENGINE_URL", "").rstrip("/"),
    "farm_url":    os.environ.get("ONTINUITY_FARM_URL", "").rstrip("/"),
    "corpus_repo": os.environ.get("CORPUS_REPO", "").strip(),
    "corpus_ref":  os.environ.get("CORPUS_REF", "main").strip(),
    "db_path":     os.environ.get("ONTINUITY_DB_PATH", ""),
    "github_token": "",
}

def configure(**kw):
    for k, v in kw.items():
        if k in INSTALL and v is not None:
            INSTALL[k] = v.rstrip("/") if isinstance(v, str) and k.endswith("_url") else v
    return {k: v for k, v in INSTALL.items() if k != "github_token"}

SECRET_PATTERNS = [
    r"csk-[A-Za-z0-9]{16,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",   # IPv4 literals (operator/box IPs)
]

CONTRACT_PATHS = {  # paths whose change means "the contract changed" (CHECK 5 derivation)
    "worker": [r"^app\.py$", r"(^|/)seat_mailbox\.py$", r"(^|/)box_ops\.py$", r"(^|/)file_server\.py$", r"(^|/)gate\.py$",
               r"(^|/)WORKER_MANUAL\.md$", r"(^|/)WORKER_BOOT_PACKET\.md$", r"(^|/)WORKER_QUICKBOOT\.md$"],
}
WORKER_DOCS = ["live/WORKER_MANUAL.md", "live/WORKER_BOOT_PACKET.md", "live/WORKER_QUICKBOOT.md"]

# ---- http helpers (stdlib) --------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None
_OPENER = urllib.request.build_opener(_NoRedirect)

def _get(url, timeout=30, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with _OPENER.open(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")

def _post(url, body, timeout=40, headers=None):
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with _OPENER.open(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def _api(): return f"https://api.github.com/repos/{INSTALL['corpus_repo']}"
def _gh_headers(accept):
    return {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28", "Authorization": f"Bearer {INSTALL['github_token']}"}
def _gh_raw(path): return _get(f"{_api()}/contents/{path}?ref={INSTALL['corpus_ref']}", headers=_gh_headers("application/vnd.github.raw"))
def _gh_json(path):
    st, body = _get(f"{_api()}/contents/{path}?ref={INSTALL['corpus_ref']}", headers=_gh_headers("application/vnd.github+json")); return st, json.loads(body)

def _session_commits(started_at):
    """Every commit on the corpus ref since started_at, with the files each touched. Fetched once."""
    params = {"sha": INSTALL["corpus_ref"], "per_page": "100", "since": started_at}
    st, body = _get(f"{_api()}/commits?" + urllib.parse.urlencode(params), headers=_gh_headers("application/vnd.github+json"))
    out = []
    for c in json.loads(body):
        sha = c.get("sha", "")
        try:
            st2, det = _get(f"{_api()}/commits/{sha}", headers=_gh_headers("application/vnd.github+json"))
            files = [f.get("filename", "") for f in json.loads(det).get("files", [])]
        except Exception:
            files = []
        out.append({"sha": sha, "date": (c.get("commit", {}).get("committer", {}) or {}).get("date", ""), "files": files,
                    "message": (c.get("commit", {}).get("message") or "")[:120]})
    return out

def _ok(name, fact): return {"name": name, "pass": True, "returned_fact": fact}
def _fail(name, fact, msg): return {"name": name, "pass": False, "returned_fact": fact, "failure_message": msg}
def _touched(commits, path): return [c["sha"][:7] for c in commits if path in c["files"]]

# ---- the checks --------------------------------------------------------------
def check_punch_list(commits, contract_items=None):
    """CHECK 1 — RECONCILIATION (L6.5). If the session registered a contract, every item must be DONE with
    evidence that exists in this session's window (a commit sha, or a ledger op_id) or CARRIED with a note;
    JUDGED items close on the operator's recorded ruling. The punch list itself must also have been committed."""
    name = "PUNCH-LIST"
    try: st, body = _gh_raw("live/PUNCH_LIST.md")
    except Exception as e:
        return _fail(name, f"PUNCH_LIST unreachable: {e}", "CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: could not read PUNCH_LIST.md to verify reconciliation.")
    m = re.search(r"Last resolved:\s*(\d{4}-\d{2}-\d{2})", body); last = m.group(1) if m else None
    hits = _touched(commits, "live/PUNCH_LIST.md")
    items = contract_items or []
    shas = {c["sha"][:7] for c in commits} | {c["sha"] for c in commits}
    unmet = []
    for it in items:
        stt = (it.get("status") or "OPEN").upper(); ev = (it.get("evidence") or "").strip(); kind = (it.get("kind") or "JUDGED").upper()
        if stt == "OPEN":
            unmet.append(f"{it['item_id']} ({it['title'][:40]}): still OPEN")
        elif stt == "CARRIED" and not ev:
            unmet.append(f"{it['item_id']} ({it['title'][:40]}): CARRIED without a carry note")
        elif stt == "DONE" and kind == "VERIFIABLE":
            ok = any(tok in shas for tok in re.findall(r"\b[0-9a-f]{7,40}\b", ev)) or bool(re.search(r"\bop_id[:= ]\s*\d+", ev))
            if not ok:
                unmet.append(f"{it['item_id']} ({it['title'][:40]}): DONE but evidence '{ev[:30]}' is not a commit in this session's window or a ledger op_id")
        elif stt == "DONE" and kind == "JUDGED" and not ev:
            unmet.append(f"{it['item_id']} ({it['title'][:40]}): JUDGED item marked DONE without the operator's ruling")
    fact = f"Last-resolved={last}; committed_this_session={hits or 'no'}; contract_items={len(items)}; unmet={len(unmet)}"
    if unmet:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: contract not reconciled — " + " | ".join(unmet))
    if not hits:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 1 PUNCH-LIST]: PUNCH_LIST.md was not committed this session — punch list not reconciled this close.")
    return _ok(name, fact + ("" if items else " (no contract registered this session)"))


def check_conversation(commits):
    name = "CONVERSATION"
    recs = [(c["sha"], f) for c in commits for f in c["files"] if f.startswith("live/conversations/") and f.endswith(".md") and not f.endswith("CONVENTION.md")]
    if not recs:
        return _fail(name, "no live/conversations/*.md committed this session",
                     "CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: no conversation record committed this session — the dialogue/rulings were not captured (only the control seat can; a worker backfilling from commits cannot see the window).")
    rec_sha, rec_path = recs[-1]
    others = [c["sha"] for c in commits if c["sha"] != rec_sha]
    try: st, body = _gh_raw(rec_path)
    except Exception as e:
        return _fail(name, f"record {rec_path} unreadable: {e}", "CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: record committed but unreadable.")
    cited = sorted({s[:7] for s in others if s[:7] in body})
    fact = f"record={rec_path}@{rec_sha[:7]}; session_commits={len(commits)}; cites={cited or 'none'}"
    if others and not cited:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 2 CONVERSATION]: the record cites no commit from this session — no join from conversation to change; add the shas of the work it describes.")
    return _ok(name, fact + ("" if others else " (only commit this session is the record itself: pass-with-note)"))

def check_queue_fold(commits):
    name = "QUEUE-FOLD"
    hits = _touched(commits, "live/agent_queue.md")
    if not hits:
        return _fail(name, "agent_queue.md not committed this session", "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: agent_queue tail predates this session — no narrative fold appended.")
    try: st, body = _gh_raw("live/agent_queue.md")
    except Exception as e:
        return _fail(name, f"agent_queue unreachable: {e}", "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: could not read agent_queue.md to verify a fold was appended.")
    lines = body.splitlines()
    heads = [i for i, l in enumerate(lines) if re.fullmatch(r"## (?:FOLD|CURRENT-STATE TOUCH POINT)(?:[ \t]+.*)?", l)]
    if not heads:
        return _fail(name, "no fold header", "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: no `## CURRENT-STATE TOUCH POINT` fold at the tail.")
    latest = lines[heads[-1]:]
    nexts = [l for l in latest if re.match(r"\s*\*\*NEXT\b", l)]
    fact = f"committed_this_session={hits}; latest_fold='{lines[heads[-1]][:60]}'; NEXT_markers={len(nexts)}"
    if len(nexts) != 1:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 3 QUEUE-FOLD]: latest fold needs exactly one **NEXT line (the bootstrap gate parses it).")
    return _ok(name, fact)

def check_manual_currency(diag_key):
    name = "MANUAL"
    try: st, manual = _gh_raw("live/OPERATING_MANUAL.md")
    except Exception as e:
        return _fail(name, f"manual unreachable: {e}", "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: OPERATING_MANUAL.md unreachable; cannot verify allowlist currency.")
    m = re.search(r"[Aa]llowlist\s*\(live,\s*(\d+)\s*ops?\)", manual); manual_count = int(m.group(1)) if m else None
    try:
        st, body = _post(f"{INSTALL['engine_url']}/diag/op/__probe__", {"seat": "close_gate"}, headers={"X-Diag-Key": diag_key})
        d = json.loads(body); live_count = len(d["allowed"]) if isinstance(d.get("allowed"), list) else None
    except Exception as e:
        return _fail(name, f"probe error: {e}; manual={manual_count}", "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: could not read live OP_ALLOWED count from the engine probe.")
    fact = f"manual_count={manual_count}; live_count={live_count}"
    if manual_count is None or live_count is None:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 4 MANUAL]: could not parse one of the counts (manual phrase or probe body).")
    if manual_count != live_count:
        return _fail(name, fact, f"CLOSE NOT COMPLETE [CHECK 4 MANUAL]: allowlist manual={manual_count} live={live_count} — manual not synced this close.")
    return _ok(name, fact)

def check_contract_doc(commits):
    """CHECK 5 — DERIVED: did any commit this session touch a contract-bearing path? If so, the worker
    contract docs that EXIST in this corpus must also have been committed this session."""
    name = "CONTRACT-DOC"
    rx = [re.compile(p) for p in CONTRACT_PATHS["worker"]]
    changed = sorted({f for c in commits for f in c["files"] if any(r.search(f) for r in rx)})
    if not changed:
        return _ok(name, "no contract-bearing path committed this session (derived from the commit list; no self-report)")
    try:
        st, listing = _gh_json("live"); present = {"live/" + x.get("name", "") for x in listing if isinstance(x, dict)}
    except Exception as e:
        return _fail(name, f"could not list live/: {e}", "CLOSE NOT COMPLETE [CHECK 5 CONTRACT-DOC]: contract changed but the doc set could not be listed.")
    required = [d for d in WORKER_DOCS if d in present]
    missing = [d for d in required if not _touched(commits, d)]
    fact = f"contract_changed_via={changed[:6]}; required_docs={required or 'none in this corpus'}; missing={missing or 'none'}"
    if missing:
        return _fail(name, fact, f"CLOSE NOT COMPLETE [CHECK 5 CONTRACT-DOC]: worker contract changed but {missing} not committed this close — the packet the worker RUNS is stale.")
    return _ok(name, fact)

def check_secrets(commits, values=()):
    name = "SECRETS"
    pats = [re.compile(p) for p in SECRET_PATTERNS] + [re.compile(re.escape(v)) for v in values if v and len(v) >= 12]
    hits, scanned = [], 0
    for c in commits:
        for p in c["files"]:
            if not p.endswith((".md", ".py", ".txt", ".json", ".yaml", ".yml", ".html", ".sh")): continue
            try: st, blob = _gh_raw(p)
            except Exception: continue
            scanned += 1
            for ln, line in enumerate(blob.splitlines(), 1):
                if any(rx.search(line) for rx in pats):
                    hits.append(f"{p}:{ln}"); break
    fact = f"files_scanned={scanned}; hits={hits or 'none'}"
    if hits:
        return _fail(name, fact, f"CLOSE NOT COMPLETE [CHECK 6 SECRETS]: potential secret in {hits[0]} committed this session — redact + rotate before close. (all hits: {hits})")
    return _ok(name, fact)

def check_state_clean(diag_key):
    name = "STATE"; facts, bad = [], []
    engines = [("MAIN", INSTALL["engine_url"])] + ([("FARM", INSTALL["farm_url"])] if INSTALL.get("farm_url") else [])
    for label, base in engines:
        try:
            st, body = _get(f"{base}/diag/engine", headers={"X-Diag-Key": diag_key}); d = json.loads(body)
            facts.append(f"{label}.running={d.get('running')}")
            if d.get("running") is True: bad.append(f"{label} running")
        except Exception as e:
            facts.append(f"{label} unreachable: {e}"); bad.append(f"{label} unreachable")
    try:
        c = sqlite3.connect(INSTALL["db_path"]); claimed = c.execute("SELECT COUNT(*) FROM seat_mailbox WHERE status='claimed'").fetchone()[0]; c.close()
        facts.append(f"orphaned_claims={claimed}")
        if claimed: bad.append(f"{claimed} orphaned claims")
    except Exception as e:
        facts.append(f"claims query error: {e}"); bad.append("claims unqueryable")
    fact = "; ".join(facts)
    if bad: return _fail(name, fact, f"CLOSE NOT COMPLETE [CHECK 7 STATE]: {' | '.join(bad)} — state not left clean.")
    return _ok(name, fact)

def check_handoff(commits):
    name = "HANDOFF"
    hits = _touched(commits, "live/CONTROL_HANDOFF.md")
    try: st, body = _gh_raw("live/CONTROL_HANDOFF.md")
    except Exception as e:
        return _fail(name, f"CONTROL_HANDOFF unreachable: {e}", "CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: CONTROL_HANDOFF.md unreachable; next seat has no single next action.")
    no_header = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#") or l.lstrip().startswith("##"))
    has_next = bool(re.search(r"^#{1,6}\s*[^\n]*(?:SINGLE NEXT ACTION|NEXT ACTION|NEXT[- ]SEAT)[^\n]*\n+\s*\S", no_header, re.I | re.M))
    fact = f"committed_this_session={hits or 'no'}; has_next_action={has_next}"
    if not has_next:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: handoff missing a single next-action line — next seat has no clear target.")
    if not hits:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 8 HANDOFF]: handoff stale (not committed this session) — next seat would orient onto a stale target.")
    return _ok(name, fact)

def check_orient(seat_session_id, started_at):
    """CHECK 9 — the OPEN ritual ran: an `orient` ledger row belongs to this session."""
    name = "ORIENT"
    try:
        c = sqlite3.connect(INSTALL["db_path"])
        rows = c.execute("SELECT op_id, args, started_at FROM operations_ledger WHERE operation='orient' AND status='ok' AND "
                         "(seat_session_id=? OR (seat_session_id IS NULL AND started_at>=?)) ORDER BY op_id", (seat_session_id, started_at)).fetchall(); c.close()
    except Exception as e:
        return _fail(name, f"ledger query error: {e}", "CLOSE NOT COMPLETE [CHECK 9 ORIENT]: could not query the ledger for this session's orient rows.")
    fact = f"orient_rows_this_session={len(rows)}" + (f"; first={rows[0][1][:80]}" if rows else "")
    if not rows:
        return _fail(name, fact, "CLOSE NOT COMPLETE [CHECK 9 ORIENT]: no `orient` row for this session — the open ritual did not run (or ran without the session key).")
    return _ok(name, fact)

# ---- the gate ----------------------------------------------------------------
def run_gate(seat, seat_session_id, started_at, diag_key, github_token, secret_values=(), contract_items=None, exploration_only=False):
    """Report ALL failing checks in one run. closed == every check passed.
    exploration_only (L6.5): an EXPLICIT declaration by the seat that this session did no corpus work. The gate
    verifies it (zero commits in the window, no contract items) and then closes with the corpus-write checks
    marked N/A; it never infers it, so a seat that forgot its record cannot get a free close."""
    INSTALL["github_token"] = github_token or ""
    result = {"closed": False, "seat": seat, "seat_session_id": seat_session_id, "session_start": started_at, "checks": [], "exploration_only": False}
    miss = [k for k, v in (("started_at", started_at), ("diag_key", diag_key), ("github_token", github_token),
                            ("engine_url", INSTALL["engine_url"]), ("corpus_repo", INSTALL["corpus_repo"]), ("db_path", INSTALL["db_path"])) if not v]
    if miss:
        result["checks"].append(_fail("PRECONDITION", f"missing: {miss}", f"CLOSE NOT COMPLETE [PRECONDITION]: missing {miss} — the session window or install values are undecidable; nothing is inferred."))
        INSTALL["github_token"] = ""; return result
    try:
        commits = _session_commits(started_at)
    except Exception as e:
        result["checks"].append(_fail("PRECONDITION", f"commits API error: {e}", "CLOSE NOT COMPLETE [PRECONDITION]: could not list this session's commits."))
        INSTALL["github_token"] = ""; return result
    result["session_commits"] = [{"sha": c["sha"][:7], "files": c["files"]} for c in commits]
    if exploration_only:
        if commits or (contract_items or []):
            result["checks"].append(_fail("EXPLORATION-ONLY", f"commits_in_window={len(commits)}; contract_items={len(contract_items or [])}",
                                          "CLOSE NOT COMPLETE [EXPLORATION-ONLY]: this session committed work or registered a contract; close it properly, not as exploration."))
            INSTALL["github_token"] = ""; return result
        result["exploration_only"] = True
        checks = [_ok("EXPLORATION-ONLY", "declared by the seat; verified: zero commits in the window, no contract items — corpus-write checks N/A"),
                  check_manual_currency(diag_key), check_state_clean(diag_key)]
        result["checks"] = checks; result["closed"] = all(c["pass"] for c in checks); INSTALL["github_token"] = ""; return result
    checks = [check_punch_list(commits, contract_items), check_conversation(commits), check_queue_fold(commits), check_manual_currency(diag_key),
              check_contract_doc(commits), check_secrets(commits, secret_values), check_state_clean(diag_key), check_handoff(commits),
              check_orient(seat_session_id, started_at)]
    result["checks"] = checks; result["closed"] = all(c["pass"] for c in checks)
    INSTALL["github_token"] = ""
    return result
