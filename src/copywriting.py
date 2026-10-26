# -*- coding: utf-8 -*-
"""文案渲染。"""
from __future__ import annotations

import json
import re
from pathlib import Path

_TITLE_EN = {"男": "Mr", "女": "Ms"}


def _is_foreign_name(name: str) -> bool:
    return bool(re.search(r"[A-Za-z]", name))


def load_templates(path: str | Path) -> dict[str, str]:
    with open(path, encoding="utf-8") as fp:
        data = json.load(fp)
    for key in ("生日", "成立周年", "入园周年", "英文"):
        if key not in data:
            raise ValueError(f"文案模板缺少 {key}")
    return data


def render(event: dict, templates: dict[str, str], signature: str) -> str:
    """按事件渲染文案；外文姓名走英文模板。"""
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
