"use client";

import { useState, useCallback, useRef } from "react";
import { apiClient, PROJECT_ID } from "@/lib/api-client";
import type { Script, ScriptGenerateRequest } from "@/types/script";

export function useScriptGeneration() {
  const [scriptId, setScriptId] = useState<string | null>(null);
  const [streamedText, setStreamedText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  /**
   * POST /api/v1/scripts/{project_id}/generate でSSEストリーミング生成。
   * バックエンドは sse_starlette で以下のイベントを返す:
   * - event: start  → { script_id }
   * - event: chunk  → { text }
   * - event: done   → { script_id, word_count }
   * - event: error  → { error }
   */
  const generate = useCallback(async (request: ScriptGenerateRequest) => {
    setGenerating(true);
    setProgress(0);
    setError(null);
    setStreamedText("");
    setScriptId(null);
    setDone(false);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await apiClient.postStream(
        `/api/v1/scripts/${PROJECT_ID}/generate`,
        request,
        { signal: controller.signal },
      );

      let chunkCount = 0;

      for await (const { event, data } of apiClient.parseSSE(response)) {
        if (controller.signal.aborted) break;

        try {
          const parsed = JSON.parse(data);

          switch (event) {
            case "start":
              setScriptId(parsed.script_id);
              setProgress(5);
              break;

            case "chunk":
              chunkCount++;
              setStreamedText((prev) => prev + parsed.text);
              // 進捗を5%〜90%の範囲で推定
              setProgress(Math.min(90, 5 + chunkCount * 2));
              break;

            case "done":
              setScriptId(parsed.script_id);
              setProgress(100);
              setDone(true);
              setGenerating(false);
              break;

            case "error":
              setError(parsed.error || "台本生成中にエラーが発生しました");
              setGenerating(false);
              break;
          }
        } catch {
          // JSONパースエラーは無視（空行など）
        }
      }

      // ストリーム終了後、生成完了していなければ完了扱い
      if (!controller.signal.aborted) {
        setGenerating(false);
        if (!done) {
          setProgress(100);
          setDone(true);
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError(err instanceof Error ? err.message : "台本生成に失敗しました");
      }
      setGenerating(false);
    }
  }, [done]);

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setGenerating(false);
  }, []);

  return {
    scriptId,
    streamedText,
    generating,
    progress,
    error,
    done,
    generate,
    cancel,
  };
}
