"""
認証・認可モジュール。
Supabase Auth JWTトークンの検証を行う。
"""

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User

logger = logging.getLogger(__name__)

# Bearer トークン抽出スキーム
bearer_scheme = HTTPBearer(auto_error=False)

# Supabase JWTの検証に使う公開鍵URL / シークレット
# Supabaseは HS256 + JWT secret でJWTを署名する
ALGORITHM = "HS256"


def _decode_token(token: str) -> dict[str, Any]:
    """
    JWTトークンをデコード・検証する。
    新しいSupabase キー形式（sb_publishable_, sb_secret_）では
    JWT署名キーが publishable key や secret key とは異なる場合がある。
    SUPABASE_KEY → SUPABASE_SERVICE_ROLE_KEY の順で検証を試みる。
    """
    keys_to_try = [settings.SUPABASE_KEY, settings.SUPABASE_SERVICE_ROLE_KEY]
    last_error: Exception | None = None

    for key in keys_to_try:
        if not key:
            continue
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=[ALGORITHM],
                audience="authenticated",
            )
            return payload
        except JWTError as e:
            last_error = e
            continue

    # どのキーでも検証できなかった場合は、audience検証なしでも試す
    for key in keys_to_try:
        if not key:
            continue
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[ALGORITHM],
                options={"verify_aud": False},
            )
            return payload
        except JWTError as e:
            last_error = e
            continue

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"トークン検証に失敗しました: {str(last_error)}",
        headers={"WWW-Authenticate": "Bearer"},
    )


DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


async def _ensure_user_exists(
    db: AsyncSession, auth_id: str, email: str | None
) -> None:
    """
    usersテーブルにレコードがなければ自動作成する。
    初回ログイン時にユーザーレコードをINSERTする。
    """
    try:
        result = await db.execute(
            select(User).where(User.auth_id == auth_id)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user is None:
            new_user = User(
                auth_id=auth_id,
                email=email or f"{auth_id}@unknown.com",
                display_name=email.split("@")[0] if email else None,
                plan="free",
                quota_used=0,
                quota_limit=100,
            )
            db.add(new_user)
            await db.flush()
            logger.info(f"新規ユーザーを作成しました: auth_id={auth_id}, email={email}")
    except Exception as e:
        logger.warning(f"ユーザー自動作成中にエラー: {e}")
        # ユーザー作成に失敗してもリクエスト自体は通す
        await db.rollback()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
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

    # ユーザーの自動作成（初回ログイン時）
    await _ensure_user_exists(db, user_id, email)

    return {
        "user_id": user_id,
        "email": email,
        "role": payload.get("role", "authenticated"),
        "raw": payload,
    }
