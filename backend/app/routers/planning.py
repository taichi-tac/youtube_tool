"""
AI企画提案ルーター。
ユーザーのプロファイルに基づいて企画候補を自動生成する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.services.planning_service import generate_project_ideas

router = APIRouter(prefix="/planning", tags=["企画提案"])


class PlanningRequest(BaseModel):
    count: int = 10


class PlanningNextRequest(BaseModel):
    count: int = 10
    exclude_keywords: list[str] = []


@router.post("/{project_id}/ideas")
async def generate_ideas(
    project_id: uuid.UUID,
    body: PlanningRequest = PlanningRequest(),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """プロファイルに基づいて企画を生成する"""
    # プロファイル取得
    profile = _get_profile(project_id, user)

    if not profile.get("genre"):
        raise HTTPException(
            status_code=400,
            detail="ジャンルが設定されていません。先にプロファイルを設定してください。",
        )

    ideas = await generate_project_ideas(
        genre=profile.get("genre", ""),
        target_audience=profile.get("target_audience", ""),
        benchmark_channels=profile.get("benchmark_channels", []),
        strengths=profile.get("strengths", ""),
        content_style=profile.get("content_style", ""),
        count=body.count,
    )

    return ideas


@router.post("/{project_id}/ideas/next")
async def generate_more_ideas(
    project_id: uuid.UUID,
    body: PlanningNextRequest = PlanningNextRequest(),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """追加の企画を生成する（前回と重複しないように）"""
    profile = _get_profile(project_id, user)

    if not profile.get("genre"):
        raise HTTPException(
            status_code=400,
            detail="ジャンルが設定されていません。",
        )

    ideas = await generate_project_ideas(
        genre=profile.get("genre", ""),
        target_audience=profile.get("target_audience", ""),
        benchmark_channels=profile.get("benchmark_channels", []),
        strengths=profile.get("strengths", ""),
        content_style=profile.get("content_style", ""),
        count=body.count,
        exclude_keywords=body.exclude_keywords,
    )

    return ideas


def _get_profile(project_id: uuid.UUID, user: dict[str, Any]) -> dict[str, Any]:
    """プロジェクトのプロファイル情報を取得"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select("*").eq("id", str(project_id)).eq("user_id", user["user_id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        return result.data[0]
    else:
        raise HTTPException(status_code=501, detail="SQLAlchemy未対応")
