"""
動画ルーター。
YouTube動画の検索・取得・管理を提供する。
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db, get_supabase, use_supabase_sdk
from app.core.quota_manager import quota_manager
from app.core.security import get_current_user
from app.models.models import Video, VideoComment
from app.schemas.schemas import (
    CommentAnalysisResponse,
    QuotaStatusResponse,
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    VideoCommentResponse,
    VideoResponse,
    VideoSearchRequest,
    VideoUrlRequest,
)
from app.services.comment_service import (
    fetch_and_store_comments,
    get_comments_by_video,
)
from app.services.comment_service import analyze_comments_with_llm
from app.services.youtube_service import (
    get_channel_details,
    get_video_details,
    search_videos,
)

router = APIRouter(prefix="/videos", tags=["動画"])


@router.get("/quota", response_model=QuotaStatusResponse)
async def get_quota_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """YouTube APIクォータ使用状況を取得する"""
    return quota_manager.get_status()


def _calc_trending_fields(view_count, published_at, now) -> dict[str, Any]:
    """views_per_day と is_trending を計算する（Supabase SDK用）"""
    if published_at and view_count is not None:
        if isinstance(published_at, str):
            # ISO 8601文字列をdatetimeに変換
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        days_since = (now - published_at).days
        views_per_day = round(view_count / max(1, days_since), 2)
        is_recent = days_since <= 180
        is_trending = is_recent and views_per_day > 100
        return {"views_per_day": views_per_day, "is_trending": is_trending}
    return {"views_per_day": None, "is_trending": False}


def _calc_viral_metrics(
    detail: dict[str, Any],
    channel_info: dict[str, Any] | None,
) -> dict[str, Any]:
    """拡散率・登録率・各エンゲージメント率を計算する"""
    view_count = detail.get("view_count") or 0
    like_count = detail.get("like_count") or 0
    comment_count = detail.get("comment_count") or 0
    subscriber_count = (channel_info or {}).get("subscriber_count") or 0
    channel_total = (channel_info or {}).get("channel_total_view_count") or 0
    total_videos = (channel_info or {}).get("total_video_count") or 0

    views_to_subs_ratio = (view_count / subscriber_count) if subscriber_count > 0 else 0.0
    subscriber_rate = (subscriber_count / channel_total) if channel_total > 0 else 0.0
    like_rate = (like_count / view_count) if view_count > 0 else 0.0
    comment_rate = (comment_count / view_count) if view_count > 0 else 0.0
    engagement_rate = ((like_count + comment_count) / view_count) if view_count > 0 else 0.0

    return {
        "subscriber_count": subscriber_count or None,
        "channel_total_view_count": channel_total or None,
        "total_video_count": total_videos or None,
        "views_to_subs_ratio": round(views_to_subs_ratio, 2),
        "subscriber_rate": round(subscriber_rate, 6),
        "like_rate": round(like_rate, 6),
        "comment_rate": round(comment_rate, 6),
        "engagement_rate": round(engagement_rate, 6),
    }


@router.post("/{project_id}/search")
async def search_and_save_videos(
    project_id: uuid.UUID,
    body: VideoSearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """YouTube動画を検索してDBに保存する（SSE 配信）。

    YouTube API + Supabase への逐次書き込み(≈15件×2query)で 20-40 秒かかり、
    Cloudflare/Render のアイドルタイムアウトで CORS ヘッダごと落ちてしまう
    ケースを、SSE の keep-alive (ping=15秒 + 8秒毎の progress) で回避する。
    """
    async def _do_work() -> list[dict[str, Any]]:
        return await _search_and_save_impl(project_id, body, user, db)

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"pct": 5}, ensure_ascii=False)}
        task = asyncio.create_task(_do_work())
        _progress_steps = [15, 30, 45, 60, 75, 85, 92, 96]
        _step_idx = 0
        # asyncio.wait は task の例外を再送出しないので、後段で task.exception() が拾える
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


async def _search_and_save_impl(
    project_id: uuid.UUID,
    body: VideoSearchRequest,
    user: dict[str, Any],
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """search_and_save_videos の実処理本体。SSE ラッパから呼ばれる。"""
    # プロジェクトのカスタムAPIキーを取得
    user_api_key = None
    if use_supabase_sdk():
        sb = get_supabase()
        proj = sb.table("projects").select("youtube_api_key").eq("id", str(project_id)).execute()
        if proj.data and proj.data[0].get("youtube_api_key"):
            user_api_key = proj.data[0]["youtube_api_key"]

    # viral mode かどうかでデフォルト並び順を変える
    effective_order = body.order
    if body.viral_mode and effective_order == "relevance":
        # Miyabi 仕様: viral では relevance で検索し、後段で急上昇率順にソート
        effective_order = "relevance"

    # YouTube検索実行（最大50件）
    search_results = await search_videos(
        query=body.query,
        max_results=min(body.max_results, 50),
        order=effective_order,
        api_key=user_api_key,
        published_after=body.published_after,
        published_before=body.published_before,
        video_duration=body.video_duration,
    )

    if not search_results:
        return []

    # 動画IDリストから詳細情報を取得
    video_ids = [r["youtube_video_id"] for r in search_results]
    details = await get_video_details(video_ids, api_key=user_api_key)
    detail_map: dict[str, dict[str, Any]] = {d["youtube_video_id"]: d for d in details}

    # viral mode のときのみ channel 情報を取得（クォータ節約）
    channel_map: dict[str, dict[str, Any]] = {}
    if body.viral_mode:
        channel_ids = [d.get("channel_id") for d in details if d.get("channel_id")]
        channel_map = await get_channel_details(channel_ids, api_key=user_api_key)

    now = datetime.now(timezone.utc)

    def _build_viral_payload(detail: dict[str, Any]) -> dict[str, Any]:
        """viral mode 用に拡散率・登録率等とハッシュタグを返す"""
        if not body.viral_mode:
            return {}
        ch_info = channel_map.get(detail.get("channel_id") or "")
        payload = _calc_viral_metrics(detail, ch_info)
        payload["hashtags"] = detail.get("hashtags") or []
        return payload

    def _passes_viral_filter(detail: dict[str, Any], metrics: dict[str, Any]) -> bool:
        """viral 表示用フィルタ。Miyabi互換: threshold は絞り込みに使わない。
        ゲームカテゴリのみ除外する。"""
        if not body.viral_mode:
            return True
        if detail.get("category_id") == "20":  # ゲームカテゴリ除外
            return False
        return True

    if use_supabase_sdk():
        sb = get_supabase()
        saved_videos = []

        for result in search_results:
            yt_id = result["youtube_video_id"]
            detail = detail_map.get(yt_id, {})

            # 既存チェック
            existing = sb.table("videos").select("*").eq(
                "youtube_video_id", yt_id
            ).execute()

            viral_payload = _build_viral_payload(detail)
            if not _passes_viral_filter(detail, viral_payload):
                continue

            if existing.data:
                video_data = existing.data[0]
                refreshed: dict[str, Any] = {}
                if "view_count" in detail:
                    refreshed["view_count"] = detail["view_count"]
                if "like_count" in detail:
                    refreshed["like_count"] = detail["like_count"]
                if "comment_count" in detail:
                    refreshed["comment_count"] = detail["comment_count"]
                effective_view_count = refreshed.get("view_count", video_data.get("view_count"))
                trending = _calc_trending_fields(
                    effective_view_count,
                    video_data.get("published_at"),
                    now,
                )
                update_payload = {**refreshed, **trending, **viral_payload}
                sb.table("videos").update(update_payload).eq("id", video_data["id"]).execute()
                video_data.update(update_payload)
                saved_videos.append(video_data)
                continue

            published_at = detail.get("published_at", result.get("published_at"))
            view_count = detail.get("view_count")
            trending = _calc_trending_fields(view_count, published_at, now)

            video_data = {
                "project_id": str(project_id),
                "youtube_video_id": yt_id,
                "title": detail.get("title", result.get("title", "")),
                "description": detail.get("description", result.get("description")),
                "channel_title": detail.get("channel_title", result.get("channel_title")),
                "channel_id": detail.get("channel_id", result.get("channel_id")),
                "published_at": published_at.isoformat() if isinstance(published_at, datetime) else published_at,
                "view_count": view_count,
                "like_count": detail.get("like_count"),
                "comment_count": detail.get("comment_count"),
                "duration_seconds": detail.get("duration_seconds"),
                "thumbnail_url": detail.get("thumbnail_url", result.get("thumbnail_url")),
                "keyword_id": str(body.keyword_id) if body.keyword_id else None,
                "views_per_day": trending["views_per_day"],
                "is_trending": trending["is_trending"],
                **viral_payload,
            }
            insert_result = sb.table("videos").insert(video_data).execute()
            saved_videos.append(insert_result.data[0])

        # viral mode は急上昇率(views_per_day)降順に並べ替え
        if body.viral_mode:
            saved_videos.sort(
                key=lambda v: float(v.get("views_per_day") or 0),
                reverse=True,
            )
        return saved_videos

    # SQLAlchemy path
    saved_videos: list[Video] = []
    for result in search_results:
        yt_id = result["youtube_video_id"]
        detail = detail_map.get(yt_id, {})

        viral_payload = _build_viral_payload(detail)
        if not _passes_viral_filter(detail, viral_payload):
            continue

        # 既存チェック
        stmt = select(Video).where(Video.youtube_video_id == yt_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            if "view_count" in detail:
                existing.view_count = detail["view_count"]
            if "like_count" in detail:
                existing.like_count = detail["like_count"]
            if "comment_count" in detail:
                existing.comment_count = detail["comment_count"]
            for k, v in viral_payload.items():
                setattr(existing, k, v)
            _update_trending_fields(existing, now)
            saved_videos.append(existing)
            continue

        published_at = detail.get("published_at", result.get("published_at"))
        view_count = detail.get("view_count")

        video = Video(
            project_id=project_id,
            youtube_video_id=yt_id,
            title=detail.get("title", result.get("title", "")),
            description=detail.get("description", result.get("description")),
            channel_title=detail.get("channel_title", result.get("channel_title")),
            channel_id=detail.get("channel_id", result.get("channel_id")),
            published_at=published_at,
            view_count=view_count,
            like_count=detail.get("like_count"),
            comment_count=detail.get("comment_count"),
            duration_seconds=detail.get("duration_seconds"),
            thumbnail_url=detail.get("thumbnail_url", result.get("thumbnail_url")),
            keyword_id=body.keyword_id,
            **viral_payload,
        )
        _update_trending_fields(video, now)
        db.add(video)
        saved_videos.append(video)

    await db.flush()
    for v in saved_videos:
        await db.refresh(v)

    if body.viral_mode:
        saved_videos.sort(
            key=lambda v: float(v.views_per_day or 0),
            reverse=True,
        )
    return [_video_to_dict(v) for v in saved_videos]


def _video_to_dict(v: Any) -> dict[str, Any]:
    """SQLAlchemy Video → dict 変換（SSE JSON 化用）"""
    if isinstance(v, dict):
        return v
    result: dict[str, Any] = {}
    for col in v.__table__.columns:
        val = getattr(v, col.name, None)
        if isinstance(val, (datetime, uuid.UUID)):
            val = str(val)
        result[col.name] = val
    return result


def _extract_youtube_video_id(url: str) -> Optional[str]:
    """YouTube URLから動画IDを抽出する"""
    import re
    patterns = [
        r"(?:youtube\.com/watch\?(?:.*&)?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@router.post("/{project_id}/add-by-url", response_model=VideoResponse)
async def add_video_by_url(
    project_id: uuid.UUID,
    body: VideoUrlRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """YouTube URLを指定して動画を追加する"""
    yt_id = _extract_youtube_video_id(body.url)
    if not yt_id:
        raise HTTPException(status_code=400, detail="有効なYouTube URLではありません")

    user_api_key = None
    if use_supabase_sdk():
        sb = get_supabase()
        proj = sb.table("projects").select("youtube_api_key").eq("id", str(project_id)).execute()
        if proj.data and proj.data[0].get("youtube_api_key"):
            user_api_key = proj.data[0]["youtube_api_key"]

    now = datetime.now(timezone.utc)

    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("videos").select("*").eq("youtube_video_id", yt_id).execute()
        if existing.data:
            return existing.data[0]

        details = await get_video_details([yt_id], api_key=user_api_key)
        if not details:
            raise HTTPException(status_code=404, detail="動画が見つかりません")
        detail = details[0]

        published_at = detail.get("published_at")
        view_count = detail.get("view_count")
        trending = _calc_trending_fields(view_count, published_at, now)

        video_data = {
            "project_id": str(project_id),
            "youtube_video_id": yt_id,
            "title": detail.get("title", ""),
            "description": detail.get("description"),
            "channel_title": detail.get("channel_title"),
            "channel_id": detail.get("channel_id"),
            "published_at": published_at.isoformat() if isinstance(published_at, datetime) else published_at,
            "view_count": view_count,
            "like_count": detail.get("like_count"),
            "comment_count": detail.get("comment_count"),
            "duration_seconds": detail.get("duration_seconds"),
            "thumbnail_url": detail.get("thumbnail_url"),
            "views_per_day": trending["views_per_day"],
            "is_trending": trending["is_trending"],
        }
        insert_result = sb.table("videos").insert(video_data).execute()
        return insert_result.data[0]

    # SQLAlchemy path
    stmt = select(Video).where(Video.youtube_video_id == yt_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    details = await get_video_details([yt_id], api_key=user_api_key)
    if not details:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    detail = details[0]

    video = Video(
        project_id=project_id,
        youtube_video_id=yt_id,
        title=detail.get("title", ""),
        description=detail.get("description"),
        channel_title=detail.get("channel_title"),
        channel_id=detail.get("channel_id"),
        published_at=detail.get("published_at"),
        view_count=detail.get("view_count"),
        like_count=detail.get("like_count"),
        comment_count=detail.get("comment_count"),
        duration_seconds=detail.get("duration_seconds"),
        thumbnail_url=detail.get("thumbnail_url"),
    )
    _update_trending_fields(video, now)
    db.add(video)
    await db.flush()
    await db.refresh(video)
    return video


def _update_trending_fields(video: Video, now: datetime) -> None:
    """views_per_day と is_trending を計算・更新する"""
    if video.published_at and video.view_count is not None:
        days_since = (now - video.published_at).days
        video.views_per_day = round(video.view_count / max(1, days_since), 2)
        is_recent = days_since <= 180
        video.is_trending = is_recent and (video.views_per_day or 0) > 100
    else:
        video.views_per_day = None
        video.is_trending = False


@router.get("/{project_id}", response_model=list[VideoResponse])
async def list_videos(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = Query("views_per_day", description="ソート項目: views_per_day | view_count | published_at"),
    trending_only: bool = Query(False, description="is_trending=Trueのみフィルタ"),
    days: int = Query(180, ge=1, description="指定日数以内に公開された動画のみ"),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """プロジェクトの保存済み動画一覧を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = sb.table("videos").select("*").eq(
            "project_id", str(project_id)
        ).gte("published_at", cutoff)

        if trending_only:
            query = query.eq("is_trending", True)

        # ソート
        desc = True
        if sort_by in ("views_per_day", "view_count", "published_at"):
            query = query.order(sort_by, desc=desc, nullsfirst=False)
        else:
            query = query.order("views_per_day", desc=True, nullsfirst=False)

        result = query.range(skip, skip + limit - 1).execute()
        return result.data

    stmt = select(Video).where(Video.project_id == project_id)

    if trending_only:
        stmt = stmt.where(Video.is_trending == True)  # noqa: E712

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = stmt.where(Video.published_at >= cutoff)

    sort_column_map = {
        "views_per_day": Video.views_per_day.desc().nulls_last(),
        "view_count": Video.view_count.desc().nulls_last(),
        "published_at": Video.published_at.desc().nulls_last(),
    }
    order_clause = sort_column_map.get(sort_by, Video.views_per_day.desc().nulls_last())
    stmt = stmt.order_by(order_clause).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{project_id}/{video_id}", response_model=VideoResponse)
async def get_video(
    project_id: uuid.UUID,
    video_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """動画の詳細を取得する"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("videos").select("*").eq(
            "id", str(video_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="動画が見つかりません")
        return result.data[0]

    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return video


@router.delete("/{project_id}/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    project_id: uuid.UUID,
    video_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """動画を削除する"""
    if use_supabase_sdk():
        sb = get_supabase()
        existing = sb.table("videos").select("id").eq(
            "id", str(video_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="動画が見つかりません")

        sb.table("videos").delete().eq("id", str(video_id)).execute()
        return

    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    await db.delete(video)
    await db.flush()


# ============================================================
# コメント取得・分析
# ============================================================


@router.post(
    "/{project_id}/{video_id}/comments",
    response_model=list[VideoCommentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def fetch_comments(
    project_id: uuid.UUID,
    video_id: uuid.UUID,
    max_results: int = Query(50, ge=1, le=100, description="最大取得件数"),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """YouTube APIでコメントを取得してDB保存する"""
    if use_supabase_sdk():
        sb = get_supabase()
        # 動画の存在確認
        video_result = sb.table("videos").select("youtube_video_id").eq(
            "id", str(video_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not video_result.data:
            raise HTTPException(status_code=404, detail="動画が見つかりません")

        youtube_video_id = video_result.data[0]["youtube_video_id"]

        # YouTube APIからコメント取得
        from app.services.youtube_service import get_comments as yt_get_comments
        raw_comments = await yt_get_comments(youtube_video_id, max_results)

        for raw in raw_comments:
            youtube_comment_id = raw.get("youtube_comment_id", "")
            if not youtube_comment_id:
                continue

            # 重複チェック
            dup = sb.table("video_comments").select("id").eq(
                "youtube_comment_id", youtube_comment_id
            ).execute()
            if dup.data:
                continue

            comment_data = {
                "video_id": str(video_id),
                "youtube_comment_id": youtube_comment_id,
                "author_name": raw.get("author_name"),
                "text": raw.get("text", ""),
                "like_count": raw.get("like_count", 0),
                "published_at": raw.get("published_at").isoformat() if isinstance(raw.get("published_at"), datetime) else raw.get("published_at"),
            }
            sb.table("video_comments").insert(comment_data).execute()

        # 保存済みコメントを返却
        comments_result = sb.table("video_comments").select("*").eq(
            "video_id", str(video_id)
        ).order(
            "like_count", desc=True
        ).limit(max_results).execute()
        return comments_result.data

    # SQLAlchemy path
    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    saved_count = await fetch_and_store_comments(
        db=db,
        video_id=video_id,
        youtube_video_id=video.youtube_video_id,
        max_results=max_results,
    )
    comments = await get_comments_by_video(db=db, video_id=video_id, limit=max_results)
    return comments


@router.post(
    "/{project_id}/{video_id}/analyze-comments",
    response_model=CommentAnalysisResponse,
)
async def analyze_comments(
    project_id: uuid.UUID,
    video_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentAnalysisResponse:
    """保存済みコメントをClaude APIでニーズ分析する"""
    if use_supabase_sdk():
        sb = get_supabase()
        # 動画の存在確認
        video_result = sb.table("videos").select("id").eq(
            "id", str(video_id)
        ).eq(
            "project_id", str(project_id)
        ).execute()
        if not video_result.data:
            raise HTTPException(status_code=404, detail="動画が見つかりません")

        # 全コメント取得
        comments_result = sb.table("video_comments").select("*").eq(
            "video_id", str(video_id)
        ).order("like_count", desc=True).execute()
        comments = comments_result.data

        if not comments:
            raise HTTPException(status_code=400, detail="分析対象のコメントがありません")

        # Claude APIで分析
        comment_dicts = [
            {"id": c["id"], "text": c["text"], "like_count": c.get("like_count", 0)}
            for c in comments
        ]
        analysis_results = await analyze_comments_with_llm(comment_dicts)

        # 結果をDBに反映
        analysis_map = {r["id"]: r for r in analysis_results}
        for comment in comments:
            analysis = analysis_map.get(comment["id"])
            if analysis:
                sb.table("video_comments").update({
                    "need_category": analysis.get("need_category"),
                    "sentiment": analysis.get("sentiment"),
                    "is_question": analysis.get("is_question", False),
                }).eq("id", comment["id"]).execute()
                comment.update(analysis)

        # 集計
        return _build_comment_analysis_response(video_id, comments, analysis_results)

    # SQLAlchemy path
    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    comment_stmt = (
        select(VideoComment)
        .where(VideoComment.video_id == video_id)
        .order_by(VideoComment.like_count.desc())
    )
    comment_result = await db.execute(comment_stmt)
    comments = list(comment_result.scalars().all())

    if not comments:
        raise HTTPException(status_code=400, detail="分析対象のコメントがありません")

    comment_dicts = [
        {"id": str(c.id), "text": c.text, "like_count": c.like_count}
        for c in comments
    ]
    analysis_results = await analyze_comments_with_llm(comment_dicts)

    analysis_map = {r["id"]: r for r in analysis_results}
    for comment in comments:
        analysis = analysis_map.get(str(comment.id))
        if analysis:
            comment.need_category = analysis.get("need_category")
            comment.sentiment = analysis.get("sentiment")
            comment.is_question = analysis.get("is_question", False)

    await db.flush()

    # ニーズカテゴリ別ランキングを集計（ORM版）
    comments_as_dicts = [
        {
            "need_category": c.need_category,
            "sentiment": c.sentiment,
            "is_question": c.is_question,
            "text": c.text,
        }
        for c in comments
    ]
    return _build_comment_analysis_response(video_id, comments_as_dicts, analysis_results)


def _build_comment_analysis_response(
    video_id: uuid.UUID,
    comments: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
) -> CommentAnalysisResponse:
    """コメント分析結果を集計してレスポンスを構築する"""
    category_data: dict[str, dict[str, Any]] = {}
    sentiment_counts: dict[str, int] = {}
    question_count = 0

    for comment in comments:
        cat = comment.get("need_category") or "その他"
        if cat not in category_data:
            category_data[cat] = {"count": 0, "representative_comments": []}
        category_data[cat]["count"] += 1
        if len(category_data[cat]["representative_comments"]) < 3:
            text = comment.get("text", "")
            category_data[cat]["representative_comments"].append(text[:200])

        sent = comment.get("sentiment") or "neutral"
        sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

        if comment.get("is_question"):
            question_count += 1

    sorted_categories = sorted(category_data.items(), key=lambda x: x[1]["count"], reverse=True)

    from app.schemas.schemas import NeedCategory
    need_categories = [
        NeedCategory(
            category=cat,
            count=data["count"],
            representative_comments=data["representative_comments"],
        )
        for cat, data in sorted_categories
    ]

    return CommentAnalysisResponse(
        video_id=video_id,
        total_comments=len(comments),
        analyzed_count=len(analysis_results),
        need_categories=need_categories,
        sentiment_summary=sentiment_counts,
        question_count=question_count,
    )


# ============================================================
# 動画傾向分析（Miyabi viral analyze 移植・ルールベース）
# ============================================================

def _parse_duration_to_seconds(duration: Any) -> int:
    """'1:30:45' / '4:20' / 数値 を秒数に変換"""
    if duration is None:
        return 0
    if isinstance(duration, (int, float)):
        return int(duration)
    s = str(duration)
    if ":" not in s:
        try:
            return int(float(s))
        except ValueError:
            return 0
    parts = [int(p) for p in s.split(":") if p.isdigit()]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


@router.post("/{project_id}/analyze", response_model=VideoAnalyzeResponse)
async def analyze_selected_videos(
    project_id: uuid.UUID,
    body: VideoAnalyzeRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """選択した動画の数値傾向・共通キーワード・企画案を返す（ルールベース）"""
    import re as _re
    import statistics as _stats

    videos = body.videos or []
    if len(videos) < 2:
        raise HTTPException(status_code=400, detail="2本以上の動画を選択してください")

    def _f(v: Any, default: float = 0.0) -> float:
        try:
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    view_counts = [_f(v.get("view_count") or v.get("viewCount")) for v in videos]
    views_per_days = [_f(v.get("views_per_day") or v.get("viewsPerDay")) for v in videos]
    like_rates = [_f(v.get("like_rate") or v.get("likeRate")) for v in videos]
    engagement_rates = [_f(v.get("engagement_rate") or v.get("engagementRate")) for v in videos]
    subscriber_counts = [_f(v.get("subscriber_count") or v.get("subscriberCount")) for v in videos]
    durations = [
        _parse_duration_to_seconds(v.get("duration_seconds") or v.get("duration"))
        for v in videos
    ]

    avg_duration = sum(durations) / len(durations) if durations else 0
    if avg_duration < 240:
        duration_trend = "ショート（4分未満）"
    elif avg_duration < 600:
        duration_trend = "短め（4〜10分）"
    elif avg_duration < 1200:
        duration_trend = "中尺（10〜20分）"
    else:
        duration_trend = "長尺（20分以上）"

    avg_subs = sum(subscriber_counts) / len(subscriber_counts) if subscriber_counts else 0
    if avg_subs < 10000:
        channel_size = "小規模（1万未満）"
    elif avg_subs < 100000:
        channel_size = "中規模（1〜10万）"
    elif avg_subs < 1000000:
        channel_size = "大規模（10〜100万）"
    else:
        channel_size = "超大規模（100万以上）"

    # タイトル共通キーワード
    title_words: dict[str, int] = {}
    for v in videos:
        title = str(v.get("title") or "")
        title = _re.sub(r"[【】「」『』()（）\[\]]", " ", title)
        for w in _re.split(r"[\s　・、。!！?？]+", title):
            if len(w) >= 2:
                title_words[w] = title_words.get(w, 0) + 1
    threshold_count = max(2, -(-len(videos) * 4 // 10))  # ceil(len*0.4)
    common_words = [
        w for w, c in sorted(title_words.items(), key=lambda x: -x[1])
        if c >= threshold_count
    ][:8]

    # ハッシュタグ
    hashtag_counts: dict[str, int] = {}
    for v in videos:
        tags = v.get("hashtags") or []
        if isinstance(tags, list):
            for tag in tags:
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
    common_hashtags = [
        t for t, c in sorted(hashtag_counts.items(), key=lambda x: -x[1]) if c >= 2
    ][:5]

    avg_views = sum(view_counts) / len(view_counts) if view_counts else 0
    median_vpd = _stats.median(views_per_days) if views_per_days else 0
    avg_like_rate = sum(like_rates) / len(like_rates) if like_rates else 0
    avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

    kw = "・".join(common_words[:3]) if common_words else "検索キーワード"
    plans = [
        f"【数字訴求】「{kw}で{max(1, round(avg_views / 1000))}倍の結果を出す○○の方法」",
        f"【入門系】「{kw}完全ガイド｜初心者でも{'5分で' if avg_duration < 600 else ''}わかる基礎から実践まで」",
        f"【比較系】「{kw}を徹底比較！プロが選ぶTOP{len(videos)}選【2026年版】」",
        f"【失敗談】「{kw}で失敗した○○の話〜やってはいけないこと全部教えます」",
        f"【結果系】「{kw}を1ヶ月続けた結果がヤバすぎた」",
    ]

    return VideoAnalyzeResponse(
        summary={
            "count": len(videos),
            "avg_views": round(avg_views),
            "median_views_per_day": round(median_vpd),
            "avg_like_rate": round(avg_like_rate * 100, 2),
            "avg_engagement": round(avg_engagement * 100, 2),
            "duration_trend": duration_trend,
            "channel_size": channel_size,
        },
        common_words=common_words,
        common_hashtags=common_hashtags,
        plans=plans,
    )
