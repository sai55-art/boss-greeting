# -*- coding: utf-8 -*-
"""生成园区祝福数据填报模板（给各园区填写用）。"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

OUT = Path(__file__).resolve().parents[1] / "园区祝福数据填报模板.xlsx"

wb = Workbook()
ws = wb.active
ws.title = "Sheet1"

bold = Font(bold=True)
section_fill = PatternFill("solid", fgColor="FFF2E2")
title_font = Font(bold=True, size=12)

ws["A1"] = "园区名称（必填，例如：滨海智造港）："
ws["A1"].font = title_font
ws["B1"].font = Font(bold=True, color="D46B08")
ws["A2"] = "填表说明：日期一律填公历，格式 YYYY-MM-DD（如 2019-11-18）；只知月日不知年份的填 MM-DD（如 11-16）；不要修改各小节标题行与列头；同一人多条信息写一行即可。"
ws["A2"].font = Font(color="86909C", size=10)

row = 4


def section(title, headers, example):
    global row
    ws.cell(row=row, column=1, value=title).font = title_font
    ws.cell(row=row, column=1).fill = section_fill
    row += 1
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = bold
    row += 1
    for col, v in enumerate(example, start=1):
        c = ws.cell(row=row, column=col, value=v)
        c.font = Font(italic=True, color="86909C")
    row += 2


section("企业家成立周年庆", ["企业名称", "成立时间", "企业法人", "性别"],
        ["示例科技有限公司（填写时删除本行）", "2015-06-08", "张三", "男"])
section("企业家入园周年庆", ["企业名称", "入园时间", "企业法人", "性别"],
        ["示例贸易有限公司（填写时删除本行）", "2020-03-15", "李四", "女"])
section("企业家生日", ["企业名称", "企业法人", "法人生日", "性别"],
        ["示例信息技术有限公司（填写时删除本行）", "王五", "1988-11-16", "男"])

wb.save(OUT)
print("模板已生成:", OUT)
