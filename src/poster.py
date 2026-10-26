# -*- coding: utf-8 -*-
"""海报合成：文字叠加到背景图；背景缺失时自动生成橙色渐变占位图。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BODY_LINE_GAP = 76
BODY_FONT_SIZE = 44
NAME_FONT_SIZE = 62
SIGN_FONT_SIZE = 46


def _font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    candidates = [path, "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
    for cand in candidates:
        if cand and Path(cand).exists():
            return ImageFont.truetype(cand, size)
    raise RuntimeError("未找到可用中文字体，请在 config.yaml font 段配置")


def _placeholder_background(width: int, height: int) -> Image.Image:
    """生成与样例风格接近的橙色渐变占位背景（正式背景图到位后替换）。"""
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


def render_poster(
    name_line: str,
    body_lines: list[str],
    signature: str,
    background_path: str | None,
    font_cfg: dict,
    size: tuple[int, int],
) -> Image.Image:
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

    def center_y(text: str, y: int, font: ImageFont.FreeTypeFont) -> None:
        w = draw.textlength(text, font=font)
        draw.text(((width - w) / 2, y), text, font=font, fill=(255, 255, 255))

    y = int(height * 0.53)
    center_y(name_line, y, name_font)
    y += int(NAME_FONT_SIZE * 1.9)
    for line in body_lines:
        center_y(line, y, body_font)
        y += BODY_LINE_GAP

    if has_bg:
        # 底图自带黄色分隔线（约 0.876H），落款画在分隔线下方
        sign_y = int(height * 0.905)
    else:
        y += int(BODY_FONT_SIZE * 0.6)
        draw.rectangle([(width / 2 - 32, y), (width / 2 + 32, y + 8)], fill=(250, 204, 60))
        sign_y = y + int(SIGN_FONT_SIZE * 2.2)
    center_y(signature, sign_y, sign_font)
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
    img = render_poster(name_line, body, signature, background_path, font_cfg, size)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    return out_path
