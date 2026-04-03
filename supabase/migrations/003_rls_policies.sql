-- ============================================================
-- 003_rls_policies.sql
-- Row Level Security ポリシー
-- ============================================================

-- ============================================================
-- RLS 有効化
-- ============================================================
ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects         ENABLE ROW LEVEL SECURITY;
ALTER TABLE keywords         ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos           ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_comments   ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE scripts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE thumbnails       ENABLE ROW LEVEL SECURITY;
ALTER TABLE theories         ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- users: auth_id = auth.uid()
-- ============================================================
CREATE POLICY "users_select_own" ON users
    FOR SELECT USING (auth_id = auth.uid());

CREATE POLICY "users_insert_own" ON users
    FOR INSERT WITH CHECK (auth_id = auth.uid());

CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (auth_id = auth.uid())
    WITH CHECK (auth_id = auth.uid());

CREATE POLICY "users_delete_own" ON users
    FOR DELETE USING (auth_id = auth.uid());

-- ============================================================
-- projects: user_id 経由で本人のみ
-- ============================================================
CREATE POLICY "projects_select_own" ON projects
    FOR SELECT USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "projects_insert_own" ON projects
    FOR INSERT WITH CHECK (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "projects_update_own" ON projects
    FOR UPDATE USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    ) WITH CHECK (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "projects_delete_own" ON projects
    FOR DELETE USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

-- ============================================================
-- keywords: project_id 経由
-- ============================================================
CREATE POLICY "keywords_select_own" ON keywords
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "keywords_insert_own" ON keywords
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "keywords_update_own" ON keywords
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "keywords_delete_own" ON keywords
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

-- ============================================================
-- videos: project_id 経由
-- ============================================================
CREATE POLICY "videos_select_own" ON videos
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "videos_insert_own" ON videos
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "videos_update_own" ON videos
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "videos_delete_own" ON videos
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

-- ============================================================
-- video_comments: video_id → videos.project_id 経由
-- ============================================================
CREATE POLICY "video_comments_select_own" ON video_comments
    FOR SELECT USING (
        video_id IN (
            SELECT id FROM videos WHERE project_id IN (
                SELECT id FROM projects WHERE user_id IN (
                    SELECT id FROM users WHERE auth_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "video_comments_insert_own" ON video_comments
    FOR INSERT WITH CHECK (
        video_id IN (
            SELECT id FROM videos WHERE project_id IN (
                SELECT id FROM projects WHERE user_id IN (
                    SELECT id FROM users WHERE auth_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "video_comments_update_own" ON video_comments
    FOR UPDATE USING (
        video_id IN (
            SELECT id FROM videos WHERE project_id IN (
                SELECT id FROM projects WHERE user_id IN (
                    SELECT id FROM users WHERE auth_id = auth.uid()
                )
            )
        )
    ) WITH CHECK (
        video_id IN (
            SELECT id FROM videos WHERE project_id IN (
                SELECT id FROM projects WHERE user_id IN (
                    SELECT id FROM users WHERE auth_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "video_comments_delete_own" ON video_comments
    FOR DELETE USING (
        video_id IN (
            SELECT id FROM videos WHERE project_id IN (
                SELECT id FROM projects WHERE user_id IN (
                    SELECT id FROM users WHERE auth_id = auth.uid()
                )
            )
        )
    );

-- ============================================================
-- knowledge_chunks: project_id 経由 + NULL は全員読取可能
-- ============================================================
CREATE POLICY "knowledge_chunks_select_own_or_global" ON knowledge_chunks
    FOR SELECT USING (
        project_id IS NULL
        OR project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "knowledge_chunks_insert_own" ON knowledge_chunks
    FOR INSERT WITH CHECK (
        project_id IS NULL
        OR project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "knowledge_chunks_update_own" ON knowledge_chunks
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "knowledge_chunks_delete_own" ON knowledge_chunks
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

-- ============================================================
-- scripts: project_id 経由
-- ============================================================
CREATE POLICY "scripts_select_own" ON scripts
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "scripts_insert_own" ON scripts
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "scripts_update_own" ON scripts
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "scripts_delete_own" ON scripts
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

-- ============================================================
-- thumbnails: project_id 経由
-- ============================================================
CREATE POLICY "thumbnails_select_own" ON thumbnails
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "thumbnails_insert_own" ON thumbnails
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "thumbnails_update_own" ON thumbnails
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "thumbnails_delete_own" ON thumbnails
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

-- ============================================================
-- theories: project_id 経由 + NULL は全員読取可能
-- ============================================================
CREATE POLICY "theories_select_own_or_global" ON theories
    FOR SELECT USING (
        project_id IS NULL
        OR project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "theories_insert_own" ON theories
    FOR INSERT WITH CHECK (
        project_id IS NULL
        OR project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "theories_update_own" ON theories
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    ) WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );

CREATE POLICY "theories_delete_own" ON theories
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id IN (
                SELECT id FROM users WHERE auth_id = auth.uid()
            )
        )
    );
