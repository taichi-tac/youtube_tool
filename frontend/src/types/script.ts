/** バックエンド ScriptResponse に対応 */
export interface Script {
  id: string;
  project_id: string;
  keyword_id: string | null;
  title: string;
  status: string;
  target_viewer: string | null;
  viewer_problem: string | null;
  promise: string | null;
  uniqueness: string | null;
  hook: string | null;
  body: string | null;
  closing: string | null;
  word_count: number | null;
  generation_model: string | null;
  prompt_version: string | null;
  used_knowledge: Record<string, unknown> | null;
  generation_cost: number | null;
  created_at: string;
  updated_at: string;
}

/** 台本生成リクエスト（バックエンド ScriptGenerateRequest に対応） */
export interface ScriptGenerateRequest {
  title: string;
  keyword_id?: string;
  target_viewer: string;
  viewer_problem?: string;
  promise?: string;
  uniqueness?: string;
  additional_context?: string;
  use_rag?: boolean;
  model_id?: string;
}

/** 台本作成リクエスト */
export interface ScriptCreateRequest {
  title: string;
  keyword_id?: string;
  target_viewer?: string;
  viewer_problem?: string;
  promise?: string;
  uniqueness?: string;
}

/** 台本更新リクエスト */
export interface ScriptUpdateRequest {
  title?: string;
  status?: string;
  target_viewer?: string;
  viewer_problem?: string;
  promise?: string;
  uniqueness?: string;
  hook?: string;
  body?: string;
  closing?: string;
  word_count?: number;
}

export type WizardStep = 1 | 2 | 3 | 4;
