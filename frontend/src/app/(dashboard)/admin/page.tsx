"use client";

import { useState, useEffect } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";

interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at: string | null;
  email_confirmed_at: string | null;
  is_banned: boolean;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<{ users: AdminUser[] }>("/api/v1/admin/users");
      setUsers(data.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  const handleBan = async (userId: string, isBanned: boolean) => {
    setActionLoading(userId);
    try {
      const endpoint = isBanned ? "unban" : "ban";
      await apiClient.patch(`/api/v1/admin/users/${userId}/${endpoint}`);
      setUsers((prev) =>
        prev.map((u) => u.id === userId ? { ...u, is_banned: !isBanned } : u)
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "操作に失敗しました");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId: string) => {
    setActionLoading(userId);
    setConfirmDelete(null);
    try {
      await apiClient.delete(`/api/v1/admin/users/${userId}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "削除に失敗しました");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <PageHeader title="管理者" description="登録ユーザーの管理" />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
      ) : (
        <>
          <p className="mb-4 text-sm text-gray-500">{users.length}人のユーザー</p>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">メールアドレス</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">登録日</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">最終ログイン</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">メール確認</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">状態</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((u) => (
                  <tr key={u.id} className={u.is_banned ? "bg-red-50" : "hover:bg-gray-50"}>
                    <td className="px-4 py-3 font-medium text-gray-900">{u.email}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(u.created_at)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(u.last_sign_in_at)}</td>
                    <td className="px-4 py-3">
                      {u.email_confirmed_at
                        ? <span className="text-green-600 text-xs font-medium">確認済</span>
                        : <span className="text-gray-400 text-xs">未確認</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      {u.is_banned
                        ? <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">無効</span>
                        : <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">有効</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleBan(u.id, u.is_banned)}
                          disabled={actionLoading === u.id}
                          className={`rounded px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                            u.is_banned
                              ? "bg-green-100 text-green-700 hover:bg-green-200"
                              : "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                          }`}
                        >
                          {actionLoading === u.id ? "..." : u.is_banned ? "有効化" : "無効化"}
                        </button>
                        {confirmDelete === u.id ? (
                          <>
                            <button
                              onClick={() => handleDelete(u.id)}
                              disabled={actionLoading === u.id}
                              className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                            >
                              確認削除
                            </button>
                            <button
                              onClick={() => setConfirmDelete(null)}
                              className="rounded border px-3 py-1 text-xs text-gray-600 hover:bg-gray-100"
                            >
                              キャンセル
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setConfirmDelete(u.id)}
                            className="rounded bg-red-50 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-100"
                          >
                            削除
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
