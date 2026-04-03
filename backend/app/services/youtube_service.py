"""
YouTube Data API v3 サービスモジュール。
google-api-python-clientを使用して動画検索・詳細取得・コメント取得を行う。
"""

import re
from datetime import datetime
from typing import Any, Optional

from googleapiclient.discovery import build

from app.core.config import settings
from app.core.quota_manager import quota_manager


def _get_youtube_client() -> Any:
    """YouTube Data API v3クライアントを生成する"""
    return build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)


def _iso8601_duration_to_seconds(duration: Optional[str]) -> Optional[int]:
    """
    ISO 8601 duration文字列（例: PT1H2M3S）を秒数に変換する。

    Args:
        duration: ISO 8601 duration文字列

    Returns:
        秒数。Noneまたはパース不能な場合はNone。
    """
    if not duration:
        return None
    pattern = re.compile(
        r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
    )
    match = pattern.fullmatch(duration)
    if not match:
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


async def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    region_code: str = "JP",
) -> list[dict[str, Any]]:
    """
    YouTube動画を検索する。

    Args:
        query: 検索クエリ
        max_results: 最大取得件数
        order: 並び順（relevance, date, viewCount, rating）
        region_code: リージョンコード

    Returns:
        検索結果のリスト
    """
    # クォータチェック
    if not await quota_manager.consume("search.list"):
        raise RuntimeError("YouTube APIの1日あたりのクォータ上限に達しました")

    youtube = _get_youtube_client()
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results,
        order=order,
        regionCode=region_code,
    )
    response: dict[str, Any] = request.execute()

    results: list[dict[str, Any]] = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        results.append({
            "youtube_video_id": item["id"]["videoId"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if snippet.get("publishedAt") else None,
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        })

    return results


async def get_video_details(video_ids: list[str]) -> list[dict[str, Any]]:
    """
    動画IDリストから詳細情報（統計・コンテンツ詳細）を取得する。

    Args:
        video_ids: YouTube動画IDのリスト

    Returns:
        動画詳細情報のリスト
    """
    if not video_ids:
        return []

    # クォータ消費（videos.listは1ユニット/リクエスト）
    if not await quota_manager.consume("videos.list"):
        raise RuntimeError("YouTube APIの1日あたりのクォータ上限に達しました")

    youtube = _get_youtube_client()
    request = youtube.videos().list(
        id=",".join(video_ids),
        part="snippet,statistics,contentDetails",
    )
    response: dict[str, Any] = request.execute()

    results: list[dict[str, Any]] = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        results.append({
            "youtube_video_id": item["id"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if snippet.get("publishedAt") else None,
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "duration_seconds": _iso8601_duration_to_seconds(content.get("duration")),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        })

    return results


async def get_comments(
    video_id: str,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    動画のコメントスレッドを取得する。

    Args:
        video_id: YouTube動画ID
        max_results: 最大取得件数

    Returns:
        コメントのリスト
    """
    if not await quota_manager.consume("commentThreads.list"):
        raise RuntimeError("YouTube APIの1日あたりのクォータ上限に達しました")

    youtube = _get_youtube_client()
    request = youtube.commentThreads().list(
        videoId=video_id,
        part="snippet",
        maxResults=max_results,
        order="relevance",
        textFormat="plainText",
    )
    response: dict[str, Any] = request.execute()

    comments: list[dict[str, Any]] = []
    for item in response.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "youtube_comment_id": item["id"],
            "author_name": top.get("authorDisplayName", ""),
            "text": top.get("textDisplay", ""),
            "like_count": top.get("likeCount", 0),
            "published_at": top.get("publishedAt"),
        })

    return comments
