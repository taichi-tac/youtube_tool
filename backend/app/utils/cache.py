"""
キャッシュユーティリティモジュール。
Redis接続およびキャッシュ操作のヘルパーを提供する。
"""

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

# Redisクライアント（設定されている場合のみ）
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Redisクライアントを取得する（未設定ならNone）"""
    global _redis_client
    if settings.REDIS_URL is None:
        return None
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """
    キャッシュからデータを取得する。

    Args:
        key: キャッシュキー

    Returns:
        キャッシュされたデータ（存在しない場合はNone）
    """
    client = await get_redis()
    if client is None:
        return None

    try:
        value = await client.get(key)
        if value is not None:
            return json.loads(value)
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    キャッシュにデータを保存する。

    Args:
        key: キャッシュキー
        value: 保存するデータ（JSON直列化可能なもの）
        ttl: 有効期限（秒）

    Returns:
        保存成功ならTrue
    """
    client = await get_redis()
    if client is None:
        return False

    try:
        serialized = json.dumps(value, ensure_ascii=False)
        await client.set(key, serialized, ex=ttl)
        return True
    except Exception:
        return False


async def cache_delete(key: str) -> bool:
    """
    キャッシュからデータを削除する。

    Args:
        key: キャッシュキー

    Returns:
        削除成功ならTrue
    """
    client = await get_redis()
    if client is None:
        return False

    try:
        await client.delete(key)
        return True
    except Exception:
        return False


async def close_redis() -> None:
    """Redisコネクションを閉じる"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
