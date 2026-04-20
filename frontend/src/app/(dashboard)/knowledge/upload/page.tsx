"use client";

import { useState, useRef } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";
import { supabase } from "@/lib/supabase";

type Tab = "file" | "text";
type SourceType = "user_upload" | "book_article" | "market_analysis";

interface UploadResult {
  filename: string;
  chunk_count: number;
  message: string;
}

const SOURCE_LABELS: Record<SourceType, string> = {
  user_upload: "ノウハウメモ",
  book_article: "書籍・記事",
  market_analysis: "参考資料",
};

export default function KnowledgeUploadPage() {
  const [tab, setTab] = useState<Tab>("file");

  // ファイルタブ
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileResults, setFileResults] = useState<UploadResult[]>([]);
  const [fileErrors, setFileErrors] = useState<string[]>([]);
  const [fileLoading, setFileLoading] = useState(false);

  // テキストタブ
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("user_upload");
  const [textResult, setTextResult] = useState<{ chunk_count: number } | null>(null);
  const [textError, setTextError] = useState<string | null>(null);
  const [textLoading, setTextLoading] = useState(false);

  // ---- ファイル処理 ----
  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const allowed = [".md", ".txt", ".markdown"];
    const valid = Array.from(incoming).filter((f) =>
      allowed.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...valid.filter((f) => !names.has(f.name))];
    });
  };

  const removeFile = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleFileUpload = async () => {
    if (files.length === 0) return;
    setFileLoading(true);
    setFileResults([]);
    setFileErrors([]);

    const pid = await getProjectId();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const baseUrl = apiClient.getUrl(`/api/v1/knowledge/${pid}/upload`);

    const results: UploadResult[] = [];
    const errors: string[] = [];

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(baseUrl, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (!res.ok) {
          const txt = await res.text().catch(() => "");
          errors.push(`${file.name}: ${txt || res.statusText}`);
        } else {
          const data = await res.json();
          results.push(data);
        }
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof Error ? err.message : "失敗"}`);
      }
    }

    setFileResults(results);
    setFileErrors(errors);
    if (errors.length === 0) setFiles([]);
    setFileLoading(false);
  };

  // ---- テキスト処理 ----
  const handleTextSubmit = async () => {
    if (!title.trim() || !content.trim()) return;
    setTextLoading(true);
    setTextResult(null);
    setTextError(null);
    try {
      const pid = await getProjectId();
      const data = await apiClient.post<{ chunk_count: number; message: string }>(
        `/api/v1/knowledge/${pid}/add-theory`,
        { title: title.trim(), content: content.trim(), source_type: sourceType }
      );
      setTextResult(data);
      setTitle("");
      setContent("");
    } catch (err) {
      setTextError(err instanceof Error ? err.message : "保存に失敗しました");
    } finally {
      setTextLoading(false);
    }
  };

  return (
    <div>
      <PageHeader title="ナレッジを追加" description="書籍・記事・メモ・Obsidianノートをナレッジベースに登録" />

      {/* タブ */}
      <div className="mb-6 flex gap-1 rounded-xl bg-gray-100 p-1 w-fit">
        {(["file", "text"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-lg px-5 py-2 text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "file" ? "ファイル (.md/.txt)" : "テキスト直接入力"}
          </button>
        ))}
      </div>

      {/* ファイルタブ */}
      {tab === "file" && (
        <div className="max-w-2xl space-y-4">
          {/* ドロップゾーン */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
              dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }`}
          >
            <p className="text-sm font-medium text-gray-700">クリックまたはドラッグ＆ドロップ</p>
            <p className="mt-1 text-xs text-gray-400">.md / .txt / .markdown（Obsidianノート対応、複数可）</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".md,.txt,.markdown"
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {/* ファイルリスト */}
          {files.length > 0 && (
            <ul className="space-y-2">
              {files.map((f) => (
                <li key={f.name} className="flex items-center justify-between rounded-lg border bg-white px-4 py-2 text-sm">
                  <span className="truncate text-gray-800">{f.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(f.name)}
                    className="ml-4 flex-shrink-0 text-xs text-gray-400 hover:text-red-500"
                  >
                    削除
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button
            type="button"
            onClick={handleFileUpload}
            disabled={fileLoading || files.length === 0}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {fileLoading ? `アップロード中...` : `${files.length}件をアップロード`}
          </button>

          {/* 結果 */}
          {fileResults.length > 0 && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-4 space-y-1">
              {fileResults.map((r) => (
                <p key={r.filename} className="text-sm text-green-800">
                  ✓ {r.filename} — {r.chunk_count}チャンク保存
                </p>
              ))}
            </div>
          )}
          {fileErrors.length > 0 && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4 space-y-1">
              {fileErrors.map((e, i) => (
                <p key={i} className="text-sm text-red-700">{e}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* テキストタブ */}
      {tab === "text" && (
        <div className="max-w-2xl space-y-5">
          {/* カテゴリ選択 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">カテゴリ</label>
            <div className="flex gap-2 flex-wrap">
              {(Object.entries(SOURCE_LABELS) as [SourceType, string][]).map(([val, label]) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setSourceType(val)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    sourceType === val
                      ? "border-blue-600 bg-blue-50 text-blue-700"
                      : "border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* タイトル */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">タイトル</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例: マーケティングの法則 / 自分の集客ノウハウ"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* テキスト */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">内容</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={14}
              placeholder="書籍のテキスト、記事の内容、自分のノウハウメモなどを貼り付けてください。Markdown形式も対応しています。"
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
            />
            <p className="mt-1 text-xs text-gray-400">{content.length}文字</p>
          </div>

          <button
            type="button"
            onClick={handleTextSubmit}
            disabled={textLoading || !title.trim() || !content.trim()}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {textLoading ? "保存中..." : "ナレッジに保存"}
          </button>

          {textResult && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-sm text-green-800">
              ✓ {textResult.chunk_count}チャンクとして保存しました。台本生成時に自動参照されます。
            </div>
          )}
          {textError && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
              {textError}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
