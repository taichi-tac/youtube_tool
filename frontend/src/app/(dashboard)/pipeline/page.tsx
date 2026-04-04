"use client";

import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";
import { useRouter } from "next/navigation";

export default function PipelinePage() {
  const router = useRouter();
  const [urls, setUrls] = useState(["", "", ""]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"input" | "analyzing" | "result">("input");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const updateUrl = (index: number, value: string) => {
    const updated = [...urls];
    updated[index] = value;
    setUrls(updated);
  };

  const validUrls = urls.filter((u) => u.trim());

  const handleAnalyze = async () => {
    if (validUrls.length === 0) return;
    setLoading(true);
    setStep("analyzing");
    setError(null);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<any>(`/api/v1/pipeline/${pid}/full`, {
        video_urls: validUrls,
      });
      setResult(data);
      setStep("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析に失敗しました");
      setStep("input");
    } finally {
      setLoading(false);
    }
  };

  const handleUseProposal = (proposal: any) => {
    const params = new URLSearchParams({
      title: proposal.title || "",
      target: proposal.target || "",
      problem: result?.analysis?.market_gaps?.[0] || "",
      promise: proposal.concept || "",
      uniqueness: proposal.uniqueness || "",
    });
    router.push(`/scripts/new?${params.toString()}`);
  };

  return (
    <div>
      <PageHeader
        title="リサーチ → 企画 → 台本"
        description="伸びてる動画を分析して、あなた専用の企画と台本を一気に作成"
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {step === "input" && (
        <div className="mx-auto max-w-2xl">
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              伸びてる動画のURLを入力（1〜3本）
            </h2>
            <p className="mb-4 text-sm text-gray-500">
              参考にしたい動画のURLを入力すると、共通構造を分析して企画を提案します
            </p>
            <div className="space-y-3">
              {urls.map((url, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-400 w-6">{i + 1}.</span>
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => updateUrl(i, e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="flex-1 rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
            <button
              onClick={handleAnalyze}
              disabled={validUrls.length === 0 || loading}
              className="mt-6 w-full rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 py-3 text-sm font-bold text-white hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
            >
              分析して企画を提案する
            </button>
          </div>
        </div>
      )}

      {step === "analyzing" && (
        <div className="flex flex-col items-center py-20">
          <svg className="animate-spin h-12 w-12 text-blue-600 mb-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-600 font-medium">動画を分析中...</p>
          <p className="text-sm text-gray-400 mt-1">共通構造を抽出しています（30秒〜1分）</p>
        </div>
      )}

      {step === "result" && result && (
        <div className="space-y-6">
          {/* 分析結果 */}
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">分析結果</h2>

            {result.analysis?.analyzed_videos && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">分析した動画</h3>
                {result.analysis.analyzed_videos.map((v: any, i: number) => (
                  <p key={i} className="text-sm text-gray-700">
                    {i + 1}. {v.title} (再生: {v.view_count?.toLocaleString()})
                  </p>
                ))}
              </div>
            )}

            {result.analysis?.success_factors && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">成功要因</h3>
                <ul className="list-disc pl-5 space-y-1">
                  {result.analysis.success_factors.map((f: string, i: number) => (
                    <li key={i} className="text-sm text-gray-700">{f}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.analysis?.market_gaps && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">市場の穴（チャンス）</h3>
                <ul className="list-disc pl-5 space-y-1">
                  {result.analysis.market_gaps.map((g: string, i: number) => (
                    <li key={i} className="text-sm text-green-700 font-medium">{g}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 企画提案 */}
          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">企画提案</h2>
            <div className="space-y-3">
              {result.analysis?.proposals?.map((p: any, i: number) => (
                <div key={i} className="rounded-lg border bg-white p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{p.title}</h3>
                      <p className="mt-1 text-sm text-gray-600">{p.concept}</p>
                      <div className="mt-2 flex gap-3 text-xs text-gray-500">
                        <span>ターゲット: {p.target}</span>
                        <span>差別化: {p.uniqueness}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleUseProposal(p)}
                      className="ml-4 flex-shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700"
                    >
                      台本を作成
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => { setStep("input"); setResult(null); }}
            className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            別の動画で分析する
          </button>
        </div>
      )}
    </div>
  );
}
