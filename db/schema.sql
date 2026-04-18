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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_user_resource_time'
    ) THEN
        ALTER TABLE study_sessions
        ADD CONSTRAINT unique_user_resource_time
        UNIQUE (user_id, resource_id, scheduled_at);
    END IF;
END $$;

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

-- Finance agent
-- Add this to schema.sql, replacing the current expenses table definition
CREATE TABLE IF NOT EXISTS expenses (
    id          SERIAL PRIMARY KEY,
    amount      NUMERIC(10, 2)  NOT NULL,
    category    TEXT,
    description TEXT,
    date        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE  -- match other tables
);

CREATE INDEX IF NOT EXISTS expenses_user_date_idx
    ON expenses(user_id, date DESC);

-- =============================================================================
-- HEALTH DOMAIN TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS health_daily_metrics (
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    total_steps         INT,
    total_calories      NUMERIC,
    active_minutes      INT,
    resting_heart_rate  NUMERIC,
    synced_at           TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, date)
);

CREATE TABLE IF NOT EXISTS health_sleep_logs (
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ,
    duration_minutes    INT,
    sleep_stages        JSONB,
    synced_at           TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, date)
);

CREATE TABLE IF NOT EXISTS health_activity_logs (
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    activity_type       TEXT NOT NULL,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ,
    duration_minutes    INT,
    calories_burned     NUMERIC,
    steps               INT,
    distance_meters     NUMERIC,
    avg_heart_rate      NUMERIC,
    PRIMARY KEY (user_id, start_time)
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

-- =============================================================================
-- FEATURE 1: SKILL GAP ANALYSIS
-- Stores skills the user has, and skills required for career goals.
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_name      TEXT        NOT NULL,
    category        TEXT        NOT NULL,   -- e.g. "programming" | "cloud" | "data"
    proficiency     TEXT        NOT NULL DEFAULT 'beginner',
    -- Values: beginner | intermediate | advanced | expert
    verified        BOOLEAN     NOT NULL DEFAULT false,
    -- true = backed by a completed resource or cert in learning_resources
    source_resource_id UUID REFERENCES learning_resources(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, skill_name)
);

-- Career role skill requirements (predefined, seeded below)
CREATE TABLE IF NOT EXISTS role_skill_requirements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name       TEXT        NOT NULL,   -- e.g. "Data Engineer"
    skill_name      TEXT        NOT NULL,
    importance      TEXT        NOT NULL DEFAULT 'required',
    -- Values: required | recommended | optional
    UNIQUE(role_name, skill_name)
);


-- =============================================================================
-- FEATURE 2: SPACED REPETITION / FLASHCARDS
-- Stores flashcards and tracks review schedule using SM-2 algorithm intervals.
-- =============================================================================

CREATE TABLE IF NOT EXISTS flashcards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    resource_id     UUID REFERENCES learning_resources(id) ON DELETE CASCADE,
    question        TEXT        NOT NULL,
    answer          TEXT        NOT NULL,
    tags            TEXT[]      NOT NULL DEFAULT '{}',
    -- SM-2 spaced repetition fields
    ease_factor     NUMERIC(4,2) NOT NULL DEFAULT 2.5,  -- starts at 2.5
    interval_days   INT          NOT NULL DEFAULT 1,     -- days until next review
    repetitions     INT          NOT NULL DEFAULT 0,     -- times reviewed correctly
    next_review_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_reviewed_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS flashcards_next_review_idx
    ON flashcards(user_id, next_review_at);


-- =============================================================================
-- FEATURE 3 & 4: LEARNING PATHS / ROADMAPS
-- A learning path is an ordered sequence of resources toward a specific goal.
-- =============================================================================

CREATE TABLE IF NOT EXISTS learning_paths (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,   -- e.g. "Become a Data Engineer"
    description     TEXT,
    target_role     TEXT,                   -- links to role_skill_requirements
    status          TEXT        NOT NULL DEFAULT 'active',
    -- Values: active | completed | paused
    estimated_weeks INT,                    -- total estimated duration
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_path_steps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id         UUID REFERENCES learning_paths(id) ON DELETE CASCADE,
    resource_id     UUID REFERENCES learning_resources(id) ON DELETE CASCADE,
    step_order      INT         NOT NULL,   -- 1, 2, 3 ...
    title           TEXT        NOT NULL,
    why_this        TEXT,                   -- explains why this step matters
    status          TEXT        NOT NULL DEFAULT 'pending',
    -- Values: pending | in_progress | completed | skipped
    estimated_hours INT,
    completed_at    TIMESTAMPTZ,
    UNIQUE(path_id, step_order)
);


-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Role skill requirements for common tech roles
INSERT INTO role_skill_requirements (role_name, skill_name, importance) VALUES
-- Data Engineer
('Data Engineer', 'Python',             'required'),
('Data Engineer', 'SQL',                'required'),
('Data Engineer', 'Apache Spark',       'required'),
('Data Engineer', 'Apache Airflow',     'required'),
('Data Engineer', 'Data Warehousing',   'required'),
('Data Engineer', 'ETL Pipelines',      'required'),
('Data Engineer', 'Google BigQuery',    'recommended'),
('Data Engineer', 'dbt',               'recommended'),
('Data Engineer', 'Kafka',             'recommended'),
('Data Engineer', 'Docker',            'recommended'),
('Data Engineer', 'Cloud Platforms',   'recommended'),
('Data Engineer', 'Git',               'optional'),

-- ML Engineer
('ML Engineer', 'Python',              'required'),
('ML Engineer', 'Machine Learning',    'required'),
('ML Engineer', 'Deep Learning',       'required'),
('ML Engineer', 'TensorFlow',          'required'),
('ML Engineer', 'PyTorch',             'required'),
('ML Engineer', 'MLOps',               'recommended'),
('ML Engineer', 'Docker',              'recommended'),
('ML Engineer', 'SQL',                 'recommended'),
('ML Engineer', 'Statistics',          'recommended'),

-- Cloud Engineer
('Cloud Engineer', 'Google Cloud Platform', 'required'),
('Cloud Engineer', 'Terraform',            'required'),
('Cloud Engineer', 'Kubernetes',           'required'),
('Cloud Engineer', 'Docker',              'required'),
('Cloud Engineer', 'Networking',          'required'),
('Cloud Engineer', 'Python',              'recommended'),
('Cloud Engineer', 'CI/CD',              'recommended'),
('Cloud Engineer', 'IAM & Security',     'recommended'),

-- Backend Developer
('Backend Developer', 'Python',          'required'),
('Backend Developer', 'REST APIs',       'required'),
('Backend Developer', 'SQL',             'required'),
('Backend Developer', 'Docker',          'recommended'),
('Backend Developer', 'System Design',   'recommended'),
('Backend Developer', 'Git',             'recommended')

ON CONFLICT (role_name, skill_name) DO NOTHING;

-- Demo user skills (mapped to existing demo seed data)
INSERT INTO user_skills (user_id, skill_name, category, proficiency, verified)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'Python',           'programming', 'intermediate', true),
    ('00000000-0000-0000-0000-000000000001', 'SQL',              'data',        'beginner',     false),
    ('00000000-0000-0000-0000-000000000001', 'Google Cloud Platform', 'cloud', 'intermediate', true),
    ('00000000-0000-0000-0000-000000000001', 'Machine Learning', 'ai',          'beginner',     false)
ON CONFLICT (user_id, skill_name) DO NOTHING;

-- Demo flashcards for Python Crash Course
INSERT INTO flashcards (user_id, resource_id, question, answer, tags)
SELECT
    '00000000-0000-0000-0000-000000000001',
    id,
    'What does a list comprehension look like in Python?',
    '[expression for item in iterable if condition] — e.g. [x*2 for x in range(10) if x > 3]',
    ARRAY['python', 'syntax']
FROM learning_resources
WHERE user_id = '00000000-0000-0000-0000-000000000001'
  AND title = 'Python Crash Course'
LIMIT 1
ON CONFLICT DO NOTHING;
