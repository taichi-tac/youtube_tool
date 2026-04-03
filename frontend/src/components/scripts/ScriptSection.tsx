"use client";

/**
 * ScriptSection is now integrated directly into scripts/[id]/page.tsx
 * with hook/body/closing fields instead of the old sections array.
 * Kept as a placeholder for backwards compatibility.
 */

interface ScriptSectionProps {
  sectionType: string;
  title: string;
  content: string;
  onUpdate?: (content: string) => void;
}

const sectionTypeColor: Record<string, string> = {
  hook: "border-l-red-500",
  body: "border-l-blue-500",
  closing: "border-l-green-500",
};

export default function ScriptSection({ sectionType, title, content, onUpdate }: ScriptSectionProps) {
  return (
    <div className={`rounded-lg border border-gray-200 border-l-4 bg-white p-4 ${sectionTypeColor[sectionType] || "border-l-gray-400"}`}>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">{title}</span>
        <span className="text-xs text-gray-400">{content.length}文字</span>
      </div>
      <textarea
        value={content}
        onChange={(e) => onUpdate?.(e.target.value)}
        rows={6}
        className="w-full resize-none rounded border border-gray-200 p-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </div>
  );
}
