# -*- coding: utf-8 -*-
"""读取台账并匹配当天节点。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

CATEGORY_ORDER = ["生日", "成立周年", "入园周年"]
TYPE_FILENAME = {"生日": "生日", "成立周年": "成立周年", "入园周年": "入园周年"}


def load_roster(path: str | Path) -> list[dict]:
    """读取规范化台账，返回记录列表。日期解析失败或关键字段缺失的行跳过并告警。"""
    df = pd.read_excel(path)
    required = {"类别", "企业名称", "姓名", "性别", "节点日期"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"台账缺少字段: {missing}")
    records = []
    for i, row in df.iterrows():
        d = pd.to_datetime(row["节点日期"], errors="coerce")
        if pd.isna(d) or not str(row["姓名"]).strip():
            print(f"[warn] 台账第 {i + 2} 行字段不完整，已跳过")
            continue
        records.append({
            "category": str(row["类别"]).strip(),
            "company": str(row["企业名称"]).strip(),
            "project": str(row.get("所属项目", "") or "").strip(),
            "name": str(row["姓名"]).strip(),
            "title": str(row.get("职务", "") or "").strip(),
            "gender": str(row.get("性别", "") or "").strip(),
            "date": d.date(),
        })
    return records


def _anniversary_years(start: dt.date, today: dt.date) -> int:
    return today.year - start.year


def _today_mmdd(today: dt.date) -> tuple[int, int]:
    """2/29 生日的记录在平年落到 2/28 匹配。"""
    if (today.month, today.day) == (2, 28) and not _is_leap(today.year):
        return (2, 29)
    return (today.month, today.day)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def match_date(records: list[dict], today: dt.date) -> list[dict]:
    """匹配 MM-DD 相同的记录；周年类附带周年数，周年数<=0 跳过。"""
    target = _today_mmdd(today)
    events = []
    for r in records:
        if (r["date"].month, r["date"].day) != target:
            continue
        event = dict(r)
        if r["category"] in ("成立周年", "入园周年"):
            years = _anniversary_years(r["date"], today)
            if years <= 0:
                continue
            event["years"] = years
        events.append(event)
    # 排序：生日 -> 成立周年 -> 入园周年，再按姓名
    events.sort(key=lambda e: (CATEGORY_ORDER.index(e["category"]), e["name"]))
    return events
