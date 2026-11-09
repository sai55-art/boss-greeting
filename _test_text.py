# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

ROOT = Path("/home/sai/boss-greeting")
sys.path.insert(0, str(ROOT))
from src.dingtalk import get_access_token, get_userid_by_mobile, send_work_notification

cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
dt = cfg["dingtalk"]
token = get_access_token(dt["appkey"], dt["appsecret"])
uid = get_userid_by_mobile(token, "18439120467")
r = send_work_notification(token, int(dt["agentid"]), uid, text="单条文本通道测试")
print("sent:", r)
