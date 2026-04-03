"use client";

import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { useKnowledgeSearch } from "@/hooks/useKnowledgeSearch";
import Link from "next/link";

export default function KnowledgePage() {
  const { chunks, loading, error, search } = useKnowledgeSearch();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      search(query.trim());
    }
  };

  return (
    <div>
      <PageHeader
        title="ナレッジ一覧"
        description="RAGナレッジベースを検索"
        actions={
          <Link
            href="/knowledge/upload"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            アップロード
          </Link>
        }
      />

      {/* 検索フォーム */}
      <form onSubmit={handleSearch} className="mb-6 flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ナレッジを検索..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "検索中..." : "検索"}
        </button>
      </form>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="py-8 text-center text-sm text-gray-500">検索中...</div>
      ) : chunks.length > 0 ? (
        <>
          <p className="mb-3 text-sm text-gray-500">{chunks.length}件のチャンクが見つかりました</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                    {chunk.source_type}
                  </span>
                  {chunk.score != null && (
                    <span className="text-xs text-gray-400">
                      類似度: {chunk.score.toFixed(3)}
                    </span>
                  )}
                </div>
                <h3 className="mb-1 text-sm font-semibold text-gray-900">
                  {chunk.source_file}
                </h3>
                <p className="text-xs text-gray-400 mb-2">
                  チャンク #{chunk.chunk_index}
                  {chunk.token_count != null && ` / ${chunk.token_count}トークン`}
                </p>
                <p className="text-xs text-gray-600 line-clamp-5">{chunk.content}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-sm text-gray-400">
            検索クエリを入力してナレッジベースを検索してください
          </p>
          <Link
            href="/knowledge/upload"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            ナレッジを追加
          </Link>
        </div>
      )}
    </div>
  );
}
