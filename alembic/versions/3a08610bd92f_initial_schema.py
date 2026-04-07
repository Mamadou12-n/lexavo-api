"""initial_schema

Revision ID: 3a08610bd92f
Revises: 
Create Date: 2026-04-07 16:39:45.298002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a08610bd92f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée le schéma initial Lexavo (PostgreSQL)."""
    op.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'fr',
    region TEXT DEFAULT NULL,
    profession TEXT DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
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
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources_json TEXT DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free','basic','pro','business','firm_s','firm_m','enterprise')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','canceled','past_due','trialing')),
    current_period_start TEXT,
    current_period_end TEXT,
    questions_used INTEGER NOT NULL DEFAULT 0,
    questions_reset_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS shield_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    contract_type TEXT,
    verdict TEXT NOT NULL,
    summary TEXT NOT NULL,
    clauses_json TEXT NOT NULL DEFAULT '[]',
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    domains TEXT NOT NULL DEFAULT '[]',
    token TEXT NOT NULL,
    confirmed BOOLEAN DEFAULT FALSE,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS emergency_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    description TEXT NOT NULL,
    phone TEXT NOT NULL,
    city TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','assigned','completed','cancelled')),
    price_cents INTEGER NOT NULL DEFAULT 4900,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS alert_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    domains TEXT NOT NULL DEFAULT '[]',
    frequency TEXT NOT NULL DEFAULT 'daily' CHECK(frequency IN ('realtime','daily','weekly')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS proof_cases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed','archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS proof_entries (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES proof_cases(id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL DEFAULT 'note' CHECK(entry_type IN ('note','document','photo','email','sms','testimony')),
    content TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS push_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{"legal_alerts":true,"deadlines":true,"news":false,"subscription":true}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, token)
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS beta_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    milestone TEXT NOT NULL,
    email_to TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    error_msg TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, milestone)
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS audit_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT,
    company_type TEXT NOT NULL DEFAULT 'srl',
    score INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    op.execute("""
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    # Index
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lawyers_city ON lawyers(city)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_shield_user ON shield_analyses(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_emergency_user ON emergency_requests(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_alert_prefs_user ON alert_preferences(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_proof_cases_user ON proof_cases(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_proof_entries_case ON proof_entries(case_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_push_tokens_user ON push_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_reports_user ON audit_reports(user_id)")


def downgrade() -> None:
    """Supprime toutes les tables Lexavo."""
    for tbl in [
        "password_reset_tokens", "audit_reports", "beta_notifications",
        "push_tokens", "proof_entries", "proof_cases", "alert_preferences",
        "emergency_requests", "refresh_tokens", "newsletter_subscribers",
        "shield_analyses", "subscriptions", "messages", "conversations",
        "lawyers", "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
