"""
AI企画提案サービス。
ユーザーのプロファイルとYouTubeサジェストを組み合わせて企画を自動生成する。
"""

import json
import logging
from typing import Any, Optional

import anthropic

from app.core.config import settings
from app.services.keyword_service import extract_suggestions

logger = logging.getLogger(__name__)


async def generate_project_ideas(
    genre: str,
    target_audience: str = "",
    benchmark_channels: list[str] | None = None,
    strengths: str = "",
    content_style: str = "",
    count: int = 10,
    exclude_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    ユーザーのプロファイルに基づいて企画候補を生成する。

    1. ジャンルからYouTube Suggestでキーワードを大量取得
    2. Claude APIで企画候補をランキング付きで生成
    """
    # キーワード収集
    suggestions = await extract_suggestions(genre)
    # ジャンルの派生キーワードでも追加取得
    extra_seeds = [f"{genre} やり方", f"{genre} 初心者", f"{genre} コツ", f"{genre} おすすめ"]
    for seed in extra_seeds:
        try:
            more = await extract_suggestions(seed)
            suggestions.extend(more)
        except Exception:
            pass

    # 重複除去
    suggestions = list(set(suggestions))
    if exclude_keywords:
        suggestions = [s for s in suggestions if s not in exclude_keywords]

    logger.info(f"収集キーワード数: {len(suggestions)}")

    # Claude APIで企画生成
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = """あなたはYouTube企画のプロフェッショナルです。
与えられたキーワードリストとユーザープロファイルから、伸びる可能性の高い企画を提案してください。

各企画には以下を含めてください：
- title: 動画タイトル案（具体的で興味を引くもの）
- target_viewer: この動画のターゲット視聴者
- keyword: 狙うキーワード
- reason: なぜこの企画が伸びるか（100文字以内）
- demand_score: 需要スコア（1-10、検索ボリュームや関心度）
- niche_score: 穴場度スコア（1-10、競合が少ないほど高い）

JSON配列で返してください。"""

    user_prompt = f"""## ユーザープロファイル
- ジャンル: {genre}
- ターゲット: {target_audience or '未設定'}
- ベンチマークチャンネル: {', '.join(benchmark_channels or []) or '未設定'}
- 強み・独自性: {strengths or '未設定'}
- コンテンツスタイル: {content_style or '未設定'}

## 収集キーワード（{len(suggestions)}個）
{chr(10).join(suggestions[:100])}

## 指示
上記のキーワードとプロファイルを踏まえ、{count}個の企画を提案してください。
ユーザーの強みを活かせる企画を優先してください。
需要スコア×穴場度スコアが高い順にソートしてください。
JSON配列のみを返してください。"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text
        # JSON部分を抽出
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        ideas = json.loads(text.strip())

        # スコアでソート
        ideas.sort(key=lambda x: (x.get("demand_score", 0) * x.get("niche_score", 0)), reverse=True)

        return ideas[:count]

    except Exception as e:
        logger.error(f"企画生成エラー: {e}")
        return []
