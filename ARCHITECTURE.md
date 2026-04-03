# YouTube運用支援WEBツール アーキテクチャ設計書

**作成日**: 2026年4月2日
**バージョン**: 1.0
**対象読者**: 実装担当エンジニア、プロジェクトオーナー

---

## エグゼクティブサマリー

**アーキテクチャスタイル**: モジュラーモノリス（段階的マイクロサービス移行対応）
**MVP定義**: Stage 1 = キーワード検索 + 台本生成（4〜6週間で実装可能）
**対象スケール**: 受講生100〜500名、同時接続50名、月間API呼び出し5万回
**コスト試算（月額）**: Vercel無料枠 + Railway $20 + Supabase $25 + Claude API $50〜150 = **月額約$100〜200**

---

## アーキテクチャ決定記録（ADR-001）

### 決定: モジュラーモノリスを採用し、バックエンドをPython FastAPIの単一サービスとして構築する

**ステータス**: 採用

**背景**:
- 受講生は最大500名規模であり、マイクロサービスの運用コストに見合わない
- 機能が6フェーズに分かれているが、データ境界（動画→キーワード→台本）は密に連携する
- 実装チームは小規模（1〜2名）であり、複数サービスの運用は非現実的

**決定内容**:
- バックエンドは単一のFastAPIサービスとして構築し、内部をモジュール（routers/）で分離する
- 各モジュールは独立してテスト可能な設計とし、将来のマイクロサービス分割を妨げない
- フロントエンドはNext.js 15（App Router）として完全分離する

**却下した代替案**:
1. マイクロサービス: 運用コストが高すぎる。500名規模では過剰設計
2. フルスタックNext.js（API Routes）: Python LLM処理・YouTube API処理との統合が複雑になる

**結果**:
- メリット: デプロイ簡素、デバッグ容易、コスト最小
- トレードオフ: Stage 5以降でスケールアウトが必要になった時点でサービス分割を検討

---

## 1. ディレクトリ構造

```
youtube-tool/                          # モノレポルート
├── frontend/                          # Next.js 15 App Router
│   ├── src/
│   │   ├── app/                       # App Routerページ
│   │   │   ├── (auth)/               # 認証グループ
│   │   │   │   ├── login/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── layout.tsx
│   │   │   ├── (dashboard)/          # メインアプリグループ
│   │   │   │   ├── layout.tsx        # サイドバー・ヘッダー共通レイアウト
│   │   │   │   ├── page.tsx          # ダッシュボード（/）
│   │   │   │   ├── keywords/
│   │   │   │   │   ├── page.tsx      # キーワード検索・一覧
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx  # キーワード詳細・関連動画
│   │   │   │   ├── videos/
│   │   │   │   │   ├── page.tsx      # 動画一覧・フィルタ
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx  # 動画詳細・コメント分析
│   │   │   │   ├── scripts/
│   │   │   │   │   ├── page.tsx      # 台本一覧
│   │   │   │   │   ├── new/
│   │   │   │   │   │   └── page.tsx  # 台本生成ウィザード（Stage 1 MVP中核）
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx  # 台本編集・リライト
│   │   │   │   ├── knowledge/
│   │   │   │   │   ├── page.tsx      # ナレッジ一覧・検索
│   │   │   │   │   └── upload/
│   │   │   │   │       └── page.tsx  # mdファイルアップロード
│   │   │   │   ├── thumbnails/
│   │   │   │   │   └── page.tsx      # サムネ分析・パターン比較
│   │   │   │   ├── theories/
│   │   │   │   │   └── page.tsx      # 理論一覧・自動構築結果
│   │   │   │   └── projects/
│   │   │   │       ├── page.tsx      # プロジェクト一覧
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx  # プロジェクト設定
│   │   │   └── api/                  # Next.js API Routes（BFFのみ）
│   │   │       └── auth/
│   │   │           └── [...nextauth]/
│   │   │               └── route.ts  # NextAuth.js
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui ベースコンポーネント
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── textarea.tsx
│   │   │   │   └── progress.tsx
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── PageHeader.tsx
│   │   │   ├── keywords/
│   │   │   │   ├── KeywordSearchForm.tsx    # シードキーワード入力
│   │   │   │   ├── KeywordResultTable.tsx   # 検索結果テーブル
│   │   │   │   └── VideoTrendCard.tsx       # 伸びてる動画カード
│   │   │   ├── scripts/
│   │   │   │   ├── ScriptWizard.tsx         # 企画→台本生成ウィザード
│   │   │   │   ├── ScriptEditor.tsx         # 台本リライトエディタ
│   │   │   │   ├── ScriptSection.tsx        # 台本セクション単位表示
│   │   │   │   └── KnowledgePanel.tsx       # RAG参照ナレッジ表示
│   │   │   ├── knowledge/
│   │   │   │   ├── KnowledgeCard.tsx
│   │   │   │   └── KnowledgeSearch.tsx
│   │   │   └── thumbnails/
│   │   │       ├── ThumbnailGrid.tsx
│   │   │       └── ThumbnailAnalysisCard.tsx
│   │   ├── hooks/
│   │   │   ├── useKeywordSearch.ts
│   │   │   ├── useScriptGeneration.ts       # ストリーミングSSE対応
│   │   │   ├── useKnowledgeSearch.ts
│   │   │   └── useVideoAnalysis.ts
│   │   ├── lib/
│   │   │   ├── api-client.ts                # FastAPI呼び出しクライアント
│   │   │   ├── supabase.ts                  # Supabase クライアント
│   │   │   └── utils.ts
│   │   └── types/
│   │       ├── keyword.ts
│   │       ├── video.ts
│   │       ├── script.ts
│   │       └── knowledge.ts
│   ├── public/
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── components.json                      # shadcn/ui設定
│   └── package.json
│
├── backend/                           # Python FastAPI
│   ├── app/
│   │   ├── main.py                    # FastAPIアプリ起動点
│   │   ├── core/
│   │   │   ├── config.py              # 環境変数・設定管理（pydantic-settings）
│   │   │   ├── database.py            # Supabase/PostgreSQL接続
│   │   │   ├── security.py            # JWT検証・認証ミドルウェア
│   │   │   └── quota_manager.py       # YouTube APIクォータ管理
│   │   ├── routers/                   # APIエンドポイント定義
│   │   │   ├── keywords.py            # /api/v1/keywords/*
│   │   │   ├── videos.py              # /api/v1/videos/*
│   │   │   ├── scripts.py             # /api/v1/scripts/*
│   │   │   ├── knowledge.py           # /api/v1/knowledge/*
│   │   │   ├── thumbnails.py          # /api/v1/thumbnails/*
│   │   │   ├── theories.py            # /api/v1/theories/*
│   │   │   └── projects.py            # /api/v1/projects/*
│   │   ├── services/                  # ビジネスロジック層
│   │   │   ├── youtube_service.py     # YouTube Data API v3ラッパー
│   │   │   ├── keyword_service.py     # キーワード抽出・アルファベットスープ法
│   │   │   ├── script_service.py      # 台本生成（Claude API）
│   │   │   ├── rag_service.py         # RAGパイプライン（LangChain + pgvector）
│   │   │   ├── thumbnail_service.py   # サムネイル取得・Claude Vision分析
│   │   │   ├── comment_service.py     # コメント取得・ニーズ抽出
│   │   │   └── theory_service.py      # 理論自動構築
│   │   ├── models/                    # SQLAlchemy ORMモデル
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── keyword.py
│   │   │   ├── video.py
│   │   │   ├── script.py
│   │   │   ├── knowledge_chunk.py
│   │   │   ├── thumbnail.py
│   │   │   └── theory.py
│   │   ├── schemas/                   # Pydantic リクエスト/レスポンス定義
│   │   │   ├── keyword.py
│   │   │   ├── video.py
│   │   │   ├── script.py
│   │   │   ├── knowledge.py
│   │   │   └── theory.py
│   │   ├── tasks/                     # バックグラウンドタスク（将来のCelery移行点）
│   │   │   ├── keyword_crawl.py       # キーワード網羅的収集（非同期）
│   │   │   ├── video_batch.py         # 動画バッチ取得
│   │   │   └── knowledge_ingest.py    # mdファイルインジェスト
│   │   └── utils/
│   │       ├── cache.py               # Redis キャッシュラッパー
│   │       ├── text_splitter.py       # LangChain MarkdownTextSplitter
│   │       └── prompt_builder.py      # Claudeプロンプトテンプレート管理
│   ├── migrations/                    # Alembic DBマイグレーション
│   │   └── versions/
│   ├── tests/
│   │   ├── test_keyword_service.py
│   │   ├── test_script_service.py
│   │   └── test_rag_service.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.toml
│
├── supabase/                          # Supabase設定・SQLマイグレーション
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_pgvector_extension.sql
│   │   └── 003_rls_policies.sql
│   └── seed/
│       └── knowledge_seed.sql         # 和理論・市場分析の初期ナレッジ
│
├── docs/
│   ├── ARCHITECTURE.md               # 本ドキュメント
│   ├── adr/
│   │   ├── 001-architecture-style.md
│   │   ├── 002-database-selection.md
│   │   └── 003-llm-strategy.md
│   └── api/
│       └── openapi.yaml              # FastAPI自動生成
│
├── .env.example
├── docker-compose.yml                # ローカル開発環境（PostgreSQL + Redis）
└── README.md
```

---

## 2. データベーススキーマ設計

### 設計方針
- Supabase（PostgreSQL 15 + pgvector拡張）を使用
- pgvector: `knowledge_chunks`の埋め込みベクトル（1536次元、OpenAI text-embedding-3-small）
- Row Level Security (RLS) をSupabase側で設定し、ユーザーデータを完全分離
- `updated_at` は全テーブルにトリガーで自動更新

```sql
-- =============================================
-- 拡張機能
-- =============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- users（ユーザー管理）
-- Supabase Authと連携
-- =============================================
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  auth_id       UUID UNIQUE NOT NULL,        -- Supabase Auth の user.id と紐付け
  email         TEXT UNIQUE NOT NULL,
  display_name  TEXT,
  plan          TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'pro')),
  quota_used    INTEGER NOT NULL DEFAULT 0,  -- 当月のAPI呼び出し消費数
  quota_limit   INTEGER NOT NULL DEFAULT 100,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================
-- projects（プロジェクト / チャンネル単位）
-- 受講生が複数チャンネルを持つケースに対応
-- =============================================
CREATE TABLE projects (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  channel_id      TEXT,                    -- YouTube チャンネルID（オプション）
  channel_url     TEXT,
  genre           TEXT,                    -- 市場ジャンル（例: ビジネス, 副業）
  target_audience TEXT,                    -- ターゲット辞書からの参照
  concept         TEXT,                    -- 1行契約・コンセプト
  center_pin      TEXT,                    -- センターピン
  settings        JSONB NOT NULL DEFAULT '{}', -- フェーズA設計情報を格納
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================
-- keywords（抽出されたキーワード）
-- アルファベットスープ法で収集したサジェストキーワード
-- =============================================
CREATE TABLE keywords (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  keyword         TEXT NOT NULL,
  seed_keyword    TEXT NOT NULL,           -- 起点となったシードキーワード
  source          TEXT NOT NULL DEFAULT 'youtube_suggest'
                  CHECK (source IN ('youtube_suggest', 'manual', 'related')),
  search_volume   INTEGER,                 -- 推定検索ボリューム（将来: SerpAPI等から取得）
  competition     NUMERIC(3,2),            -- 競合度 0.00〜1.00
  trend_score     NUMERIC(5,2),            -- トレンドスコア（pytrends等から算出）
  is_selected     BOOLEAN NOT NULL DEFAULT FALSE, -- ユーザーが選択したキーワード
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (project_id, keyword)
);

CREATE INDEX idx_keywords_project_id ON keywords(project_id);
CREATE INDEX idx_keywords_trend_score ON keywords(trend_score DESC);

-- =============================================
-- videos（分析した動画データ）
-- YouTube Data API v3 から取得した動画情報
-- =============================================
CREATE TABLE videos (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  youtube_video_id  TEXT NOT NULL UNIQUE,
  title             TEXT NOT NULL,
  channel_id        TEXT NOT NULL,
  channel_title     TEXT NOT NULL,
  description       TEXT,
  published_at      TIMESTAMPTZ NOT NULL,
  view_count        BIGINT NOT NULL DEFAULT 0,
  like_count        BIGINT,
  comment_count     INTEGER,
  duration_seconds  INTEGER,
  thumbnail_url     TEXT,

  -- 計算・分析フィールド
  views_per_day     NUMERIC(10,2),          -- 再生数/経過日数（伸び速度指標）
  is_trending       BOOLEAN NOT NULL DEFAULT FALSE, -- 半年以内に伸びてる判定
  keyword_id        UUID REFERENCES keywords(id), -- どのキーワード検索で見つかったか

  -- サムネイル分析結果（Claude Vision）
  thumbnail_analysis JSONB,               -- 構図, 色, テキスト, 感情スコア等

  fetched_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_videos_project_id ON videos(project_id);
CREATE INDEX idx_videos_published_at ON videos(published_at DESC);
CREATE INDEX idx_videos_views_per_day ON videos(views_per_day DESC);
CREATE INDEX idx_videos_trending ON videos(is_trending) WHERE is_trending = TRUE;

-- =============================================
-- video_comments（コメントデータ）
-- ニーズ抽出・ランキング化に使用
-- =============================================
CREATE TABLE video_comments (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  video_id              UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  youtube_comment_id    TEXT NOT NULL UNIQUE,
  author_name           TEXT,
  text                  TEXT NOT NULL,
  like_count            INTEGER NOT NULL DEFAULT 0,
  published_at          TIMESTAMPTZ,

  -- LLM分析フィールド
  need_category         TEXT,             -- 抽出されたニーズカテゴリ
  sentiment             TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', 'question')),
  is_question           BOOLEAN NOT NULL DEFAULT FALSE,
  extracted_needs       JSONB,            -- ニーズ抽出の詳細JSON

  fetched_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_video_comments_video_id ON video_comments(video_id);
CREATE INDEX idx_video_comments_like_count ON video_comments(like_count DESC);
CREATE INDEX idx_video_comments_need ON video_comments(need_category);

-- =============================================
-- knowledge_chunks（ナレッジのチャンク + ベクトル）
-- 和理論・市場分析・第二の脳のmdファイルをRAG用に分割・ベクトル化
-- =============================================
CREATE TABLE knowledge_chunks (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE, -- NULLの場合は全ユーザー共有
  source_file     TEXT NOT NULL,          -- 元のmdファイル名（例: MOC_YouTube和理論_全体.md）
  source_type     TEXT NOT NULL CHECK (source_type IN (
                    'wa_theory',          -- 和理論
                    'market_analysis',    -- 市場分析
                    'second_brain',       -- 第二の脳
                    'user_upload'         -- ユーザーがアップロードしたmd
                  )),
  chunk_index     INTEGER NOT NULL,       -- ファイル内のチャンク順序
  content         TEXT NOT NULL,          -- チャンクのテキスト本文
  metadata        JSONB NOT NULL DEFAULT '{}', -- 見出し・タグ等のメタデータ
  embedding       vector(1536),           -- OpenAI text-embedding-3-small
  token_count     INTEGER,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_file, chunk_index)
);

-- pgvector IVFFlat インデックス（100チャンク以上になったら有効化）
CREATE INDEX idx_knowledge_chunks_embedding
  ON knowledge_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX idx_knowledge_chunks_source_type ON knowledge_chunks(source_type);
CREATE INDEX idx_knowledge_chunks_project_id ON knowledge_chunks(project_id);

-- =============================================
-- scripts（生成された台本）
-- 企画→台本の生成結果と編集履歴
-- =============================================
CREATE TABLE scripts (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id       UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  keyword_id       UUID REFERENCES keywords(id),     -- 起点キーワード
  title            TEXT NOT NULL,                    -- 動画タイトル案
  status           TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft', 'generating', 'completed', 'archived')),

  -- 外側設計（フェーズB準拠）
  target_viewer    TEXT,                             -- 対象視聴者
  viewer_problem   TEXT,                             -- 視聴者の問題
  promise          TEXT,                             -- 約束（タイトルの機能）
  uniqueness       TEXT,                             -- 独自性の匂い

  -- 台本本文（構造化）
  hook             TEXT,                             -- 冒頭フック（〜3000文字）
  body             TEXT,                             -- 本編（〜25000文字）
  closing          TEXT,                             -- クロージング・CTA

  -- メタデータ
  word_count       INTEGER,
  generation_model TEXT DEFAULT 'claude-sonnet-4-6',
  prompt_version   TEXT,                             -- プロンプトバージョン管理
  used_knowledge   JSONB,                            -- RAGで参照したナレッジIDリスト
  generation_cost  NUMERIC(8,4),                    -- 生成コスト（USD）

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scripts_project_id ON scripts(project_id);
CREATE INDEX idx_scripts_status ON scripts(status);

-- =============================================
-- thumbnails（サムネイル分析結果）
-- Claude Vision による構造的分析
-- =============================================
CREATE TABLE thumbnails (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  video_id          UUID REFERENCES videos(id) ON DELETE SET NULL,
  project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  image_url         TEXT NOT NULL,
  source_type       TEXT NOT NULL CHECK (source_type IN ('competitor', 'user_upload', 'generated_idea')),

  -- Claude Vision 分析結果
  has_face          BOOLEAN,
  face_emotion      TEXT,
  text_elements     JSONB,               -- テキスト要素の位置・内容
  dominant_colors   JSONB,               -- 主要色（hex + 割合）
  composition_type  TEXT,                -- 構図パターン（full_face, split, text_only等）
  ctr_elements      JSONB,               -- CTR向上要素の評価
  overall_score     NUMERIC(3,1),        -- 総合CTRスコア（1〜10）
  analysis_notes    TEXT,                -- Claude Visionのフリーテキスト分析

  analyzed_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_thumbnails_project_id ON thumbnails(project_id);
CREATE INDEX idx_thumbnails_overall_score ON thumbnails(overall_score DESC);

-- =============================================
-- theories（自動構築された理論）
-- マーケ本・データから抽出・蓄積された理論
-- =============================================
CREATE TABLE theories (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE, -- NULLは全体共有
  title           TEXT NOT NULL,
  category        TEXT NOT NULL CHECK (category IN (
                    'content_strategy',   -- コンテンツ戦略
                    'audience_psychology',-- 視聴者心理
                    'market_analysis',    -- 市場分析
                    'script_structure',   -- 台本構造
                    'thumbnail_design',   -- サムネイル設計
                    'channel_concept'     -- チャンネルコンセプト
                  )),
  body            TEXT NOT NULL,          -- 理論の本文
  source_type     TEXT NOT NULL CHECK (source_type IN ('manual', 'llm_generated', 'data_derived')),
  source_ref      TEXT,                   -- 出典（書籍名・URLなど）
  evidence        JSONB,                  -- 根拠となるデータ・事例
  confidence      NUMERIC(3,2) DEFAULT 0.5, -- 信頼度スコア 0.0〜1.0
  usage_count     INTEGER NOT NULL DEFAULT 0, -- RAGで参照された回数
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_theories_category ON theories(category);
CREATE INDEX idx_theories_usage ON theories(usage_count DESC);

-- =============================================
-- RLS（Row Level Security）ポリシー設定例
-- =============================================
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ユーザーは自分のプロジェクトのみ参照"
  ON projects FOR ALL
  USING (user_id = (SELECT id FROM users WHERE auth_id = auth.uid()));

ALTER TABLE scripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ユーザーは自分のプロジェクトの台本のみ参照"
  ON scripts FOR ALL
  USING (project_id IN (
    SELECT id FROM projects WHERE user_id = (
      SELECT id FROM users WHERE auth_id = auth.uid()
    )
  ));
```

---

## 3. APIエンドポイント設計

### 設計方針
- ベースURL: `https://api.youtube-tool.railway.app/api/v1`
- 認証: Bearer JWT（Supabase AuthトークンをFastAPIミドルウェアで検証）
- ストリーミング: 台本生成は Server-Sent Events (SSE) で逐次返却
- クォータ保護: `quota_manager.py` がユーザー単位の呼び出し制限を管理

```
# =============================================
# キーワード関連
# =============================================
GET    /keywords
  クエリ: project_id, limit, offset, sort_by(trend_score|search_volume)
  概要: プロジェクトのキーワード一覧取得

POST   /keywords/extract
  ボディ: { project_id, seed_keyword, depth(1-3), max_results(50-500) }
  概要: アルファベットスープ法でキーワード網羅的抽出（バックグラウンドタスク起動）
  注意: YouTube Suggest非公式APIを使用。クォータ消費なし

GET    /keywords/suggest
  クエリ: q（シードキーワード）
  概要: YouTubeサジェストをリアルタイム取得（単発検索）

POST   /keywords/{id}/select
  概要: キーワードを台本生成対象として選択/解除

DELETE /keywords/{id}
  概要: キーワード削除

# =============================================
# 動画分析関連
# =============================================
GET    /videos
  クエリ: project_id, keyword_id, is_trending, published_after, limit, offset
  概要: 動画一覧取得（半年以内伸び動画フィルタ対応）

POST   /videos/search
  ボディ: { project_id, keyword_id, published_after, max_results(10-50) }
  概要: YouTube Data API search.list を呼び出し動画取得
  クォータ: 1回あたり100ユニット消費。呼び出し前にクォータ確認

POST   /videos/batch-stats
  ボディ: { video_ids: string[] }
  概要: videos.list で最大50件の統計を一括取得（1ユニット/50件）

GET    /videos/{id}
  概要: 動画詳細取得（サムネイル分析結果含む）

# =============================================
# コメント分析関連
# =============================================
GET    /videos/{id}/comments
  クエリ: limit, offset, sentiment, need_category
  概要: 動画のコメント一覧取得（分析結果付き）

POST   /videos/{id}/comments/fetch
  概要: YouTube API commentThreads.list でコメント取得・保存

POST   /videos/{id}/comments/analyze
  概要: 保存済みコメントをClaude APIでニーズ分析・カテゴリ分類

GET    /videos/{id}/comments/needs-ranking
  概要: コメントから抽出したニーズをランキング形式で返却

# =============================================
# 台本生成関連（Stage 1 MVP中核）
# =============================================
GET    /scripts
  クエリ: project_id, status, limit, offset
  概要: 台本一覧取得

POST   /scripts
  ボディ: { project_id, keyword_id, title, target_viewer, viewer_problem, promise, uniqueness }
  概要: 台本レコード作成（生成前の外側設計入力）

POST   /scripts/{id}/generate
  ボディ: { sections: ['hook', 'body', 'closing'], rag_enabled: bool }
  概要: Claude APIで台本生成開始。SSEでストリーミング返却
  注意: rag_enabled=trueの場合、pgvectorで和理論・市場分析を検索してコンテキストに付与

GET    /scripts/{id}/stream
  概要: SSE エンドポイント。生成中の台本をリアルタイムストリーミング

PUT    /scripts/{id}
  ボディ: { title, hook, body, closing, ... }
  概要: 台本編集・保存

POST   /scripts/{id}/rewrite-section
  ボディ: { section: 'hook'|'body'|'closing', instruction: string }
  概要: 指定セクションをClaude APIでリライト（受講生向け簡易編集）

DELETE /scripts/{id}
  概要: 台本削除

# =============================================
# ナレッジ管理（RAG）
# =============================================
GET    /knowledge
  クエリ: project_id, source_type, q(セマンティック検索), limit
  概要: ナレッジ一覧 or セマンティック検索

POST   /knowledge/ingest
  ボディ: multipart/form-data（mdファイル）
  概要: mdファイルをアップロード→チャンク分割→ベクトル化→pgvector保存

POST   /knowledge/search
  ボディ: { query, source_types: string[], limit: 5 }
  概要: pgvector cosine類似度でナレッジ検索（RAG内部でも使用）

DELETE /knowledge/{id}
  概要: ナレッジチャンク削除

# =============================================
# サムネイル分析
# =============================================
GET    /thumbnails
  クエリ: project_id, source_type, limit, sort_by(overall_score)
  概要: サムネイル一覧（スコア付き）

POST   /thumbnails/analyze
  ボディ: { video_ids: string[] } or { image_urls: string[] }
  概要: Claude Vision APIでサムネイル一括分析

GET    /thumbnails/{id}
  概要: サムネイル分析詳細

# =============================================
# 理論管理
# =============================================
GET    /theories
  クエリ: category, project_id, limit
  概要: 理論一覧取得

POST   /theories
  ボディ: { title, category, body, source_ref }
  概要: 手動で理論を追加

POST   /theories/auto-build
  ボディ: { source_text, category }
  概要: マーケ本やデータテキストからClaude APIで理論を自動抽出・構造化

PUT    /theories/{id}
  概要: 理論更新

# =============================================
# プロジェクト管理
# =============================================
GET    /projects
  概要: ユーザーのプロジェクト一覧

POST   /projects
  ボディ: { name, channel_url, genre, target_audience, concept }
  概要: 新規プロジェクト作成

GET    /projects/{id}
  概要: プロジェクト詳細（フェーズA設計情報含む）

PUT    /projects/{id}
  概要: プロジェクト設定更新（コンセプト・センターピン等）

DELETE /projects/{id}
  概要: プロジェクト削除

# =============================================
# クォータ・使用状況
# =============================================
GET    /quota/status
  概要: YouTube APIクォータ残量・当月使用状況を返却
  レスポンス: { used, limit, reset_at, breakdown_by_operation }
```

---

## 4. フロントエンドのページ構成

### ページ一覧とユーザーフロー

```
認証フロー
├── /login                    Supabase Auth（メール/Googleサインイン）
│
メインアプリ（認証必須）
├── / (ダッシュボード)
│   概要: プロジェクト選択・最近の作業・クォータ残量表示
│   コンポーネント:
│   - ProjectSelector（プロジェクト切り替え）
│   - QuotaGauge（YouTube APIクォータ残量）
│   - RecentScripts（最近の台本）
│   - TrendingVideosSummary（伸びてる動画ハイライト）
│
├── /keywords（キーワード検索）  ← Stage 1 MVP
│   概要: シードキーワード入力→網羅的抽出→伸びてる動画一覧化
│   コンポーネント:
│   - KeywordSearchForm（シードキーワード入力・深度設定）
│   - KeywordResultTable（取得キーワード一覧・選択UI）
│   - TrendingVideoList（半年以内に伸びてる動画カード群）
│   - VideoMetricBadge（再生数/日・公開日・チャンネル名）
│
├── /keywords/[id]（キーワード詳細）
│   概要: 特定キーワードの動画一覧・競合分析
│
├── /videos（動画一覧）
│   概要: 全分析済み動画のフィルタ・ソート
│   コンポーネント:
│   - VideoFilter（期間・ジャンル・伸び速度フィルタ）
│   - VideoTable（ソート可能テーブル）
│
├── /videos/[id]（動画詳細）
│   概要: 動画分析・コメントニーズランキング
│   コンポーネント:
│   - VideoHeader（タイトル・サムネイル・統計）
│   - ThumbnailAnalysis（構図・色・テキスト分析）
│   - NeedsRanking（コメントから抽出したニーズTOP10）
│   - CommentList（コメント一覧・感情フィルタ）
│
├── /scripts（台本一覧）         ← Stage 1 MVP
│   概要: 生成済み台本の管理
│   コンポーネント:
│   - ScriptStatusFilter（draft/generating/completed）
│   - ScriptCard（タイトル・文字数・作成日）
│
├── /scripts/new（台本生成ウィザード）  ← Stage 1 MVP の中核UI
│   概要: 受講生が「選ぶだけ」で台本生成できるウィザード
│   ステップ構成:
│   STEP 1: キーワード選択（/keywordsで取得済みのキーワードから選ぶ）
│   STEP 2: 外側設計入力（対象視聴者・問題・約束・独自性 ← フェーズB準拠）
│   STEP 3: 参照ナレッジ確認（RAGで検索された和理論・市場分析を表示）
│   STEP 4: 生成実行（SSEストリーミングでリアルタイム表示）
│   コンポーネント:
│   - WizardStepper（ステップナビゲーション）
│   - KeywordPicker（選択UI）
│   - OuterDesignForm（外側設計入力フォーム）
│   - KnowledgePreviewPanel（参照ナレッジ一覧・除外可能）
│   - StreamingScriptViewer（生成中テキストのリアルタイム表示）
│
├── /scripts/[id]（台本編集）
│   概要: 生成済み台本のリライト・セクション編集
│   コンポーネント:
│   - ScriptSectionEditor（フック/本編/クロージングのセクション別編集）
│   - RewriteInstruction（「ここをもっとキャッチーに」等の指示入力）
│   - WordCountBadge（文字数表示）
│   - ExportButton（テキスト/Markdown形式でエクスポート）
│
├── /knowledge（ナレッジ管理）
│   概要: 和理論・市場分析のナレッジ閲覧・アップロード
│   コンポーネント:
│   - KnowledgeSourceFilter（wa_theory/market_analysis/second_brain）
│   - KnowledgeSearchBar（セマンティック検索）
│   - KnowledgeCard（チャンク表示・出典ファイル名）
│
├── /knowledge/upload（mdアップロード）
│   概要: Obsidian mdファイルのインジェスト
│   コンポーネント:
│   - MarkdownDropzone（ドラッグ&ドロップアップロード）
│   - IngestProgress（チャンク分割・ベクトル化の進捗）
│
├── /thumbnails（サムネイル分析）
│   概要: 競合サムネイルの構造分析・CTRパターン把握
│   コンポーネント:
│   - ThumbnailGrid（サムネイル一覧・スコア表示）
│   - ThumbnailAnalysisModal（詳細分析ポップアップ）
│   - PatternSummary（よく使われている構図パターン集計）
│
├── /theories（理論一覧）
│   概要: 自動構築された理論の閲覧・管理
│   コンポーネント:
│   - TheoryCategoryFilter
│   - TheoryCard（理論本文・信頼度スコア・使用回数）
│   - TheoryAutoBuilder（テキスト貼り付け→自動理論抽出UI）
│
└── /projects/[id]（プロジェクト設定）
    概要: チャンネルコンセプト・フェーズA設計情報の管理
    コンポーネント:
    - PhaseASettingsForm（市場/ターゲット/コンセプト/センターピン入力）
    - ChannelInfoForm（チャンネルID・ジャンル）
```

### コンポーネント設計方針

```
共通設計ルール:
1. Server Components をデフォルトとし、インタラクションが必要な箇所のみ 'use client'
2. データ取得は Server Components 内で fetch（キャッシュ戦略: revalidate 適用）
3. リアルタイム更新（SSEストリーミング、生成進捗）は Client Components
4. shadcn/ui をベースコンポーネントとして使用し、Tailwind でスタイル拡張
5. フォームバリデーションは React Hook Form + Zod

状態管理:
- グローバル状態: Zustand（選択中プロジェクト、クォータ情報）
- サーバー状態: SWR（APIデータのキャッシュ・再検証）
- フォーム状態: React Hook Form
```

---

## 5. データフロー図

### メインフロー: キーワード抽出→動画分析→ナレッジ蓄積→企画生成→台本出力

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: キーワード抽出フロー                                        │
│                                                                     │
│  ユーザー入力                                                         │
│  「YouTube 運用」（シードキーワード）                                  │
│       │                                                             │
│       ▼                                                             │
│  keyword_service.py                                                 │
│  アルファベットスープ法（非同期バックグラウンドタスク）               │
│  ├── 「YouTube 運用 あ」「YouTube 運用 い」... を順次リクエスト       │
│  ├── YouTube Suggest 非公式API（クォータ消費ゼロ）                   │
│  └── 取得サジェスト → keywords テーブルに保存                        │
│       │                                                             │
│       ▼                                                             │
│  youtube_service.py                                                 │
│  search.list（100ユニット × 呼び出し回数）                           │
│  ├── publishedAfter = 6ヶ月前                                        │
│  ├── 上位動画IDをリスト取得                                           │
│  └── videos テーブルに一時保存                                        │
│       │                                                             │
│       ▼                                                             │
│  youtube_service.py                                                 │
│  videos.list バッチ取得（1ユニット/50件）                            │
│  ├── view_count, like_count, published_at を取得                    │
│  ├── views_per_day = view_count / 経過日数 を計算                    │
│  ├── views_per_day 上位 → is_trending = TRUE フラグ付け              │
│  └── videos テーブル更新                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: ナレッジ蓄積フロー（初期セットアップ or 随時更新）          │
│                                                                     │
│  和理論mdファイル群（/knowledge/upload でアップロード）              │
│  ├── MOC_YouTube和理論_全体.md                                       │
│  ├── C_センターピン.md                                               │
│  ├── C_三層設計_初期設計_外側設計_内側設計.md                        │
│  └── 簡易第二の脳/* （市場分析ノート群）                              │
│       │                                                             │
│       ▼                                                             │
│  knowledge_ingest.py（バックグラウンドタスク）                       │
│  ├── LangChain MarkdownTextSplitter                                 │
│  │   chunk_size=300tokens, chunk_overlap=50tokens                  │
│  ├── OpenAI text-embedding-3-small でベクトル化                     │
│  │   （1536次元, $0.02/1M tokens）                                  │
│  └── knowledge_chunks テーブル（pgvector）に保存                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: 企画・台本生成フロー（受講生が使う中核フロー）              │
│                                                                     │
│  フロントエンド: /scripts/new ウィザード                              │
│                                                                     │
│  STEP 1: ユーザーがキーワード選択                                     │
│  「YouTube 運用 初心者」（keywords テーブルから選択）                 │
│       │                                                             │
│       ▼                                                             │
│  STEP 2: 外側設計入力（フェーズB準拠）                               │
│  ├── 対象視聴者: 「副業でYouTubeを始めた初心者」                     │
│  ├── 視聴者の問題: 「再生数が伸びない理由がわからない」               │
│  ├── 約束（タイトル機能): 「再生数が伸びない本当の原因を解説」        │
│  └── 独自性の匂い: 「契約設計という視点」                            │
│       │                                                             │
│       ▼                                                             │
│  STEP 3: RAGによるナレッジ検索                                       │
│  rag_service.py                                                     │
│  ├── 外側設計テキスト → OpenAI Embedding でベクトル化               │
│  ├── pgvector cosine類似度検索 TOP 5チャンク取得                     │
│  │   例: C_センターピン.md, C_外側4点.md, C_1行契約.md              │
│  └── 取得チャンクをコンテキストとしてプロンプトに付与                 │
│       │                                                             │
│       ▼                                                             │
│  STEP 4: Claude API で台本生成（SSEストリーミング）                  │
│  script_service.py                                                  │
│  ├── System Prompt: 和理論の三層設計原則                            │
│  ├── Context: RAGで取得した関連ナレッジ（TOP5チャンク）              │
│  ├── User Prompt: 外側設計 + キーワード + チャンネルコンセプト       │
│  ├── 出力構造:                                                       │
│  │   ① 冒頭フック（〜3000文字）: 既視感×違和感, センターピン提示   │
│  │   ② 本編（〜25000文字）: 三層設計の内側履行、信頼蓄積            │
│  │   └── ③ クロージング（〜2000文字）: CTA、次動画導線              │
│  └── SSE で逐次フロントエンドに送信                                  │
│       │                                                             │
│       ▼                                                             │
│  scripts テーブルに保存 + used_knowledge に参照ナレッジID記録        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: ナレッジ循環フロー（差別化要素）                            │
│                                                                     │
│  生成された台本・コメント分析・動画成績データ                         │
│       │                                                             │
│       ▼                                                             │
│  theory_service.py                                                  │
│  ├── コメントニーズランキング → 視聴者心理理論として自動抽出          │
│  ├── 伸びてる動画のパターン → コンテンツ戦略理論として蓄積           │
│  └── theories テーブルに保存                                         │
│       │                                                             │
│       ▼                                                             │
│  次回の台本生成時にRAGのコンテキストとして活用                        │
│  → 使うたびに賢くなるナレッジループが完成                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### YouTube APIクォータ管理フロー

```
リクエスト受信
     │
     ▼
quota_manager.py
├── Redis から当日の消費ユニット数を取得
├── 必要ユニット数（search.list = 100）を確認
├── 残量 < 必要量 → 429エラー返却（残量・リセット時刻を通知）
└── 残量 OK → APIリクエスト実行
         │
         ▼
    API実行成功
         │
         ▼
Redis の消費カウンタをインクリメント（TTL: 翌日リセット時刻まで）
         │
         ▼
結果を Redis にキャッシュ（search.list結果: TTL 24時間）
```

---

## 6. 実装ロードマップ

### Stage 1 MVP（4〜6週間）- 最優先

```
Week 1-2: インフラ・認証基盤
  ├── Supabase プロジェクト作成・スキーマ適用（001, 002, 003 migration）
  ├── Railway に FastAPI デプロイ（Dockerfile）
  ├── Vercel に Next.js デプロイ
  ├── Supabase Auth 設定（メール認証）
  └── 成功基準: /login → ダッシュボード遷移が動作する

Week 3-4: キーワード検索機能（Stage 1 の前半）
  ├── keyword_service.py: YouTube Suggest 取得
  ├── youtube_service.py: search.list + videos.list 実装
  ├── quota_manager.py: Redisクォータ管理
  ├── /keywords ページ実装
  └── 成功基準: シードキーワード入力 → 伸びてる動画一覧が表示される

Week 5-6: 台本生成機能（Stage 1 の後半）
  ├── knowledge_ingest.py: 和理論mdファイルのベクトル化・格納
  ├── rag_service.py: pgvector セマンティック検索
  ├── script_service.py: Claude API + SSEストリーミング
  ├── /scripts/new ウィザード実装
  └── 成功基準: キーワード選択 → 外側設計入力 → 台本3万文字が生成される
```

### Stage 2（Week 7〜10）

```
  ├── /videos/[id] コメント分析・ニーズランキング
  ├── /thumbnails Claude Vision 分析
  ├── /scripts/[id] リライト機能
  └── 成功基準: 台本のセクション単位リライトが動作する
```

### Stage 3以降（Week 11〜）

```
  ├── theories 自動構築（理論ループ完成）
  ├── 受講生向けUI最適化（ウィザード改善）
  ├── クォータ増加申請（YouTube API）
  └── SerpAPI / pytrends 統合（検索ボリューム付与）
```

---

## 7. 技術スタック選定理由

| レイヤー | 採用技術 | 選定理由 | 代替案と却下理由 |
|---|---|---|---|
| フロントエンド | Next.js 15 App Router | Server Components でSEO・初期表示最適化。Vercel との親和性が高い | Remix（Vercelとの最適化が劣る）|
| UIコンポーネント | shadcn/ui + Tailwind | コピーペースト方式でバンドルサイズ最小化。デザイン自由度高 | Chakra UI（重い）|
| バックエンド | Python FastAPI | LangChain・Claude SDK・pytrends がPythonネイティブ。型安全 | Node.js（LLMエコシステムがPython有利）|
| データベース | Supabase (PostgreSQL) | pgvector でベクトルDB兼用。Auth・RLS が内包。無料枠が充実 | PlanetScale（pgvector非対応）|
| ベクトルDB | pgvector（Supabase内） | 別サービス不要でコスト・運用コスト削減 | Pinecone（$70/月〜、過剰）|
| LLM | Claude API (Sonnet 4.6) | 長文台本生成に強い（200Kコンテキスト）。Vision対応 | GPT-4o（コンテキスト長が劣る）|
| Embedding | OpenAI text-embedding-3-small | コスパ最良（$0.02/1Mトークン）。pgvectorとの実績多 | Claude Embeddings（未成熟）|
| キャッシュ | Redis（Railway Addon） | クォータ管理・APIレスポンスキャッシュ | Memcached（pub/subなし）|
| デプロイ: FE | Vercel | Next.js の最適化デプロイ。無料枠で十分 | AWS Amplify |
| デプロイ: BE | Railway | Dockerfile ベース。Redis Add-on 統合。$20/月〜 | Fly.io（設定複雑）|

---

## 8. セキュリティ設計

```
認証・認可:
├── Supabase Auth（JWTトークン発行）
├── FastAPI ミドルウェア: Authorization ヘッダーの JWT 検証
├── Supabase RLS: DB レベルでユーザーデータを完全分離
└── プロジェクト単位の所有権確認（全ルーター共通）

APIキー管理:
├── 全APIキーを Railway 環境変数（シークレット）に格納
├── フロントエンドには絶対に露出しない（FastAPI 経由のみ）
├── YouTube API キー: サーバーサイドのみで使用
└── Claude API キー: サーバーサイドのみで使用

クォータ・レート制限:
├── ユーザー単位の YouTube API クォータ上限（quota_limit）
├── FastAPI: slowapi でIP単位レート制限（100req/分）
└── 台本生成: ユーザー単位で月N回まで（プラン別制限）

データ保護:
├── Supabase: 転送中・保存時の暗号化（TLS 1.3 / AES-256）
└── 受講生の台本・ナレッジデータは project_id でスコープ分離
```

---

## 9. コスト試算（月額・受講生100名規模）

| 項目 | 月額コスト | 備考 |
|---|---|---|
| Vercel（フロントエンド） | $0 | Hobby プランで十分 |
| Railway（バックエンド + Redis） | $20 | 512MB RAM, Redis 256MB |
| Supabase（DB + Auth） | $25 | Pro プラン, 8GB DB |
| Claude API（台本生成） | $50〜150 | 100名 × 月10台本 × $0.05〜0.15/台本 |
| OpenAI Embeddings（ベクトル化） | $1〜5 | 初期インジェスト + 増分 |
| YouTube Data API | $0 | 無料枠（日10,000ユニット）で運用 |
| **合計** | **$96〜200/月** | 受講料から十分回収可能な水準 |

---

## 10. ファイルパス一覧（実装時の参照用）

```
モノレポルート:
/Users/user/Documents/Cursor/Youtube_Tool/

既存ナレッジ（バックエンドのknowledge_ingest対象）:
/Users/user/Documents/Cursor/Youtube_Tool/和理論 企画作成から、台本まで、和理論を使って構築できる/
/Users/user/Documents/Cursor/Youtube_Tool/市場から穴場を探す/
/Users/user/Documents/Cursor/Youtube_Tool/簡易第二の脳/

アーキテクチャドキュメント:
/Users/user/Documents/Cursor/Youtube_Tool/ARCHITECTURE.md  ← 本ドキュメント
/Users/user/Documents/Cursor/Youtube_Tool/YouTube運用支援WEBツール_実現可能性調査レポート.md
```
