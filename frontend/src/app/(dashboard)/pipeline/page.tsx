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

  // 企画出し直し
  const [feedbackSavedMsg, setFeedbackSavedMsg] = useState<string | null>(null);
  const [showRetryForm, setShowRetryForm] = useState(false);
  const [retryFeedback, setRetryFeedback] = useState("");
  const [retryLoading, setRetryLoading] = useState(false);

  const handleRetryWithFeedback = async () => {
    if (!retryFeedback.trim()) return;
    setRetryLoading(true);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<any>(
        `/api/v1/pipeline/${pid}/regenerate-proposals`,
        {
          video_urls: validUrls,
          feedback: retryFeedback.trim(),
          current_proposals: result?.analysis?.proposals || [],
        }
      );
      if (data.proposals) {
        const updated = { ...result };
        updated.analysis = { ...updated.analysis, proposals: data.proposals };
        setResult(updated);
        setShowRetryForm(false);
        setRetryFeedback("");
        if (data.feedback_saved) {
          setFeedbackSavedMsg("指摘をナレッジに保存しました。次回以降の企画生成に反映されます。");
          setTimeout(() => setFeedbackSavedMsg(null), 5000);
        }
      }
    } catch (err) {
      alert("企画の再生成に失敗しました");
    } finally {
      setRetryLoading(false);
    }
  };

  // YouTube検索
  const HISTORY_KEY = "yt_search_history";
  const MAX_HISTORY = 20;
  const RESULTS_HISTORY_KEY = "yt_search_results_history";
  const MAX_RESULTS_HISTORY = 10;

  interface SearchSession {
    keyword: string;
    timestamp: string;
    results: VideoResult[];
  }

  const loadHistory = (): string[] => {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
  };
  const saveToHistory = (query: string) => {
    const prev = loadHistory().filter((q) => q !== query);
    localStorage.setItem(HISTORY_KEY, JSON.stringify([query, ...prev].slice(0, MAX_HISTORY)));
  };

  const loadResultsHistory = (): SearchSession[] => {
    try { return JSON.parse(localStorage.getItem(RESULTS_HISTORY_KEY) || "[]"); } catch { return []; }
  };
  const saveResultsHistory = (keyword: string, results: VideoResult[]) => {
    const prev = loadResultsHistory().filter((s) => s.keyword !== keyword);
    const session: SearchSession = { keyword, timestamp: new Date().toISOString(), results };
    localStorage.setItem(RESULTS_HISTORY_KEY, JSON.stringify([session, ...prev].slice(0, MAX_RESULTS_HISTORY)));
  };

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOrder, setSearchOrder] = useState("relevance");
  const [searchMaxResults, setSearchMaxResults] = useState(10);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<VideoResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    return loadHistory();
  });
  const [showHistory, setShowHistory] = useState(false);
  const [searchResultsHistory, setSearchResultsHistory] = useState<SearchSession[]>(() => {
    if (typeof window === "undefined") return [];
    return loadResultsHistory();
  });
  const [openSession, setOpenSession] = useState<string | null>(null);

  const handleSearch = async (query?: string) => {
    const q = (query ?? searchQuery).trim();
    if (!q) return;
    if (query) setSearchQuery(query);
    setShowHistory(false);
    setSearchLoading(true);
    setSearchError(null);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<VideoResult[]>(`/api/v1/videos/${pid}/search`, {
        query: q,
        max_results: searchMaxResults,
        order: searchOrder,
      });
      setSearchResults(data);
      saveToHistory(q);
      setSearchHistory(loadHistory());
      saveResultsHistory(q, data);
      setSearchResultsHistory(loadResultsHistory());
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "検索に失敗しました");
    } finally {
      setSearchLoading(false);
    }
  };

  const deleteHistory = (item: string) => {
    const updated = loadHistory().filter((q) => q !== item);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    setSearchHistory(updated);
  };

  const copyUrl = (videoId: string) => {
    navigator.clipboard.writeText(`https://www.youtube.com/watch?v=${videoId}`);
    setCopiedId(videoId);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const addToUrls = (videoId: string) => {
    const url = `https://www.youtube.com/watch?v=${videoId}`;
    setUrls((prev) => {
      const emptyIndex = prev.findIndex((u) => !u.trim());
      if (emptyIndex === -1) return prev; // 全枠埋まっていれば何もしない
      const updated = [...prev];
      updated[emptyIndex] = url;
      return updated;
    });
    // 入力欄にスクロール
    window.scrollTo({ top: 0, behavior: "smooth" });
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

          {feedbackSavedMsg && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700 flex items-center gap-2">
              <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {feedbackSavedMsg}
            </div>
          )}

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

          {/* 出し直しフォーム */}
          {showRetryForm && (
            <div className="rounded-xl border-2 border-purple-200 bg-purple-50 p-5">
              <h3 className="mb-2 text-sm font-semibold text-purple-800">企画の改善ポイントを入力</h3>
              <p className="mb-3 text-xs text-purple-600">
                どこが気になったか、どう変えてほしいかを書いてください。フィードバックを反映した新しい企画が生成されます。
              </p>
              <textarea
                value={retryFeedback}
                onChange={(e) => setRetryFeedback(e.target.value)}
                rows={3}
                placeholder="例: もっとニッチなターゲットにしてほしい / タイトルにインパクトが足りない / 差別化が弱い"
                className="mb-3 w-full rounded-lg border border-purple-300 px-4 py-2.5 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
              <div className="flex gap-3">
                <button
                  onClick={handleRetryWithFeedback}
                  disabled={retryLoading || !retryFeedback.trim()}
                  className="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-2 text-sm font-bold text-white hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
                >
                  {retryLoading ? "再生成中..." : "この内容で企画を出し直す"}
                </button>
                <button
                  onClick={() => { setShowRetryForm(false); setRetryFeedback(""); }}
                  className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  キャンセル
                </button>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setShowRetryForm(true)}
              disabled={showRetryForm}
              className="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-2 text-sm font-bold text-white hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
            >
              改善ポイントを指摘して出し直す
            </button>
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="rounded-lg border border-purple-300 px-4 py-2 text-sm font-medium text-purple-600 hover:bg-purple-50 disabled:opacity-50"
            >
              {loading ? "再分析中..." : "そのまま出し直す"}
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
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowHistory(true)}
              onBlur={() => setTimeout(() => setShowHistory(false), 150)}
              placeholder="検索キーワードを入力..."
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {showHistory && searchHistory.length > 0 && (
              <ul className="absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg">
                <li className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">検索履歴</li>
                {searchHistory.map((item) => (
                  <li key={item} className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 cursor-pointer"
                    onMouseDown={() => handleSearch(item)}>
                    <span className="text-sm text-gray-700 truncate">{item}</span>
                    <button
                      type="button"
                      onMouseDown={(e) => { e.stopPropagation(); deleteHistory(item); }}
                      className="ml-2 flex-shrink-0 text-gray-300 hover:text-red-400 text-xs"
                    >✕</button>
                  </li>
                ))}
              </ul>
            )}
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
            onClick={() => handleSearch()}
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

        {searchResults.length > 0 && !searchLoading && (() => {
          const avgVpd = searchResults.reduce((s, v) => s + (v.views_per_day || 0), 0) / searchResults.length;
          const maxVpd = Math.max(...searchResults.map(v => v.views_per_day || 0));
          return (
          <div className="mt-6">
            {/* サマリーバー */}
            <div className="mb-6 grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-blue-600 p-3 text-center text-white">
                <p className="text-xs opacity-80">発見した動画数</p>
                <p className="text-xl font-bold">{searchResults.length}件</p>
              </div>
              <div className="rounded-lg bg-blue-600 p-3 text-center text-white">
                <p className="text-xs opacity-80">平均 日次再生</p>
                <p className="text-xl font-bold">{avgVpd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              </div>
              <div className="rounded-lg bg-blue-600 p-3 text-center text-white">
                <p className="text-xs opacity-80">最大 日次再生</p>
                <p className="text-xl font-bold">{maxVpd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              </div>
            </div>

            {/* タイルグリッド */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {searchResults.map((v) => {
                const engRate = v.view_count ? (((v.like_count || 0) + (v.comment_count || 0)) / v.view_count * 100) : 0;
                const likeRate = v.view_count ? ((v.like_count || 0) / v.view_count * 100) : 0;
                const commentRate = v.view_count ? ((v.comment_count || 0) / v.view_count * 100) : 0;
                return (
                <div key={v.id} className="rounded-xl border bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden">
                  {/* サムネイル */}
                  <div className="relative">
                    {v.thumbnail_url && (
                      <a href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`} target="_blank" rel="noopener noreferrer">
                        <img src={v.thumbnail_url} alt="" className="w-full h-44 object-cover" />
                      </a>
                    )}
                    {v.is_trending && (
                      <span className="absolute top-2 right-2 rounded bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
                        {v.views_per_day?.toLocaleString()}/日
                      </span>
                    )}
                  </div>

                  {/* タイトル・チャンネル */}
                  <div className="p-3">
                    <a
                      href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="text-sm font-semibold text-gray-900 hover:text-blue-600 line-clamp-2"
                    >
                      {v.title}
                    </a>
                    <p className="mt-1 text-xs text-gray-500">{v.channel_title || "-"}</p>
                  </div>

                  {/* 指標グリッド */}
                  <div className="grid grid-cols-2 gap-px bg-gray-100 border-t">
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">再生数</p>
                      <p className="text-sm font-bold text-gray-900">{v.view_count != null ? v.view_count.toLocaleString() : "-"}</p>
                    </div>
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">急上昇率(1日)</p>
                      <p className="text-sm font-bold text-gray-900">{v.views_per_day != null ? v.views_per_day.toLocaleString() : "-"}</p>
                    </div>
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">エンゲージメント率</p>
                      <p className="text-sm font-bold text-gray-900">{engRate.toFixed(2)}%</p>
                    </div>
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">高評価率</p>
                      <p className="text-sm font-bold text-gray-900">{likeRate.toFixed(2)}%</p>
                    </div>
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">コメント率</p>
                      <p className="text-sm font-bold text-gray-900">{commentRate.toFixed(2)}%</p>
                    </div>
                    <div className="bg-white px-3 py-2">
                      <p className="text-[10px] text-gray-400">高評価数</p>
                      <p className="text-sm font-bold text-gray-900">{v.like_count != null ? v.like_count.toLocaleString() : "-"}</p>
                    </div>
                  </div>

                  {/* ボタン・フッター */}
                  <div className="flex gap-2 border-t p-3">
                    <a
                      href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="flex-1 rounded-lg bg-red-500 py-1.5 text-center text-xs font-bold text-white hover:bg-red-600"
                    >
                      動画を見る
                    </a>
                    <button
                      onClick={() => copyUrl(v.youtube_video_id)}
                      className={`flex-1 rounded-lg border py-1.5 text-center text-xs font-bold transition-colors ${
                        copiedId === v.youtube_video_id ? "border-green-400 text-green-600 bg-green-50" : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      {copiedId === v.youtube_video_id ? "コピー済" : "URLコピー"}
                    </button>
                    <button
                      onClick={() => addToUrls(v.youtube_video_id)}
                      disabled={!urls.some((u) => !u.trim())}
                      className="flex-1 rounded-lg bg-purple-600 py-1.5 text-center text-xs font-bold text-white hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      分析対象に追加
                    </button>
                  </div>

                  <div className="flex border-t px-3 py-2 text-[10px] text-gray-400 gap-4">
                    <span>{formatDuration(v.duration_seconds)}</span>
                    <span>{formatDate(v.published_at)}</span>
                  </div>
                </div>
                );
              })}
            </div>
          </div>
          );
        })()}
      </div>

      {/* 検索結果履歴 */}
      {searchResultsHistory.length > 0 && (
        <div className="mt-10 border-t pt-6">
          <h3 className="mb-4 text-base font-semibold text-gray-700">検索結果履歴</h3>
          <div className="space-y-2">
            {searchResultsHistory.map((session) => {
              const isOpen = openSession === session.keyword;
              const d = new Date(session.timestamp);
              const label = `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
              return (
                <div key={session.keyword} className="rounded-xl border bg-white shadow-sm overflow-hidden">
                  <button
                    className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                    onClick={() => setOpenSession(isOpen ? null : session.keyword)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-800">🔍 {session.keyword}</span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">{session.results.length}件</span>
                      <span className="text-xs text-gray-400">{label}</span>
                    </div>
                    <span className="text-gray-400 text-sm">{isOpen ? "▲" : "▼"}</span>
                  </button>
                  {isOpen && (
                    <div className="border-t px-4 pb-4 pt-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {session.results.map((v) => {
                          const engRate = v.view_count ? (((v.like_count || 0) + (v.comment_count || 0)) / v.view_count * 100) : 0;
                          return (
                            <div key={v.id} className="rounded-xl border bg-white shadow-sm overflow-hidden">
                              {v.thumbnail_url && (
                                <a href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`} target="_blank" rel="noopener noreferrer">
                                  <img src={v.thumbnail_url} alt="" className="w-full h-36 object-cover" />
                                </a>
                              )}
                              <div className="p-3">
                                <a
                                  href={`https://www.youtube.com/watch?v=${v.youtube_video_id}`}
                                  target="_blank" rel="noopener noreferrer"
                                  className="text-sm font-semibold text-gray-900 hover:text-blue-600 line-clamp-2"
                                >
                                  {v.title}
                                </a>
                                <p className="mt-1 text-xs text-gray-500">{v.channel_title || "-"}</p>
                                <div className="mt-2 flex gap-3 text-xs text-gray-500">
                                  <span>再生: {v.view_count != null ? v.view_count.toLocaleString() : "-"}</span>
                                  <span>ENG: {engRate.toFixed(2)}%</span>
                                </div>
                              </div>
                              <div className="flex gap-2 border-t p-2">
                                <button
                                  onClick={() => addToUrls(v.youtube_video_id)}
                                  disabled={!urls.some((u) => !u.trim())}
                                  className="flex-1 rounded-lg bg-purple-600 py-1.5 text-center text-xs font-bold text-white hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                  分析対象に追加
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
