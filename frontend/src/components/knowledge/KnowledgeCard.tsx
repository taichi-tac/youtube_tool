import type { KnowledgeChunk } from "@/types/knowledge";

interface KnowledgeCardProps {
  chunk: KnowledgeChunk;
  onClick?: () => void;
}

export default function KnowledgeCard({ chunk, onClick }: KnowledgeCardProps) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
          {chunk.source_type}
        </span>
        {chunk.score != null && (
          <span className="text-xs text-gray-400">スコア: {chunk.score.toFixed(3)}</span>
        )}
      </div>
      <h3 className="mb-1 text-sm font-semibold text-gray-900">{chunk.source_file}</h3>
      <p className="text-xs text-gray-400 mb-2">
        チャンク #{chunk.chunk_index}
        {chunk.token_count != null && ` / ${chunk.token_count}トークン`}
      </p>
      <p className="mb-3 text-xs text-gray-500 line-clamp-3">{chunk.content}</p>
    </div>
  );
}
