"""
プロジェクトルーター。
プロジェクトのCRUD操作を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_supabase, use_supabase_sdk
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
):
    """ユーザーのプロジェクト一覧を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select("*").eq(
            "user_id", user["user_id"]
        ).order(
            "created_at", desc=True
        ).range(skip, skip + limit - 1).execute()
        return result.data

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
):
    """新規プロジェクトを作成する"""
    if use_supabase_sdk():
        sb = get_supabase()
        data = {
            "user_id": user["user_id"],
            "name": body.name,
            "channel_id": body.channel_id,
            "channel_url": body.channel_url,
            "genre": body.genre,
            "target_audience": body.target_audience,
            "concept": body.concept,
            "center_pin": body.center_pin,
            "settings": body.settings or {},
        }
        result = sb.table("projects").insert(data).execute()
        return result.data[0]

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
):
    """プロジェクトを取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select("*").eq(
            "id", str(project_id)
        ).eq(
            "user_id", user["user_id"]
        ).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        return result.data[0]

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
):
    """プロジェクトを更新する"""
    if use_supabase_sdk():
        sb = get_supabase()
        # 存在確認
        existing = sb.table("projects").select("id").eq(
            "id", str(project_id)
        ).eq(
            "user_id", user["user_id"]
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            return existing.data[0]

        result = sb.table("projects").update(update_data).eq(
            "id", str(project_id)
        ).eq(
            "user_id", user["user_id"]
        ).execute()
        return result.data[0]

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
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("projects").select("id").eq(
            "id", str(project_id)
        ).eq(
            "user_id", user["user_id"]
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        sb.table("projects").delete().eq(
            "id", str(project_id)
        ).eq(
            "user_id", user["user_id"]
        ).execute()
        return

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


# === プロファイル エンドポイント ===

from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    genre: str | None = None
    target_audience: str | None = None
    concept: str | None = None
    center_pin: str | None = None
    benchmark_channels: list[str] | None = None
    strengths: str | None = None
    content_style: str | None = None


@router.get("/{project_id}/profile")
async def get_profile(
    project_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """プロジェクトのプロファイル情報を取得"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select(
            "genre,target_audience,concept,center_pin,benchmark_channels,strengths,content_style,onboarding_completed"
        ).eq("id", str(project_id)).eq("user_id", user["user_id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        return result.data[0]
    else:
        raise HTTPException(status_code=501, detail="SQLAlchemy未対応")


@router.patch("/{project_id}/profile")
async def update_profile(
    project_id: uuid.UUID,
    body: ProfileUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """プロファイルを更新する"""
    if use_supabase_sdk():
        sb = get_supabase()
        update_data = body.model_dump(exclude_unset=True)
        update_data["onboarding_completed"] = True
        result = sb.table("projects").update(update_data).eq(
            "id", str(project_id)
        ).eq("user_id", user["user_id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        return result.data[0]
    else:
        raise HTTPException(status_code=501, detail="SQLAlchemy未対応")
