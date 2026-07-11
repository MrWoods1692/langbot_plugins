from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            test = current + ch
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def _estimate_height(analysis: dict[str, Any]) -> int:
    llm = analysis.get("llm", {})
    members = llm.get("members", [])
    quotes = llm.get("classic_quotes", [])
    overview = llm.get("overview", {})
    base = 520
    base += len(_wrap_text(overview.get("quality_review", ""), _font(15), 820)) * 22
    base += len(members) * 130
    base += len(quotes) * 55
    return min(max(base, 1200), 3600)


def generate_group_chart(analysis: dict[str, Any]) -> str:
    """Render LLM-powered group analysis report image."""
    raw = analysis.get("raw", {})
    llm = analysis.get("llm", {})
    overview = llm.get("overview", {})

    width = 900
    height = _estimate_height(analysis)
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)

    title_font = _font(26)
    head_font = _font(19)
    body_font = _font(15)
    small_font = _font(13)

    accent = "#38bdf8"
    muted = "#94a3b8"
    card = "#1e293b"
    green = "#4ade80"
    yellow = "#fbbf24"
    pink = "#f472b6"
    orange = "#fb923c"

    y = 24
    draw.text((32, y), f"群聊深度分析报告 · {raw.get('group_id', '?')}", fill=accent, font=title_font)
    y += 38
    draw.text(
        (32, y),
        f"LLM 分析 · {analysis.get('generated_at', '')} · "
        f"氛围: {overview.get('group_vibe', '分析中')}",
        fill=muted,
        font=small_font,
    )
    y += 32

    def card_box(x: int, cy: int, w: int, h: int, label: str, value: str, color: str) -> None:
        draw.rounded_rectangle((x, cy, x + w, cy + h), radius=10, fill=card)
        draw.text((x + 12, cy + 10), label, fill=muted, font=small_font)
        draw.text((x + 12, cy + 30), value, fill=color, font=head_font)

    card_box(32, y, 130, 64, "总消息", str(raw.get("total_messages", 0)), accent)
    card_box(172, y, 130, 64, "参与人数", str(raw.get("participant_count", 0)), green)
    card_box(312, y, 130, 64, "总字符", str(raw.get("total_chars", 0)), yellow)
    card_box(452, y, 130, 64, "总图片", str(raw.get("total_images", 0)), pink)
    card_box(592, y, 130, 64, "总表情", str(raw.get("total_emojis", 0)), orange)
    card_box(732, y, 136, 64, "高频词", str(len(raw.get("top_slang", []))), "#a78bfa")
    y += 80

    periods = overview.get("active_periods") or [
        f"{h['hour']}点({h['count']}条)" for h in raw.get("active_hours", [])[:4]
    ]
    draw.text((32, y), "活跃时段", fill="#e2e8f0", font=head_font)
    y += 28
    draw.text((32, y), " · ".join(periods) or "数据积累中", fill="#cbd5e1", font=body_font)
    y += 36

    draw.text((32, y), "群聊质量锐评", fill="#f87171", font=head_font)
    y += 28
    for line in _wrap_text(overview.get("quality_review", "暂无锐评"), body_font, 820):
        draw.text((32, y), line, fill="#fecaca", font=body_font)
        y += 22
    y += 16

    draw.text((32, y), "成员深度分析", fill="#e2e8f0", font=head_font)
    y += 28
    llm_members = {m.get("user_id"): m for m in llm.get("members", [])}
    for member in raw.get("members", [])[:12]:
        uid = str(member.get("user_id", "?"))
        llm_m = llm_members.get(uid, {})
        draw.rounded_rectangle((32, y, 868, y + 118), radius=10, fill=card)
        draw.text((44, y + 10), f"👤 {uid}", fill=accent, font=body_font)
        draw.text(
            (44, y + 32),
            f"消息{member.get('message_count', 0)} · "
            f"字符{member.get('char_count', 0)} · "
            f"图片{member.get('image_count', 0)} · "
            f"表情{member.get('emoji_count', 0)}",
            fill=muted,
            font=small_font,
        )
        personality = llm_m.get("personality", "人格分析生成中...")
        habits = llm_m.get("character_habits", "")
        for i, line in enumerate(_wrap_text(f"人格: {personality}", small_font, 780)[:2]):
            draw.text((44, y + 52 + i * 18), line, fill="#cbd5e1", font=small_font)
        habit_lines = _wrap_text(f"习惯: {habits}", small_font, 780)[:2]
        for i, line in enumerate(habit_lines):
            draw.text((44, y + 88 + i * 18), line, fill="#94a3b8", font=small_font)
        y += 128

    y += 8
    draw.text((32, y), "群内经典语句摘抄", fill="#e2e8f0", font=head_font)
    y += 28
    quotes = llm.get("classic_quotes", [])
    if quotes:
        for q in quotes[:6]:
            quote = q.get("quote", "")
            user = q.get("user_id", "?")
            comment = q.get("comment", "")
            draw.text((32, y), f"「{quote[:60]}」", fill=yellow, font=body_font)
            y += 22
            draw.text((48, y), f"— {user} · {comment[:50]}", fill=muted, font=small_font)
            y += 26
    else:
        draw.text((32, y), "经典语句生成中...", fill=muted, font=body_font)
        y += 24

    draw.text((32, height - 32), "AutoLearn · LLM 群分析 qfx", fill="#475569", font=small_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
