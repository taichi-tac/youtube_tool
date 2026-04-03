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

from app.core.database import get_db
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


@router.post("/{project_id}/search", response_model=list[VideoResponse])
async def search_and_save_videos(
    project_id: uuid.UUID,
    body: VideoSearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Video]:
    """YouTube動画を検索してDBに保存する"""
    # YouTube検索実行
    search_results = await search_videos(
        query=body.query,
        max_results=body.max_results,
        order=body.order,
    )

    if not search_results:
        return []

    # 動画IDリストから詳細情報を取得
    video_ids = [r["youtube_video_id"] for r in search_results]
    details = await get_video_details(video_ids)

    # 詳細情報をマップに変換
    detail_map: dict[str, dict[str, Any]] = {d["youtube_video_id"]: d for d in details}

    now = datetime.now(timezone.utc)
    saved_videos: list[Video] = []
    for result in search_results:
        yt_id = result["youtube_video_id"]
        detail = detail_map.get(yt_id, {})

        # 既存チェック
        stmt = select(Video).where(Video.youtube_video_id == yt_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            # 既存動画でもviews_per_day / is_trendingを再計算
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

        # views_per_day / is_trending を計算
        _update_trending_fields(video, now)

        db.add(video)
        saved_videos.append(video)

    await db.flush()
    # リフレッシュして全フィールド取得
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
) -> list[Video]:
    """プロジェクトの保存済み動画一覧を取得する"""
    stmt = select(Video).where(Video.project_id == project_id)

    # trending_only フィルタ
    if trending_only:
        stmt = stmt.where(Video.is_trending == True)  # noqa: E712

    # days フィルタ
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = stmt.where(Video.published_at >= cutoff)

    # ソート
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
) -> Video:
    """動画の詳細を取得する"""
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
) -> list[VideoComment]:
    """YouTube APIでコメントを取得してDB保存する"""
    # 動画の存在確認
    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    # コメント取得・保存
    saved_count = await fetch_and_store_comments(
        db=db,
        video_id=video_id,
        youtube_video_id=video.youtube_video_id,
        max_results=max_results,
    )

    # 保存済みコメントを返却
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
    # 動画の存在確認
    stmt = select(Video).where(
        Video.id == video_id,
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    # 全コメント取得
    comment_stmt = (
        select(VideoComment)
        .where(VideoComment.video_id == video_id)
        .order_by(VideoComment.like_count.desc())
    )
    comment_result = await db.execute(comment_stmt)
    comments = list(comment_result.scalars().all())

    if not comments:
        raise HTTPException(status_code=400, detail="分析対象のコメントがありません")

    # Claude APIで分析
    comment_dicts = [
        {"id": str(c.id), "text": c.text, "like_count": c.like_count}
        for c in comments
    ]
    analysis_results = await analyze_comments_with_llm(comment_dicts)

    # 結果をDBに反映
    analysis_map = {r["id"]: r for r in analysis_results}
    for comment in comments:
        analysis = analysis_map.get(str(comment.id))
        if analysis:
            comment.need_category = analysis.get("need_category")
            comment.sentiment = analysis.get("sentiment")
            comment.is_question = analysis.get("is_question", False)

    await db.flush()

    # ニーズカテゴリ別ランキングを集計
    category_data: dict[str, dict[str, Any]] = {}
    sentiment_counts: dict[str, int] = {}
    question_count = 0

    for comment in comments:
        cat = comment.need_category or "その他"
        if cat not in category_data:
            category_data[cat] = {"count": 0, "representative_comments": []}
        category_data[cat]["count"] += 1
        # 代表コメントは最大3件
        if len(category_data[cat]["representative_comments"]) < 3:
            category_data[cat]["representative_comments"].append(comment.text[:200])

        sent = comment.sentiment or "neutral"
        sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

        if comment.is_question:
            question_count += 1

    # カテゴリを件数降順でソート
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
