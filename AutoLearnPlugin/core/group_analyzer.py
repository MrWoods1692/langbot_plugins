from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from langbot_plugin.api.entities.builtin.provider import message as provider_message

from core.store import LearnStore


def _extract_llm_text(resp: provider_message.Message) -> str:
    if isinstance(resp.content, str):
        return resp.content.strip()
    if isinstance(resp.content, list):
        parts: list[str] = []
        for ce in resp.content:
            if hasattr(ce, "text") and ce.text:
                parts.append(ce.text)
        return "\n".join(parts).strip()
    return ""


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def collect_group_raw_data(store: LearnStore, group_key: str) -> dict[str, Any]:
    stats = store.data.get("group_stats", {}).get(group_key, {})
    members_raw = store.data.get("group_members", {}).get(group_key, {})
    members: list[dict[str, Any]] = []

    for user_key, info in members_raw.items():
        style = store.data["style_profiles"].get(user_key, {})
        rel = store.data["relationships"].get(user_key, {})
        members.append({
            "user_id": info.get("user_id", user_key),
            "message_count": info.get("message_count", 0),
            "char_count": info.get("char_count", 0),
            "image_count": info.get("image_count", 0),
            "emoji_count": info.get("emoji_count", 0),
            "samples": info.get("samples", [])[:12],
            "favorability": rel.get("favorability", 50),
            "mood": rel.get("mood", "neutral"),
            "common_phrases": sorted(
                style.get("common_phrases", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:8],
        })
    members.sort(key=lambda m: m["message_count"], reverse=True)

    hourly = stats.get("hourly", {})
    active_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:6]

    return {
        "group_key": group_key,
        "group_id": group_key.split("_", 1)[-1] if "_" in group_key else group_key,
        "total_messages": stats.get("total_messages", 0),
        "total_chars": stats.get("total_chars", 0),
        "total_images": stats.get("total_images", 0),
        "total_emojis": stats.get("total_emojis", 0),
        "participant_count": len(members_raw),
        "active_hours": [{"hour": int(h), "count": c} for h, c in active_hours],
        "members": members,
        "message_log": stats.get("message_log", [])[-80:],
        "top_slang": store.get_top_slang(group_key, 15),
    }


def _build_analysis_prompt(raw: dict[str, Any]) -> str:
    members_text = []
    for m in raw.get("members", [])[:15]:
        phrases = ", ".join(f"{p}({c})" for p, c in m.get("common_phrases", [])[:5])
        samples = "\n".join(f"    - {s}" for s in m.get("samples", [])[:6])
        members_text.append(
            f"用户 {m['user_id']}: 消息{m['message_count']}条, "
            f"字符{m['char_count']}, 图片{m['image_count']}, 表情{m['emoji_count']}, "
            f"好感度{m.get('favorability', 50):.0f}\n"
            f"  常用语: {phrases or '无'}\n"
            f"  发言样本:\n{samples or '    - 无'}"
        )

    hours = raw.get("active_hours", [])
    hours_text = ", ".join(f"{h['hour']}点({h['count']}条)" for h in hours) or "数据不足"

    log_lines = []
    for item in raw.get("message_log", [])[-50:]:
        log_lines.append(f"[{item.get('user_id')}] {item.get('text', '')[:100]}")

    slang_lines = [
        f"{s['word']}({s['count']}次)" for s in raw.get("top_slang", [])[:10]
    ]

    return f"""你是一位毒舌但精准的群聊社会学家。请根据以下群聊统计数据和发言记录，输出 JSON 分析报告。

## 群基础数据
- 群号: {raw.get('group_id')}
- 总消息: {raw.get('total_messages')} 条
- 参与人数: {raw.get('participant_count')} 人
- 总字符数: {raw.get('total_chars')}
- 总图片数: {raw.get('total_images')}
- 总表情数: {raw.get('total_emojis')}
- 活跃时段: {hours_text}
- 高频词: {', '.join(slang_lines) or '无'}

## 各成员数据
{chr(10).join(members_text) or '暂无成员数据'}

## 近期群聊记录（节选）
{chr(10).join(log_lines) or '暂无记录'}

请严格输出以下 JSON（不要输出其他内容）:
{{
  "overview": {{
    "quality_review": "群聊质量锐评，200字以内，辛辣幽默",
    "active_periods": ["活跃时段描述，如 20-22点"],
    "group_vibe": "群整体氛围一句话概括"
  }},
  "members": [
    {{
      "user_id": "用户ID",
      "message_count": 0,
      "personality": "人格分析，80字以内",
      "character_habits": "性格、爱好、说话习惯，80字以内"
    }}
  ],
  "classic_quotes": [
    {{"quote": "经典原句", "user_id": "发言人", "comment": "一句话点评"}}
  ]
}}

要求:
1. members 覆盖所有有发言的成员
2. classic_quotes 摘抄 3-6 条最有代表性的原句
3. 分析要基于实际数据，不要编造不存在的用户
4. 全部用中文"""


async def analyze_group_with_llm(plugin, group_key: str) -> dict[str, Any]:
    raw = collect_group_raw_data(plugin.store, group_key)
    if raw["total_messages"] == 0:
        return {"error": "暂无群聊学习数据，继续聊天后会自动生成分析。"}

    model_uuid = plugin.get_config().get("llm_model", "")
    if not model_uuid:
        return {"error": "请先在插件配置中选择 LLM 模型，群分析需要 LLM 支持。"}

    prompt = _build_analysis_prompt(raw)
    try:
        resp = await plugin.invoke_llm(
            model_uuid,
            [provider_message.Message(role="user", content=prompt)],
            timeout=120,
        )
        llm_text = _extract_llm_text(resp)
        parsed = _parse_llm_json(llm_text)
        if not parsed:
            return {
                "error": "LLM 返回格式异常，请重试",
                "raw": raw,
                "llm_raw": llm_text[:500],
            }
    except Exception as e:
        return {"error": f"LLM 分析失败: {e}", "raw": raw}

    return {
        "raw": raw,
        "llm": parsed,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
