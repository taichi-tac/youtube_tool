"""
理論ルーター。
動画企画の理論・フレームワークのCRUD操作を提供する。
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
) -> list[Theory]:
    """プロジェクトの理論一覧を取得する"""
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
) -> Theory:
    """理論を作成する"""
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
) -> Theory:
    """理論の詳細を取得する"""
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
) -> Theory:
    """理論を更新する"""
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
    deleted = await delete_theory(db, theory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="理論が見つかりません")
