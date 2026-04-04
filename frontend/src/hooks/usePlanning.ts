"use client";

import { useState, useCallback } from "react";
import { apiClient, getProjectId } from "@/lib/api-client";
import type { PlanningIdea } from "@/types/planning";

export function usePlanning() {
  const [ideas, setIdeas] = useState<PlanningIdea[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateIdeas = useCallback(async (count: number = 10) => {
    setLoading(true);
    setError(null);
    try {
      const pid = await getProjectId();
      const result = await apiClient.post<PlanningIdea[]>(
        `/api/v1/planning/${pid}/ideas`,
        { count },
      );
      setIdeas(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "企画生成に失敗しました");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const generateMore = useCallback(async (count: number = 10) => {
    setLoading(true);
    setError(null);
    try {
      const pid = await getProjectId();
      const excludeKeywords = ideas.map((i) => i.keyword);
      const result = await apiClient.post<PlanningIdea[]>(
        `/api/v1/planning/${pid}/ideas/next`,
        { count, exclude_keywords: excludeKeywords },
      );
      setIdeas((prev) => [...prev, ...result]);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "追加企画生成に失敗しました");
      return [];
    } finally {
      setLoading(false);
    }
  }, [ideas]);

  return { ideas, loading, error, generateIdeas, generateMore };
}
