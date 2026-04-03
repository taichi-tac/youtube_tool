"use client";

import type { KnowledgeChunk } from "@/types/knowledge";

interface KnowledgePanelProps {
  chunks: KnowledgeChunk[];
  loading?: boolean;
}

export default function KnowledgePanel({ chunks, loading }: KnowledgePanelProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-900">参照ナレッジ</h3>
      {loading ? (
        <p className="text-sm text-gray-400">検索中...</p>
      ) : chunks.length === 0 ? (
        <p className="text-sm text-gray-400">ナレッジがありません</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {chunks.map((chunk) => (
            <div
              key={chunk.id}
              className="rounded-lg border border-gray-100 p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {chunk.source_file}
                </p>
                {chunk.score != null && (
                  <span className="text-xs text-gray-400">
                    {chunk.score.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">{chunk.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
