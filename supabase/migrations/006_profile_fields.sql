-- プロファイル関連カラム追加
ALTER TABLE projects ADD COLUMN IF NOT EXISTS benchmark_channels JSONB DEFAULT '[]';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS strengths TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS content_style TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;
