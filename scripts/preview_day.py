# -*- coding: utf-8 -*-
"""生成成品预览：某天命中的所有节点 -> 文案 + 海报路径"""
import datetime as dt
import io
import sys
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.copywriting import load_templates, render
from src.poster import make_poster
from src.roster import load_roster, match_date

ROOT = Path(__file__).resolve().parents[1]
day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2026, 3, 5)

cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
templates = load_templates(ROOT / "templates" / "文案模板.json")
events = match_date(load_roster(ROOT / cfg["roster_path"]), day)

lines = []
for ev in events:
    signature = cfg["project_signature"].get(ev["project"], ev["project"])
    text = render(ev, templates, signature)
    ftype = {"生日": "生日", "成立周年": "成立周年", "入园周年": "入园周年"}[ev["category"]]
    poster = ROOT / "output" / day.isoformat() / f"{ev['project']}-{ftype}-{day:%m%d}-{ev['name']}.jpg"
    make_poster(ev, text, cfg["poster"]["backgrounds"].get(ev["category"]),
                cfg["font"], (cfg["poster"]["width"], cfg["poster"]["height"]), poster)
    lines.append(f"### {ev['company']}｜{ev['name']}｜{ev['category']}"
                 f"（{ev.get('years', '')}{'周年' if ev.get('years') else ''}）")
    lines.append("")
    lines.append("【企微消息文案】")
    lines.append(text)
    lines.append("")
    lines.append(f"【海报】output/{day.isoformat()}/{poster.name}")
    lines.append("")
    lines.append("=" * 46)
    lines.append("")

(ROOT / "_preview.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"已生成 {len(events)} 条预览 -> _preview.txt")
