-- ============================================================
-- knowledge_seed.sql
-- サンプルデータ INSERT
-- ============================================================

-- サンプルユーザー
INSERT INTO users (id, auth_id, email, display_name, plan, quota_used, quota_limit) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'demo@example.com', 'デモユーザー', 'pro', 5, 1000);

-- サンプルプロジェクト
INSERT INTO projects (id, user_id, name, channel_id, channel_url, genre, target_audience, concept, center_pin) VALUES
    ('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     'YouTube攻略チャンネル', 'UC_sample_channel_id', 'https://youtube.com/@sample',
     'ビジネス・マーケティング', '20-40代の副業・起業志望者',
     '和理論に基づくYouTube成長戦略を解説するチャンネル',
     'データドリブンなYouTube攻略');

-- サンプルキーワード
INSERT INTO keywords (id, project_id, keyword, seed_keyword, source, search_volume, competition, trend_score, is_selected) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     'YouTube 再生回数 増やし方', 'YouTube 再生回数', 'youtube_suggest', 12000, 0.75, 85.50, TRUE),
    ('d0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000001',
     'YouTube サムネイル 作り方', 'YouTube サムネイル', 'youtube_suggest', 8500, 0.60, 72.30, TRUE),
    ('d0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000001',
     'YouTube 台本 書き方', 'YouTube 台本', 'manual', 5200, 0.45, 68.10, FALSE);

-- サンプル動画
INSERT INTO videos (id, project_id, youtube_video_id, title, channel_id, channel_title, description, published_at, view_count, like_count, comment_count, duration_seconds, thumbnail_url, views_per_day, is_trending, keyword_id) VALUES
    ('e0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     'dQw4w9WgXcQ_sample', 'YouTube再生回数を10倍にする方法【完全解説】',
     'UC_competitor_01', '競合チャンネルA',
     'この動画ではYouTubeの再生回数を劇的に増やすための具体的な手法を解説します。',
     '2025-12-01 10:00:00+09', 150000, 4500, 320, 900,
     'https://img.youtube.com/vi/sample/maxresdefault.jpg',
     1250.00, TRUE, 'd0000000-0000-0000-0000-000000000001');

-- サンプルコメント
INSERT INTO video_comments (id, video_id, youtube_comment_id, author_name, text, like_count, published_at, need_category, sentiment, is_question, extracted_needs) VALUES
    ('f0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001',
     'comment_sample_001', '視聴者A',
     'めちゃくちゃ参考になりました！サムネイルの作り方も教えてほしいです。',
     15, '2025-12-02 14:30:00+09',
     'how_to_request', 'positive', TRUE,
     '{"needs": ["サムネイル作成方法"], "topics": ["サムネイル"]}'),
    ('f0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000001',
     'comment_sample_002', '視聴者B',
     '初心者でも実践できる内容で助かります。チャンネル登録しました！',
     8, '2025-12-03 09:15:00+09',
     'gratitude', 'positive', FALSE,
     '{"needs": [], "topics": ["初心者向け"]}');

-- サンプル knowledge_chunks (グローバル: project_id IS NULL)
INSERT INTO knowledge_chunks (id, project_id, source_file, source_type, chunk_index, content, metadata, token_count) VALUES
    ('70000000-0000-0000-0000-000000000001', NULL,
     'wa_theory_fundamentals.md', 'wa_theory', 0,
     '和理論の基本原則: YouTube動画の成功は「市場選定」「企画力」「台本構成」の三位一体で決まる。市場選定では、検索ボリュームと競合度のバランスを分析し、勝てるポジションを見つけることが最優先。',
     '{"chapter": "基礎理論", "section": "三位一体の原則"}',
     85),
    ('70000000-0000-0000-0000-000000000002', NULL,
     'wa_theory_fundamentals.md', 'wa_theory', 1,
     'フック理論: 動画の最初の5秒で視聴者の離脱を防ぐ。具体的には「問題提起」「意外性のある事実」「ベネフィットの提示」の3パターンが有効。冒頭で自己紹介を入れるのは離脱率を上げるため避ける。',
     '{"chapter": "台本構成", "section": "フック理論"}',
     92),
    ('70000000-0000-0000-0000-000000000003', NULL,
     'wa_theory_fundamentals.md', 'wa_theory', 2,
     'サムネイルのCTR最適化: 人の顔（驚き・喜びの表情）、コントラストの高い配色、3-5文字の大きなテキスト、右下にYouTubeの再生バーが重なるエリアを避ける配置が重要。',
     '{"chapter": "サムネイル", "section": "CTR最適化"}',
     78),
    ('70000000-0000-0000-0000-000000000004', NULL,
     'market_analysis_guide.md', 'market_analysis', 0,
     '穴場市場の発見方法: 月間検索ボリューム1,000-10,000のキーワードで、上位10動画の平均再生回数が50,000以下、かつチャンネル登録者数10万以下のチャンネルが上位を占める市場を狙う。',
     '{"chapter": "市場分析", "section": "穴場市場"}',
     88);

-- プロジェクト固有の knowledge_chunks
INSERT INTO knowledge_chunks (id, project_id, source_file, source_type, chunk_index, content, metadata, token_count) VALUES
    ('70000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000001',
     'channel_analysis_notes.md', 'second_brain', 0,
     '当チャンネルの強み: データ分析に基づく客観的なアドバイスが差別化ポイント。競合は経験談ベースが多い中、具体的な数値を示すことで信頼性を確保する。',
     '{"type": "channel_strategy", "date": "2025-11-15"}',
     65);

-- サンプル台本
INSERT INTO scripts (id, project_id, keyword_id, title, status, target_viewer, viewer_problem, promise, uniqueness, hook, body, closing, word_count, generation_model, prompt_version) VALUES
    ('80000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     'd0000000-0000-0000-0000-000000000001',
     'YouTube再生回数を10倍にする5つの秘訣', 'completed',
     '登録者1000人未満のYouTube初心者',
     '動画を投稿しても再生回数が伸びない',
     'この動画を見れば、次の投稿から再生回数が劇的に変わります',
     'データ分析に基づく再現性のある手法を公開',
     'あなたの動画が再生されない理由、実はたった1つの要素が欠けているだけかもしれません。今日お話しする5つの秘訣を実践したチャンネルは、平均で再生回数が10倍になっています。',
     '【秘訣1: キーワード選定】まず最初に取り組むべきは...',
     '今日お伝えした5つの秘訣、まずは1つだけでいいので次の動画で試してみてください。チャンネル登録して通知をオンにしていただければ、来週はサムネイルの作り方を徹底解説します。',
     3500, 'gpt-4o', 'v1.0');

-- サンプルサムネイル
INSERT INTO thumbnails (id, video_id, project_id, image_url, source_type, dominant_colors, text_overlay, face_count, emotion, composition_type, click_score) VALUES
    ('90000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001',
     'c0000000-0000-0000-0000-000000000001',
     'https://img.youtube.com/vi/sample/maxresdefault.jpg', 'youtube',
     '{"colors": ["#FF0000", "#FFFFFF", "#000000"]}',
     '再生10倍', 1, 'surprise', 'face_left_text_right', 78.50);

-- サンプル理論
INSERT INTO theories (id, project_id, title, category, body, source_type, source_ref, evidence, confidence, usage_count, is_active) VALUES
    ('a1000000-0000-0000-0000-000000000001', NULL,
     'フック5秒ルール', 'hook',
     '動画の最初の5秒で視聴者の注意を引けなければ離脱される。冒頭に自己紹介やチャンネル紹介を入れず、いきなり本題の核心に触れる。',
     'wa_theory', 'wa_theory_fundamentals.md#hook',
     '{"studies": ["YouTube Creator Academy 2024"], "sample_size": 500}',
     0.92, 15, TRUE),
    ('a1000000-0000-0000-0000-000000000002', NULL,
     'サムネイル3色ルール', 'ctr',
     'サムネイルに使う色は3色以内に抑える。背景・メインテキスト・アクセントの3色構成がCTRを最大化する。',
     'wa_theory', 'wa_theory_fundamentals.md#thumbnail',
     '{"ab_tests": 50, "avg_ctr_improvement": "23%"}',
     0.85, 8, TRUE),
    ('a1000000-0000-0000-0000-000000000003', NULL,
     'ストーリーテリングPASTORフレームワーク', 'storytelling',
     'Problem(問題) → Amplify(増幅) → Story(物語) → Transformation(変化) → Offer(提案) → Response(行動喚起)の順で台本を構成する。',
     'ai_extracted', 'analysis_batch_2025_11',
     '{"source_videos": 200, "avg_retention_improvement": "18%"}',
     0.78, 3, TRUE);
