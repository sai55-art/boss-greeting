# -*- coding: utf-8 -*-
"""按日期范围导出推送内容为 Word（核实行 + 海报 + 祝福语）。

用法: python scripts/make_range_doc.py 2026-11-16 2026-11-17

排版：统一使用微软雅黑（含中文 eastAsia 字体设置），标题/正文/标签三级字号，
避免中英文回退字体混排造成的粗细不一。
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from src.copywriting import load_templates, render, render_notice, templates_for
from src.emoji_map import to_emoji
from src.poster import make_poster
from src.roster import TYPE_FILENAME, load_roster, match_date

FONT = "微软雅黑"
EMOJI_FONT = "Segoe UI Emoji"
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
DARK = RGBColor(0x1D, 0x21, 0x29)
BODY = RGBColor(0x2E, 0x33, 0x3A)
GRAY = RGBColor(0x86, 0x90, 0x9C)
ACCENT = RGBColor(0xD4, 0x6B, 0x08)
WEEK_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _force_font(rpr, name=FONT):
    """写入显式字体，并清除主题字体属性（主题字体优先级更高，会覆盖显式设置）。"""
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def apply_style_font(style, size=None, bold=None, color=None):
    """统一设置中英文字体（中文必须写 w:eastAsia，否则会回退到宋体）。"""
    style.font.name = FONT
    _force_font(style.element.get_or_add_rPr())
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color


def run_font(run, size=None, bold=None, color=None, name=FONT):
    """对单个 run 也补齐 eastAsia，避免同一段内字体不一致。"""
    run.font.name = name
    _force_font(run._element.get_or_add_rPr(), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _split_emoji(text):
    """把文本切成 (片段, 是否emoji) 连续段。"""
    out, buf, mode = [], "", None
    for ch in text:
        is_e = bool(_EMOJI_RE.match(ch))
        if mode is None or is_e == mode:
            buf += ch
            mode = is_e
        else:
            out.append((buf, mode))
            buf, mode = ch, is_e
    if buf:
        out.append((buf, mode))
    return out


def add_rich(paragraph, text, size=10.5, bold=False, color=BODY):
    """写入文本，emoji 用 Segoe UI Emoji、正文用雅黑，避免表情显示成方块或文字代码。"""
    for seg, is_e in _split_emoji(text):
        run_font(paragraph.add_run(seg), size=size, bold=bold, color=color,
                 name=EMOJI_FONT if is_e else FONT)


def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/make_range_doc.py <起始YYYY-MM-DD> <结束YYYY-MM-DD>")
        return 2
    start = date.fromisoformat(sys.argv[1])
    end = date.fromisoformat(sys.argv[2])

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    templates = load_templates(ROOT / "templates" / "文案模板.json")
    signatures = cfg.get("project_signature", {})
    font_cfg = cfg.get("font", {})
    pw = cfg.get("poster", {})
    size = (int(pw.get("width", 1242)), int(pw.get("height", 2760)))
    records = load_roster(ROOT / cfg["roster_path"])

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.4)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.2)

    # 统一所有可能用到的样式，杜绝回退字体
    apply_style_font(doc.styles["Normal"], size=10.5, color=BODY)
    doc.styles["Normal"].paragraph_format.space_after = Pt(3)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.45
    for name, sz in (("Title", 20), ("Heading 1", 15), ("Heading 2", 13.5),
                     ("Heading 3", 12)):
        try:
            st = doc.styles[name]
            apply_style_font(st, size=sz, bold=True, color=DARK)
            st.font.italic = False
            st.paragraph_format.space_before = Pt(10)
            st.paragraph_format.space_after = Pt(6)
        except KeyError:
            pass

    # 封面标题（去掉 Title 样式自带的下边框，改用整幅宽度分隔线）
    t = doc.add_paragraph()
    t.paragraph_format.space_before = Pt(0)
    t.paragraph_format.space_after = Pt(2)
    run_font(t.add_run("推送清单"), size=19, bold=True, color=DARK)

    sub = doc.add_paragraph()
    sr = sub.add_run(f"{start:%Y年%m月%d日} — {end:%m月%d日}　|　联科国际信息产业园")
    run_font(sr, size=9, bold=False, color=GRAY)
    sub.paragraph_format.space_after = Pt(12)

    total = 0
    d = start
    while d <= end:
        events = match_date(records, d)
        if events:
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(16)
            h.paragraph_format.space_after = Pt(7)
            h.paragraph_format.keep_with_next = True
            run_font(h.add_run(f"{d.month}月{d.day}日（{WEEK_CN[d.weekday()]}）"),
                     size=13, bold=True, color=ACCENT)

        for ev in events:
            total += 1
            sig = signatures.get(ev["project"], ev["project"] or "产业中天")
            group = templates_for(templates, ev["project"])
            poster_copy = render(ev, group["海报"], sig)
            bless = render(ev, group["祝福"], sig)
            notice = render_notice(ev, group.get("核实"), d)
            years = f" · {ev['years']}周年" if ev.get("years") else ""
            ftype = TYPE_FILENAME[ev["category"]]
            poster = ROOT / cfg.get("output_dir", "output") / d.isoformat() / \
                f"{ev['project']}-{ftype}-{d:%m%d}-{ev['name']}.jpg"
            make_poster(ev, poster_copy, pw.get("backgrounds", {}).get(ev["category"]),
                        font_cfg, size, poster)

            # 标题行：序号 + 姓名（粗） + 企业（常规灰）
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run_font(p.add_run(f"{total}. "), size=11, bold=True, color=ACCENT)
            run_font(p.add_run(ev["name"]), size=11, bold=True, color=DARK)
            run_font(p.add_run(f"　{ev['company']}"), size=10, bold=False, color=BODY)
            run_font(p.add_run(f"（{ev['category']}{years}）"),
                     size=9.5, bold=False, color=GRAY)

            # 左海报 / 右文字 的无边框两栏（表格在部分渲染器会带边框，改用单栏：文字 → 海报 → 祝福语）
            def inline_para(label_text, text, after=5, keep=False):
                bp = doc.add_paragraph()
                bp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                bp.paragraph_format.space_before = Pt(0)
                bp.paragraph_format.space_after = Pt(after)
                bp.paragraph_format.line_spacing = 1.4
                bp.paragraph_format.keep_with_next = keep
                run_font(bp.add_run(label_text), size=8.5, bold=True, color=GRAY)
                add_rich(bp, to_emoji(text), size=10.5, color=BODY)
                return bp

            if notice:
                inline_para("核实行　", notice, after=6, keep=True)

            pic_p = doc.add_paragraph()
            pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pic_p.paragraph_format.space_before = Pt(4)
            pic_p.paragraph_format.space_after = Pt(6)
            pic_p.paragraph_format.keep_with_next = True
            pic_p.add_run().add_picture(str(poster), width=Cm(3.8))

            tidy = [to_emoji(line) for line in bless.splitlines() if line.strip()]
            for i, line in enumerate(tidy):
                bp = doc.add_paragraph()
                bp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                bp.paragraph_format.space_before = Pt(0)
                bp.paragraph_format.space_after = Pt(3 if i == len(tidy) - 1 else 0)
                bp.paragraph_format.line_spacing = 1.4
                if i == 0:
                    run_font(bp.add_run("祝福语　"), size=8.5, bold=True, color=GRAY)
                add_rich(bp, line, size=10.5, color=BODY)

            # 浅色分隔线（整幅宽度）
            sep = doc.add_paragraph()
            sep.paragraph_format.space_before = Pt(7)
            sep.paragraph_format.space_after = Pt(2)
            pPr = sep._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "E5E6EB")
            pbdr.append(bottom)
            pPr.append(pbdr)

        d = d + timedelta(days=1)

    end_p = doc.add_paragraph()
    end_p.paragraph_format.space_before = Pt(12)
    run_font(end_p.add_run(f"共 {total} 条　|　生成于 {date.today():%Y-%m-%d}"),
             size=9, bold=False, color=GRAY)

    out = ROOT / f"推送清单（{start:%m%d}-{end:%m%d}）.docx"
    doc.save(str(out))
    print(f"已生成 {out}（{total} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())