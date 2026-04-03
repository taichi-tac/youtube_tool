-- ============================================================
-- 002_indexes.sql
-- インデックス定義
-- ============================================================

-- users
CREATE INDEX idx_users_auth_id ON users (auth_id);
CREATE INDEX idx_users_email   ON users (email);
CREATE INDEX idx_users_plan    ON users (plan);

-- projects
CREATE INDEX idx_projects_user_id    ON projects (user_id);
CREATE INDEX idx_projects_channel_id ON projects (channel_id);
CREATE INDEX idx_projects_genre      ON projects (genre);

-- keywords
CREATE INDEX idx_keywords_project_id   ON keywords (project_id);
CREATE INDEX idx_keywords_seed_keyword ON keywords (seed_keyword);
CREATE INDEX idx_keywords_source       ON keywords (source);
CREATE INDEX idx_keywords_is_selected  ON keywords (project_id, is_selected) WHERE is_selected = TRUE;
CREATE INDEX idx_keywords_trend_score  ON keywords (trend_score DESC NULLS LAST);

-- videos
CREATE INDEX idx_videos_project_id       ON videos (project_id);
CREATE INDEX idx_videos_youtube_video_id ON videos (youtube_video_id);
CREATE INDEX idx_videos_keyword_id       ON videos (keyword_id);
CREATE INDEX idx_videos_channel_id       ON videos (channel_id);
CREATE INDEX idx_videos_published_at     ON videos (published_at DESC);
CREATE INDEX idx_videos_view_count       ON videos (view_count DESC);
CREATE INDEX idx_videos_views_per_day    ON videos (views_per_day DESC NULLS LAST);
CREATE INDEX idx_videos_is_trending      ON videos (project_id, is_trending) WHERE is_trending = TRUE;

-- video_comments
CREATE INDEX idx_video_comments_video_id   ON video_comments (video_id);
CREATE INDEX idx_video_comments_sentiment  ON video_comments (sentiment);
CREATE INDEX idx_video_comments_is_question ON video_comments (video_id, is_question) WHERE is_question = TRUE;
CREATE INDEX idx_video_comments_need_category ON video_comments (need_category) WHERE need_category IS NOT NULL;

-- knowledge_chunks
CREATE INDEX idx_knowledge_chunks_project_id  ON knowledge_chunks (project_id);
CREATE INDEX idx_knowledge_chunks_source_type ON knowledge_chunks (source_type);
CREATE INDEX idx_knowledge_chunks_source_file ON knowledge_chunks (source_file);

-- pgvector IVFFlat cosine インデックス
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- scripts
CREATE INDEX idx_scripts_project_id ON scripts (project_id);
CREATE INDEX idx_scripts_keyword_id ON scripts (keyword_id);
CREATE INDEX idx_scripts_status     ON scripts (status);
CREATE INDEX idx_scripts_created_at ON scripts (created_at DESC);

-- thumbnails
CREATE INDEX idx_thumbnails_video_id    ON thumbnails (video_id);
CREATE INDEX idx_thumbnails_project_id  ON thumbnails (project_id);
CREATE INDEX idx_thumbnails_source_type ON thumbnails (source_type);
CREATE INDEX idx_thumbnails_click_score ON thumbnails (click_score DESC NULLS LAST);

-- theories
CREATE INDEX idx_theories_project_id  ON theories (project_id);
CREATE INDEX idx_theories_category    ON theories (category);
CREATE INDEX idx_theories_source_type ON theories (source_type);
CREATE INDEX idx_theories_is_active   ON theories (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_theories_confidence  ON theories (confidence DESC NULLS LAST);
CREATE INDEX idx_theories_usage_count ON theories (usage_count DESC);
