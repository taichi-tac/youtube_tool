"""
キーワードルーター。
キーワード管理・サジェスト取得を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Keyword
from app.schemas.schemas import (
    KeywordCreate,
    KeywordResponse,
    KeywordSuggestRequest,
    KeywordSuggestResponse,
    KeywordUpdate,
)
from app.services.keyword_service import alphabet_soup, extract_suggestions

router = APIRouter(prefix="/keywords", tags=["キーワード"])


@router.get("/{project_id}", response_model=list[KeywordResponse])
async def list_keywords(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Keyword]:
    """プロジェクトのキーワード一覧を取得する"""
    stmt = (
        select(Keyword)
        .where(Keyword.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .order_by(Keyword.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{project_id}", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    project_id: uuid.UUID,
    body: KeywordCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Keyword:
    """キーワードを手動追加する"""
    keyword = Keyword(
        project_id=project_id,
        keyword=body.keyword,
        seed_keyword=body.seed_keyword,
        source=body.source,
        is_selected=body.is_selected,
    )
    db.add(keyword)
    await db.flush()
    await db.refresh(keyword)
    return keyword


@router.patch("/{project_id}/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    project_id: uuid.UUID,
    keyword_id: uuid.UUID,
    body: KeywordUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Keyword:
    """キーワードを更新する（選択フラグ等）"""
    stmt = select(Keyword).where(
        Keyword.id == keyword_id,
        Keyword.project_id == project_id,
    )
    result = await db.execute(stmt)
    keyword = result.scalar_one_or_none()
    if keyword is None:
        raise HTTPException(status_code=404, detail="キーワードが見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(keyword, key, value)

    await db.flush()
    await db.refresh(keyword)
    return keyword


@router.post("/{project_id}/suggest", response_model=KeywordSuggestResponse)
async def get_suggestions(
    project_id: uuid.UUID,
    body: KeywordSuggestRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> KeywordSuggestResponse:
    """YouTubeサジェストキーワードを取得する"""
    suggestions = await extract_suggestions(
        seed_keyword=body.seed_keyword,
        language=body.language,
    )
    return KeywordSuggestResponse(
        seed_keyword=body.seed_keyword,
        suggestions=suggestions,
    )


@router.post("/{project_id}/alphabet-soup")
async def run_alphabet_soup(
    project_id: uuid.UUID,
    body: KeywordSuggestRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """アルファベットスープ法でサジェストキーワードを取得する"""
    results = await alphabet_soup(
        seed_keyword=body.seed_keyword,
        language=body.language,
    )
    # 全サジェストの合計数を計算
    total = sum(len(v) for v in results.values())
    return {
        "seed_keyword": body.seed_keyword,
        "total_suggestions": total,
        "results": results,
    }


@router.delete("/{project_id}/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    project_id: uuid.UUID,
    keyword_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """キーワードを削除する"""
    stmt = select(Keyword).where(
        Keyword.id == keyword_id,
        Keyword.project_id == project_id,
    )
    result = await db.execute(stmt)
    keyword = result.scalar_one_or_none()
    if keyword is None:
        raise HTTPException(status_code=404, detail="キーワードが見つかりません")

    await db.delete(keyword)
    await db.flush()
