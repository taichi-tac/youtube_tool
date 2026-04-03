import PageHeader from "@/components/layout/PageHeader";

export default async function KeywordDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div>
      <PageHeader title="キーワード詳細" description={`キーワードID: ${id}`} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">キーワード情報</h2>
            <div className="space-y-3 text-sm text-gray-600">
              <p>検索ボリューム、難易度、トレンド情報がここに表示されます。</p>
            </div>
          </div>
          <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">関連動画</h2>
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
              関連動画一覧がここに表示されます
            </div>
          </div>
        </div>
        <div>
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">関連キーワード</h2>
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
              関連キーワードがここに表示されます
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
