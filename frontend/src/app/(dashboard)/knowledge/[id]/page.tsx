"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";

type Tab = "personal" | "content" | "product";

const PERSONAL_FIELDS = [
  { key: "achievements", label: "実績（数値ベース）", placeholder: "例: 登録者10万人、累計再生1億回、受講生500名" },
  { key: "profile", label: "プロフィール・経歴・肩書・年齢", placeholder: "例: 元営業マン、29歳、心理カウンセラー資格保持" },
  { key: "origin_story", label: "原体験ストーリー（転機・苦労・逆転劇）", placeholder: "例: 25歳まで彼女ゼロ、心理学に出会い人生が変わった" },
  { key: "values", label: "価値観・人生哲学・信念", placeholder: "例: 誠実さが最強の武器、駆け引きは不要" },
  { key: "vision", label: "ビジョン・目標（作りたい世界観）", placeholder: "例: 恋愛で苦しむ男性をゼロにする" },
  { key: "strengths", label: "強み・ポジショントーク（なぜ自分から学ぶべきか）", placeholder: "例: 非モテから実践で結果を出した再現性のある方法論" },
  { key: "first_person", label: "一人称・基本の口調", placeholder: "例: 僕、〜なんですよね" },
  { key: "tone_rules", label: "語尾・言い回しルール", placeholder: "例: 〜じゃないですか、〜だと思うんですよ" },
  { key: "casual_level", label: "フランクさレベル（丁寧⇔カジュアル配分）", placeholder: "例: 7:3でカジュアル寄り、友達に話す感じ" },
  { key: "expression_patterns", label: "推奨表現パターン（断定・対比・数字活用・例え話等）", placeholder: "例: 数字で断定する、ビフォーアフターを対比させる" },
  { key: "decoration_rules", label: "装飾記号の使い方", placeholder: "例: 【】を見出しに使用、！は多用しない" },
  { key: "ng_expressions", label: "避けるべき表現（NG集）", placeholder: "例: 絶対、必ず、誰でも、簡単に" },
];

const CONTENT_FIELDS = [
  { key: "popular_keywords", label: "発信ジャンルの人気キーワード・共通言語", placeholder: "例: モテ、脈あり、アプローチ、LINE術" },
  { key: "target_info", label: "発信ターゲット情報", placeholder: "例: 20-35歳の恋愛に自信がない男性、社会人" },
  { key: "youtube_templates", label: "YouTubeコンテンツ（動画台本テンプレ・概要欄テンプレ等）", placeholder: "例: 冒頭で共感→問題提起→解決策3つ→まとめ→CTA" },
];

const PRODUCT_FIELDS = [
  { key: "product_overview", label: "商品概要（何を提供するか）", placeholder: "例: 恋愛コンサルティング、オンライン講座" },
  { key: "core_concept", label: "コアコンセプト・USP", placeholder: "例: 心理学×実体験の再現性ある恋愛メソッド" },
  { key: "curriculum", label: "カリキュラム構成（学べる内容の全体像）", placeholder: "例: 基礎編→実践編→応用編の3ステップ" },
  { key: "support_community", label: "サポート体制・コミュニティ", placeholder: "例: 専用Discordコミュニティ、月2回のグループコンサル" },
  { key: "benefits", label: "入会特典一覧", placeholder: "例: LINE添削、デートプラン作成シート、マッチングアプリ攻略ガイド" },
  { key: "pricing", label: "料金プラン・保証制度", placeholder: "例: 月額9,800円、30日間全額返金保証" },
  { key: "appeal_keywords", label: "訴求キーワード一覧", placeholder: "例: 最小努力、再現性、非モテ脱出、心理学" },
  { key: "target_attributes", label: "ターゲット属性（職業・状況・理解レベル）", placeholder: "例: 会社員、恋愛経験少ない、恋愛本は読んだことある" },
  { key: "target_problems", label: "具体的な悩み・課題", placeholder: "例: マッチングアプリで会えない、デートで沈黙する" },
  { key: "ideal_future", label: "最高の未来（理想の状態）", placeholder: "例: 自然体でモテる、彼女ができて自信がつく" },
  { key: "worst_future", label: "最悪の未来（恐怖・不安）", placeholder: "例: 一生独身、周りが結婚していく焦り" },
  { key: "required_mindset", label: "必須マインドセット（求める受講者像）", placeholder: "例: 素直に実践する人、言い訳しない人" },
  { key: "client_results", label: "クライアント成果事例（ビフォーアフター・期間・数値）", placeholder: "例: 30歳会社員→3ヶ月で彼女、25歳→初デートから交際" },
];

export default function ModelEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: modelId } = use(params);
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("personal");
  const [model, setModel] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [autofilling, setAutofilling] = useState(false);
  const [autofillUrl, setAutofillUrl] = useState("");
  const [autofillText, setAutofillText] = useState("");

  // フォームstate
  const [personal, setPersonal] = useState<Record<string, string>>({});
  const [content, setContent] = useState<Record<string, string>>({});
  const [product, setProduct] = useState<Record<string, string>>({});

  useEffect(() => {
    async function load() {
      try {
        const pid = await getProjectId();
        const data = await apiClient.get<any>(`/api/v1/models/${pid}/${modelId}`);
        setModel(data);
        setPersonal(data.personal_knowledge || {});
        setContent(data.content_knowledge || {});
        setProduct(data.product_knowledge || {});
      } catch { router.push("/knowledge"); }
      finally { setLoading(false); }
    }
    load();
  }, [modelId, router]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const pid = await getProjectId();
      await apiClient.patch(`/api/v1/models/${pid}/${modelId}`, {
        personal_knowledge: personal,
        content_knowledge: content,
        product_knowledge: product,
      });
      alert("保存しました");
    } catch (err) {
      alert("保存失敗: " + (err instanceof Error ? err.message : ""));
    } finally { setSaving(false); }
  };

  const [autofillResult, setAutofillResult] = useState<string>("");

  const handleAutofill = async () => {
    setAutofilling(true);
    setAutofillResult("");
    try {
      const pid = await getProjectId();
      const result = await apiClient.post<any>(`/api/v1/models/${pid}/${modelId}/autofill`, {
        youtube_channel_url: autofillUrl,
        text_input: autofillText,
      });
      if (result.personal_knowledge) {
        const filtered: Record<string, string> = {};
        for (const [k, v] of Object.entries(result.personal_knowledge)) { if (v) filtered[k] = String(v); }
        setPersonal(prev => ({ ...prev, ...filtered }));
      }
      if (result.content_knowledge) {
        const filtered: Record<string, string> = {};
        for (const [k, v] of Object.entries(result.content_knowledge)) { if (v) filtered[k] = String(v); }
        setContent(prev => ({ ...prev, ...filtered }));
      }
      if (result.product_knowledge) {
        const filtered: Record<string, string> = {};
        for (const [k, v] of Object.entries(result.product_knowledge)) { if (v) filtered[k] = String(v); }
        setProduct(prev => ({ ...prev, ...filtered }));
      }
      const pCount = Object.values(result.personal_knowledge || {}).filter((v: any) => v).length;
      const cCount = Object.values(result.content_knowledge || {}).filter((v: any) => v).length;
      const prCount = Object.values(result.product_knowledge || {}).filter((v: any) => v).length;
      setAutofillResult(`AIで ${pCount + cCount + prCount} 項目を入力しました（パーソナル:${pCount} コンテンツ:${cCount} プロダクト:${prCount}）。各タブで確認して保存してください。`);
    } catch (err) {
      setAutofillResult("自動入力失敗: " + (err instanceof Error ? err.message : ""));
    } finally { setAutofilling(false); }
  };

  const updateField = (category: Tab, key: string, value: string) => {
    if (category === "personal") setPersonal(prev => ({ ...prev, [key]: value }));
    else if (category === "content") setContent(prev => ({ ...prev, [key]: value }));
    else setProduct(prev => ({ ...prev, [key]: value }));
  };

  if (loading) return <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>;

  const tabs: { key: Tab; label: string; color: string }[] = [
    { key: "personal", label: "パーソナル", color: "purple" },
    { key: "content", label: "コンテンツ", color: "blue" },
    { key: "product", label: "プロダクト", color: "green" },
  ];

  const currentFields = tab === "personal" ? PERSONAL_FIELDS : tab === "content" ? CONTENT_FIELDS : PRODUCT_FIELDS;
  const currentData = tab === "personal" ? personal : tab === "content" ? content : product;

  return (
    <div>
      <PageHeader title={model?.name || "モデル編集"} description="ナレッジの各項目を入力・編集"
        actions={
          <div className="flex gap-2">
            <button onClick={() => router.push("/knowledge")} className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">一覧に戻る</button>
            <button onClick={handleSave} disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        }
      />

      {/* AI自動入力 */}
      <div className="mb-6 rounded-xl border bg-gradient-to-r from-purple-50 to-blue-50 p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-800">🤖 AIで自動入力</h3>
        <p className="mb-3 text-xs text-gray-500">YouTubeチャンネルURLまたはテキストを入力すると、AIが各項目を自動で埋めます。</p>
        <div className="space-y-2">
          <input type="text" value={autofillUrl} onChange={(e) => setAutofillUrl(e.target.value)}
            placeholder="YouTubeチャンネルURL（例: https://www.youtube.com/@channelname）"
            className="w-full rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          <textarea value={autofillText} onChange={(e) => setAutofillText(e.target.value)}
            placeholder="または、自分の情報をテキストで自由に入力..."
            rows={3} className="w-full rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          <button onClick={handleAutofill} disabled={autofilling || (!autofillUrl.trim() && !autofillText.trim())}
            className="rounded-lg bg-purple-600 px-6 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
            {autofilling ? "AI分析中...（30秒〜1分かかります）" : "AIで自動入力"}
          </button>
          {autofillResult && (
            <div className={`mt-2 rounded-lg p-3 text-sm ${autofillResult.includes("失敗") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
              {autofillResult}
            </div>
          )}
        </div>
      </div>

      {/* タブ */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-white shadow-sm text-gray-900" : "text-gray-500"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* フォーム */}
      <div className="space-y-4">
        {currentFields.map((field) => (
          <div key={field.key} className="rounded-lg border bg-white p-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">{field.label}</label>
            <textarea
              value={Array.isArray(currentData[field.key]) ? (currentData[field.key] as unknown as string[]).join(", ") : (currentData[field.key] || "")}
              onChange={(e) => updateField(tab, field.key, e.target.value)}
              placeholder={field.placeholder}
              rows={3}
              className="w-full rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end">
        <button onClick={handleSave} disabled={saving}
          className="rounded-lg bg-blue-600 px-8 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {saving ? "保存中..." : "保存する"}
        </button>
      </div>
    </div>
  );
}
