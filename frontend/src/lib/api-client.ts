import { supabase } from "@/lib/supabase";

// バックエンドURL（環境変数またはデフォルト）
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/** プロジェクトIDキャッシュ */
let _cachedProjectId: string | null = null;

/**
 * ユーザーのプロジェクトIDを取得する。
 * プロジェクトがなければ自動で「マイチャンネル」を作成する。
 */
export async function getProjectId(): Promise<string> {
  if (_cachedProjectId) return _cachedProjectId;

  try {
    const projects = await apiClient.get<{ id: string }[]>("/api/v1/projects/");
    if (projects.length > 0) {
      _cachedProjectId = projects[0].id;
      return _cachedProjectId;
    }

    // プロジェクトがなければ自動作成
    const newProject = await apiClient.post<{ id: string }>("/api/v1/projects/", {
      name: "マイチャンネル",
      genre: "YouTube運用",
    });
    _cachedProjectId = newProject.id;
    return _cachedProjectId;
  } catch {
    // フォールバック
    return "00000000-0000-0000-0000-000000000002";
  }
}

/** 開発用固定値（後方互換） */
export const PROJECT_ID = "00000000-0000-0000-0000-000000000002";

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

/**
 * Supabase Authのアクセストークンを取得する。
 * セッションがない場合はundefinedを返す。
 */
async function getAccessToken(): Promise<string | undefined> {
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token;
  } catch {
    return undefined;
  }
}

/**
 * 認証ヘッダーを生成する。
 * アクセストークンがある場合は Authorization: Bearer {token} を返す。
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(path, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }
    return url.toString();
  }

  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const authHeaders = await getAuthHeaders();
    const res = await fetch(this.buildUrl(path, params), {
      ...fetchOptions,
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...fetchOptions?.headers,
      },
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API Error: ${res.status} ${res.statusText} ${text}`);
    }
    return res.json();
  }

  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const authHeaders = await getAuthHeaders();
    const res = await fetch(this.buildUrl(path, params), {
      ...fetchOptions,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...fetchOptions?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API Error: ${res.status} ${res.statusText} ${text}`);
    }
    return res.json();
  }

  async patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const authHeaders = await getAuthHeaders();
    const res = await fetch(this.buildUrl(path, params), {
      ...fetchOptions,
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...fetchOptions?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API Error: ${res.status} ${res.statusText} ${text}`);
    }
    return res.json();
  }

  async delete(path: string, options?: RequestOptions): Promise<void> {
    const { params, ...fetchOptions } = options || {};
    const authHeaders = await getAuthHeaders();
    const res = await fetch(this.buildUrl(path, params), {
      ...fetchOptions,
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...fetchOptions?.headers,
      },
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API Error: ${res.status} ${res.statusText} ${text}`);
    }
  }

  /**
   * SSEストリーミング用: POSTリクエストを送り、ReadableStreamを返す。
   * EventSourceはGETのみ対応のため、fetch + ReadableStreamで実装。
   */
  async postStream(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<Response> {
    const { params, ...fetchOptions } = options || {};
    const authHeaders = await getAuthHeaders();
    const res = await fetch(this.buildUrl(path, params), {
      ...fetchOptions,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...authHeaders,
        ...fetchOptions?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API Error: ${res.status} ${res.statusText} ${text}`);
    }
    return res;
  }

  /** SSEイベントストリームをパースするユーティリティ */
  async *parseSSE(
    response: Response,
  ): AsyncGenerator<{ event: string; data: string }> {
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Response body is null");

    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent = "message";
    let currentData = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            currentData += (currentData ? "\n" : "") + line.slice(5).trim();
          } else if (line.trim() === "") {
            if (currentData) {
              yield { event: currentEvent, data: currentData };
            }
            currentEvent = "message";
            currentData = "";
          }
        }
      }
      // バッファに残ったデータも処理
      if (currentData) {
        yield { event: currentEvent, data: currentData };
      }
    } finally {
      reader.releaseLock();
    }
  }

  getUrl(path: string, params?: Record<string, string>): string {
    return this.buildUrl(path, params);
  }
}

export const apiClient = new ApiClient(BASE_URL);
export default apiClient;
