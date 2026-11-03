# -*- coding: utf-8 -*-
"""联科月度祝福统计导入：三段式 Sheet1 -> 规范化台账。

用法: python scripts/import_lianke.py [源xlsx路径] [所属项目名]
清除旧台账，整表替换为本次导入数据。
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = r"D:\ProgramData\Wechat\xwechat_files\wxid_unjfid23mkf022_9fcc\msg\attach\093c6493f5899e5e68aea928c0bae320\2026-11\Rec\a97f8fd0c1ced3c7\F\0\联科11月企业家祝福统计(20261103).xlsx"
SECTIONS = {"成立周年庆": "成立周年", "入园周年庆": "入园周年", "生日": "生日"}
EXCEL_EPOCH = datetime(1899, 12, 30)


def parse_date(val):
    """Excel 序列号 / datetime / '阳历11.16' / '2023-11-28' -> date 字符串；无法解析返回 None。"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, (int, float)):
        return (EXCEL_EPOCH + timedelta(days=float(val))).date().isoformat()
    s = str(val).strip()
    m = re.match(r"阳历(\d{1,2})[.月](\d{1,2})", s)
    if m:
        return f"1900-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    d = pd.to_datetime(s, errors="coerce")
    return None if pd.isna(d) else d.date().isoformat()


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_SRC)
    project = sys.argv[2] if len(sys.argv) > 2 else "联科国际信息产业园"
    raw = pd.read_excel(src, sheet_name="Sheet1", header=None)

    records, seen, skipped = [], set(), []
    current = None
    for i in range(len(raw)):
        first = str(raw.iat[i, 0]).strip() if pd.notna(raw.iat[i, 0]) else ""
        for key, cat in SECTIONS.items():
            if key in first and len(first) < 30:
                current = cat
        if current is None or first.startswith("楼栋") or first.startswith("单元"):
            continue
        row = raw.iloc[i]
        # 生日段姓名在[9]企业法人；周年段在[11]企业法人/负责人
        name = row[9] if current == "生日" else row[11]
        company = row[3]
        if pd.isna(company) or pd.isna(name):
            continue
        if current == "生日":
            date_val = row[11]          # 法人生日（序列号/文本）
        elif current == "成立周年":
            date_val = row[9]           # 成立时间
        else:
            date_val = row[9]           # 入园时间
        date = parse_date(date_val)
        if date is None:
            skipped.append(f"{name}({date_val})")
            continue
        gender = str(row[12]).strip() if pd.notna(row[12]) else ""
        gender = "男" if gender.startswith("男") else ("女" if gender.startswith("女") else "")
        key = (str(name).strip(), current, date)
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "类别": current,
            "企业名称": str(company).strip(),
            "所属项目": project,
            "姓名": str(name).strip(),
            "职务": "法人" if current != "生日" else "",
            "性别": gender,
            "节点日期": date,
        })

    df = pd.DataFrame(records, columns=["类别", "企业名称", "所属项目", "姓名", "职务", "性别", "节点日期"])
    dst = ROOT / "data" / "关怀台账.xlsx"
    df.to_excel(dst, index=False)
    print(f"导入 {len(df)} 条 -> {dst}")
    print(df.groupby("类别").size().to_string())
    if skipped:
        print("跳过（无法解析日期）:", "; ".join(skipped))


if __name__ == "__main__":
    main()
