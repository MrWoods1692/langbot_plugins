from __future__ import annotations

import json
from typing import Any

import aiohttp

API_URL = "https://yunzhiapi.cn/API/qqsqcx.php"


async def query_timezone(
    token: str,
    country: str,
    kind: str,
    response_type: str = "json",
) -> dict[str, Any]:
    """Query global timezone information from the API.

    Args:
        token: API authentication token.
        country: Country name, supports Chinese and English.
        kind: Timezone type — "UST" (US Time) or "CST" (China Standard Time).
        response_type: Response format — "json" or "text". Defaults to "json".

    Returns:
        Parsed API response as a dictionary.
    """
    params: dict[str, str] = {
        "token": token,
        "country": country,
        "kind": kind,
    }
    if response_type:
        params["type"] = response_type

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params, timeout=15) as resp:
            text = await resp.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": False, "error": True, "code": 500, "data": text}


def format_timezone_result(data: dict[str, Any]) -> str:
    """Format the API response into a human-readable text message.

    Args:
        data: The API response dictionary.

    Returns:
        Formatted string for display.
    """
    if not data.get("success"):
        error_msg = data.get("data", str(data))
        return f"❌ 查询失败: {error_msg}"

    d = data.get("data", {})
    lines = [
        f"🌍 时区查询结果",
        f"━━━━━━━━━━━━━━━━━━",
        f"国家: {d.get('country_cn', 'N/A')} ({d.get('country_en', 'N/A')})",
        f"首都: {d.get('capital', 'N/A')}",
        f"标准时区: {d.get('timezone', 'N/A')}",
        f"UTC 偏移: {d.get('utc_offset', 'N/A')}",
        f"━━━━━━━━━━━━━━━━━━",
        f"时区类型: {d.get('kind', 'N/A')}",
        f"时区名称: {d.get('kind_tz_name', 'N/A')} ({d.get('kind_tz_name_cn', 'N/A')})",
        f"时区偏移: {d.get('kind_tz_offset', 'N/A')}",
        f"代表城市: {d.get('kind_tz_city', 'N/A')}",
        f"━━━━━━━━━━━━━━━━━━",
        f"当地时间: {d.get('local_time', 'N/A')}",
        f"北京时间: {d.get('query_time_beijing', 'N/A')}",
        f"UTC 时间: {d.get('query_time_utc', 'N/A')}",
        f"时差: {d.get('time_diff', 'N/A')}",
    ]
    return "\n".join(lines)