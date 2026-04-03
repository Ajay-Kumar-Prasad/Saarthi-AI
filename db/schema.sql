-- =============================================================================
-- Saarthi AI — AlloyDB Schema
-- Learning domain tables (learning_resources, study_sessions, study_goals)
-- plus the shared tables referenced by all sub-agents.
--
-- Run this once against your AlloyDB instance:
--   psql $ALLOYDB_URL -f db/schema.sql
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";           -- pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS "google_ml_integration"; -- AlloyDB AI NL-to-SQL

-- =============================================================================
-- SHARED TABLES (referenced by all sub-agents)
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    email       TEXT        UNIQUE NOT NULL,
    timezone    TEXT        NOT NULL DEFAULT 'Asia/Kolkata',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS goals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,
    domain          TEXT        NOT NULL,   -- work|health|finance|learning|social
    target_date     DATE,
    progress_pct    INT         NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    status          TEXT        NOT NULL DEFAULT 'active',
    milestones      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS life_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    domain      TEXT        NOT NULL,
    entry       TEXT        NOT NULL,
    mood        INT         CHECK (mood BETWEEN 1 AND 10),
    embedding   vector(768),               -- pgvector for semantic RAG
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS life_logs_embedding_idx
    ON life_logs USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- LEARNING DOMAIN TABLES
-- =============================================================================

-- Books, courses, articles, videos the user is tracking
CREATE TABLE IF NOT EXISTS learning_resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,
    resource_type   TEXT        NOT NULL DEFAULT 'course',
    -- Values: book | course | article | video | podcast
    url             TEXT,
    author          TEXT,
    status          TEXT        NOT NULL DEFAULT 'not_started',
    -- Values: not_started | in_progress | completed | paused
    progress_pct    INT         NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    total_pages     INT,                   -- for books
    current_page    INT,
    notes           TEXT,
    tags            TEXT[]      NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS learning_resources_user_idx
    ON learning_resources(user_id, status);

-- Scheduled study blocks (synced with Google Calendar via MCP)
CREATE TABLE IF NOT EXISTS study_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    resource_id         UUID REFERENCES learning_resources(id) ON DELETE CASCADE,
    title               TEXT        NOT NULL,
    scheduled_at        TIMESTAMPTZ NOT NULL,
    duration_minutes    INT         NOT NULL DEFAULT 60,
    calendar_event_id   TEXT,              -- Google Calendar event ID from MCP
    completed           BOOLEAN     NOT NULL DEFAULT false,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS study_sessions_user_date_idx
    ON study_sessions(user_id, scheduled_at);

-- High-level learning goals (e.g. "Finish Python bootcamp by June")
CREATE TABLE IF NOT EXISTS study_goals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    resource_id             UUID REFERENCES learning_resources(id) ON DELETE SET NULL,
    title                   TEXT        NOT NULL,
    target_date             DATE,
    weekly_hours_target     NUMERIC(5,2) NOT NULL DEFAULT 5.0,
    progress_pct            INT         NOT NULL DEFAULT 0,
    status                  TEXT        NOT NULL DEFAULT 'active',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- DEMO SEED DATA — delete before production
-- =============================================================================

-- Demo user (password hashing not shown — use IAM in production)
INSERT INTO users (id, name, email, timezone)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Demo User',
    'demo@saarthi.ai',
    'Asia/Kolkata'
) ON CONFLICT (email) DO NOTHING;

-- Sample resources
INSERT INTO learning_resources (user_id, title, resource_type, status, progress_pct, total_pages, current_page, tags)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'Python Crash Course', 'book', 'in_progress', 45, 544, 245, ARRAY['python', 'programming']),
    ('00000000-0000-0000-0000-000000000001', 'Google Cloud Professional Certificate', 'course', 'in_progress', 60, NULL, NULL, ARRAY['cloud', 'gcp']),
    ('00000000-0000-0000-0000-000000000001', 'System Design Primer', 'article', 'not_started', 0, NULL, NULL, ARRAY['system-design', 'architecture']),
    ('00000000-0000-0000-0000-000000000001', 'Deep Learning Specialization', 'course', 'paused', 30, NULL, NULL, ARRAY['ml', 'ai'])
ON CONFLICT DO NOTHING;

-- Sample study sessions (next 7 days)
INSERT INTO study_sessions (user_id, resource_id, title, scheduled_at, duration_minutes, completed)
SELECT
    '00000000-0000-0000-0000-000000000001',
    id,
    'Study: ' || title,
    now() + INTERVAL '1 day' + (RANDOM() * INTERVAL '6 days'),
    60,
    false
FROM learning_resources
WHERE user_id = '00000000-0000-0000-0000-000000000001'
  AND status = 'in_progress'
ON CONFLICT DO NOTHING;

-- Sample study goal
INSERT INTO study_goals (user_id, title, weekly_hours_target, progress_pct, target_date)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Complete GCP certification before hackathon demo',
    8.0,
    60,
    (CURRENT_DATE + INTERVAL '30 days')::DATE
) ON CONFLICT DO NOTHING;