-- ユーザーAPIキーのカラムを追加
ALTER TABLE projects ADD COLUMN IF NOT EXISTS youtube_api_key TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS openai_api_key TEXT;
