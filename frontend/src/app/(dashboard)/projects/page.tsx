import PageHeader from "@/components/layout/PageHeader";
import Link from "next/link";

export default function ProjectsPage() {
  return (
    <div>
      <PageHeader
        title="プロジェクト一覧"
        description="チャンネルごとのプロジェクト管理"
        actions={
          <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
            新規プロジェクト
          </button>
        }
      />
      <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
        <p className="text-sm text-gray-400">プロジェクトがまだありません</p>
        <p className="mt-1 text-xs text-gray-400">プロジェクトを作成してチャンネル設定を管理しましょう</p>
      </div>
    </div>
  );
}
