/** バックエンド KnowledgeChunkResponse に対応 */
export interface KnowledgeChunk {
  id: string;
  source_file: string;
  source_type: string;
  chunk_index: number;
  content: string;
  token_count: number | null;
  score: number | null;
}

export interface KnowledgeSearchRequest {
  query: string;
  top_k?: number;
}

/** アップロードレスポンス */
export interface KnowledgeUploadResponse {
  filename: string;
  chunk_count: number;
  message: string;
}
