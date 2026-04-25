"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "ダッシュボード", href: "/", icon: "📊" },
  { name: "STEP1 コンセプト設定", href: "/onboarding", icon: "🎨" },
  { name: "STEP2 リサーチ", href: "/pipeline", icon: "🔍" },
  { name: "STEP3 企画提案", href: "/planning", icon: "🎯" },
  { name: "STEP4 台本生成", href: "/scripts/new", icon: "✨" },
  { name: "台本一覧", href: "/scripts", icon: "📝" },
  { name: "ナレッジ", href: "/knowledge", icon: "📚" },
  { name: "知識を追加", href: "/knowledge/upload", icon: "➕" },
  { name: "プロジェクト", href: "/projects", icon: "📁" },
  { name: "管理者", href: "/admin", icon: "🔐" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
        <span className="text-xl font-bold text-gray-900">YouTube Tool</span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
