# ── GOVERNOR CONSOLE ──────────────────────────────────────────────────
# Read-only operator observatory. Page served openly (no secrets in it);
# all DATA goes through /governor/data which reuses auth_required (X-API-Key).
# Data is fetched server-side from the diag endpoints, so the browser only
# ever talks same-origin to this server.
import urllib.request as _ug_req, urllib.parse as _ug_parse

_GOV_MAIN = "https://web-production-7eaf8.up.railway.app"
_GOV_FARM = "https://ontinuity-farm-production.up.railway.app"
_GOV_BOUNDARY = "2026-06-08_0"

def _gov_diag(base, path, params):
    cfg = load_config()
    dk = cfg.get("diag_key", "")
    p = dict(params); p["diag_key"] = dk
    url = f"{base}{path}?{_ug_parse.urlencode(p)}"
    try:
        # short timeout: this server is single-threaded and the Governor polls
        # every 6s; a slow upstream must fail fast or polls stack and saturate it.
        return json.loads(_ug_req.urlopen(url, timeout=4).read().decode())
    except Exception as e:
        return {"error": str(e)}

def _gov_q(sql):
    r = _gov_diag(_GOV_MAIN, "/diag/api/query", {"sql": sql})
    try:
        return r["rows"]
    except Exception:
        return None

@app.route("/governor")
def governor_page():
    try:
        with open(os.path.join(os.path.dirname(__file__), "governor.html")) as fh:
            return fh.read()
    except Exception as e:
        return f"governor.html not found beside file_server.py: {e}", 500

@app.route("/governor/data")
@auth_required
def governor_data():
    out = {"boundary": _GOV_BOUNDARY}
    out["main"] = _gov_diag(_GOV_MAIN, "/diag/engine", {})
    out["farm"] = _gov_diag(_GOV_FARM, "/diag/engine", {})
    rnd = _gov_q(f"SELECT COUNT(*) FROM behavioral_observations WHERE randomized_flag=1 AND session_id >= '{_GOV_BOUNDARY}'")
    ses = _gov_q(f"SELECT COUNT(DISTINCT session_id) FROM behavioral_observations WHERE computed_signal IS NOT NULL AND session_id >= '{_GOV_BOUNDARY}'")
    rec = _gov_q("SELECT MAX(receipt_id) FROM write_receipts")
    bks = _gov_q(f"SELECT status, COUNT(*) FROM sessions WHERE session_id >= '{_GOV_BOUNDARY}' GROUP BY status")
    out["randomized"] = rnd[0][0] if rnd else None
    out["sessions"] = ses[0][0] if ses else None
    out["receipt"] = rec[0][0] if rec else None
    out["buckets"] = {row[0]: row[1] for row in bks} if bks else {}
    return jsonify(out)
