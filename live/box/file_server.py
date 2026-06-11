"""
ONTINUITY WORKSPACE SERVER  v2.0
=================================
Persistent local server giving any AI assistant direct read/write access
to your project files — without going through any cloud intermediary.

What this solves:
  - AI assistants lose context between conversations
  - Copy-pasting code changes is slow and error-prone
  - GitHub caching makes AI reads unreliable
  - No persistent memory of decisions made across sessions

Endpoints:
  GET  /              -> dashboard UI
  GET  /status        -> server health
  GET  /settings      -> config (auth required)
  POST /settings      -> update config (auth required)
  GET  /workspace     -> full project context for AI (auth required)
  POST /workspace     -> update workspace state (auth required)
  GET  /projects      -> list all projects (auth required)
  POST /projects      -> create project (auth required)
  POST /projects/switch -> switch active project (auth required)
  GET  /read?file=X   -> read file (auth required)
  POST /write         -> write file with diff + push (auth required)
  POST /run           -> whitelisted command (auth required)
  GET  /log           -> live session log tail (auth required)
  GET  /history       -> change history list (auth required)
  GET  /history/<id>  -> specific change (auth required)
  POST /rollback      -> restore file to previous version (auth required)
  GET  /manifest      -> latest push manifest (auth required)
  POST /api/session   -> receive Ontinuity session data (workspace_db_endpoint)
  GET  /api/ledger    -> query Established Results Ledger
  GET  /api/project_state -> Projenius ORIENT feed
  GET  /api/behavioral_corpus -> Psychology of AI Data corpus
  GET  /api/health    -> database health check
"""

import json
import os, json, glob, uuid, difflib, secrets, subprocess, threading, platform, urllib.parse
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, render_template_string

# ── Ontinuity database integration ───────────────────────────────────
try:
    from workspace_db_endpoint import db_blueprint, init_db
    DB_INTEGRATION = True
except ImportError:
    DB_INTEGRATION = False
    print("[SERVER] workspace_db_endpoint.py not found — database endpoints disabled.")

app = Flask(__name__)

if DB_INTEGRATION:
    app.register_blueprint(db_blueprint)
    from seat_mailbox import seat_mailbox_bp
    app.register_blueprint(seat_mailbox_bp)
    from box_ops import box_ops_bp
    app.register_blueprint(box_ops_bp)
    # Launch the shepherd detect-and-alert loop as a daemon thread (built SHEP-1,
    # wired to start with the workspace so restart_workspace brings it up).
    try:
        import threading, shepherd_alert
        threading.Thread(target=shepherd_alert.main, daemon=True, name="shepherd").start()
        print("[startup] shepherd_alert daemon launched")
    except Exception as _e:
        print("[startup] shepherd launch failed:", _e)

# ── PATHS ─────────────────────────────────────────────────────────────

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH    = os.path.join(BASE_DIR, "config.json")
WORKSPACE_PATH = os.path.join(BASE_DIR, "workspace_state.json")
HISTORY_DIR    = os.path.join(BASE_DIR, ".workspace", "changes")
AUDIT_LOG_PATH = os.path.join(BASE_DIR, ".workspace", "audit.log")
os.makedirs(HISTORY_DIR, exist_ok=True)

# ── CONFIG ────────────────────────────────────────────────────────────

_cfg_lock = threading.Lock()

DEFAULT_PROJECT = {
    "name":        "My Project",
    "project_dir": BASE_DIR,
    "session_dir": os.path.join(BASE_DIR, "sessions"),
    "github_repo": ""
}

DEFAULT_CONFIG = {
    "projects":       [DEFAULT_PROJECT],
    "active_project": "My Project",
    "server_port":    5001,
    "server_host":    "0.0.0.0",
    "max_log_lines":  100,
    "duckdns_domain": "",
    "duckdns_token":  "",
    "api_key":        "",
    "safe_commands":  ["python push_to_github.py", "python --version", "pip list"]
}

def load_config():
    with _cfg_lock:
        if not os.path.exists(CONFIG_PATH):
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            data.setdefault(k, v)
        return data

def save_config(cfg):
    with _cfg_lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

def active_project(cfg):
    name = cfg.get("active_project", "")
    for p in cfg.get("projects", []):
        if p["name"] == name:
            return p
    projects = cfg.get("projects", [])
    return projects[0] if projects else DEFAULT_PROJECT.copy()

# ── WORKSPACE STATE ───────────────────────────────────────────────────

DEFAULT_WORKSPACE = {
    "project":      "",
    "description":  "",
    "last_updated": "",
    "current_state": {
        "summary":       "Project initialized",
        "active_files":  [],
        "pending_items": [],
        "known_issues":  []
    },
    "decisions": [],
    "sessions":  [],
    "context_for_ai": ""
}

def load_workspace():
    if not os.path.exists(WORKSPACE_PATH):
        ws = DEFAULT_WORKSPACE.copy()
        ws["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_workspace(ws)
        return ws
    with open(WORKSPACE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_workspace(ws):
    ws["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(WORKSPACE_PATH, "w", encoding="utf-8") as f:
        json.dump(ws, f, indent=2)

# ── CHANGE HISTORY ────────────────────────────────────────────────────

def record_change(filename, old_content, new_content, description=""):
    change_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()
    diff_lines = list(difflib.unified_diff(
        (old_content or "").splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile="before/" + filename,
        tofile="after/" + filename,
        lineterm=""
    ))
    diff_text = "".join(diff_lines)
    changed   = len([l for l in diff_lines if l.startswith(("+","-")) and not l.startswith(("+++","---"))])
    change = {
        "id": change_id, "timestamp": timestamp, "file": filename,
        "description": description, "diff": diff_text,
        "old_content": old_content or "", "new_content": new_content,
        "lines_changed": changed
    }
    path = os.path.join(HISTORY_DIR, timestamp[:10] + "_" + change_id + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(change, f, indent=2)
    return change_id, diff_text

def list_history(limit=50):
    files = sorted(glob.glob(os.path.join(HISTORY_DIR, "*.json")), reverse=True)
    results = []
    for path in files[:limit]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                ch = json.load(f)
            results.append({
                "id": ch["id"], "timestamp": ch["timestamp"],
                "file": ch["file"], "description": ch.get("description",""),
                "lines_changed": ch.get("lines_changed", 0)
            })
        except Exception:
            pass
    return results

def get_change(change_id):
    files = glob.glob(os.path.join(HISTORY_DIR, "*_" + change_id + ".json"))
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)

# ── SERVER STATE ──────────────────────────────────────────────────────

server_state = {"started_at": datetime.now().isoformat(), "writes": [], "commands": []}
state_lock   = threading.Lock()

def log_write(filename, pushed, change_id):
    with state_lock:
        server_state["writes"].append({
            "file": filename, "timestamp": datetime.now().isoformat(),
            "pushed": pushed, "change_id": change_id
        })
        if len(server_state["writes"]) > 100:
            server_state["writes"].pop(0)

def log_cmd(command, returncode):
    with state_lock:
        server_state["commands"].append({
            "command": command, "timestamp": datetime.now().isoformat(),
            "returncode": returncode
        })
        if len(server_state["commands"]) > 30:
            server_state["commands"].pop(0)

def audit(action, detail="", extra=None):
    """Append-only audit log. Every read, write, command, and session POST
    is recorded here before the response is returned. Never truncated."""
    entry = {
        "ts":     datetime.now(timezone.utc).isoformat(),
        "ip":     request.remote_addr if request else "internal",
        "action": action,
        "detail": detail,
    }
    if extra:
        entry.update(extra)
    line = json.dumps(entry, separators=(",", ":")) + "\n"
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[AUDIT] Write failed: {e}")

# ── AUTH ──────────────────────────────────────────────────────────────

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cfg = load_config()
        key = cfg.get("api_key", "")
        if key and not secrets.compare_digest(request.headers.get("X-API-Key",""), key):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── HELPERS ───────────────────────────────────────────────────────────

def safe_path(filename, project):
    pd   = project["project_dir"]
    full = os.path.normpath(os.path.join(pd, filename))
    return full if full.startswith(os.path.normpath(pd)) else None

def active_session_log(project):
    sd    = project.get("session_dir", os.path.join(project["project_dir"], "sessions"))
    files = glob.glob(os.path.join(sd, "session_*.txt"))
    return max(files, key=os.path.getmtime) if files else None

def push_file_cmd(filepath, project):
    script = os.path.join(project["project_dir"], "push_to_github.py")
    if not os.path.exists(script):
        return False, "push_to_github.py not found"
    try:
        r = subprocess.run(["python", script, filepath],
                           capture_output=True, text=True, timeout=30,
                           cwd=project["project_dir"])
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)

def command_is_safe(command, cfg):
    return command.strip() in cfg.get("safe_commands", [])

# ── ENDPOINTS ─────────────────────────────────────────────────────────

@app.route("/status")
@auth_required
def status():
    cfg = load_config()
    p   = active_project(cfg)
    log = active_session_log(p)
    with state_lock:
        return jsonify({
            "status": "running", "version": "2.0",
            "platform": platform.system(),
            "started_at": server_state["started_at"],
            "active_project": p["name"],
            "project_dir": p["project_dir"],
            "github_repo": p.get("github_repo",""),
            "duckdns_domain": cfg.get("duckdns_domain",""),
            "active_session": os.path.basename(log) if log else None,
            "recent_writes": server_state["writes"][-10:],
            "recent_commands": server_state["commands"][-5:],
            "db_integration": DB_INTEGRATION,
        })

@app.route("/settings", methods=["GET"])
@auth_required
def get_settings():
    cfg  = load_config()
    safe = {k:v for k,v in cfg.items() if k != "api_key"}
    safe["api_key_set"] = bool(cfg.get("api_key"))
    return jsonify(safe)

@app.route("/settings", methods=["POST"])
@auth_required
def update_settings():
    data = request.json or {}
    cfg  = load_config()
    for field in ["active_project","server_port","max_log_lines",
                  "duckdns_domain","duckdns_token","safe_commands"]:
        if field in data:
            cfg[field] = data[field]
    if data.get("api_key"):
        cfg["api_key"] = data["api_key"]
    save_config(cfg)
    return jsonify({"status": "saved", "timestamp": datetime.now().isoformat()})

@app.route("/workspace", methods=["GET"])
@auth_required
def get_workspace():
    ws  = load_workspace()
    cfg = load_config()
    p   = active_project(cfg)
    log = active_session_log(p)
    return jsonify({
        "workspace":      ws,
        "active_project": p["name"],
        "project_dir":    p["project_dir"],
        "github_repo":    p.get("github_repo",""),
        "active_session": os.path.basename(log) if log else None,
        "recent_changes": list_history(10),
        "server_url":     request.host_url.rstrip("/"),
        "fetched_at":     datetime.now(timezone.utc).isoformat()
    })

@app.route("/workspace", methods=["POST"])
@auth_required
def update_workspace():
    data = request.json or {}
    ws   = load_workspace()
    for field in ["project","description","context_for_ai"]:
        if field in data:
            ws[field] = data[field]
    if "current_state" in data:
        ws.setdefault("current_state", {})
        ws["current_state"].update(data["current_state"])
    if "decision" in data:
        ws.setdefault("decisions", [])
        ws["decisions"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision":  data["decision"],
            "rationale": data.get("rationale","")
        })
        ws["decisions"] = ws["decisions"][-100:]
    if "session" in data:
        ws.setdefault("sessions", [])
        ws["sessions"].append({"timestamp": datetime.now(timezone.utc).isoformat(), **data["session"]})
        ws["sessions"] = ws["sessions"][-50:]
    save_workspace(ws)
    return jsonify({"status":"updated","timestamp":ws["last_updated"]})

@app.route("/projects", methods=["GET"])
@auth_required
def list_projects():
    cfg = load_config()
    return jsonify({"projects": cfg.get("projects",[]), "active_project": cfg.get("active_project","")})

@app.route("/projects", methods=["POST"])
@auth_required
def create_project():
    data = request.json or {}
    name = data.get("name","").strip()
    if not name:
        return jsonify({"error":"name required"}), 400
    cfg = load_config()
    cfg.setdefault("projects",[])
    if any(p["name"]==name for p in cfg["projects"]):
        return jsonify({"error":"project already exists"}), 409
    cfg["projects"].append({
        "name": name,
        "project_dir": data.get("project_dir", BASE_DIR),
        "session_dir": data.get("session_dir", os.path.join(BASE_DIR,"sessions")),
        "github_repo": data.get("github_repo","")
    })
    save_config(cfg)
    return jsonify({"status":"created","name":name})

@app.route("/projects/switch", methods=["POST"])
@auth_required
def switch_project():
    data = request.json or {}
    name = data.get("name","").strip()
    cfg  = load_config()
    if not any(p["name"]==name for p in cfg.get("projects",[])):
        return jsonify({"error": "project not found"}), 404
    cfg["active_project"] = name
    save_config(cfg)
    return jsonify({"status":"switched","active_project":name})

@app.route("/read")
@auth_required
def read_file():
    cfg      = load_config()
    project  = active_project(cfg)
    filename = request.args.get("file")
    if not filename:
        return jsonify({"error":"missing ?file= parameter"}), 400
    full_path = safe_path(filename, project)
    if not full_path:
        return jsonify({"error":"path traversal rejected"}), 403
    if not os.path.exists(full_path):
        return jsonify({"error":"file not found: "+filename}), 404
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        audit("READ", filename, {"size": len(content)})
        return jsonify({
            "file": filename, "content": content, "size": len(content),
            "mtime": datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
        })
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/write", methods=["POST"])
@auth_required
def write_file():
    cfg         = load_config()
    project     = active_project(cfg)
    data        = request.json or {}
    filename    = data.get("filename")
    content     = data.get("content")
    auto_push   = data.get("push", True)
    diff_only   = data.get("diff_only", False)
    description = data.get("description", "")

    if not filename or content is None:
        return jsonify({"error":"missing filename or content"}), 400
    full_path = safe_path(filename, project)
    if not full_path:
        return jsonify({"error":"path traversal rejected"}), 403

    old_content = None
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.read()
        except Exception:
            pass

    diff_lines = list(difflib.unified_diff(
        (old_content or "").splitlines(keepends=True),
        content.splitlines(keepends=True),
        fromfile="current/"+filename, tofile="incoming/"+filename, lineterm=""
    ))
    diff_text = "".join(diff_lines)

    if diff_only:
        return jsonify({"file":filename,"diff":diff_text,"status":"diff_only"})

    try:
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return jsonify({"error":"write failed: "+str(e)}), 500

    change_id, _ = record_change(filename, old_content, content, description)
    pushed, push_output = False, None
    if auto_push:
        pushed, push_output = push_file_cmd(full_path, project)
    log_write(filename, pushed, change_id)
    audit("WRITE", filename, {"change_id": change_id, "pushed": pushed, "lines_changed": changed})
    changed = len([l for l in diff_lines if l.startswith(("+","-")) and not l.startswith(("+++","---"))])

    return jsonify({
        "status":"written", "file":filename, "change_id":change_id,
        "pushed":pushed, "push_output":push_output,
        "diff":diff_text, "lines_changed":changed,
        "timestamp":datetime.now().isoformat()
    })

@app.route("/run", methods=["POST"])
@auth_required
def run_command():
    cfg     = load_config()
    project = active_project(cfg)
    data    = request.json or {}
    command = data.get("command","").strip()
    if not command:
        return jsonify({"error":"no command provided"}), 400
    if not command_is_safe(command, cfg):
        return jsonify({"error":"not in whitelist","safe_commands":cfg.get("safe_commands",[])}), 403
    try:
        r = subprocess.run(command, shell=True, cwd=project["project_dir"],
                           capture_output=True, text=True, timeout=30)
        log_cmd(command, r.returncode)
        audit("CMD", command, {"returncode": r.returncode})
        return jsonify({"command":command,"stdout":r.stdout,"stderr":r.stderr,
                        "returncode":r.returncode,"timestamp":datetime.now().isoformat()})
    except subprocess.TimeoutExpired:
        return jsonify({"error":"timed out"}), 408
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/log")
@auth_required
def get_log():
    cfg     = load_config()
    project = active_project(cfg)
    n       = int(request.args.get("lines", cfg.get("max_log_lines",100)))
    log_path = active_session_log(project)
    if not log_path:
        return jsonify({"error":"no active session log found"}), 404
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return jsonify({"session":os.path.basename(log_path),"total":len(lines),
                        "content":"".join(lines[-n:]),"timestamp":datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/history")
@auth_required
def history():
    limit = int(request.args.get("limit", 50))
    return jsonify({"changes": list_history(limit)})

@app.route("/history/<change_id>")
@auth_required
def history_detail(change_id):
    ch = get_change(change_id)
    if not ch:
        return jsonify({"error":"change not found"}), 404
    return jsonify(ch)

@app.route("/rollback", methods=["POST"])
@auth_required
def rollback():
    cfg     = load_config()
    project = active_project(cfg)
    data    = request.json or {}
    change_id = data.get("change_id")
    if not change_id:
        return jsonify({"error":"change_id required"}), 400
    ch = get_change(change_id)
    if not ch:
        return jsonify({"error":"change not found"}), 404

    full_path = safe_path(ch["file"], project)
    if not full_path:
        return jsonify({"error":"path traversal rejected"}), 403

    current = ""
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            current = f.read()

    old_content = ch.get("old_content","")
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(old_content)
    except Exception as e:
        return jsonify({"error":"rollback write failed: "+str(e)}), 500

    new_change_id, diff_text = record_change(
        ch["file"], current, old_content,
        description="Rollback to " + change_id
    )

    pushed, push_output = False, None
    if data.get("push", True):
        pushed, push_output = push_file_cmd(full_path, project)

    log_write(ch["file"], pushed, new_change_id)
    return jsonify({
        "status":"rolled_back", "file":ch["file"],
        "rolled_back_to":change_id, "new_change_id":new_change_id,
        "pushed":pushed, "push_output":push_output,
        "timestamp":datetime.now().isoformat()
    })

@app.route("/manifest")
@auth_required
def get_manifest():
    cfg  = load_config()
    p    = active_project(cfg)
    path = os.path.join(p["project_dir"], "manifest.json")
    if not os.path.exists(path):
        return jsonify({"error":"no manifest found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

# ── DASHBOARD ─────────────────────────────────────────────────────────

DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ontinuity Workspace</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Courier New',monospace;background:#0d1117;color:#c9d1d9;padding:16px;min-height:100vh}
h1{color:#58a6ff;font-size:1.3em}
.sub{color:#8b949e;font-size:.8em;margin-bottom:14px}
nav{display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid #21262d;padding-bottom:8px;flex-wrap:wrap}
nav button{background:none;border:none;color:#8b949e;padding:6px 12px;cursor:pointer;font-family:inherit;font-size:.82em;border-radius:4px}
nav button.active,nav button:hover{background:#21262d;color:#c9d1d9}
.tab{display:none}.tab.active{display:block}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.panel{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px}
.panel h2{color:#58a6ff;font-size:.78em;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#3fb950;margin-right:6px}
.dot.off{background:#f85149}
table{width:100%;border-collapse:collapse;font-size:.78em}
td,th{padding:5px 8px;border-bottom:1px solid #21262d}
th{color:#8b949e;font-weight:normal;text-align:left}
.log{background:#0d1117;border:1px solid #21262d;border-radius:4px;padding:10px;font-size:.73em;height:300px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.deep{color:#58a6ff}.near{color:#3fb950}.ods{color:#d2a8ff}.err{color:#f85149}
input,textarea,select{width:100%;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:6px 8px;font-family:inherit;font-size:.82em;margin-top:4px;margin-bottom:10px}
textarea{height:80px;resize:vertical}
label{color:#8b949e;font-size:.78em}
.btn{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:5px 12px;cursor:pointer;font-family:inherit;font-size:.8em}
.btn:hover{background:#30363d}
.btn.p{background:#1f6feb;border-color:#1f6feb;color:#fff}.btn.p:hover{background:#388bfd}
.btn.danger{background:#3d1f1f;border-color:#f85149;color:#f85149}
.badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:.7em}
.ok{background:#1f3d2a;color:#3fb950}.fail{background:#3d1f1f;color:#f85149}
.msg{font-size:.78em;margin-top:8px;min-height:16px}
.msg.ok{color:#3fb950}.msg.fail{color:#f85149}
.ws-field{background:#0d1117;border:1px solid #21262d;border-radius:4px;padding:8px;font-size:.78em;margin-bottom:8px;color:#c9d1d9;min-height:40px;white-space:pre-wrap;word-break:break-all}
.diff{font-size:.72em;height:200px;overflow-y:auto;white-space:pre;background:#0d1117;border:1px solid #21262d;border-radius:4px;padding:8px}
.diff .add{color:#3fb950}.diff .del{color:#f85149}.diff .meta{color:#8b949e}
.proj-badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.72em;background:#1f3d2a;color:#3fb950;margin-right:4px}
@media(max-width:680px){.g2,.g3{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>&#x2B21; Ontinuity Workspace</h1>
<div class="sub" id="sub">Connecting...</div>

<nav>
  <button class="active" onclick="TAB('dash',this)">Dashboard</button>
  <button onclick="TAB('workspace',this)">Workspace</button>
  <button onclick="TAB('log',this)">Session Log</button>
  <button onclick="TAB('history',this)">History</button>
  <button onclick="TAB('projects',this)">Projects</button>
  <button onclick="TAB('settings',this)">Settings</button>
</nav>

<!-- ── DASHBOARD ── -->
<div id="tab-dash" class="tab active">
  <div class="g2">
    <div class="panel">
      <h2>Status</h2>
      <table>
        <tr><th>Server</th><td><span class="dot" id="dot"></span><span id="ss">checking</span></td></tr>
        <tr><th>Project</th><td id="sp">-</td></tr>
        <tr><th>Repo</th><td id="sr">-</td></tr>
        <tr><th>Session</th><td id="se">-</td></tr>
        <tr><th>Domain</th><td id="sd">-</td></tr>
        <tr><th>Started</th><td id="st">-</td></tr>
        <tr><th>Database</th><td id="sdb">-</td></tr>
      </table>
    </div>
    <div class="panel">
      <h2>Recent Writes</h2>
      <table>
        <tr><th>File</th><th>Time</th><th>Pushed</th><th></th></tr>
        <tbody id="wb"><tr><td colspan="4" style="color:#8b949e">No writes yet</td></tr></tbody>
      </table>
    </div>
    <div class="panel" style="grid-column:1/-1">
      <h2>Run Command</h2>
      <select id="cmdsel"></select>
      <button class="btn p" onclick="runCmd()" style="margin-top:4px">Run</button>
      <div class="log" id="cmdout" style="height:100px;margin-top:8px"></div>
    </div>
  </div>
</div>

<!-- ── WORKSPACE (AI MEMORY) ── -->
<div id="tab-workspace" class="tab">
  <div class="g2">
    <div class="panel">
      <h2>Current State</h2>
      <label>Summary</label>
      <div class="ws-field" id="ws-summary">Loading...</div>
      <label>Known Issues</label>
      <div class="ws-field" id="ws-issues">Loading...</div>
      <label>Pending Items</label>
      <div class="ws-field" id="ws-pending">Loading...</div>
    </div>
    <div class="panel">
      <h2>Recent Decisions</h2>
      <div class="ws-field" id="ws-decisions" style="height:200px;overflow-y:auto">Loading...</div>
      <h2 style="margin-top:12px">Context for AI</h2>
      <div class="ws-field" id="ws-context">Loading...</div>
    </div>
    <div class="panel" style="grid-column:1/-1">
      <h2>Update Workspace</h2>
      <div class="g3">
        <div>
          <label>State Summary</label>
          <textarea id="upd-summary" placeholder="What is the current state of the project?"></textarea>
        </div>
        <div>
          <label>Known Issues (one per line)</label>
          <textarea id="upd-issues" placeholder="Issue 1&#10;Issue 2"></textarea>
        </div>
        <div>
          <label>Pending Items (one per line)</label>
          <textarea id="upd-pending" placeholder="Next step 1&#10;Next step 2"></textarea>
        </div>
      </div>
      <label>Record a Decision</label>
      <input type="text" id="upd-decision" placeholder="Decision made...">
      <label>Rationale</label>
      <input type="text" id="upd-rationale" placeholder="Why...">
      <button class="btn p" onclick="saveWorkspace()">Update Workspace</button>
      <div class="msg" id="ws-msg"></div>
    </div>
  </div>
</div>

<!-- ── SESSION LOG ── -->
<div id="tab-log" class="tab">
  <div class="panel">
    <h2>Live Session Log &nbsp;<span id="logname" style="color:#8b949e;font-size:.85em"></span></h2>
    <div class="log" id="logview">Waiting for session...</div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:8px">
      <label>Refresh:</label>
      <select id="rrate" onchange="setRefresh()" style="width:auto;margin:0">
        <option value="3000">3s</option>
        <option value="5000" selected>5s</option>
        <option value="10000">10s</option>
        <option value="0">Off</option>
      </select>
      <span id="lupd" style="color:#8b949e;font-size:.75em"></span>
    </div>
  </div>
</div>

<!-- ── HISTORY ── -->
<div id="tab-history" class="tab">
  <div class="panel">
    <h2>Change History</h2>
    <table>
      <tr><th>ID</th><th>File</th><th>Description</th><th>Lines</th><th>Time</th><th></th></tr>
      <tbody id="hist-body"><tr><td colspan="6" style="color:#8b949e">Loading...</td></tr></tbody>
    </table>
  </div>
  <div class="panel" id="diff-panel" style="margin-top:12px;display:none">
    <h2>Change Detail &nbsp;<span id="diff-id" style="color:#8b949e"></span></h2>
    <div class="diff" id="diff-view"></div>
    <div style="margin-top:8px">
      <button class="btn danger" onclick="doRollback()" id="rollback-btn">Rollback to Before This Change</button>
      <div class="msg" id="rollback-msg"></div>
    </div>
  </div>
</div>

<!-- ── PROJECTS ── -->
<div id="tab-projects" class="tab">
  <div class="g2">
    <div class="panel">
      <h2>Projects</h2>
      <div id="proj-list"></div>
    </div>
    <div class="panel">
      <h2>Add Project</h2>
      <label>Name</label>
      <input type="text" id="new-proj-name" placeholder="My Project">
      <label>Project Directory</label>
      <input type="text" id="new-proj-dir" placeholder="C:\myproject">
      <label>Session Directory</label>
      <input type="text" id="new-proj-sessions" placeholder="C:\myproject\sessions">
      <label>GitHub Repo</label>
      <input type="text" id="new-proj-repo" placeholder="username/reponame">
      <button class="btn p" onclick="createProject()">Add Project</button>
      <div class="msg" id="proj-msg"></div>
    </div>
  </div>
</div>

<!-- ── SETTINGS ── -->
<div id="tab-settings" class="tab">
  <div class="g2">
    <div class="panel">
      <h2>Network</h2>
      <label>DuckDNS Domain (e.g. myname.duckdns.org)</label>
      <input type="text" id="c-duckdns_domain">
      <label>DuckDNS Token</label>
      <input type="password" id="c-duckdns_token">
      <label>Server Port</label>
      <input type="number" id="c-server_port" min="1024" max="65535">
      <label>Max Log Lines</label>
      <input type="number" id="c-max_log_lines" min="10" max="500">
    </div>
    <div class="panel">
      <h2>Security</h2>
      <label>API Key (blank = keep current)</label>
      <input type="password" id="c-api_key" placeholder="Enter new key or leave blank">
      <div style="color:#8b949e;font-size:.75em;margin-bottom:10px">
        Current: <span id="keyst">checking...</span>
      </div>
      <button class="btn" onclick="genKey()">Generate Random Key</button>
      <p style="color:#8b949e;font-size:.72em;margin-top:8px">
        After setting a key, save it in your browser or a password manager.
        The key is stored in config.json on your laptop.
      </p>
    </div>
    <div class="panel" style="grid-column:1/-1">
      <h2>Safe Commands</h2>
      <label>One per line — exact match required for execution</label>
      <textarea id="c-safe_commands" style="height:120px"></textarea>
    </div>
    <div class="panel" style="grid-column:1/-1">
      <button class="btn p" onclick="saveSettings()">Save Settings</button>
      <button class="btn" onclick="loadSettings()" style="margin-left:8px">Reload</button>
      <div class="msg" id="smsg"></div>
    </div>
  </div>
</div>

<script>
let KEY = localStorage.getItem('ok') || '';
let logTimer = null;
let currentChangeId = null;

function H(){ return {'Content-Type':'application/json','X-API-Key':KEY}; }

function TAB(name, btn){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  btn.classList.add('active');
  const actions = {
    log: refreshLog, settings: loadSettings,
    workspace: loadWorkspace, history: loadHistory, projects: loadProjects
  };
  if(actions[name]) actions[name]();
}

// ── Status ──
async function refreshStatus(){
  try{
    const r=await fetch('/status',{headers:H()});
    if(r.status===401){document.getElementById('ss').textContent='Set API key in Settings';return;}
    const d=await r.json();
    document.getElementById('dot').className='dot';
    document.getElementById('ss').textContent='Running v'+d.version;
    document.getElementById('sp').textContent=d.active_project;
    document.getElementById('sr').textContent=d.github_repo||'Not configured';
    document.getElementById('se').textContent=d.active_session||'None';
    document.getElementById('sd').textContent=d.duckdns_domain||'Not configured';
    document.getElementById('st').textContent=d.started_at.replace('T',' ').slice(0,19);
    document.getElementById('sdb').textContent=d.db_integration?'Connected':'Not configured';
    document.getElementById('sub').textContent='Connected \u00b7 '+window.location.host+' \u00b7 '+new Date().toLocaleTimeString();
    const tb=document.getElementById('wb');
    if(d.recent_writes&&d.recent_writes.length)
      tb.innerHTML=d.recent_writes.slice().reverse().map(w=>
        `<tr><td>${w.file}</td><td>${w.timestamp.slice(11,19)}</td>
         <td><span class="badge ${w.pushed?'ok':'fail'}">${w.pushed?'yes':'no'}</span></td>
         <td><button class="btn" onclick="showChange('${w.change_id}')" style="padding:2px 6px;font-size:.7em">diff</button></td></tr>`
      ).join('');
  }catch(e){
    document.getElementById('dot').className='dot off';
    document.getElementById('ss').textContent='Offline';
  }
}

// ── Log ──
function colorize(t){
  return t.replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\[DEEP\][^\n]*/g,m=>`<span class="deep">${m}</span>`)
    .replace(/\[NEAR\][^\n]*/g,m=>`<span class="near">${m}</span>`)
    .replace(/\[ODS\][^\n]*/g, m=>`<span class="ods">${m}</span>`)
    .replace(/Error[^\n]*/g,   m=>`<span class="err">${m}</span>`);
}
async function refreshLog(){
  try{
    const r=await fetch('/log?lines=100',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    const el=document.getElementById('logview');
    const at=el.scrollTop+el.clientHeight>=el.scrollHeight-30;
    el.innerHTML=colorize(d.content);
    if(at)el.scrollTop=el.scrollHeight;
    document.getElementById('logname').textContent=d.session||'';
    document.getElementById('lupd').textContent='Updated '+new Date().toLocaleTimeString();
  }catch(e){}
}
function setRefresh(){
  if(logTimer)clearInterval(logTimer);
  const rate=parseInt(document.getElementById('rrate').value);
  if(rate>0)logTimer=setInterval(refreshLog,rate);
}

// ── Commands ──
async function loadCmds(){
  try{
    const r=await fetch('/settings',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    const sel=document.getElementById('cmdsel');
    sel.innerHTML='<option value="">&#x2014; select command &#x2014;</option>'+
      (d.safe_commands||[]).map(c=>`<option value="${c}">${c}</option>`).join('');
  }catch(e){}
}
async function runCmd(){
  const command=document.getElementById('cmdsel').value;
  if(!command)return;
  const out=document.getElementById('cmdout');
  out.textContent='Running...';
  try{
    const r=await fetch('/run',{method:'POST',headers:H(),body:JSON.stringify({command})});
    const d=await r.json();
    out.textContent=d.error?'Error: '+d.error:(d.stdout||'')+(d.stderr?'\n[stderr]\n'+d.stderr:'');
  }catch(e){out.textContent='Failed: '+e;}
}

// ── Workspace ──
async function loadWorkspace(){
  try{
    const r=await fetch('/workspace',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    const ws=d.workspace||{};
    const cs=ws.current_state||{};
    document.getElementById('ws-summary').textContent=cs.summary||'Not set';
    document.getElementById('ws-issues').textContent=(cs.known_issues||[]).join('\n')||'None';
    document.getElementById('ws-pending').textContent=(cs.pending_items||[]).join('\n')||'None';
    document.getElementById('ws-context').textContent=ws.context_for_ai||'Not set';
    const decs=(ws.decisions||[]).slice(-10).reverse();
    document.getElementById('ws-decisions').textContent=
      decs.length ? decs.map(d=>`[${d.timestamp.slice(0,10)}] ${d.decision}`+
        (d.rationale?'\n  '+d.rationale:'')).join('\n\n') : 'No decisions recorded';
  }catch(e){}
}
async function saveWorkspace(){
  const msg=document.getElementById('ws-msg');
  const payload={};
  const summary=document.getElementById('upd-summary').value.trim();
  const issues=document.getElementById('upd-issues').value.trim();
  const pending=document.getElementById('upd-pending').value.trim();
  const decision=document.getElementById('upd-decision').value.trim();
  const rationale=document.getElementById('upd-rationale').value.trim();

  if(summary||issues||pending){
    payload.current_state={};
    if(summary) payload.current_state.summary=summary;
    if(issues)  payload.current_state.known_issues=issues.split('\n').map(s=>s.trim()).filter(Boolean);
    if(pending) payload.current_state.pending_items=pending.split('\n').map(s=>s.trim()).filter(Boolean);
  }
  if(decision){ payload.decision=decision; if(rationale) payload.rationale=rationale; }

  try{
    const r=await fetch('/workspace',{method:'POST',headers:H(),body:JSON.stringify(payload)});
    const d=await r.json();
    msg.textContent=d.status==='updated'?'Workspace updated \u2713':'Error: '+JSON.stringify(d);
    msg.className='msg '+(d.status==='updated'?'ok':'fail');
    if(d.status==='updated'){
      document.getElementById('upd-summary').value='';
      document.getElementById('upd-issues').value='';
      document.getElementById('upd-pending').value='';
      document.getElementById('upd-decision').value='';
      document.getElementById('upd-rationale').value='';
      loadWorkspace();
    }
  }catch(e){msg.textContent='Failed: '+e;msg.className='msg fail';}
}

// ── History ──
async function loadHistory(){
  try{
    const r=await fetch('/history?limit=30',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    const tb=document.getElementById('hist-body');
    if(!d.changes||!d.changes.length){
      tb.innerHTML='<tr><td colspan="6" style="color:#8b949e">No changes recorded yet</td></tr>';
      return;
    }
    tb.innerHTML=d.changes.map(c=>
      `<tr>
        <td style="font-family:monospace;color:#58a6ff">${c.id}</td>
        <td>${c.file}</td>
        <td style="color:#8b949e">${c.description||'-'}</td>
        <td>${c.lines_changed}</td>
        <td>${c.timestamp.slice(0,16).replace('T',' ')}</td>
        <td><button class="btn" onclick="showChange('${c.id}')" style="padding:2px 6px;font-size:.7em">view</button></td>
      </tr>`
    ).join('');
  }catch(e){}
}
async function showChange(id){
  currentChangeId=id;
  try{
    const r=await fetch('/history/'+id,{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    document.getElementById('diff-id').textContent=id+' \u2014 '+d.file;
    const dv=document.getElementById('diff-view');
    dv.innerHTML=(d.diff||'No diff available').split('\n').map(line=>{
      if(line.startsWith('+++')|| line.startsWith('---')) return `<span class="meta">${line}</span>`;
      if(line.startsWith('+')) return `<span class="add">${line}</span>`;
      if(line.startsWith('-')) return `<span class="del">${line}</span>`;
      if(line.startsWith('@@')) return `<span class="meta">${line}</span>`;
      return line;
    }).join('\n');
    document.getElementById('diff-panel').style.display='block';
    document.getElementById('rollback-msg').textContent='';
    document.getElementById('diff-panel').scrollIntoView({behavior:'smooth'});
    if(document.getElementById('tab-history').classList.contains('active')){}
    else{ TAB('history', document.querySelector('nav button:nth-child(4)')); }
  }catch(e){}
}
async function doRollback(){
  if(!currentChangeId)return;
  if(!confirm('Roll back to before change '+currentChangeId+'? This will overwrite the current file.'))return;
  const msg=document.getElementById('rollback-msg');
  try{
    const r=await fetch('/rollback',{method:'POST',headers:H(),
                        body:JSON.stringify({change_id:currentChangeId,push:true})});
    const d=await r.json();
    msg.textContent=d.status==='rolled_back'?'Rolled back \u2713 new change id: '+d.new_change_id:'Error: '+JSON.stringify(d);
    msg.className='msg '+(d.status==='rolled_back'?'ok':'fail');
    if(d.status==='rolled_back')loadHistory();
  }catch(e){msg.textContent='Failed: '+e;msg.className='msg fail';}
}

// ── Projects ──
async function loadProjects(){
  try{
    const r=await fetch('/projects',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    const el=document.getElementById('proj-list');
    el.innerHTML=d.projects.map(p=>
      `<div style="margin-bottom:10px;padding:8px;background:#0d1117;border:1px solid #21262d;border-radius:4px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="color:${p.name===d.active_project?'#3fb950':'#c9d1d9'};font-size:.85em">
            ${p.name} ${p.name===d.active_project?'<span class="proj-badge">active</span>':''}
          </span>
          ${p.name!==d.active_project?`<button class="btn" onclick="switchProj('${p.name}')" style="padding:2px 8px;font-size:.72em">Switch</button>`:''}
        </div>
        <div style="color:#8b949e;font-size:.72em;margin-top:4px">${p.project_dir}</div>
      </div>`
    ).join('');
  }catch(e){}
}
async function switchProj(name){
  try{
    await fetch('/projects/switch',{method:'POST',headers:H(),body:JSON.stringify({name})});
    loadProjects(); refreshStatus();
  }catch(e){}
}
async function createProject(){
  const msg=document.getElementById('proj-msg');
  const payload={
    name:        document.getElementById('new-proj-name').value.trim(),
    project_dir: document.getElementById('new-proj-dir').value.trim(),
    session_dir: document.getElementById('new-proj-sessions').value.trim(),
    github_repo: document.getElementById('new-proj-repo').value.trim()
  };
  if(!payload.name){msg.textContent='Name required';msg.className='msg fail';return;}
  try{
    const r=await fetch('/projects',{method:'POST',headers:H(),body:JSON.stringify(payload)});
    const d=await r.json();
    msg.textContent=d.status==='created'?'Project created \u2713':'Error: '+JSON.stringify(d);
    msg.className='msg '+(d.status==='created'?'ok':'fail');
    if(d.status==='created') loadProjects();
  }catch(e){msg.textContent='Failed: '+e;msg.className='msg fail';}
}

// ── Settings ──
async function loadSettings(){
  try{
    const r=await fetch('/settings',{headers:H()});
    if(!r.ok)return;
    const d=await r.json();
    document.getElementById('c-duckdns_domain').value=d.duckdns_domain||'';
    document.getElementById('c-duckdns_token').value=d.duckdns_token||'';
    document.getElementById('c-server_port').value=d.server_port||5001;
    document.getElementById('c-max_log_lines').value=d.max_log_lines||100;
    document.getElementById('c-safe_commands').value=(d.safe_commands||[]).join('\n');
    document.getElementById('keyst').textContent=d.api_key_set?'Set \u2713':'Not set (open access)';
    loadCmds();
  }catch(e){}
}
async function saveSettings(){
  const msg=document.getElementById('smsg');
  const payload={
    duckdns_domain: document.getElementById('c-duckdns_domain').value,
    duckdns_token:  document.getElementById('c-duckdns_token').value,
    server_port:    parseInt(document.getElementById('c-server_port').value)||5001,
    max_log_lines:  parseInt(document.getElementById('c-max_log_lines').value)||100,
    safe_commands:  document.getElementById('c-safe_commands').value
                    .split('\n').map(s=>s.trim()).filter(Boolean),
  };
  const nk=document.getElementById('c-api_key').value.trim();
  if(nk){payload.api_key=nk;localStorage.setItem('ok',nk);KEY=nk;}
  try{
    const r=await fetch('/settings',{method:'POST',headers:H(),body:JSON.stringify(payload)});
    const d=await r.json();
    msg.textContent=d.status==='saved'?'Saved \u2713 (restart for port changes)':'Error: '+JSON.stringify(d);
    msg.className='msg '+(d.status==='saved'?'ok':'fail');
    if(d.status==='saved') loadSettings();
  }catch(e){msg.textContent='Failed: '+e;msg.className='msg fail';}
}
function genKey(){
  const c='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  document.getElementById('c-api_key').value=
    Array.from({length:48},()=>c[Math.floor(Math.random()*c.length)]).join('');
}

// ── Init ──
refreshStatus();
setRefresh();
setInterval(refreshStatus,10000);
loadCmds();
</script>
</body>
</html>"""

@app.route("/audit")
@auth_required
def get_audit_log():
    """Return the append-only audit log. Never truncated — full history."""
    n = int(request.args.get("lines", 200))
    if not os.path.exists(AUDIT_LOG_PATH):
        return jsonify({"entries": [], "total": 0,
                        "message": "No audit log yet."})
    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line.strip()))
            except Exception:
                entries.append({"raw": line.strip()})
        return jsonify({"entries": entries, "total": len(lines),
                        "showing": len(entries)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["POST"])
@auth_required
def search():
    """
    Brave Search endpoint for Ontinuity session queries.
    Called by the session engine when Projenius issues a SEARCH function call.

    POST body:
        query        (str, required)  — the search query
        context      (str, optional)  — citation or claim context for verification
        count        (int, optional)  — number of results to return (default 5, max 10)

    Returns:
        results: list of {title, url, description, age}
        query: the query that was run
        total: number of results returned
    """
    brave_key = os.environ.get("BRAVE_API_KEY", "").strip()
    if not brave_key:
        return jsonify({"error": "BRAVE_API_KEY not configured on workspace server"}), 503

    data    = request.get_json(force=True, silent=True) or {}
    query   = data.get("query", "").strip()
    context = data.get("context", "").strip()
    count   = min(int(data.get("count", 5)), 10)

    if not query:
        return jsonify({"error": "query is required"}), 400

    # If context is provided (citation verification), prepend it to sharpen the query
    search_query = query
    if context:
        search_query = f"{context} {query}"

    try:
        import urllib.request
        url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(search_query)}&count={count}&text_decorations=false&search_lang=en"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": brave_key
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            import gzip
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            result_data = json.loads(raw.decode("utf-8"))

        web_results = result_data.get("web", {}).get("results", [])
        results = [{
            "title":       r.get("title", ""),
            "url":         r.get("url", ""),
            "description": r.get("description", ""),
            "age":         r.get("age", ""),
        } for r in web_results[:count]]

        audit("SEARCH", search_query, {"results": len(results)})
        return jsonify({
            "query":   search_query,
            "context": context,
            "results": results,
            "total":   len(results)
        })

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD)

# ── ENTRY POINT ───────────────────────────────────────────────────────


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



# --- Self-registering egress whitelist (Option A) -------------------------
import ipaddress as _ipaddr

@app.route("/register_egress", methods=["POST"])
def register_egress():
    cfg = load_config()
    dk = cfg.get("diag_key", "")
    if not dk or not secrets.compare_digest(request.headers.get("X-Diag-Key", ""), dk):
        return jsonify({"error": "unauthorized"}), 401
    ip = request.remote_addr or ""
    try:
        _ipaddr.IPv4Address(ip)
    except Exception:
        return jsonify({"error": "bad source ip", "ip": ip}), 400
    op_id = _ops_begin("register_egress", "SAFE", "diag-key", ip, {"ip": ip, "port": 5001})
    try:
        r = subprocess.run(
            ["ufw", "allow", "from", ip, "to", "any", "port", "5001",
             "comment", "auto-egress-" + ip],
            capture_output=True, text=True, timeout=15)
        ok = r.returncode == 0
        _ops_finish(op_id, "ok" if ok else "fail", (r.stdout or r.stderr).strip()[:200])
        return jsonify({"ok": ok, "ip": ip,
                        "result": (r.stdout or r.stderr).strip()[:200]}), (200 if ok else 500)
    except Exception as e:
        _ops_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500




# --- Punch-list panel (renders live/PUNCH_LIST.md as past/present/future) ---
import re as _pl_re

def _pl_path():
    for p in ("/opt/ontinuity/PUNCH_LIST.md",
              os.path.join(os.path.dirname(__file__), "PUNCH_LIST.md"),
              os.path.join(os.path.dirname(__file__), "live", "PUNCH_LIST.md")):
        if os.path.exists(p):
            return p
    return None

def _pl_parse(md):
    out = {"resolved": None, "done": [], "in_progress": [],
           "open": {"HIGH": [], "MED": [], "MINOR": []}, "operator_gated": []}
    m = _pl_re.search(r"Last resolved:\s*([0-9-]+)", md)
    if m: out["resolved"] = m.group(1)
    section = None      # done | in_progress | open
    subtier = None      # HIGH | MED | MINOR | OPERATOR-GATED
    for line in md.splitlines():
        s = line.strip()
        h2 = _pl_re.match(r"##\s+([A-Z-]+)", s)
        if h2:
            tag = h2.group(1).upper()
            section = {"DONE": "done", "IN-PROGRESS": "in_progress", "OPEN": "open"}.get(tag)
            subtier = None
            continue
        h3 = _pl_re.match(r"###\s+([A-Z-]+)", s)
        if h3:
            subtier = h3.group(1).upper()
            continue
        bullet = _pl_re.match(r"-\s+\*\*(.+?)\*\*\s*(.*)$", s)
        if not bullet or not section:
            continue
        title = bullet.group(1).strip()
        rest = bullet.group(2).strip(" —.-")
        if section == "done":
            out["done"].append({"title": title, "ref": rest})
        elif section == "in_progress":
            tierm = _pl_re.search(r"\[([A-Z/ ]+)\]", rest)
            tier = (tierm.group(1).split("/")[0].strip() if tierm else "")
            awaitm = _pl_re.search(r"[Aa]waiting ([^.]+)", rest)
            await_ = ("awaiting " + awaitm.group(1).strip()) if awaitm else ""
            refm = _pl_re.search(r"\b([0-9a-f]{7,40})\b", rest)
            ref = refm.group(1) if refm else ""
            out["in_progress"].append({"title": title, "tier": tier, "await_": await_, "ref": ref})
        elif section == "open":
            if subtier in ("HIGH", "MED", "MINOR"):
                out["open"][subtier].append({"title": title})
            elif subtier == "OPERATOR-GATED":
                out["operator_gated"].append({"title": title})
            else:
                out["open"]["MED"].append({"title": title})
    return out

@app.route("/governor/punchlist")
def governor_punchlist_page():
    try:
        with open(os.path.join(os.path.dirname(__file__), "governor_punchlist.html")) as fh:
            return fh.read()
    except Exception as e:
        return f"governor_punchlist.html not found: {e}", 500

@app.route("/governor/punchlist/data")
@auth_required
def governor_punchlist_data():
    p = _pl_path()
    if not p:
        return jsonify({"error": "PUNCH_LIST.md not found on server"}), 404
    try:
        with open(p) as fh:
            return jsonify(_pl_parse(fh.read()))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500




# --- Operations Ledger (audit spine for scoped operations) ----------------
# Append-only record of every privileged scoped operation. Dual-end write:
# an intent row on invocation, updated with the result on completion, so a
# crashed/hung operation leaves a visible incomplete record (no fail-quiet).
import sqlite3 as _ops_sqlite
from datetime import datetime as _ops_dt, timezone as _ops_tz
_OPS_DB = os.environ.get("ONTINUITY_DB_PATH", os.path.join(os.path.dirname(__file__), "ontinuity.db"))

# ---------------------------------------------------------------------------
# KEYS-2 — per-identity key registry + authentication (KEYS-1 spec).
# Identity comes from WHICH key authenticated, never from a body field. The
# registry maps sha256(key) -> {seat, lineage, status}; NO plaintext key is ever
# stored (hash only — repo/box-safe per the no-credentials rule). The key material
# lives only in each seat's sandbox + the operator vault (#42). This is the lookup
# the vault populates on issuance.
# ---------------------------------------------------------------------------
import hashlib as _kr_hashlib

_SEAT_KEYS_PATH = os.environ.get("ONTINUITY_SEAT_KEYS",
                                 os.path.join(BASE_DIR, "live", "seat_keys.json"))

def _kr_hash(key):
    return _kr_hashlib.sha256((key or "").encode("utf-8")).hexdigest()

def _kr_load():
    """Load the hash->identity registry. {sha256hex: {seat, lineage, status}}.
    Absent file -> empty registry (system runs in shared-key mode)."""
    try:
        with open(_SEAT_KEYS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def authenticate_identity(presented_key):
    """Resolve a presented key to a seat identity. Returns:
      {seat, lineage, status, authenticated: bool, mode: 'per_identity'|'shared'|'none'}.
    - per-identity hit (active)  -> authenticated=True, the registry identity.
    - the shared DIAG_KEY        -> authenticated=False, seat='unattributed' (BACK-COMPAT:
                                    old callers still pass the gate, but are visibly NOT a
                                    real seat; identity-sensitive routes may downgrade to
                                    body fallback or refuse).
    - anything else              -> None (caller should 401).
    Constant-time compares; no plaintext stored."""
    if not presented_key:
        return None
    reg = _kr_load()
    h = _kr_hash(presented_key)
    # per-identity: constant-time scan so a hit/miss isn't timing-distinguishable
    match = None
    for stored_hash, ident in reg.items():
        if secrets.compare_digest(stored_hash, h):
            match = ident
    if match is not None:
        if match.get("status", "active") != "active":
            return {"seat": match.get("seat"), "lineage": match.get("lineage"),
                    "status": match.get("status"), "authenticated": False, "mode": "revoked"}
        return {"seat": match.get("seat"), "lineage": match.get("lineage"),
                "status": "active", "authenticated": True, "mode": "per_identity"}
    # shared-key back-compat
    try:
        dk = load_config().get("diag_key", "") or os.environ.get("DIAG_KEY", "")
    except Exception:
        dk = os.environ.get("DIAG_KEY", "")
    if dk and secrets.compare_digest(presented_key, dk):
        return {"seat": "unattributed", "lineage": "shared-key",
                "status": "active", "authenticated": False, "mode": "shared"}
    return None

def register_seat_key(plaintext_key, seat, lineage, status="active"):
    """Issuance helper (called by the vault / bootstrap-gate issuance-on-pass).
    Stores ONLY the hash. Returns the hash. Never logs the plaintext."""
    reg = _kr_load()
    reg[_kr_hash(plaintext_key)] = {"seat": seat, "lineage": lineage, "status": status}
    os.makedirs(os.path.dirname(_SEAT_KEYS_PATH), exist_ok=True)
    tmp = _SEAT_KEYS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, _SEAT_KEYS_PATH)
    return _kr_hash(plaintext_key)


def _ops_ledger_init():
    try:
        c = _ops_sqlite.connect(_OPS_DB)
        c.execute("""CREATE TABLE IF NOT EXISTS operations_ledger (
            op_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            operation   TEXT NOT NULL,
            tier        TEXT,
            caller      TEXT,
            source_ip   TEXT,
            args        TEXT,
            result      TEXT,
            status      TEXT NOT NULL,   -- started | ok | fail
            started_at  TEXT NOT NULL,
            finished_at TEXT )""")
        c.commit(); c.close()
    except Exception as e:
        print(f"ops_ledger init failed: {e}")

def _ops_begin(operation, tier, caller, source_ip, args):
    """Log intent; return op_id (or None on failure — never blocks the op).
    CALLER-1: `caller` is a TRUSTED-NOT-AUTHENTICATED label. For seat ops it is the
    self-asserted seat name ('seat:<name>', threaded by the _ledger wrappers in
    seat_mailbox.py/box_ops.py from the request body); for this module's own routes
    that carry no seat (register_egress/read_journal/restart_workspace) it stays the
    auth-method label 'diag-key'. The shared diag key proves a keyholder called, NOT
    which seat — so caller records who CLAIMS to act, not proof. Authenticated only
    once per-identity keys derive the seat from the key (see
    live/specs/mailbox_threat_audit.md SECAUDIT-1 Q4)."""
    try:
        c = _ops_sqlite.connect(_OPS_DB)
        cur = c.execute(
            "INSERT INTO operations_ledger (operation,tier,caller,source_ip,args,status,started_at) VALUES (?,?,?,?,?, 'started', ?)",
            (operation, tier, caller, source_ip, str(args)[:1000], _ops_dt.now(_ops_tz.utc).isoformat()))
        c.commit(); oid = cur.lastrowid; c.close()
        return oid
    except Exception as e:
        print(f"ops_begin failed: {e}"); return None

def _ops_finish(op_id, status, result=""):
    if op_id is None: return
    try:
        c = _ops_sqlite.connect(_OPS_DB)
        c.execute("UPDATE operations_ledger SET status=?, result=?, finished_at=? WHERE op_id=?",
                  (status, str(result)[:1000], _ops_dt.now(_ops_tz.utc).isoformat(), op_id))
        c.commit(); c.close()
    except Exception as e:
        print(f"ops_finish failed: {e}")

_ops_ledger_init()
# --------------------------------------------------------------------------




# --- Scoped operation: read_journal (SAFE, read-only) ---------------------
@app.route("/op/read_journal", methods=["POST"])
def op_read_journal():
    cfg = load_config()
    dk = cfg.get("diag_key", "")
    if not dk or not secrets.compare_digest(request.headers.get("X-Diag-Key", ""), dk):
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    try:
        lines = int(body.get("lines", 40))
    except Exception:
        lines = 40
    lines = max(1, min(lines, 200))   # bounded: 1..200
    unit = "ontinuity-workspace"      # fixed unit, no arbitrary input
    op_id = _ops_begin("read_journal", "SAFE", "diag-key", request.remote_addr, {"unit": unit, "lines": lines})
    try:
        r = subprocess.run(["journalctl", "-u", unit, "--no-pager", "-n", str(lines)],
                           capture_output=True, text=True, timeout=20)
        ok = r.returncode == 0
        out = (r.stdout or r.stderr)[-12000:]
        _ops_finish(op_id, "ok" if ok else "fail", f"{lines} lines, rc={r.returncode}")
        return jsonify({"ok": ok, "unit": unit, "lines": lines, "log": out}), (200 if ok else 500)
    except Exception as e:
        _ops_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500

# --- Scoped operation: restart_workspace (SAFE, reversible mutation) -------
@app.route("/op/restart_workspace", methods=["POST"])
def op_restart_workspace():
    cfg = load_config()
    dk = cfg.get("diag_key", "")
    if not dk or not secrets.compare_digest(request.headers.get("X-Diag-Key", ""), dk):
        return jsonify({"error": "unauthorized"}), 401
    op_id = _ops_begin("restart_workspace", "SAFE", "diag-key", request.remote_addr, {"unit": "ontinuity-workspace"})
    # Mark the result NOW (the restart kills this process before a post-restart write
    # could land). 'ok' means the restart was dispatched; the service coming back is
    # observable via /status. Detached + delayed so this HTTP response returns first.
    _ops_finish(op_id, "ok", "restart dispatched (detached, 1s delay)")
    try:
        subprocess.Popen(["bash", "-c", "sleep 1 && systemctl restart ontinuity-workspace"],
                         start_new_session=True)
        return jsonify({"ok": True, "note": "restart dispatched; service returns in a few seconds — confirm via /status"}), 200
    except Exception as e:
        _ops_finish(op_id, "fail", str(e)[:200])
        return jsonify({"error": str(e)[:200]}), 500


if __name__ == "__main__":
    cfg  = load_config()
    port = cfg.get("server_port", 5001)
    host = cfg.get("server_host", "0.0.0.0")

    if not cfg.get("api_key"):
        key = secrets.token_urlsafe(36)
        cfg["api_key"] = key
        save_config(cfg)
        print("\n[SERVER] *** FIRST RUN — API KEY GENERATED ***")
        print(f"[SERVER] Your API key: {key}")
        print("[SERVER] Copy this. Also visible in Settings tab.")
        print("[SERVER] Keep config.json private — do not commit it.\n")

    print(f"[SERVER] Ontinuity Workspace Server v2.0")
    print(f"[SERVER] Platform: {platform.system()}")
    print(f"[SERVER] Starting on {host}:{port}")
    print(f"[SERVER] Dashboard: http://localhost:{port}")

    if DB_INTEGRATION:
        init_db()
        print(f"[SERVER] Database: ontinuity.db")
    else:
        print(f"[SERVER] Database: not configured (workspace_db_endpoint.py missing)")

    print(f"[SERVER] Audit log: {AUDIT_LOG_PATH}")
    brave_key = os.environ.get("BRAVE_API_KEY", "").strip()
    print(f"[SERVER] Brave Search: {'configured' if brave_key else 'not configured (set BRAVE_API_KEY env var)'}")
    app.run(host=host, port=port, debug=False)


