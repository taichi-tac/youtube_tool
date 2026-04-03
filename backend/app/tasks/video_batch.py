"""
動画バッチ処理タスク。
キーワードリストに基づいて動画を一括検索・保存する。
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Keyword, Video
from app.services.youtube_service import get_video_details, search_videos


async def batch_search_videos(
    db: AsyncSession,
    project_id: uuid.UUID,
    max_results_per_keyword: int = 5,
    max_keywords: int = 20,
) -> dict[str, Any]:
    """
    プロジェクトの保存済みキーワードで動画を一括検索する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        max_results_per_keyword: キーワードあたりの最大取得件数
        max_keywords: 処理する最大キーワード数

    Returns:
        処理結果のサマリー
    """
    # キーワード取得
    stmt = (
        select(Keyword)
        .where(Keyword.project_id == project_id)
        .limit(max_keywords)
        .order_by(Keyword.created_at.desc())
    )
    result = await db.execute(stmt)
    keywords = list(result.scalars().all())

    total_new = 0
    total_existing = 0
    errors: list[str] = []

    for kw in keywords:
        try:
            # YouTube検索
            search_results = await search_videos(
                query=kw.keyword,
                max_results=max_results_per_keyword,
            )

            if not search_results:
                continue

            # 詳細取得
            video_ids = [r["youtube_video_id"] for r in search_results]
            details = await get_video_details(video_ids)
            detail_map: dict[str, dict[str, Any]] = {
                d["youtube_video_id"]: d for d in details
            }

            for sr in search_results:
                yt_id = sr["youtube_video_id"]

                # 重複チェック
                exists_stmt = select(Video).where(Video.youtube_video_id == yt_id)
                existing = (await db.execute(exists_stmt)).scalar_one_or_none()
                if existing:
                    total_existing += 1
                    continue

                detail = detail_map.get(yt_id, {})

                video = Video(
                    project_id=project_id,
                    youtube_video_id=yt_id,
                    title=detail.get("title", sr.get("title", "")),
                    description=detail.get("description", sr.get("description")),
                    channel_title=detail.get("channel_title", sr.get("channel_title")),
                    channel_id=detail.get("channel_id", sr.get("channel_id")),
                    published_at=detail.get("published_at"),
                    view_count=detail.get("view_count"),
                    like_count=detail.get("like_count"),
                    comment_count=detail.get("comment_count"),
                    duration_seconds=detail.get("duration_seconds"),
                    thumbnail_url=detail.get("thumbnail_url", sr.get("thumbnail_url")),
                    keyword_id=kw.id,
                )
                db.add(video)
                total_new += 1

        except Exception as e:
            errors.append(f"キーワード '{kw.keyword}': {str(e)}")

    await db.flush()

    return {
        "keywords_processed": len(keywords),
        "new_videos": total_new,
        "existing_videos": total_existing,
        "errors": errors,
    }
