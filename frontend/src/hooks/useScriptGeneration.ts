"use client";

import { useState, useCallback, useRef } from "react";
import { apiClient, getProjectId } from "@/lib/api-client";
import type { Script, ScriptGenerateRequest } from "@/types/script";

export function useScriptGeneration() {
  const [scriptId, setScriptId] = useState<string | null>(null);
  const [streamedText, setStreamedText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [targetChars, setTargetChars] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const totalCharsRef = useRef(0);

  /**
   * POST /api/v1/scripts/{project_id}/generate でSSEストリーミング生成。
   * バックエンドは sse_starlette で以下のイベントを返す:
   * - event: start  → { script_id }
   * - event: chunk  → { text }
   * - event: done   → { script_id, word_count }
   * - event: error  → { error }
   */
  const generate = useCallback(async (request: ScriptGenerateRequest, durationMinutes: number = 15) => {
    const target = durationMinutes * 300;
    setTargetChars(target);
    totalCharsRef.current = 0;
    setCharCount(0);
    setGenerating(true);
    setProgress(0);
    setError(null);
    setStreamedText("");
    setScriptId(null);
    setDone(false);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const pid = await getProjectId();
      const response = await apiClient.postStream(
        `/api/v1/scripts/${pid}/generate`,
        request,
        { signal: controller.signal },
      );

      let chunkCount = 0;
      let receivedScriptId: string | null = null;
      let receivedDone = false;

      for await (const { event, data } of apiClient.parseSSE(response)) {
        if (controller.signal.aborted) break;

        try {
          const parsed = JSON.parse(data);

          switch (event) {
            case "start":
              receivedScriptId = parsed.script_id;
              setScriptId(parsed.script_id);
              setProgress(5);
              break;

            case "chunk":
              chunkCount++;
              totalCharsRef.current += (parsed.text || "").length;
              setStreamedText((prev) => prev + parsed.text);
              setCharCount(totalCharsRef.current);
              const pct = target > 0
                ? Math.min(99, Math.round((totalCharsRef.current / target) * 100))
                : Math.min(99, 5 + chunkCount * 2);
              setProgress(pct);
              break;

            case "done":
              receivedScriptId = parsed.script_id;
              receivedDone = true;
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
          // JSONパースエラーは無視
        }
      }

      // ストリーム終了後、doneイベントが来なかった場合も完了扱い
      if (!controller.signal.aborted && !receivedDone) {
        setProgress(100);
        setDone(true);
        setGenerating(false);
        if (receivedScriptId) {
          setScriptId(receivedScriptId);
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
    charCount,
    targetChars,
    error,
    done,
    generate,
    cancel,
  };
}
