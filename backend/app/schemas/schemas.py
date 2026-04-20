"""
Pydanticスキーマ定義。
Create / Update / Response の各スキーマを提供する。
DBスキーマ: supabase/migrations/001_initial_schema.sql と完全一致。
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# プロジェクト
# ============================================================


class ProjectCreate(BaseModel):
    """プロジェクト作成リクエスト"""
    name: str = Field(..., description="プロジェクト名")
    channel_id: Optional[str] = Field(None, description="YouTubeチャンネルID")
    channel_url: Optional[str] = Field(None, description="チャンネルURL")
    genre: Optional[str] = Field(None, description="ジャンル")
    target_audience: Optional[str] = Field(None, description="ターゲット視聴者")
    concept: Optional[str] = Field(None, description="チャンネルコンセプト")
    center_pin: Optional[str] = Field(None, description="センターピン")
    settings: Optional[dict[str, Any]] = Field(default_factory=dict, description="追加設定（JSONB）")


class ProjectUpdate(BaseModel):
    """プロジェクト更新リクエスト"""
    name: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    concept: Optional[str] = None
    center_pin: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """プロジェクトレスポンス"""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    channel_id: Optional[str]
    channel_url: Optional[str]
    genre: Optional[str]
    target_audience: Optional[str]
    concept: Optional[str]
    center_pin: Optional[str]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# キーワード
# ============================================================


class KeywordCreate(BaseModel):
    """キーワード作成リクエスト"""
    keyword: str = Field(..., description="キーワード")
    seed_keyword: Optional[str] = Field(None, description="シードキーワード")
    source: str = Field("manual", description="取得元 (youtube_suggest / manual / related)")
    is_selected: bool = Field(False, description="選択済みフラグ")


class KeywordUpdate(BaseModel):
    """キーワード更新リクエスト"""
    is_selected: Optional[bool] = None
    search_volume: Optional[int] = None
    competition: Optional[float] = None
    trend_score: Optional[float] = None


class KeywordResponse(BaseModel):
    """キーワードレスポンス"""
    id: uuid.UUID
    project_id: uuid.UUID
    keyword: str
    seed_keyword: Optional[str]
    source: str
    search_volume: Optional[int]
    competition: Optional[float]
    trend_score: Optional[float]
    is_selected: bool
    fetched_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KeywordSuggestRequest(BaseModel):
    """サジェストキーワード取得リクエスト"""
    seed_keyword: str = Field(..., description="シードキーワード")
    language: str = Field("ja", description="言語コード")


class KeywordSuggestResponse(BaseModel):
    """サジェストキーワードレスポンス"""
    seed_keyword: str
    suggestions: list[str]


# ============================================================
# 動画
# ============================================================


class VideoSearchRequest(BaseModel):
    """動画検索リクエスト"""
    query: str = Field(..., description="検索クエリ")
    max_results: int = Field(10, ge=1, le=50, description="最大取得件数")
    order: str = Field("relevance", description="並び順")
    keyword_id: Optional[uuid.UUID] = Field(None, description="紐づけるキーワードID")


class VideoUrlRequest(BaseModel):
    """URL指定で動画を追加するリクエスト"""
    url: str = Field(..., description="YouTube動画URL")


class VideoResponse(BaseModel):
    """動画レスポンス"""
    id: uuid.UUID
    project_id: uuid.UUID
    youtube_video_id: str
    title: str
    channel_id: Optional[str]
    channel_title: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]
    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    duration_seconds: Optional[int]
    thumbnail_url: Optional[str]
    views_per_day: Optional[float]
    is_trending: bool
    keyword_id: Optional[uuid.UUID]
    thumbnail_analysis: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoCommentResponse(BaseModel):
    """動画コメントレスポンス"""
    id: uuid.UUID
    video_id: uuid.UUID
    youtube_comment_id: str
    author_name: Optional[str]
    text: str
    like_count: int
    published_at: Optional[datetime]
    need_category: Optional[str]
    sentiment: Optional[str]
    is_question: bool
    extracted_needs: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


# ============================================================
# 台本
# ============================================================


class ScriptCreate(BaseModel):
    """台本作成リクエスト"""
    title: str = Field(..., description="台本タイトル")
    keyword_id: Optional[uuid.UUID] = Field(None, description="紐づけるキーワードID")
    target_viewer: Optional[str] = Field(None, description="ターゲット視聴者")
    viewer_problem: Optional[str] = Field(None, description="視聴者の悩み")
    promise: Optional[str] = Field(None, description="動画の約束")
    uniqueness: Optional[str] = Field(None, description="独自性")


class ScriptUpdate(BaseModel):
    """台本更新リクエスト"""
    title: Optional[str] = None
    status: Optional[str] = None
    target_viewer: Optional[str] = None
    viewer_problem: Optional[str] = None
    promise: Optional[str] = None
    uniqueness: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    closing: Optional[str] = None
    word_count: Optional[int] = None


class ScriptResponse(BaseModel):
    """台本レスポンス"""
    id: uuid.UUID
    project_id: uuid.UUID
    keyword_id: Optional[uuid.UUID]
    title: str
    status: str
    target_viewer: Optional[str]
    viewer_problem: Optional[str]
    promise: Optional[str]
    uniqueness: Optional[str]
    hook: Optional[str]
    body: Optional[str]
    closing: Optional[str]
    word_count: Optional[int]
    generation_model: Optional[str]
    prompt_version: Optional[str]
    used_knowledge: Optional[dict[str, Any]]
    generation_cost: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptGenerateRequest(BaseModel):
    """台本AI生成リクエスト"""
    title: str = Field(..., description="動画タイトル")
    keyword_id: Optional[uuid.UUID] = Field(None, description="紐づけるキーワードID")
    target_viewer: str = Field("一般視聴者", description="ターゲット視聴者")
    viewer_problem: Optional[str] = Field(None, description="視聴者の悩み")
    promise: Optional[str] = Field(None, description="動画の約束・ベネフィット")
    uniqueness: Optional[str] = Field(None, description="独自性・差別化ポイント")
    additional_context: Optional[str] = Field(None, description="追加コンテキスト")
    use_rag: bool = Field(False, description="RAGで知識を参照するか")
    model_id: Optional[uuid.UUID] = Field(None, description="使用するナレッジモデルID")


# ============================================================
# ナレッジ
# ============================================================


class KnowledgeUploadResponse(BaseModel):
    """ナレッジアップロードレスポンス"""
    filename: str
    chunk_count: int
    message: str


class KnowledgeSearchRequest(BaseModel):
    """ナレッジ検索リクエスト"""
    query: str = Field(..., description="検索クエリ")
    top_k: int = Field(5, ge=1, le=20, description="取得件数")


class KnowledgeChunkResponse(BaseModel):
    """ナレッジチャンクレスポンス"""
    id: uuid.UUID
    source_file: str
    source_type: str
    chunk_index: int
    content: str
    token_count: Optional[int] = None
    score: Optional[float] = None

    model_config = {"from_attributes": True}


# ============================================================
# サムネイル
# ============================================================


class ThumbnailAnalyzeRequest(BaseModel):
    """サムネイル分析リクエスト"""
    video_ids: list[uuid.UUID] = Field(..., description="分析対象の動画IDリスト")


class ThumbnailAnalysisDetail(BaseModel):
    """サムネイル分析詳細"""
    video_id: uuid.UUID
    thumbnail_url: str
    dominant_colors: list[dict[str, str]] = Field(default_factory=list, description="主要色リスト [{hex, name}]")
    text_overlay: Optional[str] = Field(None, description="サムネ上のテキスト")
    face_count: int = Field(0, description="顔の数")
    emotion: Optional[str] = Field(None, description="表情 (surprise / smile / serious / etc)")
    composition_type: Optional[str] = Field(None, description="構図パターン (full_face / split / text_only / product / before_after / etc)")
    click_score: float = Field(0.0, description="CTR予測スコア (1-10)")
    analysis_raw: Optional[str] = Field(None, description="自由記述の分析コメント")


class ThumbnailCreate(BaseModel):
    """サムネイル作成リクエスト"""
    image_url: str = Field(..., description="画像URL")
    source_type: str = Field("uploaded", description="ソース種別 (youtube / uploaded / generated)")
    video_id: Optional[uuid.UUID] = Field(None, description="紐づける動画ID")


class ThumbnailUpdate(BaseModel):
    """サムネイル更新リクエスト"""
    image_url: Optional[str] = None
    dominant_colors: Optional[dict[str, Any]] = None
    text_overlay: Optional[str] = None
    face_count: Optional[int] = None
    emotion: Optional[str] = None
    composition_type: Optional[str] = None
    click_score: Optional[float] = None
    analysis_raw: Optional[dict[str, Any]] = None
    analyzed_at: Optional[datetime] = None


class ThumbnailResponse(BaseModel):
    """サムネイルレスポンス"""
    id: uuid.UUID
    video_id: Optional[uuid.UUID]
    project_id: uuid.UUID
    image_url: str
    source_type: str
    dominant_colors: Optional[dict[str, Any]]
    text_overlay: Optional[str]
    face_count: Optional[int]
    emotion: Optional[str]
    composition_type: Optional[str]
    click_score: Optional[float]
    analysis_raw: Optional[dict[str, Any]]
    analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 理論
# ============================================================


class TheoryCreate(BaseModel):
    """理論作成リクエスト"""
    title: str = Field(..., description="理論タイトル")
    category: str = Field(..., description="カテゴリ (hook / retention / ctr / seo / storytelling / editing)")
    body: str = Field(..., description="理論本文")
    source_type: str = Field(..., description="ソース種別 (wa_theory / user_defined / ai_extracted)")
    source_ref: Optional[str] = Field(None, description="参照元")
    evidence: Optional[dict[str, Any]] = Field(None, description="エビデンス（JSONB）")
    confidence: Optional[float] = Field(None, description="確信度 (0.00-1.00)")


class TheoryUpdate(BaseModel):
    """理論更新リクエスト"""
    title: Optional[str] = None
    category: Optional[str] = None
    body: Optional[str] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    is_active: Optional[bool] = None


class TheoryResponse(BaseModel):
    """理論レスポンス"""
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    title: str
    category: str
    body: str
    source_type: str
    source_ref: Optional[str]
    evidence: Optional[dict[str, Any]]
    confidence: Optional[float]
    usage_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 共通
# ============================================================


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    version: str


class QuotaStatusResponse(BaseModel):
    """クォータ状況レスポンス"""
    date: str
    used: int
    remaining: int
    limit: int


# ============================================================
# コメント分析
# ============================================================


class NeedCategory(BaseModel):
    """ニーズカテゴリ（カテゴリ名、件数、代表コメント）"""
    category: str = Field(..., description="ニーズカテゴリ名")
    count: int = Field(..., description="該当コメント件数")
    representative_comments: list[str] = Field(default_factory=list, description="代表コメント")


class CommentAnalysisResponse(BaseModel):
    """コメント分析レスポンス（ニーズランキング）"""
    video_id: uuid.UUID
    total_comments: int
    analyzed_count: int
    need_categories: list[NeedCategory] = Field(default_factory=list, description="ニーズカテゴリ別ランキング")
    sentiment_summary: dict[str, int] = Field(default_factory=dict, description="感情分布")
    question_count: int = Field(0, description="質問コメント数")
