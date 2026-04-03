interface Thumbnail {
  id: string;
  url: string;
  title: string;
  score?: number;
}

interface ThumbnailGridProps {
  thumbnails: Thumbnail[];
  onSelect?: (id: string) => void;
}

export default function ThumbnailGrid({ thumbnails, onSelect }: ThumbnailGridProps) {
  if (thumbnails.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-sm text-gray-400">
        サムネイルがありません
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {thumbnails.map((thumb) => (
        <div
          key={thumb.id}
          onClick={() => onSelect?.(thumb.id)}
          className="cursor-pointer overflow-hidden rounded-lg border border-gray-200 transition-shadow hover:shadow-md"
        >
          <div className="aspect-video bg-gray-100">
            <img src={thumb.url} alt={thumb.title} className="h-full w-full object-cover" />
          </div>
          <div className="p-3">
            <p className="text-sm font-medium text-gray-900 line-clamp-1">{thumb.title}</p>
            {thumb.score !== undefined && (
              <div className="mt-1 flex items-center gap-1">
                <div className="h-1.5 flex-1 rounded-full bg-gray-200">
                  <div
                    className="h-1.5 rounded-full bg-green-500"
                    style={{ width: `${thumb.score}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500">{thumb.score}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
