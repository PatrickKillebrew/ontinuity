"""box_boot.py — Railway/container entrypoint for an Ontinuity BOX.

Writes config.json from environment variables, then starts file_server.py unchanged.
The box code itself is byte-identical to the operator's install (live/box/* + db.py +
workspace_db_endpoint.py); only this shim is container-specific. "Duplicate what works."

Env consumed:
  DIAG_KEY            required — /op/* auth (same value as the engine's DIAG_KEY)
  BOX_API_KEY         required — X-API-Key for the dashboard/HTTP surface (= engine WORKSPACE_API_KEY)
  CORPUS_REPO         owner/repo of THIS install's corpus (also read by box_ops)
  PORT                listen port (Railway sets; default 5001)
  RAILWAY_TOKEN, RAILWAY_PROJECT_ID, RAILWAY_ENVIRONMENT_ID, RAILWAY_SERVICE_ID_MAIN
                      optional — the box's own deploy/vault hand (only if this install uses /op/deploy)
  ONTINUITY_DB_PATH   optional — put on a volume (e.g. /data/ontinuity.db) so the DB survives redeploys
  ENGINE_URL          this install's engine base URL (the bootstrap gate reads it from config.json)
  FARM_URL            optional second engine; CORPUS_SESSION_FLOOR optional (gate CHECK 3; default 0)
"""
import json, os, sys, runpy

BASE = os.path.dirname(os.path.abspath(__file__))
CFG  = os.path.join(BASE, "config.json")

def need(k):
    v = os.environ.get(k, "").strip()
    if not v:
        print(f"[BOX_BOOT] missing required env {k}", file=sys.stderr); sys.exit(2)
    return v

cfg = {}
if os.path.exists(CFG):
    try: cfg = json.load(open(CFG))
    except Exception: cfg = {}

repo = os.environ.get("CORPUS_REPO", "").strip()
cfg.update({
    "server_port": int(os.environ.get("PORT", "5001")),
    "server_host": "0.0.0.0",
    "api_key":     need("BOX_API_KEY"),
    "diag_key":    need("DIAG_KEY"),
    "max_log_lines": cfg.get("max_log_lines", 100),
    "safe_commands": cfg.get("safe_commands", ["python --version"]),
})
for k, envk in (("engine_url","ENGINE_URL"),("farm_url","FARM_URL"),("corpus_session_floor","CORPUS_SESSION_FLOOR")):
    v = os.environ.get(envk, "").strip()
    if v: cfg[k] = int(v) if k == "corpus_session_floor" else v
for k in ("railway_token","railway_project_id","railway_environment_id","railway_service_id_main"):
    v = os.environ.get(k.upper(), "").strip()
    if v: cfg[k] = v
if not cfg.get("projects"):
    cfg["projects"] = [{"name": os.environ.get("INSTANCE_NAME", "corpus"),
                        "project_dir": BASE,
                        "session_dir": os.path.join(BASE, "sessions"),
                        "github_repo": repo or "PatrickKillebrew/ontinuity"}]
    cfg["active_project"] = cfg["projects"][0]["name"]
elif repo:
    for p in cfg["projects"]: p["github_repo"] = repo

# DB on the volume if provided
dbp = os.environ.get("ONTINUITY_DB_PATH", "").strip()
if dbp: os.makedirs(os.path.dirname(dbp), exist_ok=True)

with open(CFG, "w") as f: json.dump(cfg, f, indent=2)
os.chmod(CFG, 0o600)
print(f"[BOX_BOOT] config.json written; port={cfg['server_port']} repo={cfg['projects'][0]['github_repo']} db={dbp or 'local'}")
sys.argv = ["file_server.py"]
runpy.run_path(os.path.join(BASE, "file_server.py"), run_name="__main__")
