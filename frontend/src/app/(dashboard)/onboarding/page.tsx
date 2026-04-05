"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getProjectId } from "@/lib/api-client";

const GENRE_CHIPS = ["恋愛", "ビジネス", "副業", "美容", "筋トレ", "料理", "ゲーム", "教育", "投資", "転職", "ダイエット", "プログラミング"];
const STYLE_CHIPS = ["ノウハウ系", "エンタメ系", "Vlog系", "解説系", "ストーリー系", "比較/レビュー系"];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [genre, setGenre] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [contentStyle, setContentStyle] = useState("");
  const [benchmarks, setBenchmarks] = useState<string[]>([""]);
  const [strengths, setStrengths] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // 既存プロファイルを読み込み
  useEffect(() => {
    async function loadProfile() {
      try {
        const pid = await getProjectId();
        const profile = await apiClient.get<any>(`/api/v1/projects/${pid}/profile`);
        if (profile) {
          if (profile.genre) setGenre(profile.genre);
          if (profile.target_audience) setTargetAudience(profile.target_audience);
          if (profile.content_style) setContentStyle(profile.content_style);
          if (profile.benchmark_channels && profile.benchmark_channels.length > 0) {
            setBenchmarks(profile.benchmark_channels);
          }
          if (profile.strengths) setStrengths(profile.strengths);
        }
      } catch {
        // 新規ユーザーの場合はエラーを無視
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  const addBenchmark = () => {
    if (benchmarks.length < 10) setBenchmarks([...benchmarks, ""]);
  };

  const updateBenchmark = (index: number, value: string) => {
    const updated = [...benchmarks];
    updated[index] = value;
    setBenchmarks(updated);
  };

  const removeBenchmark = (index: number) => {
    setBenchmarks(benchmarks.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const pid = await getProjectId();
      await apiClient.patch(`/api/v1/projects/${pid}/profile`, {
        genre,
        target_audience: targetAudience,
        content_style: contentStyle,
        benchmark_channels: benchmarks.filter((b) => b.trim()),
        strengths,
      });
      router.push("/");
    } catch (err) {
      alert("保存に失敗しました: " + (err instanceof Error ? err.message : ""));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="py-12 text-center text-sm text-gray-500">プロファイル読み込み中...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">プロファイル設定</h1>
      <p className="mb-8 text-sm text-gray-500">あなたのチャンネル情報を教えてください。企画提案や検索結果がパーソナライズされます。</p>

      {/* ステップインジケーター */}
      <div className="mb-8 flex items-center gap-2">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex items-center">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
              s <= step ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-500"
            }`}>
              {s < step ? "✓" : s}
            </div>
            {s < 4 && <div className={`mx-1 h-0.5 w-8 ${s < step ? "bg-blue-600" : "bg-gray-200"}`} />}
          </div>
        ))}
      </div>

      <div className="rounded-xl border bg-white p-6 shadow-sm">
        {/* STEP 1: ジャンル */}
        {step === 1 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">どんなジャンルのチャンネルですか？</h2>
            <input
              type="text"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              placeholder="例：男性向け恋愛チャンネル"
              className="mb-4 w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <div className="flex flex-wrap gap-2">
              {GENRE_CHIPS.map((g) => (
                <button
                  key={g}
                  onClick={() => setGenre(genre ? `${genre} ${g}` : g)}
                  className="rounded-full border px-3 py-1 text-xs text-gray-600 hover:border-blue-400 hover:bg-blue-50"
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* STEP 2: ターゲット+スタイル */}
        {step === 2 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">ターゲットとスタイルを教えてください</h2>
            <label className="mb-1 block text-sm font-medium text-gray-700">ターゲット視聴者</label>
            <input
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              placeholder="例：20-30代男性サラリーマン"
              className="mb-4 w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <label className="mb-2 block text-sm font-medium text-gray-700">コンテンツスタイル</label>
            <div className="flex flex-wrap gap-2">
              {STYLE_CHIPS.map((s) => (
                <button
                  key={s}
                  onClick={() => setContentStyle(s)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    contentStyle === s
                      ? "border-blue-600 bg-blue-600 text-white"
                      : "text-gray-600 hover:border-blue-400"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* STEP 3: ベンチマーク */}
        {step === 3 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">目指しているチャンネルは？（最大10個）</h2>
            <div className="space-y-2">
              {benchmarks.map((b, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={b}
                    onChange={(e) => updateBenchmark(i, e.target.value)}
                    placeholder="チャンネル名やURL"
                    className="flex-1 rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                  {benchmarks.length > 1 && (
                    <button onClick={() => removeBenchmark(i)} className="text-red-400 hover:text-red-600 text-sm">削除</button>
                  )}
                </div>
              ))}
            </div>
            {benchmarks.length < 10 && (
              <button onClick={addBenchmark} className="mt-2 text-sm text-blue-600 hover:underline">+ 追加</button>
            )}
          </div>
        )}

        {/* STEP 4: 強み */}
        {step === 4 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold">あなたの強み・独自性は？</h2>
            <textarea
              value={strengths}
              onChange={(e) => setStrengths(e.target.value)}
              placeholder="例：元営業マンで心理学に詳しい。3年間の海外生活経験がある。"
              rows={5}
              className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        )}

        {/* ナビゲーション */}
        <div className="mt-6 flex justify-between">
          <button
            onClick={() => setStep(step - 1)}
            disabled={step === 1}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-30"
          >
            戻る
          </button>
          {step < 4 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              次へ
            </button>
          ) : (
            <button
              onClick={handleSave}
              disabled={saving || !genre}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "保存中..." : "完了してダッシュボードへ"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
