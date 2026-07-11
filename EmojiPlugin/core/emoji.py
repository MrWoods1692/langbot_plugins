from __future__ import annotations

import json
from typing import Any

import aiohttp

API_URL = "https://yunzhiapi.cn/API/emoji/"


async def emoji_fusion(
    token: str,
    go: str,
    to: str,
) -> dict[str, Any]:
    """Fuse two emojis into one via the Emoji API.

    Args:
        token: API authentication token.
        go: The first emoji.
        to: The second emoji.

    Returns:
        Parsed API response as a dictionary containing `text` and `url` fields.

    Raises:
        aiohttp.ClientError: On network or HTTP errors.
    """
    params: dict[str, str] = {
        "token": token,
        "go": go,
        "to": to,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params, timeout=30) as resp:
            text_response = await resp.text()

            # Try JSON first, fallback to plain text
            try:
                data = json.loads(text_response)
                return data
            except json.JSONDecodeError:
                # API may return plain text URL
                return {
                    "text": text_response.strip(),
                    "url": text_response.strip(),
                }


def format_emoji_result(data: dict[str, Any], go: str, to: str) -> str:
    """Format the emoji fusion API response into a readable message.

    API response structure:
        {"code": 1, "text": "获取成功", "data": {"url": "https://..."}}

    Args:
        data: The API response dictionary.
        go: The first emoji.
        to: The second emoji.

    Returns:
        Formatted string with the fusion result.
    """
    text = data.get("text", "")
    url = data.get("data", {}).get("url", "")

    if not url:
        return f"❌ 表情融合失败: 未获取到结果"

    lines = [
        f"🎨 表情融合结果",
        f"━━━━━━━━━━━━━━━━━━",
        f"{go} + {to} →",
        f"━━━━━━━━━━━━━━━━━━",
    ]
    if text and text != url:
        lines.append(f"描述: {text}")
    lines.append(f"链接: {url}")
    return "\n".join(lines)