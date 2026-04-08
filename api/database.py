"""
Database layer for Lexavo — PostgreSQL (production) / SQLite (dev fallback).
All CRUD operations for users, lawyers, conversations, messages, subscriptions,
shield analyses, newsletters, alerts, proof cases, push tokens.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("database")

# ─── Database config ────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    log.info("Database: PostgreSQL")
else:
    _default_db = str(Path(__file__).parent.parent / "output" / "lexavo.db")
    DB_PATH = Path(os.getenv("LEXAVO_DB_PATH", _default_db))
    DB_DIR = DB_PATH.parent
    log.info(f"Database: SQLite ({DB_PATH})")

# ─── Placeholder: %s for PostgreSQL, ? for SQLite ───────────────────────────
PH = "%s" if USE_PG else "?"


def _get_conn():
    """Get a database connection (PostgreSQL or SQLite)."""
    if USE_PG:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = False
        return conn
    else:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _execute(conn, sql, params=None):
    """Execute a query, adapting cursor usage for PG vs SQLite."""
    if USE_PG:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur
    else:
        return conn.execute(sql, params or ())


def _fetchone(conn, sql, params=None) -> Optional[dict]:
    """Execute + fetchone, returns dict or None."""
    cur = _execute(conn, sql, params)
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def _fetchall(conn, sql, params=None) -> list:
    """Execute + fetchall, returns list of dicts."""
    cur = _execute(conn, sql, params)
    return [dict(r) for r in cur.fetchall()]


def _insert_returning_id(conn, sql, params=None) -> int:
    """INSERT and return the new row's ID. Uses RETURNING for PG, lastrowid for SQLite."""
    if USE_PG:
        cur = conn.cursor()
        cur.execute(sql + " RETURNING id", params or ())
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT n'a retourné aucune ligne")
        return row["id"]
    else:
        cur = conn.execute(sql, params or ())
        return cur.lastrowid


def _integrity_error():
    """Return the IntegrityError class for the active DB backend."""
    return psycopg2.IntegrityError if USE_PG else sqlite3.IntegrityError


def _now_sql():
    """Return SQL expression for current timestamp."""
    return "CURRENT_TIMESTAMP"


# ─── Init ────────────────────────────────────────────────────────────────────

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'fr',
    region TEXT DEFAULT NULL,
    profession TEXT DEFAULT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lawyers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    bar TEXT NOT NULL,
    specialties TEXT NOT NULL DEFAULT '[]',
    email TEXT,
    phone TEXT,
    city TEXT NOT NULL,
    description TEXT,
    rating REAL DEFAULT 0.0,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources_json TEXT DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'basic', 'pro', 'business', 'firm_s', 'firm_m', 'enterprise')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'canceled', 'past_due', 'trialing')),
    current_period_start TEXT,
    current_period_end TEXT,
    questions_used INTEGER NOT NULL DEFAULT 0,
    questions_reset_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shield_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    contract_type TEXT,
    verdict TEXT NOT NULL,
    summary TEXT NOT NULL,
    clauses_json TEXT NOT NULL DEFAULT '[]',
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    domains TEXT NOT NULL DEFAULT '[]',
    token TEXT NOT NULL,
    confirmed BOOLEAN DEFAULT FALSE,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emergency_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    description TEXT NOT NULL,
    phone TEXT NOT NULL,
    city TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'assigned', 'completed', 'cancelled')),
    price_cents INTEGER NOT NULL DEFAULT 4900,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    domains TEXT NOT NULL DEFAULT '[]',
    frequency TEXT NOT NULL DEFAULT 'daily' CHECK(frequency IN ('realtime', 'daily', 'weekly')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proof_cases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proof_entries (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES proof_cases(id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL DEFAULT 'note' CHECK(entry_type IN ('note', 'document', 'photo', 'email', 'sms', 'testimony')),
    content TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS push_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{"legal_alerts":true,"deadlines":true,"news":false,"subscription":true}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, token)
);

CREATE TABLE IF NOT EXISTS beta_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    milestone TEXT NOT NULL,
    email_to TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    error_msg TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, milestone)
);

CREATE TABLE IF NOT EXISTS audit_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT,
    company_type TEXT NOT NULL DEFAULT 'srl',
    score INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch TEXT NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    streak_count INTEGER NOT NULL DEFAULT 0,
    streak_last_date TEXT,
    total_quizzes INTEGER NOT NULL DEFAULT 0,
    total_correct INTEGER NOT NULL DEFAULT 0,
    best_score INTEGER NOT NULL DEFAULT 0,
    total_flashcards INTEGER NOT NULL DEFAULT 0,
    total_case_studies INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, branch)
);

CREATE TABLE IF NOT EXISTS student_badges (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id TEXT NOT NULL,
    badge_name TEXT NOT NULL,
    badge_emoji TEXT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, badge_id)
);

CREATE TABLE IF NOT EXISTS student_quiz_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch TEXT NOT NULL,
    mode TEXT NOT NULL,
    score INTEGER,
    total_questions INTEGER,
    difficulty TEXT DEFAULT 'moyen',
    xp_earned INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_flashcard_srs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch TEXT NOT NULL,
    card_hash TEXT NOT NULL,
    box INTEGER NOT NULL DEFAULT 1,
    next_review_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    times_correct INTEGER NOT NULL DEFAULT 0,
    times_wrong INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, card_hash)
);

CREATE TABLE IF NOT EXISTS student_groups (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

CREATE TABLE IF NOT EXISTS student_lms_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL DEFAULT 'moodle',
    site_url TEXT NOT NULL,
    token TEXT NOT NULL,
    site_name TEXT,
    user_fullname TEXT,
    moodle_user_id INTEGER,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, platform)
);

CREATE TABLE IF NOT EXISTS student_lms_courses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id INTEGER NOT NULL REFERENCES student_lms_connections(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL,
    course_name TEXT NOT NULL,
    course_shortname TEXT,
    imported_content TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, course_id)
);

CREATE TABLE IF NOT EXISTS student_shared_notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    author_name TEXT DEFAULT 'Anonyme',
    is_anonymous BOOLEAN DEFAULT TRUE,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    university TEXT,
    study_year TEXT,
    file_type TEXT DEFAULT 'text',
    content_text TEXT,
    file_url TEXT,
    downloads INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_PG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_lawyers_city ON lawyers(city);
CREATE INDEX IF NOT EXISTS idx_shield_user ON shield_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_emergency_user ON emergency_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_prefs_user ON alert_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_proof_cases_user ON proof_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_proof_entries_case ON proof_entries(case_id);
CREATE INDEX IF NOT EXISTS idx_push_tokens_user ON push_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_beta_notif_user ON beta_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_beta_notif_milestone ON beta_notifications(milestone);
CREATE INDEX IF NOT EXISTS idx_beta_notif_status ON beta_notifications(status);
CREATE INDEX IF NOT EXISTS idx_audit_reports_user ON audit_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_student_progress_user ON student_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_student_badges_user ON student_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_student_quiz_history_user ON student_quiz_history(user_id);
CREATE INDEX IF NOT EXISTS idx_student_quiz_history_branch ON student_quiz_history(branch);
CREATE INDEX IF NOT EXISTS idx_student_flashcard_srs_user ON student_flashcard_srs(user_id);
CREATE INDEX IF NOT EXISTS idx_student_flashcard_srs_review ON student_flashcard_srs(user_id, next_review_at);
CREATE INDEX IF NOT EXISTS idx_student_groups_code ON student_groups(code);
CREATE INDEX IF NOT EXISTS idx_student_group_members_group ON student_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_student_group_members_user ON student_group_members(user_id);
"""

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'fr' CHECK(language IN ('fr', 'nl', 'en')),
    region TEXT DEFAULT NULL,
    profession TEXT DEFAULT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS lawyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, bar TEXT NOT NULL, specialties TEXT NOT NULL DEFAULT '[]',
    email TEXT, phone TEXT, city TEXT NOT NULL, description TEXT,
    rating REAL DEFAULT 0.0, verified INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, title TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL, sources_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'basic', 'pro', 'business', 'firm_s', 'firm_m', 'enterprise')),
    stripe_customer_id TEXT, stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'canceled', 'past_due', 'trialing')),
    current_period_start TEXT, current_period_end TEXT,
    questions_used INTEGER NOT NULL DEFAULT 0,
    questions_reset_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS shield_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, contract_type TEXT,
    verdict TEXT NOT NULL, summary TEXT NOT NULL,
    clauses_json TEXT NOT NULL DEFAULT '[]', sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL, domains TEXT NOT NULL DEFAULT '[]',
    token TEXT NOT NULL, confirmed INTEGER DEFAULT 0,
    subscribed_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS emergency_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    description TEXT NOT NULL, phone TEXT NOT NULL, city TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'assigned', 'completed', 'cancelled')),
    price_cents INTEGER NOT NULL DEFAULT 4900,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS alert_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE, domains TEXT NOT NULL DEFAULT '[]',
    frequency TEXT NOT NULL DEFAULT 'daily' CHECK(frequency IN ('realtime', 'daily', 'weekly')),
    enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS proof_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, title TEXT NOT NULL, description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed', 'archived')),
    created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS proof_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    entry_type TEXT NOT NULL DEFAULT 'note' CHECK(entry_type IN ('note', 'document', 'photo', 'email', 'sms', 'testimony')),
    content TEXT NOT NULL, metadata_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (case_id) REFERENCES proof_cases(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS push_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, token TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{"legal_alerts":true,"deadlines":true,"news":false,"subscription":true}',
    created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, token)
);

CREATE TABLE IF NOT EXISTS beta_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    milestone TEXT NOT NULL,
    email_to TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    error_msg TEXT,
    sent_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, milestone)
);

CREATE TABLE IF NOT EXISTS audit_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_name TEXT,
    company_type TEXT NOT NULL DEFAULT 'srl',
    score INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    branch TEXT NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    streak_count INTEGER NOT NULL DEFAULT 0,
    streak_last_date TEXT,
    total_quizzes INTEGER NOT NULL DEFAULT 0,
    total_correct INTEGER NOT NULL DEFAULT 0,
    best_score INTEGER NOT NULL DEFAULT 0,
    total_flashcards INTEGER NOT NULL DEFAULT 0,
    total_case_studies INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, branch)
);

CREATE TABLE IF NOT EXISTS student_badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    badge_id TEXT NOT NULL,
    badge_name TEXT NOT NULL,
    badge_emoji TEXT NOT NULL,
    earned_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, badge_id)
);

CREATE TABLE IF NOT EXISTS student_quiz_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    branch TEXT NOT NULL,
    mode TEXT NOT NULL,
    score INTEGER,
    total_questions INTEGER,
    difficulty TEXT DEFAULT 'moyen',
    xp_earned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_flashcard_srs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    branch TEXT NOT NULL,
    card_hash TEXT NOT NULL,
    box INTEGER NOT NULL DEFAULT 1,
    next_review_at TEXT NOT NULL DEFAULT (datetime('now')),
    times_correct INTEGER NOT NULL DEFAULT 0,
    times_wrong INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, card_hash)
);

CREATE TABLE IF NOT EXISTS student_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS student_group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (group_id) REFERENCES student_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(group_id, user_id)
);

CREATE TABLE IF NOT EXISTS student_lms_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    platform TEXT NOT NULL DEFAULT 'moodle',
    site_url TEXT NOT NULL,
    token TEXT NOT NULL,
    site_name TEXT,
    user_fullname TEXT,
    moodle_user_id INTEGER,
    connected_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, platform)
);

CREATE TABLE IF NOT EXISTS student_lms_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    connection_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    course_name TEXT NOT NULL,
    course_shortname TEXT,
    imported_content TEXT,
    synced_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (connection_id) REFERENCES student_lms_connections(id) ON DELETE CASCADE,
    UNIQUE(user_id, course_id)
);

CREATE TABLE IF NOT EXISTS student_shared_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    author_name TEXT DEFAULT 'Anonyme',
    is_anonymous INTEGER DEFAULT 1,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    university TEXT,
    study_year TEXT,
    file_type TEXT DEFAULT 'text',
    content_text TEXT,
    file_url TEXT,
    downloads INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
""" + _PG_INDEXES


def init_db():
    """Create all tables if they don't exist."""
    conn = _get_conn()
    try:
        if USE_PG:
            cur = conn.cursor()
            for stmt in (_PG_SCHEMA + _PG_INDEXES).split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt + ";")
            conn.commit()
        else:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
        # Migration safe : ajouter colonnes si absentes
        _safe_add_column(conn, "users", "region", "TEXT DEFAULT NULL")
        _safe_add_column(conn, "users", "profession", "TEXT DEFAULT NULL")
        _safe_add_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
        # emergency_requests : colonne paid si absente (ancien schema)
        _safe_add_column(conn, "emergency_requests", "paid", "BOOLEAN NOT NULL DEFAULT FALSE")
        log.info("Database schema initialized")
    finally:
        conn.close()


def _safe_add_column(conn, table: str, column: str, col_type: str):
    """Ajoute une colonne si elle n'existe pas encore (safe pour migration)."""
    try:
        if USE_PG:
            cur = conn.cursor()
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type};")
            conn.commit()
        else:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
            conn.commit()
    except Exception:
        # Colonne existe deja — ignorer
        try:
            conn.rollback()
        except Exception:
            pass


# ─── Users CRUD ──────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, name: str, language: str = "fr") -> dict:
    conn = _get_conn()
    try:
        # Le premier utilisateur inscrit (id=1) recoit le role admin
        count_row = _fetchone(conn, "SELECT COUNT(*) AS cnt FROM users")
        role = "admin" if (count_row and count_row["cnt"] == 0) else "user"
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO users (email, password_hash, name, language, role) VALUES ({PH}, {PH}, {PH}, {PH}, {PH})",
            (email, password_hash, name, language, role),
        )
        conn.commit()
        return get_user_by_id(new_id)
    except _integrity_error():
        conn.rollback()
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT id, email, name, language, role, created_at FROM users WHERE id = {PH}", (user_id,))
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(
            conn,
            f"SELECT id, email, password_hash, name, language, role, created_at FROM users WHERE email = {PH}",
            (email,),
        )
    finally:
        conn.close()


# ─── Lawyers CRUD ────────────────────────────────────────────────────────────

def create_lawyer(name: str, bar: str, specialties: list, email: str, phone: str,
                  city: str, description: str, rating: float = 0.0, verified: bool = False) -> dict:
    conn = _get_conn()
    try:
        v = verified if USE_PG else int(verified)
        new_id = _insert_returning_id(
            conn,
            f"""INSERT INTO lawyers (name, bar, specialties, email, phone, city, description, rating, verified)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
            (name, bar, json.dumps(specialties, ensure_ascii=False), email, phone, city, description, rating, v),
        )
        conn.commit()
        return get_lawyer_by_id(new_id)
    finally:
        conn.close()


def get_lawyer_by_id(lawyer_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        d = _fetchone(conn, f"SELECT * FROM lawyers WHERE id = {PH}", (lawyer_id,))
        if not d:
            return None
        d["specialties"] = json.loads(d["specialties"])
        d["verified"] = bool(d["verified"])
        return d
    finally:
        conn.close()


def list_lawyers(city: Optional[str] = None, specialty: Optional[str] = None, language: Optional[str] = None) -> list:
    conn = _get_conn()
    try:
        query = "SELECT * FROM lawyers WHERE 1=1"
        params = []
        if city:
            query += f" AND LOWER(city) = LOWER({PH})"
            params.append(city)
        if specialty:
            query += f" AND LOWER(specialties) LIKE LOWER({PH})"
            params.append(f"%{specialty}%")
        query += " ORDER BY rating DESC, name ASC"
        rows = _fetchall(conn, query, params)
        for d in rows:
            d["specialties"] = json.loads(d["specialties"])
            d["verified"] = bool(d["verified"])
        return rows
    finally:
        conn.close()


def count_lawyers() -> int:
    conn = _get_conn()
    try:
        row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM lawyers")
        return row["cnt"] if row else 0
    finally:
        conn.close()


# ─── Conversations CRUD ─────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO conversations (user_id, title) VALUES ({PH}, {PH})",
            (user_id, title),
        )
        conn.commit()
        return get_conversation_by_id(new_id)
    finally:
        conn.close()


def get_conversation_by_id(conversation_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM conversations WHERE id = {PH}", (conversation_id,))
    finally:
        conn.close()


def list_conversations(user_id: int) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM conversations WHERE user_id = {PH} ORDER BY created_at DESC", (user_id,))
    finally:
        conn.close()


# ─── Messages CRUD ──────────────────────────────────────────────────────────

def create_message(conversation_id: int, role: str, content: str, sources_json: str = "[]") -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO messages (conversation_id, role, content, sources_json) VALUES ({PH}, {PH}, {PH}, {PH})",
            (conversation_id, role, content, sources_json),
        )
        conn.commit()
        return get_message_by_id(new_id)
    finally:
        conn.close()


def get_message_by_id(message_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        d = _fetchone(conn, f"SELECT * FROM messages WHERE id = {PH}", (message_id,))
        if d:
            try:
                d["sources_json"] = json.loads(d["sources_json"])
            except (json.JSONDecodeError, TypeError):
                d["sources_json"] = []
        return d
    finally:
        conn.close()


def list_messages(conversation_id: int) -> list:
    conn = _get_conn()
    try:
        rows = _fetchall(conn, f"SELECT * FROM messages WHERE conversation_id = {PH} ORDER BY created_at ASC", (conversation_id,))
        for d in rows:
            try:
                d["sources_json"] = json.loads(d["sources_json"])
            except (json.JSONDecodeError, TypeError):
                d["sources_json"] = []
        return rows
    finally:
        conn.close()


# ─── Subscriptions CRUD ────────────────────────────────────────────────────

def get_subscription(user_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = _fetchone(conn, f"SELECT * FROM subscriptions WHERE user_id = {PH}", (user_id,))
        if row:
            return row
        _execute(conn, f"INSERT INTO subscriptions (user_id, plan) VALUES ({PH}, 'free')", (user_id,))
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM subscriptions WHERE user_id = {PH}", (user_id,))
    finally:
        conn.close()


def update_subscription(user_id: int, plan: str, stripe_customer_id: Optional[str] = None,
                        stripe_subscription_id: Optional[str] = None, status: str = "active",
                        current_period_start: Optional[str] = None, current_period_end: Optional[str] = None) -> Optional[dict]:
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT id FROM subscriptions WHERE user_id = {PH}", (user_id,))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if existing:
            _execute(conn, f"""UPDATE subscriptions
                SET plan = {PH}, stripe_customer_id = COALESCE({PH}, stripe_customer_id),
                    stripe_subscription_id = COALESCE({PH}, stripe_subscription_id),
                    status = {PH}, current_period_start = COALESCE({PH}, current_period_start),
                    current_period_end = COALESCE({PH}, current_period_end), updated_at = {PH}
                WHERE user_id = {PH}""",
                (plan, stripe_customer_id, stripe_subscription_id, status,
                 current_period_start, current_period_end, now, user_id))
        else:
            _execute(conn, f"""INSERT INTO subscriptions
                (user_id, plan, stripe_customer_id, stripe_subscription_id, status,
                 current_period_start, current_period_end)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
                (user_id, plan, stripe_customer_id, stripe_subscription_id, status,
                 current_period_start, current_period_end))
        conn.commit()
        return get_subscription(user_id)
    finally:
        conn.close()


def increment_question_count(user_id: int) -> dict:
    conn = _get_conn()
    try:
        sub = get_subscription(user_id)
        if not sub:
            return {"questions_used": 0, "limit": 5}
        reset_at = sub.get("questions_reset_at", "")
        now = datetime.now(timezone.utc)
        if reset_at:
            try:
                reset_str = str(reset_at)[:19]
                reset_date = datetime.strptime(reset_str, "%Y-%m-%d %H:%M:%S")
                days_since = (now - reset_date.replace(tzinfo=timezone.utc)).days
                if days_since >= 30:
                    _execute(conn, f"UPDATE subscriptions SET questions_used = 0, questions_reset_at = {PH} WHERE user_id = {PH}",
                             (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
                    conn.commit()
                    sub["questions_used"] = 0
            except (ValueError, TypeError):
                pass
        _execute(conn, f"UPDATE subscriptions SET questions_used = questions_used + 1, updated_at = {PH} WHERE user_id = {PH}",
                 (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        limits = {
            "free": 5, "basic": 50, "pro": -1, "business": -1,
            "firm_s": -1, "firm_m": -1, "enterprise": -1, "cabinet": -1,
        }
        plan = sub.get("plan", "free")
        return {"questions_used": sub["questions_used"] + 1, "limit": limits.get(plan, 5), "plan": plan}
    finally:
        conn.close()


def get_subscription_by_stripe_customer(stripe_customer_id: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM subscriptions WHERE stripe_customer_id = {PH}", (stripe_customer_id,))
    finally:
        conn.close()


# ─── Shield CRUD ────────────────────────────────────────────────────────────

def save_shield_analysis(user_id: int, contract_type: str, verdict: str,
                         summary: str, clauses_json: str, sources_json: str) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"""INSERT INTO shield_analyses (user_id, contract_type, verdict, summary, clauses_json, sources_json)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
            (user_id, contract_type, verdict, summary, clauses_json, sources_json),
        )
        conn.commit()
        return get_shield_analysis(new_id)
    finally:
        conn.close()


def get_shield_analysis(analysis_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM shield_analyses WHERE id = {PH}", (analysis_id,))
    finally:
        conn.close()


def list_shield_analyses(user_id: int, limit: int = 20) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM shield_analyses WHERE user_id = {PH} ORDER BY created_at DESC LIMIT {PH}", (user_id, limit))
    finally:
        conn.close()


# ─── Newsletter CRUD ────────────────────────────────────────────────────────

def subscribe_newsletter(email: str, domains: list) -> dict:
    import secrets as _secrets
    token = _secrets.token_urlsafe(32)
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO newsletter_subscribers (email, domains, token, confirmed) VALUES ({PH}, {PH}, {PH}, {PH})",
            (email, json.dumps(domains, ensure_ascii=False), token, False if USE_PG else 0),
        )
        conn.commit()
        d = _fetchone(conn, f"SELECT * FROM newsletter_subscribers WHERE id = {PH}", (new_id,))
        if d:
            d["domains"] = json.loads(d["domains"])
            d["confirmed"] = bool(d["confirmed"])
        return d
    except _integrity_error():
        conn.rollback()
        d = _fetchone(conn, f"SELECT * FROM newsletter_subscribers WHERE email = {PH}", (email,))
        if d:
            d["domains"] = json.loads(d["domains"])
            d["confirmed"] = bool(d["confirmed"])
        return d
    finally:
        conn.close()


def unsubscribe_newsletter(token: str) -> bool:
    conn = _get_conn()
    try:
        cur = _execute(conn, f"DELETE FROM newsletter_subscribers WHERE token = {PH}", (token,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_confirmed_subscribers() -> list:
    conn = _get_conn()
    try:
        rows = _fetchall(conn, f"SELECT * FROM newsletter_subscribers WHERE confirmed = {PH} ORDER BY subscribed_at DESC",
                         (True if USE_PG else 1,))
        for d in rows:
            d["domains"] = json.loads(d["domains"])
            d["confirmed"] = bool(d["confirmed"])
        return rows
    finally:
        conn.close()


# ─── Push Tokens ──────────────────────────────────────────────────────────────

def save_push_token(user_id: int, token: str) -> None:
    conn = _get_conn()
    try:
        if USE_PG:
            _execute(conn,
                f"""INSERT INTO push_tokens (user_id, token, updated_at) VALUES ({PH}, {PH}, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, token) DO UPDATE SET updated_at = CURRENT_TIMESTAMP""",
                (user_id, token))
        else:
            _execute(conn,
                "INSERT INTO push_tokens (user_id, token, updated_at) VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(user_id, token) DO UPDATE SET updated_at = datetime('now')",
                (user_id, token))
        conn.commit()
    finally:
        conn.close()


def update_push_preferences(user_id: int, token: str, preferences: dict) -> None:
    conn = _get_conn()
    try:
        if USE_PG:
            _execute(conn, f"UPDATE push_tokens SET preferences = {PH}, updated_at = CURRENT_TIMESTAMP WHERE user_id = {PH} AND token = {PH}",
                     (json.dumps(preferences), user_id, token))
        else:
            _execute(conn, "UPDATE push_tokens SET preferences = ?, updated_at = datetime('now') WHERE user_id = ? AND token = ?",
                     (json.dumps(preferences), user_id, token))
        conn.commit()
    finally:
        conn.close()


def get_push_tokens_for_user(user_id: int) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM push_tokens WHERE user_id = {PH}", (user_id,))
    finally:
        conn.close()


# ─── Alert Preferences CRUD ────────────────────────────────────────────────

def get_alert_preferences(user_id: int) -> dict:
    conn = _get_conn()
    try:
        row = _fetchone(conn, f"SELECT * FROM alert_preferences WHERE user_id = {PH}", (user_id,))
        if row:
            row["domains"] = json.loads(row["domains"])
            row["enabled"] = bool(row["enabled"])
            return row
        _execute(conn, f"INSERT INTO alert_preferences (user_id) VALUES ({PH})", (user_id,))
        conn.commit()
        return get_alert_preferences(user_id)
    finally:
        conn.close()


def update_alert_preferences(user_id: int, domains: list = None, frequency: str = None, enabled: bool = None) -> dict:
    conn = _get_conn()
    try:
        get_alert_preferences(user_id)
        parts, params = [], []
        if domains is not None:
            parts.append(f"domains = {PH}")
            params.append(json.dumps(domains, ensure_ascii=False))
        if frequency is not None:
            parts.append(f"frequency = {PH}")
            params.append(frequency)
        if enabled is not None:
            parts.append(f"enabled = {PH}")
            params.append(enabled if USE_PG else int(enabled))
        if parts:
            parts.append("updated_at = CURRENT_TIMESTAMP" if USE_PG else "updated_at = datetime('now')")
            params.append(user_id)
            _execute(conn, f"UPDATE alert_preferences SET {', '.join(parts)} WHERE user_id = {PH}", params)
            conn.commit()
        return get_alert_preferences(user_id)
    finally:
        conn.close()


# ─── Proof Cases CRUD ───────────────────────────────────────────────────────

def create_proof_case(user_id: int, title: str, description: str = None) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO proof_cases (user_id, title, description) VALUES ({PH}, {PH}, {PH})",
            (user_id, title, description),
        )
        conn.commit()
        return get_proof_case(new_id)
    finally:
        conn.close()


def get_proof_case(case_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM proof_cases WHERE id = {PH}", (case_id,))
    finally:
        conn.close()


def list_proof_cases(user_id: int) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM proof_cases WHERE user_id = {PH} ORDER BY created_at DESC", (user_id,))
    finally:
        conn.close()


def add_proof_entry(case_id: int, entry_type: str, content: str, metadata: dict = None) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"INSERT INTO proof_entries (case_id, entry_type, content, metadata_json) VALUES ({PH}, {PH}, {PH}, {PH})",
            (case_id, entry_type, content, json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM proof_entries WHERE id = {PH}", (new_id,))
    finally:
        conn.close()


def list_proof_entries(case_id: int) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM proof_entries WHERE case_id = {PH} ORDER BY created_at ASC", (case_id,))
    finally:
        conn.close()


# ─── Backup ──────────────────────────────────────────────────────────────────

def backup_database(backup_dir: str = None) -> str:
    """Backup: pg_dump pour PostgreSQL, fichier copy pour SQLite."""
    if USE_PG:
        import subprocess
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = f"/tmp/lexavo_backup_{timestamp}.sql"
        subprocess.run(["pg_dump", DATABASE_URL, "-f", backup_path], check=True)
        return backup_path
    else:
        backup_dir = backup_dir or str(DB_DIR / "backups")
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = str(Path(backup_dir) / f"lexavo_backup_{timestamp}.db")
        conn = _get_conn()
        try:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            return backup_path
        finally:
            conn.close()


# ─── Emergency Requests CRUD ────────────────────────────────────────────────

def create_emergency_request(user_id: int, category: str, priority: str,
                              description: str, phone: str, city: str) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"""INSERT INTO emergency_requests (user_id, category, priority, description, phone, city)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
            (user_id, category, priority, description, phone, city),
        )
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM emergency_requests WHERE id = {PH}", (new_id,))
    finally:
        conn.close()


def list_emergency_requests(user_id: int) -> list:
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM emergency_requests WHERE user_id = {PH} ORDER BY created_at DESC", (user_id,))
    finally:
        conn.close()


def update_emergency_paid(emergency_id: int) -> None:
    conn = _get_conn()
    try:
        _execute(conn, f"UPDATE emergency_requests SET status = 'completed' WHERE id = {PH}", (emergency_id,))
        conn.commit()
    finally:
        conn.close()


# ─── Refresh Tokens CRUD ────────────────────────────────────────────────────

def save_refresh_token(user_id: int, token: str, expires_at: str) -> None:
    conn = _get_conn()
    try:
        _execute(conn, f"INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES ({PH}, {PH}, {PH})",
                 (user_id, token, expires_at))
        conn.commit()
    finally:
        conn.close()


def get_refresh_token(token: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM refresh_tokens WHERE token = {PH}", (token,))
    finally:
        conn.close()


def delete_refresh_token(token: str) -> bool:
    conn = _get_conn()
    try:
        cur = _execute(conn, f"DELETE FROM refresh_tokens WHERE token = {PH}", (token,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_user_refresh_tokens(user_id: int) -> None:
    conn = _get_conn()
    try:
        _execute(conn, f"DELETE FROM refresh_tokens WHERE user_id = {PH}", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ─── Password Reset Tokens ───────────────────────────────────────────────────

def create_password_reset_token(user_id: int, token: str, expires_at: str) -> None:
    conn = _get_conn()
    try:
        # Invalider les anciens tokens non utilisés pour cet utilisateur
        _used_false = "FALSE" if USE_PG else "0"
        _execute(conn, f"DELETE FROM password_reset_tokens WHERE user_id = {PH} AND used = {_used_false}", (user_id,))
        _execute(conn, f"INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES ({PH}, {PH}, {PH})",
                 (user_id, token, expires_at))
        conn.commit()
    finally:
        conn.close()


def get_password_reset_token(token: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM password_reset_tokens WHERE token = {PH}", (token,))
    finally:
        conn.close()


def mark_password_reset_token_used(token: str) -> None:
    conn = _get_conn()
    try:
        _used_true = "TRUE" if USE_PG else "1"
        _execute(conn, f"UPDATE password_reset_tokens SET used = {_used_true} WHERE token = {PH}", (token,))
        conn.commit()
    finally:
        conn.close()


def update_user_password(user_id: int, password_hash: str) -> None:
    conn = _get_conn()
    try:
        _execute(conn, f"UPDATE users SET password_hash = {PH} WHERE id = {PH}", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


# ─── Conversations DELETE ────────────────────────────────────────────────────

def delete_conversation(conversation_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = _execute(conn, f"DELETE FROM conversations WHERE id = {PH}", (conversation_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ─── Audit Reports CRUD ───────────────────────────────────────────────────

def save_audit_report(user_id: int, company_name: str, company_type: str,
                      score: int, verdict: str, report_json: str) -> dict:
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(
            conn,
            f"""INSERT INTO audit_reports (user_id, company_name, company_type, score, verdict, report_json)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
            (user_id, company_name, company_type, score, verdict, report_json),
        )
        conn.commit()
        return {"id": new_id}
    finally:
        conn.close()


def get_audit_reports(user_id: int) -> list:
    conn = _get_conn()
    try:
        if USE_PG:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, company_name, company_type, score, verdict, created_at "
                "FROM audit_reports WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
            cols = ["id", "company_name", "company_type", "score", "verdict", "created_at"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        else:
            cur = conn.execute(
                "SELECT id, company_name, company_type, score, verdict, created_at "
                "FROM audit_reports WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
            cols = ["id", "company_name", "company_type", "score", "verdict", "created_at"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


# ── User Context ──────────────────────────────────────────────
def get_user_context(user_id: int) -> dict:
    """Recuperer le contexte utilisateur (region, profession, langue)."""
    conn = _get_conn()
    try:
        row = _fetchone(conn, "SELECT region, profession, language FROM users WHERE id = %s" if USE_PG else "SELECT region, profession, language FROM users WHERE id = ?", (user_id,))
        if not row:
            return {"region": None, "profession": None, "language": "fr"}
        return {"region": row.get("region"), "profession": row.get("profession"), "language": row.get("language") or "fr"}
    finally:
        conn.close()


def update_user_context(user_id: int, region: str = None, profession: str = None, language: str = None) -> dict:
    """Mettre a jour le contexte utilisateur."""
    fields = []
    values = []
    if region is not None:
        fields.append("region")
        values.append(region)
    if profession is not None:
        fields.append("profession")
        values.append(profession)
    if language is not None:
        fields.append("language")
        values.append(language)
    if not fields:
        return get_user_context(user_id)

    conn = _get_conn()
    try:
        ph = "%s" if USE_PG else "?"
        set_clause = ", ".join(f"{f} = {ph}" for f in fields)
        values.append(user_id)
        _execute(conn, f"UPDATE users SET {set_clause} WHERE id = {ph}", tuple(values))
        conn.commit()
        return get_user_context(user_id)
    finally:
        conn.close()


# ─── Student Gamification CRUD ──────────────────────────────────────────────

def get_student_progress(user_id: int, branch: str = None) -> list:
    """Get student progress for all branches or a specific one."""
    conn = _get_conn()
    try:
        if branch:
            row = _fetchone(conn, f"SELECT * FROM student_progress WHERE user_id = {PH} AND branch = {PH}", (user_id, branch))
            return [row] if row else []
        return _fetchall(conn, f"SELECT * FROM student_progress WHERE user_id = {PH} ORDER BY xp DESC", (user_id,))
    finally:
        conn.close()


def upsert_student_progress(user_id: int, branch: str, xp_delta: int = 0,
                            quiz_done: int = 0, correct: int = 0, mode: str = "quiz") -> dict:
    """Insert or update student progress for a branch."""
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT * FROM student_progress WHERE user_id = {PH} AND branch = {PH}", (user_id, branch))
        if existing:
            new_xp = existing["xp"] + xp_delta
            new_level = max(1, new_xp // 500 + 1)
            new_quizzes = existing["total_quizzes"] + quiz_done
            new_correct = existing["total_correct"] + correct
            new_best = max(existing["best_score"], int((correct / max(quiz_done, 1)) * 100) if quiz_done > 0 else 0)
            fc_delta = 1 if mode == "flashcards" else 0
            cs_delta = 1 if mode == "case_study" else 0
            _execute(conn, f"""UPDATE student_progress
                SET xp = {PH}, level = {PH}, total_quizzes = {PH}, total_correct = {PH},
                    best_score = {PH}, total_flashcards = total_flashcards + {PH},
                    total_case_studies = total_case_studies + {PH},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {PH} AND branch = {PH}""",
                (new_xp, new_level, new_quizzes, new_correct, new_best, fc_delta, cs_delta, user_id, branch))
        else:
            score_pct = int((correct / max(quiz_done, 1)) * 100) if quiz_done > 0 else 0
            level = max(1, xp_delta // 500 + 1)
            fc = 1 if mode == "flashcards" else 0
            cs = 1 if mode == "case_study" else 0
            _execute(conn, f"""INSERT INTO student_progress
                (user_id, branch, xp, level, total_quizzes, total_correct, best_score, total_flashcards, total_case_studies)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
                (user_id, branch, xp_delta, level, quiz_done, correct, score_pct, fc, cs))
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM student_progress WHERE user_id = {PH} AND branch = {PH}", (user_id, branch)) or {}
    finally:
        conn.close()


def update_student_streak(user_id: int) -> dict:
    """Update streak: if last activity was yesterday, increment. Otherwise reset to 1."""
    conn = _get_conn()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
        rows = _fetchall(conn, f"SELECT DISTINCT streak_last_date, streak_count FROM student_progress WHERE user_id = {PH} LIMIT 1", (user_id,))
        if rows:
            last_date = (rows[0].get("streak_last_date") or "")[:10]
            current_streak = rows[0].get("streak_count", 0)
            if last_date == today:
                return {"streak_count": current_streak, "streak_last_date": today}
            elif last_date == yesterday:
                new_streak = current_streak + 1
            else:
                new_streak = 1
        else:
            new_streak = 1
        _execute(conn, f"UPDATE student_progress SET streak_count = {PH}, streak_last_date = {PH} WHERE user_id = {PH}",
                 (new_streak, today, user_id))
        conn.commit()
        return {"streak_count": new_streak, "streak_last_date": today}
    finally:
        conn.close()


def get_student_badges(user_id: int) -> list:
    """Get all badges earned by a user."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT badge_id, badge_name, badge_emoji, earned_at FROM student_badges WHERE user_id = {PH} ORDER BY earned_at DESC", (user_id,))
    finally:
        conn.close()


def award_student_badge(user_id: int, badge_id: str, badge_name: str, badge_emoji: str) -> bool:
    """Award a badge to a user. Returns True if newly awarded, False if already had it."""
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT id FROM student_badges WHERE user_id = {PH} AND badge_id = {PH}", (user_id, badge_id))
        if existing:
            return False
        _execute(conn, f"INSERT INTO student_badges (user_id, badge_id, badge_name, badge_emoji) VALUES ({PH}, {PH}, {PH}, {PH})",
                 (user_id, badge_id, badge_name, badge_emoji))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def save_quiz_history(user_id: int, branch: str, mode: str, score: int, total_questions: int,
                      difficulty: str = "moyen", xp_earned: int = 0) -> int:
    """Save a quiz/activity to history. Returns the new entry ID."""
    conn = _get_conn()
    try:
        new_id = _insert_returning_id(conn,
            f"INSERT INTO student_quiz_history (user_id, branch, mode, score, total_questions, difficulty, xp_earned) VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})",
            (user_id, branch, mode, score, total_questions, difficulty, xp_earned))
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_quiz_history(user_id: int, limit: int = 20) -> list:
    """Get recent quiz/activity history."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT * FROM student_quiz_history WHERE user_id = {PH} ORDER BY created_at DESC LIMIT {PH}", (user_id, limit))
    finally:
        conn.close()


def get_leaderboard(branch: str = None, limit: int = 20) -> list:
    """Get top users by total XP, optionally filtered by branch."""
    conn = _get_conn()
    try:
        if branch:
            return _fetchall(conn, f"""SELECT sp.user_id, u.name, sp.xp, sp.level
                FROM student_progress sp JOIN users u ON sp.user_id = u.id
                WHERE sp.branch = {PH} ORDER BY sp.xp DESC LIMIT {PH}""", (branch, limit))
        return _fetchall(conn, f"""SELECT sp.user_id, u.name, SUM(sp.xp) as total_xp, MAX(sp.level) as level
            FROM student_progress sp JOIN users u ON sp.user_id = u.id
            GROUP BY sp.user_id, u.name ORDER BY total_xp DESC LIMIT {PH}""", (limit,))
    finally:
        conn.close()


def get_weak_branches(user_id: int, limit: int = 3) -> list:
    """Get branches with lowest best_score for targeted revision."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"SELECT branch, best_score, xp, total_quizzes FROM student_progress WHERE user_id = {PH} AND total_quizzes > 0 ORDER BY best_score ASC LIMIT {PH}", (user_id, limit))
    finally:
        conn.close()


def get_student_total_xp(user_id: int) -> int:
    """Get total XP across all branches."""
    conn = _get_conn()
    try:
        row = _fetchone(conn, f"SELECT COALESCE(SUM(xp), 0) as total_xp FROM student_progress WHERE user_id = {PH}", (user_id,))
        return row["total_xp"] if row else 0
    finally:
        conn.close()


# ─── Flashcard SRS (Leitner) ───────────────────────────────────────────────

LEITNER_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}  # box → days

def get_due_flashcards(user_id: int, branch: str = None, limit: int = 20) -> list:
    """Get flashcards due for review (next_review_at <= now)."""
    conn = _get_conn()
    try:
        if branch:
            return _fetchall(conn, f"SELECT * FROM student_flashcard_srs WHERE user_id = {PH} AND branch = {PH} AND next_review_at <= CURRENT_TIMESTAMP ORDER BY box ASC, next_review_at ASC LIMIT {PH}", (user_id, branch, limit))
        return _fetchall(conn, f"SELECT * FROM student_flashcard_srs WHERE user_id = {PH} AND next_review_at <= CURRENT_TIMESTAMP ORDER BY box ASC, next_review_at ASC LIMIT {PH}", (user_id, limit))
    finally:
        conn.close()


def upsert_flashcard_srs(user_id: int, branch: str, card_hash: str, correct: bool) -> dict:
    """Update Leitner box for a flashcard. Correct → box+1, Wrong → box 1."""
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT * FROM student_flashcard_srs WHERE user_id = {PH} AND card_hash = {PH}", (user_id, card_hash))
        if existing:
            if correct:
                new_box = min(existing["box"] + 1, 5)
                tc = existing["times_correct"] + 1
                tw = existing["times_wrong"]
            else:
                new_box = 1
                tc = existing["times_correct"]
                tw = existing["times_wrong"] + 1
            interval_days = LEITNER_INTERVALS.get(new_box, 1)
            if USE_PG:
                next_review = f"CURRENT_TIMESTAMP + INTERVAL '{interval_days} days'"
            else:
                next_review = f"datetime('now', '+{interval_days} days')"
            _execute(conn, f"UPDATE student_flashcard_srs SET box = {PH}, next_review_at = {next_review}, times_correct = {PH}, times_wrong = {PH} WHERE id = {PH}",
                     (new_box, tc, tw, existing["id"]))
        else:
            interval_days = LEITNER_INTERVALS.get(1 if not correct else 2, 1)
            new_box = 1 if not correct else 2
            if USE_PG:
                next_review_val = f"CURRENT_TIMESTAMP + INTERVAL '{interval_days} days'"
            else:
                next_review_val = f"datetime('now', '+{interval_days} days')"
            _execute(conn, f"INSERT INTO student_flashcard_srs (user_id, branch, card_hash, box, next_review_at, times_correct, times_wrong) VALUES ({PH}, {PH}, {PH}, {PH}, {next_review_val}, {PH}, {PH})",
                     (user_id, branch, card_hash, new_box, 1 if correct else 0, 0 if correct else 1))
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM student_flashcard_srs WHERE user_id = {PH} AND card_hash = {PH}", (user_id, card_hash)) or {}
    finally:
        conn.close()


# ─── Student Groups CRUD ───────────────────────────────────────────────────

def create_student_group(name: str, user_id: int) -> dict:
    """Create a study group with a unique 6-char code. Creator auto-joins."""
    import random, string
    conn = _get_conn()
    try:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # Ensure unique
        while _fetchone(conn, f"SELECT id FROM student_groups WHERE code = {PH}", (code,)):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        group_id = _insert_returning_id(conn,
            f"INSERT INTO student_groups (name, code, created_by) VALUES ({PH}, {PH}, {PH})",
            (name, code, user_id))
        # Auto-join creator
        _execute(conn, f"INSERT INTO student_group_members (group_id, user_id) VALUES ({PH}, {PH})", (group_id, user_id))
        conn.commit()
        return {"id": group_id, "name": name, "code": code, "created_by": user_id}
    finally:
        conn.close()


def join_student_group(code: str, user_id: int) -> dict:
    """Join a group by code. Returns group info or None if not found."""
    conn = _get_conn()
    try:
        group = _fetchone(conn, f"SELECT * FROM student_groups WHERE code = {PH}", (code,))
        if not group:
            return None
        existing = _fetchone(conn, f"SELECT id FROM student_group_members WHERE group_id = {PH} AND user_id = {PH}", (group["id"], user_id))
        if not existing:
            _execute(conn, f"INSERT INTO student_group_members (group_id, user_id) VALUES ({PH}, {PH})", (group["id"], user_id))
            conn.commit()
        return dict(group)
    finally:
        conn.close()


def leave_student_group(group_id: int, user_id: int) -> bool:
    """Leave a group."""
    conn = _get_conn()
    try:
        _execute(conn, f"DELETE FROM student_group_members WHERE group_id = {PH} AND user_id = {PH}", (group_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


def get_user_groups(user_id: int) -> list:
    """Get all groups a user belongs to, with member count."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"""SELECT g.id, g.name, g.code, g.created_by,
            (SELECT COUNT(*) FROM student_group_members WHERE group_id = g.id) as member_count
            FROM student_groups g
            JOIN student_group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = {PH} ORDER BY g.name""", (user_id,))
    finally:
        conn.close()


def get_group_leaderboard(group_id: int) -> list:
    """Get leaderboard for a specific group."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"""SELECT u.id as user_id, u.name, COALESCE(SUM(sp.xp), 0) as total_xp, COALESCE(MAX(sp.level), 1) as level
            FROM student_group_members gm
            JOIN users u ON gm.user_id = u.id
            LEFT JOIN student_progress sp ON sp.user_id = u.id
            WHERE gm.group_id = {PH}
            GROUP BY u.id, u.name ORDER BY total_xp DESC""", (group_id,))
    finally:
        conn.close()


# ─── LMS Connections CRUD ─────────────────────────────────────────────────────

def save_lms_connection(user_id: int, platform: str, site_url: str, token: str,
                        site_name: str = '', user_fullname: str = '', moodle_user_id: int = None) -> dict:
    """Save or update an LMS connection (UPSERT on user_id+platform)."""
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT id FROM student_lms_connections WHERE user_id = {PH} AND platform = {PH}", (user_id, platform))
        if existing:
            _execute(conn, f"""UPDATE student_lms_connections
                SET site_url = {PH}, token = {PH}, site_name = {PH}, user_fullname = {PH}, moodle_user_id = {PH}
                WHERE user_id = {PH} AND platform = {PH}""",
                (site_url, token, site_name, user_fullname, moodle_user_id, user_id, platform))
            conn.commit()
            return _fetchone(conn, f"SELECT * FROM student_lms_connections WHERE id = {PH}", (existing['id'],))
        else:
            new_id = _insert_returning_id(conn,
                f"""INSERT INTO student_lms_connections (user_id, platform, site_url, token, site_name, user_fullname, moodle_user_id)
                    VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
                (user_id, platform, site_url, token, site_name, user_fullname, moodle_user_id))
            conn.commit()
            return _fetchone(conn, f"SELECT * FROM student_lms_connections WHERE id = {PH}", (new_id,))
    finally:
        conn.close()


def get_lms_connection(user_id: int, platform: str = 'moodle') -> Optional[dict]:
    """Get the user's LMS connection."""
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM student_lms_connections WHERE user_id = {PH} AND platform = {PH}", (user_id, platform))
    finally:
        conn.close()


def delete_lms_connection(user_id: int, platform: str = 'moodle') -> bool:
    """Delete an LMS connection (and all cached courses via CASCADE)."""
    conn = _get_conn()
    try:
        _execute(conn, f"DELETE FROM student_lms_connections WHERE user_id = {PH} AND platform = {PH}", (user_id, platform))
        conn.commit()
        return True
    finally:
        conn.close()


def save_lms_course(user_id: int, connection_id: int, course_id: int,
                    course_name: str, course_shortname: str = '', imported_content: str = '') -> dict:
    """Save or update a cached LMS course."""
    conn = _get_conn()
    try:
        existing = _fetchone(conn, f"SELECT id FROM student_lms_courses WHERE user_id = {PH} AND course_id = {PH}", (user_id, course_id))
        if existing:
            _execute(conn, f"""UPDATE student_lms_courses
                SET course_name = {PH}, course_shortname = {PH}, imported_content = {PH}, synced_at = CURRENT_TIMESTAMP
                WHERE id = {PH}""",
                (course_name, course_shortname, imported_content, existing['id']))
            conn.commit()
            return _fetchone(conn, f"SELECT * FROM student_lms_courses WHERE id = {PH}", (existing['id'],))
        else:
            new_id = _insert_returning_id(conn,
                f"""INSERT INTO student_lms_courses (user_id, connection_id, course_id, course_name, course_shortname, imported_content)
                    VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
                (user_id, connection_id, course_id, course_name, course_shortname, imported_content))
            conn.commit()
            return _fetchone(conn, f"SELECT * FROM student_lms_courses WHERE id = {PH}", (new_id,))
    finally:
        conn.close()


def get_lms_courses(user_id: int) -> list:
    """Get all cached LMS courses for the user."""
    conn = _get_conn()
    try:
        return _fetchall(conn, f"""SELECT id, course_id, course_name, course_shortname, imported_content IS NOT NULL as has_content, synced_at
            FROM student_lms_courses WHERE user_id = {PH} ORDER BY course_name""", (user_id,))
    finally:
        conn.close()


def get_lms_course_content(user_id: int, course_id: int) -> Optional[str]:
    """Get the imported text content for a course."""
    conn = _get_conn()
    try:
        row = _fetchone(conn, f"SELECT imported_content FROM student_lms_courses WHERE user_id = {PH} AND course_id = {PH}", (user_id, course_id))
        return row['imported_content'] if row else None
    finally:
        conn.close()


# ─── Notes partagées (bibliothèque communautaire) ───────────────────────────

def create_shared_note(user_id: int, author_name: str, is_anonymous: bool,
                       title: str, subject: str, university: str = None,
                       study_year: str = None, file_type: str = 'text',
                       content_text: str = None, file_url: str = None) -> dict:
    conn = _get_conn()
    try:
        new_id = _execute(conn,
            f"""INSERT INTO student_shared_notes
                (user_id, author_name, is_anonymous, title, subject, university, study_year, file_type, content_text, file_url)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})""",
            (user_id, author_name if not is_anonymous else 'Anonyme',
             is_anonymous, title, subject, university, study_year,
             file_type, content_text, file_url))
        conn.commit()
        return _fetchone(conn, f"SELECT * FROM student_shared_notes WHERE id = {PH}", (new_id,))
    finally:
        conn.close()


def list_shared_notes(subject: str = None, university: str = None, limit: int = 50, offset: int = 0) -> list:
    conn = _get_conn()
    try:
        clauses, params = [], []
        if subject:
            clauses.append(f"subject = {PH}")
            params.append(subject)
        if university:
            clauses.append(f"university = {PH}")
            params.append(university)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.extend([limit, offset])
        return _fetchall(conn,
            f"""SELECT id, author_name, is_anonymous, title, subject, university, study_year,
                       file_type, downloads, likes, created_at
                FROM student_shared_notes {where}
                ORDER BY created_at DESC LIMIT {PH} OFFSET {PH}""", tuple(params))
    finally:
        conn.close()


def get_shared_note(note_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        return _fetchone(conn, f"SELECT * FROM student_shared_notes WHERE id = {PH}", (note_id,))
    finally:
        conn.close()


def increment_note_downloads(note_id: int):
    conn = _get_conn()
    try:
        _execute(conn, f"UPDATE student_shared_notes SET downloads = downloads + 1 WHERE id = {PH}", (note_id,))
        conn.commit()
    finally:
        conn.close()


def increment_note_likes(note_id: int):
    conn = _get_conn()
    try:
        _execute(conn, f"UPDATE student_shared_notes SET likes = likes + 1 WHERE id = {PH}", (note_id,))
        conn.commit()
    finally:
        conn.close()


def delete_shared_note(note_id: int, user_id: int) -> bool:
    """Supprime une note — seulement si c'est l'auteur."""
    conn = _get_conn()
    try:
        row = _fetchone(conn, f"SELECT user_id FROM student_shared_notes WHERE id = {PH}", (note_id,))
        if not row or row['user_id'] != user_id:
            return False
        _execute(conn, f"DELETE FROM student_shared_notes WHERE id = {PH}", (note_id,))
        conn.commit()
        return True
    finally:
        conn.close()
