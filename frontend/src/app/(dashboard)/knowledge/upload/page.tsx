"use client";

import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";

export default function KnowledgeUploadPage() {
  const [title, setTitle] = useState("");
  const [uploadType, setUploadType] = useState<"file" | "url" | "text">("file");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [tags, setTags] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: API call
  };

  return (
    <div>
      <PageHeader title="アップロード" description="ナレッジソースを追加" />
      <div className="mx-auto max-w-2xl rounded-lg border border-gray-200 bg-white p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">タイトル</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ナレッジのタイトル"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">ソースタイプ</label>
            <div className="flex gap-3">
              {(["file", "url", "text"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setUploadType(type)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    uploadType === type
                      ? "border-blue-600 bg-blue-50 text-blue-700"
                      : "border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {type === "file" ? "ファイル" : type === "url" ? "URL" : "テキスト"}
                </button>
              ))}
            </div>
          </div>

          {uploadType === "file" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">ファイル</label>
              <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
                <input type="file" className="hidden" id="file-upload" />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-sm text-blue-600 hover:text-blue-800"
                >
                  クリックしてファイルを選択
                </label>
                <p className="mt-1 text-xs text-gray-400">PDF, TXT, DOCX (最大10MB)</p>
              </div>
            </div>
          )}

          {uploadType === "url" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://..."
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}

          {uploadType === "text" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">テキスト</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={8}
                placeholder="テキストを入力..."
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">タグ (カンマ区切り)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="例: マーケティング, YouTube, SEO"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            アップロード
          </button>
        </form>
      </div>
    </div>
  );
}
