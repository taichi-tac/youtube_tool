"""
ナレッジモデル管理ルーター。
パーソナル/コンテンツ/プロダクトナレッジをモデル単位で管理する。
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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
        # チャンネルURLから動画を取得して分析
        try:
            from app.services.youtube_service import search_videos
            channel_name = body.youtube_channel_url.split("/")[-1].replace("@", "")
            videos = await search_videos(query=channel_name, max_results=5)
            video_texts = []
            for v in videos:
                video_texts.append(f"タイトル: {v.get('title', '')}\n説明: {v.get('description', '')}")
            input_text = f"チャンネル: {channel_name}\n\n" + "\n---\n".join(video_texts)
        except Exception:
            input_text = f"YouTubeチャンネル: {body.youtube_channel_url}"

    if not input_text.strip():
        raise HTTPException(status_code=400, detail="URLまたはテキストを入力してください")

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下の情報を分析し、YouTubeチャンネル運営者のナレッジを3カテゴリに分類して抽出してください。

## 入力情報
{input_text[:4000]}

## 抽出してほしい項目（JSON形式）
{{
  "personal_knowledge": {{
    "achievements": "数値ベースの実績",
    "profile": "プロフィール・経歴・肩書",
    "origin_story": "原体験ストーリー（転機・苦労・逆転劇）",
    "values": "価値観・人生哲学・信念",
    "vision": "ビジョン・目標",
    "strengths": "強み・ポジショントーク",
    "first_person": "一人称・基本の口調",
    "tone_rules": "語尾・言い回しルール",
    "casual_level": "フランクさレベル",
    "expression_patterns": "推奨表現パターン",
    "decoration_rules": "装飾記号の使い方",
    "ng_expressions": "避けるべき表現"
  }},
  "content_knowledge": {{
    "popular_keywords": "人気キーワード・共通言語",
    "target_info": "発信ターゲット情報",
    "youtube_templates": "動画構成の特徴"
  }},
  "product_knowledge": {{
    "product_overview": "商品概要",
    "core_concept": "コアコンセプト・USP",
    "curriculum": "カリキュラム構成",
    "support_community": "サポート体制",
    "benefits": "特典",
    "pricing": "料金・保証",
    "appeal_keywords": "訴求キーワード",
    "target_attributes": "ターゲット属性",
    "target_problems": "ターゲットの悩み",
    "ideal_future": "理想の未来",
    "worst_future": "最悪の未来",
    "required_mindset": "必須マインドセット",
    "client_results": "クライアント成果事例"
  }}
}}

情報が不明な項目は空文字にしてください。JSONのみ返してください。"""

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
