import { formatNumber } from "@/lib/utils";

interface VideoTrendCardProps {
  title: string;
  channelName: string;
  viewCount: number;
  publishedAt: string;
  thumbnailUrl?: string;
}

export default function VideoTrendCard({
  title,
  channelName,
  viewCount,
  publishedAt,
  thumbnailUrl,
}: VideoTrendCardProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-md">
      <div className="aspect-video bg-gray-100">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt={title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-400">
            サムネイル
          </div>
        )}
      </div>
      <div className="p-4">
        <h3 className="line-clamp-2 text-sm font-medium text-gray-900">{title}</h3>
        <p className="mt-1 text-xs text-gray-500">{channelName}</p>
        <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
          <span>{formatNumber(viewCount)}回視聴</span>
          <span>{publishedAt}</span>
        </div>
      </div>
    </div>
  );
}
