"""
キーワードサジェストサービスモジュール。
YouTube Suggest APIを使用してサジェストキーワードを取得する。
"""

import string
from typing import Any

import httpx

# YouTube Suggest APIエンドポイント
SUGGEST_URL = "https://suggestqueries-clients6.youtube.com/complete/search"


async def extract_suggestions(
    seed_keyword: str,
    language: str = "ja",
) -> list[str]:
    """
    シードキーワードからYouTubeサジェストを取得する。

    Args:
        seed_keyword: 元となるキーワード
        language: 言語コード（ja, enなど）

    Returns:
        サジェストキーワードのリスト
    """
    params: dict[str, str] = {
        "client": "youtube",
        "ds": "yt",
        "q": seed_keyword,
        "hl": language,
        "gl": "JP" if language == "ja" else "US",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(SUGGEST_URL, params=params)
        response.raise_for_status()

    # レスポンスはJSONP形式: window.google.ac.h([ ... ])
    text = response.text
    # JSONPからJSON部分を抽出
    start = text.index("[")
    data: list[Any] = _parse_jsonp(text[start:])

    suggestions: list[str] = []
    if len(data) > 1 and isinstance(data[1], list):
        for item in data[1]:
            if isinstance(item, list) and len(item) > 0:
                suggestions.append(str(item[0]))

    return suggestions


def _parse_jsonp(text: str) -> list[Any]:
    """JSONP形式のテキストからリストをパースする"""
    import json
    # 末尾の閉じ括弧等を除去して純粋なJSONを取得
    cleaned = text.strip()
    if cleaned.endswith(")"):
        cleaned = cleaned[:-1]
    return json.loads(cleaned)  # type: ignore[no-any-return]


async def alphabet_soup(
    seed_keyword: str,
    language: str = "ja",
    include_numbers: bool = False,
) -> dict[str, list[str]]:
    """
    アルファベットスープ法：シードキーワード + a〜z の各文字でサジェストを取得する。

    Args:
        seed_keyword: 元となるキーワード
        language: 言語コード
        include_numbers: 0-9も含めるか

    Returns:
        文字をキー、サジェストリストを値とする辞書
    """
    characters: list[str] = list(string.ascii_lowercase)
    if include_numbers:
        characters.extend([str(i) for i in range(10)])

    # あ行〜わ行のひらがなも追加（日本語の場合）
    if language == "ja":
        hiragana = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわ")
        characters.extend(hiragana)

    results: dict[str, list[str]] = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for char in characters:
            query = f"{seed_keyword} {char}"
            params: dict[str, str] = {
                "client": "youtube",
                "ds": "yt",
                "q": query,
                "hl": language,
                "gl": "JP" if language == "ja" else "US",
            }
            try:
                response = await client.get(SUGGEST_URL, params=params)
                response.raise_for_status()
                text = response.text
                start = text.index("[")
                data: list[Any] = _parse_jsonp(text[start:])
                suggestions: list[str] = []
                if len(data) > 1 and isinstance(data[1], list):
                    for item in data[1]:
                        if isinstance(item, list) and len(item) > 0:
                            suggestions.append(str(item[0]))
                results[char] = suggestions
            except Exception:
                # 個別のリクエスト失敗は無視して続行
                results[char] = []

    return results
