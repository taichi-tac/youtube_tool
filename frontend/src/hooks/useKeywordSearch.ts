"use client";

import { useState, useCallback } from "react";
import { apiClient, getProjectId } from "@/lib/api-client";
import type { Keyword, KeywordSuggestResponse } from "@/types/keyword";

export function useKeywordSearch() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** プロジェクトのキーワード一覧を取得 */
  const fetchKeywords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const pid = await getProjectId();
      const result = await apiClient.get<Keyword[]>(
        `/api/v1/keywords/${pid}`,
      );
      setKeywords(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "キーワード取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  /** シードキーワードからサジェストを取得 */
  const suggest = useCallback(async (seedKeyword: string, language = "ja") => {
    setLoading(true);
    setError(null);
    setSuggestions([]);
    try {
      const pid = await getProjectId();
      const result = await apiClient.post<KeywordSuggestResponse>(
        `/api/v1/keywords/${pid}/suggest`,
        { seed_keyword: seedKeyword, language },
      );
      setSuggestions(result.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "サジェスト取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  /** キーワードをDBに保存 */
  const saveKeyword = useCallback(async (keyword: string, seedKeyword: string) => {
    try {
      const pid = await getProjectId();
      const created = await apiClient.post<Keyword>(
        `/api/v1/keywords/${pid}`,
        {
          keyword,
          seed_keyword: seedKeyword,
          source: "youtube_suggest",
          is_selected: false,
        },
      );
      setKeywords((prev) => [created, ...prev]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : "キーワード保存に失敗しました");
      return null;
    }
  }, []);

  return { keywords, suggestions, loading, error, fetchKeywords, suggest, saveKeyword };
}
