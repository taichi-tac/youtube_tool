"""
プロジェクトごとのAPIキー取得ユーティリティ。
ユーザーが登録したキーを優先し、未登録の場合はシステムキーにフォールバック。
"""

import uuid
from typing import Optional

from app.core.config import settings
from app.core.database import get_supabase, use_supabase_sdk


def get_anthropic_key(project_keys: dict) -> str:
    """Anthropic APIキーを返す（ユーザーキー優先）"""
    return project_keys.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY


def get_openai_key(project_keys: dict) -> str:
    """OpenAI APIキーを返す（ユーザーキー優先）"""
    return project_keys.get("openai_api_key") or settings.OPENAI_API_KEY


def get_youtube_key(project_keys: dict) -> str:
    """YouTube APIキーを返す（ユーザーキー優先）"""
    return project_keys.get("youtube_api_key") or settings.YOUTUBE_API_KEY


def fetch_project_keys(project_id: uuid.UUID) -> dict:
    """プロジェクトのAPIキーを取得する（同期版）"""
    if use_supabase_sdk():
        try:
            sb = get_supabase()
            result = sb.table("projects").select(
                "anthropic_api_key,openai_api_key,youtube_api_key"
            ).eq("id", str(project_id)).execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass
    return {}
