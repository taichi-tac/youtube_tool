"""
一気通貫パイプラインルーター。
リサーチ → 企画 → 台本の一貫フローを提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.services.pipeline_service import analyze_video_structure, pipeline_to_script, regenerate_persona

router = APIRouter(prefix="/pipeline", tags=["パイプライン"])


class AnalyzeRequest(BaseModel):
    video_urls: list[str]


class PipelineRequest(BaseModel):
    video_urls: list[str]


class RegeneratePersonaRequest(BaseModel):
    title: str
    concept: str
    current_target: str = ""
    current_inner_voice: str = ""


@router.post("/{project_id}/analyze")
async def analyze_videos(
    project_id: uuid.UUID,
    body: AnalyzeRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """伸びてる動画のURLから共通構造を分析する"""
    if len(body.video_urls) < 1 or len(body.video_urls) > 10:
        raise HTTPException(status_code=400, detail="URLは1〜10個で指定してください")

    result = await analyze_video_structure(body.video_urls)
    return result


@router.post("/{project_id}/full")
async def full_pipeline(
    project_id: uuid.UUID,
    body: PipelineRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """リサーチ→企画→台本パラメータまでの一気通貫パイプライン"""
    if len(body.video_urls) < 1:
        raise HTTPException(status_code=400, detail="URLを1つ以上指定してください")

    # プロファイル取得
    profile = {}
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("projects").select("*").eq("id", str(project_id)).eq("user_id", user["user_id"]).execute()
        if result.data:
            profile = result.data[0]

    pipeline_result = await pipeline_to_script(
        video_urls=body.video_urls,
        profile=profile,
        project_id=str(project_id),
    )

    return pipeline_result


@router.post("/{project_id}/regenerate-persona")
async def regenerate_persona_endpoint(
    project_id: uuid.UUID,
    body: RegeneratePersonaRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """企画のペルソナと心の声を再生成する"""
    return await regenerate_persona(
        title=body.title,
        concept=body.concept,
        current_target=body.current_target,
        current_inner_voice=body.current_inner_voice,
    )
