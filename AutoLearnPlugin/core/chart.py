from __future__ import annotations

import base64
import io
import math
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
    base = 500
    base += len(_wrap_text(overview.get("quality_review", ""), _font(14), 740)) * 22
    # Two-column layout: half the rows
    member_rows = math.ceil(len(members) / 2)
    base += member_rows * 148
    base += len(quotes) * 80
    return min(max(base, 1500), 4200)


def _draw_card(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    radius: int = 12,
    shadow: bool = True,
    fill: str = "#ffffff",
) -> None:
    if shadow:
        draw.rounded_rectangle(
            (x + 2, y + 2, x + w + 2, y + h + 2),
            radius=radius, fill="#e2e4e8",
        )
    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=radius, fill=fill,
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


def generate_group_chart(analysis: dict[str, Any]) -> str:
    """Render a modern, beautifully designed group analysis report."""
    raw = analysis.get("raw", {})
    llm = analysis.get("llm", {})
    overview = llm.get("overview", {})

    width = 900
    height = _estimate_height(analysis)
    img = Image.new("RGB", (width, height), "#f0f2f5")
    draw = ImageDraw.Draw(img)

    # Fonts
    f_title = _font(22)
    f_sub = _font(13)
    f_head = _font(15)
    f_body = _font(13)
    f_small = _font(12)
    f_tiny = _font(10)
    f_micro = _font(9)

    # ── Color System ──
    C = {
        "text": "#1a1a2e",
        "text2": "#4a4a6a",
        "text3": "#8a8aa0",
        "text4": "#b0b0c0",
        "card": "#ffffff",
        "bg": "#f0f2f5",
        "shadow": "#e2e4e8",
        "blue": "#4361ee",
        "blue_bg": "#eef0ff",
        "green": "#2ec4b6",
        "green_bg": "#e8faf7",
        "amber": "#f4a261",
        "amber_bg": "#fef6ed",
        "rose": "#e63946",
        "rose_bg": "#fde8ea",
        "purple": "#7b2cbf",
        "purple_bg": "#f3edff",
        "orange": "#e76f51",
        "orange_bg": "#fef0ea",
        "cyan": "#00b4d8",
        "cyan_bg": "#e6faff",
        "pink": "#d63384",
        "pink_bg": "#fce8f3",
        "teal": "#20b2aa",
        "indigo": "#5c6bc0",
        "gold": "#d4a017",
        "gold_bg": "#fef7e0",
        "border": "#e8e8ee",
    }

    y = 20

    # ═══════════════════════════════════════════════
    #  HEADER
    # ═══════════════════════════════════════════════
    _draw_card(draw, 24, y, 852, 72)
    # Gradient top bar
    for bx in range(24, 876):
        ratio = (bx - 24) / 852
        r = int(67 + ratio * 54)
        g = int(97 + ratio * 20)
        b = int(238 - ratio * 30)
        draw.line([(bx, y), (bx, y + 4)], fill=(r, g, b))

    draw.text((40, y + 16), "Group Chat Analysis Report", fill=C["text"], font=f_title)
    gid = raw.get("group_id", "?")
    gen = analysis.get("generated_at", "")
    vibe = overview.get("group_vibe", "analyzing")
    draw.text((40, y + 46), f"Group {gid}  |  {gen}  |  Vibe: {vibe}", fill=C["text3"], font=f_sub)
    y += 88

    # ═══════════════════════════════════════════════
    #  STATISTICS ROW
    # ═══════════════════════════════════════════════
    stats = [
        ("Messages",  str(raw.get("total_messages", 0)),  C["blue"],   C["blue_bg"]),
        ("Users",     str(raw.get("participant_count", 0)), C["green"],  C["green_bg"]),
        ("Characters",str(raw.get("total_chars", 0)),      C["amber"],  C["amber_bg"]),
        ("Images",    str(raw.get("total_images", 0)),     C["rose"],   C["rose_bg"]),
        ("Emojis",    str(raw.get("total_emojis", 0)),     C["orange"], C["orange_bg"]),
        ("Slang",     str(len(raw.get("top_slang", []))), C["purple"], C["purple_bg"]),
    ]
    cw, cg = 132, 8
    sx = 24
    for i, (label, val, color, bg) in enumerate(stats):
        cx = sx + i * (cw + cg)
        _draw_card(draw, cx, y, cw, 74)
        draw.rounded_rectangle((cx + 6, y + 6, cx + cw - 6, y + 8), radius=2, fill=color)
        draw.text((cx + 12, y + 18), label, fill=C["text3"], font=f_tiny)
        draw.text((cx + 12, y + 34), val, fill=color, font=f_head)
        draw.line([(cx + 12, y + 64), (cx + cw - 12, y + 64)], fill=C["border"], width=1)
    y += 92

    # ═══════════════════════════════════════════════
    #  ACTIVE PERIODS
    # ═══════════════════════════════════════════════
    _draw_card(draw, 24, y, 852, 56)
    periods = overview.get("active_periods") or [
        f"{h['hour']}:00 ({h['count']}msgs)" for h in raw.get("active_hours", [])[:4]
    ]
    period_text = "  |  ".join(periods) if periods else "Insufficient data"
    _draw_tag(draw, 36, y + 13, "Active Hours", C["cyan"], C["cyan_bg"])
    draw.text((160, y + 17), period_text, fill=C["text2"], font=f_body)
    # Timeline dots
    for di in range(8):
        dc = [C["cyan"], C["blue"], C["purple"], C["green"], C["amber"], C["rose"], C["orange"], C["pink"]][di]
        draw.ellipse((810 + di * 10, y + 15, 810 + di * 10 + 5, y + 20), fill=dc)
    y += 74

    # ═══════════════════════════════════════════════
    #  QUALITY REVIEW
    # ═══════════════════════════════════════════════
    review = overview.get("quality_review", "No review yet")
    rlines = _wrap_text(review, f_body, 740)
    rh = max(44, len(rlines) * 22 + 52)
    _draw_card(draw, 24, y, 852, rh)
    _draw_tag(draw, 24, y, "Quality Review", C["rose"], C["rose_bg"])
    for i, line in enumerate(rlines):
        draw.text((40, y + 40 + i * 22), line, fill=C["text2"], font=f_body)
    y += rh + 20

    # ═══════════════════════════════════════════════
    #  MEMBER ANALYSIS (TWO-COLUMN LAYOUT)
    # ═══════════════════════════════════════════════
    _draw_card(draw, 24, y, 852, 40)
    _draw_tag(draw, 24, y, "Member Analysis", C["blue"], C["blue_bg"])
    draw.text((170, y + 7), f"Total: {len(raw.get('members', []))} participants", fill=C["text3"], font=f_small)
    y += 56

    llm_members = {m.get("user_id"): m for m in llm.get("members", [])}
    raw_members = raw.get("members", [])[:12]
    max_msg = max((m.get("message_count", 1) for m in raw_members), default=1)

    apal = [C["blue"], C["green"], C["rose"], C["amber"], C["purple"],
            C["cyan"], C["orange"], C["pink"], C["teal"], C["indigo"]]

    # Two-column layout
    col_w = 410
    col_gap = 16
    col_start_x = 32

    for pair_idx in range(0, len(raw_members), 2):
        pair = raw_members[pair_idx:pair_idx + 2]
        max_h = 0

        # First pass: calculate heights
        member_data = []
        for member in pair:
            uid = str(member.get("user_id", "?"))
            llm_m = llm_members.get(uid, {})
            mc = member.get("message_count", 0)
            cc = member.get("char_count", 0)
            ic = member.get("image_count", 0)
            ec = member.get("emoji_count", 0)
            pers = llm_m.get("personality", "Analyzing...")
            hab = llm_m.get("character_habits", "")
            pl = _wrap_text(f"Personality: {pers}", f_small, 320)[:2]
            hl = _wrap_text(f"Habits: {hab}", f_small, 320)[:2]
            h = 132 + max(0, len(pl) - 2) * 18 + max(0, len(hl) - 2) * 18
            max_h = max(max_h, h)
            member_data.append((uid, llm_m, mc, cc, ic, ec, pl, hl))

        # Second pass: render
        for col_idx, (uid, llm_m, mc, cc, ic, ec, pl, hl) in enumerate(member_data):
            cx = col_start_x + col_idx * (col_w + col_gap)
            ac = apal[(pair_idx + col_idx) % len(apal)]

            _draw_card(draw, cx, y, col_w, max_h)

            # Avatar
            draw.ellipse((cx + 14, y + 10, cx + 14 + 38, y + 48), fill=ac)
            draw.text((cx + 22, y + 19), uid[:2], fill="#ffffff", font=f_head)

            # Name
            draw.text((cx + 64, y + 12), uid, fill=C["text"], font=f_head)

            # Badges
            bx = cx + 200
            for bl, bc, bbg in [
                (f"Msg {mc}", C["blue"], C["blue_bg"]),
                (f"Char {cc}", C["amber"], C["amber_bg"]),
                (f"Img {ic}", C["rose"], C["rose_bg"]),
                (f"Emoji {ec}", C["orange"], C["orange_bg"]),
            ]:
                _draw_badge(draw, bx, y + 12, bl, bc, bbg)
                bx += 56

            # Activity bar
            draw.text((cx + 64, y + 36), "Activity", fill=C["text4"], font=f_micro)
            draw.rounded_rectangle((cx + 64, y + 48, cx + 64 + 180, y + 55), radius=4, fill=C["border"])
            if max_msg > 0:
                fw = max(6, int((mc / max_msg) * 180))
                draw.rounded_rectangle((cx + 64, y + 48, cx + 64 + fw, y + 55), radius=4, fill=ac)

            # Personality
            for i, line in enumerate(pl):
                draw.text((cx + 14, y + 62 + i * 18), line, fill=C["text2"], font=f_small)

            # Habits
            for i, line in enumerate(hl):
                draw.text((cx + 14, y + 100 + i * 18), line, fill=C["text3"], font=f_small)

        y += max_h + 10

    y += 6

    # ═══════════════════════════════════════════════
    #  CLASSIC QUOTES
    # ═══════════════════════════════════════════════
    _draw_card(draw, 24, y, 852, 40)
    _draw_tag(draw, 24, y, "Classic Quotes", C["gold"], C["gold_bg"])
    y += 56

    quotes = llm.get("classic_quotes", [])
    if quotes:
        for q in quotes[:6]:
            quote = q.get("quote", "")
            user = q.get("user_id", "?")
            comment = q.get("comment", "")

            ql = _wrap_text(quote, f_body, 700)
            qh = max(46, len(ql) * 22 + 56)

            _draw_card(draw, 32, y, 836, qh)

            # Left gold bar
            draw.rounded_rectangle((36, y + 6, 40, y + qh - 6), radius=3, fill=C["gold"])

            # Quote mark
            draw.text((56, y + 8), '"', fill=C["gold"], font=f_head)

            for i, line in enumerate(ql):
                draw.text((74, y + 12 + i * 22), line, fill=C["text2"], font=f_body)

            draw.text(
                (74, y + qh - 22),
                f"-- {user}  |  {comment[:50]}",
                fill=C["text4"],
                font=f_small,
            )
            y += qh + 10
    else:
        _draw_card(draw, 32, y, 836, 40)
        draw.text((56, y + 12), "Generating classic quotes...", fill=C["text3"], font=f_body)
        y += 56

    # ═══════════════════════════════════════════════
    #  FOOTER
    # ═══════════════════════════════════════════════
    y += 10
    _draw_card(draw, 24, y, 852, 36, shadow=False)
    draw.text(
        (310, y + 10),
        "AutoLearn  |  LLM Group Analysis  |  Powered by LangBot",
        fill=C["text4"],
        font=f_small,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")