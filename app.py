"""
Ontinuity Web App - Backend
app.py
Run with: python app.py
Then open http://localhost:5000 in your browser.
Install dependencies first:
    pip install flask flask-socketio requests
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import os
import re
import base64
import datetime
import time
import requests as http_requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ontinuity-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# -----------------------------------------
# WORKSPACE / KNOWTEXT PATH RESOLUTION
# -----------------------------------------
# Workspace server — where session data is written after each session.
# Set WORKSPACE_URL in Railway env vars to enable database persistence.
# Example: https://your-duckdns-domain.duckdns.org:5001
WORKSPACE_URL     = os.environ.get("WORKSPACE_URL", "").strip().rstrip("/")
WORKSPACE_PROJECT = os.environ.get("WORKSPACE_PROJECT", "Ontinuity Platform").strip()
WORKSPACE_BRANCH  = os.environ.get("WORKSPACE_BRANCH", "main").strip()

def get_knowtext_filename():
    """Return branch-aware Knowtext filename.
    Uses knowtext_{branch}.txt when WORKSPACE_BRANCH is set and not 'main'.
    Falls back to knowtext_current.txt for backward compatibility."""
    branch = WORKSPACE_BRANCH
    if branch and branch != "main":
        # Sanitize branch name for filename safety
        safe_branch = re.sub(r'[^a-zA-Z0-9_-]', '_', branch)
        return f"knowtext_{safe_branch}.txt"
    return "knowtext_current.txt"

def get_github_knowtext_path():
    """Return branch-aware GitHub file path for Knowtext."""
    branch = WORKSPACE_BRANCH
    if branch and branch != "main":
        safe_branch = re.sub(r'[^a-zA-Z0-9_-]', '_', branch)
        return f"knowtext_{safe_branch}.txt"
    return "knowtext_current.txt"

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
CONFIG = {
    "knowtext_path": get_knowtext_filename(),
    "backup1_path": "knowtext_backup1.txt",
    "backup2_path": "knowtext_backup2.txt",
    "artifacts_dir": "session_artifacts",
    "checkpoint_interval": 10,
    "model_a": {
        "url": "",
        "api_key": "",
        "model": "",
        "system_prompt_path": "prompts/model_a_system.txt"
    },
    "model_b": {
        "url": "",
        "api_key": "",
        "model": "",
        "system_prompt_path": "prompts/model_b_system.txt"
    },
    "model_c": {
        "url": "",
        "api_key": "",
        "model": "",
        "system_prompt_path": "prompts/model_c_system.txt"
    },
    "projenius": {
        "url": "",
        "api_key": "",
        "model": "",
        "system_prompt_path": "prompts/projenius_system.txt"
    },
    "parietal": {
        "url": "",
        "api_key": "",
        "model": "",
        "system_prompt_path": "prompts/parietal_system.txt"
    }
}

KNOWTEXT_REQUIRED_FIELDS = [
    "Identity", "Active Frameworks", "Open Questions",
    "Valence Mapping", "Delta Log", "Correction History", "Climate Notes"
]

SCHEMA_VERSION = "KNOWTEXT SCHEMA VERSION: 1.1"

# -----------------------------------------
# SESSION STATE
# -----------------------------------------
active_session = {
    "running": False,
    "transcript": [],
    "tag_sequence": [],
    "signal_sequence": [],
    "challenge_events": [],
    "errors": [],
    "cycle": 0,
    "start_time": None,
    "end_time": None,
    "knowtext_version": None,
    "waiting_for_input": False,
    "input_type": None,
    "human_input_event": threading.Event(),
    "human_input_value": None,
    "artifacts": [],
    "session_ledger": [],  # Running list of established results per cycle
    "parietal_navigate_outputs": [],   # All NAVIGATE outputs this session
    "parietal_adjudicate_rulings": [], # All ADJUDICATE rulings this session
    "rejected_claims": [],             # Claims formally ruled against — injected into Researcher system prompt each cycle
    "start_fresh": False,              # If True, skip Knowtext injection for this session
    "distillation_method": "failed",   # Tracks which method succeeded: parietal/projenius/failed
    "no_progress_count": 0,            # F.1: consecutive cycles Challenger flagged no progress; reset on progress or successful RESOLVE
    "malformed_count": 0,             # F.1: consecutive Researcher cycles with no valid status tag
    "execution_log": [],               # F.2: deterministic record of every real workspace execution this session (F.3 detector ground truth)
    "claim_warning_count": 0           # F.2: consecutive Researcher cycles with execution-claims but no real execution
}

# Runtime config overrides (set from frontend settings modal)
# Structure: { 'model_b': {'key': '...', 'url': '...', 'model': '...'} }
runtime_configs = {}

# User-supplied GitHub config (overrides environment variable)
# Structure: { 'token': '...', 'repo': 'user/repo' }
runtime_github = {}

def get_effective_config(role):
    """Merge base CONFIG with any runtime overrides from the frontend settings modal."""
    config = dict(CONFIG[role])
    if role in runtime_configs:
        rc = runtime_configs[role]
        if rc.get('key'): config['api_key'] = rc['key'].strip()
        if rc.get('url'): config['url'] = rc['url'].strip()
        if rc.get('model'): config['model'] = rc['model'].strip()
    return config

def get_best_available_model():
    """Return the best configured model role for extraction tasks.
    Falls back down the chain if model_a has no key configured."""
    for role in ["model_a", "projenius", "model_b"]:
        cfg = get_effective_config(role)
        if cfg.get("api_key") and cfg.get("url"):
            return role
    return "model_a"  # last resort — will fail with clear error via call_model guard

def detect_api_format(url):
    """Auto-detect API format from endpoint URL. No manual format field required."""
    if "anthropic.com" in url:
        return "anthropic"
    if "generativelanguage.googleapis.com" in url:
        return "gemini"
    return "openai"  # covers GROQ, OpenAI, Cerebras, OpenRouter, Together, Mistral, etc.

# -----------------------------------------
# FILE UTILITIES
# -----------------------------------------
def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def sanitize_content(text):
    """Strip problematic unicode characters that break database extraction.
    Replaces curly quotes and similar typographic characters with ASCII equivalents."""
    if not text:
        return text
    replacements = {
        '\u201c': '"', '\u201d': '"',  # curly double quotes
        '\u2018': "'", '\u2019': "'",  # curly single quotes / apostrophe
        '\u2013': '-', '\u2014': '--', # en-dash, em-dash
        '\u2026': '...',               # ellipsis
        '\u00a0': ' ',                 # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

# -----------------------------------------
# BEHAVIORAL ANALYSIS HELPERS
# -----------------------------------------
HEDGING_MARKERS = [
    "possibly", "might", "maybe", "perhaps", "unclear", "uncertain",
    "approximately", "roughly", "could", "may", "seems", "appears",
    "likely", "probably", "potentially", "i think", "i believe",
    "it seems", "it appears", "not certain", "not sure", "suggest"
]
CERTAINTY_MARKERS = [
    "confirmed", "established", "proven", "verified", "concluded",
    "determined", "demonstrated", "shown", "clear", "definitive",
    "resolved", "complete", "established:", "result:", "confirmed:"
]

def count_markers(text, markers):
    if not text:
        return 0
    text_lower = text.lower()
    return sum(1 for m in markers if m in text_lower)

def parse_signal_sequence(signal_sequence):
    profile = []
    reasons = []
    for entry in signal_sequence:
        sig_match = re.search(r'SIGNAL\s+(\d)', entry)
        reason_match = re.search(r'SIGNAL\s+\d+\s*[-\u2013]\s*(.+)', entry)
        profile.append(int(sig_match.group(1)) if sig_match else 0)
        reasons.append(reason_match.group(1).strip() if reason_match else "")
    return profile, reasons

def parse_challenge_counts(challenge_events, tag_sequence):
    counts = {"challenge": 0, "uphold": 0, "reject": 0,
              "pursue_both": 0, "escalate": 0}
    for event in challenge_events:
        eu = event.upper()
        if "UPHOLD" in eu:
            counts["uphold"] += 1; counts["challenge"] += 1
        elif "REJECT" in eu:
            counts["reject"] += 1; counts["challenge"] += 1
        elif "PURSUE BOTH" in eu or "PURSUE_BOTH" in eu:
            counts["pursue_both"] += 1; counts["challenge"] += 1
        elif "ESCALATE" in eu:
            counts["escalate"] += 1; counts["challenge"] += 1
    return counts

def build_behavioral_observations(session_id, transcript,
                                   signal_sequence, tag_sequence,
                                   challenge_events):
    observations = []
    profile, reasons = parse_signal_sequence(signal_sequence)
    by_cycle = {}
    for entry in transcript:
        cycle = entry.get("cycle", 0)
        role = entry.get("role", "")
        if cycle not in by_cycle:
            by_cycle[cycle] = {}
        by_cycle[cycle][role] = entry.get("content", "")
    cumulative_challenges = 0
    cumulative_upholds = 0
    for i, sig in enumerate(profile):
        cycle_num = i + 1
        cycle_data = by_cycle.get(cycle_num, {})
        a_content = cycle_data.get("model_a", "")
        b_content = cycle_data.get("model_b", "")
        a_words = len(a_content.split()) if a_content else 0
        b_words = len(b_content.split()) if b_content else 0
        a_tag = next((t.split(": ")[-1] for t in tag_sequence
                      if f"Cycle {cycle_num} A:" in t), "CONTINUE")
        b_tag = next((t.split(": ")[-1] for t in tag_sequence
                      if f"Cycle {cycle_num} B:" in t), "CONTINUE")
        b_challenged = b_tag == "CHALLENGE"
        if b_challenged:
            cumulative_challenges += 1
        ruling = None
        if b_challenged:
            for event in challenge_events:
                if f"Cycle {cycle_num}:" in event:
                    for r in ["UPHOLD", "REJECT", "PURSUE BOTH", "ESCALATE"]:
                        if r in event.upper():
                            ruling = r
                            if r == "UPHOLD":
                                cumulative_upholds += 1
                            break
                    break
        observations.append({
            "session_id": session_id,
            "cycle_number": cycle_num,
            "friction_signal": sig,
            "friction_reason": reasons[i] if i < len(reasons) else "",
            "model_a_tag": a_tag,
            "model_a_word_count": a_words,
            "model_a_token_est": int(a_words * 1.3),
            "model_a_hedging_count": count_markers(a_content, HEDGING_MARKERS),
            "model_a_certainty_count": count_markers(a_content, CERTAINTY_MARKERS),
            "model_b_tag": b_tag,
            "model_b_word_count": b_words,
            "model_b_token_est": int(b_words * 1.3),
            "model_b_challenge_issued": b_challenged,
            "ambient_signal": sig,
            "cumulative_uphold_count": cumulative_upholds,
            "cumulative_challenge_count": cumulative_challenges,
            "session_cycle_ratio": round(cycle_num / max(len(profile), 1), 3),
            "ruling_if_challenged": ruling,
        })
    return observations

def build_session_payload():
    s = active_session
    session_id = s.get("start_time") or timestamp()
    profile, reasons = parse_signal_sequence(s.get("signal_sequence", []))
    counts = parse_challenge_counts(
        s.get("challenge_events", []), s.get("tag_sequence", []))
    avg_signal = round(sum(profile) / len(profile), 3) if profile else 0
    variance = 0.0
    if len(profile) > 1:
        variance = round(sum((x - avg_signal)**2 for x in profile) / len(profile), 3)
    first_challenge = None
    for tag_line in s.get("tag_sequence", []):
        if "CHALLENGE" in tag_line:
            m = re.search(r'Cycle (\d+)', tag_line)
            if m:
                first_challenge = int(m.group(1))
            break
    def model_str(role):
        cfg = get_effective_config(role)
        return cfg.get("model", CONFIG[role]["model"])
    behavioral_obs = build_behavioral_observations(
        session_id=session_id,
        transcript=s.get("transcript", []),
        signal_sequence=s.get("signal_sequence", []),
        tag_sequence=s.get("tag_sequence", []),
        challenge_events=s.get("challenge_events", [])
    )
    turn_number = 0
    transcript_turns = []
    for entry in s.get("transcript", []):
        turn_number += 1
        cycle = entry.get("cycle", 0)
        content = sanitize_content(entry.get("content", "")) or ""
        role = entry.get("role", "")
        role_key = "a" if role == "model_a" else ("b" if role == "model_b" else "")
        tag = None
        if role_key:
            tag_line = next((t for t in s.get("tag_sequence", [])
                             if f"Cycle {cycle} {role_key.upper()}:" in t), "")
            if ": " in tag_line:
                tag = tag_line.split(": ")[-1]
        sig_entry = next((ln for ln in s.get("signal_sequence", [])
                          if f"Cycle {cycle}:" in ln), "")
        sig_m = re.search(r'SIGNAL\s+(\d)', sig_entry)
        transcript_turns.append({
            "cycle_number": cycle,
            "turn_number": turn_number,
            "role": role,
            "content": content,
            "tag": tag,
            "friction_signal": int(sig_m.group(1)) if sig_m else None,
        })
    return {
        "session_id": session_id,
        "objective": sanitize_content(s.get("objective", "")),
        "start_time": s.get("start_time"),
        "end_time": s.get("end_time"),
        "total_cycles": s.get("cycle", 0),
        "status": "complete",
        "project_name": WORKSPACE_PROJECT,
        "branch_name": WORKSPACE_BRANCH,
        "models": {
            "model_a": model_str("model_a"),
            "model_b": model_str("model_b"),
            "model_c": model_str("model_c"),
            "parietal": model_str("parietal"),
            "projenius": model_str("projenius"),
        },
        "distillation_method": s.get("distillation_method", "failed"),
        "knowtext_version": s.get("knowtext_version"),
        "friction_profile": profile,
        "friction_reasons": reasons,
        "challenge_count": counts["challenge"],
        "uphold_count": counts["uphold"],
        "reject_count": counts["reject"],
        "pursue_both_count": counts["pursue_both"],
        "escalate_count": counts["escalate"],
        "avg_friction_signal": avg_signal,
        "signal_variance": variance,
        "peak_signal": max(profile) if profile else 0,
        "cycles_to_first_challenge": first_challenge,
        "cycles_to_session_end": s.get("cycle", 0),
        "session_ledger": s.get("session_ledger", []),
        "challenge_events_raw": s.get("challenge_events", []),
        "transcript_turns": transcript_turns,
        "behavioral_observations": behavioral_obs,
        "artifacts": [
            {"label": a.get("label"),
             "content": sanitize_content(a.get("content", "")),
             "path": a.get("path")}
            for a in s.get("artifacts", [])
        ],
        "knowtext_content": sanitize_content(
            load_file(CONFIG["knowtext_path"]) or ""),
    }

def record_workspace_write_failure(msg, payload=None):
    """On a failed workspace write: append to the session error list,
    update the already-written Session Log artifact in place so the
    session carries the record of its own failed persistence, and dump
    the payload to /tmp so a dead write is recoverable, not just mourned."""
    active_session["errors"].append(msg)
    try:
        for a in active_session["artifacts"]:
            if a.get("label") == "Session Log" and a.get("path"):
                a["content"] = a["content"] + "\n" + msg
                save_file(a["path"], a["content"])
                break
    except Exception as e:
        print(f"[WORKSPACE WRITE] could not update session log artifact: {e}", flush=True)
    if payload is not None:
        try:
            import json as _json
            sid = str(payload.get("session_id", "unknown")).replace("/", "_")
            dump_path = f"/tmp/failed_session_{sid}.json"
            with open(dump_path, "w", encoding="utf-8") as f:
                _json.dump(payload, f)
            print(f"[WORKSPACE WRITE] payload dumped to {dump_path} for recovery", flush=True)
            socketio.emit('routing_action', {
                'type': 'error',
                'message': f'Failed-write payload saved to {dump_path} — recoverable until next redeploy.'
            })
        except Exception as e:
            print(f"[WORKSPACE WRITE] payload dump failed: {e}", flush=True)


def write_session_to_workspace():
    """Write the completed session to the workspace database. Fail-loud:
    announces entry BEFORE building the payload, prints every step to
    stdout (Railway logs persist), retries 3x treating any non-200 OR
    exception as retryable, and on final failure records the failure in
    the session itself plus a /tmp recovery dump."""
    print("[WORKSPACE WRITE] entering write_session_to_workspace", flush=True)
    socketio.emit('routing_action', {
        'type': 'distillation',
        'message': 'Writing session to workspace database...'
    })
    if not WORKSPACE_URL:
        msg = 'Workspace write SKIPPED — WORKSPACE_URL not configured.'
        print(f"[WORKSPACE WRITE] {msg}", flush=True)
        socketio.emit('routing_action', {'type': 'error', 'message': msg})
        record_workspace_write_failure(msg, payload=None)
        return False
    try:
        payload = build_session_payload()
    except Exception as e:
        msg = f'Workspace write FAILED building payload: {type(e).__name__}: {e}'
        print(f"[WORKSPACE WRITE] {msg}", flush=True)
        socketio.emit('routing_action', {'type': 'error', 'message': msg})
        record_workspace_write_failure(msg, payload=None)
        return False
    api_key = os.environ.get("WORKSPACE_API_KEY", "").strip()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    last_error = None
    for attempt in range(1, 4):
        try:
            print(f"[WORKSPACE WRITE] POST attempt {attempt}/3 to {WORKSPACE_URL}/api/session", flush=True)
            response = http_requests.post(
                f"{WORKSPACE_URL}/api/session",
                json=payload,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                print("[WORKSPACE WRITE] SUCCESS — 200 from workspace", flush=True)
                socketio.emit('routing_action', {
                    'type': 'distillation',
                    'message': 'Session written to workspace database.'
                })
                return True
            last_error = f'HTTP {response.status_code}: {response.text[:200]}'
            print(f"[WORKSPACE WRITE] attempt {attempt} failed — {last_error}", flush=True)
        except Exception as e:
            last_error = f'{type(e).__name__}: {e}'
            print(f"[WORKSPACE WRITE] attempt {attempt} exception — {last_error}", flush=True)
        if attempt < 3:
            time.sleep(5)
    msg = f'Workspace write FAILED after 3 attempts — {last_error}'
    print(f"[WORKSPACE WRITE] {msg}", flush=True)
    socketio.emit('routing_action', {'type': 'error', 'message': msg})
    record_workspace_write_failure(msg, payload=payload)
    return False


def rotate_backups():
    if os.path.exists(CONFIG["backup1_path"]):
        save_file(CONFIG["backup2_path"], load_file(CONFIG["backup1_path"]))
    if os.path.exists(CONFIG["knowtext_path"]):
        save_file(CONFIG["backup1_path"], load_file(CONFIG["knowtext_path"]))

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def artifact_path(label):
    os.makedirs(CONFIG["artifacts_dir"], exist_ok=True)
    return os.path.join(CONFIG["artifacts_dir"], f"{timestamp()}_{label}.txt")

# -----------------------------------------
# GITHUB PERSISTENCE
# -----------------------------------------
GITHUB_REPO = "PatrickKillebrew/ontinuity"
GITHUB_FILE_PATH = get_github_knowtext_path()
GITHUB_BRANCH = "main"

def github_pull_knowtext():
    """Pull knowtext_current.txt from GitHub if local file is missing or empty."""
    token = runtime_github.get("token") or os.environ.get("GITHUB_TOKEN", "").strip()
    repo = runtime_github.get("repo") or GITHUB_REPO
    if not token:
        return False
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE_PATH}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        response = http_requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            save_file(CONFIG["knowtext_path"], content)
            socketio.emit('routing_action', {'type': 'injection', 'message': 'Knowtext pulled from GitHub.'})
            return True
        else:
            socketio.emit('routing_action', {'type': 'error', 'message': f'GitHub pull failed: {response.status_code}'})
            return False
    except Exception as e:
        socketio.emit('routing_action', {'type': 'error', 'message': f'GitHub pull error: {str(e)}'})
        return False

def github_push_knowtext():
    """Commit updated knowtext_current.txt to GitHub after successful distillation."""
    token = runtime_github.get("token") or os.environ.get("GITHUB_TOKEN", "").strip()
    repo = runtime_github.get("repo") or GITHUB_REPO
    if not token:
        return False
    content = load_file(CONFIG["knowtext_path"])
    if not content:
        return False
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE_PATH}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        # Get current file SHA (required for update)
        get_response = http_requests.get(url, headers=headers, timeout=30)
        sha = get_response.json().get("sha", "") if get_response.status_code == 200 else ""
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        body = {
            "message": f"Knowtext update — {timestamp()}",
            "content": encoded,
            "branch": GITHUB_BRANCH
        }
        if sha:
            body["sha"] = sha
        put_response = http_requests.put(url, headers=headers, json=body, timeout=30)
        if put_response.status_code in (200, 201):
            socketio.emit('routing_action', {'type': 'distillation', 'message': 'Knowtext committed to GitHub.'})
            return True
        else:
            socketio.emit('routing_action', {'type': 'error', 'message': f'GitHub push failed: {put_response.status_code}'})
            return False
    except Exception as e:
        socketio.emit('routing_action', {'type': 'error', 'message': f'GitHub push error: {str(e)}'})
        return False

# -----------------------------------------
# KNOWTEXT SECTION EXTRACTION
# -----------------------------------------
def get_working_context(knowtext):
    """Extract the WORKING CONTEXT section from Knowtext."""
    if not knowtext:
        return ""
    if "--- WORKING CONTEXT ---" in knowtext:
        parts = knowtext.split("--- WORKING CONTEXT ---")
        if len(parts) > 1:
            working = parts[1]
            if "--- ARCHIVE ---" in working:
                working = working.split("--- ARCHIVE ---")[0]
            return working.strip()
    # Fallback: return everything after schema version line
    lines = knowtext.split("\n")
    return "\n".join(lines[2:]).strip()

def get_model_b_context(knowtext):
    """Extract Active Frameworks and Correction History from Working Context for Model B."""
    working = get_working_context(knowtext)
    if not working:
        return ""
    result = []
    sections = ["Active Frameworks", "Correction History"]
    lines = working.split("\n")
    current_section = None
    current_content = []
    for line in lines:
        matched = next((s for s in sections if line.strip().startswith(s + ":")), None)
        if matched:
            if current_section:
                result.append(f"{current_section}:\n" + "\n".join(current_content).strip())
            current_section = matched
            current_content = [line.split(":", 1)[-1].strip() if ":" in line else ""]
        elif current_section:
            # Stop at next top-level section not in our list
            if any(line.strip().startswith(s + ":") for s in
                   ["Open Questions", "Valence Mapping", "Delta Log", "Identity", "Climate Notes"]):
                result.append(f"{current_section}:\n" + "\n".join(current_content).strip())
                current_section = None
                current_content = []
            else:
                current_content.append(line)
    if current_section:
        result.append(f"{current_section}:\n" + "\n".join(current_content).strip())
    return "\n\n".join(result)

def get_session_ledger_summary():
    """Return compressed summary of established results from current session."""
    if not active_session["session_ledger"]:
        return ""
    lines = [f"Cycle {entry['cycle']}: {entry['summary']}"
             for entry in active_session["session_ledger"]]
    return "SESSION ESTABLISHED RESULTS:\n" + "\n".join(lines)

def extract_rejected_claim(response, cycle):
    """Extract the core rejected claim from an UPHOLD ruling or DIRECT CORRECTION.
    Appends a one-line summary to active_session['rejected_claims']."""
    if not response:
        return
    lines = response.split("\n")
    # Look for the specific challenged claim or correction content
    keywords = ["the challenged claim", "the claim", "the statement",
                "directly contradicts", "incorrectly asserts", "erroneously",
                "DIRECT CORRECTION", "cannot", "has not been", "no evidence"]
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw.lower() in line_lower for kw in keywords):
            # Collect this line and next substantive line
            candidate = line.strip()
            if len(candidate) > 30:
                summary = f"Cycle {cycle}: {candidate[:250]}"
                if summary not in active_session["rejected_claims"]:
                    active_session["rejected_claims"].append(summary)
                return
    # Fallback: use first substantive line
    for line in lines:
        if len(line.strip()) > 40:
            summary = f"Cycle {cycle}: {line.strip()[:200]}"
            if summary not in active_session["rejected_claims"]:
                active_session["rejected_claims"].append(summary)
            return

def get_datetime_injection():
    """F.4: inject the real current date/time from the system clock. The model has
    no clock; without this line any date it states is a fabrication by construction."""
    now = datetime.datetime.utcnow().strftime("%A, %Y-%m-%d %H:%M UTC")
    return ("\n\n[GROUND TRUTH — CURRENT DATE/TIME]: " + now +
            ". Injected by the system clock. Use this for any date or time reference. "
            "Never state a current date or time from memory.")

CONTRACT_LINE = re.compile(
    r"^\s*C(\d+)\s*\|\s*(VERIFIABLE|JUDGED)\s*\|\s*([^|]+?)\s*(?:\|\s*EVIDENCE:\s*(.+?))?\s*$",
    re.IGNORECASE | re.MULTILINE)

def parse_contract(text):
    """Parse CONTRACT criteria lines from a PRE_SESSION response.
    Returns list of {id, kind, text, evidence}. Empty list when none found —
    every consumer treats an empty contract as 'no contract' (backward compatible)."""
    out = []
    for m in CONTRACT_LINE.finditer(text or ""):
        out.append({
            "id": f"C{m.group(1)}",
            "kind": m.group(2).upper(),
            "text": m.group(3).strip()[:300],
            "evidence": (m.group(4) or "").strip()[:200],
        })
    return out

def get_contract_injection():
    """Format the frozen session contract for injection into BOTH models, every cycle."""
    contract = active_session.get("contract", [])
    if not contract:
        return ""
    lines = []
    for c in contract:
        ev = f" | evidence: {c['evidence']}" if c["evidence"] else ""
        lines.append(f"  {c['id']} [{c['kind']}] {c['text']}{ev}")
    return (
        "\n\n--- SESSION CONTRACT (frozen at session start) ---\n"
        "The deliverable is complete when and only when every criterion below is met. "
        "Criteria cannot be added, removed, or reinterpreted mid-session. VERIFIABLE "
        "criteria are checked by code against the execution log at close; JUDGED "
        "criteria are assessed by the Challenger.\n" + "\n".join(lines) +
        "\n--- END SESSION CONTRACT ---"
    )

def contract_close_check():
    """Deterministic close-gate walk of the contract. Returns list of unmet
    VERIFIABLE criteria as {id, text, reason}. Rules:
    - evidence names a `command` -> requires a PASSED execution log entry for it
    - evidence mentions the injection/ground-truth line -> satisfied by construction
    - otherwise uncheckable by code -> left to the Challenger (skipped here)
    JUDGED criteria are never checked here — they are the Challenger's call."""
    unmet = []
    for c in active_session.get("contract", []):
        if c["kind"] != "VERIFIABLE":
            continue
        ev = c.get("evidence", "")
        cmds = re.findall(r"`([^`]{2,120})`", ev)
        if cmds:
            for cmd in cmds:
                passed = [e for e in _f3_find_entries(cmd)
                          if e["status"].upper().startswith("PASSED")]
                if not passed:
                    unmet.append({"id": c["id"], "text": c["text"],
                                  "reason": f"requires a successful execution of `{cmd}` — no PASSED log entry exists."})
                    break
        elif re.search(r"inject|ground.?truth", ev, re.IGNORECASE):
            continue  # the injection is always present by construction
        # else: uncheckable by code — Challenger territory, not a code refusal
    return unmet

def get_results_board_injection():
    """F.9: format the session results board for injection. Empty string if no results yet.
    Mirrors rejected_claims: survives conversation trimming, so early results never evaporate."""
    board = active_session.get("results_board", [])
    if not board:
        return ""
    lines = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(board))
    return (
        "\n\n--- ESTABLISHED THIS SESSION (ground truth, full values) ---\n"
        "These results were really executed and their outputs recorded. Repeat them, "
        "build on them, cite them in the deliverable. Do not re-derive or re-run "
        "them unless verification requires it:\n" + lines +
        "\n--- END ESTABLISHED RESULTS ---"
    )

def get_rejected_claims_injection():
    """Format rejected claims list for injection into Researcher system prompt.
    Returns empty string if no claims have been rejected yet."""
    if not active_session["rejected_claims"]:
        return ""
    lines = "\n".join(f"  {i+1}. {claim}"
                      for i, claim in enumerate(active_session["rejected_claims"]))
    return (
        "\n\n--- SESSION RULINGS: DO NOT REINTRODUCE ---\n"
        "The following claims have been formally ruled against in this session "
        "by the Challenger or Parietal. Do not reintroduce them in any form, "
        "directly or as variants:\n" + lines +
        "\n--- END SESSION RULINGS ---"
    )

# -----------------------------------------
# PROJENIUS — PROJECT-LEVEL CONSCIOUSNESS
# -----------------------------------------
def call_projenius(function_tag, **kwargs):
    """Call a Projenius function by tag. Returns response string or None.
    Only fires when Projenius has been explicitly configured with a key and url."""
    projenius_cfg = get_effective_config("projenius")
    has_projenius = bool(projenius_cfg.get("api_key") and projenius_cfg.get("url"))
    if not has_projenius:
        return None
    system = load_file("prompts/projenius_system.txt") or ""
    parts = [f"[PROJENIUS: {function_tag}]"]
    for k, v in kwargs.items():
        if v:
            parts.append(f"{k.upper()}:\n{v}")
    content = "\n\n".join(parts)
    messages = [{"role": "user", "content": content}]
    socketio.emit('routing_action', {'type': 'parietal', 'message': f'Projenius {function_tag}...'})
    response = call_model("projenius", messages, system_override=system)
    return response

def run_projenius_orient(objective, knowtext):
    """Run ORIENT — returns project-level context string or None."""
    working = get_working_context(knowtext) if knowtext else ""
    response = call_projenius("ORIENT",
                              session_objective=objective,
                              knowtext_active_frameworks=working)
    return response

def run_projenius_synthesize(delta_log, knowtext):
    """Run SYNTHESIZE — updates Established Results Ledger after session distillation."""
    if not delta_log:
        return None
    branch = os.environ.get("WORKSPACE_BRANCH", "main")
    session_id = active_session.get("start_time", "unknown")
    correction_history = ""
    for entry in active_session.get("session_ledger", []):
        if "retract" in entry.get("summary", "").lower():
            correction_history += f"Cycle {entry['cycle']}: {entry['summary']}\n"
    response = call_projenius("SYNTHESIZE",
                               delta_log=delta_log,
                               branch=branch,
                               session_id=session_id,
                               correction_history=correction_history or "None")
    return response

def run_projenius_search(query, context, search_results):
    """Run SEARCH — synthesizes raw Brave results into grounded answer with citations."""
    if not query or not search_results:
        return None
    # Format search results for Projenius
    results_text = ""
    for i, r in enumerate(search_results[:5], 1):
        results_text += f"[{i}] {r.get('title','')}\n{r.get('url','')}\n{r.get('description','')}\nAge: {r.get('age','unknown')}\n\n"
    response = call_projenius("SEARCH",
                               query=query,
                               context=context or "NONE",
                               search_results=results_text)
    return response

def call_workspace_search(query, context=""):
    """POST to workspace /search endpoint. Returns list of result dicts or None."""
    if not WORKSPACE_URL:
        return None
    api_key = os.environ.get("WORKSPACE_API_KEY", "").strip()
    try:
        payload = {"query": query, "context": context, "count": 5}
        headers = {"Content-Type": "application/json", "X-API-Key": api_key}
        response = http_requests.post(
            f"{WORKSPACE_URL}/search",
            json=payload,
            headers=headers,
            timeout=20
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            return None
    except Exception as e:
        socketio.emit('routing_action', {'type': 'error', 'message': f'Workspace search error: {str(e)}'})
        return None

def call_workspace_run(command):
    """POST to workspace /run endpoint. Returns {stdout, stderr, returncode} or None.
    Command must be in the safe_commands whitelist on the workspace server."""
    if not WORKSPACE_URL:
        return None
    api_key = os.environ.get("WORKSPACE_API_KEY", "").strip()
    try:
        payload = {"command": command}
        headers = {"Content-Type": "application/json", "X-API-Key": api_key}
        response = http_requests.post(
            f"{WORKSPACE_URL}/run",
            json=payload,
            headers=headers,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            # F.10: the server's 403 includes safe_commands — teach the model the
            # legal moves instead of letting it guess (June 4 evening session spent
            # ~10 cycles probing; its own ledger said "contents of whitelist unknown").
            safe = []
            try:
                safe = response.json().get("safe_commands", [])
            except Exception:
                pass
            wl = ("\nWhitelisted commands (the ONLY commands that will execute): "
                  + "; ".join(safe)) if safe else ""
            return {"stdout": "", "stderr": f"Command not in whitelist: {command}{wl}", "returncode": 403}
        else:
            return {"stdout": "", "stderr": f"Workspace /run returned {response.status_code}", "returncode": response.status_code}
    except Exception as e:
        socketio.emit('routing_action', {'type': 'error', 'message': f'Workspace run error: {str(e)}'})
        return None

def extract_search_request(response):
    """Extract QUERY and CONTEXT from lines above SEARCH_REQUEST tag in Model A response.
    Returns (query, context) tuple. Context may be empty string."""
    lines = response.split("\n")
    query = ""
    context = ""
    for line in lines:
        line = line.strip()
        if line.upper().startswith("QUERY:"):
            query = line[6:].strip()
        elif line.upper().startswith("CONTEXT:"):
            ctx = line[8:].strip()
            if ctx.upper() != "NONE":
                context = ctx
    return query, context

def extract_verify_citation(response):
    """Extract CITATION, CLAIM, and QUERY from lines above VERIFY_CITATION tag in Model B response.
    Returns (citation, claim, query) tuple."""
    lines = response.split("\n")
    citation = ""
    claim = ""
    query = ""
    for line in lines:
        line = line.strip()
        if line.upper().startswith("CITATION:"):
            citation = line[9:].strip()
        elif line.upper().startswith("CLAIM:"):
            claim = line[6:].strip()
        elif line.upper().startswith("QUERY:"):
            query = line[6:].strip()
    return citation, claim, query

def extract_code_test(response):
    """Extract COMMAND from lines above CODE_TEST tag in Model A response.
    Returns command string or empty string."""
    lines = response.split("\n")
    for line in lines:
        line = line.strip()
        if line.upper().startswith("COMMAND:"):
            return line[8:].strip()
    return ""

# -----------------------------------------
# F.2: EXECUTION LOG + CLAIM-WITHOUT-EXECUTION DETECTION
# -----------------------------------------
def record_execution(kind, detail, status, result=""):
    """Record a real workspace execution in the session's deterministic execution log.
    kind: 'code_test' | 'search' | 'citation'. This log is the ground truth the
    F.3 fabrication detector checks claims against. `result` stores a snippet of
    the real output so misreported values can be detected, not just missing runs."""
    active_session["execution_log"].append({
        "cycle": active_session["cycle"],
        "kind": kind,
        "detail": str(detail)[:300],
        "status": str(status)[:100],
        "result": str(result)[:2000],
        "at": timestamp()
    })

# Conservative claim markers, v2. v1 covered first-person active claims; the
# 2026-06-04 session fabricated in PASSIVE voice ("The command ... was executed
# successfully", "the version string retrieved was") and passed. Passive forms
# are now covered, scoped to execution contexts (command/script/test/code/query)
# so prose about *other* people's experiments still passes.
CLAIM_PATTERN = re.compile(
    r"(\bI\s+(ran|executed|tested|invoked)\b"
    r"|\bthe\s+(command|script|test)\s+(returned|produced|output|printed|exited)\b"
    r"|\b(command|script|test|code|query|check)\b[^.\n]{0,60}\b(was|were)\s+(executed|run|tested|invoked)\b"
    r"|\b(executed|ran|completed)\s+successfully\b"
    r"|\b(version|output|result)\s+string\s+(retrieved|returned|is|was)\b"
    r"|\b(stdout|stderr|exit\s+code|return\s+code)\s*[:=]"
    r"|\bsearch\s+results?\s+(show|showed|returned|confirm)\b)",
    re.IGNORECASE
)

# At-close pattern: aggressive on purpose. A false positive here costs nothing
# but one real execution before the session may close — the right price.
CLOSE_CLAIM_PATTERN = re.compile(
    r"(\b(was|were)\s+(executed|run|tested|verified|retrieved)\b"
    r"|\b(executed|ran|verified|confirmed|retrieved)\b"
    r"|\bexact\s+version\b"
    r"|\b(stdout|stderr|exit\s+code|return\s+code)\b)",
    re.IGNORECASE
)

def session_claims_execution(texts):
    """True if any of the given texts (final response, ledger summaries) claims execution."""
    for t in texts:
        if t and (CLAIM_PATTERN.search(t) or CLOSE_CLAIM_PATTERN.search(t)):
            return True
    return False

def claims_execution_without_log(response):
    """True when the Researcher's prose claims an execution but the execution log
    shows nothing ran this cycle. Deterministic, code-side; conservative by design."""
    if not response or not CLAIM_PATTERN.search(response):
        return False
    this_cycle = active_session["cycle"]
    ran_this_cycle = any(e["cycle"] == this_cycle for e in active_session["execution_log"])
    return not ran_this_cycle

# -----------------------------------------
# F.3 — DETERMINISTIC FABRICATION DETECTOR
# Claims about executions are parsed and checked against the execution log as a
# structured lookup. Three verdicts: CORROBORATED (log entry matches),
# FABRICATED (no entry exists), MISREPORTED (entry exists, reported result
# contradicts the stored output). Negated/honest statements ("was not executed",
# "could not be verified", "UNMEASURED") are not claims and are skipped — which
# retires the close-gate negation false positive by construction.
# -----------------------------------------
F3_NEGATION = re.compile(
    r"(\bnot\s+(executed|run|injected|returned|available|reachable|measured|verified|determined)\b"
    r"|\b(was|were|is|are)\s+(never|not)\b"
    r"|\bno\s+(result|output|response|entry|version|command|execution)\b"
    r"|\b(could\s*not|couldn't|cannot|can't|unable\s+to|failed\s+to|fail\s+to)\b"
    r"|\bUNMEASURED\b|\bUNDETERMINED\b|\bunverified\b|\bunreachable\b"
    r"|\b(missing|absent|pending|awaiting|without)\b"
    r"|\bopen\s+question\b|\bresolution\s+path\b)",
    re.IGNORECASE
)

F3_CMDREF = re.compile(r"`([^`\n]{2,120})`")  # backticks ONLY — quoted strings are outputs, not commands (June 5 lesson)
F3_VALUE = re.compile(r"\b\d+\.\d+(?:\.\d+)?\b")  # version-like values: 3.11.9, 3.10

def _f3_chunks(text):
    """Split prose into checkable chunks: line-ish sentences."""
    raw = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [c.strip() for c in raw if c and len(c.strip()) > 8]

F3_RESULT_VERB = re.compile(
    r"\b(returned|confirmed|produced|output|outputs|printed|retrieved|reported|showed|shows|gave|yielded|executed|ran|succeeded|passed|verified)\b",
    re.IGNORECASE
)

def extract_execution_claims(text):
    """Parse execution claims from prose. Returns list of dicts:
    {chunk, commands[], values[], generic} — generic=True when the chunk claims
    an execution without naming a specific command. A chunk is a claim when the
    prose patterns match OR when it references a concrete command alongside a
    result verb (catches `cmd` returned X, confirmed by `cmd`, etc.)."""
    claims = []
    for chunk in _f3_chunks(text):
        if F3_NEGATION.search(chunk):
            continue  # honest non-claims are exempt by construction
        commands = list(F3_CMDREF.findall(chunk))
        commands = [c.strip() for c in commands if c and not c.strip().startswith("[")]
        is_claim = bool(CLAIM_PATTERN.search(chunk)) or (bool(commands) and bool(F3_RESULT_VERB.search(chunk)))
        if not is_claim:
            continue
        values = F3_VALUE.findall(chunk)
        claims.append({
            "chunk": chunk[:240],
            "commands": commands,
            "values": values,
            "generic": not commands
        })
    return claims

def _f3_find_entries(command):
    """Log entries whose recorded detail overlaps the claimed command (either direction)."""
    cl = command.lower().strip()
    hits = []
    for e in active_session["execution_log"]:
        dl = e["detail"].lower().strip()
        if cl and dl and (cl in dl or dl in cl):
            hits.append(e)
    return hits

F3_FAILURE_ASSERTION = re.compile(
    r"\b(not\s+in\s+(the\s+)?whitelist|failed|was\s+not\s+executed|could\s+not\s+be\s+executed"
    r"|did\s+not\s+(run|execute|return)|no\s+output|blocked|rejected|unsuccessful)\b",
    re.IGNORECASE
)

def check_denied_successes(text):
    """F.3 v2 — FABRICATED FAILURE detection (the June 4 evening specimen: the
    deliverable listed `python --version` as 'Not in whitelist' while the log
    held two PASSED entries for it). For every chunk that NAMES a command and
    asserts its failure/non-execution, check the log: a PASSED entry for that
    command makes the denial MISREPORTED. Negation cannot shield a claim that
    names a command with a successful log entry."""
    verdicts = []
    for chunk in _f3_chunks(text):
        commands = list(F3_CMDREF.findall(chunk))
        commands = [c.strip() for c in commands if c and not c.strip().startswith("[")]
        if not commands or not F3_FAILURE_ASSERTION.search(chunk):
            continue
        for cmd in commands:
            passed = [e for e in _f3_find_entries(cmd) if e["status"].upper().startswith("PASSED")]
            if passed:
                e = passed[-1]
                shown = (" Its recorded output: " + e["result"][:120]) if e.get("result") else ""
                verdicts.append({"verdict": "MISREPORTED", "claim": chunk[:240],
                                 "reason": f"`{cmd}` is asserted to have failed or been blocked, but the execution log shows it PASSED in cycle {e['cycle']}.{shown}"})
    return verdicts

def check_execution_claims(text):
    """F.3 core: every execution claim in `text` is checked against the execution
    log. Returns list of verdict dicts {verdict, claim, reason}. Deterministic —
    no model judgment anywhere in this path. Includes the v2 anti-denial check:
    fabricated failures (denying logged successes) are caught symmetrically with
    fabricated successes."""
    verdicts = list(check_denied_successes(text))
    log = active_session["execution_log"]
    for claim in extract_execution_claims(text):
        if claim["generic"]:
            if not log:
                verdicts.append({"verdict": "FABRICATED", "claim": claim["chunk"],
                                 "reason": "Execution claimed but the execution log is empty — nothing has run this session."})
            elif claim["values"]:
                # A claimed value must appear in at least one stored result snippet,
                # when any snippets exist to check against.
                snippets = [e.get("result", "") for e in log if e.get("result")]
                if snippets and not any(v in s for v in claim["values"] for s in snippets):
                    verdicts.append({"verdict": "MISREPORTED", "claim": claim["chunk"],
                                     "reason": f"Claimed value(s) {claim['values']} do not appear in any recorded execution output."})
                else:
                    verdicts.append({"verdict": "CORROBORATED", "claim": claim["chunk"], "reason": "Execution log is non-empty and no recorded output contradicts the claim."})
            else:
                verdicts.append({"verdict": "CORROBORATED", "claim": claim["chunk"], "reason": "Execution log is non-empty."})
            continue
        for cmd in claim["commands"]:
            entries = _f3_find_entries(cmd)
            if not entries:
                verdicts.append({"verdict": "FABRICATED", "claim": claim["chunk"],
                                 "reason": f"No execution log entry exists for `{cmd}` — this command never ran."})
                continue
            entry = entries[-1]
            failed = entry["status"].upper().startswith("FAILED")
            asserts_success = bool(re.search(r"\b(success|passed|confirmed|verified|retrieved|returned)\b", claim["chunk"], re.IGNORECASE))
            if failed and asserts_success:
                verdicts.append({"verdict": "MISREPORTED", "claim": claim["chunk"],
                                 "reason": f"`{cmd}` ran but its recorded status is {entry['status']} — the claim asserts success."})
            elif claim["values"] and entry.get("result") and not any(v in entry["result"] for v in claim["values"]):
                all_outputs = [e.get("result", "") for e in log if e.get("result")]
                if any(v in s for v in claim["values"] for s in all_outputs):
                    verdicts.append({"verdict": "CORROBORATED", "claim": claim["chunk"],
                                     "reason": f"Claimed value(s) {claim['values']} are recorded in another execution's output this session (cross-attribution in prose, not fabrication)."})
                else:
                    verdicts.append({"verdict": "MISREPORTED", "claim": claim["chunk"],
                                     "reason": f"`{cmd}` ran, but claimed value(s) {claim['values']} do not appear in any recorded output."})
            else:
                verdicts.append({"verdict": "CORROBORATED", "claim": claim["chunk"],
                                 "reason": f"Log entry for `{cmd}` ({entry['status']}) supports the claim."})
    return verdicts

def f3_bad(verdicts):
    return [v for v in verdicts if v["verdict"] in ("FABRICATED", "MISREPORTED")]

def f3_summary(verdicts):
    if not verdicts:
        return "No execution claims present."
    lines = []
    for v in verdicts[:6]:
        lines.append(f"{v['verdict']}: \"{v['claim'][:100]}\" — {v['reason']}")
    return "\n".join(lines)

# -----------------------------------------
# API CALLS - PROVIDER AGNOSTIC
# -----------------------------------------
def get_api_key(role):
    """Get API key — runtime override from frontend takes precedence over environment."""
    if role in runtime_configs and runtime_configs[role].get('key'):
        return runtime_configs[role]['key'].strip()
    return CONFIG[role]["api_key"].strip()

def call_openai_format(endpoint_config, messages, role, max_tokens=2000):
    headers = {
        "Authorization": f"Bearer {get_api_key(role)}",
        "Content-Type": "application/json"
    }
    body = {
        "model": endpoint_config["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3
    }
    delays = [30, 60, 120]
    for attempt, delay in enumerate(delays + [None]):
        try:
            response = http_requests.post(
                endpoint_config["url"], headers=headers, json=body, timeout=120
            )
            if response.status_code == 429:
                if delay is None:
                    msg = "Rate limit — max retries exceeded. Wait a few minutes and start a new session."
                    active_session["errors"].append("API error: 429 rate limit, max retries exceeded")
                    socketio.emit('routing_action', {'type': 'error', 'message': msg})
                    return None
                msg = f"Rate limit — waiting {delay}s before retry {attempt + 1}/3..."
                socketio.emit('routing_action', {'type': 'error', 'message': msg})
                time.sleep(delay)
                continue
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except http_requests.exceptions.Timeout as e:
            # Read-timeout flake (Novita): retry instead of killing the session.
            if delay is not None:
                socketio.emit('routing_action', {'type': 'error', 'message': f"API read timeout — retrying in 5s (attempt {attempt + 1}/3)..."})
                time.sleep(5)
                continue
            active_session["errors"].append(f"API error: {str(e)}")
            socketio.emit('routing_action', {'type': 'error', 'message': f"API call failed after retries: {str(e)}"})
            return None
        except Exception as e:
            active_session["errors"].append(f"API error: {str(e)}")
            socketio.emit('routing_action', {'type': 'error', 'message': f"API call failed: {str(e)}"})
            return None

def call_anthropic_format(endpoint_config, system_prompt, messages, role, max_tokens=2000):
    headers = {
        "x-api-key": get_api_key(role),
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    body = {
        "model": endpoint_config["model"],
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages
    }
    try:
        response = http_requests.post(
            endpoint_config["url"], headers=headers, json=body, timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        active_session["errors"].append(f"API error: {str(e)}")
        socketio.emit('routing_action', {'type': 'error', 'message': f"API call failed: {str(e)}"})
        return None

def call_gemini_native(endpoint_config, system_prompt, messages, role, max_tokens=2000):
    """Call Google Gemini using native API format with x-goog-api-key header."""
    api_key = get_api_key(role)
    model = endpoint_config["model"]
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    # Convert OpenAI-style messages to Gemini format
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            pass  # handled as systemInstruction below
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        response = http_requests.post(url, headers=headers, json=body, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        active_session["errors"].append(f"Gemini API error: {str(e)}")
        socketio.emit('routing_action', {'type': 'error', 'message': f"Gemini API call failed: {str(e)}"})
        return None

def call_model(role, conversation_messages, system_override=None, max_tokens=None):
    config = get_effective_config(role)
    if not config.get("url") or not config.get("api_key"):
        msg = f"Model '{role}' has no URL or API key configured — skipping call."
        active_session["errors"].append(msg)
        socketio.emit('routing_action', {'type': 'error', 'message': msg})
        return None
    # Parietal DISTILL needs more room — default higher for parietal role
    if max_tokens is None:
        max_tokens = 4000 if role == "parietal" else 2000
    api_format = detect_api_format(config["url"])
    system_prompt = system_override or load_file(config["system_prompt_path"]) or ""
    if api_format == "anthropic":
        return call_anthropic_format(config, system_prompt, conversation_messages, role, max_tokens)
    elif api_format == "gemini":
        return call_gemini_native(config, system_prompt, conversation_messages, role, max_tokens)
    else:
        messages = [{"role": "system", "content": system_prompt}] + conversation_messages
        return call_openai_format(config, messages, role, max_tokens)

# -----------------------------------------
# TAG AND SIGNAL UTILITIES
# -----------------------------------------
def extract_tag(response):
    match = re.search(r'\[CYCLE_STATUS:\s*([\w_]+)\]', response)
    return match.group(1) if match else "CONTINUE"

def has_valid_tag(response):
    """True only if the response contains a real bracketed status tag.
    Used to detect malformed cycles, where extract_tag's CONTINUE default would hide an omitted tag."""
    return bool(response and re.search(r'\[CYCLE_STATUS:\s*[\w_]+\]', response))

def extract_challenger_assessment(response):
    """Parse the Challenger's structured session-state assessment line.
    Returns dict with keys deliverable, progress, result_check.
    Missing fields default conservatively: deliverable=incomplete, progress=no, result_check=na.
    Conservative defaults mean a Challenger that omits the line cannot accidentally signal completion or progress."""
    deliverable = "incomplete"
    progress = "no"
    result_check = "na"
    if response:
        m = re.search(r'DELIVERABLE:\s*(complete|incomplete)', response, re.IGNORECASE)
        if m:
            deliverable = m.group(1).lower()
        m = re.search(r'PROGRESS:\s*(yes|no)', response, re.IGNORECASE)
        if m:
            progress = m.group(1).lower()
        m = re.search(r'RESULT_CHECK:\s*(present|absent|na)', response, re.IGNORECASE)
        if m:
            result_check = m.group(1).lower()
    return {"deliverable": deliverable, "progress": progress, "result_check": result_check}

def extract_signal(response):
    match = re.search(r'SIGNAL:\s*([0-4])', response)
    return int(match.group(1)) if match else 0

def get_ambient_signal_line(signal):
    labels = {0: "clear", 1: "nominal", 2: "caution", 3: "warning", 4: "override"}
    return f"AMBIENT_SIGNAL: {signal} ({labels.get(signal, 'unknown')})"

def extract_ledger_entry(response, cycle):
    """Extract a one-line summary of established results from Model A response."""
    lines = response.split("\n")
    keywords = ["ESTABLISHED:", "RESULT:", "CONFIRMED:", "CONCLUDED:"]
    
    # First pass: look for keyword lines and capture content after them
    for i, line in enumerate(lines):
        if any(kw in line.upper() for kw in keywords):
            # Check if content is on the same line after the keyword
            for kw in keywords:
                idx = line.upper().find(kw)
                if idx != -1:
                    inline_content = line[idx + len(kw):].strip()
                    if len(inline_content) > 20:
                        active_session["session_ledger"].append({"cycle": cycle, "summary": inline_content[:300]})
                        return
            # Content is on subsequent lines — collect next substantive lines
            collected = []
            for j in range(i + 1, min(i + 6, len(lines))):
                next_line = lines[j].strip()
                if next_line and len(next_line) > 10:
                    # Stop if we hit another section header
                    if any(kw in next_line.upper() for kw in keywords + ["ASSUMED:", "OPEN QUESTIONS:", "NEXT STEPS:"]):
                        break
                    collected.append(next_line)
                    if len(" ".join(collected)) > 250:
                        break
            if collected:
                summary = " ".join(collected)[:300]
                active_session["session_ledger"].append({"cycle": cycle, "summary": summary})
                return

    # Fallback: use first substantive line
    for line in lines:
        if len(line.strip()) > 40:
            active_session["session_ledger"].append({"cycle": cycle, "summary": line.strip()[:200]})
            return

# -----------------------------------------
# HUMAN INPUT
# -----------------------------------------
def wait_for_human_input(input_type, context):
    active_session["waiting_for_input"] = True
    active_session["input_type"] = input_type
    active_session["human_input_event"].clear()
    active_session["human_input_value"] = None
    socketio.emit('human_input_needed', {
        'type': input_type,
        'context': context,
        'cycle': active_session["cycle"]
    })
    active_session["human_input_event"].wait(timeout=3600)
    active_session["waiting_for_input"] = False
    return active_session["human_input_value"] or ""

# -----------------------------------------
# FRICTION SCORING
# -----------------------------------------
def get_friction_signal():
    recent = active_session["transcript"][-6:] if len(active_session["transcript"]) > 6 else active_session["transcript"]
    snippet = "\n".join([f"[{e['role'].upper()}] {e['content'][:300]}" for e in recent])
    messages = [{"role": "user", "content": f"Score this session state:\n\n{snippet}"}]
    response = call_model("model_c", messages)
    if not response:
        return 0
    signal = extract_signal(response)
    reason_match = re.search(r'REASON:\s*(.+)', response)
    reason = reason_match.group(1).strip() if reason_match else "no reason given"
    active_session["signal_sequence"].append(
        f"Cycle {active_session['cycle']}: SIGNAL {signal} - {reason}"
    )
    socketio.emit('friction_signal', {
        'signal': signal,
        'reason': reason,
        'cycle': active_session["cycle"]
    })
    return signal

# -----------------------------------------
# PARIETAL — PRE_SESSION, NAVIGATE, ADJUDICATE, DISTILL
# -----------------------------------------
PARIETAL_SYSTEM = None

def get_parietal_system():
    global PARIETAL_SYSTEM
    if PARIETAL_SYSTEM is None:
        PARIETAL_SYSTEM = load_file("prompts/parietal_system.txt") or (
            "You are the Parietal — navigator, adjudicator, and distiller for an Ontinuity session. "
            "You have four callable functions activated by tags: PRE_SESSION, NAVIGATE, ADJUDICATE, DISTILL. "
            "Execute the function matching the tag in the user message. Be precise and structured."
        )
    return PARIETAL_SYSTEM

def call_parietal(function_tag, **kwargs):
    """Call a Parietal function by tag. Returns response string or None.
    Requires both api_key and url to be configured — url alone is not sufficient."""
    parietal_cfg = get_effective_config("parietal")
    has_parietal = bool(parietal_cfg.get("api_key") and parietal_cfg.get("url"))
    if not has_parietal:
        return None
    system = get_parietal_system()
    parts = [f"[PARIETAL: {function_tag}]"]
    for k, v in kwargs.items():
        if v:
            parts.append(f"{k.upper()}:\n{v}")
    content = "\n\n".join(parts)
    messages = [{"role": "user", "content": content}]
    socketio.emit('routing_action', {'type': 'parietal', 'message': f'Parietal {function_tag}...'})
    response = call_model("parietal", messages, system_override=system)
    return response

def run_pre_session(objective, orient_context=""):
    """Run PRE_SESSION — returns (refined_objective, needs_answers, contract)."""
    kwargs = {"objective": objective}
    if orient_context:
        kwargs["projenius_orient_context"] = orient_context
    # Pass project and branch context so Parietal knows which project this session belongs to
    if WORKSPACE_PROJECT:
        kwargs["project"] = WORKSPACE_PROJECT
    if WORKSPACE_BRANCH:
        kwargs["branch"] = WORKSPACE_BRANCH
    response = call_parietal("PRE_SESSION", **kwargs)
    if not response:
        return objective, False, []
    if "READY:" in response.upper():
        idx = response.upper().find("READY:")
        refined = response[idx + 6:].strip()
        # Strip SCOPE line if present — just take the objective line
        if "\n" in refined:
            refined = refined.split("\n")[0].strip()
        socketio.emit('parietal_pre_session', {'status': 'ready', 'questions': response, 'cycle': 0})
        return refined or objective, False, parse_contract(response)
    socketio.emit('parietal_pre_session', {'status': 'questions', 'questions': response, 'cycle': 0})
    return objective, True, []

def run_pre_session_with_answers(raw_objective, answers):
    """Run PRE_SESSION with operator answers — returns (refined_objective, contract)."""
    response = call_parietal("PRE_SESSION",
                             objective=raw_objective,
                             operator_answers=answers)
    if not response:
        return raw_objective, []
    if "READY:" in response.upper():
        idx = response.upper().find("READY:")
        refined = response[idx + 6:].strip()
        if "\n" in refined:
            refined = refined.split("\n")[0].strip()
        return refined or raw_objective, parse_contract(response)
    return raw_objective, []

def run_parietal_navigate(knowtext, signal_sequence_recent=None):
    """Run NAVIGATE — returns structured orientation string or None."""
    working = get_working_context(knowtext) if knowtext else ""
    ledger = get_session_ledger_summary()
    signal_info = ""
    if signal_sequence_recent:
        signal_info = "\n".join(signal_sequence_recent[-5:])
    kwargs = dict(
        knowtext_working_context=working,
        session_ledger=ledger,
        friction_signal_sequence=signal_info
    )
    if WORKSPACE_PROJECT:
        kwargs["project"] = WORKSPACE_PROJECT
    if WORKSPACE_BRANCH:
        kwargs["branch"] = WORKSPACE_BRANCH
    response = call_parietal("NAVIGATE", **kwargs)
    if response:
        socketio.emit('parietal_navigate', {'output': response, 'cycle': active_session["cycle"]})
    return response

def run_parietal_adjudicate(disputed_claim, grounds, knowtext):
    """Run ADJUDICATE — returns ruling string or None."""
    working = get_working_context(knowtext) if knowtext else ""
    ledger = get_session_ledger_summary()
    signal = active_session["signal_sequence"][-1] if active_session["signal_sequence"] else ""
    exec_log = "\n".join(
        f"cycle {e['cycle']}: {e['kind']} {e['status']}: {e['detail'][:100]}" + (f" -> {e['result'][:400]}" if e.get('result') else "")
        for e in active_session["execution_log"][-10:]
    ) or "No executions this session."
    response = call_parietal("ADJUDICATE",
                             disputed_claim=disputed_claim,
                             grounds=grounds,
                             session_ledger=ledger,
                             execution_log_ground_truth=exec_log,
                             knowtext_active_frameworks=working,
                             current_ambient_signal=signal)
    if response:
        ruling = "pursue_both"
        if "PURSUE BOTH" in response.upper(): ruling = "pursue_both"
        elif "UPHOLD" in response.upper(): ruling = "uphold"
        elif "REJECT" in response.upper(): ruling = "reject"
        elif "ESCALATE" in response.upper(): ruling = "escalate"
        socketio.emit('parietal_adjudicate', {
            'ruling': ruling,
            'output': response,
            'cycle': active_session["cycle"]
        })
    return response

def run_parietal_resolve(question, knowtext):
    """Run RESOLVE — autonomous domain resolution of hard forks. Uses Model A (Researcher) as domain resolver."""
    resolve_system = load_file("prompts/parietal_resolve.txt") or get_parietal_system()
    working = get_working_context(knowtext) if knowtext else ""
    ledger = get_session_ledger_summary()
    parts = [
        "[PARIETAL: RESOLVE]",
        f"QUESTION:\n{question}",
    ]
    if ledger:
        parts.append(f"SESSION LEDGER:\n{ledger}")
    if working:
        parts.append(f"KNOWTEXT WORKING CONTEXT:\n{working}")
    content = "\n\n".join(parts)
    messages = [{"role": "user", "content": content}]
    socketio.emit('routing_action', {'type': 'parietal', 'message': 'Parietal RESOLVE (Model A)...'})
    response = call_model("model_a", messages, system_override=resolve_system)
    if not response:
        return None
    if "ESCALATE_TO_HUMAN" in response:
        return None  # Fall through to human input
    return response


def run_parietal_distill(knowtext):
    """Run DISTILL — returns updated Knowtext string or None."""
    ledger = get_session_ledger_summary()
    navigate_outputs = "\n\n".join(active_session.get("parietal_navigate_outputs", []))
    adjudicate_rulings = "\n\n".join(active_session.get("parietal_adjudicate_rulings", []))
    signal_seq = "\n".join(active_session["signal_sequence"])
    kwargs = dict(
        session_ledger=ledger,
        navigate_outputs=navigate_outputs,
        adjudicate_rulings=adjudicate_rulings,
        friction_signal_sequence=signal_seq,
        current_knowtext=knowtext or ""
    )
    if WORKSPACE_PROJECT:
        kwargs["project"] = WORKSPACE_PROJECT
    if WORKSPACE_BRANCH:
        kwargs["branch"] = WORKSPACE_BRANCH
    response = call_parietal("DISTILL", **kwargs)
    return response


def validate_knowtext_response(response):
    for field in KNOWTEXT_REQUIRED_FIELDS:
        if field not in response:
            return False, field
    return True, None

def run_distillation():
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Running Projenius extraction into Knowtext...'})
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])
    extraction_prompt = load_file("prompts/knowtext_extraction_prompt.txt") or \
        "Extract session content into the Knowtext schema fields. Write only what changed. Preserve all numerical values, category names, thresholds, and defined terms verbatim."
    messages = [{"role": "user", "content": f"{extraction_prompt}\n\n---SESSION TRANSCRIPT---\n\n{transcript_text}"}]
    response = call_model("projenius", messages)
    if not response:
        socketio.emit('routing_action', {'type': 'error', 'message': 'Distillation failed - no response'})
        return False
    valid, missing_field = validate_knowtext_response(response)
    if not valid:
        socketio.emit('routing_action', {'type': 'error', 'message': f'Distillation failed - missing field: {missing_field}'})
        return False
    rotate_backups()
    new_knowtext = f"{SCHEMA_VERSION}\n\n{response}"
    save_file(CONFIG["knowtext_path"], new_knowtext)
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Knowtext updated successfully.'})
    # Push to GitHub for persistence across deployments
    github_push_knowtext()
    return True

# -----------------------------------------
# WORK PRODUCT EXTRACTION
# -----------------------------------------
def build_verified_results_block():
    """Assemble the Verified Results section of the work product BY CODE, from the
    contract and the execution log. The deliverable's spine is a receipt, not a
    retelling: each VERIFIABLE criterion is shown with its real recorded output.
    Returns "" when no contract exists (pre-contract sessions keep old behavior)."""
    contract = active_session.get("contract", [])
    if not contract:
        return ""
    lines = ["## Verified Results", ""]
    for c in contract:
        if c["kind"] == "VERIFIABLE":
            cmds = re.findall(r"`([^`]{2,120})`", c.get("evidence", ""))
            if cmds:
                entry = None
                for cmd in cmds:
                    passed = [e for e in _f3_find_entries(cmd) if e["status"].upper().startswith("PASSED")]
                    if passed:
                        entry = passed[-1]
                        break
                if entry:
                    out = entry.get("result", "").strip()
                    shown = out[:800] + ("..." if len(out) > 800 else "") if out else "(no output)"
                    lines.append(f"**{c['id']} — {c['text']}**: MET")
                    lines.append(f"Evidence: `{entry['detail']}` (cycle {entry['cycle']}, {entry['status']})")
                    lines.append(f"```\n{shown}\n```")
                else:
                    lines.append(f"**{c['id']} — {c['text']}**: UNMET — no successful execution recorded.")
            else:
                lines.append(f"**{c['id']} — {c['text']}**: satisfied by injected ground truth (see transcript).")
        else:
            lines.append(f"**{c['id']} — {c['text']}**: JUDGED criterion — assessed by the Challenger at close.")
        lines.append("")
    return "\n".join(lines)

def run_work_product_extraction():
    socketio.emit('routing_action', {'type': 'extraction', 'message': 'Extracting session work product...'})
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])
    verified_block = build_verified_results_block()
    board = active_session.get("results_board", [])
    board_text = ("\n\n---ESTABLISHED RESULTS (ground truth, authoritative over the transcript)---\n"
                  + "\n".join(board)) if board else ""
    if verified_block:
        extraction_prompt = (
            "You are writing the work product for a completed Ontinuity session. "
            "The VERIFIED RESULTS section below was assembled by code directly from the "
            "execution log — it is authoritative and must appear VERBATIM as the first "
            "section of the document, unchanged. After it, add only the supporting "
            "narrative, context, and any non-execution deliverables from the transcript. "
            "Never contradict, restate with different values, or hedge the verified section. "
            "Output a clean document. No process, discussion, or metadata."
        )
        head = f"{extraction_prompt}\n\n---VERIFIED RESULTS (reproduce verbatim)---\n{verified_block}{board_text}"
    else:
        extraction_prompt = (
            "You are reviewing a completed Ontinuity session. Extract the work product - "
            "everything that was established, built, decided, or completed in this session. "
            "Where the ESTABLISHED RESULTS section provides recorded values, use those exact "
            "values in the deliverable - they are real executions and take precedence over "
            "any retraction or hedging in the transcript. "
            "Output a clean document containing only the deliverables. Do not include process, "
            "discussion, or metadata. Format appropriate to the content."
        )
        head = f"{extraction_prompt}{board_text}"
    messages = [{"role": "user", "content": f"{head}\n\n---SESSION TRANSCRIPT---\n\n{transcript_text}"}]
    extractor = get_best_available_model()
    response = call_model(extractor, messages)
    if not response or len(response.strip()) < 20:
        messages = [{"role": "user", "content": f"Review the session transcript and output everything that was established or produced:\n\n{transcript_text}"}]
        response = call_model(extractor, messages)
    path = artifact_path("work_product")
    content = sanitize_content(response) if (response and len(response.strip()) >= 20) else "[EXTRACTION FAILED]"
    # F.3 audits the deliverable itself — the last unaudited artifact in the system.
    # Flagged claims are annotated loudly, never silently shipped.
    if content != "[EXTRACTION FAILED]":
        try:
            wp_bad = f3_bad(check_execution_claims(content))
            if wp_bad:
                content += "\n\n--- F.3 AUDIT ANNOTATION (automatic) ---\n" + f3_summary(wp_bad)
                socketio.emit('routing_action', {'type': 'error', 'message': f"WP audit: F.3 flagged {len(wp_bad)} claim(s) in the extracted work product — annotated in the document."})
        except Exception as e:
            print(f"[WP AUDIT] audit error: {e}", flush=True)
    save_file(path, content)
    active_session["artifacts"].append({"label": "Work Product", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Work Product', 'content': content})

# -----------------------------------------
# FINAL SYNTHESIS
# -----------------------------------------
def run_final_synthesis():
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Generating final synthesis...'})
    knowtext = load_file(CONFIG["knowtext_path"]) or ""
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])
    synthesis_prompt = (
        "You are generating a final project synthesis. Review the accumulated Knowtext context "
        "and the current session transcript. Produce a single coherent document containing: "
        "all established results, all open questions with their current state, the correction "
        "history across the full project, and a summary of what was built. This is the final "
        "deliverable for the project. Format as a clean readable document."
    )
    messages = [{"role": "user", "content": f"{synthesis_prompt}\n\n---KNOWTEXT---\n{knowtext}\n\n---SESSION TRANSCRIPT---\n{transcript_text}"}]
    synthesizer = get_best_available_model()
    response = call_model(synthesizer, messages)
    content = sanitize_content(response) if response else "[FINAL SYNTHESIS FAILED]"
    path = artifact_path("final_synthesis")
    save_file(path, content)
    active_session["artifacts"].append({"label": "Final Synthesis", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Final Synthesis', 'content': content})
    if response:
        github_push_knowtext()
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Final synthesis complete. Project closed.'})

# -----------------------------------------
# SESSION LOG
# -----------------------------------------
def write_session_log():
    active_session["end_time"] = timestamp()
    def get_runtime_model(role):
        cfg = get_effective_config(role)
        return cfg.get("model", CONFIG[role]["model"])
    log_lines = [
        "ONTINUITY SESSION LOG",
        f"Session start: {active_session['start_time']}",
        f"Session end: {active_session['end_time']}",
        f"Knowtext version: {active_session['knowtext_version'] or 'none'}",
        f"Model A: {get_runtime_model('model_a')}",
        f"Model B: {get_runtime_model('model_b')}",
        f"Model C: {get_runtime_model('model_c')}",
        f"Projenius: {get_runtime_model('projenius')}",
        f"Total cycles: {active_session['cycle']}",
        "", "STATUS TAG SEQUENCE:"
    ] + active_session["tag_sequence"] + [
        "", "FRICTION SIGNAL SEQUENCE:"
    ] + active_session["signal_sequence"] + [
        "", "CHALLENGE EVENTS:"
    ] + (active_session["challenge_events"] or ["none"]) + [
        "", "SESSION LEDGER:"
    ] + ([f"Cycle {e['cycle']}: {e['summary']}" for e in active_session["session_ledger"]] or ["none"]) + [
        "", "ERRORS:"
    ] + (active_session["errors"] or ["none"])
    content = "\n".join(log_lines)
    path = artifact_path("session_log")
    save_file(path, content)
    active_session["artifacts"].append({"label": "Session Log", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Session Log', 'content': content})

# -----------------------------------------
# MAIN SESSION LOOP
# -----------------------------------------
def run_session_loop(objective, start_fresh=False, contract=None):
    active_session["running"] = True
    active_session["start_time"] = timestamp()
    active_session["transcript"] = []
    active_session["tag_sequence"] = []
    active_session["signal_sequence"] = []
    active_session["challenge_events"] = []
    active_session["errors"] = []
    active_session["cycle"] = 0
    active_session["artifacts"] = []
    active_session["session_ledger"] = []
    active_session["rejected_claims"] = []
    active_session["results_board"] = []   # F.9: every PASSED result + value, banked at injection time
    active_session["contract"] = contract or []  # frozen criteria from PRE_SESSION; empty = no contract
    if active_session["contract"]:
        contract_display = "\n".join(
            f"{c['id']} [{c['kind']}] {c['text']}" + (f" — evidence: {c['evidence']}" if c['evidence'] else "")
            for c in active_session["contract"])
        socketio.emit('routing_action', {'type': 'parietal',
            'message': f"Session contract frozen ({len(active_session['contract'])} criteria):\n{contract_display}"})
    active_session["no_progress_count"] = 0
    active_session["malformed_count"] = 0
    active_session["execution_log"] = []       # F.2: fresh deterministic execution record per session
    active_session["claim_warning_count"] = 0  # F.2: fresh claim-without-execution counter

    # Load and filter Knowtext for injection
    if start_fresh:
        knowtext = ""
        socketio.emit('routing_action', {'type': 'injection', 'message': 'Starting fresh — Knowtext context cleared for this session. GitHub copy preserved.'})
    else:
        socketio.emit('routing_action', {'type': 'injection', 'message': 'Loading Knowtext...'})
        if not os.path.exists(CONFIG["knowtext_path"]) or os.path.getsize(CONFIG["knowtext_path"]) == 0:
            socketio.emit('routing_action', {'type': 'injection', 'message': 'Local Knowtext not found — pulling from GitHub...'})
            github_pull_knowtext()
        knowtext = load_file(CONFIG["knowtext_path"]) or ""
        if knowtext:
            first_line = knowtext.split("\n")[0].strip()
            active_session["knowtext_version"] = first_line
            socketio.emit('routing_action', {'type': 'injection', 'message': 'Knowtext injected into Researcher context.'})
        else:
            socketio.emit('routing_action', {'type': 'injection', 'message': 'No Knowtext found - starting fresh.'})

    # Model A system: base prompt + full Working Context section
    model_a_base = load_file(CONFIG["model_a"]["system_prompt_path"]) or "You are the Researcher in a Triform session."
    working_context = get_working_context(knowtext)
    model_a_system = model_a_base
    if working_context:
        model_a_system = f"{model_a_base}\n\n--- WORKING CONTEXT ---\n{working_context}"

    # Model B base context: Active Frameworks + Correction History only
    knowtext_for_b = get_model_b_context(knowtext)
    model_b_base = load_file(CONFIG["model_b"]["system_prompt_path"]) or "You are the Challenger in a Triform session."

    conversation = [{"role": "user", "content": f"Session objective: {objective}\n\nBegin."}]
    socketio.emit('session_started', {'objective': objective})

    while active_session["running"]:
        active_session["cycle"] += 1
        researcher_requested_end = False  # F.1: set True when Researcher proposes SESSION_END at/above floor
        # Context trimming — keep conversation window manageable
        if len(conversation) > 10:
            conversation = conversation[:1] + conversation[-8:]
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} - Researcher generating...'})

        # Rebuild model_a_system each cycle to inject current rejected claims
        # This survives conversation trimming — the Researcher always sees what has been ruled out
        rejected_injection = get_rejected_claims_injection()
        cycle_model_a_system = model_a_system + get_datetime_injection()  # F.4: real clock every cycle
        contract_injection = get_contract_injection()  # frozen criteria, every cycle
        if contract_injection:
            cycle_model_a_system += contract_injection
        board_injection = get_results_board_injection()  # F.9: banked results, full values, every cycle
        if board_injection:
            cycle_model_a_system += board_injection
        if rejected_injection:
            cycle_model_a_system += rejected_injection

        # Model A
        a_response = call_model("model_a", conversation, system_override=cycle_model_a_system)
        if not a_response:
            socketio.emit('routing_action', {'type': 'error', 'message': 'Researcher returned no response. Stopping.'})
            break
        active_session["transcript"].append({"role": "model_a", "content": a_response})
        conversation.append({"role": "assistant", "content": a_response})
        socketio.emit('model_response', {'role': 'model_a', 'label': 'Researcher', 'content': a_response, 'cycle': active_session["cycle"]})

        # Update session ledger from Model A response
        extract_ledger_entry(a_response, active_session["cycle"])

        # Friction signal
        signal = get_friction_signal()
        ambient_line = get_ambient_signal_line(signal)

        # Tag
        tag = extract_tag(a_response)
        active_session["tag_sequence"].append(f"Cycle {active_session['cycle']} A: {tag}")
        socketio.emit('tag_detected', {'role': 'model_a', 'tag': tag, 'cycle': active_session["cycle"]})

        # F.1: Malformed-tag handling. A missing or unparseable status tag is not a free CONTINUE.
        # Re-prompt for a valid tag; two consecutive malformed cycles escalate so an omitted-tag
        # loop cannot trap the session silently.
        if not has_valid_tag(a_response):
            active_session["malformed_count"] += 1
            if active_session["malformed_count"] >= 2:
                socketio.emit('routing_action', {'type': 'error', 'message': 'Researcher produced two consecutive responses with no valid status tag — escalating.'})
                nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
                escalate_ctx = nav if nav else "Researcher is not emitting valid status tags; the loop cannot determine its intent."
                direction = wait_for_human_input("malformed", escalate_ctx)
                active_session["malformed_count"] = 0
                conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
                continue
            socketio.emit('routing_action', {'type': 'error', 'message': 'Researcher response carried no valid status tag — requesting reissue.'})
            conversation.append({"role": "user", "content": f"Your last response carried no valid status tag. Reissue your response ending with exactly one [CYCLE_STATUS: ...] tag.\n{ambient_line}"})
            continue
        else:
            active_session["malformed_count"] = 0

        # F.3: Deterministic fabrication detection (replaces the F.2 tripwire).
        # Every execution claim is parsed and checked against the execution log.
        # A response that ALSO emits SEARCH_REQUEST/CODE_TEST is allowed through —
        # the action branch will execute and inject real results next.
        cycle_f3 = []
        if tag not in ("SEARCH_REQUEST", "CODE_TEST"):
            cycle_f3 = check_execution_claims(a_response)
        bad_f3 = f3_bad(cycle_f3)
        if bad_f3:
            active_session["claim_warning_count"] += 1
            first = bad_f3[0]
            socketio.emit('routing_action', {'type': 'error', 'message': f"F.3 {first['verdict']}: {first['reason']}"})
            active_session["challenge_events"].append(
                f"Cycle {active_session['cycle']}: F.3 {first['verdict']} — {first['claim'][:140]}"
            )
            if active_session["claim_warning_count"] >= 2:
                socketio.emit('routing_action', {'type': 'error', 'message': 'F.3 fired twice consecutively — escalating for fabrication review.'})
                nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
                escalate_ctx = nav if nav else f"Cycle {active_session['cycle']}: F.3 detector verdicts:\n{f3_summary(bad_f3)}"
                direction = wait_for_human_input("result_absent", escalate_ctx)
                active_session["claim_warning_count"] = 0
                conversation.append({"role": "user", "content": f"[OPERATOR — RESULT VERIFICATION]: {direction}\n{ambient_line}"})
                continue
            conversation.append({"role": "user", "content": f"[F.3 EXECUTION AUDIT — DETERMINISTIC]: The following claims were checked against the session's execution log:\n{f3_summary(bad_f3)}\n\nNothing runs unless you emit a tag. To actually execute, reissue with a CODE_TEST or SEARCH_REQUEST tag and the required COMMAND/QUERY line; otherwise restate your reasoning without claiming results.\n{ambient_line}"})
            continue
        else:
            active_session["claim_warning_count"] = 0

        # Signal 4 override — DEFERRED when the response carries an action tag.
        # A false-positive Signal 4 that blocks a CODE_TEST/SEARCH_REQUEST starves
        # the session of the ground truth that would resolve the drift (the June 4
        # doom loop: correct `python --version` emitted twice, preempted twice).
        if signal == 4 and tag in ("CODE_TEST", "SEARCH_REQUEST"):
            socketio.emit('routing_action', {'type': 'error', 'message': 'Signal 4 raised but response carries an action tag — executing first; override deferred one cycle.'})
        elif signal == 4:
            socketio.emit('routing_action', {'type': 'error', 'message': 'Signal 4 — critical drift. Running NAVIGATE for context...'})
            nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
            if nav:
                active_session["parietal_navigate_outputs"].append(nav)
                signal4_context = nav
            else:
                ledger = get_session_ledger_summary()
                signal4_context = f"Signal 4 — critical drift at cycle {active_session['cycle']}.\n\n{ledger}"
            direction = wait_for_human_input("signal4", signal4_context)
            conversation.append({"role": "user", "content": f"[OPERATOR ALIGNMENT]: {direction}\n{ambient_line}"})
            continue

        if tag == "SESSION_END":
            # F.1: The Researcher cannot end the session unilaterally.
            # Floor: never honor SESSION_END before cycle 2, so at least one Challenger review always occurs.
            if active_session["cycle"] < 2:
                socketio.emit('routing_action', {'type': 'session_end', 'message': 'SESSION_END requested at cycle 1 — below minimum; one adversarial review required before any close. Continuing.'})
                conversation.append({"role": "user", "content": f"A session cannot close before at least one full adversarial review has occurred. Continue the work toward the objective.\n{ambient_line}"})
                continue
            # At or above the floor: do not break here. Fall through to the Challenger review,
            # then let the post-review decision rule decide whether the session actually ends.
            researcher_requested_end = True
            socketio.emit('routing_action', {'type': 'session_end', 'message': 'Researcher proposed SESSION_END — routing to Challenger for completion assessment.'})
        elif tag == "SEARCH_REQUEST":
            # Model A is requesting a web search — route through workspace + Projenius SEARCH
            search_query, search_context = extract_search_request(a_response)
            if search_query:
                socketio.emit('routing_action', {'type': 'parietal', 'message': f'Search request: {search_query[:80]}...'})
                raw_results = call_workspace_search(search_query, search_context)
                record_execution("search", search_query, "results" if raw_results else "unavailable")  # F.2: ground-truth log
                if raw_results:
                    projenius_answer = run_projenius_search(search_query, search_context, raw_results)
                    if projenius_answer:
                        conversation.append({"role": "user", "content": f"[SEARCH RESULT]:\n{projenius_answer}\n\n{ambient_line}"})
                    else:
                        # Projenius unavailable — inject raw results directly
                        raw_text = "\n".join([f"[{i+1}] {r.get('title','')} — {r.get('url','')}\n{r.get('description','')}" for i, r in enumerate(raw_results[:5])])
                        conversation.append({"role": "user", "content": f"[SEARCH RESULTS — RAW]:\n{raw_text}\n\n{ambient_line}"})
                else:
                    conversation.append({"role": "user", "content": f"[SEARCH RESULT]: Search unavailable — workspace not reachable or no results returned for: {search_query}\n\n{ambient_line}"})
            else:
                conversation.append({"role": "user", "content": f"[SEARCH RESULT]: Search request received but no QUERY line found above the tag.\n\n{ambient_line}"})
            continue
        elif tag == "CODE_TEST":
            # Model A is requesting a code test — route to workspace /run endpoint
            command = extract_code_test(a_response)
            if command:
                socketio.emit('routing_action', {'type': 'parietal', 'message': f'Code test: {command[:80]}'})
                result = call_workspace_run(command)
                if result:
                    returncode = result.get("returncode", -1)
                    stdout = result.get("stdout", "").strip()
                    stderr = result.get("stderr", "").strip()
                    status = "PASSED" if returncode == 0 else f"FAILED (exit {returncode})"
                    output_parts = [f"[CODE_TEST RESULT]: {status}", f"COMMAND: {command}"]
                    if stdout:
                        output_parts.append(f"STDOUT:\n{stdout[:2000]}")
                    if stderr:
                        output_parts.append(f"STDERR:\n{stderr[:1000]}")
                    conversation.append({"role": "user", "content": "\n".join(output_parts) + f"\n\n{ambient_line}"})
                    ledger_summary_line = f"CODE_TEST {status}: {command}"
                    if returncode == 0 and stdout:
                        ledger_summary_line += f" -> {stdout[:500]}"
                    active_session["session_ledger"].append({
                        "cycle": active_session["cycle"],
                        "summary": ledger_summary_line
                    })
                    record_execution("code_test", command, status, result=stdout[:2000])  # F.3: ground truth incl. output
                    if returncode == 0:
                        active_session["results_board"].append(
                            f"`{command}` -> {(stdout[:500] + ('...' if len(stdout) > 500 else '')) if stdout else '(no output)'}"
                        )
                else:
                    conversation.append({"role": "user", "content": f"[CODE_TEST RESULT]: Workspace not reachable — cannot execute: {command}\n\n{ambient_line}"})
            else:
                conversation.append({"role": "user", "content": f"[CODE_TEST RESULT]: CODE_TEST tag received but no COMMAND line found above the tag.\n\n{ambient_line}"})
            continue
        elif tag == "ALIGNMENT_NEEDED":
            nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
            if nav:
                active_session["parietal_navigate_outputs"].append(nav)
                # Try RESOLVE before escalating to human
                resolve = run_parietal_resolve(nav, knowtext)
                if resolve:
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: RESOLVED — {resolve[:200]}"
                    )
                    # Extract any DIRECT CORRECTION claims for Researcher memory
                    if "DIRECT CORRECTION" in resolve.upper() or "CANNOT" in resolve.upper():
                        extract_rejected_claim(resolve, active_session["cycle"])
                    socketio.emit('parietal_adjudicate', {
                        'ruling': 'resolve',
                        'output': resolve,
                        'cycle': active_session["cycle"]
                    })
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("alignment", nav)
                    conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
            else:
                # No NAVIGATE output — try RESOLVE directly on raw response
                resolve = run_parietal_resolve(a_response, knowtext)
                if resolve:
                    if "DIRECT CORRECTION" in resolve.upper() or "CANNOT" in resolve.upper():
                        extract_rejected_claim(resolve, active_session["cycle"])
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("alignment", a_response)
                    conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
            continue
        elif tag == "CHECKPOINT":
            # CHECKPOINT is an operator review point — it must always reach the human.
            # Unlike ALIGNMENT_NEEDED (a stuck fork, where Parietal RESOLVE-first is correct),
            # a checkpoint means "operator, review before continuing." NAVIGATE is run only to
            # provide the operator orienting context; the session always blocks for human input.
            nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
            ledger = get_session_ledger_summary()
            if nav:
                active_session["parietal_navigate_outputs"].append(nav)
                checkpoint_context = nav
            elif ledger:
                checkpoint_context = f"Cycle {active_session['cycle']} checkpoint.\n\n{ledger}"
            else:
                checkpoint_context = f"Cycle {active_session['cycle']} checkpoint."
            direction = wait_for_human_input("checkpoint", checkpoint_context)
            conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})
            continue

        # Brief pause to spread GROQ rate limit load
        time.sleep(2)

        # Model B - two-layer context: filtered Knowtext + session ledger
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} - Challenger reviewing...'})
        ledger_summary = get_session_ledger_summary()
        b_context_parts = []
        # The judge reads the contract: the Challenger assesses completion against the
        # objective, so the objective must be in its context — not inferred from the
        # ledger. (June 5: an honest Challenger refused to assess completion of an
        # objective it had never been shown. It was right.)
        b_context_parts.append(f"[SESSION OBJECTIVE]\n{objective}")
        contract_injection_b = get_contract_injection()
        if contract_injection_b:
            b_context_parts.append(contract_injection_b)
        if knowtext_for_b:
            b_context_parts.append(f"[PROJECT CONTEXT]\n{knowtext_for_b}")
        if ledger_summary:
            b_context_parts.append(f"[{ledger_summary}]")
        board_injection_b = get_results_board_injection()  # F.9: judges see the same ground truth as the claimant
        if board_injection_b:
            b_context_parts.append(board_injection_b)
        if cycle_f3:
            b_context_parts.append(f"[F.3 EXECUTION AUDIT — deterministic check of claims against the execution log]\n{f3_summary(cycle_f3)}")
        elif active_session["execution_log"]:
            full = active_session["execution_log"]
            b_context_parts.append("[EXECUTION LOG — ground truth, FULL session]\n" + "\n".join(
                f"cycle {e['cycle']}: {e['kind']} {e['status']}: {e['detail'][:80]}" + (f" -> {e['result'][:300]}" if e.get('result') else "")
                for e in full[-25:]))
        b_context_parts.append(f"[CURRENT OUTPUT TO REVIEW]\n{a_response}\n\n{ambient_line}")
        b_content = "\n\n".join(b_context_parts)
        b_system = model_b_base
        b_messages = [{"role": "user", "content": b_content}]
        b_response = call_model("model_b", b_messages, system_override=b_system)

        if b_response:
            active_session["transcript"].append({"role": "model_b", "content": b_response})
            socketio.emit('model_response', {'role': 'model_b', 'label': 'Challenger', 'content': b_response, 'cycle': active_session["cycle"]})
            b_tag = extract_tag(b_response)
            active_session["tag_sequence"].append(f"Cycle {active_session['cycle']} B: {b_tag}")
            socketio.emit('tag_detected', {'role': 'model_b', 'tag': b_tag, 'cycle': active_session["cycle"]})

            # F.1: Parse the Challenger's structured session-state assessment every cycle.
            assessment = extract_challenger_assessment(b_response)
            active_session["signal_sequence"].append(
                f"Cycle {active_session['cycle']} ASSESS: deliverable={assessment['deliverable']} progress={assessment['progress']} result_check={assessment['result_check']}"
            )
            socketio.emit('routing_action', {'type': 'parietal', 'message': f"Challenger assessment — deliverable: {assessment['deliverable']}, progress: {assessment['progress']}, result_check: {assessment['result_check']}"})
            # Update the no-progress counter: increment on no progress, reset on progress.
            if assessment["progress"] == "no":
                active_session["no_progress_count"] += 1
            else:
                active_session["no_progress_count"] = 0

            if b_tag == "CHALLENGE":
                # F.3-FIRST DISPUTE ROUTING: a dispute about an execution result is
                # answered by the execution log, not by a model. If every execution
                # claim in the challenged response is CORROBORATED by the log, the
                # challenge is resolved deterministically with the stored ground
                # truth — no ADJUDICATE, no testimony. Model adjudication remains
                # for disputes the log cannot decide (reasoning, scope, quality).
                a_verdicts = check_execution_claims(a_response)
                if a_verdicts and not f3_bad(a_verdicts):
                    cited = []
                    for v in a_verdicts[:4]:
                        cited.append(f"CORROBORATED: \"{v['claim'][:160]}\" — {v['reason'][:200]}")
                    log_lines_full = []
                    for e in active_session["execution_log"][-6:]:
                        log_lines_full.append(f"cycle {e['cycle']}: {e['kind']} {e['status']}: {e['detail'][:100]}" + (f"\n  OUTPUT: {e['result'][:800]}" if e.get('result') else ""))
                    resolution = ("[F.3 GROUND TRUTH RESOLUTION — deterministic]: The challenged claims were "
                                  "checked against the session execution log and are corroborated by real "
                                  "recorded output. The challenge is answered by ground truth:\n"
                                  + "\n".join(cited)
                                  + "\n\nFULL RECORDED OUTPUT (authoritative):\n" + "\n".join(log_lines_full))
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: F.3 RESOLVED — challenge against corroborated claims answered by execution log"
                    )
                    socketio.emit('routing_action', {'type': 'parietal', 'message': 'Challenge resolved by execution log — claims corroborated; ADJUDICATE skipped.'})
                    conversation.append({"role": "user", "content": f"{resolution}\n{ambient_line}"})
                    continue
                # Try Parietal ADJUDICATE (log cannot decide this dispute)
                ruling = run_parietal_adjudicate(b_response, "", knowtext)
                if ruling:
                    active_session["parietal_adjudicate_rulings"].append(
                        f"Cycle {active_session['cycle']}: {ruling[:300]}"
                    )
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: {ruling[:200]}"
                    )
                    # If ruling is UPHOLD, extract the rejected claim for Researcher memory
                    if "UPHOLD" in ruling.upper():
                        extract_rejected_claim(ruling, active_session["cycle"])
                        socketio.emit('routing_action', {
                            'type': 'parietal',
                            'message': 'Claim ruled against — added to Researcher session memory.'
                        })
                    if "ESCALATE" in ruling.upper():
                        # Parietal says escalate — get human input
                        nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
                        escalate_ctx = nav if nav else ruling
                        adjudication = wait_for_human_input("challenge", escalate_ctx)
                        active_session["challenge_events"].append(
                            f"Cycle {active_session['cycle']}: ESCALATED — {adjudication}"
                        )
                        conversation.append({"role": "user", "content": f"[CHALLENGE ESCALATED]: {adjudication}\n{ambient_line}"})
                    else:
                        conversation.append({"role": "user", "content": f"[PARIETAL RULING]: {ruling}\n{ambient_line}"})
                else:
                    # Parietal not configured — fall back to human
                    adjudication = wait_for_human_input("challenge", b_response)
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: {adjudication}"
                    )
                    conversation.append({"role": "user", "content": f"[CHALLENGE ADJUDICATED]: {adjudication}\n{ambient_line}"})
                continue
            elif b_tag == "VERIFY_CITATION":
                # Model B suspects a fabricated citation — route to Projenius SEARCH for verification
                citation, claim, query = extract_verify_citation(b_response)
                if query:
                    socketio.emit('routing_action', {'type': 'parietal', 'message': f'Citation verification: {query[:80]}...'})
                    raw_results = call_workspace_search(query, citation)
                    record_execution("citation", query, "results" if raw_results else "unavailable")  # F.2: ground-truth log
                    if raw_results:
                        projenius_answer = run_projenius_search(query, citation, raw_results)
                        if projenius_answer:
                            active_session["challenge_events"].append(
                                f"Cycle {active_session['cycle']}: VERIFY_CITATION — {projenius_answer[:200]}"
                            )
                            conversation.append({"role": "user", "content": f"[CITATION VERIFICATION]:\n{projenius_answer}\n\n{ambient_line}"})
                        else:
                            conversation.append({"role": "user", "content": f"[CITATION VERIFICATION]: Projenius unavailable — raw search returned {len(raw_results)} results for: {query}\n\n{ambient_line}"})
                    else:
                        conversation.append({"role": "user", "content": f"[CITATION VERIFICATION]: Verification unavailable — workspace search not reachable. Citation unverified: {citation}\n\n{ambient_line}"})
                else:
                    conversation.append({"role": "user", "content": f"[CITATION VERIFICATION]: VERIFY_CITATION received but no QUERY line found above the tag.\n\n{ambient_line}"})
                continue
            elif b_tag == "SESSION_END":
                # F.1: The Challenger's SESSION_END is a strong end signal but not a unilateral break.
                # It feeds the same decision rule below. Record it as a request to end.
                researcher_requested_end = True
                socketio.emit('routing_action', {'type': 'session_end', 'message': 'Challenger proposed SESSION_END — applying completion decision rule.'})

        # F.1: Termination decision rule. Reached only when the Challenger did not raise an
        # active CHALLENGE or VERIFY_CITATION this cycle (those branches continue above).
        # The code decides end / continue / escalate from the parsed assessment, the
        # Researcher/Challenger end requests, and the no-progress counter. No single model ends the session.
        if b_response:
            # Track 2 — result claimed but absent: the fabrication signature. Surface to the operator now.
            # F.3 will later replace this human gate with the deterministic execution-log detector.
            if assessment["result_check"] == "absent":
                socketio.emit('routing_action', {'type': 'error', 'message': 'Challenger reports a claimed result with no matching execution — escalating for fabrication review.'})
                nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
                escalate_ctx = nav if nav else f"Cycle {active_session['cycle']}: Model A claimed a tool-call result with no injected result block present. Possible fabrication."
                direction = wait_for_human_input("result_absent", escalate_ctx)
                conversation.append({"role": "user", "content": f"[OPERATOR — RESULT VERIFICATION]: {direction}\n{ambient_line}"})
                continue

            # End decision — only at or above the floor, when an end was requested this cycle.
            if researcher_requested_end and active_session["cycle"] >= 2:
                # F.3 close gate: every execution claim in the closing response and the
                # session ledger is checked against the execution log as a structured
                # lookup. FABRICATED or MISREPORTED claims block the close. Honest
                # negative statements ("could not be verified", "UNMEASURED") contain
                # no checkable claim and pass by construction. Deterministic — checks
                # the log, not any model's judgment.
                ledger_texts = [e.get("summary", "") for e in active_session["session_ledger"]]
                close_verdicts = []
                for t in [a_response] + ledger_texts:
                    close_verdicts.extend(check_execution_claims(t))
                close_bad = f3_bad(close_verdicts)
                if close_bad:
                    socketio.emit('routing_action', {'type': 'error', 'message': f"CLOSE REFUSED — F.3: {close_bad[0]['verdict']} claim in the deliverable. {close_bad[0]['reason']}"})
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: CLOSE REFUSED — F.3 {close_bad[0]['verdict']}: {close_bad[0]['claim'][:140]}"
                    )
                    conversation.append({"role": "user", "content": f"The session cannot close. F.3 deterministic audit of the deliverable against the execution log:\n{f3_summary(close_bad)}\n\nEither obtain the real result (emit CODE_TEST or SEARCH_REQUEST with the required COMMAND/QUERY line) or restate the deliverable without the unsupported claims, then request SESSION_END again.\n{ambient_line}"})
                    continue
                unmet = contract_close_check()
                if unmet:
                    u = unmet[0]
                    socketio.emit('routing_action', {'type': 'error', 'message': f"CLOSE REFUSED — contract criterion {u['id']} unmet: {u['reason']}"})
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: CLOSE REFUSED — contract {u['id']} unmet"
                    )
                    unmet_lines = "\n".join(f"{x['id']}: {x['text']} — {x['reason']}" for x in unmet)
                    conversation.append({"role": "user", "content": f"The session cannot close. The session contract has unmet VERIFIABLE criteria:\n{unmet_lines}\n\nObtain the required real execution(s) via CODE_TEST, then request SESSION_END again.\n{ambient_line}"})
                    continue
                if assessment["deliverable"] == "complete":
                    socketio.emit('routing_action', {'type': 'session_end', 'message': 'Deliverable assessed complete, contract satisfied, end requested — closing session.'})
                    break
                else:
                    # End requested but Challenger judges the deliverable incomplete — override, continue.
                    socketio.emit('routing_action', {'type': 'session_end', 'message': 'End requested but Challenger assesses deliverable incomplete — continuing.'})
                    conversation.append({"role": "user", "content": f"The session cannot close yet: review indicates the deliverable is not complete. Continue the work.\n\n[CHALLENGER REVIEW]: {b_response}\n{ambient_line}"})
                    continue

            # Track 1 — no-progress ceiling: N consecutive cycles with no progress.
            # Try Parietal NAVIGATE -> RESOLVE first; fall through to the operator only if RESOLVE declines.
            if active_session["no_progress_count"] >= 3:
                socketio.emit('routing_action', {'type': 'error', 'message': f'No progress for {active_session["no_progress_count"]} consecutive cycles — attempting Parietal resolution.'})
                nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
                if nav:
                    active_session["parietal_navigate_outputs"].append(nav)
                resolve = run_parietal_resolve(nav if nav else f"Session has made no progress for {active_session['no_progress_count']} cycles.", knowtext)
                if resolve:
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: NO-PROGRESS RESOLVED — {resolve[:200]}"
                    )
                    active_session["no_progress_count"] = 0  # successful resolve resets the runway
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("no_progress", nav if nav else f"Session has made no progress for {active_session['no_progress_count']} cycles and Parietal could not resolve it.")
                    active_session["no_progress_count"] = 0
                    conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
                continue

        # Continue
        next_input = ambient_line
        if b_response:
            next_input += f"\n\n[CHALLENGER REVIEW]: {b_response}"
        conversation.append({"role": "user", "content": next_input})

        # Auto checkpoint
        if active_session["cycle"] % CONFIG["checkpoint_interval"] == 0:
            nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
            if nav:
                active_session["parietal_navigate_outputs"].append(nav)
                resolve = run_parietal_resolve(nav, knowtext)
                if resolve:
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: AUTO-CHECKPOINT RESOLVED — {resolve[:200]}"
                    )
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("checkpoint", nav)
                    conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})
            else:
                ledger = get_session_ledger_summary()
                auto_ctx = f"Auto-checkpoint at cycle {active_session['cycle']}.\n\n{ledger}" if ledger else f"Auto-checkpoint at cycle {active_session['cycle']}."
                direction = wait_for_human_input("checkpoint", auto_ctx)
                conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})

    # End sequence
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Waiting 5s before distillation...'})
    time.sleep(5)

    def run_distillation_with_timeout(fn, timeout=90):
        """Run a distillation function with a hard timeout. Returns result or None on timeout."""
        result = [None]
        def target():
            result[0] = fn()
        t = threading.Thread(target=target)
        t.daemon = True
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            socketio.emit('routing_action', {'type': 'error', 'message': f'Distillation timed out after {timeout}s — skipping.'})
            return None
        return result[0]

    # Try Parietal DISTILL first — entire distillation phase guarded so a
    # failure here can never skip the session log or the workspace write.
    try:
        parietal_distilled = run_distillation_with_timeout(lambda: run_parietal_distill(knowtext))
        distilled = False
        if parietal_distilled:
            valid, missing = validate_knowtext_response(parietal_distilled)
            if valid:
                rotate_backups()
                new_knowtext = f"{SCHEMA_VERSION}\n\n{parietal_distilled}"
                save_file(CONFIG["knowtext_path"], new_knowtext)
                socketio.emit('routing_action', {'type': 'distillation', 'message': 'Knowtext updated by Parietal.'})
                github_push_knowtext()
                active_session["distillation_method"] = "parietal"
                distilled = True
            else:
                socketio.emit('routing_action', {'type': 'distillation', 'message': f'Parietal distillation missing field: {missing} — falling back to Projenius.'})
                distilled = run_distillation_with_timeout(run_distillation) or False
                if distilled:
                    active_session["distillation_method"] = "projenius"
        else:
            socketio.emit('routing_action', {'type': 'distillation', 'message': 'Parietal distillation failed — trying Projenius...'})
            distilled = run_distillation_with_timeout(run_distillation) or False
            if distilled:
                active_session["distillation_method"] = "projenius"
        if not distilled:
            socketio.emit('routing_action', {'type': 'distillation', 'message': 'Distillation skipped — session complete without Knowtext update.'})
            active_session["distillation_method"] = "failed"
        else:
            # Run Projenius SYNTHESIZE to update Established Results Ledger
            delta_log = ""
            if parietal_distilled:
                # Collect Delta Log content — may span multiple lines until next field header.
                # Field headers are members of KNOWTEXT_REQUIRED_FIELDS, or "HANDOFF".
                other_field_headers = [f"{f}:" for f in KNOWTEXT_REQUIRED_FIELDS if f != "Delta Log"] + ["HANDOFF:"]
                distill_lines = parietal_distilled.split("\n")
                in_delta = False
                collected = []
                for line in distill_lines:
                    stripped = line.strip()
                    if stripped.startswith("Delta Log:"):
                        in_delta = True
                        # Capture any inline content after the colon on the same line
                        inline = stripped[len("Delta Log:"):].strip()
                        if inline:
                            collected.append(inline)
                        continue
                    if in_delta:
                        if any(stripped.startswith(h) for h in other_field_headers):
                            break
                        collected.append(line.rstrip())
                delta_log = "\n".join(collected).strip()
                if not delta_log:
                    # Fallback: use session ledger summary
                    delta_log = get_session_ledger_summary()
            if delta_log:
                socketio.emit('routing_action', {'type': 'parietal', 'message': 'Projenius SYNTHESIZE — updating Established Results Ledger...'})
                try:
                    synthesize_result = [None]
                    def do_synthesize():
                        synthesize_result[0] = run_projenius_synthesize(delta_log, knowtext)
                    synth_thread = threading.Thread(target=do_synthesize)
                    synth_thread.daemon = True
                    synth_thread.start()
                    synth_thread.join(timeout=30)
                    if synth_thread.is_alive():
                        socketio.emit('routing_action', {'type': 'parietal', 'message': 'Projenius SYNTHESIZE timed out — ledger not updated this session.'})
                    elif synthesize_result[0]:
                        socketio.emit('routing_action', {'type': 'parietal', 'message': 'Established Results Ledger updated.'})
                    else:
                        socketio.emit('routing_action', {'type': 'parietal', 'message': 'Projenius SYNTHESIZE returned no result — ledger not updated.'})
                except Exception as e:
                    socketio.emit('routing_action', {'type': 'error', 'message': f'Projenius SYNTHESIZE error: {str(e)}'})
    except Exception as e:
        print(f"[END SEQUENCE] distillation phase error: {e}", flush=True)
        active_session["errors"].append(f"Distillation phase error: {e}")
        socketio.emit('routing_action', {'type': 'error', 'message': f'Distillation phase error — proceeding to log and write: {str(e)}'})
    finally:
        for _step_name, _step_fn in (
                ("Work product extraction", run_work_product_extraction),
                ("Session log", write_session_log),
                ("Workspace write", write_session_to_workspace)):
            try:
                _step_fn()
            except Exception as e:
                msg = f"{_step_name} failed: {type(e).__name__}: {e}"
                print(f"[END SEQUENCE] {msg}", flush=True)
                active_session["errors"].append(msg)
                socketio.emit('routing_action', {'type': 'error', 'message': msg})
        active_session["running"] = False
        socketio.emit('session_complete', {
            'cycles': active_session["cycle"],
            'artifacts_count': len(active_session["artifacts"])
        })

# -----------------------------------------
# FLASK ROUTES
# -----------------------------------------
# ---------------------------------------------------------------
# /diag — read-only diagnostic relay (autonomous-mode access path).
# Claude's sandbox reaches Railway cleanly on 443 but not the workspace's
# port 5001; Railway already holds WORKSPACE_API_KEY and a proven path.
# GET-only, endpoint-whitelisted, gated by DIAG_KEY env var. Returns the
# workspace response verbatim. No write surface is exposed.
DIAG_ALLOWED = {"status", "log", "manifest", "history",
                "api/health", "api/ledger", "api/project_state",
                "api/behavioral_corpus", "api/query"}

@app.route('/diag/<path:endpoint>')
def diag_relay(endpoint):
    diag_key = os.environ.get("DIAG_KEY", "").strip()
    if not diag_key:
        return jsonify({"error": "diag disabled — set DIAG_KEY in Railway variables"}), 503
    if request.headers.get("X-Diag-Key", "") != diag_key and request.args.get("diag_key", "") != diag_key:
        return jsonify({"error": "unauthorized"}), 401
    base = endpoint.split("?")[0].strip("/")
    if base not in DIAG_ALLOWED and not base.startswith("history/"):
        return jsonify({"error": f"endpoint not in diag whitelist", "allowed": sorted(DIAG_ALLOWED)}), 403
    if not WORKSPACE_URL:
        return jsonify({"error": "WORKSPACE_URL not configured"}), 503
    try:
        params = {k: v for k, v in request.args.items() if k != "diag_key"}
        headers = {"X-API-Key": os.environ.get("WORKSPACE_API_KEY", "").strip()}
        r = http_requests.get(f"{WORKSPACE_URL}/{base}", params=params, headers=headers, timeout=25)
        return (r.text, r.status_code, {"Content-Type": r.headers.get("Content-Type", "application/json")})
    except Exception as e:
        return jsonify({"error": f"relay error: {str(e)}"}), 502

@app.route('/')
def index():
    return render_template('index.html')

# -----------------------------------------
# INTAKE PROXY ROUTE
# -----------------------------------------
# Lets ontinuity.org/intake.html run a problem-discovery conversation with
# NO user configuration. The provider key lives here on the server (env var),
# never in the browser. Provider-agnostic — calls the shared model_client
# module, the same primitive any future configuration uses. Session-independent:
# uses call_provider, not call_model, so it touches no session state or socket.
#
# Requires: model_client.py in the repo, prompts/intake_system.txt in the repo,
# and one Railway env var (the only intake item on Railway — it's a secret):
#   CEREBRAS_KEY          = csk-...        (provider API key)
# Optional (defaults to Cerebras gpt-oss-120b if unset):
#   INTAKE_PROVIDER_URL   = https://api.cerebras.ai/v1/chat/completions
#   INTAKE_PROVIDER_MODEL = gpt-oss-120b

from model_client import call_provider, ModelClientError

INTAKE_PROVIDER_URL   = os.environ.get(
    "INTAKE_PROVIDER_URL", "https://api.cerebras.ai/v1/chat/completions").strip()
INTAKE_PROVIDER_MODEL = os.environ.get(
    "INTAKE_PROVIDER_MODEL", "gpt-oss-120b").strip()
INTAKE_PROVIDER_KEY   = os.environ.get("CEREBRAS_KEY", "").strip()

INTAKE_ALLOWED_ORIGINS = {
    "https://ontinuity.org",
    "https://www.ontinuity.org",
}

INTAKE_SYSTEM_PROMPT_PATH = "prompts/intake_system.txt"

def _intake_system_prompt():
    # Same convention as every other role: prompt is a versioned file in the repo.
    return load_file(INTAKE_SYSTEM_PROMPT_PATH) or ""

def _intake_cors_headers(origin):
    allow = origin if origin in INTAKE_ALLOWED_ORIGINS else "https://ontinuity.org"
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
    }

@app.route("/intake_chat", methods=["POST", "OPTIONS"])
def intake_chat():
    origin = request.headers.get("Origin", "")
    headers = _intake_cors_headers(origin)

    if request.method == "OPTIONS":
        return ("", 204, headers)

    if not INTAKE_PROVIDER_KEY:
        return (jsonify({"error": "Intake provider key not configured on server."}), 500, headers)

    if not _intake_system_prompt():
        # F.5 principle: a missing prompt file fails loud, never silently substitutes nothing.
        return (jsonify({"error": "Intake system prompt file missing on server (prompts/intake_system.txt)."}), 500, headers)

    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return (jsonify({"error": "No messages provided."}), 400, headers)

    # Sanitize: only role/content, only user/assistant roles, cap length and count.
    # Cap is 80: a complete intake (~22 exchanges) plus markers runs 40-50 messages,
    # and dropping early messages would silently lose orientation answers.
    clean = []
    for m in messages[-80:]:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            clean.append({"role": role, "content": content[:8000]})
    if not clean:
        return (jsonify({"error": "No valid messages."}), 400, headers)

    try:
        reply = call_provider(
            url=INTAKE_PROVIDER_URL,
            api_key=INTAKE_PROVIDER_KEY,
            model=INTAKE_PROVIDER_MODEL,
            messages=clean,
            system_prompt=_intake_system_prompt(),
            max_tokens=2000,
            temperature=0.7,
        )
        return (jsonify({"reply": reply}), 200, headers)
    except ModelClientError as e:
        return (jsonify({"error": e.message, "detail": e.detail}), (e.status or 502), headers)
    except Exception as e:
        return (jsonify({"error": "Unexpected intake error.", "detail": str(e)[:200]}), 500, headers)

# -----------------------------------------
# INTAKE CAPTURE ROUTE
# -----------------------------------------
# Periodic + final capture of intake sessions to the private intake-data repo.
# Each checkpoint sends the FULL transcript so far and overwrites the previous
# checkpoint file for that session — the latest file is always the complete
# session to that moment. No reassembly needed: one session, one file.
# Fire-and-forget from the page's perspective: failures here never block the
# user's conversation or downloads.
#
# Requires Railway env vars:
#   INTAKE_GITHUB_TOKEN = github_pat_...  (fine-grained, scoped to the data repo)
# Optional:
#   INTAKE_DATA_REPO    = PatrickKillebrew/ontinuity-intake-data  (default)

INTAKE_DATA_REPO  = os.environ.get("INTAKE_DATA_REPO", "PatrickKillebrew/ontinuity-intake-data").strip()
INTAKE_DATA_TOKEN = os.environ.get("INTAKE_GITHUB_TOKEN", "").strip()

@app.route("/intake_capture", methods=["POST", "OPTIONS"])
def intake_capture():
    origin = request.headers.get("Origin", "")
    headers = _intake_cors_headers(origin)

    if request.method == "OPTIONS":
        return ("", 204, headers)

    if not INTAKE_DATA_TOKEN:
        return (jsonify({"error": "Capture token not configured."}), 500, headers)

    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    # Sanitize session_id for filename safety
    session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)[:64]
    if not session_id:
        return (jsonify({"error": "No session_id provided."}), 400, headers)

    transcript = data.get("transcript", [])
    if not isinstance(transcript, list):
        transcript = []
    workspace_state = data.get("workspace_state", None)
    is_final = bool(data.get("final", False))
    # Sequence number from the client (history length): monotonic across sittings.
    try:
        seq = max(0, min(int(data.get("seq", 0)), 9999))
    except (TypeError, ValueError):
        seq = 0

    record = {
        "session_id": session_id,
        "captured_at": timestamp(),
        "final": is_final,
        "seq": seq,
        "exchange_count": sum(1 for m in transcript if isinstance(m, dict) and m.get("role") == "user"),
        "transcript": transcript[:200],
        "workspace_state": workspace_state,
    }

    # Append-only: every checkpoint is a NEW file. Nothing ever overwrites a
    # prior checkpoint, and a fresh path can never serve cached stale content.
    suffix = "final" if is_final else f"{seq:04d}"
    file_path = f"sessions/intake_{session_id}_{suffix}.json"
    gh_url = f"https://api.github.com/repos/{INTAKE_DATA_REPO}/contents/{file_path}"
    gh_headers = {
        "Authorization": f"Bearer {INTAKE_DATA_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        # Get current SHA if the file exists (required to overwrite)
        get_r = http_requests.get(gh_url, headers=gh_headers, timeout=30)
        sha = get_r.json().get("sha", "") if get_r.status_code == 200 else ""
        encoded = base64.b64encode(
            _intake_json_dumps(record).encode("utf-8")).decode("utf-8")
        body = {
            "message": f"Intake {'final' if is_final else 'checkpoint'} — {session_id} — {timestamp()}",
            "content": encoded,
        }
        if sha:
            body["sha"] = sha
        put_r = http_requests.put(gh_url, headers=gh_headers, json=body, timeout=30)
        if put_r.status_code in (200, 201):
            return (jsonify({"captured": True, "final": is_final}), 200, headers)
        return (jsonify({"error": f"GitHub write failed: {put_r.status_code}"}), 502, headers)
    except Exception as e:
        return (jsonify({"error": "Capture error.", "detail": str(e)[:200]}), 502, headers)

def _intake_json_dumps(obj):
    import json as _j
    return _j.dumps(obj, indent=2, ensure_ascii=False)

# -----------------------------------------
# INTAKE RESUME ROUTE
# -----------------------------------------
# Returns the stored session record for a session_id, if one exists, so a
# returning participant picks up exactly where they left off — same transcript,
# same voice. The page restores the full history; the model resumes in-context.

@app.route("/intake_resume", methods=["POST", "OPTIONS"])
def intake_resume():
    origin = request.headers.get("Origin", "")
    headers = _intake_cors_headers(origin)

    if request.method == "OPTIONS":
        return ("", 204, headers)

    if not INTAKE_DATA_TOKEN:
        return (jsonify({"found": False}), 200, headers)

    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)[:64]
    if not session_id:
        return (jsonify({"found": False}), 200, headers)

    file_prefix = f"intake_{session_id}_"
    dir_url = f"https://api.github.com/repos/{INTAKE_DATA_REPO}/contents/sessions"
    gh_headers = {
        "Authorization": f"Bearer {INTAKE_DATA_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        list_r = http_requests.get(dir_url, headers=gh_headers, timeout=30)
        if list_r.status_code != 200:
            return (jsonify({"found": False}), 200, headers)
        entries = list_r.json()
        if not isinstance(entries, list):
            return (jsonify({"found": False}), 200, headers)
        # Find this session's checkpoints: prefer the final file; else highest seq.
        best_name, best_seq, found_final = None, -1, False
        for e in entries:
            name = e.get("name", "")
            if not name.startswith(file_prefix) or not name.endswith(".json"):
                continue
            tail = name[len(file_prefix):-5]  # strip prefix and ".json"
            if tail == "final":
                best_name, found_final = name, True
                break
            if tail.isdigit() and int(tail) > best_seq:
                best_seq, best_name = int(tail), name
        if not best_name:
            return (jsonify({"found": False}), 200, headers)
        file_url = f"{dir_url}/{best_name}"
        get_r = http_requests.get(file_url, headers=gh_headers, timeout=30)
        if get_r.status_code != 200:
            return (jsonify({"found": False}), 200, headers)
        import json as _j
        content_b64 = get_r.json().get("content", "")
        record = _j.loads(base64.b64decode(content_b64).decode("utf-8"))
        return (jsonify({
            "found": True,
            "final": bool(record.get("final", False)) or found_final,
            "transcript": record.get("transcript", []),
            "workspace_state": record.get("workspace_state"),
        }), 200, headers)
    except Exception:
        # Resume is best-effort: any failure means a fresh start, never an error screen.
        return (jsonify({"found": False}), 200, headers)

# -----------------------------------------
# SOCKETIO EVENTS
# -----------------------------------------
@socketio.on('start_session')
def handle_start_session(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Session already running'})
        return
    objective = data.get('objective', '').strip()
    if not objective:
        emit('routing_action', {'type': 'error', 'message': 'No objective provided'})
        return
    # Accept full config overrides (key, url, model) from frontend settings
    configs = data.get('api_keys', {})
    if configs:
        # Fully replace runtime_configs — new config supersedes old entirely
        runtime_configs.clear()
        for role, cfg in configs.items():
            if isinstance(cfg, dict):
                runtime_configs[role] = cfg
            elif isinstance(cfg, str) and cfg.strip():
                # Backward compat: plain key string
                runtime_configs[role] = {'key': cfg.strip()}
    received_fresh = bool(data.get('start_fresh', False))
    emit('routing_action', {'type': 'injection', 'message': f'start_fresh received from dashboard: {received_fresh}'})
    thread = threading.Thread(target=pre_session_then_start, args=(objective, received_fresh))
    thread.daemon = True
    thread.start()

def pre_session_then_start(obj, start_fresh=False):
    # Run Projenius ORIENT to prime session with project-level context
    # Uses a short timeout — if ORIENT is slow or unavailable, session starts without it
    # F.7: start_fresh skips ORIENT entirely — otherwise prior-session knowledge
    # leaks into the objective even though Knowtext injection is correctly skipped.
    knowtext = load_file(CONFIG["knowtext_path"]) or ""
    orient_context = ""
    if start_fresh:
        socketio.emit('routing_action', {'type': 'injection', 'message': 'Starting fresh — skipping Projenius ORIENT (no project context).'})
    else:
        try:
            orient_result = [None]
            def do_orient():
                orient_result[0] = run_projenius_orient(obj, knowtext)
            orient_thread = threading.Thread(target=do_orient)
            orient_thread.daemon = True
            orient_thread.start()
            orient_thread.join(timeout=25)
            if orient_thread.is_alive():
                socketio.emit('routing_action', {'type': 'injection', 'message': 'Projenius ORIENT timed out — starting without project context.'})
            elif orient_result[0]:
                orient_context = orient_result[0]
                socketio.emit('routing_action', {'type': 'injection', 'message': 'Projenius ORIENT complete — project context primed.'})
            else:
                socketio.emit('routing_action', {'type': 'injection', 'message': 'Projenius ORIENT returned no context — starting without it.'})
        except Exception as e:
            socketio.emit('routing_action', {'type': 'error', 'message': f'Projenius ORIENT error: {str(e)} — continuing without project context.'})

    parietal_cfg = get_effective_config("parietal")
    has_parietal = bool(parietal_cfg.get("api_key") and parietal_cfg.get("url"))
    if has_parietal:
        # Pass ORIENT context to PRE_SESSION if available
        refined, needs_answers, contract = run_pre_session(obj, orient_context=orient_context)
        if needs_answers:
            active_session["_pre_session_objective"] = obj
            active_session["start_fresh"] = start_fresh
            return
        obj = refined
    else:
        socketio.emit('routing_action', {'type': 'error', 'message': 'Parietal not configured — starting without PRE_SESSION.'})
        contract = []
    run_session_loop(obj, start_fresh=start_fresh, contract=contract)

@socketio.on('save_api_keys')
def handle_save_api_keys(data):
    global runtime_configs, runtime_github
    configs = data.get('api_keys', {})
    # Fully replace runtime_configs — new config supersedes old entirely
    runtime_configs = {}
    for role, cfg in configs.items():
        if isinstance(cfg, dict):
            runtime_configs[role] = cfg
        elif isinstance(cfg, str) and cfg.strip():
            runtime_configs[role] = {'key': cfg.strip()}
    # Fully replace runtime_github
    runtime_github = {}
    github_cfg = data.get('github', {})
    if github_cfg.get('token'):
        runtime_github['token'] = github_cfg['token'].strip()
    if github_cfg.get('repo'):
        runtime_github['repo'] = github_cfg['repo'].strip()
    emit('routing_action', {'type': 'injection', 'message': 'Model configuration saved for this session.'})

@socketio.on('new_session')
def handle_new_session(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Stop the current session before starting a new one.'})
        return
    active_session["transcript"] = []
    active_session["tag_sequence"] = []
    active_session["signal_sequence"] = []
    active_session["challenge_events"] = []
    active_session["errors"] = []
    active_session["cycle"] = 0
    active_session["artifacts"] = []
    active_session["start_time"] = None
    active_session["end_time"] = None
    active_session["knowtext_version"] = None
    active_session["waiting_for_input"] = False
    active_session["input_type"] = None
    active_session["human_input_value"] = None
    active_session["session_ledger"] = []
    active_session["parietal_navigate_outputs"] = []
    active_session["parietal_adjudicate_rulings"] = []
    active_session["rejected_claims"] = []
    active_session["results_board"] = []
    active_session["contract"] = []
    active_session["start_fresh"] = False
    active_session["distillation_method"] = "failed"
    knowtext = load_file(CONFIG["knowtext_path"]) or ""
    version = knowtext.split("\n")[0].strip() if knowtext else "none"
    emit('session_reset', {
        'message': 'Session reset. Knowtext loaded and ready.',
        'knowtext_version': version
    })

@socketio.on('pre_session_answer')
def handle_pre_session_answer(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Session already running'})
        return
    raw_objective = active_session.get("_pre_session_objective", "")
    answers = data.get('answers', '').strip()
    start_fresh = active_session.get("start_fresh", False)
    def answer_then_start():
        objective, contract = run_pre_session_with_answers(raw_objective, answers)
        run_session_loop(objective, start_fresh=start_fresh, contract=contract)
    thread = threading.Thread(target=answer_then_start)
    thread.daemon = True
    thread.start()

@socketio.on('end_session_final')
def handle_end_session_final(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Stop the current session before ending the project.'})
        return
    # F.8: accept configs with the event (survives Railway restarts between
    # session end and synthesis click) and fail loud with recovery guidance
    # instead of silently skipping the model call.
    configs = (data or {}).get('api_keys', {})
    if configs:
        runtime_configs.clear()
        for role, cfg in configs.items():
            if isinstance(cfg, dict):
                runtime_configs[role] = cfg
            elif isinstance(cfg, str) and cfg.strip():
                runtime_configs[role] = {'key': cfg.strip()}
    synth_cfg = get_effective_config("model_a")
    if not synth_cfg.get("url") or not synth_cfg.get("api_key"):
        emit('routing_action', {'type': 'error', 'message': 'Final synthesis blocked: model configs are not in server memory (the server may have restarted). Open KEYS, press Save, then click End Session — Final Synthesis again.'})
        return
    thread = threading.Thread(target=run_final_synthesis)
    thread.daemon = True
    thread.start()

@socketio.on('human_input')
def handle_human_input(data):
    if active_session["waiting_for_input"]:
        active_session["human_input_value"] = data.get('value', '')
        active_session["human_input_event"].set()

@socketio.on('stop_session')
def handle_stop_session(data):
    active_session["running"] = False
    if active_session["waiting_for_input"]:
        active_session["human_input_value"] = "[SESSION STOPPED BY OPERATOR]"
        active_session["human_input_event"].set()
    socketio.emit('routing_action', {'type': 'error', 'message': 'Session stopped by operator.'})

@socketio.on('get_status')
def handle_get_status(data):
    emit('status', {
        'running': active_session["running"],
        'cycle': active_session["cycle"],
        'waiting_for_input': active_session["waiting_for_input"],
        'input_type': active_session["input_type"]
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, allow_unsafe_werkzeug=True)
