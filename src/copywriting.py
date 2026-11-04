# -*- coding: utf-8 -*-
"""文案渲染。模板文件 v2 结构：{项目名: {类别: 模板, 核实: {类别: 模板}}, default: {...}}"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

_TITLE_EN = {"男": "Mr", "女": "Ms"}
_CATEGORIES = ("生日", "成立周年", "入园周年", "英文")
_WEEK_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _is_foreign_name(name: str) -> bool:
    return bool(re.search(r"[A-Za-z]", name))


def load_templates(path: str | Path) -> dict:
    """读取 v3 模板文件：{项目: {海报:{类别:模板}, 祝福:{...}, 核实:{...}}, default: {...}}"""
    with open(path, encoding="utf-8") as fp:
        data = json.load(fp)
    if "default" not in data:
        raise ValueError("文案模板缺少 default 分组")
    for group_name, group in data.items():
        for key in ("海报", "祝福"):
            if key not in group:
                raise ValueError(f"文案模板 {group_name} 缺少 {key} 子组")
            for cat in _CATEGORIES:
                if cat not in group[key]:
                    raise ValueError(f"文案模板 {group_name}.{key} 缺少 {cat}")
        group.setdefault("核实", {})
    return data


def templates_for(data: dict, project: str) -> dict:
    """按项目取模板组：精确匹配项目名，否则 default。"""
    return data.get(project) or data["default"]


def render(event: dict, templates: dict[str, str], signature: str) -> str:
    """按事件渲染祝福文案；外文姓名走英文模板。"""
    salutation = "女士" if event["gender"] == "女" else "先生"
    if _is_foreign_name(event["name"]):
        template = templates["英文"]
        mapping = {
            "姓名": event["name"],
            "称谓_en": _TITLE_EN.get(event["gender"], "Mr"),
            "项目落款": signature,
            "周年数": str(event.get("years", "")),
        }
    else:
        template = templates[event["category"]]
        mapping = {
            "姓名": event["name"],
            "称谓": salutation,
            "项目落款": signature,
            "周年数": str(event.get("years", "")),
        }
    text = template
    for key, value in mapping.items():
        text = text.replace("{" + key + "}", value)
    return text.strip()


def render_notice(event: dict, notice_tpl: dict[str, str] | None, today: date) -> str:
    """渲染管家核实信息行；无模板或类别缺失返回空串。"""
    if not notice_tpl or event["category"] not in notice_tpl:
        return ""
    tpl = notice_tpl[event["category"]]
    birth = event.get("date")
    birth_str = f"{birth.year}年{birth.month}月{birth.day}日" if birth else ""
    iso_str = birth.isoformat() if birth else ""
    mapping = {
        "企业名称": event.get("company", ""),
        "姓名": event.get("name", ""),
        "月": today.month,
        "日": today.day,
        "周": _WEEK_CN[today.weekday()],
        "周年数": str(event.get("years", "")),
        "生日日期": birth_str,
        "成立日期": iso_str,
    }
    text = tpl
    for key, value in mapping.items():
        text = text.replace("{" + key + "}", str(value))
    return text.strip()
