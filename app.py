"""
Ontinuity Web App - Backend
app.py
Run with: python app.py
Then open http://localhost:5000 in your browser.
Install dependencies first:
    pip install flask flask-socketio requests
"""
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import os
import re
import datetime
import time
import requests as http_requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ontinuity-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
CONFIG = {
    "knowtext_path": "knowtext_current.txt",
    "backup1_path": "knowtext_backup1.txt",
    "backup2_path": "knowtext_backup2.txt",
    "artifacts_dir": "session_artifacts",
    "checkpoint_interval": 10,
    "model_a": {
        "url": "https://api.anthropic.com/v1/messages",
        "api_key": os.environ.get("CLAUDE_API_KEY", "").strip(),
        "model": "claude-sonnet-4-20250514",
        "api_format": "anthropic",
        "system_prompt_path": "prompts/model_a_system.txt"
    },
    "model_b": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_1", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "api_format": "openai",
        "system_prompt_path": "prompts/model_b_system.txt"
    },
    "model_c": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_2", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "api_format": "openai",
        "system_prompt_path": "prompts/model_c_system.txt"
    },
    "projenius": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_3", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "api_format": "openai",
        "system_prompt_path": "prompts/projenius_system.txt"
    },
    "parietal": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_3", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "api_format": "openai",
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
    "start_fresh": False               # If True, skip Knowtext injection for this session
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
GITHUB_FILE_PATH = "knowtext_current.txt"
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
            import base64
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
        import base64
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

# -----------------------------------------
# API CALLS - PROVIDER AGNOSTIC
# -----------------------------------------
def get_api_key(role):
    """Get API key — runtime override from frontend takes precedence over environment."""
    if role in runtime_configs and runtime_configs[role].get('key'):
        return runtime_configs[role]['key'].strip()
    return CONFIG[role]["api_key"].strip()

def call_openai_format(endpoint_config, messages, role):
    headers = {
        "Authorization": f"Bearer {get_api_key(role)}",
        "Content-Type": "application/json"
    }
    body = {
        "model": endpoint_config["model"],
        "messages": messages,
        "max_tokens": 2000,
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
        except Exception as e:
            active_session["errors"].append(f"API error: {str(e)}")
            socketio.emit('routing_action', {'type': 'error', 'message': f"API call failed: {str(e)}"})
            return None

def call_anthropic_format(endpoint_config, system_prompt, messages, role):
    headers = {
        "x-api-key": get_api_key(role),
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    body = {
        "model": endpoint_config["model"],
        "max_tokens": 2000,
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

def call_gemini_native(endpoint_config, system_prompt, messages, role):
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
        "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.3}
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

def call_model(role, conversation_messages, system_override=None):
    config = get_effective_config(role)
    api_format = detect_api_format(config["url"])
    system_prompt = system_override or load_file(config["system_prompt_path"]) or ""
    if api_format == "anthropic":
        return call_anthropic_format(config, system_prompt, conversation_messages, role)
    elif api_format == "gemini":
        return call_gemini_native(config, system_prompt, conversation_messages, role)
    else:
        messages = [{"role": "system", "content": system_prompt}] + conversation_messages
        return call_openai_format(config, messages, role)

# -----------------------------------------
# TAG AND SIGNAL UTILITIES
# -----------------------------------------
def extract_tag(response):
    match = re.search(r'\[CYCLE_STATUS:\s*([\w_]+)\]', response)
    return match.group(1) if match else "CONTINUE"

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
    """Call a Parietal function by tag. Returns response string or None."""
    parietal_cfg = get_effective_config("parietal")
    has_parietal = bool(parietal_cfg.get("api_key") or parietal_cfg.get("url"))
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

def run_pre_session(objective):
    """Run PRE_SESSION — returns (refined_objective, needs_answers)."""
    response = call_parietal("PRE_SESSION", objective=objective)
    if not response:
        return objective, False
    if "READY:" in response.upper():
        idx = response.upper().find("READY:")
        refined = response[idx + 6:].strip()
        socketio.emit('parietal_pre_session', {'status': 'ready', 'questions': response, 'cycle': 0})
        return refined or objective, False
    socketio.emit('parietal_pre_session', {'status': 'questions', 'questions': response, 'cycle': 0})
    return objective, True

def run_pre_session_with_answers(raw_objective, answers):
    """Run PRE_SESSION with operator answers — returns refined objective."""
    response = call_parietal("PRE_SESSION",
                             objective=raw_objective,
                             operator_answers=answers)
    if not response:
        return raw_objective
    if "READY:" in response.upper():
        idx = response.upper().find("READY:")
        refined = response[idx + 6:].strip()
        return refined or raw_objective
    return raw_objective

def run_parietal_navigate(knowtext, signal_sequence_recent=None):
    """Run NAVIGATE — returns structured orientation string or None."""
    working = get_working_context(knowtext) if knowtext else ""
    ledger = get_session_ledger_summary()
    signal_info = ""
    if signal_sequence_recent:
        signal_info = "\n".join(signal_sequence_recent[-5:])
    response = call_parietal("NAVIGATE",
                             knowtext_working_context=working,
                             session_ledger=ledger,
                             friction_signal_sequence=signal_info)
    if response:
        socketio.emit('parietal_navigate', {'output': response, 'cycle': active_session["cycle"]})
    return response

def run_parietal_adjudicate(disputed_claim, grounds, knowtext):
    """Run ADJUDICATE — returns ruling string or None."""
    working = get_working_context(knowtext) if knowtext else ""
    ledger = get_session_ledger_summary()
    signal = active_session["signal_sequence"][-1] if active_session["signal_sequence"] else ""
    response = call_parietal("ADJUDICATE",
                             disputed_claim=disputed_claim,
                             grounds=grounds,
                             session_ledger=ledger,
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


    """Run DISTILL — returns updated Knowtext string or None."""
    ledger = get_session_ledger_summary()
    navigate_outputs = "\n\n".join(active_session.get("parietal_navigate_outputs", []))
    adjudicate_rulings = "\n\n".join(active_session.get("parietal_adjudicate_rulings", []))
    signal_seq = "\n".join(active_session["signal_sequence"])
    response = call_parietal("DISTILL",
                             session_ledger=ledger,
                             navigate_outputs=navigate_outputs,
                             adjudicate_rulings=adjudicate_rulings,
                             friction_signal_sequence=signal_seq,
                             current_knowtext=knowtext or "")
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
def run_work_product_extraction():
    socketio.emit('routing_action', {'type': 'extraction', 'message': 'Extracting session work product...'})
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])
    extraction_prompt = (
        "You are reviewing a completed Ontinuity session. Extract the work product - "
        "everything that was established, built, decided, or completed in this session. "
        "Output a clean document containing only the deliverables. Do not include process, "
        "discussion, or metadata. Format appropriate to the content."
    )
    messages = [{"role": "user", "content": f"{extraction_prompt}\n\n---SESSION TRANSCRIPT---\n\n{transcript_text}"}]
    response = call_model("model_a", messages)
    if not response or len(response.strip()) < 20:
        messages = [{"role": "user", "content": f"Review the session transcript and output everything that was established or produced:\n\n{transcript_text}"}]
        response = call_model("model_a", messages)
    path = artifact_path("work_product")
    content = response if (response and len(response.strip()) >= 20) else "[EXTRACTION FAILED]"
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
    response = call_model("model_a", messages)
    content = response if response else "[FINAL SYNTHESIS FAILED]"
    path = artifact_path("final_synthesis")
    save_file(path, content)
    active_session["artifacts"].append({"label": "Final Synthesis", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Final Synthesis', 'content': content})
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
def run_session_loop(objective, start_fresh=False):
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
        # Context trimming — keep conversation window manageable
        if len(conversation) > 10:
            conversation = conversation[:1] + conversation[-8:]
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} - Researcher generating...'})

        # Model A
        a_response = call_model("model_a", conversation, system_override=model_a_system)
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

        # Signal 4 override
        if signal == 4:
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
            socketio.emit('routing_action', {'type': 'session_end', 'message': 'SESSION_END received.'})
            break
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
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("alignment", a_response)
                    conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
            continue
        elif tag == "CHECKPOINT":
            nav = run_parietal_navigate(knowtext, active_session["signal_sequence"])
            if nav:
                active_session["parietal_navigate_outputs"].append(nav)
                resolve = run_parietal_resolve(nav, knowtext)
                if resolve:
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: CHECKPOINT RESOLVED — {resolve[:200]}"
                    )
                    conversation.append({"role": "user", "content": f"{resolve}\n{ambient_line}"})
                else:
                    direction = wait_for_human_input("checkpoint", nav)
                    conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})
            else:
                ledger = get_session_ledger_summary()
                checkpoint_context = f"Cycle {active_session['cycle']} checkpoint.\n\n{ledger}" if ledger else f"Cycle {active_session['cycle']} checkpoint."
                direction = wait_for_human_input("checkpoint", checkpoint_context)
                conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})
            continue

        # Brief pause to spread GROQ rate limit load
        time.sleep(2)

        # Model B - two-layer context: filtered Knowtext + session ledger
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} - Challenger reviewing...'})
        ledger_summary = get_session_ledger_summary()
        b_context_parts = []
        if knowtext_for_b:
            b_context_parts.append(f"[PROJECT CONTEXT]\n{knowtext_for_b}")
        if ledger_summary:
            b_context_parts.append(f"[{ledger_summary}]")
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

            if b_tag == "CHALLENGE":
                # Try Parietal ADJUDICATE first
                ruling = run_parietal_adjudicate(b_response, "", knowtext)
                if ruling:
                    active_session["parietal_adjudicate_rulings"].append(
                        f"Cycle {active_session['cycle']}: {ruling[:300]}"
                    )
                    active_session["challenge_events"].append(
                        f"Cycle {active_session['cycle']}: {ruling[:200]}"
                    )
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
            elif b_tag == "SESSION_END":
                socketio.emit('routing_action', {'type': 'session_end', 'message': 'SESSION_END received from Challenger.'})
                break

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

    # Try Parietal DISTILL first
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
            distilled = True
        else:
            socketio.emit('routing_action', {'type': 'distillation', 'message': f'Parietal distillation missing field: {missing} — falling back to Projenius.'})
            distilled = run_distillation_with_timeout(run_distillation) or False
    else:
        socketio.emit('routing_action', {'type': 'distillation', 'message': 'Parietal distillation failed — trying Projenius...'})
        distilled = run_distillation_with_timeout(run_distillation) or False
    if not distilled:
        socketio.emit('routing_action', {'type': 'distillation', 'message': 'Distillation skipped — session complete without Knowtext update.'})
        run_work_product_extraction()
    write_session_log()

    # Step 4.5 — Behavioral database extraction
    try:
        from extract_to_db import extract_and_store
        session_log_content = next(
            (a["content"] for a in active_session["artifacts"] 
             if a["label"] == "Session Log"), None
        )
        if session_log_content:
            db_result = extract_and_store(
                session_log_content,
                "ontinuity_behavioral_data.db"
            )
            socketio.emit('routing_action', {
                'type': 'distillation',
                'message': f"Behavioral database updated. "
                           f"{db_result['challenges']} challenges, "
                           f"{db_result['signals']} signals recorded."
            })
            commit_to_github(
                "ontinuity_behavioral_data.db",
                f"Session data: {active_session['start_time']}"
            )
        else:
            socketio.emit('routing_action', {
                'type': 'distillation',
                'message': 'Database extraction skipped — session log not found.'
            })
    except Exception as e:
        socketio.emit('routing_action', {
            'type': 'distillation',
            'message': f'Database extraction failed: {str(e)}'
        })

    active_session["running"] = False
    socketio.emit('session_complete', {
        'cycles': active_session["cycle"],
        'artifacts_count': len(active_session["artifacts"])
    })


# -----------------------------------------
# FLASK ROUTES
# -----------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

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
    thread = threading.Thread(target=pre_session_then_start, args=(objective, data.get('start_fresh', False)))
    thread.daemon = True
    thread.start()

def pre_session_then_start(obj, start_fresh=False):
    parietal_cfg = get_effective_config("parietal")
    has_parietal = bool(parietal_cfg.get("api_key") or parietal_cfg.get("url"))
    if has_parietal:
        refined, needs_answers = run_pre_session(obj)
        if needs_answers:
            active_session["_pre_session_objective"] = obj
            active_session["start_fresh"] = start_fresh
            return
        obj = refined
    else:
        socketio.emit('routing_action', {'type': 'error', 'message': 'Parietal not configured — starting without PRE_SESSION.'})
    run_session_loop(obj, start_fresh=start_fresh)

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
    active_session["start_fresh"] = False
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
        objective = run_pre_session_with_answers(raw_objective, answers)
        run_session_loop(objective, start_fresh=start_fresh)
    thread = threading.Thread(target=answer_then_start)
    thread.daemon = True
    thread.start()

@socketio.on('end_session_final')
def handle_end_session_final(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Stop the current session before ending the project.'})
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
