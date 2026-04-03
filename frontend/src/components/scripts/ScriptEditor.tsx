"use client";

/**
 * ScriptEditor is now integrated directly into scripts/[id]/page.tsx.
 * This component is kept as a placeholder for backwards compatibility.
 */

import type { Script } from "@/types/script";

interface ScriptEditorProps {
  script: Script;
  onSave?: (script: Script) => void;
}

export default function ScriptEditor({ script }: ScriptEditorProps) {
  return (
    <div className="text-center py-12 text-sm text-gray-500">
      このコンポーネントは scripts/[id]/page.tsx に統合されました。
    </div>
  );
}

export type { ScriptEditorProps };
