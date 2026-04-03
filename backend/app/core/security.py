"""
認証・認可モジュール。
Supabase Auth JWTトークンの検証を行う（ES256 JWKS対応）。
"""

import logging
from typing import Any

import httpx
import jwt as pyjwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, get_supabase, use_supabase_sdk, async_session_factory
from app.models.models import User

logger = logging.getLogger(__name__)

# Bearer トークン抽出スキーム
bearer_scheme = HTTPBearer(auto_error=False)

# Supabase JWKS エンドポイント
JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# PyJWKClient（公開鍵をキャッシュして取得）
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """JWKSクライアントをシングルトンで取得"""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URL)
    return _jwks_client


def _decode_token(token: str) -> dict[str, Any]:
    """
    JWTトークンをデコード・検証する。
    Supabase の ES256 JWKS を使用して検証。
    """
    try:
        # JWKSから署名キーを取得
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # トークンを検証・デコード
        payload: dict[str, Any] = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256", "RS256"],
            audience="authenticated",
        )
        return payload
    except pyjwt.InvalidAudienceError:
        # audience検証なしで再試行
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "HS256", "RS256"],
                options={"verify_aud": False},
            )
            return payload
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"トークン検証に失敗しました: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"トークン検証に失敗しました: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def _ensure_user_exists_supabase(auth_id_str: str, email: str | None) -> str:
    """
    Supabase SDK版: usersテーブルにレコードがなければ自動作成する。

    Returns:
        usersテーブルのid（UUID文字列）
    """
    try:
        sb = get_supabase()
        result = sb.table("users").select("id").eq("auth_id", auth_id_str).execute()

        if result.data:
            return str(result.data[0]["id"])

        # 新規ユーザー作成
        new_user = sb.table("users").insert({
            "auth_id": auth_id_str,
            "email": email or f"{auth_id_str}@unknown.com",
            "display_name": email.split("@")[0] if email else None,
            "plan": "free",
            "quota_used": 0,
            "quota_limit": 100,
        }).execute()

        logger.info(f"新規ユーザーを作成しました: auth_id={auth_id_str}, email={email}")
        return str(new_user.data[0]["id"])
    except Exception as e:
        logger.warning(f"ユーザー自動作成中にエラー: {e}")
        return auth_id_str


async def _ensure_user_exists(
    db: AsyncSession, auth_id_str: str, email: str | None
) -> str:
    """
    usersテーブルにレコードがなければ自動作成する。
    初回ログイン時にユーザーレコードをINSERTする。

    Returns:
        usersテーブルのid（UUID文字列）
    """
    import uuid as uuid_mod
    auth_id = uuid_mod.UUID(auth_id_str)

    try:
        result = await db.execute(
            select(User).where(User.auth_id == auth_id)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user is None:
            new_user = User(
                auth_id=auth_id,
                email=email or f"{auth_id_str}@unknown.com",
                display_name=email.split("@")[0] if email else None,
                plan="free",
                quota_used=0,
                quota_limit=100,
            )
            db.add(new_user)
            await db.flush()
            await db.refresh(new_user)
            logger.info(f"新規ユーザーを作成しました: auth_id={auth_id_str}, email={email}")
            return str(new_user.id)

        return str(existing_user.id)
    except Exception as e:
        logger.warning(f"ユーザー自動作成中にエラー: {e}")
        await db.rollback()
        return auth_id_str


async def _get_db_optional():
    """Supabase SDKモード時はNoneを返すDB依存"""
    if use_supabase_sdk():
        yield None
    else:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession | None = Depends(_get_db_optional),
) -> dict[str, Any]:
    """
    現在のユーザー情報を取得する依存関数。
    DEV_MODE=true の場合は認証をバイパスしてテストユーザーを返す。
    """
    if settings.DEV_MODE:
        return {
            "user_id": DEV_USER_ID,
            "email": "test@example.com",
            "role": "authenticated",
            "raw": {},
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報が提供されていません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンにユーザーIDが含まれていません",
        )

    email: str | None = payload.get("email")

    # ユーザーの自動作成（初回ログイン時）→ usersテーブルのidを取得
    if use_supabase_sdk():
        db_user_id = _ensure_user_exists_supabase(user_id, email)
    else:
        db_user_id = await _ensure_user_exists(db, user_id, email)

    return {
        "user_id": db_user_id,
        "email": email,
        "role": payload.get("role", "authenticated"),
        "raw": payload,
    }
