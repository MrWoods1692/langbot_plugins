from __future__ import annotations

import base64
import io
import math
import urllib.error
import urllib.request
from typing import Any

from PIL import Image, ImageDraw, ImageFont


_AVATAR_CACHE: dict[str, Image.Image | None] = {}


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
            try:
                bbox = font.getbbox(test)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(test) * (font.size // 2)
            if tw <= max_width:
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
    base = 600
    base += len(_wrap_text(overview.get("quality_review", ""), _font(15), 760)) * 24
    if analysis.get("raw", {}).get("top_slang"):
        base += 86
    member_rows = math.ceil(len(members) / 2)
    base += member_rows * 178
    base += max(1, len(quotes)) * 108
    return min(max(base, 1550), 4600)


def _text_width(font: ImageFont.ImageFont, text: str) -> int:
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except Exception:
        size = getattr(font, "size", 12)
        return len(text) * (size // 2)


def _fit_text(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if _text_width(font, text) <= max_width:
        return text
    suffix = "..."
    current = ""
    for ch in text:
        if _text_width(font, current + ch + suffix) > max_width:
            break
        current += ch
    return current + suffix if current else suffix


def _get_qq_avatar(user_id: str, size: int = 100) -> Image.Image | None:
    qq = "".join(ch for ch in str(user_id) if ch.isdigit())
    if not qq:
        return None
    cache_key = f"{qq}:{size}"
    if cache_key in _AVATAR_CACHE:
        cached = _AVATAR_CACHE[cache_key]
        return cached.copy() if cached else None

    url = f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s={size}"
    try:
        with urllib.request.urlopen(url, timeout=1.2) as resp:
            data = resp.read(1024 * 256)
        avatar = Image.open(io.BytesIO(data)).convert("RGB")
        _AVATAR_CACHE[cache_key] = avatar.copy()
        return avatar
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        _AVATAR_CACHE[cache_key] = None
        return None


def _draw_member_avatar(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
    user_id: str,
    accent: str,
    font: ImageFont.ImageFont,
) -> None:
    avatar = _get_qq_avatar(user_id, size=100)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    draw.ellipse((x - 4, y + 3, x + size + 4, y + size + 11), fill="#dce3dd")
    draw.ellipse((x - 3, y - 3, x + size + 3, y + size + 3), fill="#ffffff")
    draw.ellipse((x - 5, y - 5, x + size + 5, y + size + 5), outline=accent, width=2)
    if avatar:
        avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        img.paste(avatar, (x, y), mask)
        return

    draw.ellipse((x, y, x + size, y + size), fill=accent)
    avatar_text = _fit_text(user_id[-2:], font, size - 14)
    tw = _text_width(font, avatar_text)
    draw.text((x + (size - tw) / 2, y + size / 2 - 12), avatar_text, fill="#ffffff", font=font)


def _lerp_color(start: str, end: str, ratio: float) -> tuple[int, int, int]:
    s = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
    e = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(s[i] + (e[i] - s[i]) * ratio) for i in range(3))


def _draw_vertical_gradient(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    top: str,
    bottom: str,
) -> None:
    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line((0, y, width, y), fill=_lerp_color(top, bottom, ratio))


def _draw_background(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    _draw_vertical_gradient(draw, width, height, "#f8efe2", "#e8f3ec")
    draw.polygon((0, 0, 900, 0, 900, 250, 0, 430), fill="#f2dfc4")
    draw.polygon((0, 315, 900, 120, 900, 220, 0, 450), fill="#dceee7")
    for offset in range(-180, 980, 180):
        draw.line((offset, 0, offset + 540, 460), fill="#f8f2e8", width=10)
    for px in range(58, width, 84):
        for py in range(52, 396, 68):
            draw.ellipse((px, py, px + 3, py + 3), fill="#ead7ba")
    draw.rectangle((0, 430, width, height), fill="#eef5ef")
    for py in range(500, height, 92):
        draw.line((36, py, width - 36, py), fill="#e4ece5", width=1)


def _draw_section_header(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    title: str,
    subtitle: str,
    color: str,
    font_title: ImageFont.ImageFont,
    font_sub: ImageFont.ImageFont,
    text_color: str,
    sub_color: str,
) -> None:
    draw.rounded_rectangle((x, y + 2, x + 6, y + 30), radius=3, fill=color)
    draw.text((x + 16, y), title, fill=text_color, font=font_title)
    if subtitle:
        draw.text((x + 116, y + 4), subtitle, fill=sub_color, font=font_sub)


def _draw_card(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    radius: int = 12,
    shadow: bool = True,
    fill: str = "#ffffff",
) -> None:
    if shadow:
        for idx, color in enumerate(("#d9ded8", "#e6e9e3", "#eef0eb"), 1):
            grow = idx * 2
            draw.rounded_rectangle(
                (x - grow, y + idx * 3, x + w + grow, y + h + idx * 3 + grow),
                radius=radius + grow,
                fill=color,
            )
    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=radius, fill=fill, outline="#e9f0eb",
    )


def _draw_tag(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, text: str,
    color: str, bg: str,
) -> int:
    f = _font(12)
    tw = f.getbbox(text)[2] - f.getbbox(text)[0]
    pw = tw + 22
    draw.rounded_rectangle((x, y, x + pw, y + 26), radius=13, fill=bg)
    draw.text((x + 11, y + 5), text, fill=color, font=f)
    return x + pw


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, text: str,
    color: str, bg: str,
) -> None:
    f = _font(10)
    tw = f.getbbox(text)[2] - f.getbbox(text)[0]
    pw = tw + 14
    draw.rounded_rectangle((x, y, x + pw, y + 20), radius=5, fill=bg)
    draw.text((x + 7, y + 3), text, fill=color, font=f)


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: str,
    bg: str,
    font: ImageFont.ImageFont,
    max_width: int = 180,
) -> int:
    label = _fit_text(text, font, max_width - 24)
    width = min(max_width, _text_width(font, label) + 24)
    draw.rounded_rectangle((x, y, x + width, y + 28), radius=14, fill=bg)
    draw.text((x + 12, y + 6), label, fill=color, font=font)
    return x + width + 8


def _draw_pulse_mark(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    total_messages: int,
    participant_count: int,
    slang_count: int,
    colors: dict[str, str],
) -> None:
    max_value = max(total_messages, participant_count * 18, slang_count * 28, 1)
    rings = [
        (total_messages / max_value, colors["teal"], 64),
        ((participant_count * 18) / max_value, colors["gold"], 50),
        ((slang_count * 28) / max_value, colors["coral"], 36),
    ]
    draw.ellipse((cx - 78, cy - 78, cx + 78, cy + 78), outline="#334540", width=2)
    draw.ellipse((cx - 62, cy - 62, cx + 62, cy + 62), outline="#263733", width=8)
    start = -90
    for ratio, color, radius in rings:
        end = start + max(24, int(330 * min(ratio, 1.0)))
        draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), start, end, fill=color, width=8)
        start += 38
    draw.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill="#fff4df")
    draw.text((cx - 18, cy - 17), str(participant_count), fill=colors["ink"], font=_font(24))
    draw.text((cx - 20, cy + 10), "成员", fill="#6f7e77", font=_font(10))


def generate_group_chart(analysis: dict[str, Any]) -> str:
    """Render a polished group analysis report image."""
    raw = analysis.get("raw", {})
    llm = analysis.get("llm", {})
    overview = llm.get("overview", {})

    width = 900
    height = _estimate_height(analysis)
    img = Image.new("RGB", (width, height), "#f6f2e8")
    draw = ImageDraw.Draw(img)

    _draw_background(draw, width, height)

    f_title = _font(34)
    f_big = _font(28)
    f_sub = _font(13)
    f_head = _font(16)
    f_body = _font(14)
    f_small = _font(12)
    f_tiny = _font(10)

    C = {
        "ink": "#18211f",
        "text": "#20302d",
        "text2": "#52605b",
        "text3": "#859089",
        "text4": "#a8b0aa",
        "card": "#ffffff",
        "line": "#dfe8e2",
        "teal": "#16877c",
        "teal_bg": "#e2f4f0",
        "blue": "#315f9f",
        "blue_bg": "#e6eefb",
        "coral": "#d86145",
        "coral_bg": "#fbeae4",
        "gold": "#c08a20",
        "gold_bg": "#fbf0d5",
        "green": "#3d8b4f",
        "green_bg": "#e7f4e8",
        "slate": "#59636f",
        "slate_bg": "#eef1f2",
    }

    y = 24

    gid = raw.get("group_id", "?")
    gen = analysis.get("generated_at", "")
    vibe = _fit_text(str(overview.get("group_vibe", "持续观察中")), f_sub, 310)

    _draw_card(draw, 24, y, 852, 190, radius=22, fill=C["ink"])
    draw.polygon((638, y, 876, y, 876, y + 190, 570, y + 190), fill="#22332e")
    draw.polygon((724, y, 876, y, 876, y + 190, 686, y + 190), fill="#2d4039")
    for bx in range(24, 876):
        ratio = (bx - 24) / 852
        draw.line((bx, y + 182, bx, y + 190), fill=_lerp_color("#18a58f", "#efb547", ratio))
    draw.rounded_rectangle((50, y + 28, 158, y + 56), radius=14, fill="#2b3935")
    draw.text((66, y + 35), "AUTOLEARN", fill="#d7e8df", font=f_tiny)
    draw.text((48, y + 70), "群聊社会学报告", fill="#fffaf0", font=f_title)
    draw.text((52, y + 120), f"Group {gid} / {gen}", fill="#b9cac3", font=f_sub)
    draw.text((52, y + 146), vibe, fill="#f0dca9", font=f_sub)

    total_messages = int(raw.get("total_messages", 0) or 0)
    participant_count = int(raw.get("participant_count", 0) or 0)
    slang_count = len(raw.get("top_slang", []))
    _draw_pulse_mark(draw, 716, y + 94, total_messages, participant_count, slang_count, C)
    draw.text((598, y + 148), f"消息 {total_messages}", fill="#d7e8df", font=f_tiny)
    draw.text((678, y + 148), f"热词 {slang_count}", fill="#f0dca9", font=f_tiny)
    draw.text((748, y + 148), "群体脉冲", fill="#d7b7a9", font=f_tiny)
    y += 218

    stats = [
        ("总字符", str(raw.get("total_chars", 0)), C["blue"], C["blue_bg"]),
        ("图片", str(raw.get("total_images", 0)), C["coral"], C["coral_bg"]),
        ("表情", str(raw.get("total_emojis", 0)), C["gold"], C["gold_bg"]),
        ("活跃时段", str(len(raw.get("active_hours", []))), C["green"], C["green_bg"]),
    ]
    max_stat = max((int(val) for _, val, _, _ in stats if val.isdigit()), default=1)
    for i, (label, val, color, bg) in enumerate(stats):
        cx = 24 + i * 216
        _draw_card(draw, cx, y, 204, 92, radius=18)
        draw.rounded_rectangle((cx + 144, y, cx + 204, y + 92), radius=18, fill="#f8fbf8")
        draw.rounded_rectangle((cx + 18, y + 18, cx + 50, y + 50), radius=10, fill=bg)
        draw.ellipse((cx + 30, y + 30, cx + 38, y + 38), fill=color)
        draw.text((cx + 66, y + 20), label, fill=C["text3"], font=f_small)
        draw.text((cx + 66, y + 48), _fit_text(val, f_head, 120), fill=C["text"], font=f_head)
        ratio = int(val) / max_stat if val.isdigit() else 0
        draw.rounded_rectangle((cx + 18, y + 74, cx + 186, y + 80), radius=3, fill="#e6eee8")
        draw.rounded_rectangle((cx + 18, y + 74, cx + 18 + int(168 * ratio), y + 80), radius=3, fill=color)
    y += 116

    _draw_card(draw, 24, y, 852, 78, radius=18)
    periods = overview.get("active_periods") or [
        f"{h['hour']}:00 ({h['count']}条)" for h in raw.get("active_hours", [])[:4]
    ]
    draw.text((44, y + 20), "活跃时间", fill=C["text"], font=f_head)
    px = 142
    for period in periods[:4]:
        px = _draw_pill(draw, px, y + 20, str(period), C["teal"], C["teal_bg"], f_small, 156)
    if not periods:
        draw.text((142, y + 22), "数据还不够，等大家多聊几句。", fill=C["text3"], font=f_body)
    y += 104

    review = str(overview.get("quality_review", "暂无锐评"))
    rlines = _wrap_text(review, f_body, 756)
    rh = max(104, len(rlines) * 24 + 70)
    _draw_card(draw, 24, y, 852, rh, radius=20)
    draw.rounded_rectangle((44, y + 24, 56, y + rh - 24), radius=6, fill=C["coral"])
    draw.text((76, y + 22), "群聊锐评", fill=C["text"], font=f_head)
    for i, line in enumerate(rlines):
        draw.text((76, y + 58 + i * 24), line, fill=C["text2"], font=f_body)
    y += rh + 28

    top_slang = raw.get("top_slang", [])[:8]
    if top_slang:
        _draw_section_header(
            draw, 32, y, "高频词", "群里最近最有存在感的词", C["gold"],
            f_head, f_small, C["text"], C["text3"],
        )
        y += 42
        _draw_card(draw, 24, y, 852, 58, radius=14)
        sx = 44
        for item in top_slang:
            text = f"{item.get('word', '?')} x{item.get('count', 0)}"
            sx = _draw_pill(draw, sx, y + 15, text, C["gold"], C["gold_bg"], f_small, 130)
            if sx > 790:
                break
        y += 84

    overflow = raw.get("member_overflow_count", 0)
    subtitle = f"展示前 {len(raw.get('members', []))} 位活跃成员"
    if overflow:
        subtitle += f"，另有 {overflow} 位未展示"
    _draw_section_header(draw, 32, y, "成员画像", subtitle, C["teal"], f_head, f_small, C["text"], C["text3"])
    y += 46

    llm_members = {m.get("user_id"): m for m in llm.get("members", [])}
    raw_members = raw.get("members", [])[:12]
    max_msg = max((m.get("message_count", 1) for m in raw_members), default=1)

    apal = [C["teal"], C["blue"], C["coral"], C["gold"], C["green"], C["slate"]]

    col_w = 410
    col_gap = 16
    col_start_x = 32

    for pair_idx in range(0, len(raw_members), 2):
        pair = raw_members[pair_idx:pair_idx + 2]
        max_h = 0
        member_data = []
        for member in pair:
            uid = str(member.get("user_id", "?"))
            llm_m = llm_members.get(uid, {})
            mc = member.get("message_count", 0)
            cc = member.get("char_count", 0)
            ic = member.get("image_count", 0)
            ec = member.get("emoji_count", 0)
            pers = llm_m.get("personality", "画像生成中")
            hab = llm_m.get("character_habits", "")
            pl = _wrap_text(str(pers), f_small, 344)[:2]
            hl = _wrap_text(str(hab), f_small, 344)[:2]
            h = 174
            max_h = max(max_h, h)
            rank = pair_idx + len(member_data) + 1
            member_data.append((uid, llm_m, mc, cc, ic, ec, pl, hl, rank))

        for col_idx, (uid, llm_m, mc, cc, ic, ec, pl, hl, rank) in enumerate(member_data):
            cx = col_start_x + col_idx * (col_w + col_gap)
            ac = apal[(pair_idx + col_idx) % len(apal)]

            _draw_card(draw, cx, y, col_w, max_h, radius=14)
            draw.rounded_rectangle((cx, y, cx + col_w, y + 6), radius=5, fill=ac)
            _draw_member_avatar(img, draw, cx + 18, y + 22, 46, uid, ac, f_head)
            draw.text((cx + 74, y + 22), _fit_text(uid, f_head, 190), fill=C["text"], font=f_head)
            draw.text((cx + 74, y + 48), f"{mc} 条消息 / {cc} 字", fill=C["text3"], font=f_small)
            draw.rounded_rectangle((cx + 294, y + 52, cx + 386, y + 74), radius=11, fill="#f6faf7")
            draw.text((cx + 314, y + 57), f"TOP {rank:02d}", fill=ac, font=f_tiny)
            _draw_badge(draw, cx + 292, y + 24, f"图 {ic}", C["coral"], C["coral_bg"])
            _draw_badge(draw, cx + 342, y + 24, f"表 {ec}", C["gold"], C["gold_bg"])

            draw.rounded_rectangle((cx + 18, y + 82, cx + col_w - 18, y + 92), radius=5, fill=C["line"])
            if max_msg > 0:
                fw = max(8, int((mc / max_msg) * (col_w - 36)))
                draw.rounded_rectangle((cx + 18, y + 82, cx + 18 + fw, y + 92), radius=5, fill=ac)

            draw.text((cx + 18, y + 106), "性格", fill=ac, font=f_tiny)
            for i, line in enumerate(pl):
                draw.text((cx + 58, y + 102 + i * 19), line, fill=C["text2"], font=f_small)

            draw.text((cx + 18, y + 138), "习惯", fill=C["text3"], font=f_tiny)
            for i, line in enumerate(hl):
                draw.text((cx + 58, y + 134 + i * 19), line, fill=C["text3"], font=f_small)

        y += max_h + 10

    y += 18
    _draw_section_header(draw, 32, y, "经典发言", "从近期记录里挑出的代表句", C["coral"], f_head, f_small, C["text"], C["text3"])
    y += 46

    quotes = llm.get("classic_quotes", [])
    if quotes:
        for q in quotes[:6]:
            quote = q.get("quote", "")
            user = q.get("user_id", "?")
            comment = q.get("comment", "")

            ql = _wrap_text(str(quote), f_body, 676)
            qh = max(82, len(ql) * 24 + 58)

            _draw_card(draw, 32, y, 836, qh, radius=14)
            draw.rounded_rectangle((46, y + 16, 54, y + qh - 16), radius=4, fill=C["coral"])
            _draw_member_avatar(img, draw, 72, y + 20, 38, str(user), C["coral"], f_small)
            draw.text((116, y + 14), '"', fill=C["gold"], font=f_big)

            for i, line in enumerate(ql):
                draw.text((144, y + 20 + i * 24), line, fill=C["text2"], font=f_body)

            draw.text(
                (144, y + qh - 26),
                _fit_text(f"@{user}  /  {comment}", f_small, 660),
                fill=C["text3"],
                font=f_small,
            )
            y += qh + 10
    else:
        _draw_card(draw, 32, y, 836, 54, radius=14)
        draw.text((56, y + 17), "暂无足够有代表性的原句。", fill=C["text3"], font=f_body)
        y += 70

    y += 12
    _draw_card(draw, 24, y, 852, 42, radius=12, shadow=False, fill="#eef5f1")
    draw.text(
        (312, y + 13),
        "AutoLearn / LLM Group Analysis / LangBot",
        fill=C["text3"],
        font=f_small,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")