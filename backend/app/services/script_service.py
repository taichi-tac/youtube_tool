"""
台本生成サービスモジュール。
Anthropic Claude APIを使用してストリーミングで台本を生成する。
"""

from collections.abc import AsyncGenerator
from typing import Optional

import anthropic

from app.core.config import settings
from app.utils.prompt_builder import build_script_prompt


import re as _re


def _parse_duration_from_context(additional_context: Optional[str]) -> int:
    """additional_contextから尺（分）を抽出する。見つからなければ15を返す。"""
    if not additional_context:
        return 15
    m = _re.search(r'約(\d+)分', additional_context)
    if m:
        return int(m.group(1))
    return 15


async def generate_script_stream(
    title: str,
    target_viewer: str = "一般視聴者",
    viewer_problem: Optional[str] = None,
    promise: Optional[str] = None,
    uniqueness: Optional[str] = None,
    additional_context: Optional[str] = None,
    rag_context: Optional[str] = None,
    comment_insights: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Claude APIを使用して台本をストリーミング生成する。

    Yields:
        生成されたテキストの各チャンク
    """
    # プロンプトを構築
    system_prompt, user_prompt = build_script_prompt(
        title=title,
        target_viewer=target_viewer,
        viewer_problem=viewer_problem,
        promise=promise,
        uniqueness=uniqueness,
        additional_context=additional_context,
        rag_context=rag_context,
        comment_insights=comment_insights,
    )

    from app.core.config import settings as _settings
    client = anthropic.AsyncAnthropic(api_key=anthropic_api_key or _settings.ANTHROPIC_API_KEY)

    # 尺から max_tokens を動的に計算（日本語1文字≒1.5トークン、50%バッファ＋JSON分1000）
    duration_min = _parse_duration_from_context(additional_context)
    target_chars = duration_min * 300
    max_tokens = int(target_chars * 1.5 * 1.5) + 1000  # 文字→トークン変換 × バッファ + JSON分

    # ストリーミングで台本生成
    async with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def generate_script_full(
    title: str,
    target_viewer: str = "一般視聴者",
    viewer_problem: Optional[str] = None,
    promise: Optional[str] = None,
    uniqueness: Optional[str] = None,
    additional_context: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> str:
    """
    Claude APIを使用して台本を一括生成する（非ストリーミング）。

    Returns:
        生成された台本テキスト全文
    """
    chunks: list[str] = []
    async for chunk in generate_script_stream(
        title=title,
        target_viewer=target_viewer,
        viewer_problem=viewer_problem,
        promise=promise,
        uniqueness=uniqueness,
        additional_context=additional_context,
        rag_context=rag_context,
    ):
        chunks.append(chunk)
    return "".join(chunks)
