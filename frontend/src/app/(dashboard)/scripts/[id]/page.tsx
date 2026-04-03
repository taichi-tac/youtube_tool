"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, PROJECT_ID } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Script, ScriptUpdateRequest } from "@/types/script";

type TabKey = "hook" | "body" | "closing";

const tabs: { key: TabKey; label: string; color: string; bgColor: string }[] = [
  { key: "hook", label: "Hook (冒頭)", color: "border-red-500 text-red-700", bgColor: "bg-red-50" },
  { key: "body", label: "Body (本編)", color: "border-blue-500 text-blue-700", bgColor: "bg-blue-50" },
  { key: "closing", label: "Closing (クロージング)", color: "border-green-500 text-green-700", bgColor: "bg-green-50" },
];

export default function ScriptEditPage() {
  const params = useParams();
  const scriptId = params.id as string;

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 編集用ローカルステート
  const [editTitle, setEditTitle] = useState("");
  const [editHook, setEditHook] = useState("");
  const [editBody, setEditBody] = useState("");
  const [editClosing, setEditClosing] = useState("");

  // タブ
  const [activeTab, setActiveTab] = useState<TabKey>("hook");

  // コピー状態
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function fetchScript() {
      setLoading(true);
      setError(null);
      try {
        const result = await apiClient.get<Script>(
          `/api/v1/scripts/${PROJECT_ID}/${scriptId}`,
        );
        setScript(result);
        setEditTitle(result.title);
        setEditHook(result.hook || "");
        setEditBody(result.body || "");
        setEditClosing(result.closing || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "台本の取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }
    if (scriptId) fetchScript();
  }, [scriptId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const update: ScriptUpdateRequest = {
        title: editTitle,
        hook: editHook || undefined,
        body: editBody || undefined,
        closing: editClosing || undefined,
      };
      const updated = await apiClient.patch<Script>(
        `/api/v1/scripts/${PROJECT_ID}/${scriptId}`,
        update,
      );
      setScript(updated);
      setSuccessMsg("保存しました");
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const fullText = `# ${editTitle}\n\n## Hook\n${editHook}\n\n## Body\n${editBody}\n\n## Closing\n${editClosing}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(
        `${editHook}\n\n${editBody}\n\n${editClosing}`,
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const textarea = document.createElement("textarea");
      textarea.value = `${editHook}\n\n${editBody}\n\n${editClosing}`;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = () => {
    const blob = new Blob([fullText], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${editTitle || "台本"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getContent = (key: TabKey) => {
    if (key === "hook") return editHook;
    if (key === "body") return editBody;
    return editClosing;
  };

  const setContent = (key: TabKey, value: string) => {
    if (key === "hook") setEditHook(value);
    else if (key === "body") setEditBody(value);
    else setEditClosing(value);
  };

  if (loading) {
    return (
      <div>
        <PageHeader title="台本編集" description="台本の内容を編集" />
        <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (error && !script) {
    return (
      <div>
        <PageHeader title="台本編集" description="台本の内容を編集" />
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      </div>
    );
  }

  const hookLen = editHook.length;
  const bodyLen = editBody.length;
  const closingLen = editClosing.length;
  const totalChars = hookLen + bodyLen + closingLen;
  const estimatedMinutes = Math.round(totalChars / 300);

  return (
    <div>
      <PageHeader
        title="台本編集"
        description="台本の内容を編集"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copied ? "コピーしました" : "テキストコピー"}
            </button>
            <button
              onClick={handleExport}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              エクスポート
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}
      {successMsg && (
        <div className="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700">{successMsg}</div>
      )}

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {/* タイトル */}
        <div className="mb-6">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="w-full text-xl font-bold text-gray-900 border-none focus:outline-none focus:ring-0 p-0"
            placeholder="台本タイトル"
          />
          <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
            <span>{totalChars}文字</span>
            <span>推定 {estimatedMinutes}分</span>
            <span className="text-xs text-gray-400">
              (Hook: {hookLen} / Body: {bodyLen} / Closing: {closingLen})
            </span>
            {script && (
              <span
                className={`rounded px-2 py-0.5 text-xs font-medium ${
                  script.status === "completed"
                    ? "bg-green-50 text-green-700"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {script.status}
              </span>
            )}
          </div>

          {/* 推定読み上げ時間バー */}
          <div className="mt-3 flex items-center gap-3">
            <span className="text-xs text-gray-500">読み上げ時間:</span>
            <div className="h-2 flex-1 max-w-xs rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full bg-blue-500 transition-all duration-300"
                style={{ width: `${Math.min((estimatedMinutes / 20) * 100, 100)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-700">
              約{estimatedMinutes}分 ({totalChars}文字 / 300文字/分)
            </span>
          </div>
        </div>

        {/* 外側設計情報 */}
        {script && (script.target_viewer || script.viewer_problem || script.promise || script.uniqueness) && (
          <div className="mb-6 rounded-lg bg-gray-50 p-4">
            <h3 className="mb-2 text-xs font-semibold text-gray-500">外側設計</h3>
            <div className="space-y-1 text-sm text-gray-600">
              {script.target_viewer && (
                <p><span className="font-medium">ターゲット:</span> {script.target_viewer}</p>
              )}
              {script.viewer_problem && (
                <p><span className="font-medium">悩み:</span> {script.viewer_problem}</p>
              )}
              {script.promise && (
                <p><span className="font-medium">約束:</span> {script.promise}</p>
              )}
              {script.uniqueness && (
                <p><span className="font-medium">独自性:</span> {script.uniqueness}</p>
              )}
            </div>
          </div>
        )}

        {/* タブ切り替え */}
        <div className="mb-4 border-b border-gray-200">
          <nav className="flex gap-0">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                  activeTab === tab.key
                    ? `${tab.color} border-current`
                    : "text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300",
                )}
              >
                {tab.label}
                <span className="ml-2 text-xs text-gray-400">
                  ({getContent(tab.key).length}文字)
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* アクティブタブのエディタ */}
        {tabs.map((tab) => (
          <div
            key={tab.key}
            className={activeTab === tab.key ? "block" : "hidden"}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${tab.bgColor} ${tab.color.split(" ")[1]}`}>
                {tab.label}
              </span>
              <span className="text-xs text-gray-400">
                {getContent(tab.key).length}文字
              </span>
            </div>
            <textarea
              value={getContent(tab.key)}
              onChange={(e) => setContent(tab.key, e.target.value)}
              rows={tab.key === "body" ? 16 : 8}
              placeholder={
                tab.key === "hook"
                  ? "視聴者の注意を引くフック部分..."
                  : tab.key === "body"
                  ? "メインコンテンツ..."
                  : "まとめ・CTA..."
              }
              className="w-full resize-y rounded border border-gray-200 p-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
