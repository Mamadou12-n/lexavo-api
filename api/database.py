"""
SQLite database for Lexavo — users, lawyers, conversations, messages.
Uses only stdlib sqlite3 (no extra dependencies).

Database file: output/lexavo.db
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ─── Database path ───────────────────────────────────────────────────────────
# En production Railway : définir LEXAVO_DB_PATH=/app/db/lexavo.db
# Le volume Railway doit être monté sur /app/db/
_default_db = str(Path(__file__).parent.parent / "output" / "lexavo.db")
DB_PATH = Path(os.getenv("LEXAVO_DB_PATH", _default_db))
DB_DIR  = DB_PATH.parent


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with row_factory for dict-like access."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── Init ────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'fr' CHECK(language IN ('fr', 'nl', 'en')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS lawyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                bar TEXT NOT NULL,
                specialties TEXT NOT NULL DEFAULT '[]',
                email TEXT,
                phone TEXT,
                city TEXT NOT NULL,
                description TEXT,
                rating REAL DEFAULT 0.0,
                verified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'pro', 'cabinet')),
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'canceled', 'past_due', 'trialing')),
                current_period_start TEXT,
                current_period_end TEXT,
                questions_used INTEGER NOT NULL DEFAULT 0,
                questions_reset_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_customer_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_lawyers_city ON lawyers(city);

            CREATE TABLE IF NOT EXISTS shield_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contract_type TEXT,
                verdict TEXT NOT NULL,
                summary TEXT NOT NULL,
                clauses_json TEXT NOT NULL DEFAULT '[]',
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_shield_user ON shield_analyses(user_id);

            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                domains TEXT NOT NULL DEFAULT '[]',
                token TEXT NOT NULL,
                confirmed INTEGER DEFAULT 0,
                subscribed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);

            CREATE TABLE IF NOT EXISTS push_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                preferences TEXT NOT NULL DEFAULT '{"legal_alerts":true,"deadlines":true,"news":false,"subscription":true}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, token)
            );
            CREATE INDEX IF NOT EXISTS idx_push_tokens_user ON push_tokens(user_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Users CRUD ──────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, name: str, language: str = "fr") -> dict:
    """Insert a new user. Returns the user dict (without password_hash)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, name, language) VALUES (?, ?, ?, ?)",
            (email, password_hash, name, language),
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID (excludes password_hash)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, email, name, language, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email (includes password_hash for auth)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, name, language, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ─── Lawyers CRUD ────────────────────────────────────────────────────────────

def create_lawyer(
    name: str, bar: str, specialties: list, email: str, phone: str,
    city: str, description: str, rating: float = 0.0, verified: bool = False,
) -> dict:
    """Insert a new lawyer. Returns the lawyer dict."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO lawyers (name, bar, specialties, email, phone, city, description, rating, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, bar, json.dumps(specialties, ensure_ascii=False), email, phone,
             city, description, rating, int(verified)),
        )
        conn.commit()
        return get_lawyer_by_id(cursor.lastrowid)
    finally:
        conn.close()


def get_lawyer_by_id(lawyer_id: int) -> Optional[dict]:
    """Get a single lawyer by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM lawyers WHERE id = ?", (lawyer_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["specialties"] = json.loads(d["specialties"])
        d["verified"] = bool(d["verified"])
        return d
    finally:
        conn.close()


def list_lawyers(
    city: Optional[str] = None,
    specialty: Optional[str] = None,
    language: Optional[str] = None,
) -> list:
    """List lawyers with optional filters."""
    conn = _get_conn()
    try:
        query = "SELECT * FROM lawyers WHERE 1=1"
        params = []

        if city:
            query += " AND LOWER(city) = LOWER(?)"
            params.append(city)

        if specialty:
            # Search within JSON array stored as text
            query += " AND LOWER(specialties) LIKE LOWER(?)"
            params.append(f"%{specialty}%")

        query += " ORDER BY rating DESC, name ASC"

        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["specialties"] = json.loads(d["specialties"])
            d["verified"] = bool(d["verified"])
            results.append(d)
        return results
    finally:
        conn.close()


def count_lawyers() -> int:
    """Return the total number of lawyers in the database."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM lawyers").fetchone()
        return row["cnt"]
    finally:
        conn.close()


# ─── Conversations CRUD ─────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str) -> dict:
    """Create a new conversation for a user."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )
        conn.commit()
        return get_conversation_by_id(cursor.lastrowid)
    finally:
        conn.close()


def get_conversation_by_id(conversation_id: int) -> Optional[dict]:
    """Get a single conversation by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_conversations(user_id: int) -> list:
    """List all conversations for a user, newest first."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Messages CRUD ──────────────────────────────────────────────────────────

def create_message(
    conversation_id: int, role: str, content: str, sources_json: str = "[]",
) -> dict:
    """Add a message to a conversation."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO messages (conversation_id, role, content, sources_json)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, role, content, sources_json),
        )
        conn.commit()
        return get_message_by_id(cursor.lastrowid)
    finally:
        conn.close()


def get_message_by_id(message_id: int) -> Optional[dict]:
    """Get a single message by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["sources_json"] = json.loads(d["sources_json"])
        except (json.JSONDecodeError, TypeError):
            d["sources_json"] = []
        return d
    finally:
        conn.close()


def list_messages(conversation_id: int) -> list:
    """List all messages for a conversation, oldest first."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            try:
                d["sources_json"] = json.loads(d["sources_json"])
            except (json.JSONDecodeError, TypeError):
                d["sources_json"] = []
            results.append(d)
        return results
    finally:
        conn.close()


# ─── Subscriptions CRUD ────────────────────────────────────────────────────

def get_subscription(user_id: int) -> Optional[dict]:
    """Get subscription for a user. Creates free plan if none exists."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        # Auto-create free plan
        conn.execute(
            "INSERT INTO subscriptions (user_id, plan) VALUES (?, 'free')",
            (user_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_subscription(
    user_id: int,
    plan: str,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    status: str = "active",
    current_period_start: Optional[str] = None,
    current_period_end: Optional[str] = None,
) -> Optional[dict]:
    """Update or create a subscription for a user."""
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            conn.execute(
                """UPDATE subscriptions
                   SET plan = ?, stripe_customer_id = COALESCE(?, stripe_customer_id),
                       stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                       status = ?, current_period_start = COALESCE(?, current_period_start),
                       current_period_end = COALESCE(?, current_period_end),
                       updated_at = ?
                   WHERE user_id = ?""",
                (plan, stripe_customer_id, stripe_subscription_id,
                 status, current_period_start, current_period_end, now, user_id),
            )
        else:
            conn.execute(
                """INSERT INTO subscriptions
                   (user_id, plan, stripe_customer_id, stripe_subscription_id,
                    status, current_period_start, current_period_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, plan, stripe_customer_id, stripe_subscription_id,
                 status, current_period_start, current_period_end),
            )
        conn.commit()
        return get_subscription(user_id)
    finally:
        conn.close()


def increment_question_count(user_id: int) -> dict:
    """Increment questions_used for this billing period. Resets monthly."""
    conn = _get_conn()
    try:
        sub = get_subscription(user_id)
        if not sub:
            return {"questions_used": 0, "limit": 5}

        # Check if we need to reset (monthly)
        reset_at = sub.get("questions_reset_at", "")
        now = datetime.now(timezone.utc)
        if reset_at:
            from datetime import datetime as dt
            try:
                reset_date = dt.strptime(reset_at, "%Y-%m-%d %H:%M:%S")
                days_since = (now - reset_date.replace(tzinfo=timezone.utc)).days
                if days_since >= 30:
                    conn.execute(
                        """UPDATE subscriptions
                           SET questions_used = 0, questions_reset_at = ?
                           WHERE user_id = ?""",
                        (now.strftime("%Y-%m-%d %H:%M:%S"), user_id),
                    )
                    conn.commit()
                    sub["questions_used"] = 0
            except (ValueError, TypeError):
                pass

        # Increment
        conn.execute(
            """UPDATE subscriptions
               SET questions_used = questions_used + 1, updated_at = ?
               WHERE user_id = ?""",
            (now.strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )
        conn.commit()

        # Plan limits
        limits = {"free": 5, "pro": -1, "cabinet": -1}
        plan = sub.get("plan", "free")
        limit = limits.get(plan, 5)

        return {
            "questions_used": sub["questions_used"] + 1,
            "limit": limit,
            "plan": plan,
        }
    finally:
        conn.close()


def get_subscription_by_stripe_customer(stripe_customer_id: str) -> Optional[dict]:
    """Get subscription by Stripe customer ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE stripe_customer_id = ?",
            (stripe_customer_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ─── Shield CRUD ────────────────────────────────────────────────────────────

def save_shield_analysis(user_id: int, contract_type: str, verdict: str,
                         summary: str, clauses_json: str, sources_json: str) -> dict:
    """Sauvegarde une analyse Shield."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO shield_analyses (user_id, contract_type, verdict, summary, clauses_json, sources_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, contract_type, verdict, summary, clauses_json, sources_json),
        )
        conn.commit()
        return get_shield_analysis(cursor.lastrowid)
    finally:
        conn.close()


def get_shield_analysis(analysis_id: int) -> Optional[dict]:
    """Récupère une analyse Shield par ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM shield_analyses WHERE id = ?", (analysis_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_shield_analyses(user_id: int, limit: int = 20) -> list:
    """Liste les analyses Shield d'un utilisateur."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM shield_analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Newsletter Subscribers CRUD ─────────────────────────────────────────────

def _init_newsletter_table(conn: sqlite3.Connection):
    """Crée la table newsletter_subscribers si elle n'existe pas encore."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            domains TEXT NOT NULL DEFAULT '[]',
            token TEXT NOT NULL,
            confirmed INTEGER DEFAULT 0,
            subscribed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);
    """)
    conn.commit()


def subscribe_newsletter(email: str, domains: list) -> dict:
    """
    Inscrit un email à la newsletter Lexavo.
    Retourne le subscriber dict avec son token de confirmation/désinscription.
    Retourne None si l'email est déjà inscrit.
    """
    import secrets as _secrets
    token = _secrets.token_urlsafe(32)

    conn = _get_conn()
    try:
        _init_newsletter_table(conn)
        try:
            cursor = conn.execute(
                """INSERT INTO newsletter_subscribers (email, domains, token, confirmed)
                   VALUES (?, ?, ?, 0)""",
                (email, json.dumps(domains, ensure_ascii=False), token),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM newsletter_subscribers WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            d = dict(row)
            d["domains"] = json.loads(d["domains"])
            d["confirmed"] = bool(d["confirmed"])
            return d
        except sqlite3.IntegrityError:
            # Email déjà présent → retourner l'existant
            row = conn.execute(
                "SELECT * FROM newsletter_subscribers WHERE email = ?",
                (email,),
            ).fetchone()
            if row:
                d = dict(row)
                d["domains"] = json.loads(d["domains"])
                d["confirmed"] = bool(d["confirmed"])
                return d
            return None
    finally:
        conn.close()


def unsubscribe_newsletter(token: str) -> bool:
    """
    Désinscrit un abonné via son token.
    Retourne True si la désinscription a réussi, False si le token est inconnu.
    """
    conn = _get_conn()
    try:
        _init_newsletter_table(conn)
        cursor = conn.execute(
            "DELETE FROM newsletter_subscribers WHERE token = ?",
            (token,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_confirmed_subscribers() -> list:
    """Retourne la liste de tous les abonnés confirmés."""
    conn = _get_conn()
    try:
        _init_newsletter_table(conn)
        rows = conn.execute(
            "SELECT * FROM newsletter_subscribers WHERE confirmed = 1 ORDER BY subscribed_at DESC",
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["domains"] = json.loads(d["domains"])
            d["confirmed"] = bool(d["confirmed"])
            results.append(d)
        return results
    finally:
        conn.close()


# ─── Push Tokens ──────────────────────────────────────────────────────────────

def save_push_token(user_id: int, token: str) -> None:
    """Enregistre ou met à jour un token push Expo pour un utilisateur."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO push_tokens (user_id, token, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id, token) DO UPDATE SET updated_at = datetime('now')
            """,
            (user_id, token),
        )
        conn.commit()
    finally:
        conn.close()


def update_push_preferences(user_id: int, token: str, preferences: dict) -> None:
    """Met à jour les préférences de notification pour un token push donné."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            UPDATE push_tokens
            SET preferences = ?, updated_at = datetime('now')
            WHERE user_id = ? AND token = ?
            """,
            (json.dumps(preferences), user_id, token),
        )
        conn.commit()
    finally:
        conn.close()


def get_push_tokens_for_user(user_id: int) -> list:
    """Retourne tous les tokens push actifs d'un utilisateur."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM push_tokens WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
