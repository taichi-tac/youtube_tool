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

    # 生成した企画をDBに保存
    _save_ideas(project_id, ideas)

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

    _save_ideas(project_id, ideas)

    return ideas


@router.get("/{project_id}/history")
async def get_idea_history(
    project_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """過去に生成した企画の履歴を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("theories").select("*").eq(
            "project_id", str(project_id)
        ).eq("category", "planning").order(
            "created_at", desc=True
        ).limit(50).execute()

        # theoriesテーブルのデータを企画形式に変換
        ideas = []
        for t in result.data:
            evidence = t.get("evidence") or {}
            ideas.append({
                "id": t["id"],
                "title": t["title"],
                "target_viewer": evidence.get("target_viewer", ""),
                "keyword": evidence.get("keyword", ""),
                "reason": t.get("body", ""),
                "demand_score": float(evidence.get("demand_score", 5)),
                "niche_score": float(evidence.get("niche_score", 5)),
                "created_at": t["created_at"],
            })
        return ideas
    raise HTTPException(status_code=501, detail="SQLAlchemy未対応")


def _save_ideas(project_id: uuid.UUID, ideas: list[dict[str, Any]]) -> None:
    """企画をtheoriesテーブルに保存する（category='planning'）"""
    if not use_supabase_sdk() or not ideas:
        return
    sb = get_supabase()
    rows = []
    for idea in ideas:
        rows.append({
            "project_id": str(project_id),
            "title": idea.get("title", ""),
            "category": "planning",
            "body": idea.get("reason", ""),
            "source_type": "ai_extracted",
            "evidence": {
                "target_viewer": idea.get("target_viewer", ""),
                "keyword": idea.get("keyword", ""),
                "demand_score": idea.get("demand_score", 5),
                "niche_score": idea.get("niche_score", 5),
            },
            "confidence": round((idea.get("demand_score", 5) * idea.get("niche_score", 5)) / 100, 2),
            "is_active": True,
        })
    try:
        sb.table("theories").insert(rows).execute()
    except Exception:
        pass  # 保存失敗しても企画生成自体は止めない


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
