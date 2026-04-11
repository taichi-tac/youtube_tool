"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { apiClient, getProjectId } from "@/lib/api-client";

interface KnowledgeModel {
  id: string;
  name: string;
  personal_knowledge: Record<string, string>;
  content_knowledge: Record<string, string>;
  product_knowledge: Record<string, string>;
  created_at: string;
}

export default function KnowledgePage() {
  const router = useRouter();
  const [models, setModels] = useState<KnowledgeModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const loadModels = async () => {
    setLoading(true);
    try {
      const pid = await getProjectId();
      const data = await apiClient.get<KnowledgeModel[]>(`/api/v1/models/${pid}`);
      setModels(data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { loadModels(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const pid = await getProjectId();
      const model = await apiClient.post<KnowledgeModel>(`/api/v1/models/${pid}`, { name: newName });
      router.push(`/knowledge/${model.id}`);
    } catch (err) {
      alert("作成に失敗: " + (err instanceof Error ? err.message : ""));
    } finally { setCreating(false); }
  };

  const handleDelete = async (modelId: string) => {
    if (!confirm("このモデルを削除しますか？")) return;
    try {
      const pid = await getProjectId();
      await apiClient.delete(`/api/v1/models/${pid}/${modelId}`);
      setModels(models.filter(m => m.id !== modelId));
    } catch { /* ignore */ }
  };

  const filledCount = (obj: Record<string, string>) => Object.values(obj || {}).filter(v => v && v.trim()).length;

  return (
    <div>
      <PageHeader title="ナレッジ" description="モデルごとにパーソナル/コンテンツ/プロダクトのナレッジを管理"
        actions={<button onClick={() => setShowCreate(true)} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">+ モデルを作成</button>} />

      {showCreate && (
        <div className="mb-6 rounded-xl border-2 border-blue-200 bg-blue-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-blue-900">新しいモデルを作成</h3>
          <div className="flex gap-2">
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
              placeholder="モデル名（例: 恋愛コーチ太郎）"
              className="flex-1 rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && handleCreate()} />
            <button onClick={handleCreate} disabled={creating || !newName.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{creating ? "作成中..." : "作成"}</button>
            <button onClick={() => { setShowCreate(false); setNewName(""); }}
              className="rounded-lg border px-3 py-2 text-sm text-gray-600">キャンセル</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-gray-500">読み込み中...</div>
      ) : models.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-16 text-center">
          <div className="mb-4 text-5xl">🧠</div>
          <h3 className="text-lg font-semibold text-gray-700">モデルがまだありません</h3>
          <p className="mt-2 text-sm text-gray-500">モデルを作成して、パーソナル情報やプロダクト情報を登録しましょう。</p>
          <button onClick={() => setShowCreate(true)} className="mt-4 rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700">最初のモデルを作成</button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <div key={model.id} className="rounded-xl border bg-white p-5 hover:shadow-md transition-shadow">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-900">{model.name}</h3>
                <button onClick={() => handleDelete(model.id)} className="text-xs text-red-400 hover:text-red-600">削除</button>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between rounded bg-purple-50 px-3 py-1.5">
                  <span className="text-purple-700">パーソナル</span>
                  <span className="font-medium text-purple-900">{filledCount(model.personal_knowledge)}/12項目</span>
                </div>
                <div className="flex items-center justify-between rounded bg-blue-50 px-3 py-1.5">
                  <span className="text-blue-700">コンテンツ</span>
                  <span className="font-medium text-blue-900">{filledCount(model.content_knowledge)}/3項目</span>
                </div>
                <div className="flex items-center justify-between rounded bg-green-50 px-3 py-1.5">
                  <span className="text-green-700">プロダクト</span>
                  <span className="font-medium text-green-900">{filledCount(model.product_knowledge)}/13項目</span>
                </div>
              </div>
              <button onClick={() => router.push(`/knowledge/${model.id}`)}
                className="mt-4 w-full rounded-lg border border-blue-300 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50">編集する</button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 rounded-lg bg-gray-50 p-4">
        <p className="text-xs text-gray-500">💡 和理論ナレッジ（192チャンク）は全モデル共通で台本生成時に常に参照されます。</p>
      </div>
    </div>
  );
}
