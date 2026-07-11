"""
一気通貫パイプラインルーター。
リサーチ → 企画 → 台本の一貫フローを提供する。
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.services.pipeline_service import analyze_video_structure, pipeline_to_script, regenerate_persona, regenerate_proposals
from app.services.rag_service import ingest_document

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


class RegenerateProposalsRequest(BaseModel):
    video_urls: list[str]
    feedback: str
    current_proposals: list[dict[str, Any]] = []


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
) -> EventSourceResponse:
    """
    リサーチ→企画→台本パラメータまでの一気通貫パイプライン（SSE 配信）。

    Claude 分析は 20-40 秒かかるため、SSE で 15 秒 ping と 10 秒毎の progress
    イベントを流し続けて、Render/Cloudflare のアイドルタイムアウトで
    接続が切れる（結果 CORS ヘッダごと落ちる）ことを防ぐ。
    """
    if len(body.video_urls) < 1:
        raise HTTPException(status_code=400, detail="URLを1つ以上指定してください")

    # プロファイル取得（失敗しても続行して SSE でエラーを返す）
    profile = {}
    try:
        if use_supabase_sdk():
            sb = get_supabase()
            result = sb.table("projects").select("*").eq("id", str(project_id)).eq("user_id", user["user_id"]).execute()
            if result.data:
                profile = result.data[0]
    except Exception as e:
        logger_msg = f"プロファイル取得失敗（続行）: {e}"
        import logging
        logging.getLogger(__name__).warning(logger_msg)

    from app.core.api_keys import fetch_project_keys, get_anthropic_key, get_youtube_key
    try:
        project_keys = fetch_project_keys(project_id)
    except Exception:
        project_keys = {}
    anthropic_key = get_anthropic_key(project_keys)
    youtube_key = get_youtube_key(project_keys)

    async def _run() -> dict[str, Any]:
        return await pipeline_to_script(
            video_urls=body.video_urls,
            profile=profile,
            project_id=str(project_id),
            anthropic_api_key=anthropic_key,
            youtube_api_key=youtube_key,
        )

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"pct": 5}, ensure_ascii=False)}

        task = asyncio.create_task(_run())
        _progress_steps = [15, 30, 45, 60, 75, 85, 92, 96]
        _step_idx = 0
        # asyncio.wait は task の例外を再送出しないので、
        # wait_for + shield の「例外が漏れる」問題を回避できる。
        while not task.done():
            done_set, _pending = await asyncio.wait({task}, timeout=8.0)
            if not done_set:
                pct = _progress_steps[min(_step_idx, len(_progress_steps) - 1)]
                _step_idx += 1
                yield {
                    "event": "progress",
                    "data": json.dumps({"pct": pct}, ensure_ascii=False),
                }

        exc = task.exception()
        if exc is not None:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
            }
            return

        try:
            payload = json.dumps(task.result(), ensure_ascii=False, default=str)
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"結果のシリアライズに失敗: {e}"}, ensure_ascii=False),
            }
            return

        yield {"event": "done", "data": payload}

    return EventSourceResponse(event_generator(), ping=15)


@router.post("/{project_id}/regenerate-persona")
async def regenerate_persona_endpoint(
    project_id: uuid.UUID,
    body: RegeneratePersonaRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """企画のペルソナと心の声を再生成する"""
    from app.core.api_keys import fetch_project_keys, get_anthropic_key
    project_keys = fetch_project_keys(project_id)
    return await regenerate_persona(
        title=body.title,
        concept=body.concept,
        current_target=body.current_target,
        current_inner_voice=body.current_inner_voice,
        anthropic_api_key=get_anthropic_key(project_keys),
    )


@router.post("/{project_id}/regenerate-proposals")
async def regenerate_proposals_endpoint(
    project_id: uuid.UUID,
    body: RegenerateProposalsRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """フィードバックを反映して企画を出し直す。フィードバックは自動的にナレッジに蓄積される。"""
    # フィードバックを企画指摘ナレッジとして自動保存
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    feedback_content = (
        f"## 企画フィードバック ({timestamp})\n\n"
        f"### 指摘内容\n{body.feedback}\n\n"
    )
    if body.current_proposals:
        feedback_content += "### 対象企画\n"
        for p in body.current_proposals:
            feedback_content += f"- {p.get('title', '無題')}\n"

    try:
        await ingest_document(
            project_id=project_id,
            filename=f"proposal_feedback_{timestamp.replace(' ', '_').replace(':', '')}.md",
            content=feedback_content,
            source_type="proposal_feedback",
            db=db,
        )
    except Exception:
        pass  # ナレッジ保存失敗は企画再生成をブロックしない

    from app.core.api_keys import fetch_project_keys, get_anthropic_key
    project_keys = fetch_project_keys(project_id)
    result = await regenerate_proposals(
        video_urls=body.video_urls,
        feedback=body.feedback,
        current_proposals=body.current_proposals,
        project_id=str(project_id),
        anthropic_api_key=get_anthropic_key(project_keys),
    )
    result["feedback_saved"] = True
    return result
