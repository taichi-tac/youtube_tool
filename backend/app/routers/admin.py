"""
管理者ルーター。
登録ユーザーの一覧・無効化・削除を提供する。
Supabase Admin API (service_role_key) を使用。
"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["管理者"])

SUPABASE_ADMIN_URL = f"{settings.SUPABASE_URL}/auth/v1/admin"
ADMIN_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


def _require_admin(user: dict[str, Any]) -> None:
    """管理者メールでなければ403を返す"""
    admin_emails = [e.strip() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]
    if not admin_emails:
        raise HTTPException(status_code=403, detail="管理者が設定されていません")
    if user.get("email") not in admin_emails:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")


@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 50,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """登録ユーザー一覧を取得する"""
    _require_admin(user)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_ADMIN_URL}/users",
            headers=ADMIN_HEADERS,
            params={"page": page, "per_page": per_page},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()

    users = data.get("users", [])

    # プロジェクトのAPIキー登録状況を取得
    # auth.users.id → public.users.id → projects の順で解決する
    from app.core.database import get_supabase, use_supabase_sdk
    projects_by_user: dict[str, dict] = {}  # auth_id -> project
    if use_supabase_sdk():
        try:
            sb = get_supabase()
            auth_ids = [u.get("id") for u in users if u.get("id")]
            if auth_ids:
                # auth_id → internal user id の変換
                users_result = sb.table("users").select("id,auth_id").in_("auth_id", auth_ids).execute()
                auth_to_internal = {r["auth_id"]: r["id"] for r in (users_result.data or [])}

                internal_ids = list(auth_to_internal.values())
                if internal_ids:
                    proj_result = sb.table("projects").select(
                        "user_id,name,anthropic_api_key,youtube_api_key"
                    ).in_("user_id", internal_ids).execute()

                    # internal user_id -> project
                    projects_by_internal: dict[str, dict] = {}
                    for p in (proj_result.data or []):
                        iid = p.get("user_id")
                        if iid and iid not in projects_by_internal:
                            projects_by_internal[iid] = p

                    # auth_id -> project に変換
                    for auth_id, internal_id in auth_to_internal.items():
                        if internal_id in projects_by_internal:
                            projects_by_user[auth_id] = projects_by_internal[internal_id]
        except Exception as e:
            logger.error(f"管理者: プロジェクトキー取得エラー: {e}")

    result = []
    for u in users:
        uid = u.get("id")
        proj = projects_by_user.get(uid, {})
        result.append({
            "id": uid,
            "email": u.get("email"),
            "created_at": u.get("created_at"),
            "last_sign_in_at": u.get("last_sign_in_at"),
            "banned_until": u.get("banned_until"),
            "is_banned": bool(u.get("banned_until")),
            "email_confirmed_at": u.get("email_confirmed_at"),
            "project_name": proj.get("name"),
            "has_anthropic_key": bool(proj.get("anthropic_api_key")),
            "has_youtube_key": bool(proj.get("youtube_api_key")),
        })

    return {"users": result, "total": data.get("total", len(result))}


@router.patch("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """ユーザーを無効化する（ban）"""
    _require_admin(user)

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{SUPABASE_ADMIN_URL}/users/{user_id}",
            headers=ADMIN_HEADERS,
            json={"ban_duration": "876600h"},  # 100年
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"message": "ユーザーを無効化しました"}


@router.patch("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """ユーザーの無効化を解除する"""
    _require_admin(user)

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{SUPABASE_ADMIN_URL}/users/{user_id}",
            headers=ADMIN_HEADERS,
            json={"ban_duration": "none"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"message": "ユーザーの無効化を解除しました"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """ユーザーを完全削除する"""
    _require_admin(user)

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{SUPABASE_ADMIN_URL}/users/{user_id}",
            headers=ADMIN_HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
