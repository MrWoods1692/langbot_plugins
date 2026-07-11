from __future__ import annotations

import json
from typing import Any

import aiohttp

API_URL = "https://yunzhiapi.cn/API/saiyysc.php"


async def text_to_speech(
    token: str,
    text: str,
    response_type: str = "json",
) -> dict[str, Any]:
    """Convert text to speech via the TTS API.

    Args:
        token: API authentication token.
        text: The text content to be spoken.
        response_type: Response format — "json" or "wav". Defaults to "json".

    Returns:
        Parsed API response as a dictionary.

    Raises:
        ValueError: If the API returns an error status.
        aiohttp.ClientError: On network or HTTP errors.
    """
    params: dict[str, str] = {
        "token": token,
        "msg": text,
    }
    if response_type:
        params["type"] = response_type

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params, timeout=30) as resp:
            if response_type == "wav":
                # Return raw WAV data
                return {
                    "status": "success",
                    "data": {
                        "voice_data": await resp.read(),
                        "content_type": resp.content_type,
                    },
                }

            text_response = await resp.text()
            try:
                return json.loads(text_response)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": f"Failed to parse API response: {text_response[:200]}",
                }


def format_voice_result(data: dict[str, Any]) -> str:
    """Format the TTS API response into a readable message.

    Args:
        data: The API response dictionary.

    Returns:
        Formatted string with the voice URL.
    """
    if data.get("status") != "success":
        error_msg = data.get("message", str(data))
        return f"❌ 语音生成失败: {error_msg}"

    voice_data = data.get("data", {})
    voice_url = voice_data.get("voice", "")
    info = voice_data.get("info", {})

    if not voice_url:
        return "❌ 语音生成失败: 未获取到语音链接"

    lines = [
        f"🔊 语音已生成",
        f"━━━━━━━━━━━━━━━━━━",
        f"文本: {info.get('text', 'N/A')}",
        f"时间: {info.get('time', 'N/A')}",
        f"━━━━━━━━━━━━━━━━━━",
        f"语音链接: {voice_url}",
    ]
    return "\n".join(lines)