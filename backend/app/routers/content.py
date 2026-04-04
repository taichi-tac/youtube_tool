"""
コンテンツ変換ルーター。
台本からタイムスタンプ、コミュニティ投稿、ショート提案、メディア変換を提供する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.services.content_service import (
    convert_to_media,
    generate_community_post,
    generate_timestamps,
    suggest_shorts,
)

router = APIRouter(prefix="/content", tags=["コンテンツ変換"])


class TimestampRequest(BaseModel):
    script_id: str


class CommunityPostRequest(BaseModel):
    script_id: str


class ShortsRequest(BaseModel):
    script_id: str
    genre: str = ""
    suggestions: list[str] = []


class MediaConvertRequest(BaseModel):
    script_id: str
    format: str = "x"  # "x", "blog", "note"


def _get_script(script_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """台本データを取得"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("scripts").select("*").eq("id", script_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="台本が見つかりません")
        return result.data[0]
    raise HTTPException(status_code=501, detail="SQLAlchemy未対応")


@router.post("/{project_id}/timestamps")
async def create_timestamps(
    project_id: uuid.UUID,
    body: TimestampRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, str]]:
    """台本からタイムスタンプ（LP風ブレット）を生成"""
    script = _get_script(body.script_id, user)
    script_body = (script.get("hook", "") or "") + "\n" + (script.get("body", "") or "") + "\n" + (script.get("closing", "") or "")

    if not script_body.strip():
        raise HTTPException(status_code=400, detail="台本の本文がありません")

    return await generate_timestamps(script_body, script.get("title", ""))


@router.post("/{project_id}/community-post")
async def create_community_post(
    project_id: uuid.UUID,
    body: CommunityPostRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """コミュニティ投稿用テキストを生成"""
    script = _get_script(body.script_id, user)

    return await generate_community_post(
        title=script.get("title", ""),
        script_hook=script.get("hook", "") or "",
        target_viewer=script.get("target_viewer", "") or "",
    )


@router.post("/{project_id}/shorts")
async def create_shorts_suggestions(
    project_id: uuid.UUID,
    body: ShortsRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """ショート動画の切り抜きポイントを提案"""
    script = _get_script(body.script_id, user)
    script_body = (script.get("hook", "") or "") + "\n" + (script.get("body", "") or "") + "\n" + (script.get("closing", "") or "")

    if not script_body.strip():
        raise HTTPException(status_code=400, detail="台本の本文がありません")

    return await suggest_shorts(script_body, body.genre, body.suggestions)


@router.post("/{project_id}/convert")
async def convert_media(
    project_id: uuid.UUID,
    body: MediaConvertRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """台本をX/ブログ/note記事に変換"""
    if body.format not in ("x", "blog", "note"):
        raise HTTPException(status_code=400, detail="formatはx/blog/noteのいずれかを指定してください")

    script = _get_script(body.script_id, user)
    script_body = (script.get("hook", "") or "") + "\n" + (script.get("body", "") or "") + "\n" + (script.get("closing", "") or "")

    if not script_body.strip():
        raise HTTPException(status_code=400, detail="台本の本文がありません")

    return await convert_to_media(script_body, script.get("title", ""), body.format)
