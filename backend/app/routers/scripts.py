"""
台本ルーター。
台本のCRUD操作およびSSEストリーミング生成を提供する。
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import async_session_factory, get_db, get_supabase, use_supabase_sdk
from app.core.security import get_current_user
from app.models.models import Script
from app.schemas.schemas import ScriptCreate, ScriptGenerateRequest, ScriptResponse, ScriptUpdate
from app.services.rag_service import get_rag_context
from app.services.script_service import generate_script_stream

router = APIRouter(prefix="/scripts", tags=["台本"])


@router.get("/{project_id}", response_model=list[ScriptResponse])
async def list_scripts(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """プロジェクトの台本一覧を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("scripts").select("*").eq(
            "project_id", str(project_id)
        ).order(
            "created_at", desc=True
        ).range(skip, skip + limit - 1).execute()
        return result.data

    stmt = (
        select(Script)
        .where(Script.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .order_by(Script.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{project_id}", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def create_script(
    project_id: uuid.UUID,
    body: ScriptCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """台本レコードを手動作成する"""
    if use_supabase_sdk():
        sb = get_supabase()
        data = {
            "project_id": str(project_id),
            "keyword_id": str(body.keyword_id) if body.keyword_id else None,
            "title": body.title,
            "status": "draft",
            "target_viewer": body.target_viewer,
            "viewer_problem": body.viewer_problem,
            "promise": body.promise,
            "uniqueness": body.uniqueness,
        }
        result = sb.table("scripts").insert(data).execute()
        return result.data[0]

    script = Script(
        project_id=project_id,
        keyword_id=body.keyword_id,
        title=body.title,
        status="draft",
        target_viewer=body.target_viewer,
        viewer_problem=body.viewer_problem,
        promise=body.promise,
        uniqueness=body.uniqueness,
    )
    db.add(script)
    await db.flush()
    await db.refresh(script)
    return script


@router.post("/{project_id}/generate")
async def generate_script_sse(
    project_id: uuid.UUID,
    body: ScriptGenerateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """
    Claude APIで台本をSSEストリーミング生成する。
    クライアントはServer-Sent Eventsとして受信する。
    """
    # モデルナレッジ取得（オプション）
    model_context = None
    if body.model_id and use_supabase_sdk():
        from app.routers.models import get_model_context
        sb_m = get_supabase()
        model_result = sb_m.table("knowledge_models").select("*").eq("id", str(body.model_id)).execute()
        if model_result.data:
            model_context = get_model_context(model_result.data[0])

    # RAGコンテキスト取得（オプション）
    rag_context = None
    if body.use_rag:
        rag_context = await get_rag_context(
            project_id=project_id,
            query=f"{body.title} {body.viewer_problem or ''}",
            db=db,
        )

    if use_supabase_sdk():
        sb = get_supabase()
        # 台本レコードを事前作成
        script_data = {
            "project_id": str(project_id),
            "keyword_id": str(body.keyword_id) if body.keyword_id else None,
            "title": body.title,
            "status": "generating",
            "target_viewer": body.target_viewer,
            "viewer_problem": body.viewer_problem,
            "promise": body.promise,
            "uniqueness": body.uniqueness,
            "generation_model": "claude-sonnet-4-20250514",
        }
        insert_result = sb.table("scripts").insert(script_data).execute()
        script_id = insert_result.data[0]["id"]

        async def event_generator_supabase():
            """SSEイベント（Supabase SDK版）"""
            full_text: list[str] = []
            yield {
                "event": "start",
                "data": json.dumps({"script_id": str(script_id)}, ensure_ascii=False),
            }
            try:
                async for chunk in generate_script_stream(
                    title=body.title,
                    target_viewer=body.target_viewer,
                    viewer_problem=body.viewer_problem,
                    promise=body.promise,
                    uniqueness=body.uniqueness,
                    additional_context=(body.additional_context or "") + ("\n\n" + model_context if model_context else ""),
                    rag_context=rag_context,
                ):
                    full_text.append(chunk)
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"text": chunk}, ensure_ascii=False),
                    }

                full_body_text = "".join(full_text)
                hook_text, body_content, closing_text = _parse_script_json(full_body_text)
                total_word_count = len(hook_text or "") + len(body_content or "") + len(closing_text or "")

                # DB保存
                try:
                    sb_save = get_supabase()
                    sb_save.table("scripts").update({
                        "hook": hook_text,
                        "body": body_content,
                        "closing": closing_text,
                        "word_count": total_word_count,
                        "status": "completed",
                    }).eq("id", str(script_id)).execute()
                except Exception:
                    pass

                yield {
                    "event": "done",
                    "data": json.dumps({
                        "script_id": str(script_id),
                        "word_count": total_word_count,
                        "hook_length": len(hook_text or ""),
                        "body_length": len(body_content or ""),
                        "closing_length": len(closing_text or ""),
                    }, ensure_ascii=False),
                }
            except Exception as e:
                try:
                    sb_err = get_supabase()
                    sb_err.table("scripts").update({"status": "error"}).eq(
                        "id", str(script_id)
                    ).execute()
                except Exception:
                    pass
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}, ensure_ascii=False),
                }

        return EventSourceResponse(event_generator_supabase())

    # SQLAlchemy path
    script = Script(
        project_id=project_id,
        keyword_id=body.keyword_id,
        title=body.title,
        status="generating",
        target_viewer=body.target_viewer,
        viewer_problem=body.viewer_problem,
        promise=body.promise,
        uniqueness=body.uniqueness,
        generation_model="claude-sonnet-4-20250514",
    )
    db.add(script)
    await db.flush()
    await db.refresh(script)
    script_id = script.id

    async def event_generator():
        """SSEイベントを生成するジェネレータ"""
        full_text: list[str] = []

        yield {
            "event": "start",
            "data": json.dumps({"script_id": str(script_id)}, ensure_ascii=False),
        }

        try:
            async for chunk in generate_script_stream(
                title=body.title,
                target_viewer=body.target_viewer,
                viewer_problem=body.viewer_problem,
                promise=body.promise,
                uniqueness=body.uniqueness,
                additional_context=body.additional_context,
                rag_context=rag_context,
            ):
                full_text.append(chunk)
                yield {
                    "event": "chunk",
                    "data": json.dumps({"text": chunk}, ensure_ascii=False),
                }

            full_body_text = "".join(full_text)
            hook_text, body_content, closing_text = _parse_script_json(full_body_text)
            total_word_count = len(hook_text or "") + len(body_content or "") + len(closing_text or "")

            async with async_session_factory() as save_session:
                try:
                    stmt = select(Script).where(Script.id == script_id)
                    result = await save_session.execute(stmt)
                    db_script = result.scalar_one_or_none()
                    if db_script:
                        db_script.hook = hook_text
                        db_script.body = body_content
                        db_script.closing = closing_text
                        db_script.word_count = total_word_count
                        db_script.status = "completed"
                        await save_session.commit()
                except Exception:
                    await save_session.rollback()

            yield {
                "event": "done",
                "data": json.dumps({
                    "script_id": str(script_id),
                    "word_count": total_word_count,
                    "hook_length": len(hook_text or ""),
                    "body_length": len(body_content or ""),
                    "closing_length": len(closing_text or ""),
                }, ensure_ascii=False),
            }

        except Exception as e:
            async with async_session_factory() as err_session:
                try:
                    stmt = select(Script).where(Script.id == script_id)
                    result = await err_session.execute(stmt)
                    db_script = result.scalar_one_or_none()
                    if db_script:
                        db_script.status = "error"
                        await err_session.commit()
                except Exception:
                    await err_session.rollback()

            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


def _parse_script_json(full_body_text: str):
    """生成テキストをJSON解析してhook/body/closingに分割する"""
    hook_text = None
    body_content = None
    closing_text = None

    try:
        json_start = full_body_text.find("{")
        json_end = full_body_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = full_body_text[json_start:json_end]
            parsed = json.loads(json_str)
            hook_text = parsed.get("hook", "")
            body_content = parsed.get("body", "")
            closing_text = parsed.get("closing", "")
        else:
            body_content = full_body_text
    except (json.JSONDecodeError, ValueError):
        body_content = full_body_text

    return hook_text, body_content, closing_text


@router.get("/{project_id}/{script_id}", response_model=ScriptResponse)
async def get_script(
    project_id: uuid.UUID,
    script_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """台本の詳細を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("scripts").select("*").eq(
            "id", str(script_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="台本が見つかりません")
        return result.data[0]

    stmt = select(Script).where(
        Script.id == script_id,
        Script.project_id == project_id,
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="台本が見つかりません")
    return script


@router.patch("/{project_id}/{script_id}", response_model=ScriptResponse)
async def update_script(
    project_id: uuid.UUID,
    script_id: uuid.UUID,
    body: ScriptUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """台本を更新する"""
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("scripts").select("*").eq(
            "id", str(script_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="台本が見つかりません")

        update_data = body.model_dump(exclude_unset=True)

        # body フィールドが更新された場合は文字数を自動計算
        if "body" in update_data and update_data["body"] and "word_count" not in update_data:
            update_data["word_count"] = len(update_data["body"])

        if not update_data:
            return existing.data[0]

        result = sb.table("scripts").update(update_data).eq(
            "id", str(script_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        return result.data[0]

    stmt = select(Script).where(
        Script.id == script_id,
        Script.project_id == project_id,
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="台本が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(script, key, value)

    if script.body and "word_count" not in update_data:
        script.word_count = len(script.body)

    await db.flush()
    await db.refresh(script)
    return script


@router.delete("/{project_id}/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    project_id: uuid.UUID,
    script_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """台本を削除する"""
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("scripts").select("id").eq(
            "id", str(script_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="台本が見つかりません")

        sb.table("scripts").delete().eq("id", str(script_id)).execute()
        return

    stmt = select(Script).where(
        Script.id == script_id,
        Script.project_id == project_id,
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="台本が見つかりません")

    await db.delete(script)
    await db.flush()
