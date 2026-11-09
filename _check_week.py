# -*- coding: utf-8 -*-
"""检查 11-05 至 11-08 的事件匹配情况"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/home/sai/boss-greeting")
sys.path.insert(0, str(ROOT))
from src.roster import load_roster, match_date

records = load_roster(ROOT / "data" / "关怀台账.xlsx")
today = date.today()
for offset in range(4):
    day = today + timedelta(days=offset)
    events = match_date(records, day)
    print(f"{day} ({['周一','周二','周三','周四','周五','周六','周日'][day.weekday()]}): {len(events)} 条")
    for ev in events:
        y = f" {ev['years']}周年" if ev.get("years") else ""
        print(f"  {ev['name']} {ev['category']}{y} {ev['company']}")
print(f"\n合计: {sum(len(match_date(records, today + timedelta(days=o))) for o in range(4))} 条")
