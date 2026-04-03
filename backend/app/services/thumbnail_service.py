"""
サムネイルサービスモジュール。
サムネイル画像の管理・Claude Vision分析結果の保存を行う。
"""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import anthropic
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Thumbnail, Video

logger = logging.getLogger(__name__)

# Anthropic クライアント（モジュールレベルで初期化）
_anthropic_client: anthropic.Anthropic | None = None


def _get_anthropic_client() -> anthropic.Anthropic:
    """Anthropicクライアントのシングルトンを返す"""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


THUMBNAIL_ANALYSIS_PROMPT = """\
あなたはYouTubeサムネイル分析の専門家です。
以下の画像はYouTube動画のサムネイルです。詳細に分析して、以下のJSON形式で結果を返してください。

必ず以下のJSON形式のみを返してください。説明文は不要です。

{
  "dominant_colors": [
    {"hex": "#FF0000", "name": "赤"}
  ],
  "text_overlay": "サムネイル上に表示されているテキスト（なければnull）",
  "face_count": 0,
  "emotion": "表情の説明（surprise / smile / serious / angry / neutral / sad / excited など。顔がなければnull）",
  "composition_type": "構図パターン（full_face / split / text_only / product / before_after / collage / landscape / character / diagram のいずれか）",
  "click_score": 7,
  "analysis_raw": "この画像の分析コメントを自由記述で日本語で書いてください。色使い、構図、テキストの効果、改善提案など。"
}

注意事項:
- dominant_colors: 主要な色を最大5色まで抽出。hex値と日本語の色名を含める
- click_score: 1-10のスケールで、CTR（クリック率）を予測するスコア。視覚的インパクト、好奇心喚起、プロ品質などを総合評価
- composition_type: 最も近いパターンを1つ選択
- face_count: 顔が見える人数（イラストも含む）
- analysis_raw: 200文字程度で具体的な改善提案も含めてください
"""


async def analyze_thumbnail(image_url: str) -> dict[str, Any]:
    """
    サムネイルURLから画像を取得し、Claude Vision APIで分析する。

    Args:
        image_url: サムネイル画像のURL

    Returns:
        分析結果の辞書
    """
    # 画像をダウンロードしてbase64エンコード
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.get(image_url)
        response.raise_for_status()
        image_data = base64.standard_b64encode(response.content).decode("utf-8")

    # Content-Typeからメディアタイプを判定
    content_type = response.headers.get("content-type", "image/jpeg")
    if "png" in content_type:
        media_type = "image/png"
    elif "webp" in content_type:
        media_type = "image/webp"
    elif "gif" in content_type:
        media_type = "image/gif"
    else:
        media_type = "image/jpeg"

    # Claude Vision API呼び出し
    client = _get_anthropic_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": THUMBNAIL_ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    # レスポンスからJSONを抽出
    raw_text = message.content[0].text
    # JSON部分を抽出（```json ... ``` で囲まれている場合も考慮）
    json_text = raw_text.strip()
    if json_text.startswith("```"):
        # コードブロックからJSON部分を抽出
        lines = json_text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)
        json_text = "\n".join(json_lines)

    try:
        result = json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("Claude Vision APIのレスポンスをJSONとしてパースできませんでした: %s", raw_text[:200])
        result = {
            "dominant_colors": [],
            "text_overlay": None,
            "face_count": 0,
            "emotion": None,
            "composition_type": None,
            "click_score": 0,
            "analysis_raw": raw_text,
        }

    return result


async def analyze_thumbnails_batch(
    video_ids: list[uuid.UUID],
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    複数動画のサムネイルを一括分析してthumbnailsテーブルに保存する。

    Args:
        video_ids: 分析対象の動画IDリスト
        project_id: プロジェクトID
        db: データベースセッション

    Returns:
        分析結果のリスト
    """
    # 動画情報を取得
    stmt = select(Video).where(
        Video.id.in_(video_ids),
        Video.project_id == project_id,
    )
    result = await db.execute(stmt)
    videos = list(result.scalars().all())

    if not videos:
        return []

    results = []
    for video in videos:
        # サムネURLを構築（youtube_video_idからmaxresdefault取得）
        thumbnail_url = f"https://img.youtube.com/vi/{video.youtube_video_id}/maxresdefault.jpg"

        try:
            analysis = await analyze_thumbnail(thumbnail_url)
        except Exception as e:
            logger.error("サムネイル分析に失敗しました (video_id=%s): %s", video.id, str(e))
            # sddefault にフォールバック
            try:
                thumbnail_url = f"https://img.youtube.com/vi/{video.youtube_video_id}/sddefault.jpg"
                analysis = await analyze_thumbnail(thumbnail_url)
            except Exception as e2:
                logger.error("サムネイル分析フォールバックも失敗 (video_id=%s): %s", video.id, str(e2))
                results.append({
                    "video_id": str(video.id),
                    "thumbnail_url": thumbnail_url,
                    "error": str(e2),
                })
                continue

        # 既存のサムネイルレコードを検索
        existing_stmt = select(Thumbnail).where(
            Thumbnail.video_id == video.id,
            Thumbnail.project_id == project_id,
        )
        existing_result = await db.execute(existing_stmt)
        thumbnail = existing_result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        dominant_colors_data = analysis.get("dominant_colors", [])
        analysis_raw_text = analysis.get("analysis_raw", "")

        if thumbnail is not None:
            # 既存レコードを更新
            thumbnail.image_url = thumbnail_url
            thumbnail.dominant_colors = {"colors": dominant_colors_data}
            thumbnail.text_overlay = analysis.get("text_overlay")
            thumbnail.face_count = analysis.get("face_count", 0)
            thumbnail.emotion = analysis.get("emotion")
            thumbnail.composition_type = analysis.get("composition_type")
            thumbnail.click_score = analysis.get("click_score", 0)
            thumbnail.analysis_raw = {"comment": analysis_raw_text}
            thumbnail.analyzed_at = now
        else:
            # 新規レコードを作成
            thumbnail = Thumbnail(
                project_id=project_id,
                video_id=video.id,
                image_url=thumbnail_url,
                source_type="youtube",
                dominant_colors={"colors": dominant_colors_data},
                text_overlay=analysis.get("text_overlay"),
                face_count=analysis.get("face_count", 0),
                emotion=analysis.get("emotion"),
                composition_type=analysis.get("composition_type"),
                click_score=analysis.get("click_score", 0),
                analysis_raw={"comment": analysis_raw_text},
                analyzed_at=now,
            )
            db.add(thumbnail)

        await db.flush()
        await db.refresh(thumbnail)

        results.append({
            "video_id": str(video.id),
            "thumbnail_url": thumbnail_url,
            "dominant_colors": dominant_colors_data,
            "text_overlay": analysis.get("text_overlay"),
            "face_count": analysis.get("face_count", 0),
            "emotion": analysis.get("emotion"),
            "composition_type": analysis.get("composition_type"),
            "click_score": analysis.get("click_score", 0),
            "analysis_raw": analysis_raw_text,
        })

    return results


async def create_thumbnail(
    db: AsyncSession,
    project_id: uuid.UUID,
    image_url: str,
    source_type: str = "uploaded",
    video_id: Optional[uuid.UUID] = None,
) -> Thumbnail:
    """
    サムネイルレコードを作成する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        image_url: 画像URL（必須）
        source_type: ソース種別 (youtube / uploaded / generated)
        video_id: 紐づける動画ID（任意）

    Returns:
        作成されたサムネイルオブジェクト
    """
    thumbnail = Thumbnail(
        project_id=project_id,
        video_id=video_id,
        image_url=image_url,
        source_type=source_type,
    )
    db.add(thumbnail)
    await db.flush()
    await db.refresh(thumbnail)
    return thumbnail


async def get_thumbnails_by_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    composition_type: Optional[str] = None,
    sort_by_score: bool = False,
) -> list[Thumbnail]:
    """プロジェクトに紐づくサムネイル一覧を取得する"""
    stmt = select(Thumbnail).where(Thumbnail.project_id == project_id)

    # composition_type フィルタ
    if composition_type is not None:
        stmt = stmt.where(Thumbnail.composition_type == composition_type)

    # ソート: click_score降順 or created_at降順
    if sort_by_score:
        stmt = stmt.order_by(Thumbnail.click_score.desc().nulls_last())
    else:
        stmt = stmt.order_by(Thumbnail.created_at.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_thumbnails_by_ids(
    db: AsyncSession,
    thumbnail_ids: list[uuid.UUID],
) -> list[Thumbnail]:
    """指定IDのサムネイル一覧を取得する"""
    stmt = select(Thumbnail).where(Thumbnail.id.in_(thumbnail_ids))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_thumbnail(
    db: AsyncSession,
    thumbnail_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[Thumbnail]:
    """サムネイルレコードを更新する（Vision分析結果等）"""
    stmt = select(Thumbnail).where(Thumbnail.id == thumbnail_id)
    result = await db.execute(stmt)
    thumbnail = result.scalar_one_or_none()
    if thumbnail is None:
        return None

    for key, value in kwargs.items():
        if value is not None and hasattr(thumbnail, key):
            setattr(thumbnail, key, value)

    await db.flush()
    await db.refresh(thumbnail)
    return thumbnail


async def analyze_thumbnails_batch_supabase(
    video_ids: list[uuid.UUID],
    project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Supabase SDK版: 複数動画のサムネイルを一括分析してthumbnailsテーブルに保存する。

    Args:
        video_ids: 分析対象の動画IDリスト
        project_id: プロジェクトID

    Returns:
        分析結果のリスト
    """
    from app.core.database import get_supabase

    sb = get_supabase()
    ids_str = [str(vid) for vid in video_ids]

    # 動画情報を取得
    video_result = sb.table("videos").select("*").in_(
        "id", ids_str
    ).eq(
        "project_id", str(project_id)
    ).execute()
    videos = video_result.data

    if not videos:
        return []

    results = []
    for video in videos:
        thumbnail_url = f"https://img.youtube.com/vi/{video['youtube_video_id']}/maxresdefault.jpg"

        try:
            analysis = await analyze_thumbnail(thumbnail_url)
        except Exception as e:
            logger.error("サムネイル分析に失敗しました (video_id=%s): %s", video["id"], str(e))
            try:
                thumbnail_url = f"https://img.youtube.com/vi/{video['youtube_video_id']}/sddefault.jpg"
                analysis = await analyze_thumbnail(thumbnail_url)
            except Exception as e2:
                logger.error("サムネイル分析フォールバックも失敗 (video_id=%s): %s", video["id"], str(e2))
                results.append({
                    "video_id": str(video["id"]),
                    "thumbnail_url": thumbnail_url,
                    "error": str(e2),
                })
                continue

        dominant_colors_data = analysis.get("dominant_colors", [])
        analysis_raw_text = analysis.get("analysis_raw", "")

        # 既存のサムネイルレコードを検索
        existing_result = sb.table("thumbnails").select("*").eq(
            "video_id", str(video["id"])
        ).eq(
            "project_id", str(project_id)
        ).execute()

        now_iso = datetime.now(timezone.utc).isoformat()
        thumb_data = {
            "image_url": thumbnail_url,
            "dominant_colors": {"colors": dominant_colors_data},
            "text_overlay": analysis.get("text_overlay"),
            "face_count": analysis.get("face_count", 0),
            "emotion": analysis.get("emotion"),
            "composition_type": analysis.get("composition_type"),
            "click_score": analysis.get("click_score", 0),
            "analysis_raw": {"comment": analysis_raw_text},
            "analyzed_at": now_iso,
        }

        if existing_result.data:
            sb.table("thumbnails").update(thumb_data).eq(
                "id", existing_result.data[0]["id"]
            ).execute()
        else:
            thumb_data.update({
                "project_id": str(project_id),
                "video_id": str(video["id"]),
                "source_type": "youtube",
            })
            sb.table("thumbnails").insert(thumb_data).execute()

        results.append({
            "video_id": str(video["id"]),
            "thumbnail_url": thumbnail_url,
            "dominant_colors": dominant_colors_data,
            "text_overlay": analysis.get("text_overlay"),
            "face_count": analysis.get("face_count", 0),
            "emotion": analysis.get("emotion"),
            "composition_type": analysis.get("composition_type"),
            "click_score": analysis.get("click_score", 0),
            "analysis_raw": analysis_raw_text,
        })

    return results
