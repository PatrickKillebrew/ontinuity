"""
ONTINUITY LAPTOP SEAT  (reverse-connection hands)
=================================================
Runs on the operator's laptop. Dials OUT to the Ontinuity engine mailbox,
polls for task messages addressed to this seat, executes them locally inside
a scoped working directory against a command prefix-whitelist, and posts the
results back. No inbound port, no port-forwarding, nothing exposed to the
internet -- the laptop only ever makes outbound HTTPS POSTs to the engine.

This mirrors the box's scoped-op contract (read/write/run, diag-key gated,
bounded, logged) but over the mailbox relay instead of an inbound courier.

Config is read from the existing workspace config (C:\\donkeycar\\config.json):
  - api_key / diag_key  : auth to the engine
  - project_dir         : the scope all ops are confined to
  - safe_commands       : the run prefix-whitelist

Ops (task body is JSON):
  {"op":"run","cmd":"<command>"}              -> run whitelisted command in project_dir
  {"op":"read","path":"<rel-or-abs path>"}    -> return file contents
  {"op":"write","path":"<path>","content":""} -> write file
  {"op":"ping"}                               -> liveness check
Result is posted back as a mailbox 'result' message, body = JSON
  {"ok":true/false, "op":..., "stdout":..., "stderr":..., "rc":..., "error":...}
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
CONFIG_PATH = os.environ.get("ONTINUITY_CONFIG", r"C:\donkeycar\config.json")
ENGINE = os.environ.get("ONTINUITY_ENGINE", "https://web-production-7eaf8.up.railway.app")
SEAT = os.environ.get("ONTINUITY_SEAT", "laptop")
POLL_SECONDS = float(os.environ.get("ONTINUITY_POLL", "2.0"))
RUN_TIMEOUT = int(os.environ.get("ONTINUITY_RUN_TIMEOUT", "120"))


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_diag_key(cfg):
    # The engine mailbox gates on X-Diag-Key. The laptop config historically
    # stored an api_key; the diag key may be the same value or a separate
    # 'diag_key' field. Prefer an explicit diag_key, fall back to api_key.
    return (cfg.get("diag_key") or cfg.get("api_key") or "").strip()


def project_dir(cfg):
    # active project's dir, scope for all ops
    active = cfg.get("active_project")
    for p in cfg.get("projects", []):
        if p.get("name") == active:
            return p.get("project_dir") or os.getcwd()
    if cfg.get("projects"):
        return cfg["projects"][0].get("project_dir") or os.getcwd()
    return os.getcwd()


def command_allowed(command, cfg):
    cmd = command.strip()
    return any(cmd.startswith(p) for p in cfg.get("safe_commands", []))


# ---------------------------------------------------------------------------
# engine mailbox calls (outbound only)
# ---------------------------------------------------------------------------
def _post(path, body, diag_key):
    url = ENGINE.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Diag-Key", diag_key)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": "http %s" % e.code}
    except Exception as e:
        return {"error": str(e)[:200]}


def mailbox_fetch(diag_key):
    return _post("/diag/op/mailbox_fetch", {"seat": SEAT}, diag_key)


def mailbox_send_result(diag_key, to_seat, body, reply_to=None):
    msg = {"from_seat": SEAT, "to_seat": to_seat, "kind": "result",
           "body": json.dumps(body)}
    if reply_to:
        msg["reply_to"] = reply_to
    return _post("/diag/op/mailbox_send", msg, diag_key)


def mailbox_ack(diag_key, msg_id):
    return _post("/diag/op/mailbox_ack", {"seat": SEAT, "msg_id": msg_id}, diag_key)


# ---------------------------------------------------------------------------
# op execution (scoped + whitelisted)
# ---------------------------------------------------------------------------
def _resolve(path, scope):
    # confine to scope: relative paths join scope; absolute must be inside scope
    p = os.path.abspath(os.path.join(scope, path)) if not os.path.isabs(path) else os.path.abspath(path)
    scope_abs = os.path.abspath(scope)
    if os.path.commonpath([p, scope_abs]) != scope_abs:
        raise ValueError("path outside project scope")
    return p


def execute(op, cfg):
    scope = project_dir(cfg)
    kind = op.get("op")
    if kind == "ping":
        return {"ok": True, "op": "ping", "scope": scope}
    if kind == "run":
        cmd = op.get("cmd", "")
        if not command_allowed(cmd, cfg):
            return {"ok": False, "op": "run", "error": "not in whitelist",
                    "safe_commands": cfg.get("safe_commands", [])}
        try:
            r = subprocess.run(cmd, shell=True, cwd=scope, capture_output=True,
                               text=True, timeout=RUN_TIMEOUT)
            return {"ok": r.returncode == 0, "op": "run", "cmd": cmd,
                    "rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
        except subprocess.TimeoutExpired:
            return {"ok": False, "op": "run", "cmd": cmd, "error": "timeout"}
    if kind == "read":
        try:
            p = _resolve(op.get("path", ""), scope)
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return {"ok": True, "op": "read", "path": op.get("path"), "content": f.read()}
        except Exception as e:
            return {"ok": False, "op": "read", "error": str(e)[:200]}
    if kind == "write":
        try:
            p = _resolve(op.get("path", ""), scope)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(op.get("content", ""))
            return {"ok": True, "op": "write", "path": op.get("path"),
                    "bytes": len(op.get("content", ""))}
        except Exception as e:
            return {"ok": False, "op": "write", "error": str(e)[:200]}
    return {"ok": False, "error": "unknown op: %s" % kind}


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    diag_key = get_diag_key(cfg)
    if not diag_key:
        print("[laptop_seat] no diag/api key in config; cannot auth. exiting.")
        sys.exit(1)
    print("[laptop_seat] seat=%s engine=%s scope=%s" % (SEAT, ENGINE, project_dir(cfg)))
    print("[laptop_seat] dialing out, polling mailbox every %ss. Ctrl+C to stop." % POLL_SECONDS)
    while True:
        try:
            cfg = load_config()  # reload so whitelist/scope edits take effect live
            diag_key = get_diag_key(cfg)
            resp = mailbox_fetch(diag_key)
            msg = resp.get("message") if isinstance(resp, dict) else None
            if not msg:
                time.sleep(POLL_SECONDS)
                continue
            if msg.get("kind") != "task":
                # not for us to execute; ack to clear it and move on
                mailbox_ack(diag_key, msg.get("msg_id"))
                continue
            try:
                op = json.loads(msg.get("body", "{}"))
            except Exception:
                op = {"op": "_bad", "raw": msg.get("body")}
            print("[laptop_seat] task %s: %s" % (msg.get("msg_id"), op.get("op")))
            result = execute(op, cfg)
            mailbox_send_result(diag_key, msg.get("from_seat", "control"),
                                result, reply_to=msg.get("msg_id"))
            mailbox_ack(diag_key, msg.get("msg_id"))
            print("[laptop_seat]   -> result posted (ok=%s)" % result.get("ok"))
        except KeyboardInterrupt:
            print("\n[laptop_seat] stopped.")
            break
        except Exception as e:
            print("[laptop_seat] loop error: %s" % str(e)[:200])
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
