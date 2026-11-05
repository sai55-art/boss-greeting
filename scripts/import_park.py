# -*- coding: utf-8 -*-
"""园区填报模板通用导入（4-Sheet 版）：追加进台账，不清除已有数据。

用法: python scripts/import_park.py <填报的xlsx路径> [--dry] [--project=园区名]
园区名称取自「填写说明」页 D2 单元格。
日期支持: datetime / Excel序列号 / YYYY-MM-DD / YYYY/M/D / MM-DD / MM.DD（无年份按当年匹配）。
"""
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCEL_EPOCH = datetime(1899, 12, 30)
SHEETS = {  # sheet名 -> (类别, 日期列头关键字)
    "成立周年庆": ("成立周年", "成立时间"),
    "入园周年庆": ("入园周年", "入园时间"),
    "生日": ("生日", "法人生日"),
}
CATEGORIES = ("生日", "成立周年", "入园周年")


def parse_date(val, today):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, (int, float)):
        f = float(val)
        if 1 <= f < 32:
            # Excel 会把 "11.16" 这类输入转成数字 11.16 —— 按「月.日」解读
            month = int(f)
            day = int(round((f - month) * 100))
            if 1 <= day <= 31:
                return date(today.year, month, day).isoformat()
        return (EXCEL_EPOCH + timedelta(days=f)).date().isoformat()
    s = str(val).strip()
    m = re.match(r"^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    m = re.match(r"^(\d{1,2})[-/.月](\d{1,2})日?$", s)
    if m:
        return date(today.year, int(m[1]), int(m[2])).isoformat()
    d = pd.to_datetime(s, errors="coerce")
    return None if pd.isna(d) else d.date().isoformat()


def main():
    args = sys.argv[1:]
    src = Path(args[0]) if args else None
    dry = "--dry" in args
    project = next((a.split("=", 1)[1] for a in args if a.startswith("--project=")), "")
    if not src or not src.exists():
        print("用法: python scripts/import_park.py <填报xlsx路径> [--dry] [--project=园区名]")
        return 2
    today = datetime.now().date()

    # 园区名称：填写说明页 B 列中「园区名称」标签的同行 D 列（或同行最后一个非空单元格）
    try:
        info = pd.read_excel(src, sheet_name="填写说明", header=None)
        project = ""
        for i in range(len(info)):
            v = str(info.iat[i, 1]) if pd.notna(info.iat[i, 1]) else ""
            if "园区名称" in v:
                for j in range(2, min(info.shape[1], 6)):
                    c = info.iat[i, j]
                    if pd.notna(c) and str(c).strip():
                        project = str(c).strip()
                        break
                break
    except Exception:  # noqa: BLE001
        pass
    if not project:
        project = project or next(
            (a.split("=", 1)[1] for a in args if a.startswith("--project=")), "")
    if not project:
        print("错误：「填写说明」页未填园区名称（D2），或用 --project=园区名 指定")
        return 2

    records, seen, skipped = [], set(), []
    for sheet_name, (category, date_key) in SHEETS.items():
        try:
            df = pd.read_excel(src, sheet_name=sheet_name, header=0)
        except Exception:  # noqa: BLE001
            print(f"[warn] 缺少工作表 {sheet_name}，跳过")
            continue
        df.columns = [str(c).strip() for c in df.columns]
        name_col = next((c for c in df.columns if "企业名称" in c or "企业全称" in c), None)
        date_col = next((c for c in df.columns if date_key in c), None)
        person_col = next((c for c in df.columns if "企业法人" in c), None)
        gender_col = next((c for c in df.columns if c == "性别"), None)
        if not name_col or not date_col or not person_col:
            print(f"[warn] {sheet_name} 缺少必需列，跳过")
            continue
        for _, row in df.iterrows():
            company = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            name = str(row[person_col]).strip() if pd.notna(row[person_col]) else ""
            if not company or not name or company.startswith("示例"):
                continue
            date_str = parse_date(row[date_col], today)
            if not date_str:
                skipped.append(f"{name}({company})")
                continue
            gender = str(row[gender_col]).strip() if gender_col and pd.notna(row[gender_col]) else ""
            gender = "男" if gender.startswith("男") else ("女" if gender.startswith("女") else "")
            key = (name, category, date_str)
            if key in seen:
                continue
            seen.add(key)
            records.append({"类别": category, "企业名称": company, "所属项目": project,
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
            print("跳过:", "; ".join(skipped))
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
    import sys  # noqa: E402

    sys.exit(main())
