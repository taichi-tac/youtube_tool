"use client";

import { useState, useCallback } from "react";
import { apiClient, PROJECT_ID } from "@/lib/api-client";
import type { Video, VideoComment, CommentAnalysis } from "@/types/video";

export function useVideoAnalysis() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // コメント関連
  const [comments, setComments] = useState<VideoComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);

  // ニーズ分析関連
  const [commentAnalysis, setCommentAnalysis] = useState<CommentAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  /** プロジェクトの保存済み動画一覧を取得 */
  const fetchVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<Video[]>(
        `/api/v1/videos/${PROJECT_ID}`,
      );
      setVideos(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "動画取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  /** YouTube動画を検索してDBに保存 */
  const searchVideos = useCallback(async (query: string, maxResults = 10) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.post<Video[]>(
        `/api/v1/videos/${PROJECT_ID}/search`,
        { query, max_results: maxResults, order: "relevance" },
      );
      setVideos(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "動画検索に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  /** 単一動画を取得 */
  const fetchVideo = useCallback(async (videoId: string): Promise<Video | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<Video>(
        `/api/v1/videos/${PROJECT_ID}/${videoId}`,
      );
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "動画取得に失敗しました");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /** コメント取得 */
  const fetchComments = useCallback(async (videoId: string) => {
    setCommentsLoading(true);
    setError(null);
    try {
      const result = await apiClient.post<VideoComment[]>(
        `/api/v1/videos/${PROJECT_ID}/${videoId}/comments`,
      );
      setComments(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "コメント取得に失敗しました");
    } finally {
      setCommentsLoading(false);
    }
  }, []);

  /** ニーズ分析 */
  const analyzeComments = useCallback(async (videoId: string) => {
    setAnalysisLoading(true);
    setError(null);
    try {
      const result = await apiClient.post<CommentAnalysis>(
        `/api/v1/videos/${PROJECT_ID}/${videoId}/analyze-comments`,
      );
      setCommentAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ニーズ分析に失敗しました");
    } finally {
      setAnalysisLoading(false);
    }
  }, []);

  return {
    videos,
    loading,
    error,
    fetchVideos,
    searchVideos,
    fetchVideo,
    comments,
    commentsLoading,
    fetchComments,
    commentAnalysis,
    analysisLoading,
    analyzeComments,
  };
}
