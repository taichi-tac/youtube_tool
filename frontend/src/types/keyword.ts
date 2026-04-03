/** バックエンド KeywordResponse に対応 */
export interface Keyword {
  id: string;
  project_id: string;
  keyword: string;
  seed_keyword: string | null;
  source: string;
  search_volume: number | null;
  competition: number | null;
  trend_score: number | null;
  is_selected: boolean;
  fetched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KeywordSuggestRequest {
  seed_keyword: string;
  language?: string;
}

export interface KeywordSuggestResponse {
  seed_keyword: string;
  suggestions: string[];
}

export interface KeywordSearchParams {
  query: string;
  language?: string;
  country?: string;
  limit?: number;
}
