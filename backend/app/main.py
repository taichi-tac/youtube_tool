"""
FastAPIアプリケーション起動点。
YouTube運用支援ツール API のエントリーポイント。
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import content, keywords, knowledge, pipeline, planning, projects, scripts, thumbnails, theories, videos
from app.utils.cache import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーションのライフサイクル管理"""
    # 起動時の処理
    yield
    # 終了時の処理
    await close_redis()


import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube運用支援ツール API",
    description="YouTube動画の企画・台本作成・分析を支援するAPIサーバー",
    version="1.0.0",
    lifespan=lifespan,
    debug=True,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全例外をログに出力し、詳細をレスポンスに含める"""
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb},
    )

# === CORS設定 ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ルーター登録（/api/v1 プレフィックス） ===
API_V1_PREFIX = "/api/v1"

app.include_router(projects.router, prefix=API_V1_PREFIX)
app.include_router(keywords.router, prefix=API_V1_PREFIX)
app.include_router(videos.router, prefix=API_V1_PREFIX)
app.include_router(scripts.router, prefix=API_V1_PREFIX)
app.include_router(knowledge.router, prefix=API_V1_PREFIX)
app.include_router(thumbnails.router, prefix=API_V1_PREFIX)
app.include_router(theories.router, prefix=API_V1_PREFIX)
app.include_router(planning.router, prefix=API_V1_PREFIX)
app.include_router(pipeline.router, prefix=API_V1_PREFIX)
app.include_router(content.router, prefix=API_V1_PREFIX)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """ヘルスチェックエンドポイント"""
    return {"status": "ok", "version": "1.0.0"}
