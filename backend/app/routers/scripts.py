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

from app.core.database import async_session_factory, get_db
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
) -> list[Script]:
    """プロジェクトの台本一覧を取得する"""
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
) -> Script:
    """台本レコードを手動作成する"""
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
    # RAGコンテキスト取得（オプション）
    rag_context = None
    if body.use_rag:
        rag_context = await get_rag_context(
            db=db,
            project_id=project_id,
            query=f"{body.title} {body.viewer_problem or ''}",
        )

    # 台本レコードを事前作成（ステータス: generating）
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

        # 開始イベント
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

            # 生成テキストをJSON解析してhook/body/closingに分割
            full_body_text = "".join(full_text)
            hook_text = None
            body_content = None
            closing_text = None

            try:
                # JSON形式 {"hook":"...","body":"...","closing":"..."} を解析
                # 先頭・末尾の余分なテキストを除去してJSON部分を抽出
                json_start = full_body_text.find("{")
                json_end = full_body_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = full_body_text[json_start:json_end]
                    parsed = json.loads(json_str)
                    hook_text = parsed.get("hook", "")
                    body_content = parsed.get("body", "")
                    closing_text = parsed.get("closing", "")
                else:
                    # JSON部分が見つからない場合はbodyに全文格納
                    body_content = full_body_text
            except (json.JSONDecodeError, ValueError):
                # JSONパース失敗時はbodyに全文を格納
                body_content = full_body_text

            # DB保存（event_generator内なので新しいセッションを使う）
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

            # 完了イベント
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
            # エラー時もステータスを更新
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


@router.get("/{project_id}/{script_id}", response_model=ScriptResponse)
async def get_script(
    project_id: uuid.UUID,
    script_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Script:
    """台本の詳細を取得する"""
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
) -> Script:
    """台本を更新する"""
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

    # body フィールドが更新された場合は文字数を自動計算
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
