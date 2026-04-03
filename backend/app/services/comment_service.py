"""
コメント分析サービスモジュール。
動画コメントの取得・分析・感情分析を行う。
"""

import json
import uuid
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import VideoComment
from app.services.youtube_service import get_comments as yt_get_comments


async def fetch_and_store_comments(
    db: AsyncSession,
    video_id: uuid.UUID,
    youtube_video_id: str,
    max_results: int = 50,
) -> int:
    """
    YouTube APIからコメントを取得してDBに保存する。

    Args:
        db: データベースセッション
        video_id: DB上の動画ID (videos.id)
        youtube_video_id: YouTube動画ID (videos.youtube_video_id)
        max_results: 最大取得件数

    Returns:
        保存されたコメント数
    """
    raw_comments = await yt_get_comments(youtube_video_id, max_results)

    count = 0
    for raw in raw_comments:
        youtube_comment_id = raw.get("youtube_comment_id", "")
        if not youtube_comment_id:
            continue

        # 重複チェック（youtube_comment_id はUNIQUE制約）
        stmt = select(VideoComment).where(
            VideoComment.youtube_comment_id == youtube_comment_id
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        comment = VideoComment(
            video_id=video_id,
            youtube_comment_id=youtube_comment_id,
            author_name=raw.get("author_name"),
            text=raw.get("text", ""),
            like_count=raw.get("like_count", 0),
            published_at=raw.get("published_at"),
        )
        db.add(comment)
        count += 1

    await db.flush()
    return count


async def get_comments_by_video(
    db: AsyncSession,
    video_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[VideoComment]:
    """DB上の動画コメントを取得する"""
    stmt = (
        select(VideoComment)
        .where(VideoComment.video_id == video_id)
        .offset(skip)
        .limit(limit)
        .order_by(VideoComment.like_count.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def analyze_comment_sentiment(comments: list[dict[str, Any]]) -> dict[str, Any]:
    """
    コメントの簡易感情分析を行う（キーワードベース）。

    Args:
        comments: コメントリスト

    Returns:
        感情分析結果
    """
    positive_words = ["すごい", "最高", "面白い", "好き", "ありがとう", "わかりやすい", "神", "素晴らしい"]
    negative_words = ["つまらない", "嫌い", "微妙", "ひどい", "残念", "ダメ", "最悪", "がっかり"]

    total = len(comments)
    positive_count = 0
    negative_count = 0

    for comment in comments:
        text = comment.get("text", "")
        if any(word in text for word in positive_words):
            positive_count += 1
        if any(word in text for word in negative_words):
            negative_count += 1

    neutral_count = total - positive_count - negative_count

    return {
        "total": total,
        "positive": positive_count,
        "negative": negative_count,
        "neutral": max(0, neutral_count),
        "positive_ratio": round(positive_count / total, 3) if total > 0 else 0.0,
        "negative_ratio": round(negative_count / total, 3) if total > 0 else 0.0,
    }


async def analyze_comments_with_llm(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Claude APIでコメントのニーズ分析を行う。

    各コメントに対して以下を判定する:
    - need_category: ニーズカテゴリ
    - sentiment: 感情 (positive / negative / neutral)
    - is_question: 質問かどうか

    Args:
        comments: コメントリスト [{"id": "...", "text": "...", "like_count": N}, ...]

    Returns:
        分析結果リスト [{"id": "...", "need_category": "...", "sentiment": "...", "is_question": bool}, ...]
    """
    if not comments:
        return []

    # コメントを整形
    comments_text = "\n".join(
        f"[ID:{c['id']}] (いいね:{c.get('like_count', 0)}) {c['text'][:500]}"
        for c in comments
    )

    system_prompt = """あなたはYouTube動画のコメント分析エキスパートです。
与えられたコメントそれぞれについて、以下の3つを判定してください。

1. need_category（ニーズカテゴリ）: 以下のいずれかを選択
   - "ノウハウ詳細": 具体的なやり方・手順をもっと知りたい
   - "再現性への疑問": 本当にできるのか、自分にもできるのか疑問
   - "成功体験共有": 自分もやってみた、うまくいった
   - "モチベーション": やる気が出た、励まされた
   - "批判/否定": 内容への批判や否定的意見
   - "質問": 具体的な質問
   - "その他": 上記に該当しない

2. sentiment（感情）: "positive" / "negative" / "neutral" のいずれか

3. is_question（質問か）: true / false

必ず以下のJSON配列形式で出力してください。他のテキストは含めないでください。
[
  {"id": "コメントID", "need_category": "カテゴリ", "sentiment": "感情", "is_question": true/false},
  ...
]"""

    user_prompt = f"""以下のYouTubeコメントを分析してください。

{comments_text}"""

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )

    response_text = response.content[0].text.strip()

    # JSON部分を抽出してパース
    try:
        json_start = response_text.find("[")
        json_end = response_text.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            results = json.loads(response_text[json_start:json_end])
        else:
            results = json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        # パース失敗時は空リストを返す
        results = []

    # 型を整形して返す
    validated: list[dict[str, Any]] = []
    for r in results:
        if not isinstance(r, dict) or "id" not in r:
            continue
        validated.append({
            "id": r["id"],
            "need_category": r.get("need_category", "その他"),
            "sentiment": r.get("sentiment", "neutral"),
            "is_question": bool(r.get("is_question", False)),
        })

    return validated
