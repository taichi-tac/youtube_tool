"""
データベース接続モジュール。
SQLAlchemy非同期セッション・Base宣言・依存関数を提供。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Supabase Pooler (Transaction mode) 用設定
# prepared_statement_cache_size=0 でprepared statements無効化
_connect_args = {}
_db_url = settings.async_database_url
if "pooler.supabase.com" in _db_url:
    _connect_args = {
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    }

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

# 非同期セッションファクトリ
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """全モデルの基底クラス"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依存関数: 非同期DBセッションを提供する"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
