"use client";

import { useState, useEffect } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";

type Tab = "timestamps" | "community" | "shorts" | "media" | "theory";

interface ScriptOption {
  id: string;
  title: string;
  status: string;
  word_count: number | null;
  created_at: string;
}

export default function ContentPage() {
  const [tab, setTab] = useState<Tab>("timestamps");
  const [scriptId, setScriptId] = useState("");
  const [scripts, setScripts] = useState<ScriptOption[]>([]);
  const [scriptsLoading, setScriptsLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // 台本一覧を読み込み
  useEffect(() => {
    async function loadScripts() {
      try {
        const pid = await getProjectId();
        const data = await apiClient.get<ScriptOption[]>(`/api/v1/scripts/${pid}`);
        setScripts(data.filter((s) => s.status === "completed"));
        if (data.length > 0 && !scriptId) {
          const completed = data.filter((s) => s.status === "completed");
          if (completed.length > 0) setScriptId(completed[0].id);
        }
      } catch {
        // ignore
      } finally {
        setScriptsLoading(false);
      }
    }
    loadScripts();
  }, []);

  // Theory inputs
  const [theoryTitle, setTheoryTitle] = useState("");
  const [theoryContent, setTheoryContent] = useState("");

  // Media format
  const [mediaFormat, setMediaFormat] = useState("x");

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "timestamps", label: "タイムスタンプ", icon: "⏱" },
    { key: "community", label: "コミュニティ投稿", icon: "📢" },
    { key: "shorts", label: "ショート提案", icon: "📱" },
    { key: "media", label: "X/ブログ/note", icon: "📄" },
    { key: "theory", label: "理論追加", icon: "🧠" },
  ];

  const handleGenerate = async () => {
    if (!scriptId && tab !== "theory") {
      setError("台本IDを入力してください");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const pid = await getProjectId();
      let data: any;

      switch (tab) {
        case "timestamps":
          data = await apiClient.post(`/api/v1/content/${pid}/timestamps`, { script_id: scriptId });
          break;
        case "community":
          data = await apiClient.post(`/api/v1/content/${pid}/community-post`, { script_id: scriptId });
          break;
        case "shorts":
          data = await apiClient.post(`/api/v1/content/${pid}/shorts`, { script_id: scriptId });
          break;
        case "media":
          data = await apiClient.post(`/api/v1/content/${pid}/convert`, { script_id: scriptId, format: mediaFormat });
          break;
        case "theory":
          data = await apiClient.post(`/api/v1/knowledge/${pid}/add-theory`, {
            title: theoryTitle,
            content: theoryContent,
          });
          break;
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div>
      <PageHeader title="コンテンツ工房" description="台本から各種コンテンツを自動生成" />

      {error && <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {/* タブ */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setResult(null); }}
            className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition-colors ${
              tab === t.key ? "bg-white text-blue-700 shadow-sm" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* 入力 */}
      <div className="mb-6 rounded-xl border bg-white p-6">
        {tab !== "theory" ? (
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">台本を選択</label>
            {scriptsLoading ? (
              <p className="mb-4 text-sm text-gray-400">台本を読み込み中...</p>
            ) : scripts.length === 0 ? (
              <p className="mb-4 text-sm text-gray-400">完了済みの台本がありません。先に台本を生成してください。</p>
            ) : (
              <select
                value={scriptId}
                onChange={(e) => setScriptId(e.target.value)}
                className="mb-4 w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none bg-white"
              >
                {scripts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} ({s.word_count?.toLocaleString() || "?"}文字)
                  </option>
                ))}
              </select>
            )}
            {tab === "media" && (
              <div className="mb-4">
                <label className="mb-2 block text-sm font-medium text-gray-700">出力形式</label>
                <div className="flex gap-2">
                  {[
                    { value: "x", label: "X (Twitter)" },
                    { value: "blog", label: "ブログ" },
                    { value: "note", label: "note" },
                  ].map((f) => (
                    <button
                      key={f.value}
                      onClick={() => setMediaFormat(f.value)}
                      className={`rounded-full border px-4 py-1.5 text-xs font-medium ${
                        mediaFormat === f.value ? "border-blue-600 bg-blue-600 text-white" : "text-gray-600"
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">理論タイトル</label>
              <input
                type="text"
                value={theoryTitle}
                onChange={(e) => setTheoryTitle(e.target.value)}
                placeholder="例：視聴者維持率を上げる3つの原則"
                className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">内容</label>
              <textarea
                value={theoryContent}
                onChange={(e) => setTheoryContent(e.target.value)}
                placeholder="あなたの理論、ノウハウ、気づきを自由に書いてください..."
                rows={8}
                className="w-full rounded-lg border px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "生成中..." : tab === "theory" ? "ナレッジに追加" : "生成する"}
        </button>
      </div>

      {/* 結果表示 */}
      {result && (
        <div className="rounded-xl border bg-white p-6">
          {/* タイムスタンプ */}
          {tab === "timestamps" && Array.isArray(result) && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">タイムスタンプ（{result.length}個）</h3>
                <button
                  onClick={() => copyToClipboard(result.map((r: any) => `${r.time} ${r.text}`).join("\n"))}
                  className="rounded border px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                >
                  コピー
                </button>
              </div>
              <div className="rounded-lg bg-gray-50 p-4 font-mono text-sm">
                {result.map((r: any, i: number) => (
                  <div key={i} className="py-0.5">{r.time} {r.text}</div>
                ))}
              </div>
            </div>
          )}

          {/* コミュニティ投稿 */}
          {tab === "community" && result.standard && (
            <div className="space-y-4">
              {["short", "standard", "long"].map((key) => (
                <div key={key} className="rounded-lg border p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500">
                      {key === "short" ? "短め" : key === "standard" ? "標準" : "長め"}
                    </span>
                    <button
                      onClick={() => copyToClipboard(result[key])}
                      className="rounded border px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-50"
                    >
                      コピー
                    </button>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-gray-800">{result[key]}</p>
                </div>
              ))}
            </div>
          )}

          {/* ショート提案 */}
          {tab === "shorts" && Array.isArray(result) && (
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900">ショート動画候補（{result.length}件）</h3>
              {result.map((s: any, i: number) => (
                <div key={i} className="rounded-lg border p-4">
                  <h4 className="font-medium text-gray-900">{i + 1}. {s.title}</h4>
                  <p className="mt-1 text-xs text-gray-500">KW: {s.keyword} | 約{s.estimated_seconds}秒</p>
                  <p className="mt-1 text-sm text-gray-700">{s.reason}</p>
                  <p className="mt-1 text-xs text-gray-400">開始: 「{s.start_text}」</p>
                </div>
              ))}
            </div>
          )}

          {/* メディア変換 */}
          {tab === "media" && result.format && (
            <div>
              {result.format === "x" && result.main && (
                <div className="space-y-3">
                  <div className="rounded-lg bg-blue-50 p-4">
                    <div className="mb-1 flex justify-between">
                      <span className="text-xs font-medium text-blue-700">メインツイート</span>
                      <button onClick={() => copyToClipboard(result.main)} className="text-xs text-blue-600">コピー</button>
                    </div>
                    <p className="text-sm text-gray-900">{result.main}</p>
                  </div>
                  {result.thread?.map((t: string, i: number) => (
                    <div key={i} className="rounded-lg border p-3">
                      <div className="mb-1 flex justify-between">
                        <span className="text-xs text-gray-500">スレッド {i + 1}</span>
                        <button onClick={() => copyToClipboard(t)} className="text-xs text-gray-400">コピー</button>
                      </div>
                      <p className="text-sm text-gray-800">{t}</p>
                    </div>
                  ))}
                </div>
              )}
              {(result.format === "blog" || result.format === "note") && (
                <div>
                  <button
                    onClick={() => {
                      const text = result.format === "blog"
                        ? `# ${result.title}\n\n${result.intro}\n\n${(result.sections || []).map((s: any) => `## ${s.heading}\n${s.body}`).join("\n\n")}\n\n## まとめ\n${result.conclusion}`
                        : `# ${result.title}\n\n${result.intro}\n\n${result.body}\n\n${result.closing}`;
                      copyToClipboard(text);
                    }}
                    className="mb-4 rounded border px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                  >
                    全文コピー
                  </button>
                  <h3 className="text-lg font-bold text-gray-900">{result.title}</h3>
                  <p className="mt-2 text-sm text-gray-700">{result.intro}</p>
                  {result.sections?.map((s: any, i: number) => (
                    <div key={i} className="mt-4">
                      <h4 className="font-semibold text-gray-900">{s.heading}</h4>
                      <p className="mt-1 text-sm text-gray-700">{s.body}</p>
                    </div>
                  ))}
                  {result.body && <p className="mt-4 whitespace-pre-wrap text-sm text-gray-700">{result.body}</p>}
                  {result.conclusion && <p className="mt-4 text-sm text-gray-600">{result.conclusion}</p>}
                  {result.closing && <p className="mt-4 text-sm text-gray-600">{result.closing}</p>}
                </div>
              )}
            </div>
          )}

          {/* 理論追加 */}
          {tab === "theory" && result.message && (
            <div className="rounded-lg bg-green-50 p-4 text-sm text-green-700">
              {result.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
