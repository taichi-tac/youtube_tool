import PageHeader from "@/components/layout/PageHeader";

const theories = [
  { id: "1", name: "PREP法", description: "Point, Reason, Example, Point の構成で論理的に伝える手法" },
  { id: "2", name: "ストーリーテリング", description: "物語形式で視聴者の感情に訴えかける手法" },
  { id: "3", name: "問題解決型", description: "問題提起から解決策を提示する構成" },
  { id: "4", name: "比較型", description: "A vs B の形式で比較しながら解説する手法" },
  { id: "5", name: "リスト型", description: "〇選、〇つの方法 などリスト形式で情報を整理する手法" },
];

export default function TheoriesPage() {
  return (
    <div>
      <PageHeader title="理論一覧" description="台本生成に使用できる構成理論" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {theories.map((theory) => (
          <div
            key={theory.id}
            className="rounded-lg border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md"
          >
            <h3 className="text-sm font-semibold text-gray-900">{theory.name}</h3>
            <p className="mt-2 text-xs text-gray-500">{theory.description}</p>
            <button className="mt-4 text-xs font-medium text-blue-600 hover:text-blue-800">
              詳細を見る
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
