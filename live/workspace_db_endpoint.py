"""
workspace_db_endpoint.py

Flask Blueprint for the Ontinuity workspace server.
Receives session data POSTed by Railway app after each session ends
and writes it to the local Ontinuity database via db.py.

INTEGRATION — add to your existing workspace server:

    from workspace_db_endpoint import db_blueprint, init_db
    app.register_blueprint(db_blueprint)
    init_db()          # call once at startup

Or run standalone for testing:
    python3 workspace_db_endpoint.py

Railway env vars needed:
    WORKSPACE_URL     = https://your-domain.duckdns.org:5001
    WORKSPACE_PROJECT = Ontinuity Platform   (or whichever project)
    WORKSPACE_BRANCH  = main

The endpoint authenticates via a shared secret token.
Set WORKSPACE_TOKEN in both Railway and your workspace server env.
If not set, authentication is skipped (acceptable for local-only use).
"""

import os
import json
import re
from flask import Flask, Blueprint, request, jsonify

# Import the database module — must be in same directory or on PYTHONPATH
try:
    from db import OntinuityDB, sanitize, now_utc
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("WARNING: db.py not found. Database writes will be skipped.")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
DB_PATH        = os.environ.get("ONTINUITY_DB_PATH", "ontinuity.db")
WORKSPACE_TOKEN = os.environ.get("WORKSPACE_TOKEN", "").strip()
# If set, Railway must send this in the X-Workspace-Token header.
# Leave empty during local development.

# Singleton database instance
_db = None

def get_db() -> "OntinuityDB":
    global _db
    if _db is None and DB_AVAILABLE:
        _db = OntinuityDB(DB_PATH)
        _db.init()
    return _db

def init_db():
    """Call once at workspace server startup."""
    db = get_db()
    if db:
        print(f"Ontinuity DB ready at {DB_PATH}")
    else:
        print("Ontinuity DB unavailable — db.py missing.")


# ─────────────────────────────────────────────
# BLUEPRINT
# ─────────────────────────────────────────────
db_blueprint = Blueprint("ontinuity_db", __name__)


def _auth_ok():
    """Check workspace token if one is configured."""
    if not WORKSPACE_TOKEN:
        return True  # no auth configured — allow all (local dev)
    token = request.headers.get("X-Workspace-Token", "")
    return token == WORKSPACE_TOKEN


def _get_or_create_project(db, user_id, project_name, branch_name):
    """Find or create project and branch. Returns (project_id, branch_id)."""
    conn = db.connect()

    # Find project
    row = conn.execute(
        "SELECT project_id FROM projects WHERE user_id = ? AND name = ?",
        (user_id, project_name)
    ).fetchone()
    if row:
        project_id = row["project_id"]
    else:
        project_id = db.insert_project(user_id, project_name)

    # Find branch
    row = conn.execute(
        "SELECT branch_id FROM branches "
        "WHERE project_id = ? AND name = ?",
        (project_id, branch_name)
    ).fetchone()
    if row:
        branch_id = row["branch_id"]
    else:
        branch_id = db.insert_branch(project_id, user_id, branch_name)

    return project_id, branch_id


def _get_or_create_user(db):
    """Return first user in database, or create a default one."""
    conn = db.connect()
    row = conn.execute(
        "SELECT user_id FROM users LIMIT 1"
    ).fetchone()
    if row:
        return row["user_id"]
    return db.insert_user("Workspace User", plan="personal")


def _register_models(db, models_dict):
    """Register all session models in model_registry. Returns model_id map."""
    provider_map = {
        "anthropic": "anthropic", "claude": "anthropic",
        "gpt": "openai", "openai": "openai",
        "llama": "meta", "qwen": "alibaba",
        "gemini": "google", "cerebras": "cerebras",
        "groq": "groq", "mistral": "mistral",
    }
    model_ids = {}
    for role, model_str in models_dict.items():
        if not model_str:
            continue
        provider = next(
            (v for k, v in provider_map.items()
             if k in model_str.lower()),
            "custom"
        )
        model_ids[role] = db.insert_model(model_str, provider)
    return model_ids


@db_blueprint.route("/api/session", methods=["POST"])
def receive_session():
    """
    Receive a completed session payload from the Railway app.
    Writes all data to the local Ontinuity database.

    Expected JSON payload structure matches build_session_payload()
    in app.py — see that function for full field list.
    """
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database not available"}), 503

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    session_id   = data.get("session_id")
    project_name = data.get("project_name", "Ontinuity Platform")
    branch_name  = data.get("branch_name", "main")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        user_id = _get_or_create_user(db)
        project_id, branch_id = _get_or_create_project(
            db, user_id, project_name, branch_name)

        # Register models
        model_ids = _register_models(db, data.get("models", {}))

        # ── Insert session ──────────────────────────────────────────────
        db.insert_session({
            "session_id":              session_id,
            "user_id":                 user_id,
            "project_id":              project_id,
            "branch_id":               branch_id,
            "objective":               data.get("objective"),
            "start_time":              data.get("start_time"),
            "end_time":                data.get("end_time"),
            "total_cycles":            data.get("total_cycles", 0),
            "status":                  data.get("status", "complete"),
            "model_a_id":              model_ids.get("model_a"),
            "model_b_id":              model_ids.get("model_b"),
            "model_c_id":              model_ids.get("model_c"),
            "parietal_id":             model_ids.get("parietal"),
            "projenius_id":            model_ids.get("projenius"),
            "model_a_string":          data.get("models", {}).get("model_a"),
            "model_b_string":          data.get("models", {}).get("model_b"),
            "model_c_string":          data.get("models", {}).get("model_c"),
            "parietal_string":         data.get("models", {}).get("parietal"),
            "projenius_string":        data.get("models", {}).get("projenius"),
            "distillation_method":     data.get("distillation_method"),
            "knowtext_version":        data.get("knowtext_version"),
            "friction_profile":        data.get("friction_profile", []),
            "friction_reasons":        data.get("friction_reasons", []),
            "challenge_count":         data.get("challenge_count", 0),
            "uphold_count":            data.get("uphold_count", 0),
            "reject_count":            data.get("reject_count", 0),
            "pursue_both_count":       data.get("pursue_both_count", 0),
            "escalate_count":          data.get("escalate_count", 0),
            "avg_friction_signal":     data.get("avg_friction_signal"),
            "signal_variance":         data.get("signal_variance"),
            "peak_signal":             data.get("peak_signal"),
            "cycles_to_first_challenge": data.get("cycles_to_first_challenge"),
            "cycles_to_session_end":   data.get("cycles_to_session_end"),
            "created_at":              now_utc(),
        })

        # ── Insert transcript turns ─────────────────────────────────────
        for turn in data.get("transcript_turns", []):
            db.insert_transcript_turn(
                session_id=session_id,
                cycle_number=turn.get("cycle_number", 0),
                turn_number=turn.get("turn_number", 0),
                role=turn.get("role", ""),
                content=turn.get("content", ""),
                tag=turn.get("tag"),
                friction_signal=turn.get("friction_signal"),
            )

        # ── Insert artifacts ────────────────────────────────────────────
        for artifact in data.get("artifacts", []):
            db.insert_artifact(
                session_id=session_id,
                user_id=user_id,
                artifact_type=_normalize_artifact_type(
                    artifact.get("label", "")),
                content=artifact.get("content", ""),
                file_path=artifact.get("path"),
            )

        # ── Insert Knowtext version ─────────────────────────────────────
        knowtext_content = data.get("knowtext_content", "")
        if knowtext_content and len(knowtext_content.strip()) > 20:
            db.insert_knowtext_version(
                session_id=session_id,
                branch_id=branch_id,
                user_id=user_id,
                content_full=knowtext_content,
                schema_version=data.get("knowtext_version",
                                        "KNOWTEXT SCHEMA VERSION: 1.1"),
                distillation_method=data.get("distillation_method"),
            )

        # ── Insert challenge events ─────────────────────────────────────
        raw_events = data.get("challenge_events_raw", [])
        for event_str in raw_events:
            cycle_m = re.search(r'Cycle (\d+):', event_str)
            cycle_num = int(cycle_m.group(1)) if cycle_m else 0
            ruling = "UNKNOWN"
            for r in ["UPHOLD", "REJECT", "PURSUE BOTH", "ESCALATE",
                      "PURSUE_BOTH"]:
                if r in event_str.upper():
                    ruling = r.replace(" ", "_")
                    break
            db.insert_challenge_event(
                session_id=session_id,
                user_id=user_id,
                cycle_number=cycle_num,
                challenged_claim="",  # raw events don't separate this
                grounds="",
                ruling=ruling,
                ruling_justification=sanitize(event_str[:500]),
            )

        # ── Insert behavioral observations ──────────────────────────────
        for obs in data.get("behavioral_observations", []):
            obs["user_id"] = user_id
            db.insert_behavioral_observation(obs)

        return jsonify({
            "status": "ok",
            "session_id": session_id,
            "project_id": project_id,
            "branch_id": branch_id,
            "turns_written": len(data.get("transcript_turns", [])),
            "artifacts_written": len(data.get("artifacts", [])),
            "observations_written": len(
                data.get("behavioral_observations", [])),
        }), 200

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Session write error: {error_detail}")
        return jsonify({
            "error": str(e),
            "session_id": session_id
        }), 500


@db_blueprint.route("/api/ledger", methods=["GET"])
def query_ledger():
    """
    Query the Established Results Ledger.
    Used by Projenius LEDGER_QUERY and ORIENT functions.

    Query params:
        project_name  (optional)
        branch_name   (optional)
        confidence    (optional: ESTABLISHED, PROVISIONAL)
    """
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database not available"}), 503

    project_name = request.args.get("project_name")
    branch_name  = request.args.get("branch_name")
    confidence   = request.args.get("confidence")

    try:
        conn = db.connect()
        project_id = branch_id = None

        if project_name:
            row = conn.execute(
                "SELECT project_id FROM projects WHERE name = ? LIMIT 1",
                (project_name,)
            ).fetchone()
            if row:
                project_id = row["project_id"]

        if branch_name and project_id:
            row = conn.execute(
                "SELECT branch_id FROM branches "
                "WHERE project_id = ? AND name = ? LIMIT 1",
                (project_id, branch_name)
            ).fetchone()
            if row:
                branch_id = row["branch_id"]

        results = db.get_active_results(
            branch_id=branch_id,
            project_id=project_id,
            confidence=confidence
        )
        return jsonify({"results": results, "count": len(results)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@db_blueprint.route("/api/project_state", methods=["GET"])
def get_project_state():
    """
    Return full project state for Projenius ORIENT.
    Query params: project_name (required)
    """
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database not available"}), 503

    project_name = request.args.get("project_name", "")
    if not project_name:
        return jsonify({"error": "project_name required"}), 400

    try:
        conn = db.connect()
        row = conn.execute(
            "SELECT project_id FROM projects WHERE name = ? LIMIT 1",
            (project_name,)
        ).fetchone()
        if not row:
            return jsonify({"error": f"Project '{project_name}' not found"}), 404
        state = db.get_project_state(row["project_id"])
        return jsonify(state), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@db_blueprint.route("/api/behavioral_corpus", methods=["GET"])
def get_behavioral_corpus():
    """
    Return behavioral corpus for Psychology of AI Data analysis.
    Query params: project_name (optional), model_family (optional)
    """
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database not available"}), 503

    project_name  = request.args.get("project_name")
    model_family  = request.args.get("model_family")

    try:
        project_id = None
        if project_name:
            row = db.connect().execute(
                "SELECT project_id FROM projects WHERE name = ? LIMIT 1",
                (project_name,)
            ).fetchone()
            if row:
                project_id = row["project_id"]

        corpus = db.get_behavioral_corpus(
            project_id=project_id,
            model_family=model_family
        )
        return jsonify({
            "observations": corpus,
            "count": len(corpus)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@db_blueprint.route("/api/health", methods=["GET"])
def health():
    """Health check — confirms workspace DB endpoint is alive."""
    db = get_db()
    if not db:
        return jsonify({"status": "degraded", "db": False}), 200
    try:
        count = db.connect().execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]
        return jsonify({
            "status": "ok",
            "db": True,
            "sessions": count
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def _normalize_artifact_type(label: str) -> str:
    """Normalize artifact label to database artifact_type value."""
    label_lower = label.lower()
    if "work product" in label_lower:
        return "work_product"
    if "session log" in label_lower:
        return "session_log"
    if "final synthesis" in label_lower or "synthesis" in label_lower:
        return "final_synthesis"
    if "knowtext" in label_lower:
        return "knowtext_snapshot"
    return "work_product"


# ─────────────────────────────────────────────
# STANDALONE RUNNER (for testing)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    standalone = Flask(__name__)
    standalone.register_blueprint(db_blueprint)
    init_db()
    port = int(os.environ.get("PORT", 5001))
    print(f"Workspace DB endpoint running on port {port}")
    print(f"Database: {DB_PATH}")
    print(f"Auth: {'enabled' if WORKSPACE_TOKEN else 'disabled (local dev)'}")
    standalone.run(host="0.0.0.0", port=port, debug=False)
