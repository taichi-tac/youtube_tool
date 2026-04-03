"""
サムネイルルーター。
サムネイルのCRUD操作およびClaude Visionによる分析機能を提供する。
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_supabase, use_supabase_sdk
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
    """
    if not body.video_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_idsを1つ以上指定してください",
        )

    if use_supabase_sdk():
        from app.services.thumbnail_service import analyze_thumbnails_batch_supabase
        results = await analyze_thumbnails_batch_supabase(
            video_ids=body.video_ids,
            project_id=project_id,
        )
        return results

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
):
    """
    サムネイル比較用データを返す。
    指定したthumbnail_idsのサムネイルを並列表示用に取得する。
    """
    if len(thumbnail_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="比較には2つ以上のサムネイルIDを指定してください",
        )

    if use_supabase_sdk():
        sb = get_supabase()
        ids_str = [str(tid) for tid in thumbnail_ids]
        result = sb.table("thumbnails").select("*").in_("id", ids_str).execute()
        thumbnails = result.data

        for t in thumbnails:
            if t.get("project_id") != str(project_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="指定されたサムネイルはこのプロジェクトに属していません",
                )
        return thumbnails

    thumbnails = await get_thumbnails_by_ids(db, thumbnail_ids)

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
):
    """
    プロジェクトのサムネイル一覧を取得する。
    """
    if use_supabase_sdk():
        sb = get_supabase()
        query = sb.table("thumbnails").select("*").eq(
            "project_id", str(project_id)
        )

        if composition_type is not None:
            query = query.eq("composition_type", composition_type)

        if sort_by_score:
            query = query.order("click_score", desc=True, nullsfirst=False)
        else:
            query = query.order("created_at", desc=True)

        result = query.range(skip, skip + limit - 1).execute()
        return result.data

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
):
    """サムネイルを作成する"""
    if use_supabase_sdk():
        sb = get_supabase()
        data = {
            "project_id": str(project_id),
            "video_id": str(body.video_id) if body.video_id else None,
            "image_url": body.image_url,
            "source_type": body.source_type,
        }
        result = sb.table("thumbnails").insert(data).execute()
        return result.data[0]

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
):
    """サムネイルを更新する"""
    if use_supabase_sdk():
        sb = get_supabase()
        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            existing = sb.table("thumbnails").select("*").eq(
                "id", str(thumbnail_id)
            ).execute()
            if not existing.data:
                raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
            return existing.data[0]

        result = sb.table("thumbnails").update(update_data).eq(
            "id", str(thumbnail_id)
        ).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
        return result.data[0]

    update_data = body.model_dump(exclude_unset=True)
    result = await update_thumbnail(db, thumbnail_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
    return result
