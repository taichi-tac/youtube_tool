"""
ナレッジルーター。
RAG用ドキュメントのアップロード・検索を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, use_supabase_sdk
from app.core.security import get_current_user
from app.schemas.schemas import (
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeUploadResponse,
)
from app.services.rag_service import ingest_document, search_similar

router = APIRouter(prefix="/knowledge", tags=["ナレッジ"])


@router.post(
    "/{project_id}/upload",
    response_model=KnowledgeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeUploadResponse:
    """
    Markdownドキュメントをアップロードしてベクトル化する。
    対応形式: .md, .txt
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="ファイル名が必要です")

    # ファイル形式チェック
    allowed_extensions = {".md", ".txt", ".markdown"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(allowed_extensions)}",
        )

    # ファイル内容を読み取り
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8")

    if not content.strip():
        raise HTTPException(status_code=400, detail="ファイルが空です")

    # ドキュメントをチャンク分割・embedding生成・DB保存
    chunk_count = await ingest_document(
        project_id=project_id,
        filename=file.filename,
        content=content,
        db=db,
    )

    return KnowledgeUploadResponse(
        filename=file.filename,
        chunk_count=chunk_count,
        message=f"{chunk_count}個のチャンクに分割して保存しました",
    )


@router.post("/{project_id}/search", response_model=list[KnowledgeChunkResponse])
async def search_knowledge(
    project_id: uuid.UUID,
    body: KnowledgeSearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """ナレッジベースをベクトル検索する"""
    results = await search_similar(
        project_id=project_id,
        query=body.query,
        top_k=body.top_k,
        db=db,
    )
    return results
