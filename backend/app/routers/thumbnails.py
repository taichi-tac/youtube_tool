"""
サムネイルルーター。
サムネイルのCRUD操作およびClaude Visionによる分析機能を提供する。
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Thumbnail
from app.schemas.schemas import (
    ThumbnailAnalyzeRequest,
    ThumbnailCreate,
    ThumbnailResponse,
    ThumbnailUpdate,
)
from app.services.thumbnail_service import (
    analyze_thumbnails_batch,
    create_thumbnail,
    get_thumbnails_by_ids,
    get_thumbnails_by_project,
    update_thumbnail,
)

router = APIRouter(prefix="/thumbnails", tags=["サムネイル"])


@router.post("/{project_id}/analyze")
async def analyze_thumbnails(
    project_id: uuid.UUID,
    body: ThumbnailAnalyzeRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    指定した動画IDリストのサムネイルをClaude Visionで分析する。

    サムネURL取得 → Claude Vision分析 → thumbnailsテーブルに保存 → 分析結果を返す。
    """
    if not body.video_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_idsを1つ以上指定してください",
        )

    results = await analyze_thumbnails_batch(
        video_ids=body.video_ids,
        project_id=project_id,
        db=db,
    )
    return results


@router.get("/{project_id}/compare", response_model=list[ThumbnailResponse])
async def compare_thumbnails(
    project_id: uuid.UUID,
    thumbnail_ids: list[uuid.UUID] = Query(..., description="比較するサムネイルIDリスト"),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Thumbnail]:
    """
    サムネイル比較用データを返す。
    指定したthumbnail_idsのサムネイルを並列表示用に取得する。
    """
    if len(thumbnail_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="比較には2つ以上のサムネイルIDを指定してください",
        )

    thumbnails = await get_thumbnails_by_ids(db, thumbnail_ids)

    # プロジェクトIDの一致を検証
    for t in thumbnails:
        if t.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="指定されたサムネイルはこのプロジェクトに属していません",
            )

    return thumbnails


@router.get("/{project_id}", response_model=list[ThumbnailResponse])
async def list_thumbnails(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    composition_type: Optional[str] = Query(None, description="構図パターンでフィルタ"),
    sort_by_score: bool = Query(False, description="click_score順でソート"),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Thumbnail]:
    """
    プロジェクトのサムネイル一覧を取得する。
    click_score順ソート、composition_typeフィルタに対応。
    """
    return await get_thumbnails_by_project(
        db,
        project_id,
        skip,
        limit,
        composition_type=composition_type,
        sort_by_score=sort_by_score,
    )


@router.post(
    "/{project_id}",
    response_model=ThumbnailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_thumbnail_endpoint(
    project_id: uuid.UUID,
    body: ThumbnailCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Thumbnail:
    """サムネイルを作成する"""
    return await create_thumbnail(
        db=db,
        project_id=project_id,
        image_url=body.image_url,
        source_type=body.source_type,
        video_id=body.video_id,
    )


@router.patch("/{project_id}/{thumbnail_id}", response_model=ThumbnailResponse)
async def update_thumbnail_endpoint(
    project_id: uuid.UUID,
    thumbnail_id: uuid.UUID,
    body: ThumbnailUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Thumbnail:
    """サムネイルを更新する"""
    update_data = body.model_dump(exclude_unset=True)
    result = await update_thumbnail(db, thumbnail_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
    return result
