"use client";

import type { Keyword } from "@/types/keyword";

interface KeywordResultTableProps {
  keywords: Keyword[];
}

export default function KeywordResultTable({ keywords }: KeywordResultTableProps) {
  if (keywords.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 p-8 text-center text-gray-500">
        キーワードが見つかりません
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">キーワード</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">シード</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ソース</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">選択</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {keywords.map((kw) => (
            <tr key={kw.id} className="hover:bg-gray-50">
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">{kw.keyword}</td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">{kw.seed_keyword || "-"}</td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">{kw.source}</td>
              <td className="whitespace-nowrap px-6 py-4 text-sm">
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${kw.is_selected ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {kw.is_selected ? "選択済" : "未選択"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
