"use client";

import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";
import { useRouter } from "next/navigation";

interface VideoResult {
  id: string;
  youtube_video_id: string;
  title: string;
  channel_title?: string;
  view_count?: number;
  like_count?: number;
  comment_count?: number;
  published_at?: string;
  thumbnail_url?: string;
  views_per_day?: number;
  is_trending: boolean;
  duration_seconds?: number;
}

function formatDuration(seconds?: number): string {
  if (!seconds) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

export default function PipelinePage() {
  const router = useRouter();
  const [urls, setUrls] = useState(["", "", ""]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"input" | "analyzing" | "result">("input");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // ペルソナモーダル
  const [personaModal, setPersonaModal] = useState<{ index: number; proposal: any } | null>(null);
  const [editTarget, setEditTarget] = useState("");
  const [editInnerVoice, setEditInnerVoice] = useState("");
  const [personaLoading, setPersonaLoading] = useState(false);

  const openPersonaModal = (index: number, proposal: any) => {
    setPersonaModal({ index, proposal });
    setEditTarget(proposal.target || "");
    setEditInnerVoice(proposal.inner_voice || "");
  };

  const savePersonaEdit = () => {
    if (!personaModal || !result) return;
    const updated = { ...result };
    updated.analysis.proposals[personaModal.index] = {
      ...personaModal.proposal,
      target: editTarget,
      inner_voice: editInnerVoice,
    };
    setResult(updated);
    setPersonaModal(null);
  };

  const retryPersona = async () => {
    if (!personaModal) return;
    setPersonaLoading(true);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<{ target: string; inner_voice: string }>(
        `/api/v1/pipeline/${pid}/regenerate-persona`,
        {
          title: personaModal.proposal.title || "",
          concept: personaModal.proposal.concept || "",
          current_target: editTarget,
          current_inner_voice: editInnerVoice,
        }
      );
      if (data.target) setEditTarget(data.target);
      if (data.inner_voice) setEditInnerVoice(data.inner_voice);
    } catch (err) {
      alert("ペルソナ再生成に失敗しました");
    } finally {
      setPersonaLoading(false);
    }
  };

  // YouTube検索
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOrder, setSearchOrder] = useState("relevance");
  const [searchMaxResults, setSearchMaxResults] = useState(10);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<VideoResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError(null);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<VideoResult[]>(`/api/v1/videos/${pid}/search`, {
        query: searchQuery.trim(),
        max_results: searchMaxResults,
        order: searchOrder,
      });
      setSearchResults(data);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "検索に失敗しました");
    } finally {
      setSearchLoading(false);
    }
  };

  const copyUrl = (videoId: string) => {
    navigator.clipboard.writeText(`https://www.youtube.com/watch?v=${videoId}`);
    setCopiedId(videoId);
    setTimeout(() => setCopiedId(null), 1500);
  };

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
                      <div className="mt-2 text-xs text-gray-500">
                        <button
                          onClick={(e) => { e.stopPropagation(); openPersonaModal(i, p); }}
                          className="text-left hover:bg-blue-50 rounded px-1 py-0.5 -mx-1 transition-colors group"
                          title="クリックしてペルソナを詳細表示・編集"
                        >
                          <span className="group-hover:text-blue-600">ペルソナ: {p.target}</span>
                          {p.inner_voice && (
                            <p className="mt-1 italic text-gray-400 group-hover:text-blue-400">"{p.inner_voice}"</p>
                          )}
                          <span className="ml-1 text-blue-400 opacity-0 group-hover:opacity-100 text-[10px]">[ 編集 ]</span>
                        </button>
                        <p className="mt-1">差別化: {p.uniqueness}</p>
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

          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-2 text-sm font-bold text-white hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
            >
              {loading ? "再分析中..." : "同じURLで企画を出し直す"}
            </button>
            <button
              onClick={() => { setStep("input"); setResult(null); }}
              className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              別の動画で分析する
            </button>
          </div>
        </div>
      )}

      {/* ペルソナ編集モーダル */}
      {personaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setPersonaModal(null)}>
          <div className="mx-4 w-full max-w-lg rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">ペルソナ設計</h3>
              <button onClick={() => setPersonaModal(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>

            <p className="mb-4 text-xs text-gray-500 bg-gray-50 rounded p-2">
              企画: {personaModal.proposal.title}
            </p>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">ペルソナ（具体的な一人）</label>
                <textarea
                  value={editTarget}
                  onChange={(e) => setEditTarget(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="年齢・職業・状況・悩みを含む具体的な人物像"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">心の声（本音・不安・葛藤）</label>
                <textarea
                  value={editInnerVoice}
                  onChange={(e) => setEditInnerVoice(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border px-3 py-2 text-sm italic focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="そのペルソナが心の中で思っていること"
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={retryPersona}
                disabled={personaLoading}
                className="rounded-lg border border-purple-300 px-4 py-2 text-sm font-medium text-purple-600 hover:bg-purple-50 disabled:opacity-50"
              >
                {personaLoading ? "再生成中..." : "AIで再生成"}
              </button>
              <button
                onClick={savePersonaEdit}
                className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* YouTube動画検索セクション */}
      <div className="mt-12 border-t pt-8">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">YouTube動画検索</h2>
        <p className="mb-4 text-sm text-gray-500">
          キーワードでYouTube動画を検索し、再生数・トレンドを確認できます
        </p>

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
              placeholder="検索キーワードを入力..."
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <select
            value={searchOrder}
            onChange={(e) => setSearchOrder(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="relevance">関連度順</option>
            <option value="viewCount">再生数順</option>
            <option value="date">新着順</option>
            <option value="rating">評価順</option>
          </select>
          <select
            value={searchMaxResults}
            onChange={(e) => setSearchMaxResults(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value={10}>10件</option>
            <option value={20}>20件</option>
            <option value={30}>30件</option>
            <option value={50}>50件</option>
          </select>
          <button
            onClick={handleSearch}
            disabled={searchLoading || !searchQuery.trim()}
            className="rounded-lg bg-gradient-to-r from-green-600 to-teal-600 px-6 py-2.5 text-sm font-bold text-white hover:from-green-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {searchLoading ? "検索中..." : "検索"}
          </button>
        </div>

        {searchError && (
          <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{searchError}</div>
        )}

        {searchLoading && (
          <div className="flex items-center justify-center py-12">
            <svg className="animate-spin h-8 w-8 text-green-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        )}

        {searchResults.length > 0 && !searchLoading && (
          <div className="mt-6">
            <p className="mb-3 text-sm font-medium text-gray-600">
              検索結果: {searchResults.length}件
            </p>
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">動画</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">チャンネル</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">再生数</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">日平均</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">高評価</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">コメント</th>
                    <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">時間</th>
                    <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">公開日</th>
                    <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">URL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {searchResults.map((v) => (
                    <tr key={v.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {v.thumbnail_url && (
                            <a
                              href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <img
                                src={v.thumbnail_url}
                                alt=""
                                className="h-14 w-24 rounded object-cover flex-shrink-0"
                              />
                            </a>
                          )}
                          <a
                            href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-gray-900 hover:text-blue-600 line-clamp-2 max-w-[280px]"
                          >
                            {v.title}
                          </a>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{v.channel_title || "-"}</td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-900 whitespace-nowrap">
                        {v.view_count != null ? v.view_count.toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm whitespace-nowrap">
                        {v.views_per_day != null ? (
                          <span className={v.is_trending ? "font-bold text-orange-600" : "text-gray-600"}>
                            {v.views_per_day.toLocaleString()}
                            {v.is_trending && " 🔥"}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-600 whitespace-nowrap">
                        {v.like_count != null ? v.like_count.toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-600 whitespace-nowrap">
                        {v.comment_count != null ? v.comment_count.toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600 whitespace-nowrap">
                        {formatDuration(v.duration_seconds)}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600 whitespace-nowrap">
                        {formatDate(v.published_at)}
                      </td>
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        <button
                          onClick={() => copyUrl(v.youtube_video_id)}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
                          title="URLをコピー"
                        >
                          {copiedId === v.youtube_video_id ? (
                            <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                              <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                            </svg>
                          )}
                          {copiedId === v.youtube_video_id ? "コピー済" : "コピー"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
