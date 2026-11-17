# -*- coding: utf-8 -*-
"""把指定日期范围内「已经推送过」的节点写入防重日志（切换推送模式时避免重复推送）。

用法（在服务器上执行）：
  .venv/bin/python scripts/seed_sent.py 2026-11-18 2026-11-22 --dry
  .venv/bin/python scripts/seed_sent.py 2026-11-18 2026-11-22
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.roster import load_roster, match_date


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if len(args) < 2:
        print("用法: python scripts/seed_sent.py <起始YYYY-MM-DD> <结束YYYY-MM-DD> [--dry]")
        return 2
    start = date.fromisoformat(args[0])
    end = date.fromisoformat(args[1])

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    records = load_roster(ROOT / cfg["roster_path"])
    log = ROOT / cfg.get("log_dir", "logs") / "sent.jsonl"

    existing = set()
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(line).get("key"))
            except json.JSONDecodeError:
                continue

    seeded = []
    d = start
    while d <= end:
        for ev in match_date(records, d):
            key = f"{d.isoformat()}|{ev['name']}|{ev['category']}|{ev['company']}"
            if key in existing:
                continue
            seeded.append({
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "date": d.isoformat(),
                "key": key,
                "name": ev["name"],
                "category": ev["category"],
                "company": ev["company"],
                "status": "ok",
                "error": "",
                "poster": "",
                "seeded": True,
                "note": "切换推送模式前补记：该节点已在上一轮批量推送中发送",
            })
        d += timedelta(days=1)

    if not seeded:
        print("无需补记（这些节点均已存在防重记录）")
        return 0

    print(f"[{'dry' if dry else 'write'}] 将补记 {len(seeded)} 条：")
    for s in seeded:
        print("  ", s["date"], s["name"], s["category"])

    if not dry:
        with open(log, "a", encoding="utf-8") as fp:
            for s in seeded:
                fp.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"已写入 {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())