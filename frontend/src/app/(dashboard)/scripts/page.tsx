"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import Link from "next/link";
import { apiClient, getProjectId } from "@/lib/api-client";
import type { Script } from "@/types/script";
import { formatDate } from "@/lib/utils";

const statusLabel: Record<string, string> = {
  draft: "下書き",
  generating: "生成中",
  completed: "完了",
  error: "エラー",
};

const statusColor: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  generating: "bg-yellow-50 text-yellow-700",
  completed: "bg-green-50 text-green-700",
  error: "bg-red-50 text-red-700",
};

export default function ScriptsPage() {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const pid = await getProjectId();
        const result = await apiClient.get<Script[]>(`/api/v1/scripts/${pid}`);
        setScripts(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "台本一覧の取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return (
    <div>
      <PageHeader
        title="台本一覧"
        description="作成済みの台本を管理"
        actions={
          <Link
            href="/scripts/new"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            新規作成
          </Link>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-sm text-gray-500 py-12">読み込み中...</div>
      ) : scripts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-sm text-gray-400">台本がまだありません</p>
          <p className="mt-1 text-xs text-gray-400">「新規作成」から台本を生成してください</p>
          <Link
            href="/scripts/new"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            台本を生成する
          </Link>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  タイトル
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  ステータス
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  文字数
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  作成日
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {scripts.map((script) => (
                <tr key={script.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {script.title}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        statusColor[script.status] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {statusLabel[script.status] || script.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {script.word_count != null ? `${script.word_count}文字` : "-"}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(script.created_at)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm">
                    <Link
                      href={`/scripts/${script.id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      編集
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
