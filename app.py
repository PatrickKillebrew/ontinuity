"""
Ontinuity Web App — Backend
app.py

Run with: python app.py
Then open http://localhost:5000 in your browser.

Install dependencies first:
  pip install flask flask-socketio requests eventlet
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import json
import os
import re
import datetime
import requests as http_requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ontinuity-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# ─────────────────────────────────────────
# CONFIGURATION — edit before running
# ─────────────────────────────────────────

CONFIG = {
    "knowtext_path": "knowtext_current.txt",
    "backup1_path": "knowtext_backup1.txt",
    "backup2_path": "knowtext_backup2.txt",
    "artifacts_dir": "session_artifacts",
    "checkpoint_interval": 10,

    "model_a": {
        "url": "https://api.anthropic.com/v1/messages",
        "api_key": os.environ.get("CLAUDE_API_KEY", ""),
        "model": "claude-sonnet-4-20250514",
        "system_prompt_path": "prompts/model_a_system.txt"
    },
    "model_b": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_1", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "system_prompt_path": "prompts/model_b_system.txt"
    },
    "model_c": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_2", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "system_prompt_path": "prompts/model_c_system.txt"
    },
    "projenius": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.environ.get("GROQ_KEY_3", "").strip(),
        "model": "llama-3.3-70b-versatile",
        "system_prompt_path": "prompts/projenius_system.txt"
    }
}

KNOWTEXT_REQUIRED_FIELDS = [
    "Identity", "Active Frameworks", "Open Questions",
    "Valence Mapping", "Delta Log", "Correction History", "Climate Notes"
]
SCHEMA_VERSION = "KNOWTEXT SCHEMA VERSION: 1.1"

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────

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
    "artifacts": []
}

# ─────────────────────────────────────────
# FILE UTILITIES
# ─────────────────────────────────────────

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

# ─────────────────────────────────────────
# API CALLS
# ─────────────────────────────────────────

def call_openai_compatible(endpoint_config, messages):
    headers = {
        "Authorization": f"Bearer {endpoint_config['api_key']}",
        "Content-Type": "application/json"
    }
    body = {
        "model": endpoint_config["model"],
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3
    }
    try:
        response = http_requests.post(endpoint_config["url"], headers=headers, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        active_session["errors"].append(f"API error: {str(e)}")
        socketio.emit('routing_action', {'type': 'error', 'message': f"API call failed: {str(e)}"})
        return None

def call_claude(endpoint_config, system_prompt, messages):
    headers = {
        "x-api-key": endpoint_config["api_key"],
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
        response = http_requests.post(endpoint_config["url"], headers=headers, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        active_session["errors"].append(f"Claude API error: {str(e)}")
        socketio.emit('routing_action', {'type': 'error', 'message': f"Claude API call failed: {str(e)}"})
        return None

def call_model(role, conversation_messages):
    config = CONFIG[role]
    system_prompt = load_file(config["system_prompt_path"]) or ""
    if role == "model_a":
        return call_claude(config, system_prompt, conversation_messages)
    else:
        messages = [{"role": "system", "content": system_prompt}] + conversation_messages
        return call_openai_compatible(config, messages)

# ─────────────────────────────────────────
# TAG AND SIGNAL UTILITIES
# ─────────────────────────────────────────

def extract_tag(response):
    match = re.search(r'\[CYCLE_STATUS:\s*([\w_]+)\]', response)
    return match.group(1) if match else "CONTINUE"

def extract_signal(response):
    match = re.search(r'SIGNAL:\s*([0-4])', response)
    return int(match.group(1)) if match else 0

def get_ambient_signal_line(signal):
    labels = {0: "clear", 1: "nominal", 2: "caution", 3: "warning", 4: "override"}
    return f"AMBIENT_SIGNAL: {signal}  ({labels.get(signal, 'unknown')})"

# ─────────────────────────────────────────
# HUMAN INPUT — blocks thread until received
# ─────────────────────────────────────────

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

    active_session["human_input_event"].wait(timeout=300)  # 5 min timeout
    active_session["waiting_for_input"] = False

    return active_session["human_input_value"] or ""

# ─────────────────────────────────────────
# FRICTION SCORING
# ─────────────────────────────────────────

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

    active_session["signal_sequence"].append(f"Cycle {active_session['cycle']}: SIGNAL {signal} — {reason}")
    socketio.emit('friction_signal', {
        'signal': signal,
        'reason': reason,
        'cycle': active_session["cycle"]
    })
    return signal, reason

# ─────────────────────────────────────────
# DISTILLATION
# ─────────────────────────────────────────

def validate_knowtext_response(response):
    for field in KNOWTEXT_REQUIRED_FIELDS:
        if field not in response:
            return False, field
    return True, None

def run_distillation():
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Running Projenius extraction...'})
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])
    extraction_prompt = load_file("prompts/knowtext_extraction_prompt.txt") or \
        "Extract session content into the Knowtext schema fields. Write only what changed."

    messages = [{"role": "user", "content": f"{extraction_prompt}\n\n---SESSION TRANSCRIPT---\n{transcript_text}"}]
    response = call_model("projenius", messages)

    if not response:
        socketio.emit('routing_action', {'type': 'error', 'message': 'Distillation failed — retaining current Knowtext'})
        return False

    valid, missing_field = validate_knowtext_response(response)
    if not valid:
        socketio.emit('routing_action', {'type': 'error', 'message': f'Distillation failed — missing field: {missing_field}'})
        return False

    rotate_backups()
    new_knowtext = f"{SCHEMA_VERSION}\n\n{response}"
    save_file(CONFIG["knowtext_path"], new_knowtext)
    socketio.emit('routing_action', {'type': 'distillation', 'message': 'Knowtext updated successfully'})
    return True

# ─────────────────────────────────────────
# WORK PRODUCT EXTRACTION
# ─────────────────────────────────────────

def run_work_product_extraction():
    socketio.emit('routing_action', {'type': 'extraction', 'message': 'Extracting session work product...'})
    transcript_text = "\n\n".join([f"[{e['role'].upper()}] {e['content']}" for e in active_session["transcript"]])

    extraction_prompt = (
        "You are reviewing a completed Ontinuity session. Extract the work product — "
        "everything that was established, built, decided, or completed in this session. "
        "Output a clean document containing only the deliverables. Do not include process, "
        "discussion, or metadata. Format appropriate to the content."
    )

    messages = [{"role": "user", "content": f"{extraction_prompt}\n\n---SESSION TRANSCRIPT---\n{transcript_text}"}]
    response = call_model("model_a", messages)

    if not response or len(response.strip()) < 20:
        messages = [{"role": "user", "content": f"Review the session transcript and output everything completed or established. Plain text.\n\n{transcript_text}"}]
        response = call_model("model_a", messages)

    path = artifact_path("work_product")
    content = response if (response and len(response.strip()) >= 20) else f"[EXTRACTION FAILED — MANUAL REVIEW REQUIRED]\n\n{transcript_text}"
    save_file(path, content)

    active_session["artifacts"].append({"label": "Work Product", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Work Product', 'content': content})

# ─────────────────────────────────────────
# SESSION LOG
# ─────────────────────────────────────────

def write_session_log():
    active_session["end_time"] = timestamp()
    log_lines = [
        "ONTINUITY SESSION LOG",
        f"Session start: {active_session['start_time']}",
        f"Session end: {active_session['end_time']}",
        f"Knowtext version: {active_session['knowtext_version'] or 'none'}",
        f"Model A: {CONFIG['model_a']['model']}",
        f"Model B: {CONFIG['model_b']['model']}",
        f"Model C: {CONFIG['model_c']['model']}",
        f"Projenius: {CONFIG['projenius']['model']}",
        f"Total cycles: {active_session['cycle']}",
        "", "STATUS TAG SEQUENCE:"
    ] + active_session["tag_sequence"] + [
        "", "FRICTION SIGNAL SEQUENCE:"
    ] + active_session["signal_sequence"] + [
        "", "CHALLENGE EVENTS:"
    ] + (active_session["challenge_events"] or ["none"]) + [
        "", "ERRORS:"
    ] + (active_session["errors"] or ["none"])

    content = "\n".join(log_lines)
    path = artifact_path("session_log")
    save_file(path, content)
    active_session["artifacts"].append({"label": "Session Log", "path": path, "content": content})
    socketio.emit('artifact_ready', {'label': 'Session Log', 'content': content})

# ─────────────────────────────────────────
# MAIN SESSION LOOP
# ─────────────────────────────────────────

def run_session_loop(objective):
    active_session["running"] = True
    active_session["start_time"] = timestamp()
    active_session["transcript"] = []
    active_session["tag_sequence"] = []
    active_session["signal_sequence"] = []
    active_session["challenge_events"] = []
    active_session["errors"] = []
    active_session["cycle"] = 0
    active_session["artifacts"] = []

    # Function 1 — Injection
    socketio.emit('routing_action', {'type': 'injection', 'message': 'Loading Knowtext...'})
    knowtext = load_file(CONFIG["knowtext_path"]) or ""
    checkpoint_interval = CONFIG["checkpoint_interval"] if knowtext else 15
    if knowtext:
        first_line = knowtext.split("\n")[0].strip()
        active_session["knowtext_version"] = first_line
        socketio.emit('routing_action', {'type': 'injection', 'message': 'Knowtext injected into Model A context'})
    else:
        socketio.emit('routing_action', {'type': 'injection', 'message': 'No Knowtext found — starting cold'})

    model_a_system = load_file(CONFIG["model_a"]["system_prompt_path"]) or "You are Model A, the Researcher."
    if knowtext:
        model_a_system = f"{model_a_system}\n\n---KNOWTEXT---\n{knowtext}"

    conversation = [{"role": "user", "content": f"Session objective: {objective}\n\nBegin."}]

    socketio.emit('session_started', {'objective': objective})

    while active_session["running"]:
        active_session["cycle"] += 1
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} — Model A generating'})

        # Model A
        a_response = call_model("model_a", conversation)
        if not a_response:
            socketio.emit('model_warning', {'role': 'model_a', 'message': 'Model A failed to respond. Ending session.'})
            socketio.emit('routing_action', {'type': 'error', 'message': 'Model A returned no response. Ending session.'})
            break

        active_session["transcript"].append({"role": "model_a", "content": a_response})
        conversation.append({"role": "assistant", "content": a_response})
        socketio.emit('model_response', {'role': 'model_a', 'label': 'Researcher', 'content': a_response, 'cycle': active_session["cycle"]})

        # Friction signal
        signal, reason = get_friction_signal()
        ambient_line = get_ambient_signal_line(signal)

        # Tag
        tag = extract_tag(a_response)
        active_session["tag_sequence"].append(f"Cycle {active_session['cycle']} A: {tag}")
        socketio.emit('tag_detected', {'role': 'model_a', 'tag': tag, 'cycle': active_session["cycle"]})

        # Signal 4 override
        if signal == 4:
            signal4_context = f"Critical drift detected.\n\nModel C reason: {reason}\n\nAlignment input required before loop resumes."
            direction = wait_for_human_input("signal4", signal4_context)
            conversation.append({"role": "user", "content": f"[OPERATOR ALIGNMENT]: {direction}\n{ambient_line}"})
            continue

        if tag == "SESSION_END":
            socketio.emit('routing_action', {'type': 'session_end', 'message': 'SESSION_END tag received. Running end sequence.'})
            break

        elif tag == "ALIGNMENT_NEEDED":
            direction = wait_for_human_input("alignment", a_response)
            conversation.append({"role": "user", "content": f"[OPERATOR]: {direction}\n{ambient_line}"})
            continue

        elif tag == "CHECKPOINT":
            recent = active_session["transcript"][-4:] if len(active_session["transcript"]) > 4 else active_session["transcript"]
            checkpoint_context = f"Cycle {active_session['cycle']} checkpoint.\n\n" + "\n\n".join([f"[{e['role'].upper()}] {e['content'][:400]}" for e in recent])
            direction = wait_for_human_input("checkpoint", checkpoint_context)
            conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}\n{ambient_line}"})
            continue

        # Model B
        socketio.emit('routing_action', {'type': 'cycle', 'message': f'Cycle {active_session["cycle"]} — Challenger reviewing'})
        b_messages = [{"role": "user", "content": f"Review this output:\n\n{a_response}\n\n{ambient_line}"}]
        b_response = call_model("model_b", b_messages)
        if not b_response:
            socketio.emit('model_warning', {'role': 'model_b', 'message': 'Model B failed — running without adversarial review this cycle'})

        if b_response:
            active_session["transcript"].append({"role": "model_b", "content": b_response})
            socketio.emit('model_response', {'role': 'model_b', 'label': 'Challenger', 'content': b_response, 'cycle': active_session["cycle"]})

            b_tag = extract_tag(b_response)
            active_session["tag_sequence"].append(f"Cycle {active_session['cycle']} B: {b_tag}")
            socketio.emit('tag_detected', {'role': 'model_b', 'tag': b_tag, 'cycle': active_session["cycle"]})

            if b_tag == "CHALLENGE":
                adjudication = wait_for_human_input("challenge", b_response)
                active_session["challenge_events"].append(f"Cycle {active_session['cycle']}: {adjudication}")
                conversation.append({"role": "user", "content": f"[CHALLENGE ADJUDICATED]: {adjudication}\n{ambient_line}"})
                continue
            elif b_tag == "SESSION_END":
                socketio.emit('routing_action', {'type': 'session_end', 'message': 'SESSION_END from Challenger. Running end sequence.'})
                break

        # Continue
        next_input = ambient_line
        if b_response:
            next_input += f"\n\n[CHALLENGER REVIEW]: {b_response}"
        conversation.append({"role": "user", "content": next_input})

        # Auto checkpoint
        if active_session["cycle"] % checkpoint_interval == 0:
            recent = active_session["transcript"][-4:] if len(active_session["transcript"]) > 4 else active_session["transcript"]
            checkpoint_context = f"Auto-checkpoint at cycle {active_session['cycle']}.\n\n" + "\n\n".join([f"[{e['role'].upper()}] {e['content'][:400]}" for e in recent])
            direction = wait_for_human_input("checkpoint", checkpoint_context)
            conversation.append({"role": "user", "content": f"[OPERATOR CHECKPOINT]: {direction}"})

    # End sequence
    run_distillation()
    run_work_product_extraction()
    write_session_log()

    active_session["running"] = False
    socketio.emit('session_complete', {
        'cycles': active_session["cycle"],
        'artifacts_count': len(active_session["artifacts"])
    })

# ─────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ─────────────────────────────────────────
# SOCKETIO EVENTS
# ─────────────────────────────────────────

@socketio.on('start_session')
def handle_start_session(data):
    if active_session["running"]:
        emit('routing_action', {'type': 'error', 'message': 'Session already running'})
        return
    objective = data.get('objective', '').strip()
    if not objective:
        emit('routing_action', {'type': 'error', 'message': 'No objective provided'})
        return
    thread = threading.Thread(target=run_session_loop, args=(objective,))
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
    socketio.emit('routing_action', {'type': 'error', 'message': 'Session stopped by operator'})

@socketio.on('get_status')
def handle_get_status(data):
    emit('status', {
        'running': active_session["running"],
        'cycle': active_session["cycle"],
        'waiting_for_input': active_session["waiting_for_input"],
        'input_type': active_session["input_type"]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
