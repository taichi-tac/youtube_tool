-- ============================================================
-- バイラル動画検索用カラム追加
-- Miyabi viral finder ツールと同等の指標を保持する。
-- 全て nullable で、既存データへの影響なし。
-- ============================================================

ALTER TABLE videos
  ADD COLUMN IF NOT EXISTS subscriber_count bigint,
  ADD COLUMN IF NOT EXISTS channel_total_view_count bigint,
  ADD COLUMN IF NOT EXISTS total_video_count integer,
  ADD COLUMN IF NOT EXISTS views_to_subs_ratio numeric(10, 2),
  ADD COLUMN IF NOT EXISTS subscriber_rate numeric(10, 6),
  ADD COLUMN IF NOT EXISTS like_rate numeric(10, 6),
  ADD COLUMN IF NOT EXISTS comment_rate numeric(10, 6),
  ADD COLUMN IF NOT EXISTS engagement_rate numeric(10, 6),
  ADD COLUMN IF NOT EXISTS hashtags jsonb;

-- 拡散率での検索を高速化
CREATE INDEX IF NOT EXISTS idx_videos_views_to_subs_ratio
  ON videos (views_to_subs_ratio DESC NULLS LAST);
