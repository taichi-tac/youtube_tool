"""
コンセプト設定ルーター。
URL分析、コンセプトブラッシュアップ、同ジャンルチャンネル提案を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.services.concept_service import (
    analyze_text,
    analyze_url,
    brushup_concept,
    suggest_similar_channels,
)

router = APIRouter(prefix="/concept", tags=["コンセプト設定"])


class AnalyzeUrlRequest(BaseModel):
    url: str


class AnalyzeTextRequest(BaseModel):
    text: str


class SuggestChannelsRequest(BaseModel):
    genre: str
    target_audience: str = ""


class BrushupRequest(BaseModel):
    research_video_urls: list[str] = []
    research_data: dict[str, Any] = {}


@router.post("/{project_id}/analyze-url")
async def analyze_url_endpoint(
    project_id: uuid.UUID,
    body: AnalyzeUrlRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """URLを分析してジャンル・ターゲット・コンセプトを自動抽出"""
    if not body.url.strip():
        raise HTTPException(status_code=400, detail="URLを入力してください")
    return await analyze_url(body.url)


@router.post("/{project_id}/analyze-text")
async def analyze_text_endpoint(
    project_id: uuid.UUID,
    body: AnalyzeTextRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """テキストを分析してコンセプト情報を抽出"""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="テキストを入力してください")
    return await analyze_text(body.text)


@router.post("/{project_id}/suggest-channels")
async def suggest_channels_endpoint(
    project_id: uuid.UUID,
    body: SuggestChannelsRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, str]]:
    """同ジャンルのYouTubeチャンネルを提案"""
    return await suggest_similar_channels(body.genre, body.target_audience)


@router.post("/{project_id}/brushup")
async def brushup_concept_endpoint(
    project_id: uuid.UUID,
    body: BrushupRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """リサーチ結果を基にコンセプトをブラッシュアップ"""
    # 現在のコンセプトを取得
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select("*").eq("id", str(project_id)).eq("user_id", user["user_id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        current = result.data[0]
    else:
        raise HTTPException(status_code=501)

    current_concept = {
        "genre": current.get("genre", ""),
        "target_audience": current.get("target_audience", ""),
        "strengths": current.get("strengths", ""),
        "concept": current.get("concept", ""),
    }

    # リサーチデータがない場合、動画URLから分析
    research_data = body.research_data
    if not research_data and body.research_video_urls:
        from app.services.pipeline_service import analyze_video_structure
        research_data = await analyze_video_structure(body.research_video_urls)

    return await brushup_concept(current_concept, research_data or {})
