"""
ナレッジ取り込みタスク。
複数ドキュメントを一括でチャンク分割・ベクトル化して保存する。
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag_service import ingest_document


async def batch_ingest_documents(
    db: AsyncSession,
    project_id: uuid.UUID,
    documents: list[dict[str, str]],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> dict[str, Any]:
    """
    複数ドキュメントを一括でベクトル化して保存する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        documents: ドキュメントリスト [{"filename": "...", "content": "..."}]
        chunk_size: チャンクサイズ
        chunk_overlap: オーバーラップサイズ

    Returns:
        処理結果のサマリー
    """
    total_chunks = 0
    processed_files: list[str] = []
    errors: list[str] = []

    for doc in documents:
        filename = doc.get("filename", "unknown")
        content = doc.get("content", "")

        if not content.strip():
            errors.append(f"{filename}: 内容が空です")
            continue

        try:
            chunk_count = await ingest_document(
                db=db,
                project_id=project_id,
                filename=filename,
                content=content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            total_chunks += chunk_count
            processed_files.append(filename)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    return {
        "total_chunks": total_chunks,
        "processed_files": processed_files,
        "file_count": len(processed_files),
        "errors": errors,
    }
