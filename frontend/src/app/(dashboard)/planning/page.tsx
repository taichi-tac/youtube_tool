"use client";

import { useState, useEffect } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { usePlanning } from "@/hooks/usePlanning";
import { useRouter } from "next/navigation";
import { apiClient, getProjectId } from "@/lib/api-client";
import type { PlanningIdea } from "@/types/planning";

export default function PlanningPage() {
  const router = useRouter();
  const { ideas, loading, error, generateIdeas, generateMore } = usePlanning();
  const [hasGenerated, setHasGenerated] = useState(false);
  const [tab, setTab] = useState<"generate" | "history">("generate");
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const handleGenerate = async () => {
    await generateIdeas(10);
    setHasGenerated(true);
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const pid = await getProjectId();
      const data = await apiClient.get<any[]>(`/api/v1/planning/${pid}/history`);
      setHistory(data);
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "history") loadHistory();
  }, [tab]);

  return (
    <div>
      <PageHeader title="AI企画提案" description="あなたのチャンネルに最適な企画を自動提案" />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* タブ切替 */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        <button
          onClick={() => setTab("generate")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            tab === "generate" ? "bg-white text-blue-700 shadow-sm" : "text-gray-600"
          }`}
        >
          🎰 新規生成
        </button>
        <button
          onClick={() => setTab("history")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            tab === "history" ? "bg-white text-blue-700 shadow-sm" : "text-gray-600"
          }`}
        >
          📋 過去の企画
        </button>
      </div>

      {/* 過去の企画タブ */}
      {tab === "history" && (
        <div>
          {historyLoading ? (
            <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
          ) : history.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
              <p className="text-sm text-gray-400">まだ企画がありません</p>
              <button onClick={() => setTab("generate")} className="mt-2 text-sm text-blue-600 hover:underline">
                企画を生成する
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">過去の企画 ({history.length}件)</h2>
              {history.map((idea, i) => (
                <IdeaCard key={idea.id || i} idea={idea} rank={i + 1} onUse={() => {
                  const params = new URLSearchParams({
                    title: idea.title,
                    target: idea.target_viewer || "",
                    keyword: idea.keyword || "",
                    promise: idea.reason || "",
                  });
                  router.push(`/scripts/new?${params.toString()}`);
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "generate" && !hasGenerated ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="mb-8 text-center">
            <div className="mb-4 text-6xl">🎰</div>
            <h2 className="text-xl font-bold text-gray-900">企画ガチャ</h2>
            <p className="mt-2 text-sm text-gray-500">
              プロファイルとYouTubeトレンドを分析して<br />
              伸びる企画を自動提案します
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="rounded-2xl bg-gradient-to-r from-purple-600 to-blue-600 px-12 py-4 text-lg font-bold text-white shadow-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 transition-all transform hover:scale-105"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI分析中...
              </span>
            ) : (
              "🎯 企画を提案してもらう"
            )}
          </button>
        </div>
      ) : tab === "generate" ? (
        <div>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">提案企画 ({ideas.length}件)</h2>
            <button
              onClick={() => generateMore(5)}
              disabled={loading}
              className="rounded-lg border border-purple-300 px-4 py-2 text-sm font-medium text-purple-700 hover:bg-purple-50 disabled:opacity-50"
            >
              {loading ? "生成中..." : "もっと見る"}
            </button>
          </div>

          <div className="space-y-4">
            {ideas.map((idea, i) => (
              <IdeaCard key={i} idea={idea} rank={i + 1} onUse={() => {
                const params = new URLSearchParams({
                  title: idea.title,
                  target: idea.target_viewer,
                  keyword: idea.keyword,
                  promise: idea.reason,
                });
                router.push(`/scripts/new?${params.toString()}`);
              }} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function IdeaCard({ idea, rank, onUse }: { idea: PlanningIdea; rank: number; onUse: () => void }) {
  const totalScore = idea.demand_score * idea.niche_score;

  return (
    <div className="rounded-xl border bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500 text-sm font-bold text-white">
          {rank}
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-gray-900">{idea.title}</h3>
          <p className="mt-1 text-xs text-gray-500">KW: {idea.keyword} | ターゲット: {idea.target_viewer}</p>
          <p className="mt-2 text-sm text-gray-700">{idea.reason}</p>

          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-500">需要</span>
              <div className="h-2 w-20 rounded-full bg-gray-200">
                <div className="h-2 rounded-full bg-blue-500" style={{ width: `${idea.demand_score * 10}%` }} />
              </div>
              <span className="text-xs font-medium text-blue-700">{idea.demand_score}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-500">穴場</span>
              <div className="h-2 w-20 rounded-full bg-gray-200">
                <div className="h-2 rounded-full bg-green-500" style={{ width: `${idea.niche_score * 10}%` }} />
              </div>
              <span className="text-xs font-medium text-green-700">{idea.niche_score}</span>
            </div>
            <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-700">
              総合: {totalScore.toFixed(0)}
            </span>
          </div>
        </div>
        <button
          onClick={onUse}
          className="flex-shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700"
        >
          この企画で台本作成
        </button>
      </div>
    </div>
  );
}
