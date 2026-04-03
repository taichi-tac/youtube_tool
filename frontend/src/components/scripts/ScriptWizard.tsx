"use client";

/**
 * ScriptWizard is now integrated directly into scripts/new/page.tsx.
 * This component is kept as a placeholder for backwards compatibility.
 */

import type { WizardStep, ScriptGenerateRequest } from "@/types/script";
import { cn } from "@/lib/utils";

const steps: { step: WizardStep; label: string }[] = [
  { step: 1, label: "キーワード選択" },
  { step: 2, label: "外側設計" },
  { step: 3, label: "ナレッジ確認" },
  { step: 4, label: "生成実行" },
];

interface ScriptWizardProps {
  onGenerate: (request: ScriptGenerateRequest) => void;
  generating?: boolean;
  progress?: number;
}

export default function ScriptWizard({ generating, progress }: ScriptWizardProps) {
  return (
    <div className="mx-auto max-w-3xl text-center py-12 text-sm text-gray-500">
      このコンポーネントは scripts/new/page.tsx に統合されました。
    </div>
  );
}

export { steps, cn };
export type { ScriptWizardProps };
