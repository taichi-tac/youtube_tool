"""
一気通貫パイプラインサービス。
伸びてる動画URL → 構造分析 → 企画提案 → 台本生成までを一貫して実行する。
"""

import json
import logging
import re
from typing import Any, Optional

import anthropic
import httpx

from app.core.config import settings
from app.services.rag_service import get_rag_context

logger = logging.getLogger(__name__)


async def analyze_video_structure(video_urls: list[str]) -> dict[str, Any]:
    """
    複数の伸びてる動画のURLから共通構造を分析する。

    1. 各動画のメタデータ取得
    2. 字幕/説明文から台本構造を推定
    3. 共通パターンを抽出
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # YouTube動画IDを抽出
    video_ids = []
    for url in video_urls:
        match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
        if match:
            video_ids.append(match.group(1))

    if not video_ids:
        return {"error": "有効なYouTube URLが見つかりません"}

    # YouTube Data APIで動画情報取得
    from app.services.youtube_service import get_video_details
    details = await get_video_details(video_ids)

    if not details:
        return {"error": "動画情報を取得できませんでした"}

    # 動画情報をプロンプトに変換
    video_summaries = []
    for d in details:
        video_summaries.append(
            f"タイトル: {d.get('title', '')}\n"
            f"チャンネル: {d.get('channel_title', '')}\n"
            f"再生数: {d.get('view_count', 0)}\n"
            f"説明文: {(d.get('description', '') or '')[:500]}"
        )

    prompt = f"""以下の{len(details)}本のYouTube動画を分析してください。

{chr(10).join(f'--- 動画{i+1} ---{chr(10)}{s}' for i, s in enumerate(video_summaries))}

## 分析してほしいこと
1. **共通構造**: これらの動画に共通する構成パターン（冒頭、展開、結末）
2. **成功要因**: なぜこれらの動画が伸びているか（3つ以上）
3. **市場の穴**: これらの動画がカバーしていない、まだ満たされていないニーズ
4. **企画提案**: 上記を踏まえた新しい企画案（5つ）。各企画にタイトル案と概要を付ける。

JSON形式で返してください:
{{
  "common_structure": {{"intro": "...", "development": "...", "conclusion": "..."}},
  "success_factors": ["要因1", "要因2", "要因3"],
  "market_gaps": ["穴1", "穴2", "穴3"],
  "proposals": [
    {{"title": "タイトル案", "concept": "コンセプト", "target": "ターゲット", "uniqueness": "差別化ポイント"}}
  ]
}}"""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
        result["analyzed_videos"] = [
            {"id": d.get("youtube_video_id"), "title": d.get("title"), "view_count": d.get("view_count")}
            for d in details
        ]
        return result

    except Exception as e:
        logger.error(f"動画構造分析エラー: {e}")
        return {"error": str(e)}


async def pipeline_to_script(
    video_urls: list[str],
    profile: dict[str, Any],
    db: Any = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """
    伸びてる動画URL → 構造分析 → 企画提案 → 台本ドラフト生成の一気通貫パイプライン。
    """
    # Step 1: 動画構造分析
    analysis = await analyze_video_structure(video_urls)
    if "error" in analysis:
        return analysis

    # Step 2: RAGコンテキスト取得
    rag_context = None
    if db and project_id:
        query = f"{profile.get('genre', '')} {analysis.get('market_gaps', [''])[0]}"
        rag_context = await get_rag_context(db=db, project_id=project_id, query=query)

    # Step 3: 最適な企画を選定して台本の方向性を決定
    proposals = analysis.get("proposals", [])
    best_proposal = proposals[0] if proposals else {"title": "無題", "concept": "", "target": "", "uniqueness": ""}

    return {
        "analysis": analysis,
        "selected_proposal": best_proposal,
        "rag_context_available": rag_context is not None,
        "ready_for_script": True,
        "script_params": {
            "title": best_proposal.get("title", ""),
            "target_viewer": best_proposal.get("target", profile.get("target_audience", "")),
            "viewer_problem": analysis.get("market_gaps", [""])[0] if analysis.get("market_gaps") else "",
            "promise": best_proposal.get("concept", ""),
            "uniqueness": best_proposal.get("uniqueness", profile.get("strengths", "")),
        },
    }
