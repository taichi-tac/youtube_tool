"""
コンテンツ変換サービス。
台本からタイムスタンプ、コミュニティ投稿、ショート提案、X/ブログ/note記事を生成する。
"""

import json
import logging
from typing import Any, Optional

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_timestamps(script_body: str, title: str = "") -> list[dict[str, str]]:
    """
    台本からLP風ブレット（興味喚起型タイムスタンプ）を生成する。
    中身をまとめるのではなく、興味を引く表現にする。
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下のYouTube台本から、概要欄用のタイムスタンプ（目次）を生成してください。

## 重要なルール
- タイムスタンプは「LPのブレット」のように興味を引く表現にする
- 中身を要約するのではなく、「気になって見たくなる」表現にする
- 10〜15個程度
- 形式: "00:00 興味を引くフレーズ" のコピペ可能な形式

## 悪い例（NG）
00:00 挨拶
01:30 再生数が伸びない理由の解説
05:00 アルゴリズムの仕組み

## 良い例（OK）
00:00 99%の人が勘違いしている「伸びない本当の原因」
01:30 登録者100人止まりの人に共通する"ある習慣"
05:00 YouTubeが絶対に教えてくれない裏側の仕組み

## 台本
タイトル: {title}

{script_body[:8000]}

## 出力
JSON配列で返してください: [{{"time": "00:00", "text": "フレーズ"}}]"""

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
        logger.error(f"タイムスタンプ生成エラー: {e}")
        return [{"time": "ERROR", "text": str(e)}]


async def generate_community_post(
    title: str,
    script_hook: str = "",
    target_viewer: str = "",
) -> dict[str, str]:
    """
    コミュニティ投稿用のテキストを生成する。
    セールスレター風の興味喚起型告知文。
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下のYouTube動画の「前日告知用コミュニティ投稿」を作成してください。

## ルール
- セールスページのような興味喚起型にする
- 動画の内容をまとめるのではなく、「見たい！」と思わせる
- 絵文字を適度に使用
- 3つのバリエーションを作成（短め/標準/長め）
- 最後に「明日公開🔥」のような煽り文句

## 動画情報
タイトル: {title}
ターゲット: {target_viewer or '未設定'}
冒頭: {script_hook[:500] if script_hook else '未設定'}

## 出力
JSON形式: {{"short": "短いバージョン", "standard": "標準バージョン", "long": "長いバージョン"}}"""

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
        logger.error(f"コミュニティ投稿生成エラー: {e}")
        return {"short": f"エラー: {e}", "standard": f"エラー: {e}", "long": f"エラー: {e}"}


async def suggest_shorts(
    script_body: str,
    genre: str = "",
    suggestions: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    長尺台本からショート動画の切り抜きポイントを提案する。
    サジェストキーワードに合致するセグメントを特定。
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    suggest_text = ""
    if suggestions:
        suggest_text = f"\n## 狙いたいサジェストキーワード\n{chr(10).join(suggestions[:20])}\n"

    prompt = f"""以下のYouTube長尺動画の台本から、ショート動画として切り抜くべきポイントを提案してください。

## ルール
- 単に「面白い部分」ではなく、YouTube検索のサジェストキーワードで見つけてもらえる部分を優先
- 各ショートは15〜60秒（300〜1200文字）程度
- 5〜8個提案
- 各提案にタイトル案（サジェスト意識）と狙うキーワードを付ける
{suggest_text}
## ジャンル: {genre or '未設定'}

## 台本
{script_body[:8000]}

## 出力
JSON配列: [{{"title": "ショートのタイトル", "keyword": "狙うキーワード", "start_text": "台本内の開始テキスト（最初の30文字）", "reason": "なぜこの部分か", "estimated_seconds": 30}}]"""

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
        logger.error(f"ショート提案エラー: {e}")
        return [{"title": "ERROR", "keyword": str(e), "start_text": "", "reason": str(e), "estimated_seconds": 0}]


async def convert_to_media(
    script_body: str,
    title: str = "",
    target_format: str = "x",  # "x", "blog", "note"
) -> dict[str, Any]:
    """
    台本をX投稿/ブログ記事/note記事に変換する。
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    format_instructions = {
        "x": """X（Twitter）用の投稿を生成してください。
- メインツイート（140文字以内）× 1本
- スレッド用ツイート（各140文字以内）× 5〜8本
- バズりやすい表現を使う
出力: {"main": "メインツイート", "thread": ["ツイート1", "ツイート2", ...]}""",

        "blog": """SEO対応のブログ記事を生成してください。
- タイトル（H1）
- 導入文（300文字）
- 本文（見出しH2×3〜5、各セクション300〜500文字）
- まとめ（200文字）
出力: {"title": "タイトル", "intro": "導入", "sections": [{"heading": "見出し", "body": "本文"}], "conclusion": "まとめ"}""",

        "note": """note記事を生成してください。
- タイトル
- 冒頭の引き（読みたくなる導入）
- 本文（段落ごと、読みやすい改行多め）
- 締め（フォロー促進）
出力: {"title": "タイトル", "intro": "導入", "body": "本文", "closing": "締め"}""",
    }

    prompt = f"""以下のYouTube台本を{target_format}用のコンテンツに変換してください。

## 動画タイトル: {title}

## 台本
{script_body[:6000]}

## 変換ルール
{format_instructions.get(target_format, format_instructions["x"])}

JSON形式で返してください。"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        result = json.loads(text.strip())
        result["format"] = target_format
        return result
    except Exception as e:
        logger.error(f"メディア変換エラー: {e}")
        if target_format == "x":
            return {"format": target_format, "main": f"エラー: {e}", "thread": []}
        else:
            return {"format": target_format, "title": "エラー", "intro": str(e), "body": "", "conclusion": ""}
