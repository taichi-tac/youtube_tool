"""
理論ルーター。
動画企画の理論・フレームワークのCRUD操作を提供する。
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.models.models import Theory
from app.schemas.schemas import TheoryCreate, TheoryResponse, TheoryUpdate
from app.services.theory_service import (
    create_theory,
    delete_theory,
    get_theories_by_project,
    get_theory_by_id,
    update_theory,
)

router = APIRouter(prefix="/theories", tags=["理論"])


@router.get("/{project_id}", response_model=list[TheoryResponse])
async def list_theories(
    project_id: uuid.UUID,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """プロジェクトの理論一覧を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        query = sb.table("theories").select("*").eq(
            "project_id", str(project_id)
        )
        if category:
            query = query.eq("category", category)
        result = query.order(
            "created_at", desc=True
        ).range(skip, skip + limit - 1).execute()
        return result.data

    return await get_theories_by_project(db, project_id, category, skip, limit)


@router.post(
    "/{project_id}",
    response_model=TheoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_theory_endpoint(
    project_id: uuid.UUID,
    body: TheoryCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """理論を作成する"""
    if use_supabase_sdk():
        sb = get_supabase()
        data = {
            "project_id": str(project_id),
            "title": body.title,
            "category": body.category,
            "body": body.body,
            "source_type": body.source_type,
            "source_ref": body.source_ref,
            "evidence": body.evidence,
            "confidence": float(body.confidence) if body.confidence is not None else None,
        }
        result = sb.table("theories").insert(data).execute()
        return result.data[0]

    return await create_theory(
        db=db,
        project_id=project_id,
        title=body.title,
        category=body.category,
        body=body.body,
        source_type=body.source_type,
        source_ref=body.source_ref,
        evidence=body.evidence,
        confidence=body.confidence,
    )


@router.get("/{project_id}/{theory_id}", response_model=TheoryResponse)
async def get_theory_endpoint(
    project_id: uuid.UUID,
    theory_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """理論の詳細を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("theories").select("*").eq(
            "id", str(theory_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="理論が見つかりません")
        return result.data[0]

    theory = await get_theory_by_id(db, theory_id)
    if theory is None or theory.project_id != project_id:
        raise HTTPException(status_code=404, detail="理論が見つかりません")
    return theory


@router.patch("/{project_id}/{theory_id}", response_model=TheoryResponse)
async def update_theory_endpoint(
    project_id: uuid.UUID,
    theory_id: uuid.UUID,
    body: TheoryUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """理論を更新する"""
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("theories").select("id").eq(
            "id", str(theory_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="理論が見つかりません")

        update_data = body.model_dump(exclude_unset=True)
        # confidence をfloatに変換
        if "confidence" in update_data and update_data["confidence"] is not None:
            update_data["confidence"] = float(update_data["confidence"])
        if not update_data:
            return existing.data[0]

        result = sb.table("theories").update(update_data).eq(
            "id", str(theory_id)
        ).execute()
        return result.data[0]

    update_data = body.model_dump(exclude_unset=True)
    result = await update_theory(db, theory_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="理論が見つかりません")
    return result


@router.delete("/{project_id}/{theory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theory_endpoint(
    project_id: uuid.UUID,
    theory_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """理論を削除する"""
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("theories").select("id").eq(
            "id", str(theory_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="理論が見つかりません")

        sb.table("theories").delete().eq("id", str(theory_id)).execute()
        return

    deleted = await delete_theory(db, theory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="理論が見つかりません")
