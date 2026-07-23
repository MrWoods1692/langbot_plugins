from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from langbot_plugin.api.entities.builtin.provider import message as provider_message

from core.store import LearnStore


MAX_ANALYZED_MEMBERS = 12
MAX_MEMBER_SAMPLES = 8
MAX_RECENT_LOGS = 60


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


def _clean_text(text: Any, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    return cleaned[:limit]


def _member_fallback(member: dict[str, Any]) -> dict[str, Any]:
    message_count = int(member.get("message_count", 0) or 0)
    char_count = int(member.get("char_count", 0) or 0)
    emoji_count = int(member.get("emoji_count", 0) or 0)
    image_count = int(member.get("image_count", 0) or 0)
    avg_len = char_count / max(message_count, 1)

    if message_count >= 30:
        activity = "高频活跃"
    elif message_count >= 8:
        activity = "稳定参与"
    else:
        activity = "偶尔冒泡"

    habits: list[str] = []
    if avg_len >= 40:
        habits.append("偏长句输出")
    elif avg_len <= 8 and message_count > 0:
        habits.append("短句快打")
    if emoji_count:
        habits.append("表情使用明显")
    if image_count:
        habits.append("会用图片参与话题")

    return {
        "user_id": str(member.get("user_id", "?")),
        "message_count": message_count,
        "personality": f"{activity}型成员，基于现有发言量和表达长度判断。",
        "character_habits": "，".join(habits) or "数据仍少，暂以常规文字互动为主。",
    }


def _normalize_analysis(parsed: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    llm = parsed if isinstance(parsed, dict) else {}
    overview = llm.get("overview") if isinstance(llm.get("overview"), dict) else {}

    normalized: dict[str, Any] = {
        "overview": {
            "quality_review": _clean_text(
                overview.get("quality_review") or "群聊数据已收集，发言画像仍在积累中。",
                220,
            ),
            "active_periods": (
                overview.get("active_periods")
                if isinstance(overview.get("active_periods"), list)
                else []
            ),
            "group_vibe": _clean_text(overview.get("group_vibe") or "持续观察中", 60),
        },
        "members": [],
        "classic_quotes": [],
    }

    active_periods = [
        _clean_text(period, 32)
        for period in normalized["overview"]["active_periods"][:4]
        if _clean_text(period, 32)
    ]
    if not active_periods:
        active_periods = [
            f"{h['hour']}点({h['count']}条)"
            for h in raw.get("active_hours", [])[:4]
        ]
    normalized["overview"]["active_periods"] = active_periods

    llm_members = llm.get("members") if isinstance(llm.get("members"), list) else []
    by_user = {
        str(item.get("user_id")): item
        for item in llm_members
        if isinstance(item, dict) and item.get("user_id") is not None
    }
    for member in raw.get("members", [])[:MAX_ANALYZED_MEMBERS]:
        user_id = str(member.get("user_id", "?"))
        merged = _member_fallback(member)
        llm_member = by_user.get(user_id, {})
        if isinstance(llm_member, dict):
            merged["personality"] = _clean_text(
                llm_member.get("personality") or merged["personality"],
                100,
            )
            merged["character_habits"] = _clean_text(
                llm_member.get("character_habits") or merged["character_habits"],
                100,
            )
        normalized["members"].append(merged)

    seen_quotes: set[tuple[str, str]] = set()
    llm_quotes = (
        llm.get("classic_quotes")
        if isinstance(llm.get("classic_quotes"), list)
        else []
    )
    known_users = {str(m.get("user_id")) for m in raw.get("members", [])[:MAX_ANALYZED_MEMBERS]}
    known_texts = [
        item.get("text", "")
        for item in raw.get("message_log", [])
        if item.get("text")
    ]
    for quote in llm_quotes:
        if not isinstance(quote, dict):
            continue
        user_id = str(quote.get("user_id", "?"))
        text = _clean_text(quote.get("quote"), 120)
        if not text or user_id not in known_users:
            continue
        if not any(text in source or source in text for source in known_texts):
            continue
        key = (user_id, text)
        if key in seen_quotes:
            continue
        seen_quotes.add(key)
        normalized["classic_quotes"].append({
            "quote": text,
            "user_id": user_id,
            "comment": _clean_text(quote.get("comment") or "代表性发言", 60),
        })
        if len(normalized["classic_quotes"]) >= 6:
            break

    if not normalized["classic_quotes"]:
        for item in raw.get("message_log", [])[-6:]:
            text = _clean_text(item.get("text"), 120)
            if text and str(item.get("user_id")) in known_users:
                normalized["classic_quotes"].append({
                    "quote": text,
                    "user_id": str(item.get("user_id", "?")),
                    "comment": "近期代表发言",
                })
            if len(normalized["classic_quotes"]) >= 3:
                break

    return normalized


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
            "samples": [
                cleaned
                for sample in info.get("samples", [])
                if (cleaned := _clean_text(sample, 100))
            ][:MAX_MEMBER_SAMPLES],
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

    message_log = [
        {
            "user_id": str(item.get("user_id", "?")),
            "text": cleaned,
            "ts": item.get("ts"),
        }
        for item in stats.get("message_log", [])[-MAX_RECENT_LOGS:]
        if (cleaned := _clean_text(item.get("text"), 140))
    ]

    return {
        "group_key": group_key,
        "group_id": group_key.split("_", 1)[-1] if "_" in group_key else group_key,
        "total_messages": stats.get("total_messages", 0),
        "total_chars": stats.get("total_chars", 0),
        "total_images": stats.get("total_images", 0),
        "total_emojis": stats.get("total_emojis", 0),
        "participant_count": len(members_raw),
        "active_hours": [{"hour": int(h), "count": c} for h, c in active_hours],
        "members": members[:MAX_ANALYZED_MEMBERS],
        "member_overflow_count": max(len(members) - MAX_ANALYZED_MEMBERS, 0),
        "message_log": message_log,
        "top_slang": store.get_top_slang(group_key, 15),
    }


def _build_analysis_prompt(raw: dict[str, Any]) -> str:
    members_text = []
    for m in raw.get("members", [])[:MAX_ANALYZED_MEMBERS]:
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
    for item in raw.get("message_log", [])[-45:]:
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
1. members 只覆盖“各成员数据”里列出的成员，且每个成员必须出现一次
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
        "llm": _normalize_analysis(parsed, raw),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
