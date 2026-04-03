"""
キーワードクロールタスク。
バックグラウンドでキーワードサジェストを一括取得する。
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Keyword
from app.services.keyword_service import alphabet_soup, extract_suggestions


async def crawl_keyword_suggestions(
    db: AsyncSession,
    project_id: uuid.UUID,
    seed_keywords: list[str],
    language: str = "ja",
    use_alphabet_soup: bool = False,
) -> dict[str, Any]:
    """
    シードキーワードリストからサジェストを一括取得してDBに保存する。

    Args:
        db: データベースセッション
        project_id: プロジェクトID
        seed_keywords: シードキーワードのリスト
        language: 言語コード
        use_alphabet_soup: アルファベットスープ法を使うか

    Returns:
        処理結果のサマリー
    """
    total_saved = 0
    total_skipped = 0
    errors: list[str] = []

    for seed in seed_keywords:
        try:
            if use_alphabet_soup:
                # アルファベットスープ法で取得
                results = await alphabet_soup(seed, language)
                suggestions: list[str] = []
                for char_suggestions in results.values():
                    suggestions.extend(char_suggestions)
            else:
                # 通常のサジェスト取得
                suggestions = await extract_suggestions(seed, language)

            # 重複除去
            seen: set[str] = set()
            unique_suggestions: list[str] = []
            for s in suggestions:
                if s not in seen:
                    seen.add(s)
                    unique_suggestions.append(s)

            # DB保存
            for suggestion in unique_suggestions:
                keyword = Keyword(
                    project_id=project_id,
                    keyword=suggestion,
                    source="related" if use_alphabet_soup else "youtube_suggest",
                    seed_keyword=seed,
                )
                db.add(keyword)
                total_saved += 1

        except Exception as e:
            errors.append(f"{seed}: {str(e)}")

    try:
        await db.flush()
    except Exception:
        # ユニーク制約違反等は個別にスキップ
        await db.rollback()
        # 1件ずつリトライ
        total_saved = 0
        for seed in seed_keywords:
            try:
                suggestions = await extract_suggestions(seed, language)
                for suggestion in suggestions:
                    try:
                        keyword = Keyword(
                            project_id=project_id,
                            keyword=suggestion,
                            source="youtube_suggest",
                            seed_keyword=seed,
                        )
                        db.add(keyword)
                        await db.flush()
                        total_saved += 1
                    except Exception:
                        await db.rollback()
                        total_skipped += 1
            except Exception:
                pass

    return {
        "total_saved": total_saved,
        "total_skipped": total_skipped,
        "errors": errors,
    }
