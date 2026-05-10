"""
Ontinuity Database Module
db.py

Sixteen-table SQLite schema for Ontinuity session persistence, behavioral
corpus, Projenius knowledge management, and multi-user storage.

Designed for SQLite now, Postgres-compatible for future migration.
All timestamps are ISO 8601 UTC strings. All IDs are TEXT (UUID or
timestamp-based). JSON fields store valid JSON strings.

Usage:
    from db import OntinuityDB
    db = OntinuityDB("ontinuity.db")
    db.init()

Install: no dependencies beyond Python stdlib sqlite3.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# ─────────────────────────────────────────────
# SCHEMA VERSION
# Increment when tables or columns change.
# ─────────────────────────────────────────────
SCHEMA_VERSION = "1.0.0"


def now_utc() -> str:
    """Current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def sanitize(text: Optional[str]) -> Optional[str]:
    """
    Strip problematic unicode characters before database writes.
    Mirrors the sanitize_content function in app.py.
    """
    if not text:
        return text
    replacements = {
        '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'",
        '\u2013': '-', '\u2014': '--',
        '\u2026': '...',
        '\u00a0': ' ',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


# ─────────────────────────────────────────────
# DDL — TABLE DEFINITIONS
# ─────────────────────────────────────────────

DDL = """

-- ── 1. SCHEMA VERSIONS ──────────────────────────────────────────────────────
-- Tracks database migrations. One row per schema version applied.
CREATE TABLE IF NOT EXISTS schema_versions (
    version_id    TEXT PRIMARY KEY,
    version       TEXT NOT NULL,
    applied_at    TEXT NOT NULL,
    notes         TEXT
);

-- ── 2. USERS ─────────────────────────────────────────────────────────────────
-- One row per Ontinuity user. Supports both personal and hosted deployments.
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    email         TEXT,
    plan          TEXT NOT NULL DEFAULT 'personal',
    -- plan: 'personal', 'free', 'pro', 'team'
    feature_flags TEXT,
    -- JSON: {"transcript_storage": true, "behavioral_corpus": true, ...}
    created_at    TEXT NOT NULL,
    last_active   TEXT
);

-- ── 3. STORAGE CONFIGS ───────────────────────────────────────────────────────
-- User-configurable storage endpoint. Decouples Railway app from storage layer.
CREATE TABLE IF NOT EXISTS storage_configs (
    config_id         TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    storage_type      TEXT NOT NULL,
    -- type: 'local_workspace', 's3', 'r2', 'supabase', 'postgres', 'custom'
    endpoint_url      TEXT,
    -- workspace server base URL or cloud storage endpoint
    auth_config       TEXT,
    -- JSON: credentials, tokens, bucket names (encrypted at rest recommended)
    is_active         BOOLEAN NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL,
    last_verified     TEXT
);

-- ── 4. MODEL REGISTRY ────────────────────────────────────────────────────────
-- Normalizes model identities for behavioral corpus analytics.
CREATE TABLE IF NOT EXISTS model_registry (
    model_id          TEXT PRIMARY KEY,
    model_string      TEXT NOT NULL UNIQUE,
    -- exact string used in API calls: 'qwen-3-235b-a22b-instruct-2507'
    provider          TEXT NOT NULL,
    -- 'anthropic', 'openai', 'cerebras', 'groq', 'google', 'custom'
    model_family      TEXT,
    -- 'llama', 'gpt', 'claude', 'qwen', 'gemini' — for cross-family analysis
    parameter_count   TEXT,
    -- human readable: '235B', '8B', '120B'
    context_window    INTEGER,
    -- tokens
    known_strengths   TEXT,
    -- JSON: ['structured_output', 'long_context', 'adversarial_review']
    first_seen        TEXT NOT NULL,
    last_seen         TEXT
);

-- ── 5. PROJECTS ──────────────────────────────────────────────────────────────
-- Top-level research program or engagement. Parent of all branches.
CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(user_id),
    name          TEXT NOT NULL,
    -- 'Stillpoint Physics', 'Ontinuity Driving System', 'AZZ Consulting'
    description   TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    -- 'active', 'paused', 'archived', 'complete'
    created_at    TEXT NOT NULL,
    updated_at    TEXT
);

-- ── 6. BRANCHES ──────────────────────────────────────────────────────────────
-- Research track within a project. Supports PURSUE BOTH fork tracking.
CREATE TABLE IF NOT EXISTS branches (
    branch_id            TEXT PRIMARY KEY,
    project_id           TEXT NOT NULL REFERENCES projects(project_id),
    user_id              TEXT NOT NULL REFERENCES users(user_id),
    name                 TEXT NOT NULL,
    -- 'main', 'wave_mechanics', 'field_theory', 'corner_detection'
    description          TEXT,
    parent_branch_id     TEXT REFERENCES branches(branch_id),
    -- NULL for project root branch
    fork_origin_session  TEXT,
    -- session_id that issued the PURSUE BOTH ruling creating this branch
    fork_origin_cycle    INTEGER,
    status               TEXT NOT NULL DEFAULT 'active',
    -- 'active', 'paused', 'archived', 'merged'
    created_at           TEXT NOT NULL,
    created_by_session   TEXT,
    updated_at           TEXT
);

-- ── 7. SESSION SERIES ────────────────────────────────────────────────────────
-- Groups sessions from the same operator sitting (New Session — Continue path).
-- Different from branch lineage: series = continuity of intent, not derivation.
CREATE TABLE IF NOT EXISTS session_series (
    series_id     TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(project_id),
    user_id       TEXT NOT NULL REFERENCES users(user_id),
    branch_id     TEXT NOT NULL REFERENCES branches(branch_id),
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    session_count INTEGER NOT NULL DEFAULT 0
);

-- ── 8. SESSIONS ──────────────────────────────────────────────────────────────
-- One row per Ontinuity session. Core behavioral corpus unit.
CREATE TABLE IF NOT EXISTS sessions (
    session_id              TEXT PRIMARY KEY,
    -- timestamp-based: '2026-05-10_18-34-38'
    user_id                 TEXT NOT NULL REFERENCES users(user_id),
    project_id              TEXT NOT NULL REFERENCES projects(project_id),
    branch_id               TEXT NOT NULL REFERENCES branches(branch_id),
    series_id               TEXT REFERENCES session_series(series_id),
    parent_session_id       TEXT REFERENCES sessions(session_id),
    -- NULL for branch root sessions

    -- Identity
    objective               TEXT,
    start_time              TEXT,
    end_time                TEXT,
    total_cycles            INTEGER,
    status                  TEXT NOT NULL DEFAULT 'complete',
    -- 'complete', 'failed', 'stopped', 'running'

    -- Model configuration
    model_a_id              TEXT REFERENCES model_registry(model_id),
    model_b_id              TEXT REFERENCES model_registry(model_id),
    model_c_id              TEXT REFERENCES model_registry(model_id),
    parietal_id             TEXT REFERENCES model_registry(model_id),
    projenius_id            TEXT REFERENCES model_registry(model_id),
    model_a_string          TEXT,
    -- preserve original string even if not in registry
    model_b_string          TEXT,
    model_c_string          TEXT,
    parietal_string         TEXT,
    projenius_string        TEXT,

    -- Distillation
    distillation_method     TEXT,
    -- 'parietal', 'projenius', 'chunked_parallel', 'failed'
    knowtext_version        TEXT,

    -- Behavioral corpus — aggregate fields
    friction_profile        TEXT,
    -- JSON array: [0, 1, 0, 2, 1, 0, ...] one value per cycle
    friction_reasons        TEXT,
    -- JSON array of reason strings, parallel to friction_profile
    challenge_count         INTEGER DEFAULT 0,
    uphold_count            INTEGER DEFAULT 0,
    reject_count            INTEGER DEFAULT 0,
    pursue_both_count       INTEGER DEFAULT 0,
    escalate_count          INTEGER DEFAULT 0,
    avg_friction_signal     REAL,
    signal_variance         REAL,
    peak_signal             INTEGER,
    cycles_to_first_challenge INTEGER,
    cycles_to_session_end   INTEGER,

    created_at              TEXT NOT NULL
);

-- ── 9. SESSION TRANSCRIPTS ───────────────────────────────────────────────────
-- Full session dialogue, one row per model turn.
-- Queryable by role, cycle, tag — enables targeted distillation chunking.
CREATE TABLE IF NOT EXISTS session_transcripts (
    turn_id           TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    cycle_number      INTEGER NOT NULL,
    turn_number       INTEGER NOT NULL,
    -- sequential within session, regardless of cycle
    role              TEXT NOT NULL,
    -- 'model_a', 'model_b', 'model_c', 'parietal', 'projenius',
    -- 'human', 'system', 'routing_client'
    content           TEXT,
    tag               TEXT,
    -- CONTINUE, CHALLENGE, CHECKPOINT, SESSION_END, ALIGNMENT_NEEDED
    friction_signal   INTEGER,
    -- Model C signal value for this cycle (NULL for non-Model-C turns)
    word_count        INTEGER,
    token_estimate    INTEGER,
    -- rough estimate: word_count * 1.3
    created_at        TEXT NOT NULL
);

-- ── 10. ARTIFACTS ────────────────────────────────────────────────────────────
-- Work products, session logs, syntheses, Knowtext snapshots.
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id       TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    artifact_type     TEXT NOT NULL,
    -- 'work_product', 'session_log', 'final_synthesis',
    -- 'knowtext_snapshot', 'intake_summary'
    content           TEXT,
    file_path         TEXT,
    -- workspace-relative path for disk-backed artifacts
    byte_size         INTEGER,
    created_at        TEXT NOT NULL
);

-- ── 11. KNOWTEXT VERSIONS ────────────────────────────────────────────────────
-- Every Knowtext snapshot with full provenance and parsed field storage.
CREATE TABLE IF NOT EXISTS knowtext_versions (
    version_id        TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    branch_id         TEXT NOT NULL REFERENCES branches(branch_id),
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    schema_version    TEXT NOT NULL,
    content_full      TEXT NOT NULL,
    -- complete raw Knowtext text
    field_identity    TEXT,
    field_frameworks  TEXT,
    field_questions   TEXT,
    field_valence     TEXT,
    field_delta_log   TEXT,
    field_corrections TEXT,
    field_climate     TEXT,
    -- each field parsed and stored separately for targeted querying
    distillation_method TEXT,
    -- which model/method produced this version
    created_at        TEXT NOT NULL
);

-- ── 12. ESTABLISHED RESULTS ──────────────────────────────────────────────────
-- The Established Results Ledger. Cross-session canonical truth registry.
-- Projenius SYNTHESIZE writes here. Projenius LEDGER_QUERY reads here.
CREATE TABLE IF NOT EXISTS established_results (
    result_id             TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES projects(project_id),
    branch_id             TEXT NOT NULL REFERENCES branches(branch_id),
    user_id               TEXT NOT NULL REFERENCES users(user_id),
    session_id            TEXT NOT NULL REFERENCES sessions(session_id),
    -- session that first established this result

    result_text           TEXT NOT NULL,
    -- verbatim, complete — never paraphrased
    confidence            TEXT NOT NULL DEFAULT 'PROVISIONAL',
    -- 'ESTABLISHED', 'PROVISIONAL', 'RETRACTED'
    notes                 TEXT,
    -- caveats, conditions, dependencies

    supporting_sessions   TEXT,
    -- JSON array of session_ids that independently confirmed this result
    confirmation_count    INTEGER NOT NULL DEFAULT 0,

    -- Retraction fields (NULL while active)
    retracted_by_session  TEXT REFERENCES sessions(session_id),
    retraction_grounds    TEXT,
    retracted_at          TEXT,

    established_at        TEXT NOT NULL,
    updated_at            TEXT
);

-- ── 13. PROJENIUS LEDGER OPERATIONS ─────────────────────────────────────────
-- Audit trail for every Established Results Ledger modification.
-- Answers: who changed what, when, and why.
CREATE TABLE IF NOT EXISTS projenius_ledger_operations (
    operation_id      TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    operation_type    TEXT NOT NULL,
    -- 'add', 'confirm', 'retract', 'confidence_upgrade',
    -- 'confidence_downgrade', 'notes_update'
    result_id         TEXT NOT NULL REFERENCES established_results(result_id),
    prior_confidence  TEXT,
    new_confidence    TEXT,
    justification     TEXT,
    projenius_model   TEXT,
    -- model string that ran the SYNTHESIZE function
    operation_at      TEXT NOT NULL
);

-- ── 14. CHALLENGE EVENTS ─────────────────────────────────────────────────────
-- Individual challenge and ruling records. Normalized from session logs.
-- Enables adjudicator bias calibration and cross-session ruling analytics.
CREATE TABLE IF NOT EXISTS challenge_events (
    event_id              TEXT PRIMARY KEY,
    session_id            TEXT NOT NULL REFERENCES sessions(session_id),
    user_id               TEXT NOT NULL REFERENCES users(user_id),
    cycle_number          INTEGER NOT NULL,
    challenged_claim      TEXT,
    grounds               TEXT,
    ruling                TEXT NOT NULL,
    -- 'UPHOLD', 'REJECT', 'PURSUE_BOTH', 'ESCALATE'
    ruling_justification  TEXT,
    ruling_model          TEXT,
    -- parietal model string that issued the ruling
    resolution_cycles     INTEGER,
    -- cycles elapsed between CHALLENGE tag and ruling
    -- 0 means ruled in same cycle, NULL means unresolved
    fork_branch_created   TEXT REFERENCES branches(branch_id),
    -- populated if PURSUE_BOTH created a new branch
    created_at            TEXT NOT NULL
);

-- ── 15. BEHAVIORAL OBSERVATIONS ──────────────────────────────────────────────
-- Psychology of AI Data corpus. One row per cycle per session.
-- Feeds cross-architecture replication of the sigmoid friction signal finding.
CREATE TABLE IF NOT EXISTS behavioral_observations (
    observation_id        TEXT PRIMARY KEY,
    session_id            TEXT NOT NULL REFERENCES sessions(session_id),
    user_id               TEXT NOT NULL REFERENCES users(user_id),
    cycle_number          INTEGER NOT NULL,

    -- Friction signal
    friction_signal       INTEGER NOT NULL,
    friction_reason       TEXT,

    -- Model A behavior
    model_a_tag           TEXT,
    model_a_word_count    INTEGER,
    model_a_token_est     INTEGER,
    model_a_hedging_count INTEGER,
    -- count of uncertainty markers: 'possibly', 'might', 'unclear', etc.
    model_a_certainty_count INTEGER,
    -- count of certainty markers: 'confirmed', 'established', 'proven', etc.

    -- Model B behavior
    model_b_tag           TEXT,
    model_b_word_count    INTEGER,
    model_b_token_est     INTEGER,
    model_b_challenge_issued BOOLEAN DEFAULT 0,

    -- Session state
    ambient_signal        INTEGER,
    cumulative_uphold_count INTEGER,
    cumulative_challenge_count INTEGER,
    session_cycle_ratio   REAL,
    -- cycle_number / expected_total — position within session arc

    -- Ruling (if challenge was issued this cycle)
    ruling_if_challenged  TEXT,

    created_at            TEXT NOT NULL
);

-- ── 16. INTAKE SESSIONS ──────────────────────────────────────────────────────
-- Problem discovery intake conversations. Origin record for consulting work.
-- Links to the project and sessions that emerged from the intake.
CREATE TABLE IF NOT EXISTS intake_sessions (
    intake_id         TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    project_id        TEXT REFERENCES projects(project_id),
    -- populated when intake leads to a project
    participant_name  TEXT,
    organization      TEXT,
    intake_model      TEXT,
    -- model that ran the intake conversation
    conversation      TEXT,
    -- full intake dialogue as JSON array of turns
    problem_summary   TEXT,
    -- extracted problem statement
    recommended_next  TEXT,
    -- Projenius-generated recommended first session objective
    status            TEXT NOT NULL DEFAULT 'complete',
    -- 'in_progress', 'complete', 'abandoned'
    created_at        TEXT NOT NULL,
    completed_at      TEXT
);

"""

# ─────────────────────────────────────────────
# INDEXES
# ─────────────────────────────────────────────

INDEXES = """

CREATE INDEX IF NOT EXISTS idx_sessions_user
    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_branch
    ON sessions(branch_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project
    ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_series
    ON sessions(series_id);

CREATE INDEX IF NOT EXISTS idx_transcripts_session
    ON session_transcripts(session_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_role
    ON session_transcripts(session_id, role);
CREATE INDEX IF NOT EXISTS idx_transcripts_cycle
    ON session_transcripts(session_id, cycle_number);

CREATE INDEX IF NOT EXISTS idx_artifacts_session
    ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type
    ON artifacts(artifact_type);

CREATE INDEX IF NOT EXISTS idx_knowtext_branch
    ON knowtext_versions(branch_id);
CREATE INDEX IF NOT EXISTS idx_knowtext_session
    ON knowtext_versions(session_id);

CREATE INDEX IF NOT EXISTS idx_results_branch
    ON established_results(branch_id);
CREATE INDEX IF NOT EXISTS idx_results_confidence
    ON established_results(confidence);
CREATE INDEX IF NOT EXISTS idx_results_project
    ON established_results(project_id);

CREATE INDEX IF NOT EXISTS idx_ledger_ops_session
    ON projenius_ledger_operations(session_id);
CREATE INDEX IF NOT EXISTS idx_ledger_ops_result
    ON projenius_ledger_operations(result_id);

CREATE INDEX IF NOT EXISTS idx_challenges_session
    ON challenge_events(session_id);
CREATE INDEX IF NOT EXISTS idx_challenges_ruling
    ON challenge_events(ruling);

CREATE INDEX IF NOT EXISTS idx_behavioral_session
    ON behavioral_observations(session_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_signal
    ON behavioral_observations(friction_signal);

CREATE INDEX IF NOT EXISTS idx_intake_user
    ON intake_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_intake_project
    ON intake_sessions(project_id);

"""


# ─────────────────────────────────────────────
# DATABASE CLASS
# ─────────────────────────────────────────────

class OntinuityDB:
    """
    Main database interface for Ontinuity.
    Usage:
        db = OntinuityDB("ontinuity.db")
        db.init()
    """

    def __init__(self, db_path: str = "ontinuity.db"):
        self.db_path = db_path
        self._conn = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init(self):
        """Create all tables and indexes. Safe to call on existing database."""
        conn = self.connect()
        conn.executescript(DDL)
        conn.executescript(INDEXES)
        conn.commit()
        self._record_schema_version()
        print(f"Ontinuity database initialized at {self.db_path} "
              f"(schema v{SCHEMA_VERSION})")

    def _record_schema_version(self):
        conn = self.connect()
        existing = conn.execute(
            "SELECT version FROM schema_versions WHERE version = ?",
            (SCHEMA_VERSION,)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO schema_versions
                   (version_id, version, applied_at, notes)
                   VALUES (?, ?, ?, ?)""",
                (new_id(), SCHEMA_VERSION, now_utc(),
                 "Initial sixteen-table schema.")
            )
            conn.commit()

    # ── INSERT HELPERS ─────────────────────────────────────────────────────

    def insert_user(self, display_name: str, email: str = None,
                    plan: str = "personal",
                    feature_flags: dict = None) -> str:
        user_id = new_id()
        flags = json.dumps(feature_flags or {
            "transcript_storage": True,
            "behavioral_corpus": True,
            "established_results": True
        })
        self.connect().execute(
            """INSERT INTO users
               (user_id, display_name, email, plan, feature_flags, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, display_name, email, plan, flags, now_utc())
        )
        self.connect().commit()
        return user_id

    def insert_model(self, model_string: str, provider: str,
                     model_family: str = None,
                     parameter_count: str = None,
                     context_window: int = None) -> str:
        """Insert model or return existing model_id if already registered."""
        existing = self.connect().execute(
            "SELECT model_id FROM model_registry WHERE model_string = ?",
            (model_string,)
        ).fetchone()
        if existing:
            self.connect().execute(
                "UPDATE model_registry SET last_seen = ? WHERE model_id = ?",
                (now_utc(), existing["model_id"])
            )
            self.connect().commit()
            return existing["model_id"]
        model_id = new_id()
        self.connect().execute(
            """INSERT INTO model_registry
               (model_id, model_string, provider, model_family,
                parameter_count, context_window, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (model_id, model_string, provider, model_family,
             parameter_count, context_window, now_utc(), now_utc())
        )
        self.connect().commit()
        return model_id

    def insert_project(self, user_id: str, name: str,
                       description: str = None) -> str:
        project_id = new_id()
        self.connect().execute(
            """INSERT INTO projects
               (project_id, user_id, name, description, status, created_at)
               VALUES (?, ?, ?, ?, 'active', ?)""",
            (project_id, user_id, name, description, now_utc())
        )
        self.connect().commit()
        return project_id

    def insert_branch(self, project_id: str, user_id: str,
                      name: str, description: str = None,
                      parent_branch_id: str = None,
                      fork_origin_session: str = None,
                      fork_origin_cycle: int = None) -> str:
        branch_id = new_id()
        self.connect().execute(
            """INSERT INTO branches
               (branch_id, project_id, user_id, name, description,
                parent_branch_id, fork_origin_session, fork_origin_cycle,
                status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
            (branch_id, project_id, user_id, name, description,
             parent_branch_id, fork_origin_session, fork_origin_cycle,
             now_utc())
        )
        self.connect().commit()
        return branch_id

    def insert_session(self, session_data: Dict[str, Any]) -> str:
        """
        Insert a completed session record.
        session_data keys mirror the sessions table columns.
        Required: session_id, user_id, project_id, branch_id
        """
        s = session_data
        self.connect().execute(
            """INSERT OR REPLACE INTO sessions (
                session_id, user_id, project_id, branch_id, series_id,
                parent_session_id, objective, start_time, end_time,
                total_cycles, status,
                model_a_id, model_b_id, model_c_id, parietal_id, projenius_id,
                model_a_string, model_b_string, model_c_string,
                parietal_string, projenius_string,
                distillation_method, knowtext_version,
                friction_profile, friction_reasons,
                challenge_count, uphold_count, reject_count,
                pursue_both_count, escalate_count,
                avg_friction_signal, signal_variance, peak_signal,
                cycles_to_first_challenge, cycles_to_session_end,
                created_at
            ) VALUES (
                :session_id, :user_id, :project_id, :branch_id,
                :series_id, :parent_session_id, :objective,
                :start_time, :end_time, :total_cycles, :status,
                :model_a_id, :model_b_id, :model_c_id,
                :parietal_id, :projenius_id,
                :model_a_string, :model_b_string, :model_c_string,
                :parietal_string, :projenius_string,
                :distillation_method, :knowtext_version,
                :friction_profile, :friction_reasons,
                :challenge_count, :uphold_count, :reject_count,
                :pursue_both_count, :escalate_count,
                :avg_friction_signal, :signal_variance, :peak_signal,
                :cycles_to_first_challenge, :cycles_to_session_end,
                :created_at
            )""",
            {
                "session_id": s.get("session_id"),
                "user_id": s.get("user_id"),
                "project_id": s.get("project_id"),
                "branch_id": s.get("branch_id"),
                "series_id": s.get("series_id"),
                "parent_session_id": s.get("parent_session_id"),
                "objective": sanitize(s.get("objective")),
                "start_time": s.get("start_time"),
                "end_time": s.get("end_time"),
                "total_cycles": s.get("total_cycles"),
                "status": s.get("status", "complete"),
                "model_a_id": s.get("model_a_id"),
                "model_b_id": s.get("model_b_id"),
                "model_c_id": s.get("model_c_id"),
                "parietal_id": s.get("parietal_id"),
                "projenius_id": s.get("projenius_id"),
                "model_a_string": s.get("model_a_string"),
                "model_b_string": s.get("model_b_string"),
                "model_c_string": s.get("model_c_string"),
                "parietal_string": s.get("parietal_string"),
                "projenius_string": s.get("projenius_string"),
                "distillation_method": s.get("distillation_method"),
                "knowtext_version": s.get("knowtext_version"),
                "friction_profile": json.dumps(s.get("friction_profile", [])),
                "friction_reasons": json.dumps(s.get("friction_reasons", [])),
                "challenge_count": s.get("challenge_count", 0),
                "uphold_count": s.get("uphold_count", 0),
                "reject_count": s.get("reject_count", 0),
                "pursue_both_count": s.get("pursue_both_count", 0),
                "escalate_count": s.get("escalate_count", 0),
                "avg_friction_signal": s.get("avg_friction_signal"),
                "signal_variance": s.get("signal_variance"),
                "peak_signal": s.get("peak_signal"),
                "cycles_to_first_challenge": s.get("cycles_to_first_challenge"),
                "cycles_to_session_end": s.get("cycles_to_session_end"),
                "created_at": s.get("created_at", now_utc()),
            }
        )
        self.connect().commit()
        return s["session_id"]

    def insert_transcript_turn(self, session_id: str, cycle_number: int,
                                turn_number: int, role: str, content: str,
                                tag: str = None,
                                friction_signal: int = None) -> str:
        turn_id = new_id()
        clean = sanitize(content) or ""
        word_count = len(clean.split())
        token_estimate = int(word_count * 1.3)
        self.connect().execute(
            """INSERT INTO session_transcripts (
                turn_id, session_id, cycle_number, turn_number,
                role, content, tag, friction_signal,
                word_count, token_estimate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, session_id, cycle_number, turn_number,
             role, clean, tag, friction_signal,
             word_count, token_estimate, now_utc())
        )
        self.connect().commit()
        return turn_id

    def insert_artifact(self, session_id: str, user_id: str,
                        artifact_type: str, content: str,
                        file_path: str = None) -> str:
        artifact_id = new_id()
        clean = sanitize(content)
        self.connect().execute(
            """INSERT INTO artifacts (
                artifact_id, session_id, user_id, artifact_type,
                content, file_path, byte_size, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (artifact_id, session_id, user_id, artifact_type,
             clean, file_path,
             len(clean.encode("utf-8")) if clean else 0,
             now_utc())
        )
        self.connect().commit()
        return artifact_id

    def insert_knowtext_version(self, session_id: str, branch_id: str,
                                 user_id: str, content_full: str,
                                 schema_version: str,
                                 distillation_method: str = None) -> str:
        version_id = new_id()
        clean = sanitize(content_full) or ""
        fields = _parse_knowtext_fields(clean)
        self.connect().execute(
            """INSERT INTO knowtext_versions (
                version_id, session_id, branch_id, user_id,
                schema_version, content_full,
                field_identity, field_frameworks, field_questions,
                field_valence, field_delta_log, field_corrections,
                field_climate, distillation_method, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (version_id, session_id, branch_id, user_id,
             schema_version, clean,
             fields.get("Identity"),
             fields.get("Active Frameworks"),
             fields.get("Open Questions"),
             fields.get("Valence Mapping"),
             fields.get("Delta Log"),
             fields.get("Correction History"),
             fields.get("Climate Notes"),
             distillation_method, now_utc())
        )
        self.connect().commit()
        return version_id

    def insert_established_result(self, project_id: str, branch_id: str,
                                   user_id: str, session_id: str,
                                   result_text: str,
                                   confidence: str = "PROVISIONAL",
                                   notes: str = None) -> str:
        result_id = new_id()
        self.connect().execute(
            """INSERT INTO established_results (
                result_id, project_id, branch_id, user_id, session_id,
                result_text, confidence, notes,
                supporting_sessions, confirmation_count, established_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (result_id, project_id, branch_id, user_id, session_id,
             sanitize(result_text), confidence, sanitize(notes),
             json.dumps([session_id]), now_utc())
        )
        self.connect().commit()
        self._log_ledger_operation(
            session_id=session_id, user_id=user_id,
            operation_type="add", result_id=result_id,
            prior_confidence=None, new_confidence=confidence,
            justification="Initial establishment."
        )
        return result_id

    def retract_result(self, result_id: str, session_id: str,
                       user_id: str, grounds: str):
        self.connect().execute(
            """UPDATE established_results
               SET confidence = 'RETRACTED',
                   retracted_by_session = ?,
                   retraction_grounds = ?,
                   retracted_at = ?,
                   updated_at = ?
               WHERE result_id = ?""",
            (session_id, sanitize(grounds), now_utc(), now_utc(), result_id)
        )
        self.connect().commit()
        self._log_ledger_operation(
            session_id=session_id, user_id=user_id,
            operation_type="retract", result_id=result_id,
            prior_confidence="ESTABLISHED", new_confidence="RETRACTED",
            justification=grounds
        )

    def confirm_result(self, result_id: str, session_id: str,
                       user_id: str):
        """Add a confirming session to an established result."""
        row = self.connect().execute(
            "SELECT supporting_sessions, confirmation_count, confidence "
            "FROM established_results WHERE result_id = ?",
            (result_id,)
        ).fetchone()
        if not row:
            return
        sessions = json.loads(row["supporting_sessions"] or "[]")
        if session_id not in sessions:
            sessions.append(session_id)
        new_count = row["confirmation_count"] + 1
        new_confidence = (
            "ESTABLISHED" if new_count >= 2 else row["confidence"]
        )
        self.connect().execute(
            """UPDATE established_results
               SET supporting_sessions = ?,
                   confirmation_count = ?,
                   confidence = ?,
                   updated_at = ?
               WHERE result_id = ?""",
            (json.dumps(sessions), new_count, new_confidence,
             now_utc(), result_id)
        )
        self.connect().commit()
        if new_confidence != row["confidence"]:
            self._log_ledger_operation(
                session_id=session_id, user_id=user_id,
                operation_type="confidence_upgrade", result_id=result_id,
                prior_confidence=row["confidence"],
                new_confidence=new_confidence,
                justification=f"Confirmed by {new_count} sessions."
            )

    def _log_ledger_operation(self, session_id: str, user_id: str,
                               operation_type: str, result_id: str,
                               prior_confidence: Optional[str],
                               new_confidence: Optional[str],
                               justification: str = None,
                               projenius_model: str = None):
        self.connect().execute(
            """INSERT INTO projenius_ledger_operations (
                operation_id, session_id, user_id, operation_type,
                result_id, prior_confidence, new_confidence,
                justification, projenius_model, operation_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id(), session_id, user_id, operation_type, result_id,
             prior_confidence, new_confidence,
             sanitize(justification), projenius_model, now_utc())
        )
        self.connect().commit()

    def insert_challenge_event(self, session_id: str, user_id: str,
                                cycle_number: int, challenged_claim: str,
                                grounds: str, ruling: str,
                                ruling_justification: str = None,
                                ruling_model: str = None,
                                resolution_cycles: int = None) -> str:
        event_id = new_id()
        self.connect().execute(
            """INSERT INTO challenge_events (
                event_id, session_id, user_id, cycle_number,
                challenged_claim, grounds, ruling, ruling_justification,
                ruling_model, resolution_cycles, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, session_id, user_id, cycle_number,
             sanitize(challenged_claim), sanitize(grounds), ruling,
             sanitize(ruling_justification), ruling_model,
             resolution_cycles, now_utc())
        )
        self.connect().commit()
        return event_id

    def insert_behavioral_observation(self, obs: Dict[str, Any]) -> str:
        observation_id = new_id()
        self.connect().execute(
            """INSERT INTO behavioral_observations (
                observation_id, session_id, user_id, cycle_number,
                friction_signal, friction_reason,
                model_a_tag, model_a_word_count, model_a_token_est,
                model_a_hedging_count, model_a_certainty_count,
                model_b_tag, model_b_word_count, model_b_token_est,
                model_b_challenge_issued,
                ambient_signal, cumulative_uphold_count,
                cumulative_challenge_count, session_cycle_ratio,
                ruling_if_challenged, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )""",
            (
                observation_id,
                obs.get("session_id"),
                obs.get("user_id"),
                obs.get("cycle_number"),
                obs.get("friction_signal"),
                obs.get("friction_reason"),
                obs.get("model_a_tag"),
                obs.get("model_a_word_count"),
                obs.get("model_a_token_est"),
                obs.get("model_a_hedging_count", 0),
                obs.get("model_a_certainty_count", 0),
                obs.get("model_b_tag"),
                obs.get("model_b_word_count"),
                obs.get("model_b_token_est"),
                int(obs.get("model_b_challenge_issued", False)),
                obs.get("ambient_signal"),
                obs.get("cumulative_uphold_count", 0),
                obs.get("cumulative_challenge_count", 0),
                obs.get("session_cycle_ratio"),
                obs.get("ruling_if_challenged"),
                now_utc()
            )
        )
        self.connect().commit()
        return observation_id

    def insert_intake_session(self, user_id: str, participant_name: str,
                               organization: str = None,
                               intake_model: str = None,
                               conversation: list = None,
                               problem_summary: str = None) -> str:
        intake_id = new_id()
        self.connect().execute(
            """INSERT INTO intake_sessions (
                intake_id, user_id, participant_name, organization,
                intake_model, conversation, problem_summary,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'complete', ?)""",
            (intake_id, user_id, participant_name, organization,
             intake_model,
             json.dumps(conversation or []),
             sanitize(problem_summary),
             now_utc())
        )
        self.connect().commit()
        return intake_id

    # ── QUERY HELPERS ──────────────────────────────────────────────────────

    def get_active_results(self, branch_id: str = None,
                           project_id: str = None,
                           confidence: str = None) -> List[Dict]:
        """Return active (non-retracted) established results."""
        query = """
            SELECT r.*, b.name as branch_name, p.name as project_name
            FROM established_results r
            JOIN branches b ON r.branch_id = b.branch_id
            JOIN projects p ON r.project_id = p.project_id
            WHERE r.confidence != 'RETRACTED'
        """
        params = []
        if branch_id:
            query += " AND r.branch_id = ?"
            params.append(branch_id)
        if project_id:
            query += " AND r.project_id = ?"
            params.append(project_id)
        if confidence:
            query += " AND r.confidence = ?"
            params.append(confidence)
        query += " ORDER BY r.established_at ASC"
        rows = self.connect().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_session_transcript(self, session_id: str,
                                roles: List[str] = None,
                                min_cycle: int = None,
                                max_cycle: int = None) -> List[Dict]:
        """Return transcript turns with optional filters for chunked distillation."""
        query = """
            SELECT * FROM session_transcripts
            WHERE session_id = ?
        """
        params = [session_id]
        if roles:
            placeholders = ",".join("?" * len(roles))
            query += f" AND role IN ({placeholders})"
            params.extend(roles)
        if min_cycle is not None:
            query += " AND cycle_number >= ?"
            params.append(min_cycle)
        if max_cycle is not None:
            query += " AND cycle_number <= ?"
            params.append(max_cycle)
        query += " ORDER BY turn_number ASC"
        rows = self.connect().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_challenge_cycles(self, session_id: str) -> List[Dict]:
        """Return only cycles where a challenge was issued. For Correction History distillation."""
        rows = self.connect().execute(
            """SELECT t.*, c.ruling, c.ruling_justification
               FROM session_transcripts t
               LEFT JOIN challenge_events c
                   ON c.session_id = t.session_id
                   AND c.cycle_number = t.cycle_number
               WHERE t.session_id = ?
               AND t.role IN ('model_b', 'parietal')
               AND t.tag IN ('CHALLENGE', 'UPHOLD', 'REJECT', 'PURSUE_BOTH')
               ORDER BY t.turn_number ASC""",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_high_friction_cycles(self, session_id: str,
                                  min_signal: int = 2) -> List[Dict]:
        """Return cycles above a friction threshold. For Climate Notes distillation."""
        rows = self.connect().execute(
            """SELECT * FROM session_transcripts
               WHERE session_id = ?
               AND friction_signal >= ?
               ORDER BY turn_number ASC""",
            (session_id, min_signal)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_behavioral_corpus(self, project_id: str = None,
                               model_family: str = None,
                               min_cycles: int = None) -> List[Dict]:
        """Return behavioral observations for Psychology of AI Data analysis."""
        query = """
            SELECT o.*, s.model_a_string, s.model_b_string,
                   s.model_c_string, s.total_cycles,
                   mr_a.model_family as model_a_family,
                   mr_b.model_family as model_b_family
            FROM behavioral_observations o
            JOIN sessions s ON o.session_id = s.session_id
            LEFT JOIN model_registry mr_a ON s.model_a_id = mr_a.model_id
            LEFT JOIN model_registry mr_b ON s.model_b_id = mr_b.model_id
            WHERE 1=1
        """
        params = []
        if project_id:
            query += " AND s.project_id = ?"
            params.append(project_id)
        if model_family:
            query += " AND mr_a.model_family = ?"
            params.append(model_family)
        if min_cycles:
            query += " AND s.total_cycles >= ?"
            params.append(min_cycles)
        query += " ORDER BY o.session_id, o.cycle_number ASC"
        rows = self.connect().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_project_state(self, project_id: str) -> Dict:
        """
        Return complete project state for Projenius ORIENT.
        Includes active branch summary, established results count,
        most recent session, and open questions from latest Knowtext.
        """
        project = dict(self.connect().execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,)
        ).fetchone() or {})

        branches = [dict(r) for r in self.connect().execute(
            """SELECT b.*, COUNT(s.session_id) as session_count
               FROM branches b
               LEFT JOIN sessions s ON b.branch_id = s.branch_id
               WHERE b.project_id = ? AND b.status = 'active'
               GROUP BY b.branch_id
               ORDER BY b.created_at ASC""",
            (project_id,)
        ).fetchall()]

        result_counts = dict(self.connect().execute(
            """SELECT confidence, COUNT(*) as count
               FROM established_results
               WHERE project_id = ? AND confidence != 'RETRACTED'
               GROUP BY confidence""",
            (project_id,)
        ).fetchall() or [])

        last_session = dict(self.connect().execute(
            """SELECT * FROM sessions
               WHERE project_id = ?
               ORDER BY start_time DESC LIMIT 1""",
            (project_id,)
        ).fetchone() or {})

        return {
            "project": project,
            "branches": branches,
            "result_counts": result_counts,
            "last_session": last_session,
        }


# ─────────────────────────────────────────────
# KNOWTEXT FIELD PARSER
# ─────────────────────────────────────────────

def _parse_knowtext_fields(content: str) -> Dict[str, str]:
    """
    Parse the seven Knowtext fields from a raw Knowtext document.
    Returns a dict keyed by field name. Missing fields return None.
    """
    field_names = [
        "Identity", "Active Frameworks", "Open Questions",
        "Valence Mapping", "Delta Log", "Correction History",
        "Climate Notes"
    ]
    fields = {}
    for i, name in enumerate(field_names):
        # Find this field's start
        pattern = rf'\*?\*?{re.escape(name)}\*?\*?\s*[:：]?\s*\n'
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            fields[name] = None
            continue
        start = match.end()
        # Find the next field's start or end of document
        end = len(content)
        for other in field_names[i+1:]:
            other_pattern = rf'\*?\*?{re.escape(other)}\*?\*?\s*[:：]?\s*\n'
            other_match = re.search(other_pattern, content[start:], re.IGNORECASE)
            if other_match:
                end = start + other_match.start()
                break
        fields[name] = content[start:end].strip() or None
    return fields


# ─────────────────────────────────────────────
# CLI INITIALIZATION
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "ontinuity.db"
    db = OntinuityDB(db_path)
    db.init()

    # Create default user for personal deployment
    user_id = db.insert_user(
        display_name="Patrick Killebrew",
        plan="personal"
    )
    print(f"Default user created: {user_id}")

    # Create default projects
    ods_id = db.insert_project(user_id, "Ontinuity Driving System",
        "Autonomous RC car with three-horizon control architecture.")
    stillpoint_id = db.insert_project(user_id, "Stillpoint Physics",
        "Cross-domain physics research program.")
    ontinuity_id = db.insert_project(user_id, "Ontinuity Platform",
        "The Ontinuity system itself — architecture, research, deployment.")

    # Create main branches for each project
    db.insert_branch(ods_id, user_id, "main",
        "Primary ODS development track.")
    db.insert_branch(stillpoint_id, user_id, "main",
        "Primary Stillpoint research track.")
    db.insert_branch(ontinuity_id, user_id, "main",
        "Primary Ontinuity platform track.")

    print(f"Projects created: ODS ({ods_id}), "
          f"Stillpoint ({stillpoint_id}), "
          f"Ontinuity ({ontinuity_id})")
    print("Database ready.")
