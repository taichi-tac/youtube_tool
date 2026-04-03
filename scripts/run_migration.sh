#!/bin/bash
# Supabase にマイグレーションを1文ずつ実行するスクリプト
set -e

ENCODED_PASS=$(python3 -c "import urllib.parse; print(urllib.parse.quote('Rokugen2188'))")
DB_URL="postgresql://postgres:${ENCODED_PASS}@db.jlnhahvdlitrcjlcppph.supabase.co:5432/postgres"

run_sql() {
    echo ">>> Executing: ${1:0:60}..."
    npx supabase db query --db-url "$DB_URL" "$1" 2>&1
    echo "--- done ---"
}

# ===== 001: Extensions =====
run_sql 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
run_sql 'CREATE EXTENSION IF NOT EXISTS vector'

# ===== 001: Tables =====
run_sql 'CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_id UUID UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    plan TEXT NOT NULL DEFAULT '\''free'\'' CHECK (plan IN ('\''free'\'', '\''basic'\'', '\''pro'\'')),
    quota_used INT NOT NULL DEFAULT 0,
    quota_limit INT NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

run_sql 'CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    channel_id TEXT,
    channel_url TEXT,
    genre TEXT,
    target_audience TEXT,
    concept TEXT,
    center_pin TEXT,
    settings JSONB NOT NULL DEFAULT '\''{}'\''::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

run_sql 'CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    seed_keyword TEXT,
    source TEXT NOT NULL CHECK (source IN ('\''youtube_suggest'\'', '\''manual'\'', '\''related'\'')),
    search_volume INT,
    competition NUMERIC(3,2),
    trend_score NUMERIC(5,2),
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, keyword)
)'

run_sql 'CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    youtube_video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    channel_id TEXT,
    channel_title TEXT,
    description TEXT,
    published_at TIMESTAMPTZ,
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    comment_count INT DEFAULT 0,
    duration_seconds INT,
    thumbnail_url TEXT,
    views_per_day NUMERIC(10,2),
    is_trending BOOLEAN DEFAULT FALSE,
    keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    thumbnail_analysis JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

run_sql 'CREATE TABLE IF NOT EXISTS video_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    youtube_comment_id TEXT UNIQUE NOT NULL,
    author_name TEXT,
    text TEXT NOT NULL,
    like_count INT DEFAULT 0,
    published_at TIMESTAMPTZ,
    need_category TEXT,
    sentiment TEXT CHECK (sentiment IN ('\''positive'\'', '\''negative'\'', '\''neutral'\'', '\''mixed'\'')),
    is_question BOOLEAN DEFAULT FALSE,
    extracted_needs JSONB
)'

run_sql 'CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('\''wa_theory'\'', '\''market_analysis'\'', '\''second_brain'\'', '\''user_upload'\'')),
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),
    token_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_file, chunk_index)
)'

run_sql 'CREATE TABLE IF NOT EXISTS scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '\''draft'\'' CHECK (status IN ('\''draft'\'', '\''generating'\'', '\''completed'\'', '\''archived'\'')),
    target_viewer TEXT,
    viewer_problem TEXT,
    promise TEXT,
    uniqueness TEXT,
    hook TEXT,
    body TEXT,
    closing TEXT,
    word_count INT,
    generation_model TEXT,
    prompt_version TEXT,
    used_knowledge JSONB,
    generation_cost NUMERIC(8,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

run_sql 'CREATE TABLE IF NOT EXISTS thumbnails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('\''youtube'\'', '\''uploaded'\'', '\''generated'\'')),
    dominant_colors JSONB,
    text_overlay TEXT,
    face_count INT,
    emotion TEXT,
    composition_type TEXT,
    click_score NUMERIC(5,2),
    analysis_raw JSONB,
    analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

run_sql 'CREATE TABLE IF NOT EXISTS theories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('\''hook'\'', '\''retention'\'', '\''ctr'\'', '\''seo'\'', '\''storytelling'\'', '\''editing'\'')),
    body TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('\''wa_theory'\'', '\''user_defined'\'', '\''ai_extracted'\'')),
    source_ref TEXT,
    evidence JSONB,
    confidence NUMERIC(3,2),
    usage_count INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)'

# ===== 004: Trigger function =====
run_sql 'CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql'

# Triggers
for tbl in users projects keywords videos knowledge_chunks scripts thumbnails theories; do
    run_sql "DROP TRIGGER IF EXISTS trg_${tbl}_updated_at ON ${tbl}"
    run_sql "CREATE TRIGGER trg_${tbl}_updated_at BEFORE UPDATE ON ${tbl} FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
done

echo ""
echo "=== Migration complete! ==="
echo "Verifying tables..."
run_sql "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
