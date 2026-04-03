"""
テキスト分割ユーティリティモジュール。
Markdown / プレーンテキストの分割処理を提供する。
"""

import re


def split_by_headings(text: str) -> list[dict[str, str]]:
    """
    Markdownテキストを見出し単位で分割する。

    Args:
        text: Markdownテキスト

    Returns:
        セクションリスト [{"heading": "...", "content": "..."}]
    """
    # 見出しパターン（# ~ ######）
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    sections: list[dict[str, str]] = []

    matches = list(heading_pattern.finditer(text))

    if not matches:
        # 見出しがない場合は全体を1セクションとして返す
        return [{"heading": "", "content": text.strip()}]

    # 最初の見出し前のテキスト
    if matches[0].start() > 0:
        pre_content = text[: matches[0].start()].strip()
        if pre_content:
            sections.append({"heading": "", "content": pre_content})

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append({"heading": heading, "content": content})

    return sections


def split_by_sentences(text: str, max_length: int = 1000) -> list[str]:
    """
    テキストを文単位で分割し、max_length以内のチャンクにまとめる。

    Args:
        text: 分割対象のテキスト
        max_length: チャンクの最大文字数

    Returns:
        分割されたテキストチャンクのリスト
    """
    # 日本語の文末パターン
    sentence_pattern = re.compile(r"(?<=[。！？\n])")
    sentences = sentence_pattern.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) > max_length and current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(sentence)
        current_length += len(sentence)

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


def count_tokens_approx(text: str) -> int:
    """
    テキストのトークン数を概算する（日本語は文字数 * 0.5、英語は単語数 * 1.3）。

    Args:
        text: 対象テキスト

    Returns:
        概算トークン数
    """
    # 日本語文字数
    ja_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]", text))
    # 英語単語数
    en_words = len(re.findall(r"[a-zA-Z]+", text))

    return int(ja_chars * 0.5 + en_words * 1.3)
