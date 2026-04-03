"use client";

import { useState, useCallback } from "react";
import { apiClient, PROJECT_ID } from "@/lib/api-client";
import type { KnowledgeChunk } from "@/types/knowledge";

export function useKnowledgeSearch() {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** ナレッジベースをベクトル検索する */
  const search = useCallback(async (query: string, topK = 5) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.post<KnowledgeChunk[]>(
        `/api/v1/knowledge/${PROJECT_ID}/search`,
        { query, top_k: topK },
      );
      setChunks(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "検索に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setChunks([]);
    setError(null);
  }, []);

  return { chunks, loading, error, search, clear };
}
