"""
アプリケーション設定モジュール。
pydantic-settingsを使用して環境変数から設定を読み込む。
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション全体の設定クラス"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === Supabase ===
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: str = ""

    # === 外部API ===
    YOUTUBE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # === Redis (オプション) ===
    REDIS_URL: Optional[str] = None

    # === CORS ===
    CORS_ORIGINS: str = "http://localhost:3000"

    # === 開発モード ===
    DEV_MODE: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS許可オリジンをリストとして返す"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def async_database_url(self) -> str:
        """非同期用のデータベースURLを返す（postgresql+asyncpg）"""
        url = self.SUPABASE_DB_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


# シングルトン設定インスタンス
settings = Settings()
