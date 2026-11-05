# -*- coding: utf-8 -*-
"""生成园区祝福数据填报模板：4 个 Sheet（填写说明 + 三个数据表各司其职）。"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

OUT = Path(__file__).resolve().parents[1] / "园区祝福数据填报模板.xlsx"

wb = Workbook()

# ---- Sheet 1: 填写说明 ----
ws = wb.active
ws.title = "填写说明"
ws["B2"] = "园区名称（必填，例如：滨海智造港）："
ws["B2"].font = Font(bold=True, size=12)
ws["D2"].font = Font(bold=True, color="D46B08")
ws["B4"] = "填表说明"
ws["B4"].font = Font(bold=True, size=12)
notes = [
    "1. 先在本页 D2 填园区名称，再到右侧三个数据表填写企业家信息；",
    "2. 日期一律填公历，格式 YYYY-MM-DD（如 2019-11-18）；只知月日不知年份的填 MM-DD（如 11-16）；",
    "3. 灰色斜体示例行填写时可删除；不要修改各表的标题行与列头；",
    "4. 同一企业只填一行；信息有变动直接改单元格。",
]
for i, t in enumerate(notes):
    ws.cell(row=5 + i, column=2, value=t).font = Font(color="86909C", size=10)

# ---- 三个数据表 ----
bold = Font(bold=True)
example_font = Font(italic=True, color="86909C")


def add_sheet(name, date_header, example):
    ws = wb.create_sheet(name)
    headers = ["企业名称", date_header, "企业法人", "性别"]
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = bold
        c.fill = PatternFill("solid", fgColor="FFF2E2")
    for col, v in enumerate(example, start=1):
        c = ws.cell(row=2, column=col, value=v)
        c.font = example_font
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 8


add_sheet("成立周年庆", "成立时间",
          ["示例科技有限公司（填写时删除本行）", "2015-06-08", "张三", "男"])
add_sheet("入园周年庆", "入园时间",
          ["示例贸易有限公司（填写时删除本行）", "2020-03-15", "李四", "女"])
add_sheet("生日", "法人生日",
          ["示例信息技术有限公司（填写时删除本行）", "王五", "1988-11-16", "男"])

wb.save(OUT)
print("模板已生成:", OUT)
