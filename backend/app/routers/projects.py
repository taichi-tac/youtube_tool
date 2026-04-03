"""
プロジェクトルーター。
プロジェクトのCRUD操作を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project
from app.schemas.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["プロジェクト"])


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    """ユーザーのプロジェクト一覧を取得する"""
    stmt = (
        select(Project)
        .where(Project.user_id == uuid.UUID(user["user_id"]))
        .offset(skip)
        .limit(limit)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """新規プロジェクトを作成する"""
    project = Project(
        user_id=uuid.UUID(user["user_id"]),
        name=body.name,
        channel_id=body.channel_id,
        channel_url=body.channel_url,
        genre=body.genre,
        target_audience=body.target_audience,
        concept=body.concept,
        center_pin=body.center_pin,
        settings=body.settings or {},
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """プロジェクトを取得する"""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == uuid.UUID(user["user_id"]),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """プロジェクトを更新する"""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == uuid.UUID(user["user_id"]),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """プロジェクトを削除する"""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == uuid.UUID(user["user_id"]),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    await db.delete(project)
    await db.flush()
