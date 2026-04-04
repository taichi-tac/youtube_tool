"""
台本生成サービスモジュール。
Anthropic Claude APIを使用してストリーミングで台本を生成する。
"""

from collections.abc import AsyncGenerator
from typing import Optional

import anthropic

from app.core.config import settings
from app.utils.prompt_builder import build_script_prompt


async def generate_script_stream(
    title: str,
    target_viewer: str = "一般視聴者",
    viewer_problem: Optional[str] = None,
    promise: Optional[str] = None,
    uniqueness: Optional[str] = None,
    additional_context: Optional[str] = None,
    rag_context: Optional[str] = None,
    comment_insights: Optional[str] = None,
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

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ストリーミングで台本生成（和理論ベース: 30,000文字以上の台本生成に対応）
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=64000,
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
