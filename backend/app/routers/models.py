"""
ナレッジモデル管理ルーター。
パーソナル/コンテンツ/プロダクトナレッジをモデル単位で管理する。
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.core.database import get_supabase, use_supabase_sdk
from app.core.security import get_current_user

router = APIRouter(prefix="/models", tags=["ナレッジモデル"])


# === Schemas ===

class PersonalKnowledge(BaseModel):
    achievements: str = ""  # 数値ベースの実績
    profile: str = ""  # プロフィール・経歴・肩書・年齢
    origin_story: str = ""  # 原体験ストーリー（転機・苦労・逆転劇）
    values: str = ""  # 価値観・人生哲学・信念
    vision: str = ""  # ビジョン・目標（作りたい世界観）
    strengths: str = ""  # 強み・ポジショントーク
    first_person: str = ""  # 一人称・基本の口調
    tone_rules: str = ""  # 語尾・言い回しルール
    casual_level: str = ""  # フランクさレベル（丁寧⇔カジュアル配分）
    expression_patterns: str = ""  # 推奨表現パターン（断定、対比、数字活用等）
    decoration_rules: str = ""  # 装飾記号の使い方
    ng_expressions: str = ""  # 避けるべき表現（NG集）


class ContentKnowledge(BaseModel):
    popular_keywords: str = ""  # 発信ジャンルの人気KW・共通言語
    target_info: str = ""  # 発信ターゲット情報
    youtube_templates: str = ""  # 動画台本テンプレ・概要欄テンプレ等


class ProductKnowledge(BaseModel):
    product_overview: str = ""  # 商品概要（何を提供するか）
    core_concept: str = ""  # コアコンセプト・USP
    curriculum: str = ""  # カリキュラム構成
    support_community: str = ""  # サポート体制・コミュニティ
    benefits: str = ""  # 入会特典一覧
    pricing: str = ""  # 料金プラン・保証制度
    appeal_keywords: str = ""  # 訴求キーワード一覧
    target_attributes: str = ""  # ターゲット属性（職業・状況・理解レベル）
    target_problems: str = ""  # 具体的な悩み・課題
    ideal_future: str = ""  # 最高の未来（理想の状態）
    worst_future: str = ""  # 最悪の未来（恐怖・不安）
    required_mindset: str = ""  # 必須マインドセット
    client_results: str = ""  # クライアント成果事例（ビフォーアフター・期間・数値）


class ModelCreate(BaseModel):
    name: str


class ModelUpdate(BaseModel):
    name: str | None = None
    personal_knowledge: PersonalKnowledge | None = None
    content_knowledge: ContentKnowledge | None = None
    product_knowledge: ProductKnowledge | None = None


class AutoFillRequest(BaseModel):
    youtube_channel_url: str = ""
    text_input: str = ""


# === Endpoints ===

@router.get("/{project_id}")
async def list_models(
    project_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """プロジェクトのモデル一覧を取得"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("knowledge_models").select("*").eq(
            "project_id", str(project_id)
        ).order("created_at", desc=True).execute()
        return result.data
    raise HTTPException(status_code=501)


@router.post("/{project_id}")
async def create_model(
    project_id: uuid.UUID,
    body: ModelCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """新しいモデルを作成"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("knowledge_models").insert({
            "project_id": str(project_id),
            "name": body.name,
            "personal_knowledge": {},
            "content_knowledge": {},
            "product_knowledge": {},
        }).execute()
        return result.data[0]
    raise HTTPException(status_code=501)


@router.get("/{project_id}/{model_id}")
async def get_model(
    project_id: uuid.UUID,
    model_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """モデルの詳細を取得"""
    if use_supabase_sdk():
        sb = get_supabase()
        result = sb.table("knowledge_models").select("*").eq(
            "id", str(model_id)
        ).eq("project_id", str(project_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="モデルが見つかりません")
        return result.data[0]
    raise HTTPException(status_code=501)


@router.patch("/{project_id}/{model_id}")
async def update_model(
    project_id: uuid.UUID,
    model_id: uuid.UUID,
    body: ModelUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """モデルのナレッジを更新"""
    if use_supabase_sdk():
        sb = get_supabase()
        update_data: dict[str, Any] = {}
        if body.name is not None:
            update_data["name"] = body.name
        if body.personal_knowledge is not None:
            update_data["personal_knowledge"] = body.personal_knowledge.model_dump()
        if body.content_knowledge is not None:
            update_data["content_knowledge"] = body.content_knowledge.model_dump()
        if body.product_knowledge is not None:
            update_data["product_knowledge"] = body.product_knowledge.model_dump()

        if not update_data:
            raise HTTPException(status_code=400, detail="更新データがありません")

        result = sb.table("knowledge_models").update(update_data).eq(
            "id", str(model_id)
        ).eq("project_id", str(project_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="モデルが見つかりません")
        return result.data[0]
    raise HTTPException(status_code=501)


@router.delete("/{project_id}/{model_id}")
async def delete_model(
    project_id: uuid.UUID,
    model_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """モデルを削除"""
    if use_supabase_sdk():
        sb = get_supabase()
        sb.table("knowledge_models").delete().eq(
            "id", str(model_id)
        ).eq("project_id", str(project_id)).execute()
        return {"message": "削除しました"}
    raise HTTPException(status_code=501)


@router.post("/{project_id}/{model_id}/autofill")
async def autofill_model(
    project_id: uuid.UUID,
    model_id: uuid.UUID,
    body: AutoFillRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """YouTubeチャンネルURLまたはテキストからAIで各項目を自動入力"""
    import json
    import anthropic
    from app.core.config import settings

    # 入力テキスト準備
    input_text = body.text_input
    if body.youtube_channel_url:
        import re
        from app.services.youtube_service import search_videos, get_video_details
        from app.core.config import settings
        from googleapiclient.discovery import build

        url = body.youtube_channel_url
        channel_name = ""
        channel_id = ""

        # URL形式判定
        handle_match = re.search(r'youtube\.com/@([^/\?]+)', url)
        id_match = re.search(r'youtube\.com/channel/([^/\?]+)', url)

        try:
            youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

            if id_match:
                # /channel/UC... 形式 → channels.listでチャンネル情報取得
                channel_id = id_match.group(1)
                ch_resp = youtube.channels().list(part="snippet", id=channel_id).execute()
                if ch_resp.get("items"):
                    channel_name = ch_resp["items"][0]["snippet"]["title"]
            elif handle_match:
                # /@handle 形式 → forHandleで検索
                handle = handle_match.group(1)
                ch_resp = youtube.channels().list(part="snippet", forHandle=handle).execute()
                if ch_resp.get("items"):
                    channel_name = ch_resp["items"][0]["snippet"]["title"]
                    channel_id = ch_resp["items"][0]["id"]
            else:
                # それ以外 → そのまま検索キーワードとして使用
                channel_name = url.split("/")[-1].replace("@", "")

            # チャンネルIDで動画を検索
            video_texts = []
            if channel_id:
                search_resp = youtube.search().list(
                    part="id", channelId=channel_id, type="video",
                    maxResults=10, order="viewCount"
                ).execute()
                video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
            else:
                # チャンネルID不明ならチャンネル名で検索
                videos = await search_videos(query=channel_name, max_results=10)
                video_ids = [v.get("youtube_video_id", "") for v in videos if v.get("youtube_video_id")]

            if video_ids:
                details = await get_video_details(video_ids[:10])
                for d in details:
                    desc = (d.get("description") or "")[:500]
                    video_texts.append(
                        f"タイトル: {d.get('title', '')}\n"
                        f"チャンネル: {d.get('channel_title', '')}\n"
                        f"再生数: {d.get('view_count', 0)}\n"
                        f"説明: {desc}"
                    )

            # 上位3本の動画の字幕（トランスクリプト）を取得して口調分析に活用
            transcript_texts = []
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                ytt = YouTubeTranscriptApi()
                for vid in video_ids[:3]:
                    try:
                        transcript = ytt.fetch(vid, languages=["ja"])
                        t_text = " ".join([s.text for s in transcript.snippets[:100]])
                        transcript_texts.append(f"[動画{vid}の字幕]\n{t_text[:1500]}")
                    except Exception:
                        pass
            except Exception:
                pass

            transcript_section = ""
            if transcript_texts:
                transcript_section = "\n\n=== 動画の字幕（口調・話し方の分析用）===\n" + "\n---\n".join(transcript_texts)

            input_text = f"チャンネル名: {channel_name}\nチャンネルURL: {url}\n\n" + "\n---\n".join(video_texts) + transcript_section
            logger.info(f"チャンネル分析: {channel_name}, 動画{len(video_texts)}本, 字幕{len(transcript_texts)}本取得")
        except Exception as e:
            logger.warning(f"YouTube取得エラー: {e}")
            input_text = f"YouTubeチャンネル: {url}"

    if not input_text.strip():
        raise HTTPException(status_code=400, detail="URLまたはテキストを入力してください")

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下のYouTubeチャンネルの情報（動画メタデータ＋字幕テキスト）を分析し、チャンネル運営者のナレッジを抽出してください。

【最重要】字幕テキストが含まれている場合、必ず以下を分析してください：
- 一人称は何を使っているか（僕、俺、私、自分 等）
- 語尾のパターン（〜ですね、〜なんですよ、〜じゃん 等）
- 話し方のフランクさ（丁寧語中心か、タメ口中心か、その配分）
- よく使う表現パターン（断定する、質問を投げかける、数字を多用する 等）
- 原体験や過去の苦労に関するエピソードがあれば抽出

## 入力情報
{input_text[:8000]}

## 抽出してほしい項目（JSON形式）
{{
  "personal_knowledge": {{
    "achievements": "数値ベースの実績（登録者数、再生数、売上、受講生数等）",
    "profile": "プロフィール・経歴・肩書・年齢（推測でもOK）",
    "origin_story": "原体験ストーリー（字幕から過去の苦労・転機・逆転劇を抽出）",
    "values": "価値観・人生哲学・信念（字幕から読み取れる信条）",
    "vision": "ビジョン・目標（字幕やプロフィールから推測）",
    "strengths": "強み・なぜこの人から学ぶべきか",
    "first_person": "字幕から特定した一人称（例: 僕、俺、私）と基本の口調",
    "tone_rules": "字幕から抽出した語尾パターン（例: 〜ですね、〜なんですよ、〜じゃないですか）を5つ以上列挙",
    "casual_level": "フランクさレベル（例: 7:3でカジュアル寄り）丁寧語とタメ口の割合を判定",
    "expression_patterns": "字幕から抽出した特徴的な表現パターン（断定、対比、数字活用、例え話、質問形式等）",
    "decoration_rules": "概要欄やタイトルで使われている装飾記号・絵文字パターン",
    "ng_expressions": "この人が使わなさそうな表現（推測）"
  }},
  "content_knowledge": {{
    "popular_keywords": "このジャンルで頻出するキーワード・共通言語",
    "target_info": "発信ターゲット（誰に向けているか）",
    "youtube_templates": "動画の構成パターン（冒頭の入り方、展開、締め方）"
  }},
  "product_knowledge": {{
    "product_overview": "商品・サービス概要",
    "core_concept": "コアコンセプト・USP",
    "curriculum": "カリキュラム構成",
    "support_community": "サポート体制・コミュニティ",
    "benefits": "特典一覧",
    "pricing": "料金・保証制度",
    "appeal_keywords": "訴求キーワード一覧",
    "target_attributes": "ターゲット属性（職業・状況）",
    "target_problems": "ターゲットの具体的な悩み",
    "ideal_future": "理想の未来（この商品で得られる状態）",
    "worst_future": "最悪の未来（買わない場合の恐怖）",
    "required_mindset": "求める受講者像",
    "client_results": "クライアント成果事例"
  }}
}}

【重要】字幕テキストがある場合、first_person、tone_rules、casual_level、expression_patternsは必ず具体的に記入してください。空文字にしないでください。
情報が本当に不明な項目のみ空文字にしてください。JSONのみ返してください。"""

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
        extracted = json.loads(text.strip())

        # DBに保存
        if use_supabase_sdk():
            sb = get_supabase()
            sb.table("knowledge_models").update({
                "personal_knowledge": extracted.get("personal_knowledge", {}),
                "content_knowledge": extracted.get("content_knowledge", {}),
                "product_knowledge": extracted.get("product_knowledge", {}),
            }).eq("id", str(model_id)).eq("project_id", str(project_id)).execute()

        return extracted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI分析エラー: {str(e)}")


def get_model_context(model_data: dict[str, Any]) -> str:
    """モデルのナレッジをテキスト形式に変換する（台本生成のRAGコンテキスト用）"""
    parts = []

    personal = model_data.get("personal_knowledge", {})
    if any(personal.values()):
        parts.append("【パーソナルナレッジ】")
        field_labels = {
            "achievements": "実績", "profile": "プロフィール", "origin_story": "原体験",
            "values": "価値観", "vision": "ビジョン", "strengths": "強み",
            "first_person": "一人称・口調", "tone_rules": "語尾ルール",
            "casual_level": "フランクさ", "expression_patterns": "表現パターン",
            "decoration_rules": "装飾記号", "ng_expressions": "NG表現",
        }
        for key, label in field_labels.items():
            val = personal.get(key, "")
            if val:
                parts.append(f"- {label}: {val}")

    content = model_data.get("content_knowledge", {})
    if any(content.values()):
        parts.append("\n【コンテンツナレッジ】")
        for key, label in {"popular_keywords": "人気KW", "target_info": "ターゲット", "youtube_templates": "テンプレ"}.items():
            val = content.get(key, "")
            if val:
                parts.append(f"- {label}: {val}")

    product = model_data.get("product_knowledge", {})
    if any(product.values()):
        parts.append("\n【プロダクトナレッジ】")
        field_labels = {
            "product_overview": "商品概要", "core_concept": "USP", "curriculum": "カリキュラム",
            "support_community": "サポート", "benefits": "特典", "pricing": "料金",
            "appeal_keywords": "訴求KW", "target_attributes": "ターゲット属性",
            "target_problems": "悩み", "ideal_future": "理想の未来",
            "worst_future": "最悪の未来", "required_mindset": "マインドセット",
            "client_results": "成果事例",
        }
        for key, label in field_labels.items():
            val = product.get(key, "")
            if val:
                parts.append(f"- {label}: {val}")

    return "\n".join(parts) if parts else ""
