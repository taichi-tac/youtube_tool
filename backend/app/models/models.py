"""
SQLAlchemy ORMモデル定義。
全テーブルをpgvector対応で定義する。
DBスキーマ: supabase/migrations/001_initial_schema.sql と完全一致。
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    """UTC現在時刻を返すヘルパー"""
    return datetime.now(timezone.utc)


class User(Base):
    """ユーザーテーブル（Supabase Authと連携）"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auth_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Project(Base):
    """プロジェクトテーブル（チャンネル単位の管理）"""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    center_pin: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    user: Mapped["User"] = relationship(back_populates="projects")
    keywords: Mapped[list["Keyword"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    videos: Mapped[list["Video"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    scripts: Mapped[list["Script"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    thumbnails: Mapped[list["Thumbnail"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    theories: Mapped[list["Theory"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Keyword(Base):
    """キーワードテーブル（YouTube検索キーワード管理）"""
    __tablename__ = "keywords"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    seed_keyword: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    trend_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("project_id", "keyword", name="uq_project_keyword"),
    )

    # リレーション
    project: Mapped["Project"] = relationship(back_populates="keywords")
    videos: Mapped[list["Video"]] = relationship(back_populates="keyword")
    scripts: Mapped[list["Script"]] = relationship(back_populates="keyword")


class Video(Base):
    """動画テーブル（YouTube動画メタデータ）"""
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    youtube_video_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True)
    like_count: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    views_per_day: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="SET NULL"), nullable=True
    )
    thumbnail_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    project: Mapped["Project"] = relationship(back_populates="videos")
    keyword: Mapped["Keyword | None"] = relationship(back_populates="videos")
    comments: Mapped[list["VideoComment"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    thumbnails: Mapped[list["Thumbnail"]] = relationship(back_populates="video")


class VideoComment(Base):
    """動画コメントテーブル"""
    __tablename__ = "video_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    youtube_comment_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    need_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False)
    extracted_needs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # リレーション
    video: Mapped["Video"] = relationship(back_populates="comments")


class KnowledgeChunk(Base):
    """ナレッジチャンクテーブル（RAG用ベクトルストア）"""
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    # pgvector: 1536次元（OpenAI text-embedding-3-small）
    embedding = mapped_column(Vector(1536), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("source_file", "chunk_index", name="uq_source_file_chunk_index"),
    )

    # リレーション
    project: Mapped["Project | None"] = relationship(back_populates="knowledge_chunks")


class Script(Base):
    """台本テーブル（AI生成台本）"""
    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    target_viewer: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewer_problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    promise: Mapped[str | None] = mapped_column(Text, nullable=True)
    uniqueness: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    closing: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_knowledge: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_cost: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    project: Mapped["Project"] = relationship(back_populates="scripts")
    keyword: Mapped["Keyword | None"] = relationship(back_populates="scripts")


class Thumbnail(Base):
    """サムネイルテーブル"""
    __tablename__ = "thumbnails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    dominant_colors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    text_overlay: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emotion: Mapped[str | None] = mapped_column(Text, nullable=True)
    composition_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    click_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    analysis_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    video: Mapped["Video | None"] = relationship(back_populates="thumbnails")
    project: Mapped["Project"] = relationship(back_populates="thumbnails")


class Theory(Base):
    """理論テーブル（動画企画の理論・フレームワーク管理）"""
    __tablename__ = "theories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # リレーション
    project: Mapped["Project | None"] = relationship(back_populates="theories")
