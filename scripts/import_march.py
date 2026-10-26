# -*- coding: utf-8 -*-
"""把 2025年3月关怀清单 Excel 导入为规范化台账 data/关怀台账.xlsx"""
import sys
from pathlib import Path

import pandas as pd

SRC = Path(r"D:\ProgramData\Wechat\xwechat_files\wxid_unjfid23mkf022_9fcc\temp\RWTemp\2026-10\093c6493f5899e5e68aea928c0bae320\2025年3月产业中天客户重要节日关怀清单（3月）.xlsx")
DST = Path(__file__).resolve().parents[1] / "data" / "关怀台账.xlsx"

CATEGORY_MAP = {
    "企业家生日": "生日",
    "企业创立周年庆": "成立周年",
    "企业成立周年庆": "成立周年",
    "企业入园周年庆": "入园周年",
    "企业入园时间": "入园周年",
}


def main() -> None:
    raw = pd.read_excel(SRC, header=None)
    rows = []
    for i in range(len(raw)):
        cat_raw = raw.iat[i, 1]
        cat = CATEGORY_MAP.get(str(cat_raw).strip()) if pd.notna(cat_raw) else None
        if cat is None:
            continue
        name = raw.iat[i, 7] if pd.notna(raw.iat[i, 7]) else None
        company = raw.iat[i, 2] if pd.notna(raw.iat[i, 2]) else None
        date = raw.iat[i, 10] if pd.notna(raw.iat[i, 10]) else None
        if not name or not company or not date:
            continue
        care = raw.iat[i, 14] if raw.shape[1] > 14 else None
        if pd.notna(care) and str(care).strip() == "否":
            continue
        rows.append({
            "类别": cat,
            "企业名称": str(company).strip(),
            "所属项目": str(raw.iat[i, 3]).strip() if pd.notna(raw.iat[i, 3]) else "",
            "姓名": str(name).strip(),
            "职务": str(raw.iat[i, 8]).strip() if pd.notna(raw.iat[i, 8]) else "",
            "性别": str(raw.iat[i, 9]).strip() if pd.notna(raw.iat[i, 9]) else "",
            "节点日期": pd.to_datetime(date, errors="coerce"),
        })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["节点日期"])
    df["节点日期"] = df["节点日期"].dt.strftime("%Y-%m-%d")
    DST.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(DST, index=False)
    print(f"导入 {len(df)} 条 -> {DST}")
    print(df.groupby("类别").size().to_string())


if __name__ == "__main__":
    sys.exit(main())
