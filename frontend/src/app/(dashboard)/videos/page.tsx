"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";
import { useVideoAnalysis } from "@/hooks/useVideoAnalysis";
import { useThumbnailAnalysis } from "@/hooks/useThumbnailAnalysis";
import { formatNumber, formatDate } from "@/lib/utils";
import type { Video } from "@/types/video";

type SortKey = "views_per_day" | "view_count" | "published_at";
type PeriodFilter = "all" | "180" | "90" | "30";

export default function VideosPage() {
  const { videos, loading, error, fetchVideos, searchVideos } = useVideoAnalysis();
  const { analyzeThumbnails, analyzing } = useThumbnailAnalysis();
  const [searchQuery, setSearchQuery] = useState("");

  // フィルタ・ソート
  const [sortKey, setSortKey] = useState<SortKey>("views_per_day");
  const [trendingOnly, setTrendingOnly] = useState(false);
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>("all");

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchVideos(searchQuery.trim());
    }
  };

  const handleThumbnailAnalysis = async (videoId: string) => {
    await analyzeThumbnails([videoId]);
  };

  // フィルタ・ソート適用
  const filteredVideos = useMemo(() => {
    let result = [...videos];

    // 期間フィルタ
    if (periodFilter !== "all") {
      const days = Number(periodFilter);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      result = result.filter((v) => {
        if (!v.published_at) return false;
        return new Date(v.published_at) >= cutoff;
      });
    }

    // トレンドフィルタ
    if (trendingOnly) {
      result = result.filter((v) => v.is_trending);
    }

    // ソート
    result.sort((a, b) => {
      if (sortKey === "views_per_day") {
        return (b.views_per_day ?? 0) - (a.views_per_day ?? 0);
      }
      if (sortKey === "view_count") {
        return (b.view_count ?? 0) - (a.view_count ?? 0);
      }
      // published_at
      const da = a.published_at ? new Date(a.published_at).getTime() : 0;
      const db = b.published_at ? new Date(b.published_at).getTime() : 0;
      return db - da;
    });

    return result;
  }, [videos, sortKey, trendingOnly, periodFilter]);

  return (
    <div>
      <PageHeader title="動画一覧" description="YouTube動画を検索・保存・閲覧" />

      {/* 検索フォーム */}
      <form onSubmit={handleSearch} className="mb-4 flex gap-3">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="YouTube動画を検索..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading || !searchQuery.trim()}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "検索中..." : "検索"}
        </button>
      </form>

      {/* フィルタ・ソートバー */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* 並び替え */}
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="views_per_day">伸び速度順</option>
          <option value="view_count">再生数順</option>
          <option value="published_at">投稿日順</option>
        </select>

        {/* 期間フィルタ */}
        <select
          value={periodFilter}
          onChange={(e) => setPeriodFilter(e.target.value as PeriodFilter)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">全期間</option>
          <option value="180">180日以内</option>
          <option value="90">90日以内</option>
          <option value="30">30日以内</option>
        </select>

        {/* トレンドフィルタ */}
        <label className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 transition-colors">
          <input
            type="checkbox"
            checked={trendingOnly}
            onChange={(e) => setTrendingOnly(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-gray-700">伸びてる動画のみ</span>
        </label>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {loading && videos.length === 0 ? (
        <div className="text-center text-sm text-gray-500 py-12">読み込み中...</div>
      ) : filteredVideos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-sm text-gray-400">
            {videos.length === 0
              ? "動画データがまだありません"
              : "条件に一致する動画がありません"}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            上の検索フォームからYouTube動画を検索してください
          </p>
        </div>
      ) : (
        <>
          <p className="mb-3 text-sm text-gray-500">{filteredVideos.length}件の動画</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredVideos.map((video) => (
              <VideoCard
                key={video.id}
                video={video}
                analyzing={analyzing}
                onThumbnailAnalysis={handleThumbnailAnalysis}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function VideoCard({
  video,
  analyzing,
  onThumbnailAnalysis,
}: {
  video: Video;
  analyzing: boolean;
  onThumbnailAnalysis: (videoId: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-md">
      <Link href={`/videos/${video.id}`}>
        <div className="aspect-video bg-gray-100 relative">
          {video.thumbnail_url ? (
            <img
              src={video.thumbnail_url}
              alt={video.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-gray-400 text-sm">
              No Thumbnail
            </div>
          )}
          {video.is_trending && (
            <span className="absolute top-2 right-2 flex items-center gap-1 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white shadow">
              <span aria-label="trending">&#x1F525;</span> 伸びてる
            </span>
          )}
        </div>
      </Link>
      <div className="p-4">
        <Link href={`/videos/${video.id}`}>
          <h3 className="line-clamp-2 text-sm font-medium text-gray-900 hover:text-blue-600 transition-colors">
            {video.title}
          </h3>
        </Link>
        <p className="mt-1 text-xs text-gray-500">
          {video.channel_title || "不明なチャンネル"}
        </p>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
          {video.view_count != null && (
            <span>{formatNumber(video.view_count)}回視聴</span>
          )}
          {video.like_count != null && (
            <span>{formatNumber(video.like_count)}いいね</span>
          )}
          {video.published_at && (
            <span>{formatDate(video.published_at)}</span>
          )}
        </div>
        {/* 伸び速度 */}
        {video.views_per_day != null && (
          <div className="mt-2 text-xs font-medium text-orange-600">
            1日あたり{formatNumber(Math.round(video.views_per_day))}再生
          </div>
        )}

        {/* アクションボタン */}
        <div className="mt-3 flex gap-2">
          <Link
            href={`/videos/${video.id}`}
            className="flex-1 rounded bg-indigo-50 px-2 py-1.5 text-center text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
          >
            コメント分析
          </Link>
          <button
            onClick={() => onThumbnailAnalysis(video.id)}
            disabled={analyzing}
            className="flex-1 rounded bg-emerald-50 px-2 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 transition-colors"
          >
            {analyzing ? "分析中..." : "サムネ分析"}
          </button>
        </div>
      </div>
    </div>
  );
}
