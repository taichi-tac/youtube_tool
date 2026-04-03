"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import Link from "next/link";
import { apiClient, getProjectId } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import type { Project } from "@/types/project";
import type { Keyword } from "@/types/keyword";
import type { Video } from "@/types/video";
import type { Script } from "@/types/script";

interface DashboardStats {
  projectName: string;
  keywords: number;
  videos: number;
  scripts: number;
}

const quickActions = [
  { label: "台本を生成", href: "/scripts/new", description: "新しい台本をウィザードで生成" },
  { label: "キーワード検索", href: "/keywords", description: "トレンドキーワードを調査" },
  { label: "動画検索", href: "/videos", description: "YouTube動画を検索・保存" },
  { label: "ナレッジ検索", href: "/knowledge", description: "RAGナレッジベースを検索" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentScripts, setRecentScripts] = useState<Script[]>([]);
  const [recentKeywords, setRecentKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      setLoading(true);
      setError(null);
      try {
        const pid = await getProjectId();
        const [keywords, videos, scripts] = await Promise.all([
          apiClient.get<Keyword[]>(`/api/v1/keywords/${pid}`),
          apiClient.get<Video[]>(`/api/v1/videos/${pid}`),
          apiClient.get<Script[]>(`/api/v1/scripts/${pid}`),
        ]);
        const projects = await apiClient.get<Project[]>("/api/v1/projects/");
        const project = projects[0];
        setStats({
          projectName: project.name,
          keywords: keywords.length,
          videos: videos.length,
          scripts: scripts.length,
        });
        // 最近の台本3件
        const sorted = [...scripts].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setRecentScripts(sorted.slice(0, 3));
        // 最近のキーワード5件
        const kwSorted = [...keywords].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setRecentKeywords(kwSorted.slice(0, 5));
      } catch (err) {
        setError(err instanceof Error ? err.message : "データ取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  const statCards = stats
    ? [
        { label: "プロジェクト", value: stats.projectName, href: "/projects" },
        { label: "キーワード数", value: String(stats.keywords), href: "/keywords" },
        { label: "動画数", value: String(stats.videos), href: "/videos" },
        { label: "台本数", value: String(stats.scripts), href: "/scripts" },
      ]
    : [];

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

  return (
    <div>
      <PageHeader title="ダッシュボード" description="YouTube Tool の概要" />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Stats */}
      {loading ? (
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse rounded-lg border border-gray-200 bg-white p-6">
              <div className="h-4 w-20 rounded bg-gray-200" />
              <div className="mt-3 h-8 w-16 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      ) : (
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((stat) => (
            <Link
              key={stat.label}
              href={stat.href}
              className="rounded-lg border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md"
            >
              <p className="text-sm font-medium text-gray-500">{stat.label}</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">{stat.value}</p>
            </Link>
          ))}
        </div>
      )}

      {/* クイック台本生成 + クイックアクション */}
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">クイックアクション</h2>
        <Link
          href="/scripts/new"
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors shadow-sm"
        >
          クイック台本生成
        </Link>
      </div>
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {quickActions.map((action) => (
          <Link
            key={action.label}
            href={action.href}
            className="rounded-lg border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md"
          >
            <h3 className="text-sm font-semibold text-gray-900">{action.label}</h3>
            <p className="mt-1 text-xs text-gray-500">{action.description}</p>
          </Link>
        ))}
      </div>

      {/* 最近の台本 & キーワード */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 最近生成した台本 */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">最近の台本</h2>
            <Link href="/scripts" className="text-xs text-blue-600 hover:text-blue-800">
              すべて表示
            </Link>
          </div>
          {recentScripts.length > 0 ? (
            <div className="space-y-3">
              {recentScripts.map((s) => (
                <Link
                  key={s.id}
                  href={`/scripts/${s.id}`}
                  className="block rounded-lg border border-gray-100 p-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-gray-900 truncate pr-2">
                      {s.title}
                    </h3>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
                        statusColor[s.status] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {statusLabel[s.status] || s.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">
                    {formatDate(s.created_at)}
                    {s.word_count != null && ` / ${s.word_count}文字`}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">台本がまだありません</p>
          )}
        </div>

        {/* 最近検索したキーワード */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">最近のキーワード</h2>
            <Link href="/keywords" className="text-xs text-blue-600 hover:text-blue-800">
              すべて表示
            </Link>
          </div>
          {recentKeywords.length > 0 ? (
            <div className="space-y-2">
              {recentKeywords.map((kw) => (
                <Link
                  key={kw.id}
                  href={`/keywords/${kw.id}`}
                  className="flex items-center justify-between rounded-lg border border-gray-100 p-3 hover:bg-gray-50 transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-gray-900">{kw.keyword}</span>
                    {kw.seed_keyword && (
                      <span className="ml-2 text-xs text-gray-400">
                        (seed: {kw.seed_keyword})
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">{formatDate(kw.created_at)}</span>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">キーワードがまだありません</p>
          )}
        </div>
      </div>
    </div>
  );
}
