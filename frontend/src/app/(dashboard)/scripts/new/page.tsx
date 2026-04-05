"use client";

import { useState, useEffect } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { useScriptGeneration } from "@/hooks/useScriptGeneration";
import { useKeywordSearch } from "@/hooks/useKeywordSearch";
import { useKnowledgeSearch } from "@/hooks/useKnowledgeSearch";
import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import type { WizardStep, ScriptGenerateRequest } from "@/types/script";

const steps: { step: WizardStep; label: string }[] = [
  { step: 1, label: "キーワード選択" },
  { step: 2, label: "外側設計" },
  { step: 3, label: "ナレッジ確認" },
  { step: 4, label: "生成実行" },
];

export default function ScriptNewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    scriptId,
    streamedText,
    generating,
    progress,
    error: genError,
    done,
    generate,
    cancel,
  } = useScriptGeneration();
  const {
    keywords,
    suggestions,
    loading: kwLoading,
    error: kwError,
    fetchKeywords,
    suggest,
    saveKeyword,
  } = useKeywordSearch();
  const {
    chunks: knowledgeChunks,
    loading: kgLoading,
    error: kgError,
    search: searchKnowledge,
  } = useKnowledgeSearch();

  const [currentStep, setCurrentStep] = useState<WizardStep>(1);

  // Step 1: keyword
  const [seedInput, setSeedInput] = useState("");
  const [selectedKeywordId, setSelectedKeywordId] = useState<string | null>(null);
  const [selectedKeywordText, setSelectedKeywordText] = useState("");

  // Step 2: outer design
  const [title, setTitle] = useState("");
  const [targetViewer, setTargetViewer] = useState("");
  const [viewerProblem, setViewerProblem] = useState("");
  const [promise, setPromise] = useState("");
  const [uniqueness, setUniqueness] = useState("");
  const [duration, setDuration] = useState(15); // 尺（分）

  // Step 3: knowledge
  const [useRag, setUseRag] = useState(false);

  // URLパラメータから自動入力（企画提案・一気通貫からの遷移）
  useEffect(() => {
    const paramTitle = searchParams.get("title");
    const paramTarget = searchParams.get("target");
    const paramProblem = searchParams.get("problem");
    const paramPromise = searchParams.get("promise");
    const paramUniqueness = searchParams.get("uniqueness");
    const paramKeyword = searchParams.get("keyword");

    if (paramTitle) setTitle(paramTitle);
    if (paramTarget) setTargetViewer(paramTarget);
    if (paramProblem) setViewerProblem(paramProblem);
    if (paramPromise) setPromise(paramPromise);
    if (paramUniqueness) setUniqueness(paramUniqueness);
    if (paramKeyword) {
      setSelectedKeywordText(paramKeyword);
      setSeedInput(paramKeyword);
    }

    // パラメータがあればSTEP 2（外側設計）から開始
    if (paramTitle || paramTarget) {
      setCurrentStep(2);
      setUseRag(true);
    }
  }, [searchParams]);

  useEffect(() => {
    fetchKeywords();
  }, [fetchKeywords]);

  // Step 3 auto-search when entering step 3
  useEffect(() => {
    if (currentStep === 3 && (title || selectedKeywordText)) {
      searchKnowledge(`${title} ${selectedKeywordText}`.trim());
    }
  }, [currentStep, title, selectedKeywordText, searchKnowledge]);

  const handleSuggest = () => {
    if (seedInput.trim()) suggest(seedInput.trim());
  };

  const handleSelectKeyword = (kw: { id?: string; keyword: string }) => {
    setSelectedKeywordId(kw.id || null);
    setSelectedKeywordText(kw.keyword);
    if (!title) setTitle(kw.keyword);
  };

  const handleSaveSuggestion = async (s: string) => {
    const saved = await saveKeyword(s, seedInput.trim());
    if (saved) {
      handleSelectKeyword({ id: saved.id, keyword: saved.keyword });
    }
  };

  const handleGenerate = () => {
    const durationContext = `動画の尺は約${duration}分（約${duration * 300}文字）を想定してください。`;
    const request: ScriptGenerateRequest = {
      title: title || selectedKeywordText || "無題の台本",
      keyword_id: selectedKeywordId || undefined,
      target_viewer: targetViewer || "一般視聴者",
      viewer_problem: viewerProblem || undefined,
      promise: promise || undefined,
      uniqueness: uniqueness || undefined,
      additional_context: durationContext,
      use_rag: useRag,
    };
    generate(request);
  };

  const handleNext = () => {
    if (currentStep < 4) setCurrentStep((currentStep + 1) as WizardStep);
  };
  const handleBack = () => {
    if (currentStep > 1) setCurrentStep((currentStep - 1) as WizardStep);
  };

  const error = genError || kwError || kgError;

  return (
    <div>
      <PageHeader title="台本生成ウィザード" description="4ステップで台本を生成" />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="mx-auto max-w-3xl">
        {/* Step Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map(({ step, label }, index) => (
              <div key={step} className="flex flex-1 items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                      step < currentStep
                        ? "bg-blue-600 text-white"
                        : step === currentStep
                        ? "bg-blue-600 text-white ring-4 ring-blue-100"
                        : "bg-gray-200 text-gray-500",
                    )}
                  >
                    {step < currentStep ? "\u2713" : step}
                  </div>
                  <span
                    className={cn(
                      "mt-2 text-xs font-medium",
                      step <= currentStep ? "text-blue-600" : "text-gray-400",
                    )}
                  >
                    {label}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "mx-2 h-0.5 flex-1",
                      step < currentStep ? "bg-blue-600" : "bg-gray-200",
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6">
          {/* ============ STEP 1: キーワード選択 ============ */}
          {currentStep === 1 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">キーワードを選択</h2>

              {/* サジェスト取得 */}
              <div className="mb-4 flex gap-2">
                <input
                  type="text"
                  value={seedInput}
                  onChange={(e) => setSeedInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleSuggest())}
                  placeholder="シードキーワードを入力..."
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  onClick={handleSuggest}
                  disabled={kwLoading || !seedInput.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {kwLoading ? "取得中..." : "サジェスト"}
                </button>
              </div>

              {/* サジェスト結果 */}
              {suggestions.length > 0 && (
                <div className="mb-4 max-h-48 overflow-y-auto rounded border border-gray-200">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSaveSuggestion(s)}
                      className={cn(
                        "block w-full px-4 py-2 text-left text-sm hover:bg-blue-50 transition-colors",
                        selectedKeywordText === s
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-gray-700",
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {/* 保存済みキーワード */}
              {keywords.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-gray-500">保存済みキーワード:</p>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((kw) => (
                      <button
                        key={kw.id}
                        onClick={() =>
                          handleSelectKeyword({ id: kw.id, keyword: kw.keyword })
                        }
                        className={cn(
                          "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                          selectedKeywordId === kw.id
                            ? "bg-blue-600 text-white border-blue-600"
                            : "bg-white text-gray-700 border-gray-300 hover:border-blue-400",
                        )}
                      >
                        {kw.keyword}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {selectedKeywordText && (
                <div className="mt-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
                  選択中: <strong>{selectedKeywordText}</strong>
                </div>
              )}
            </div>
          )}

          {/* ============ STEP 2: 外側設計 ============ */}
          {currentStep === 2 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">外側設計</h2>
              <p className="mb-4 text-sm text-gray-500">動画の方向性を設定してください。</p>
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    動画タイトル
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="動画のタイトル"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    ターゲット視聴者 (target_viewer)
                  </label>
                  <input
                    type="text"
                    value={targetViewer}
                    onChange={(e) => setTargetViewer(e.target.value)}
                    placeholder="例: 副業に興味がある20-30代サラリーマン"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    視聴者の悩み (viewer_problem)
                  </label>
                  <textarea
                    value={viewerProblem}
                    onChange={(e) => setViewerProblem(e.target.value)}
                    placeholder="視聴者が抱えている具体的な悩み"
                    rows={2}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    動画の約束 (promise)
                  </label>
                  <textarea
                    value={promise}
                    onChange={(e) => setPromise(e.target.value)}
                    placeholder="この動画を見ると何が得られるか"
                    rows={2}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    独自性 (uniqueness)
                  </label>
                  <textarea
                    value={uniqueness}
                    onChange={(e) => setUniqueness(e.target.value)}
                    placeholder="他の動画との差別化ポイント"
                    rows={2}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    動画の尺
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min={3}
                      max={180}
                      step={1}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      className="flex-1"
                    />
                    <span className="w-20 text-right text-lg font-bold text-blue-600">{duration}分</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">
                    約{(duration * 300).toLocaleString()}文字の台本を生成します
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ============ STEP 3: ナレッジ確認 ============ */}
          {currentStep === 3 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">ナレッジ確認</h2>
              <p className="mb-4 text-sm text-gray-500">
                RAG検索結果です。台本生成時にナレッジを参照する場合は「RAGを使用」をONにしてください。
              </p>

              <label className="mb-4 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={(e) => setUseRag(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">RAGを使用して台本生成</span>
              </label>

              {kgLoading ? (
                <div className="py-8 text-center text-sm text-gray-500">ナレッジ検索中...</div>
              ) : knowledgeChunks.length > 0 ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {knowledgeChunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="rounded-lg border border-gray-200 p-3"
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-xs font-medium text-blue-600">
                          {chunk.source_file}
                        </span>
                        {chunk.score != null && (
                          <span className="text-xs text-gray-400">
                            スコア: {chunk.score.toFixed(3)}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700 line-clamp-4">{chunk.content}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
                  関連するナレッジが見つかりませんでした
                </div>
              )}
            </div>
          )}

          {/* ============ STEP 4: 生成実行 ============ */}
          {currentStep === 4 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">生成実行</h2>

              {/* 設定確認 */}
              <div className="mb-6 space-y-2 rounded-lg bg-gray-50 p-4">
                <h3 className="text-sm font-medium text-gray-700">設定内容の確認</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>
                    <span className="font-medium">キーワード:</span>{" "}
                    {selectedKeywordText || "未選択"}
                  </p>
                  <p>
                    <span className="font-medium">タイトル:</span> {title || "未設定"}
                  </p>
                  <p>
                    <span className="font-medium">ターゲット:</span>{" "}
                    {targetViewer || "一般視聴者"}
                  </p>
                  <p>
                    <span className="font-medium">悩み:</span>{" "}
                    {viewerProblem || "未設定"}
                  </p>
                  <p>
                    <span className="font-medium">約束:</span> {promise || "未設定"}
                  </p>
                  <p>
                    <span className="font-medium">独自性:</span>{" "}
                    {uniqueness || "未設定"}
                  </p>
                  <p>
                    <span className="font-medium">尺:</span>{" "}
                    {duration}分（約{(duration * 300).toLocaleString()}文字）
                  </p>
                  <p>
                    <span className="font-medium">RAG:</span>{" "}
                    {useRag ? "使用する" : "使用しない"}
                  </p>
                </div>
              </div>

              {/* プログレスバー */}
              {generating && (
                <div className="mb-4">
                  <div className="mb-2 flex justify-between text-sm text-gray-600">
                    <span>生成中...</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-gray-200">
                    <div
                      className="h-3 rounded-full bg-blue-600 transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* SSEストリーミング出力 */}
              {streamedText && (
                <div className="mb-4 max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <h3 className="mb-2 text-xs font-semibold text-gray-500">
                    生成テキスト (リアルタイム)
                  </h3>
                  <div className="whitespace-pre-wrap text-sm text-gray-800">
                    {streamedText}
                  </div>
                </div>
              )}

              {/* 完了メッセージ */}
              {done && scriptId && (
                <div className="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700">
                  台本の生成が完了しました!{" "}
                  <button
                    onClick={() => router.push(`/scripts/${scriptId}`)}
                    className="font-medium underline hover:text-green-900"
                  >
                    台本を編集する
                  </button>
                </div>
              )}

              {/* 生成ボタン */}
              <div className="flex gap-3">
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="flex-1 rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {generating ? "生成中..." : "台本を生成する"}
                </button>
                {generating && (
                  <button
                    onClick={cancel}
                    className="rounded-lg border border-red-300 px-4 py-3 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                  >
                    キャンセル
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-6 flex justify-between">
            <button
              onClick={handleBack}
              disabled={currentStep === 1 || generating}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              戻る
            </button>
            {currentStep < 4 && (
              <button
                onClick={handleNext}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                次へ
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
