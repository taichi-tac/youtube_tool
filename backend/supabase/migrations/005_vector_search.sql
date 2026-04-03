-- ============================================================
-- ベクトル検索用RPC関数
-- Supabase SDK からの呼び出し用。
-- pgvector の <=> (コサイン距離) 演算子を使用。
-- ============================================================

CREATE OR REPLACE FUNCTION match_knowledge_chunks(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  filter_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  source_file text,
  source_type text,
  chunk_index int,
  content text,
  token_count int,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    kc.id,
    kc.source_file,
    kc.source_type,
    kc.chunk_index,
    kc.content,
    kc.token_count,
    1 - (kc.embedding <=> query_embedding) as similarity
  FROM knowledge_chunks kc
  WHERE (filter_project_id IS NULL OR kc.project_id = filter_project_id)
    AND kc.embedding IS NOT NULL
  ORDER BY kc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
