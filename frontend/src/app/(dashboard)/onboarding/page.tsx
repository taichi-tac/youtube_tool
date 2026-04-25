"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getProjectId } from "@/lib/api-client";

const GENRE_CHIPS = ["恋愛", "ビジネス", "副業", "美容", "筋トレ", "料理", "ゲーム", "教育", "投資", "転職", "ダイエット", "プログラミング"];
const STYLE_CHIPS = ["ノウハウ系", "エンタメ系", "Vlog系", "解説系", "ストーリー系", "比較/レビュー系"];

type InputMode = "url" | "text" | "manual";

export default function ConceptPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Step 1: 入力方式
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [urlInput, setUrlInput] = useState("");
  const [textInput, setTextInput] = useState("");

  // Step 2: AI分析結果 → 選択/リライト
  const [genre, setGenre] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [contentStyle, setContentStyle] = useState("");
  const [strengths, setStrengths] = useState("");
  const [conceptSuggestion, setConceptSuggestion] = useState("");

  // Step 3: チャンネル
  const [likeChannels, setLikeChannels] = useState<string[]>([""]);
  const [dislikeChannels, setDislikeChannels] = useState<string[]>([""]);
  const [suggestedChannels, setSuggestedChannels] = useState<any[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(false);

  // API Keys
  const [youtubeApiKey, setYoutubeApiKey] = useState("");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");

  // 既存プロファイル読み込み
  useEffect(() => {
    async function loadProfile() {
      try {
        const pid = await getProjectId();
        const profile = await apiClient.get<any>(`/api/v1/projects/${pid}/profile`);
        if (profile) {
          if (profile.genre) setGenre(profile.genre);
          if (profile.target_audience) setTargetAudience(profile.target_audience);
          if (profile.content_style) setContentStyle(profile.content_style);
          if (profile.strengths) setStrengths(profile.strengths);
          if (profile.concept) setConceptSuggestion(profile.concept);
          if (profile.benchmark_channels?.length > 0) {
            setLikeChannels(profile.benchmark_channels);
          }
          if (profile.youtube_api_key) setYoutubeApiKey(profile.youtube_api_key);
          if (profile.anthropic_api_key) setAnthropicApiKey(profile.anthropic_api_key);
        }
      } catch { /* 新規ユーザー */ }
      finally { setLoading(false); }
    }
    loadProfile();
  }, []);

  // URL/テキスト分析
  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const pid = await getProjectId();
      let result: any;
      if (inputMode === "url" && urlInput.trim()) {
        result = await apiClient.post<any>(`/api/v1/concept/${pid}/analyze-url`, { url: urlInput });
      } else if (inputMode === "text" && textInput.trim()) {
        result = await apiClient.post<any>(`/api/v1/concept/${pid}/analyze-text`, { text: textInput });
      }
      if (result && !result.error) {
        if (result.genre) setGenre(result.genre);
        if (result.target_audience) setTargetAudience(result.target_audience);
        if (result.content_style) setContentStyle(result.content_style);
        if (result.strengths) setStrengths(result.strengths);
        if (result.concept_suggestion) setConceptSuggestion(result.concept_suggestion);
        setStep(2);
      }
    } catch (err) {
      alert("分析に失敗しました: " + (err instanceof Error ? err.message : ""));
    } finally {
      setAnalyzing(false);
    }
  };

  // チャンネル提案
  const handleSuggestChannels = async () => {
    setChannelsLoading(true);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<any[]>(`/api/v1/concept/${pid}/suggest-channels`, {
        genre, target_audience: targetAudience,
      });
      setSuggestedChannels(data);
    } catch { /* ignore */ }
    finally { setChannelsLoading(false); }
  };

  const addChannel = (list: string[], setter: (v: string[]) => void) => {
    if (list.length < 10) setter([...list, ""]);
  };
  const updateChannel = (list: string[], setter: (v: string[]) => void, i: number, val: string) => {
    const updated = [...list]; updated[i] = val; setter(updated);
  };
  const removeChannel = (list: string[], setter: (v: string[]) => void, i: number) => {
    setter(list.filter((_, idx) => idx !== i));
  };
  const selectSuggested = (name: string) => {
    const newList = [...likeChannels.filter(c => c.trim()), name];
    setLikeChannels(newList);
  };

  // 保存
  const handleSave = async () => {
    setSaving(true);
    try {
      const pid = await getProjectId();
      await apiClient.patch(`/api/v1/projects/${pid}/profile`, {
        genre,
        target_audience: targetAudience,
        content_style: contentStyle,
        strengths,
        concept: conceptSuggestion,
        benchmark_channels: likeChannels.filter(c => c.trim()),
        youtube_api_key: youtubeApiKey || undefined,
        anthropic_api_key: anthropicApiKey || undefined,
      });
      router.push("/pipeline");
    } catch (err) {
      alert("保存に失敗しました: " + (err instanceof Error ? err.message : ""));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>;

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">STEP 1: コンセプト設定</h1>
      <p className="mb-8 text-sm text-gray-500">
        あなたのチャンネルのコンセプトを設定します。URL、テキスト、または手動入力で情報を入力してください。
      </p>

      {/* ステップ */}
      <div className="mb-8 flex items-center gap-2">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
              s <= step ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-500"
            }`}>{s < step ? "✓" : s}</div>
            {s < 3 && <div className={`mx-1 h-0.5 w-8 ${s < step ? "bg-blue-600" : "bg-gray-200"}`} />}
          </div>
        ))}
        <span className="ml-2 text-xs text-gray-500">
          {step === 1 ? "情報入力" : step === 2 ? "コンセプト確認・編集" : "チャンネル設定"}
        </span>
      </div>

      <div className="rounded-xl border bg-white p-6 shadow-sm">
        {/* STEP 1: 入力 */}
        {step === 1 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">情報を入力してください</h2>
            <p className="mb-4 text-sm text-gray-500">
              LP・動画URL、テキスト貼付、または手動入力から選べます。AIが自動分析します。
            </p>

            <div className="mb-4 flex gap-2">
              {([["url", "URL入力"], ["text", "テキスト貼付"], ["manual", "手動入力"]] as const).map(([mode, label]) => (
                <button
                  key={mode}
                  onClick={() => setInputMode(mode)}
                  className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                    inputMode === mode ? "border-blue-600 bg-blue-600 text-white" : "text-gray-600 hover:border-blue-400"
                  }`}
                >{label}</button>
              ))}
            </div>

            {inputMode === "url" && (
              <div>
                <input
                  type="text" value={urlInput} onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="YouTubeチャンネルURL、動画URL、LP URL等を入力"
                  className="mb-3 w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
                />
                <p className="mb-4 text-xs text-gray-400">
                  チャンネルURL（例: youtube.com/@handle）を入力すると、人気動画から自動分析します
                </p>
              </div>
            )}

            {inputMode === "text" && (
              <textarea
                value={textInput} onChange={(e) => setTextInput(e.target.value)}
                placeholder="商品情報、チャンネル概要、やりたいことなどを自由に貼り付けてください"
                rows={6}
                className="mb-3 w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
              />
            )}

            {inputMode === "manual" && (
              <div className="space-y-3">
                <input type="text" value={genre} onChange={(e) => setGenre(e.target.value)}
                  placeholder="ジャンル（例: 恋愛、ビジネス）"
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
                <div className="flex flex-wrap gap-2">
                  {GENRE_CHIPS.map((g) => (
                    <button key={g} onClick={() => setGenre(g)}
                      className={`rounded-full border px-3 py-1 text-xs ${genre === g ? "border-blue-600 bg-blue-600 text-white" : "text-gray-600 hover:border-blue-400"}`}
                    >{g}</button>
                  ))}
                </div>
                <input type="text" value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="ターゲット（例: 20-30代男性サラリーマン）"
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
                <textarea value={strengths} onChange={(e) => setStrengths(e.target.value)}
                  placeholder="強み・独自性（例: 元営業マンで心理学に詳しい）" rows={3}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
              </div>
            )}

            <div className="mt-4 flex justify-between">
              <div />
              {inputMode === "manual" ? (
                <button onClick={() => setStep(2)}
                  className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  次へ
                </button>
              ) : (
                <button onClick={handleAnalyze} disabled={analyzing || (!urlInput.trim() && !textInput.trim())}
                  className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                  {analyzing ? "AI分析中..." : "AIで分析する"}
                </button>
              )}
            </div>
          </div>
        )}

        {/* STEP 2: AI分析結果の確認・編集 */}
        {step === 2 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">コンセプトを確認・編集</h2>
            <p className="mb-4 text-sm text-gray-500">AI分析結果です。そのまま使うか、編集してください。</p>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">コンセプト（1行）</label>
                <input type="text" value={conceptSuggestion} onChange={(e) => setConceptSuggestion(e.target.value)}
                  placeholder="例: 駆け引きをしない恋愛チャンネル"
                  className="w-full rounded-lg border-2 border-blue-300 px-4 py-3 text-sm font-medium focus:border-blue-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">ジャンル</label>
                <input type="text" value={genre} onChange={(e) => setGenre(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
                <div className="mt-2 flex flex-wrap gap-1">
                  {GENRE_CHIPS.map((g) => (
                    <button key={g} onClick={() => setGenre(g)}
                      className={`rounded-full border px-2 py-0.5 text-xs ${genre === g ? "border-blue-600 bg-blue-50 text-blue-700" : "text-gray-500"}`}
                    >{g}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">ターゲット</label>
                <input type="text" value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">コンテンツスタイル</label>
                <div className="flex flex-wrap gap-2">
                  {STYLE_CHIPS.map((s) => (
                    <button key={s} onClick={() => setContentStyle(s)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                        contentStyle === s ? "border-blue-600 bg-blue-600 text-white" : "text-gray-600 hover:border-blue-400"
                      }`}>{s}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">強み・独自性</label>
                <textarea value={strengths} onChange={(e) => setStrengths(e.target.value)} rows={3}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
              </div>
            </div>

            <div className="mt-6 flex justify-between">
              <button onClick={() => setStep(1)} className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">戻る</button>
              <button onClick={() => { setStep(3); handleSuggestChannels(); }}
                className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700">次へ</button>
            </div>
          </div>
        )}

        {/* STEP 3: チャンネル設定 */}
        {step === 3 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">同ジャンルチャンネルの設定</h2>
            <p className="mb-4 text-sm text-gray-500">最低3つ入力してください。AIからの提案も選べます。</p>

            {/* AI提案 */}
            {suggestedChannels.length > 0 && (
              <div className="mb-4 rounded-lg bg-blue-50 p-4">
                <p className="mb-2 text-xs font-medium text-blue-700">AIおすすめチャンネル（クリックで追加）</p>
                <div className="flex flex-wrap gap-2">
                  {suggestedChannels.map((ch, i) => (
                    <button key={i} onClick={() => selectSuggested(ch.name)}
                      className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs text-blue-700 hover:bg-blue-100"
                      title={ch.description}>
                      {ch.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {channelsLoading && <p className="mb-4 text-xs text-gray-400">チャンネル候補を取得中...</p>}

            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">目指すチャンネル（好き）</label>
              {likeChannels.map((ch, i) => (
                <div key={i} className="mb-1 flex gap-2">
                  <input type="text" value={ch} onChange={(e) => updateChannel(likeChannels, setLikeChannels, i, e.target.value)}
                    placeholder="チャンネル名やURL" className="flex-1 rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  {likeChannels.length > 1 && <button onClick={() => removeChannel(likeChannels, setLikeChannels, i)} className="text-xs text-red-400">削除</button>}
                </div>
              ))}
              {likeChannels.length < 10 && <button onClick={() => addChannel(likeChannels, setLikeChannels)} className="text-xs text-blue-600 hover:underline">+ 追加</button>}
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">嫌いなチャンネル（差別化したい）</label>
              {dislikeChannels.map((ch, i) => (
                <div key={i} className="mb-1 flex gap-2">
                  <input type="text" value={ch} onChange={(e) => updateChannel(dislikeChannels, setDislikeChannels, i, e.target.value)}
                    placeholder="チャンネル名やURL" className="flex-1 rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  {dislikeChannels.length > 1 && <button onClick={() => removeChannel(dislikeChannels, setDislikeChannels, i)} className="text-xs text-red-400">削除</button>}
                </div>
              ))}
              {dislikeChannels.length < 10 && <button onClick={() => addChannel(dislikeChannels, setDislikeChannels)} className="text-xs text-blue-600 hover:underline">+ 追加</button>}
            </div>

            {/* API Keys */}
            <div className="mt-6 space-y-4">
              <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
                <label className="mb-1 block text-sm font-semibold text-orange-800">Anthropic API Key（必須）</label>
                <p className="mb-2 text-xs text-orange-700">
                  台本生成・企画提案・コメント分析などAI機能すべてに使用します。
                  <a href="https://console.anthropic.com/" target="_blank" rel="noopener" className="underline ml-1">
                    Anthropic Consoleで取得
                  </a>
                </p>
                <input type="password" value={anthropicApiKey} onChange={(e) => setAnthropicApiKey(e.target.value)}
                  placeholder="sk-ant-..." className="w-full rounded-lg border border-orange-300 px-3 py-2 text-sm font-mono focus:border-orange-500 focus:outline-none bg-white" />
              </div>

              <div className="rounded-lg border border-dashed border-gray-300 p-4">
                <label className="mb-1 block text-sm font-medium text-gray-700">YouTube API Key（任意）</label>
                <p className="mb-2 text-xs text-gray-400">
                  自分のAPIキーを設定すると、検索回数の制限が大幅に緩和されます。
                  <a href="https://console.cloud.google.com/" target="_blank" rel="noopener" className="text-blue-500 underline ml-1">
                    Google Cloud Consoleで取得
                  </a>
                </p>
                <input type="text" value={youtubeApiKey} onChange={(e) => setYoutubeApiKey(e.target.value)}
                  placeholder="AIzaSy..." className="w-full rounded-lg border px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none" />
              </div>
            </div>

            <div className="mt-6 flex justify-between">
              <button onClick={() => setStep(2)} className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">戻る</button>
              <button onClick={handleSave} disabled={saving || !genre || likeChannels.filter(c => c.trim()).length < 1}
                className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "保存中..." : "保存してリサーチへ進む →"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
