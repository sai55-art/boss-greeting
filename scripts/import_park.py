# -*- coding: utf-8 -*-
"""园区填报模板通用导入：解析「园区祝福数据填报模板」格式的 xlsx，追加进台账（不清除已有数据）。

用法: python scripts/import_park.py <填报的xlsx路径>
园区名称取自模板 A1 单元格“园区名称（必填…）：”后的名称；也可用 --project 覆盖。
日期支持: datetime / Excel序列号 / YYYY-MM-DD / YYYY/M/D / MM-DD / MM.DD（无年份按当年匹配）。
"""
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCEL_EPOCH = datetime(1899, 12, 30)
SECTIONS = {"成立周年庆": "成立周年", "入园周年庆": "入园周年", "生日": "生日"}
DATE_COLS = ("成立时间", "入园时间", "法人生日", "生日")
NAME_COLS = ("企业法人", "企业法人/负责人")
NAME_HEADER = "企业名称"


def parse_date(val, today):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None, None
    if isinstance(val, datetime):
        d = val.date()
        return d.isoformat(), d
    if isinstance(val, (int, float)):
        d = (EXCEL_EPOCH + timedelta(days=float(val))).date()
        return d.isoformat(), d
    s = str(val).strip()
    m = re.match(r"^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$", s)
    if m:
        d = date(int(m[1]), int(m[2]), int(m[3]))
        return d.isoformat(), d
    m = re.match(r"^(\d{1,2})[-/.月](\d{1,2})日?$", s)
    if m:
        d = date(today.year, int(m[1]), int(m[2]))
        return d.isoformat(), d
    d = pd.to_datetime(s, errors="coerce")
    if not pd.isna(d):
        return d.date().isoformat(), d.date()
    return None, None


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not src or not src.exists():
        print("用法: python scripts/import_park.py <填报xlsx路径>")
        return 2
    dry = "--dry" in sys.argv
    today = datetime.now().date()

    raw = pd.read_excel(src, sheet_name=0, header=None)

    # 园区名称：优先读 B1 单元格；否则取 A1 最后一个冒号后的内容
    b1 = str(raw.iat[0, 1]).strip() if raw.shape[1] > 1 and pd.notna(raw.iat[0, 1]) else ""
    a1 = str(raw.iat[0, 0]) if pd.notna(raw.iat[0, 0]) else ""
    project = b1 or (a1.rsplit("：", 1)[-1].strip() if "：" in a1 else "")
    for a in sys.argv:
        if a.startswith("--project="):
            project = a.split("=", 1)[1].strip()
    if not project:
        print("错误：模板 A1 未填园区名称（或用 --project=园区名 指定）")
        return 2

    records, seen, skipped = [], set(), []
    current = None
    headers = {}
    for i in range(len(raw)):
        first = str(raw.iat[i, 0]).strip() if pd.notna(raw.iat[i, 0]) else ""
        for key, cat in SECTIONS.items():
            if key in first and len(first) < 30:
                current = cat
                headers = {}
        if current is None:
            continue
        row = raw.iloc[i]
        cells = [str(v).strip() if pd.notna(v) else "" for v in row]
        if any("企业名称" in c or "企业全称" in c for c in cells):  # 列头行
            for j, c in enumerate(cells):
                if any(k in c for k in DATE_COLS):
                    headers["date"] = j
                if any(k in c for k in NAME_COLS):
                    headers["person"] = j
                if c == NAME_HEADER or "企业全称" in c:
                    headers["company"] = j
                if c == "性别":
                    headers["gender"] = j
            continue
        if not first or first.startswith(("示例", "填表说明", "园区名称")):
            continue
        company = cells[headers.get("company", 0)]
        name = cells[headers["person"]] if "person" in headers else ""
        try:
            date_str, _ = parse_date(row[headers["date"]], today) if "date" in headers else (None, None)
        except Exception:  # noqa: BLE001
            date_str = None
        gender = cells[headers.get("gender", 0)]
        gender = "男" if gender.startswith("男") else ("女" if gender.startswith("女") else "")
        if not company or not name or not date_str:
            skipped.append(f"{name or company or first}(缺字段/日期)")
            continue
        key = (name, current, date_str)
        if key in seen:
            continue
        seen.add(key)
        records.append({"类别": current, "企业名称": company, "所属项目": project,
                        "姓名": name, "职务": "", "性别": gender, "节点日期": date_str})

    if not records:
        print("未解析到有效数据，未做任何修改")
        return 1
    new_df = pd.DataFrame(records, columns=["类别", "企业名称", "所属项目", "姓名", "职务", "性别", "节点日期"])
    dst = ROOT / "data" / "关怀台账.xlsx"
    if dry:
        print(f"[dry] 将追加 {len(new_df)} 条（{project}），预览：")
        print(new_df.to_string(index=False))
        if skipped:
            print("跳过（字段/日期缺失）:", "; ".join(skipped))
        return 0
    main_df = pd.read_excel(dst, sheet_name=0)
    before = len(main_df)
    combined = pd.concat([main_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["类别", "企业名称", "姓名", "节点日期"], keep="first")
    combined = combined.reindex(columns=["类别", "企业名称", "所属项目", "姓名", "职务", "性别", "节点日期"])
    combined.to_excel(dst, index=False)
    added = len(combined) - before
    print(f"台账原 {before} 条，本次新增 {added} 条（重复自动跳过 {len(new_df) - added} 条），现共 {len(combined)} 条")
    print(new_df.groupby("类别").size().to_string())
    if skipped:
        print("跳过（字段/日期缺失）:", "; ".join(skipped[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
