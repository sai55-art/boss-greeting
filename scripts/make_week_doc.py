# -*- coding: utf-8 -*-
"""本周（11-05 ~ 11-08）推送数据打包为 Word 文档。"""
import io
import sys
from datetime import date, timedelta
from pathlib import Path

import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "本周推送清单（11.05-11.08）.docx"

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from src.copywriting import load_templates, render, render_notice, templates_for
from src.roster import load_roster, match_date

cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
templates = load_templates(ROOT / "templates" / "文案模板.json")
signatures = cfg.get("project_signature", {})
pw = cfg.get("poster", {})
size = (int(pw.get("width", 1242)), int(pw.get("height", 2760)))

today = date.today()
records = load_roster(ROOT / cfg["roster_path"])

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Microsoft YaHei"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

doc.add_heading("本周推送清单（11.05 — 11.08）", level=0)

ACCENT = RGBColor(0xD4, 0x6B, 0x08)
GRAY = RGBColor(0x86, 0x90, 0x9C)
total = 0
for offset in range(4):
    day = today + timedelta(days=offset)
    events = match_date(records, day)
    if not events:
        continue
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()]
    doc.add_heading(f"{day.month}月{day.day}日（{weekday_cn}）", level=2)

    for ev in events:
        sig = signatures.get(ev["project"], ev["project"] or "产业中天")
        group = templates_for(templates, ev["project"])
        poster_copy = render(ev, group["海报"], sig)
        bless = render(ev, group["祝福"], sig)
        notice = render_notice(ev, group.get("核实"), day)
        years = f" {ev['years']} 周年" if ev.get("years") else ""
        cat = ev["category"]

        p = doc.add_paragraph()
        r = p.add_run(f"{ev['name']} · {ev['company']}")
        r.bold = True
        r.font.size = Pt(12)
        r2 = p.add_run(f"  {cat}{years}")
        r2.font.color.rgb = ACCENT
        r2.font.size = Pt(11)

        if notice:
            p2 = doc.add_paragraph()
            r3 = p2.add_run("核实行：")
            r3.bold = True
            r3.font.color.rgb = GRAY
            p2.add_run(notice)

        p3 = doc.add_paragraph()
        r4 = p3.add_run("祝福文案：")
        r4.bold = True
        r4.font.color.rgb = GRAY
        p3.add_run(bless)

        # 海报
        ftype = cat
        out_dir = ROOT / cfg.get("output_dir", "output") / day.isoformat()
        poster_path = out_dir / f"{ev['project']}-{ftype}-{day:%m%d}-{ev['name']}.jpg"
        if poster_path.exists():
            doc.add_picture(str(poster_path), width=Cm(4))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()  # spacing

    total += len(events)

doc.add_paragraph()
p_end = doc.add_paragraph()
r_end = p_end.add_run(f"共 {total} 条 · 生成时间 {date.today().isoformat()}")
r_end.font.color.rgb = GRAY
r_end.font.size = Pt(10)

doc.save(str(OUTPUT))
print(f"已生成: {OUTPUT}")
