"""
検索結果パーソナライズサービス。
ユーザープロファイルに基づいて動画検索結果をリランキングする。
"""

import json
import logging
from typing import Any

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


async def rerank_videos(
    videos: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    動画リストをユーザープロファイルに基づいてリランキングする。

    Args:
        videos: 動画データのリスト
        profile: ユーザープロファイル（genre, target_audience, strengths等）

    Returns:
        relevance_score と relevance_reason が付与された動画リスト
    """
    if not videos or not profile:
        return videos

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # 動画の要約リストを作成
    video_summaries = []
    for i, v in enumerate(videos[:30]):  # 最大30件
        video_summaries.append(
            f"{i}: 「{v.get('title', '')}」 ch:{v.get('channel_title', '')} "
            f"再生:{v.get('view_count', 0)} 伸び:{v.get('views_per_day', 0)}/日"
        )

    prompt = f"""以下のYouTube動画リストを、ユーザーのチャンネルプロファイルとの関連度でスコアリングしてください。

## ユーザープロファイル
- ジャンル: {profile.get('genre', '未設定')}
- ターゲット: {profile.get('target_audience', '未設定')}
- ベンチマーク: {', '.join(profile.get('benchmark_channels', [])[:5]) or '未設定'}
- 強み: {profile.get('strengths', '未設定')}
- スタイル: {profile.get('content_style', '未設定')}

## 動画リスト
{chr(10).join(video_summaries)}

## 出力
各動画について以下のJSON配列を返してください:
[{{"index": 0, "relevance_score": 8.5, "reason": "理由（30文字以内）"}}, ...]

relevance_score は 0-10 で、ユーザーのチャンネルにとって参考になる度合い。
JSON配列のみを返してください。"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        scores = json.loads(text.strip())
        score_map = {s["index"]: s for s in scores}

        # スコアを付与
        for i, v in enumerate(videos):
            if i in score_map:
                v["relevance_score"] = score_map[i].get("relevance_score", 5.0)
                v["relevance_reason"] = score_map[i].get("reason", "")
            else:
                v["relevance_score"] = 5.0
                v["relevance_reason"] = ""

        # スコア順にソート
        videos.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return videos

    except Exception as e:
        logger.error(f"パーソナライズエラー: {e}")
        # エラー時はそのまま返す
        for v in videos:
            v["relevance_score"] = None
            v["relevance_reason"] = ""
        return videos
