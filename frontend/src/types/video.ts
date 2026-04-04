/** バックエンド VideoResponse に対応 */
export interface Video {
  id: string;
  project_id: string;
  youtube_video_id: string;
  title: string;
  channel_id: string | null;
  channel_title: string | null;
  description: string | null;
  published_at: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  views_per_day: number | null;
  is_trending: boolean;
  keyword_id: string | null;
  thumbnail_analysis: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface VideoSearchRequest {
  query: string;
  max_results?: number;
  order?: string;
  keyword_id?: string;
}

/** コメント */
export interface VideoComment {
  id: string;
  video_id: string;
  author: string;
  text: string;
  like_count: number;
  published_at: string;
}

/** ニーズカテゴリ */
export interface NeedCategory {
  category: string;
  count: number;
  percentage: number;
  representative_comments: string[];
}

/** コメント分析結果 */
export interface CommentAnalysis {
  video_id: string;
  total_comments: number;
  needs: NeedCategory[];
  summary: string;
}

/** サムネ分析結果 */
export interface ThumbnailAnalysis {
  id: string;
  video_id: string | null;
  project_id: string;
  image_url: string;
  source_type: string;
  click_score: number | null;
  composition_type: string | null;
  dominant_colors: { colors?: { hex: string; name: string }[] } | null;
  text_overlay: string | null;
  face_count: number | null;
  emotion: string | null;
  analysis_raw: { comment?: string } | null;
  analyzed_at: string | null;
  created_at: string;
}
