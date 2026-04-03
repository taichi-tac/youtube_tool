"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import { useKeywordSearch } from "@/hooks/useKeywordSearch";

export default function KeywordsPage() {
  const { keywords, suggestions, loading, error, fetchKeywords, suggest, saveKeyword } =
    useKeywordSearch();
  const [seedInput, setSeedInput] = useState("");
  const [savingKeyword, setSavingKeyword] = useState<string | null>(null);

  useEffect(() => {
    fetchKeywords();
  }, [fetchKeywords]);

  const handleSuggest = (e: React.FormEvent) => {
    e.preventDefault();
    if (seedInput.trim()) {
      suggest(seedInput.trim());
    }
  };

  const handleSave = async (suggestion: string) => {
    setSavingKeyword(suggestion);
    await saveKeyword(suggestion, seedInput.trim());
    setSavingKeyword(null);
  };

  return (
    <div>
      <PageHeader title="キーワード検索" description="YouTubeサジェストからキーワードを取得" />

      {/* シードキーワード入力 */}
      <form onSubmit={handleSuggest} className="mb-6 flex gap-3">
        <input
          type="text"
          value={seedInput}
          onChange={(e) => setSeedInput(e.target.value)}
          placeholder="シードキーワードを入力..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading || !seedInput.trim()}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "取得中..." : "サジェスト取得"}
        </button>
      </form>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* サジェスト結果 */}
      {suggestions.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">
            サジェスト結果 ({suggestions.length}件)
          </h2>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    キーワード
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {suggestions.map((s) => (
                  <tr key={s} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-900">{s}</td>
                    <td className="whitespace-nowrap px-6 py-3 text-right text-sm">
                      <button
                        onClick={() => handleSave(s)}
                        disabled={savingKeyword === s}
                        className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                      >
                        {savingKeyword === s ? "保存中..." : "保存"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 保存済みキーワード一覧 */}
      <h2 className="mb-3 text-sm font-semibold text-gray-900">
        保存済みキーワード ({keywords.length}件)
      </h2>
      {keywords.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
          保存済みキーワードがありません
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  キーワード
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  シード
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  ソース
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  選択
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {keywords.map((kw) => (
                <tr key={kw.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-3 text-sm font-medium text-gray-900">
                    {kw.keyword}
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-500">
                    {kw.seed_keyword || "-"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-500">
                    {kw.source}
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-sm">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        kw.is_selected
                          ? "bg-green-50 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {kw.is_selected ? "選択済" : "未選択"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
