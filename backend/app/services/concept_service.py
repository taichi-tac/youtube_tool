"""
コンセプト設定サービス。
URL分析、コンセプトブラッシュアップ、同ジャンルチャンネル提案を行う。
"""

import json
import logging
from typing import Any, Optional

import anthropic
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def analyze_url(url: str) -> dict[str, Any]:
    """
    URLを分析してジャンル・ターゲット・コンセプト等を自動抽出する。
    LP、YouTube動画、ブログ等に対応。
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # URLからコンテンツを取得
    content_text = ""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http:
            resp = await http.get(url)
            # HTMLからテキスト抽出（簡易）
            html = resp.text
            # タグ除去
            import re
            content_text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            content_text = re.sub(r'<style[^>]*>.*?</style>', '', content_text, flags=re.DOTALL)
            content_text = re.sub(r'<[^>]+>', ' ', content_text)
            content_text = re.sub(r'\s+', ' ', content_text).strip()[:5000]
    except Exception as e:
        logger.warning(f"URL取得エラー: {e}")
        content_text = f"URL: {url} (取得失敗)"

    prompt = f"""以下のURLのコンテンツを分析し、YouTube チャンネルのコンセプト設定に必要な情報を抽出してください。

## URL: {url}
## コンテンツ:
{content_text}

## 抽出してほしい情報（JSON形式）
{{
  "genre": "ジャンル（例: 恋愛、ビジネス、副業）",
  "target_audience": "ターゲット層（例: 20-30代男性サラリーマン）",
  "content_style": "コンテンツスタイル（例: ノウハウ系、エンタメ系）",
  "strengths": "強み・独自性（分析から推測）",
  "concept_suggestion": "コンセプト案（1行で）",
  "keywords": ["関連キーワード1", "関連キーワード2", "関連キーワード3"]
}}

JSON のみを返してください。"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"URL分析エラー: {e}")
        return {"error": str(e)}


async def analyze_text(text_input: str) -> dict[str, Any]:
    """テキスト入力からコンセプト情報を抽出する。"""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下のテキストを分析し、YouTubeチャンネルのコンセプト設定に必要な情報を抽出してください。

## テキスト:
{text_input[:3000]}

## 抽出してほしい情報（JSON形式）
{{
  "genre": "ジャンル",
  "target_audience": "ターゲット層",
  "content_style": "コンテンツスタイル",
  "strengths": "強み・独自性",
  "concept_suggestion": "コンセプト案（1行）",
  "keywords": ["関連KW1", "関連KW2", "関連KW3"]
}}

JSONのみ返してください。"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"テキスト分析エラー: {e}")
        return {"error": str(e)}


async def suggest_similar_channels(genre: str, target_audience: str = "") -> list[dict[str, str]]:
    """同ジャンルのYouTubeチャンネルを提案する。"""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下のジャンルとターゲットに近いYouTubeチャンネルを10個提案してください。

ジャンル: {genre}
ターゲット: {target_audience or '未指定'}

日本のチャンネルを中心に、有名なものからニッチなものまで幅広く提案してください。

JSON配列: [{{"name": "チャンネル名", "description": "簡単な説明", "style": "スタイル（ノウハウ系、エンタメ系等）"}}]
JSONのみ返してください。"""

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
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"チャンネル提案エラー: {e}")
        return []


async def brushup_concept(
    current_concept: dict[str, Any],
    research_data: dict[str, Any],
) -> dict[str, Any]:
    """
    リサーチ結果を基にコンセプトをブラッシュアップする。
    例: 「恋愛チャンネル」→「駆け引きをしない恋愛チャンネル」
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下の現在のコンセプトとリサーチ結果を基に、より差別化された新しいコンセプトを3つ提案してください。

## 現在のコンセプト
- ジャンル: {current_concept.get('genre', '未設定')}
- ターゲット: {current_concept.get('target_audience', '未設定')}
- 強み: {current_concept.get('strengths', '未設定')}
- 現在のコンセプト: {current_concept.get('concept', '未設定')}

## リサーチ結果
- 競合の成功要因: {json.dumps(research_data.get('success_factors', []), ensure_ascii=False)}
- 市場の穴: {json.dumps(research_data.get('market_gaps', []), ensure_ascii=False)}

## ブラッシュアップの方向性
- 競合と逆のポジションを取る
- 市場の穴を埋める
- ユーザーの強みを活かす
- 「〇〇しない△△チャンネル」のように明確に差別化

## 出力（JSON配列）
[
  {{
    "concept": "新しいコンセプト（1行）",
    "genre": "ジャンル",
    "target_audience": "ターゲット",
    "reason": "なぜこのコンセプトが良いか",
    "differentiation": "何が他と違うか"
  }}
]
JSONのみ返してください。"""

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
        return {"suggestions": json.loads(text.strip())}
    except Exception as e:
        logger.error(f"コンセプトブラッシュアップエラー: {e}")
        return {"error": str(e)}
