"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { useVideoAnalysis } from "@/hooks/useVideoAnalysis";
import { useThumbnailAnalysis } from "@/hooks/useThumbnailAnalysis";
import { formatNumber, formatDate } from "@/lib/utils";
import type { Video } from "@/types/video";

export default function VideoDetailPage() {
  const params = useParams();
  const videoId = params.id as string;

  const {
    loading,
    error,
    fetchVideo,
    comments,
    commentsLoading,
    fetchComments,
    commentAnalysis,
    analysisLoading,
    analyzeComments,
  } = useVideoAnalysis();

  const { analyzeThumbnails, analyzing: thumbAnalyzing } = useThumbnailAnalysis();

  const [video, setVideo] = useState<Video | null>(null);

  useEffect(() => {
    async function load() {
      const v = await fetchVideo(videoId);
      if (v) setVideo(v);
    }
    if (videoId) load();
  }, [videoId, fetchVideo]);

  const handleFetchComments = () => {
    fetchComments(videoId);
  };

  const handleAnalyzeComments = () => {
    analyzeComments(videoId);
  };

  const handleThumbnailAnalysis = () => {
    analyzeThumbnails([videoId]);
  };

  if (loading && !video) {
    return (
      <div>
        <PageHeader title="動画詳細" description="読み込み中..." />
        <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (error && !video) {
    return (
      <div>
        <PageHeader title="動画詳細" description={`動画ID: ${videoId}`} />
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="動画詳細" description={video?.title || `動画ID: ${videoId}`} />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 左カラム: 動画情報 */}
        <div className="lg:col-span-2 space-y-6">
          {/* サムネイル */}
          <div className="aspect-video rounded-lg bg-gray-200 overflow-hidden">
            {video?.thumbnail_url ? (
              <img
                src={video.thumbnail_url}
                alt={video.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-gray-400">
                動画プレビュー
              </div>
            )}
          </div>

          {/* 動画情報 */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {video?.title || "動画タイトル"}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {video?.channel_title || "チャンネル名"}
                </p>
              </div>
              {video?.is_trending && (
                <span className="flex items-center gap-1 rounded-full bg-red-500 px-3 py-1 text-xs font-bold text-white">
                  <span>&#x1F525;</span> 伸びてる
                </span>
              )}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
              <StatItem
                label="再生数"
                value={video?.view_count != null ? formatNumber(video.view_count) : "-"}
              />
              <StatItem
                label="いいね"
                value={video?.like_count != null ? formatNumber(video.like_count) : "-"}
              />
              <StatItem
                label="コメント数"
                value={video?.comment_count != null ? formatNumber(video.comment_count) : "-"}
              />
              <StatItem
                label="投稿日"
                value={video?.published_at ? formatDate(video.published_at) : "-"}
              />
              <StatItem
                label="伸び速度"
                value={
                  video?.views_per_day != null
                    ? `${formatNumber(Math.round(video.views_per_day))}/日`
                    : "-"
                }
              />
            </div>
          </div>

          {/* コメントセクション */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">コメント</h2>
              <div className="flex gap-2">
                <button
                  onClick={handleFetchComments}
                  disabled={commentsLoading}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {commentsLoading ? "取得中..." : "コメント取得"}
                </button>
                <button
                  onClick={handleAnalyzeComments}
                  disabled={analysisLoading || comments.length === 0}
                  className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
                >
                  {analysisLoading ? "分析中..." : "ニーズ分析"}
                </button>
              </div>
            </div>

            {comments.length > 0 ? (
              <div className="max-h-80 overflow-y-auto space-y-3">
                {comments.map((comment, idx) => (
                  <div
                    key={comment.id || idx}
                    className="rounded-lg border border-gray-100 bg-gray-50 p-3"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-700">
                        {comment.author}
                      </span>
                      <span className="text-xs text-gray-400">
                        {comment.like_count > 0 && `${comment.like_count}いいね`}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{comment.text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">
                「コメント取得」ボタンでコメントを読み込んでください
              </p>
            )}
          </div>

          {/* ニーズ分析結果 */}
          {commentAnalysis && (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">
                ニーズ分析結果
              </h2>
              <p className="mb-4 text-sm text-gray-600">{commentAnalysis.summary}</p>
              <p className="mb-4 text-xs text-gray-400">
                分析コメント数: {commentAnalysis.total_comments}件
              </p>

              <div className="space-y-3">
                {commentAnalysis.needs.map((need, idx) => (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {need.category}
                      </span>
                      <span className="text-xs text-gray-500">
                        {need.count}件 ({need.percentage}%)
                      </span>
                    </div>
                    {/* 棒グラフ風UI */}
                    <div className="h-6 w-full rounded bg-gray-100 relative overflow-hidden">
                      <div
                        className="h-full rounded bg-gradient-to-r from-blue-500 to-blue-600 flex items-center transition-all duration-500"
                        style={{ width: `${Math.min(need.percentage, 100)}%` }}
                      >
                        <span className="px-2 text-xs font-medium text-white whitespace-nowrap">
                          {need.percentage}%
                        </span>
                      </div>
                    </div>
                    {need.representative_comments.length > 0 && (
                      <div className="mt-1 space-y-1">
                        {need.representative_comments.slice(0, 2).map((c, ci) => (
                          <p key={ci} className="text-xs text-gray-400 truncate pl-2 border-l-2 border-gray-200">
                            {c}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右カラム: アクション */}
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">アクション</h2>
            <div className="space-y-3">
              <button
                onClick={handleThumbnailAnalysis}
                disabled={thumbAnalyzing}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
              >
                {thumbAnalyzing ? "分析中..." : "サムネ分析"}
              </button>
              <a
                href={`https://www.youtube.com/watch?v=${video?.youtube_video_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full rounded-lg border border-gray-300 px-4 py-2.5 text-center text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                YouTubeで開く
              </a>
            </div>
          </div>

          {/* 動画説明文 */}
          {video?.description && (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-3 text-sm font-semibold text-gray-900">説明文</h2>
              <p className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-[20]">
                {video.description}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}
