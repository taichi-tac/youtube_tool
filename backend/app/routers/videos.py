"""
動画ルーター。
YouTube動画の検索・取得・管理を提供する。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_supabase, use_supabase_sdk
from app.core.quota_manager import quota_manager
from app.core.security import get_current_user
from app.models.models import Video, VideoComment
from app.schemas.schemas import (
    CommentAnalysisResponse,
    QuotaStatusResponse,
    VideoCommentResponse,
    VideoResponse,
    VideoSearchRequest,
)
from app.services.comment_service import (
    fetch_and_store_comments,
    get_comments_by_video,
)
from app.services.comment_service import analyze_comments_with_llm
from app.services.youtube_service import get_video_details, search_videos

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


@router.post("/{project_id}/search", response_model=list[VideoResponse])
async def search_and_save_videos(
    project_id: uuid.UUID,
    body: VideoSearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """YouTube動画を検索してDBに保存する"""
    # プロジェクトのカスタムAPIキーを取得
    user_api_key = None
    if use_supabase_sdk():
        sb = get_supabase()
        proj = sb.table("projects").select("youtube_api_key").eq("id", str(project_id)).execute()
        if proj.data and proj.data[0].get("youtube_api_key"):
            user_api_key = proj.data[0]["youtube_api_key"]

    # YouTube検索実行（最大50件）
    search_results = await search_videos(
        query=body.query,
        max_results=min(body.max_results, 50),
        order=body.order,
        api_key=user_api_key,
    )

    if not search_results:
        return []

    # 動画IDリストから詳細情報を取得
    video_ids = [r["youtube_video_id"] for r in search_results]
    details = await get_video_details(video_ids, api_key=user_api_key)
    detail_map: dict[str, dict[str, Any]] = {d["youtube_video_id"]: d for d in details}

    now = datetime.now(timezone.utc)

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

            if existing.data:
                video_data = existing.data[0]
                trending = _calc_trending_fields(
                    video_data.get("view_count"),
                    video_data.get("published_at"),
                    now,
                )
                sb.table("videos").update(trending).eq("id", video_data["id"]).execute()
                video_data.update(trending)
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
            }
            insert_result = sb.table("videos").insert(video_data).execute()
            saved_videos.append(insert_result.data[0])

        return saved_videos

    # SQLAlchemy path
    saved_videos: list[Video] = []
    for result in search_results:
        yt_id = result["youtube_video_id"]
        detail = detail_map.get(yt_id, {})

        # 既存チェック
        stmt = select(Video).where(Video.youtube_video_id == yt_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
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
        )
        _update_trending_fields(video, now)
        db.add(video)
        saved_videos.append(video)

    await db.flush()
    for v in saved_videos:
        await db.refresh(v)

    return saved_videos


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
