"use client";

import { useState, useCallback } from "react";
import { apiClient, PROJECT_ID } from "@/lib/api-client";
import type { ThumbnailAnalysis } from "@/types/video";

export function useThumbnailAnalysis() {
  const [thumbnails, setThumbnails] = useState<ThumbnailAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 分析済みサムネ一覧取得 */
  const fetchThumbnails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<ThumbnailAnalysis[]>(
        `/api/v1/thumbnails/${PROJECT_ID}`,
      );
      setThumbnails(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "サムネ取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  /** サムネ分析実行 */
  const analyzeThumbnails = useCallback(async (videoIds: string[]) => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await apiClient.post<ThumbnailAnalysis[]>(
        `/api/v1/thumbnails/${PROJECT_ID}/analyze`,
        { video_ids: videoIds },
      );
      setThumbnails((prev) => {
        const existingIds = new Set(prev.map((t) => t.id));
        const newItems = result.filter((t) => !existingIds.has(t.id));
        return [...newItems, ...prev];
      });
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "サムネ分析に失敗しました");
      return null;
    } finally {
      setAnalyzing(false);
    }
  }, []);

  return {
    thumbnails,
    loading,
    analyzing,
    error,
    fetchThumbnails,
    analyzeThumbnails,
  };
}
