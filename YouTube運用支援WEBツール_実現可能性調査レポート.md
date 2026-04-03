# YouTube運用支援WEBツール 実現可能性調査レポート

**調査日**: 2026年4月2日
**調査者**: リサーチアナリスト（Claude Sonnet 4.6）
**調査対象**: YouTube運用支援統合WEBツール（Phase 1〜6）の実現可能性

---

## 問いの再定義

**表面的な問い**: 構想しているWEBツールは技術的に作れるか？

**本質的な問い**:
1. YouTube Data API v3のクォータ制約の中で、商用SaaSとして成立する規模感の機能を実装できるか？
2. LLMを活用した台本・企画生成は、受講生が満足できる品質とコストで提供できるか？
3. 競合サービスが提供していない「ナレッジ循環＋和理論」という独自体験を技術的に実現できるか？
4. 法的・利用規約上のリスクをコントロールしながら運用できるか？

---

## 調査観点（論点）

- A. YouTube Data API v3のクォータ実現可能性
- B. キーワード網羅的抽出の技術的手法
- C. サムネイル分析の技術的実現性
- D. WEBアプリとして推奨されるアーキテクチャ
- E. 競合・類似サービスとの差別化ポイント
- F. コスト試算とSaaS価格感
- G. 法的・利用規約上の注意点

---

## A. YouTube Data API v3

### クォータ制限の詳細

デフォルト割り当ては **1日10,000ユニット/プロジェクト**。毎日太平洋時間（PT）午前0時にリセットされる。

| API メソッド | 1回あたりのコスト | 備考 |
|---|---|---|
| `search.list` | **100ユニット** | 最もコスト高。キーワード検索、動画検索 |
| `videos.list` | **1ユニット** | 動画ID指定で最大50件の統計を一括取得可能 |
| `commentThreads.list` | **1ユニット** | 1回で最大100件取得 |
| `channels.list` | **1ユニット** | チャンネル情報取得 |
| 動画アップロード | 最大1,600ユニット | 本ツールでは不要 |

出典: [YouTube Data API v3 クォータ計算機](https://developers.google.com/youtube/v3/determine_quota_cost)

### クォータ消費シミュレーション（1日10,000ユニット）

**Phase 1「市場キーワード網羅的抽出」の1日コスト試算**:

- キーワード検索 50回: `search.list` × 50 = **5,000ユニット**
- 動画詳細取得（上位動画500件を`videos.list`で一括取得）: 500÷50 = 10回 = **10ユニット**
- コメント取得（動画10本 × ページ5回）: `commentThreads.list` × 50 = **50ユニット**
- チャンネル情報50件: **1ユニット**

→ **合計約5,061ユニット/日**。1日に許容できるsearch.list呼び出しは約50〜100回が現実的上限。

**重要な制約**: `search.list`の1回100ユニット消費が最大のボトルネック。「網羅的キーワード抽出」を毎日大規模に行うと、すぐにクォータを枯渇させる。

### クォータ増加の申請プロセス

無料でクォータ増加申請が可能（追加料金なし）。ただし以下のプロセスが必要:
1. YouTube API サービス監査フォームの提出
2. YouTubeチームによる手動レビュー（数週間〜数ヶ月かかる場合あり）
3. 利用規約・開発者ポリシーへの完全準拠が前提条件

商用利用規模の場合は追加のOAuth認証や商用ライセンスへの切り替えを求められる可能性がある。

出典: [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits)

### 半年以内の「伸びている動画」をフィルタする方法

`search.list` の `publishedAfter` パラメータ（RFC 3339形式）を使用:

```
publishedAfter=2025-10-01T00:00:00Z
order=viewCount
```

ただし注意点として、`order=viewCount`は総再生数順であり「直近に急伸した動画」ではない。真の「急上昇」フィルタは公式には提供されていない。

**実践的な代替手法**:
- `publishedAfter`で期間を絞り込み
- `videos.list`でstatsを取得し、公開日と再生数から「再生数/経過日数」を算出
- 再生数増加速度でソート（自前計算）

---

## B. キーワード抽出の手法

### YouTube Suggest API（オートコンプリート）

**公式APIは存在しない。** 内部的に以下のエンドポイントを利用:

```
https://clients1.google.com/complete/search?client=youtube&hl=ja&q={keyword}
```

これは非公式（undocumented）なエンドポイントであり、GoogleがいつでもBlockできる。利用規約上のグレーゾーンに該当する点に注意。

**網羅的キーワード抽出のテクニック（アルファベットスープ法）**:

1. シードキーワード（例: 「YouTube 運用」）を入力
2. 後ろにアルファベット・ひらがなを1文字ずつ追加してサジェストを収集
   - 「YouTube 運用 あ」「YouTube 運用 い」... 「YouTube 運用 a」「YouTube 運用 b」...
3. 取得したサジェストを新しいシードキーワードとして再帰的に処理
4. 数千〜数万のロングテールキーワードを網羅的に収集可能

出典: [Alphabet Soup Method解説](https://answersocrates.com/blog/the-alphabet-soup-method/)、[Apify YouTubeオートコンプリートスクレイパー](https://apify.com/scraper-mind/youtube-autocomplete-scraper)

### Google Trends API

**公式APIは存在しない**（2025年時点でアルファ版のみ）。

Pythonライブラリ `pytrends` が非公式インターフェースとして広く使われている:

```python
from pytrends.request import TrendReq
pytrends = TrendReq(hl='ja-JP', tz=360)
pytrends.build_payload(['YouTube運用'], timeframe='today 6-m')
df = pytrends.interest_over_time()
```

ただし、pytrendsは非公式ライブラリであり、Googleのアップデートにより突然動作しなくなるリスクがある。SerpAPIなどの商用サービスを経由する方が安定性は高い。

出典: [pytrends GitHub](https://github.com/GeneralMills/pytrends)、[Google Trends API代替](https://meetglimpse.com/google-trends-api/)

### VidIQ / TubeBuddy のサードパーティAPI

**両サービスとも、外部開発者向けの公開APIは提供していない**（2026年4月時点）。

これらはブラウザ拡張機能として動作し、YouTubeのDOMに直接アクセスする設計。データをプログラム的に取得するAPIエンドポイントは公開されていない。

### 代替: 商用APIサービス

| サービス | 特徴 | 価格帯 |
|---|---|---|
| [Phyllo](https://www.getphyllo.com) | クリエイターデータ統合API | 要問合せ |
| [Modash API](https://www.modash.io) | 3.5億クリエイター検索可能 | 透明な従量制 |
| SerpAPI | YouTube検索結果スクレイピング | $75/月〜 |
| [SEO Review Tools YouTube Keyword API](https://api.seoreviewtools.com/documentation/keyword-apis/youtube-keyword-api/) | キーワード取得API | 従量制 |

---

## C. サムネイル分析の技術的手法

### YouTubeサムネイル画像の取得方法

動画IDさえわかれば、**APIを消費せずに直接取得可能**:

| 解像度 | URL形式 |
|---|---|
| 低画質 (120×90) | `https://img.youtube.com/vi/{VIDEO_ID}/default.jpg` |
| 中画質 (320×180) | `https://img.youtube.com/vi/{VIDEO_ID}/mqdefault.jpg` |
| 高画質 (480×360) | `https://img.youtube.com/vi/{VIDEO_ID}/hqdefault.jpg` |
| 最高画質 (1280×720) | `https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg` |

`maxresdefault.jpg`は全動画で利用可能ではないため、`hqdefault.jpg`へのフォールバック処理が必要。

出典: [YouTube Thumbnail URLs解説](https://internetzkidz.de/en/2021/03/youtube-thumbnail-urls-sizes-paths/)

### AIによる画像分析の選択肢

**Claude Vision（推奨）**:
- Claude Sonnet 4.6がすべてのビジョンタスクをサポート
- 構図分析、テキスト抽出、色使い、感情分析が可能
- コスト: 入力$3/Mトークン。1枚のサムネイル画像は約1,500〜3,000トークン相当
- 1枚あたりの分析コスト: **約$0.005〜$0.01**（約0.75〜1.5円）

**Google Cloud Vision API**:
- ラベル検出/テキスト検出/顔検出: $1.50/1,000ユニット
- 月1,000ユニットまで無料
- サムネイルの構図・テイスト分析は得意。ただし文脈的な解釈はLLMに劣る

出典: [Claude Vision API](https://platform.claude.com/docs/en/build-with-claude/vision)、[Google Cloud Vision API価格](https://cloud.google.com/vision/pricing)

### サムネイル分析の実装フロー（推奨）

```
1. videos.list でサムネイルURL取得（1ユニット/50動画）
2. 直接URLからサムネイル画像をダウンロード（APIコスト0）
3. Claude Vision APIで一括分析
   - 構図パターン（人物有無、文字配置、余白）
   - 主要色（背景/前景/テキスト色）
   - 感情・トーン（驚き、怖さ、期待等）
   - CTRに効く要素の抽出
4. 分析結果をベクトルDBに保存（類似サムネイル検索に活用）
```

---

## D. WEBアプリとしての推奨アーキテクチャ

### 推奨スタック

```
┌─────────────────────────────────────────────────────────┐
│                   フロントエンド                           │
│  Next.js 15 (App Router) + Tailwind CSS + shadcn/ui     │
│  Vercel でデプロイ                                        │
├─────────────────────────────────────────────────────────┤
│                   バックエンド                             │
│  Python FastAPI（LLM処理・YouTube API連携）               │
│  Railway または Fly.io でデプロイ                         │
├─────────────────────────────────────────────────────────┤
│                   データベース層                           │
│  Supabase（PostgreSQL + pgvector）                       │
│  ├── メタデータ: PostgreSQL（動画情報、ユーザー、分析結果）  │
│  ├── ベクトル検索: pgvector（ナレッジ埋め込み、類似検索）   │
│  └── キャッシュ: Redis（クォータ節約のための結果キャッシュ）  │
├─────────────────────────────────────────────────────────┤
│                   LLM統合層                               │
│  Claude API（台本・企画・サムネイル分析）                  │
│  OpenAI Embeddings（テキストのベクトル化）                 │
│  LangChain / LlamaIndex（RAGパイプライン）                │
└─────────────────────────────────────────────────────────┘
```

### ナレッジ蓄積（RAG）のデータフロー

Obsidianのmd群をRAGシステムに取り込む方法は技術的に確立されている:

```
Obsidian .md ファイル群
     ↓ LangChain MarkdownTextSplitter
チャンク分割（300トークン程度）
     ↓ OpenAI Embeddings / Claude Embeddings
ベクトル化
     ↓
PostgreSQL + pgvector に格納
     ↓
ユーザークエリ時にセマンティック検索
     ↓
関連ナレッジを文脈として付与してLLMに投入
```

出典: [FastAPI + pgvector RAG実装](https://medium.com/@fredyriveraacevedo13/building-a-fastapi-powered-rag-backend-with-postgresql-pgvector-c239f032508a)、[Obsidian RAG解説](https://dev.to/bohowhizz/from-markdown-to-meaning-turn-your-obsidian-notes-into-a-conversational-database-using-langchain-4pi7)

### YouTube APIクォータ節約のためのキャッシュ戦略

- **Redis TTL設定**: search.list の結果を24時間キャッシュ（同一クエリの再実行を防止）
- **videos.list バッチ処理**: 1回のAPI呼び出しで最大50動画IDを処理（1ユニット）
- **段階的取得**: 初回は基本情報のみ取得し、ユーザーが選択した動画のみ詳細取得

---

## E. 競合・類似サービスとの比較

### 主要競合サービスの機能・価格比較

| サービス | 主な機能 | 月額価格 | API提供 | 日本語対応 |
|---|---|---|---|---|
| [vidIQ](https://vidiq.com) | キーワード研究、AIアイデア生成、競合分析 | $7.5〜$79 | なし | 一部 |
| [TubeBuddy](https://www.tubebuddy.com) | SEOツール、A/Bテスト、バルク編集 | $4〜$49 | なし | あり |
| [Morningfame](https://morningfame.com) | シンプル分析、招待制 | $4.90 | なし | 限定的 |
| [NoxInfluencer](https://noxinfluencer.com) | チャンネル分析、キーワード、サムネイル生成 | 無料〜 | なし | あり |
| Phyllo | クリエイターデータAPI | 要問合せ | あり（B2B向け） | 限定的 |

出典: [Morningfame レビュー2025](https://outlierkit.com/blog/morningfame-review)、[VidIQ vs TubeBuddy比較](https://outlierkit.com/blog/vidiq-vs-tubebuddy)

### 競合との差別化ポイント（独自優位性）

既存ツールが提供していない機能:

1. **ナレッジ循環エンジン**: 既存ツールは「分析→提案」で完結。本ツールは分析結果をナレッジベースに戻し、次回の企画に活用する「循環構造」を持つ
2. **台本フル生成（数万文字）**: 競合は企画アイデアの提案まで。台本を丸ごと出力するのは本ツールのみ
3. **和理論の体系的実装**: 特定の理論体系をAIに学習させ、同じロジックで一貫した企画・台本を生成
4. **受講生データの集合知**: 複数受講生のデータを蓄積・横展開するB2B2C型の知識共有
5. **日本語特化の精度**: 既存ツールは英語圏中心。日本語コンテンツの文脈理解に最適化

---

## F. コスト感

### YouTube Data API

| 区分 | 条件 | 費用 |
|---|---|---|
| 無料枠 | 10,000ユニット/日/プロジェクト | **完全無料** |
| クォータ増加 | 審査通過後 | **無料**（金銭的コスト不要） |
| 複数プロジェクト | Googleアカウント複数作成 | **無料**（ただし規約上グレー） |

出典: [YouTube API無料か否か解説](https://www.getphyllo.com/post/is-the-youtube-api-free-costs-limits-iv)

### LLM API コスト試算

**台本生成（1本あたり）の試算**:

- 台本1本 ≒ 数万文字 ≒ 30,000〜50,000トークン（出力）
- 入力（企画情報+ナレッジ+プロンプト）≒ 5,000〜10,000トークン

| モデル | 入力コスト | 出力コスト | 台本1本のコスト |
|---|---|---|---|
| Claude Haiku 4.5 | $1/Mトークン | $5/Mトークン | **約$0.25（約37円）** |
| Claude Sonnet 4.6 | $3/Mトークン | $15/Mトークン | **約$0.75（約112円）** |
| Claude Opus 4.6 | $5/Mトークン | $25/Mトークン | **約$1.25（約187円）** |
| GPT-5 mini | $0.25/Mトークン | $2/Mトークン | **約$0.10（約15円）** |

**受講生100名が月4本の台本を生成する場合**:
- Sonnet 4.6使用: 100 × 4 × $0.75 = **月額$300（約45,000円）**
- Haiku 4.5使用: 100 × 4 × $0.25 = **月額$100（約15,000円）**

バッチAPI（50%割引）とプロンプトキャッシュ（入力90%割引）を組み合わせると、実質コストを**60〜80%削減**可能。

出典: [Claude API価格](https://platform.claude.com/docs/en/about-claude/pricing)、[LLM API価格比較2025](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025)

### インフラコスト概算（月額）

| フェーズ | 構成 | 月額コスト |
|---|---|---|
| MVP（〜10名） | Vercel無料 + Supabase無料 + Railway Hobby | **$5〜$30/月** |
| 成長期（〜100名） | Vercel Pro + Supabase Pro + Railway Pro | **$50〜$200/月** |
| スケール期（〜1,000名） | Vercel Team + Supabase Team + AWS/GCP | **$500〜$5,000/月** |

出典: [Supabase価格](https://supabase.com/pricing)、[Railway価格](https://railway.app/pricing)、[Vercel価格](https://vercel.com/pricing)

### SaaS月額価格の推奨設定

| プラン | ターゲット | 月額 | 主な機能 |
|---|---|---|---|
| スターター | 個人クリエイター | ¥2,980〜¥4,980 | キーワード分析、サムネイル参照、基本企画提案 |
| プロ | 本格運用者 | ¥9,800〜¥14,800 | 台本生成、コメント分析、ナレッジ蓄積 |
| チーム（受講生向け） | 講座受講生 | ¥3,980〜¥6,980 | 全機能、和理論テンプレート |

競合のvidIQ（月$7.5〜$79）・TubeBuddy（月$4〜$49）と比較して、日本語特化・台本生成込みの付加価値で**¥9,800〜¥14,800**は十分な競争力を持つ。

---

## G. 法的注意点

### YouTube利用規約との整合性

**許可されていること（APIを通じた正規アクセス）**:
- YouTube Data API v3経由での動画情報・コメント・統計の取得
- 取得データを用いた分析・可視化
- ユーザーの同意を得た上でのナレッジ蓄積

**禁止されていること**:
- YouTubeウェブサイトの直接スクレイピング（HTML解析）
- APIを通じずに取得したデータの利用
- YouTubeコンテンツページへの広告掲載（事前承認なし）
- APIで取得したデータの **30日超の保存**（一部の分析・統計データを除く）

出典: [YouTube API開発者ポリシー](https://developers.google.com/youtube/terms/developer-policies)

### データ保存の制限（重要）

YouTube APIポリシーは**30日以上のデータ保存を原則禁止**している（ただし、分析・集計データは例外）。

実装上の注意:
- 動画タイトル・説明文・コメント等の生データは30日で削除または更新
- 分析結果（再生数トレンド、キーワードランキング等）の集計済みデータは保存可能
- ユーザーが同意を取り消した場合、7日以内の全データ削除が義務付けられている

### コメントスクレイピングの法的リスク

| リスク | 内容 | 対処法 |
|---|---|---|
| YouTube ToS違反 | ウェブスクレイピング禁止 | **APIのみ使用**（commentThreads.listは合法） |
| 個人情報保護法（日本） | コメント投稿者が特定可能な場合は個人情報 | 匿名化・集計処理後に保存 |
| GDPR | EU在住ユーザーのコメントは規制対象 | プライバシーポリシーに明記、データ最小化 |
| CFAA（米国） | 不正アクセス法 | API使用の範囲内では問題なし |

**コメントデータの安全な取り扱い方**:
1. `commentThreads.list` API（合法）でのみ取得
2. コメント内容は分析・集計目的のみに使用
3. 個人名・アカウント情報は匿名化して保存
4. 分析結果（ニーズのカテゴリ分類等）のみを長期保存

出典: [YouTube Developer Policies](https://developers.google.com/youtube/terms/developer-policies)、[YouTubeスクレイピングの法的考察](https://proxiesapi.com/articles/does-youtube-allow-scraping)

### 日本の個人情報保護法（令和6年改正）への対応

2024年改正で強化された主要点:
- データ漏洩時の報告・通知義務が「個人情報」全般に拡大
- Cookieなど「個人関連情報」の取り扱い厳格化
- 要配慮個人情報（思想・信条等が含まれるコメント）への注意

**必須対応**:
- プライバシーポリシーの公開（収集データ・利用目的・保存期間の明記）
- ユーザーへのデータ削除機能の提供
- Googleのプライバシーポリシーへの準拠（YouTube APIデータ利用の場合）

出典: [個人情報保護法2024改正解説](https://monolith.law/en/general-corporate/personal-information-protection-2024)

---

## 実現可能性の総合判定

### フェーズ別の実現可能性スコア

| Phase | 機能 | 技術難易度 | 実現可能性 | 主な課題 |
|---|---|---|---|---|
| Phase 1 | 市場キーワード網羅抽出・動画一覧化 | ★★☆☆☆ | **高** | クォータ管理（search.list消費） |
| Phase 2 | ナレッジ循環・RAGシステム | ★★★☆☆ | **高** | Obsidian→ベクトルDB変換の設計 |
| Phase 3 | 企画・台本・サムネイル生成 | ★★★☆☆ | **高** | 長文出力の品質安定化 |
| Phase 4 | コメント分析・ニーズ抽出 | ★★☆☆☆ | **高** | データ保存30日制限への対処 |
| Phase 5 | 理論自動構築（フレームワーク分析） | ★★★★☆ | **中** | RAGの精度・ハルシネーション管理 |
| Phase 6 | 受講生向けUI（選ぶだけUI） | ★★☆☆☆ | **高** | UX設計・パーソナライズ |

### 総合判定: **「実現可能。ただし段階的な実装と利用規約管理が必須」**

**強み（GO要因）**:
- YouTube Data API v3は公式に存在し、必要な機能をほぼカバーできる
- LLMによる台本生成は技術的に確立されており、コストも現実的（1本100〜200円以下）
- pgvector + LangChainによるRAGパイプラインは実績豊富
- 競合サービスには「台本フル生成」「ナレッジ循環」がなく、差別化が明確

**リスク（注意要因）**:
- `search.list`の1日最大100回制限がキーワード網羅抽出のボトルネック
- YouTubeのデータ保存30日制限により、生データの長期保存は不可
- クォータ増加申請は審査制（時間とコンプライアンス対応が必要）
- LLM出力の品質は受講生のインプット精度に大きく依存

---

## 推奨ロードマップ

### Stage 0: 設計・準備（1〜2ヶ月）

- [ ] YouTube API Developer Console でプロジェクト作成・クォータ申請
- [ ] Obsidianデータ（簡易第二の脳・市場分析・和理論）のRAG化実験
- [ ] Claude API を使った台本生成プロトタイプ作成（品質検証）
- [ ] 利用規約コンプライアンスチェック（弁護士レビュー推奨）

### Stage 1: MVP（2〜3ヶ月）

**対象Phase**: Phase 1 + Phase 3の基本機能

- キーワード検索・動画一覧化（クォータ管理付き）
- ナレッジベースからの企画案抽出
- Claude APIによる台本生成（入力テンプレート固定）
- サムネイル参照機能（画像表示のみ）

**技術スタック**: Next.js + FastAPI + Supabase + Claude API
**想定コスト**: $30〜$100/月（インフラ+API）
**想定価格**: 初期受講生向けにβ版無料提供

### Stage 2: コアプロダクト（3〜4ヶ月）

**対象Phase**: Phase 2 + Phase 4

- RAGナレッジ循環システムの本格実装
- コメント分析・ニーズランキング機能
- 受講生データの集合知化
- サムネイルAI分析（Claude Vision）

**想定コスト**: $100〜$500/月
**想定価格**: ¥9,800〜¥14,800/月で有料化

### Stage 3: 差別化機能（4〜6ヶ月）

**対象Phase**: Phase 5 + Phase 6

- 理論自動構築エンジン
- 受講生向け「選ぶだけUI」の完成
- マーケ書籍の投入→理論紐づけ自動化
- 横展開テンプレートライブラリ

**想定コスト**: $500〜$2,000/月
**想定価格**: チームプランの追加・受講生100名スケール

### Stage 4: スケール（6ヶ月以降）

- クォータ増加申請によるAPIスケールアップ
- Modash/Phyllo等のサードパーティデータ統合検討
- 講座ブランドとしてのホワイトラベル提供
- アフィリエイト・紹介プログラムの設計

---

## 重要ポイント（まとめ）

1. **YouTubeクォータは「search.list節約」が最重要課題**: 動画IDが既知の場合は`videos.list`（1ユニット/50件）を活用し、`search.list`（100ユニット/回）の呼び出しを最小化する。

2. **データ保存30日制限への対処**: 生データは保存しない設計にし、分析・集計済みのナレッジのみ長期保存する。

3. **台本生成のコストは現実的**: Claude Sonnet 4.6で1本あたり約100〜200円。100名規模でも月5万円以下に収まり、¥9,800/月の課金設計で十分ペイできる。

4. **サムネイルはAPIコスト0で取得可能**: 動画IDから直接URL生成できるため、クォータを節約できる。

5. **スクレイピングは使わない**: YouTube ToS違反となるため、必ずAPIを経由する。コメント取得は`commentThreads.list`（1ユニット）が合法かつ低コスト。

---

## 未解決・追加調査が必要な項目

1. **クォータ増加申請の実際の承認率・期間**: 商用ツールとして申請した場合の実績データが不足
2. **和理論のプロンプト設計**: 理論体系をどのようにLLMプロンプトに落とし込むかは別途技術検証が必要
3. **日本語Suggest APIの安定性**: 非公式エンドポイントのため、代替手段の確保が必要
4. **受講生データの法的扱い**: 複数受講生のデータを集合知化する際の同意取得方法と利用規約設計
5. **競合の動向**: vidIQとTubeBuddyが日本語特化版を強化した場合の差別化戦略の見直し

---

## 参考文献・出典一覧

1. [YouTube Data API v3 クォータ計算機](https://developers.google.com/youtube/v3/determine_quota_cost)
2. [YouTube API クォータ制限詳解 (Phyllo)](https://www.getphyllo.com/post/youtube-api-limits-how-to-calculate-api-usage-cost-and-fix-exceeded-api-quota)
3. [10,000ユニット/日で100K動画を追跡する方法 (DEV Community)](https://dev.to/siyabuilt/youtubes-api-quota-is-10000-unitsday-heres-how-i-track-100k-videos-without-hitting-it-5d8h)
4. [YouTube API開発者ポリシー](https://developers.google.com/youtube/terms/developer-policies)
5. [YouTube Audit & Quota Extension申請フォーム](https://support.google.com/youtube/contact/yt_api_form?hl=en)
6. [pytrends GitHub（Google Trends非公式API）](https://github.com/GeneralMills/pytrends)
7. [アルファベットスープ法解説](https://answersocrates.com/blog/the-alphabet-soup-method/)
8. [YouTube AutocompleteスクレイパーAPI (Apify)](https://apify.com/scraper-mind/youtube-autocomplete-scraper)
9. [YouTubeサムネイルURL形式解説](https://internetzkidz.de/en/2021/03/youtube-thumbnail-urls-sizes-paths/)
10. [Claude Vision APIドキュメント](https://platform.claude.com/docs/en/build-with-claude/vision)
11. [Claude API 価格](https://platform.claude.com/docs/en/about-claude/pricing)
12. [Google Cloud Vision API価格](https://cloud.google.com/vision/pricing)
13. [FastAPI + pgvector RAG実装](https://medium.com/@fredyriveraacevedo13/building-a-fastapi-powered-rag-backend-with-postgresql-pgvector-c239f032508a)
14. [Obsidian RAG実装例](https://dev.to/bohowhizz/from-markdown-to-meaning-turn-your-obsidian-notes-into-a-conversational-database-using-langchain-4pi7)
15. [Morningfame レビュー2025](https://outlierkit.com/blog/morningfame-review)
16. [VidIQ vs TubeBuddy比較](https://outlierkit.com/blog/vidiq-vs-tubebuddy)
17. [Supabase価格](https://supabase.com/pricing)
18. [LLM API価格比較2025 (IntuitionLabs)](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025)
19. [YouTubeスクレイピングの法的考察 (ProxiesAPI)](https://proxiesapi.com/articles/does-youtube-allow-scraping)
20. [個人情報保護法2024改正 (Monolith Law)](https://monolith.law/en/general-corporate/personal-information-protection-2024)
21. [Phyllo APIサービス](https://www.getphyllo.com)
22. [Modash API (Phyllo代替)](https://www.modash.io/blog/phyllo-api-alternatives)
