interface ThumbnailAnalysisCardProps {
  thumbnailUrl: string;
  title: string;
  overallScore: number;
  criteria: {
    name: string;
    score: number;
    feedback: string;
  }[];
}

export default function ThumbnailAnalysisCard({
  thumbnailUrl,
  title,
  overallScore,
  criteria,
}: ThumbnailAnalysisCardProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <div className="aspect-video bg-gray-100">
        <img src={thumbnailUrl} alt={title} className="h-full w-full object-cover" />
      </div>
      <div className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          <span className={`rounded-full px-2.5 py-0.5 text-sm font-bold ${
            overallScore >= 80 ? "bg-green-100 text-green-700" :
            overallScore >= 60 ? "bg-yellow-100 text-yellow-700" :
            "bg-red-100 text-red-700"
          }`}>
            {overallScore}点
          </span>
        </div>
        <div className="space-y-2">
          {criteria.map((c) => (
            <div key={c.name}>
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-gray-700">{c.name}</span>
                <span className="text-gray-500">{c.score}/100</span>
              </div>
              <div className="mt-0.5 h-1.5 rounded-full bg-gray-200">
                <div
                  className="h-1.5 rounded-full bg-blue-500"
                  style={{ width: `${c.score}%` }}
                />
              </div>
              <p className="mt-0.5 text-xs text-gray-400">{c.feedback}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
