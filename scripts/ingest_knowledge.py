"""
ナレッジmd全ファイルをDBにベクトル化して投入するスクリプト。
3つのZIP（和理論・市場分析・第二の脳）のmdファイルを処理する。
"""

import asyncio
import os
import sys
from pathlib import Path

# backendのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.services.rag_service import ingest_document

# ナレッジディレクトリとソースタイプのマッピング
KNOWLEDGE_DIRS = [
    {
        "path": "簡易第二の脳",
        "source_type": "second_brain",
        "label": "簡易第二の脳",
    },
    {
        "path": "市場から穴場を探す",
        "source_type": "market_analysis",
        "label": "市場から穴場を探す",
    },
    {
        "path": "和理論 企画作成から、台本まで、和理論を使って構築できる",
        "source_type": "wa_theory",
        "label": "和理論",
    },
]

# テスト用プロジェクトID（NULLにすると全ユーザー共有）
PROJECT_ID = None  # グローバルナレッジとして投入


async def main():
    base_dir = Path(__file__).parent.parent
    total_chunks = 0
    total_files = 0

    async with async_session_factory() as db:
        for dir_info in KNOWLEDGE_DIRS:
            dir_path = base_dir / dir_info["path"]
            if not dir_path.exists():
                print(f"  ❌ ディレクトリが見つかりません: {dir_path}")
                continue

            print(f"\n📂 {dir_info['label']} ({dir_path.name})")
            print(f"   ソースタイプ: {dir_info['source_type']}")

            md_files = sorted(dir_path.glob("*.md"))
            for md_file in md_files:
                content = md_file.read_text(encoding="utf-8")
                if not content.strip():
                    print(f"   ⏭️  {md_file.name} (空ファイル、スキップ)")
                    continue

                try:
                    chunk_count = await ingest_document(
                        db=db,
                        project_id=PROJECT_ID,
                        filename=md_file.name,
                        content=content,
                        source_type=dir_info["source_type"],
                        chunk_size=800,
                        chunk_overlap=150,
                    )
                    total_chunks += chunk_count
                    total_files += 1
                    print(f"   ✅ {md_file.name} → {chunk_count}チャンク")
                except Exception as e:
                    print(f"   ❌ {md_file.name} エラー: {e}")

        await db.commit()

    print(f"\n{'='*50}")
    print(f"✅ 投入完了: {total_files}ファイル → {total_chunks}チャンク")
    print(f"{'='*50}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
