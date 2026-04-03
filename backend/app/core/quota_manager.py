"""
YouTube Data API v3 クォータ管理モジュール。
1日あたりの上限10,000ユニットを超えないよう使用量を追跡する。
"""

import asyncio
from datetime import date, datetime, timezone
from typing import Optional

from app.core.config import settings

# 各APIメソッドのクォータコスト定義
QUOTA_COSTS: dict[str, int] = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "commentThreads.list": 1,
    "playlistItems.list": 1,
    "captions.list": 50,
}

# 1日あたりのクォータ上限
DAILY_QUOTA_LIMIT: int = 10_000


class QuotaManager:
    """YouTube APIクォータの使用量を管理するクラス"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._used: int = 0
        self._date: date = datetime.now(timezone.utc).date()

    def _reset_if_new_day(self) -> None:
        """日付が変わっていたら使用量をリセットする"""
        today = datetime.now(timezone.utc).date()
        if today != self._date:
            self._used = 0
            self._date = today

    @property
    def remaining(self) -> int:
        """残りクォータを返す"""
        self._reset_if_new_day()
        return max(0, DAILY_QUOTA_LIMIT - self._used)

    @property
    def used(self) -> int:
        """使用済みクォータを返す"""
        self._reset_if_new_day()
        return self._used

    async def consume(self, method: str, count: int = 1) -> bool:
        """
        クォータを消費する。
        消費可能な場合はTrueを返し、上限超過の場合はFalseを返す。

        Args:
            method: APIメソッド名（例: "search.list"）
            count: 呼び出し回数
        """
        cost_per_call = QUOTA_COSTS.get(method, 1)
        total_cost = cost_per_call * count

        async with self._lock:
            self._reset_if_new_day()
            if self._used + total_cost > DAILY_QUOTA_LIMIT:
                return False
            self._used += total_cost
            return True

    async def check_available(self, method: str, count: int = 1) -> bool:
        """指定メソッドを呼び出すのに十分なクォータが残っているか確認する"""
        cost_per_call = QUOTA_COSTS.get(method, 1)
        total_cost = cost_per_call * count
        async with self._lock:
            self._reset_if_new_day()
            return self._used + total_cost <= DAILY_QUOTA_LIMIT

    def get_status(self) -> dict[str, int | str]:
        """現在のクォータ使用状況を返す"""
        self._reset_if_new_day()
        return {
            "date": self._date.isoformat(),
            "used": self._used,
            "remaining": self.remaining,
            "limit": DAILY_QUOTA_LIMIT,
        }


# シングルトンインスタンス
quota_manager = QuotaManager()
