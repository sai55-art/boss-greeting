# -*- coding: utf-8 -*-
"""海报合成：文字叠加到背景图；背景缺失时自动生成橙色渐变占位图。

支持中英混排 + 彩色 emoji（Segoe UI Emoji / 需在 config font.emoji 配置路径）。
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BODY_LINE_GAP = 76
BODY_FONT_SIZE = 44
NAME_FONT_SIZE = 62
SIGN_FONT_SIZE = 46

EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
_FONT_CACHE = {}


def _font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _FONT_CACHE:
        candidates = [path, "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
        for cand in candidates:
            if cand and Path(cand).exists():
                _FONT_CACHE[key] = ImageFont.truetype(cand, size)
                break
        else:
            raise RuntimeError("未找到可用中文字体，请在 config font 段配置")
    return _FONT_CACHE[key]


def _emoji_font(font_cfg: dict, size: int) -> ImageFont.FreeTypeFont | None:
    key = ("emoji", size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = [
        font_cfg.get("emoji"),
        "templates/fonts/seguiemj.ttf",
        "C:/Windows/Fonts/seguiemj.ttf",
    ]
    for cand in candidates:
        if cand and Path(cand).exists():
            try:
                _FONT_CACHE[key] = ImageFont.truetype(cand, size)
                return _FONT_CACHE[key]
            except Exception:  # noqa: BLE001
                return None
    return None


def _is_emoji(ch: str) -> bool:
    return bool(EMOJI_RE.match(ch))


def _runs(text: str) -> list[tuple[str, bool]]:
    """把文本拆成 (片段, 是否emoji) 的连续段。"""
    out: list[list] = []
    for ch in text:
        tag = _is_emoji(ch)
        if out and out[-1][1] == tag:
            out[-1][0] += ch
        else:
            out.append([ch, tag])
    return [(t, e) for t, e in out]


def _placeholder_background(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height))
    top = (255, 236, 179)
    mid = (250, 140, 60)
    bottom = (235, 80, 30)
    for y in range(height):
        t = y / height
        if t < 0.5:
            k = t / 0.5
            color = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) / 0.5
            color = tuple(int(mid[i] + (bottom[i] - mid[i]) * k) for i in range(3))
        ImageDraw.Draw(img).line([(0, y), (width, y)], fill=color)
    return img


def render_poster(name_line: str, body_lines: list[str], signature: str,
                  background_path: str | None, font_cfg: dict,
                  size: tuple[int, int]) -> Image.Image:
    width, height = size
    has_bg = bool(background_path and Path(background_path).exists())
    if has_bg:
        img = Image.open(background_path).convert("RGB")
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
    else:
        img = _placeholder_background(width, height)

    draw = ImageDraw.Draw(img)
    name_font = _font(font_cfg.get("bold"), NAME_FONT_SIZE)
    body_font = _font(font_cfg.get("regular"), BODY_FONT_SIZE)
    sign_font = _font(font_cfg.get("regular"), SIGN_FONT_SIZE)
    emoji_font = _emoji_font(font_cfg, BODY_FONT_SIZE)

    def run_width(text: str, font: ImageFont.FreeTypeFont) -> float:
        return sum(draw.textlength(t, font=_emoji_font(font_cfg, BODY_FONT_SIZE)
                                   if e else font)
                   for t, e in _runs(text))

    def wrap(text: str, font: ImageFont.FreeTypeFont) -> list[str]:
        """按像素宽度贪心换行（emoji 按其字宽计量）。"""
        max_w = width * 0.84
        out, cur = [], ""
        for ch in text:
            probe = cur + ch
            total = sum(draw.textlength(t, font=_emoji_font(font_cfg, BODY_FONT_SIZE)
                                        if e else font)
                        for t, e in _runs(probe))
            if total > max_w and cur:
                out.append(cur)
                cur = ch
            else:
                cur = probe
        if cur:
            out.append(cur)
        return out or [""]

    def draw_mixed(text: str, y: int, font: ImageFont.FreeTypeFont,
                   fill=(255, 255, 255)) -> None:
        total = run_width(text, font)
        x = (width - total) / 2
        for t, e in _runs(text):
            f = _emoji_font(font_cfg, BODY_FONT_SIZE) if e else font
            if e:
                try:
                    draw.text((x, y), t, font=f, embedded_color=True)
                except Exception:  # noqa: BLE001
                    draw.text((x, y), t, font=f, fill=fill)
            else:
                draw.text((x, y), t, font=f, fill=fill)
            x += draw.textlength(t, font=f)

    y = int(height * 0.53)
    for seg in wrap(name_line, name_font):
        draw_mixed(seg, y, name_font)
        y += int(NAME_FONT_SIZE * 1.7)
    for line in body_lines:
        for seg in wrap(line, body_font):
            draw_mixed(seg, y, body_font)
            y += BODY_LINE_GAP

    if has_bg:
        # 底图自带黄色分隔线（约 0.876H），落款画在分隔线下方
        sign_y = int(height * 0.905)
    else:
        y += int(BODY_FONT_SIZE * 0.6)
        draw.rectangle([(width / 2 - 32, y), (width / 2 + 32, y + 8)], fill=(250, 204, 60))
        sign_y = y + int(SIGN_FONT_SIZE * 2.2)
    if signature:
        draw_mixed(signature, sign_y, sign_font)
    return img


def make_poster(event: dict, copy_text: str, background_path: str | None,
                font_cfg: dict, size: tuple[int, int], out_path: Path) -> Path:
    """按文案首行为称谓行、末段为落款，合成海报并保存。"""
    lines = [ln for ln in copy_text.splitlines()]
    name_line = lines[0].strip()
    if lines and lines[-1].endswith("敬上"):
        signature = lines[-1].strip()
        body = [ln.strip() for ln in lines[1:-1] if ln.strip()]
    else:
        signature = ""
        body = [ln.strip() for ln in lines[1:] if ln.strip()]
    img = render_poster(name_line, body, signature, background_path,
                        font_cfg, size)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    return out_path
