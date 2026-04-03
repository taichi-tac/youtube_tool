# YouTube運用支援WEBツール

YouTube動画の企画・台本作成・分析を包括的に支援するWEBアプリケーションです。キーワード調査から台本生成、サムネイル分析まで、YouTube運用に必要な機能をワンストップで提供します。

---

## 機能一覧

| 機能 | 説明 |
|------|------|
| プロジェクト管理 | チャンネル/シリーズ単位でプロジェクトを作成・管理 |
| キーワード調査 | YouTube向けキーワードの検索・提案・アルファベットスープ分析 |
| 動画検索・分析 | YouTube動画の検索・メタデータ収集・トランスクリプト取得 |
| 台本生成 | AIを活用した動画台本の自動生成・編集 |
| ナレッジベース | Markdownファイルのアップロード・ベクトル検索 |
| サムネイル分析 | サムネイル画像のAI分析・パターン比較 |
| 理論管理 | コンテンツ制作理論の管理・自動構築 |

---

## 技術スタック

### フロントエンド
- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **Tailwind CSS 4**
- **Supabase JS** (認証・データ取得)

### バックエンド
- **Python 3.12**
- **FastAPI**
- **SQLAlchemy** (async) + **asyncpg**
- **Alembic** (マイグレーション)
- **LangChain** + **Anthropic Claude** + **OpenAI** (AI処理)
- **Google API Client** (YouTube Data API)
- **Redis** (キャッシュ、オプション)

### インフラ
- **Vercel** (フロントエンドホスティング)
- **Railway** (バックエンドホスティング)
- **Supabase** (PostgreSQL + pgvector + 認証)

---

## ローカル開発セットアップ

### 前提条件
- Node.js 20+
- Python 3.12+
- Docker (オプション)

### 方法1: 個別起動

**バックエンド:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.production.example .env
# .env を編集して各APIキーを設定
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**フロントエンド:**
```bash
cd frontend
npm install
cp .env.production.example .env.local
# .env.local を編集して各キーを設定
npm run dev
```

### 方法2: Docker Compose

```bash
# バックエンド環境変数を設定
cp backend/.env.production.example backend/.env
# backend/.env を編集

# フロントエンド環境変数を設定
cp frontend/.env.production.example frontend/.env.local
# frontend/.env.local を編集

# 起動
docker compose up --build
```

- フロントエンド: http://localhost:3001
- バックエンド: http://localhost:8001
- API ドキュメント: http://localhost:8001/docs

---

## デプロイ手順

### バックエンド (Railway)

1. [Railway](https://railway.app/) でアカウント作成・プロジェクト作成
2. GitHubリポジトリを接続
3. Root Directory を `backend` に設定
4. 環境変数をRailwayダッシュボードで設定（`backend/.env.production.example` を参照）
5. デプロイは自動実行される（`railway.toml` と `Dockerfile` を使用）
6. デプロイ後のURLをメモ（フロントエンドの設定に必要）

### フロントエンド (Vercel)

1. [Vercel](https://vercel.com/) でアカウント作成
2. GitHubリポジトリをインポート
3. Root Directory を `frontend` に設定
4. 環境変数を設定:
   - `NEXT_PUBLIC_SUPABASE_URL` - SupabaseプロジェクトのURL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabaseの匿名キー
   - `NEXT_PUBLIC_API_URL` - RailwayのバックエンドURL
5. デプロイ実行

### デプロイ後の確認

```bash
# バックエンドヘルスチェック
curl https://your-backend.up.railway.app/health

# API ドキュメント確認
# https://your-backend.up.railway.app/docs
```

---

## 環境変数一覧

### フロントエンド (`frontend/.env.local`)

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | SupabaseプロジェクトURL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase匿名キー |
| `NEXT_PUBLIC_API_URL` | Yes | バックエンドAPIのURL |

### バックエンド (`backend/.env`)

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `SUPABASE_URL` | Yes | SupabaseプロジェクトURL |
| `SUPABASE_KEY` | Yes | Supabase匿名キー |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabaseサービスロールキー |
| `SUPABASE_DB_URL` | Yes | PostgreSQL接続URL |
| `YOUTUBE_API_KEY` | Yes | YouTube Data API v3キー |
| `ANTHROPIC_API_KEY` | Yes | Claude APIキー |
| `OPENAI_API_KEY` | Yes | OpenAI APIキー |
| `REDIS_URL` | No | Redis接続URL（キャッシュ用） |
| `CORS_ORIGINS` | Yes | CORS許可オリジン（カンマ区切り） |
| `DEV_MODE` | No | 開発モードフラグ（デフォルト: true） |

---

## API エンドポイント一覧

ベースURL: `/api/v1`

### プロジェクト (`/api/v1/projects`)
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/` | プロジェクト一覧取得 |
| POST | `/` | プロジェクト作成 |
| GET | `/{project_id}` | プロジェクト詳細取得 |
| PATCH | `/{project_id}` | プロジェクト更新 |
| DELETE | `/{project_id}` | プロジェクト削除 |

### キーワード (`/api/v1/keywords`)
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/{project_id}` | キーワード一覧取得 |
| POST | `/{project_id}` | キーワード追加 |
| PATCH | `/{project_id}/{keyword_id}` | キーワード更新 |
| POST | `/{project_id}/suggest` | キーワード提案 |
| POST | `/{project_id}/alphabet-soup` | アルファベットスープ分析 |

### 動画 (`/api/v1/videos`)
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/quota` | YouTube API クォータ確認 |
| POST | `/{project_id}/search` | 動画検索 |
| GET | `/{project_id}` | 動画一覧取得 |
| GET | `/{project_id}/{video_id}` | 動画詳細取得 |
| DELETE | `/{project_id}/{video_id}` | 動画削除 |

### 台本 (`/api/v1/scripts`)
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/{project_id}` | 台本一覧取得 |
| POST | `/{project_id}` | 台本作成 |
| POST | `/{project_id}/generate` | AI台本生成（SSE） |
| GET | `/{project_id}/{script_id}` | 台本詳細取得 |
| PATCH | `/{project_id}/{script_id}` | 台本更新 |
| DELETE | `/{project_id}/{script_id}` | 台本削除 |

### ナレッジ (`/api/v1/knowledge`)
| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/{project_id}` | ナレッジアップロード |
| POST | `/{project_id}/search` | ナレッジ検索 |

### サムネイル (`/api/v1/thumbnails`)
| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/{project_id}/analyze` | サムネイル分析 |
| GET | `/{project_id}/compare` | サムネイル比較 |
| GET | `/{project_id}` | サムネイル一覧取得 |
| PATCH | `/{project_id}/{thumbnail_id}` | サムネイル更新 |

### 理論 (`/api/v1/theories`)
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/{project_id}` | 理論一覧取得 |
| POST | `/{project_id}` | 理論作成 |
| GET | `/{project_id}/{theory_id}` | 理論詳細取得 |
| PATCH | `/{project_id}/{theory_id}` | 理論更新 |
| DELETE | `/{project_id}/{theory_id}` | 理論削除 |

### ヘルスチェック
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/health` | サーバー稼働状態確認 |

---

## ライセンス

Private
