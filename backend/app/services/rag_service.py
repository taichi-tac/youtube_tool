"""
RAG（Retrieval-Augmented Generation）サービスモジュール。
LangChain + OpenAI Embeddings + pgvector を使用してナレッジ検索を行う。
"""

import uuid
from typing import Any, Optional

from langchain_text_splitters import MarkdownTextSplitter
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import KnowledgeChunk


def _get_embeddings() -> OpenAIEmbeddings:
    """OpenAI Embeddingsクライアントを生成する"""
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY,
    )


def split_markdown(content: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Markdownテキストをチャンクに分割する。

    Args:
        content: 分割対象のMarkdownテキスト
        chunk_size: チャンクサイズ（文字数）
        chunk_overlap: オーバーラップサイズ

    Returns:
        分割されたテキストチャンクのリスト
    """
    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(content)


async def ingest_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    filename: str,
    content: str,
    source_type: str = "user_upload",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> int:
    """
    ドキュメントをチャンク分割し、embeddingを生成してDBに保存する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        filename: ファイル名（source_file カラムに保存）
        content: ドキュメント内容
        source_type: ソース種別 (wa_theory / market_analysis / second_brain / user_upload)
        chunk_size: チャンクサイズ
        chunk_overlap: オーバーラップ

    Returns:
        保存されたチャンク数
    """
    # テキスト分割
    chunks = split_markdown(content, chunk_size, chunk_overlap)
    if not chunks:
        return 0

    # Embedding生成
    embeddings_model = _get_embeddings()
    vectors: list[list[float]] = await embeddings_model.aembed_documents(chunks)

    # DBに保存
    for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        chunk = KnowledgeChunk(
            project_id=project_id,
            source_file=filename,
            source_type=source_type,
            chunk_index=i,
            content=chunk_text,
            embedding=vector,
            token_count=len(chunk_text),
        )
        db.add(chunk)

    await db.flush()
    return len(chunks)


async def search_similar(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    クエリに類似するナレッジチャンクをベクトル検索する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        query: 検索クエリ
        top_k: 取得件数

    Returns:
        類似チャンクのリスト（スコア付き）
    """
    # クエリのembeddingを生成
    embeddings_model = _get_embeddings()
    query_vector: list[float] = await embeddings_model.aembed_query(query)

    # pgvectorのコサイン距離で類似検索
    # <=> はコサイン距離演算子（値が小さいほど類似）
    query_str = text(
        """
        SELECT id, source_file, source_type, chunk_index, content, token_count,
               1 - (embedding <=> :query_vec) AS score
        FROM knowledge_chunks
        WHERE (project_id = :project_id OR project_id IS NULL)
          AND embedding IS NOT NULL
        ORDER BY embedding <=> :query_vec
        LIMIT :top_k
        """
    )

    result = await db.execute(
        query_str,
        {
            "query_vec": str(query_vector),
            "project_id": str(project_id),
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    return [
        {
            "id": row.id,
            "source_file": row.source_file,
            "source_type": row.source_type,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "token_count": row.token_count,
            "score": float(row.score) if row.score else 0.0,
        }
        for row in rows
    ]


async def get_rag_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    top_k: int = 5,
) -> Optional[str]:
    """
    RAGコンテキストを構築する（台本生成等で使用）。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        query: 検索クエリ
        top_k: 取得件数

    Returns:
        参考情報テキスト（見つからない場合はNone）
    """
    results = await search_similar(db, project_id, query, top_k)
    if not results:
        return None

    context_parts: list[str] = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"【参考{i}】（出典: {r['source_file']}）\n{r['content']}"
        )

    return "\n\n".join(context_parts)
