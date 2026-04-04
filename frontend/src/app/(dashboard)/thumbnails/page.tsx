"use client";

import { useEffect, useState, useMemo } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { useThumbnailAnalysis } from "@/hooks/useThumbnailAnalysis";
import type { ThumbnailAnalysis } from "@/types/video";

export default function ThumbnailsPage() {
  const { thumbnails, loading, error, fetchThumbnails } = useThumbnailAnalysis();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [compareMode, setCompareMode] = useState(false);
  const [detailThumb, setDetailThumb] = useState<ThumbnailAnalysis | null>(null);

  useEffect(() => {
    fetchThumbnails();
  }, [fetchThumbnails]);

  // click_score順ソート
  const sortedThumbnails = useMemo(() => {
    return [...thumbnails].sort((a, b) => (b.click_score ?? 0) - (a.click_score ?? 0));
  }, [thumbnails]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size < 3) {
          next.add(id);
        }
      }
      return next;
    });
  };

  const selectedThumbnails = sortedThumbnails.filter((t) => selectedIds.has(t.id));

  return (
    <div>
      <PageHeader
        title="サムネ分析"
        description="YouTubeサムネイルの分析と比較"
        actions={
          <button
            onClick={() => {
              setCompareMode(!compareMode);
              if (compareMode) setSelectedIds(new Set());
            }}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              compareMode
                ? "bg-purple-600 text-white hover:bg-purple-700"
                : "border border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {compareMode ? "比較モードOFF" : "比較モード"}
          </button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* 比較パネル */}
      {compareMode && selectedThumbnails.length > 0 && (
        <div className="mb-6 rounded-lg border-2 border-purple-200 bg-purple-50 p-6">
          <h2 className="mb-4 text-sm font-semibold text-purple-900">
            サムネ比較 ({selectedThumbnails.length}/3)
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {selectedThumbnails.map((thumb) => (
              <CompareCard key={thumb.id} thumb={thumb} />
            ))}
          </div>
        </div>
      )}

      {compareMode && selectedThumbnails.length === 0 && (
        <div className="mb-6 rounded-lg border-2 border-dashed border-purple-300 p-8 text-center text-sm text-purple-400">
          比較するサムネイルを2-3枚選択してください
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
      ) : sortedThumbnails.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-sm text-gray-400">分析済みサムネイルがありません</p>
          <p className="mt-1 text-xs text-gray-400">
            動画一覧ページからサムネ分析を実行してください
          </p>
        </div>
      ) : (
        <>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            分析済みサムネイル ({sortedThumbnails.length}件)
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedThumbnails.map((thumb) => (
              <ThumbnailCard
                key={thumb.id}
                thumb={thumb}
                compareMode={compareMode}
                isSelected={selectedIds.has(thumb.id)}
                onToggle={() => toggleSelect(thumb.id)}
                onDetail={() => setDetailThumb(thumb)}
              />
            ))}
          </div>
        </>
      )}

      {/* 詳細モーダル */}
      {detailThumb && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setDetailThumb(null)}
        >
          <div
            className="relative mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setDetailThumb(null)}
              className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 text-xl"
            >
              &times;
            </button>

            <h2 className="mb-4 text-lg font-bold text-gray-900">サムネ分析詳細</h2>

            <div className="aspect-video mb-4 overflow-hidden rounded-lg bg-gray-100">
              <img
                src={detailThumb.image_url}
                alt="サムネイル"
                className="h-full w-full object-cover"
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-medium text-gray-700">CTRスコア</span>
                <span className={`text-2xl font-bold ${
                  (detailThumb.click_score ?? 0) >= 8 ? "text-green-600" :
                  (detailThumb.click_score ?? 0) >= 5 ? "text-yellow-600" : "text-red-600"
                }`}>
                  {detailThumb.click_score ?? 0}/10
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border p-3">
                  <span className="text-xs text-gray-500">構図タイプ</span>
                  <p className="text-sm font-medium text-gray-900">{detailThumb.composition_type ?? "未分析"}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <span className="text-xs text-gray-500">顔検出</span>
                  <p className="text-sm font-medium text-gray-900">
                    {detailThumb.face_count ? `${detailThumb.face_count}人` : "なし"}
                    {detailThumb.emotion && ` (${detailThumb.emotion})`}
                  </p>
                </div>
              </div>

              {detailThumb.text_overlay && (
                <div className="rounded-lg border p-3">
                  <span className="text-xs text-gray-500">テキスト要素</span>
                  <p className="text-sm text-gray-900">{detailThumb.text_overlay}</p>
                </div>
              )}

              {(detailThumb.dominant_colors?.colors ?? []).length > 0 && (
                <div className="rounded-lg border p-3">
                  <span className="text-xs text-gray-500 block mb-2">配色</span>
                  <div className="flex items-center gap-2">
                    {detailThumb.dominant_colors!.colors!.map((c, i) => (
                      <div key={i} className="flex items-center gap-1">
                        <span
                          className="inline-block h-6 w-6 rounded-full border border-gray-200"
                          style={{ backgroundColor: c.hex }}
                        />
                        <span className="text-xs text-gray-600">{c.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {detailThumb.analysis_raw?.comment && (
                <div className="rounded-lg bg-blue-50 p-4">
                  <span className="text-xs font-medium text-blue-700 block mb-1">AI分析コメント</span>
                  <p className="text-sm text-gray-800 leading-relaxed">{detailThumb.analysis_raw.comment}</p>
                </div>
              )}

              <div className="text-xs text-gray-400 text-right">
                分析日時: {detailThumb.analyzed_at ? new Date(detailThumb.analyzed_at).toLocaleString("ja-JP") : "不明"}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ThumbnailCard({
  thumb,
  compareMode,
  isSelected,
  onToggle,
  onDetail,
}: {
  thumb: ThumbnailAnalysis;
  compareMode: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onDetail: () => void;
}) {
  const score = thumb.click_score ?? 0;
  const scoreColor =
    score >= 8
      ? "bg-green-100 text-green-700"
      : score >= 5
      ? "bg-yellow-100 text-yellow-700"
      : "bg-red-100 text-red-700";

  const colors = thumb.dominant_colors?.colors ?? [];

  return (
    <div
      onClick={compareMode ? onToggle : onDetail}
      className={`overflow-hidden rounded-lg border bg-white transition-all hover:shadow-md cursor-pointer ${
        isSelected
          ? "border-purple-500 ring-2 ring-purple-200"
          : "border-gray-200"
      }`}
    >
      <div className="aspect-video bg-gray-100 relative">
        <img
          src={thumb.image_url}
          alt="サムネイル"
          className="h-full w-full object-cover"
          onError={(e) => { (e.target as HTMLImageElement).src = '/globe.svg'; }}
        />
        <span
          className={`absolute top-2 right-2 rounded-full px-2.5 py-0.5 text-sm font-bold ${scoreColor}`}
        >
          {score}/10
        </span>
      </div>
      <div className="p-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">構図タイプ</span>
            <span className="font-medium text-gray-700">{thumb.composition_type ?? "未分析"}</span>
          </div>
          {thumb.text_overlay && (
            <div className="text-xs">
              <span className="text-gray-500">テキスト: </span>
              <span className="text-gray-700">{thumb.text_overlay}</span>
            </div>
          )}
          {thumb.face_count != null && thumb.face_count > 0 && (
            <div className="text-xs">
              <span className="text-gray-500">顔検出: </span>
              <span className="text-gray-700">{thumb.face_count}人 {thumb.emotion && `(${thumb.emotion})`}</span>
            </div>
          )}
          {colors.length > 0 && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-xs text-gray-500 mr-1">配色:</span>
              {colors.map((c, i) => (
                <span
                  key={i}
                  className="inline-block h-5 w-5 rounded-full border border-gray-200"
                  style={{ backgroundColor: c.hex }}
                  title={c.name}
                />
              ))}
            </div>
          )}
          {thumb.analysis_raw?.comment && (
            <p className="text-xs text-gray-600 mt-2 line-clamp-3">{thumb.analysis_raw.comment}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function CompareCard({ thumb }: { thumb: ThumbnailAnalysis }) {
  const score = thumb.click_score ?? 0;
  const scoreColor =
    score >= 8 ? "text-green-700" : score >= 5 ? "text-yellow-700" : "text-red-700";
  const colors = thumb.dominant_colors?.colors ?? [];

  return (
    <div className="rounded-lg border border-purple-200 bg-white overflow-hidden">
      <div className="aspect-video bg-gray-100">
        <img
          src={thumb.image_url}
          alt="サムネイル"
          className="h-full w-full object-cover"
          onError={(e) => { (e.target as HTMLImageElement).src = '/globe.svg'; }}
        />
      </div>
      <div className="p-3">
        <div className="mt-2 space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Click Score</span>
            <span className={`font-bold ${scoreColor}`}>{score}/10</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">構図</span>
            <span className="text-gray-700">{thumb.composition_type ?? "-"}</span>
          </div>
          {colors.length > 0 && (
            <div className="flex items-center gap-1 mt-1">
              {colors.map((c, i) => (
                <span
                  key={i}
                  className="inline-block h-4 w-4 rounded-full border border-gray-200"
                  style={{ backgroundColor: c.hex }}
                  title={c.name}
                />
              ))}
            </div>
          )}
          {thumb.analysis_raw?.comment && (
            <p className="text-gray-600 mt-1 line-clamp-2">{thumb.analysis_raw.comment}</p>
          )}
        </div>
      </div>
    </div>
  );
}
