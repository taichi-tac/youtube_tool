"""
理論・フレームワークサービスモジュール。
動画企画に使用する理論やフレームワークの管理を行う。
"""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Theory


async def create_theory(
    db: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    category: str,
    body: str,
    source_type: str,
    source_ref: Optional[str] = None,
    evidence: Optional[dict[str, Any]] = None,
    confidence: Optional[float] = None,
) -> Theory:
    """
    理論レコードを作成する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        title: 理論タイトル
        category: カテゴリ (hook / retention / ctr / seo / storytelling / editing)
        body: 理論本文
        source_type: ソース種別 (wa_theory / user_defined / ai_extracted)
        source_ref: 参照元
        evidence: エビデンス（JSONB）
        confidence: 確信度

    Returns:
        作成された理論オブジェクト
    """
    theory = Theory(
        project_id=project_id,
        title=title,
        category=category,
        body=body,
        source_type=source_type,
        source_ref=source_ref,
        evidence=evidence,
        confidence=confidence,
    )
    db.add(theory)
    await db.flush()
    await db.refresh(theory)
    return theory


async def get_theories_by_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Theory]:
    """プロジェクトに紐づく理論一覧を取得する"""
    stmt = select(Theory).where(Theory.project_id == project_id)
    if category:
        stmt = stmt.where(Theory.category == category)
    stmt = stmt.offset(skip).limit(limit).order_by(Theory.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_theory_by_id(
    db: AsyncSession,
    theory_id: uuid.UUID,
) -> Optional[Theory]:
    """IDで理論を取得する"""
    stmt = select(Theory).where(Theory.id == theory_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_theory(
    db: AsyncSession,
    theory_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[Theory]:
    """理論レコードを更新する"""
    theory = await get_theory_by_id(db, theory_id)
    if theory is None:
        return None

    for key, value in kwargs.items():
        if value is not None and hasattr(theory, key):
            setattr(theory, key, value)

    await db.flush()
    await db.refresh(theory)
    return theory


async def delete_theory(
    db: AsyncSession,
    theory_id: uuid.UUID,
) -> bool:
    """理論レコードを削除する"""
    theory = await get_theory_by_id(db, theory_id)
    if theory is None:
        return False

    await db.delete(theory)
    await db.flush()
    return True
