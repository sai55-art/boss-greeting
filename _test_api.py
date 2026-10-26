# -*- coding: utf-8 -*-
"""API 全接口测试（本地服务）。PASS/FAIL 逐项输出。"""  # noqa
import base64  # noqa
import json  # noqa
import urllib.error  # noqa
import urllib.request  # noqa

BASE = "http://127.0.0.1:8800"
results = []


def call(method, path, body=None, raw=False):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            payload = resp.read()
            out = payload if raw else json.loads(payload.decode("utf-8"))
            return resp.status, out
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload.decode("utf-8"))
        except Exception:
            return e.code, payload


def check(name, cond):
    results.append((name, bool(cond)))


# 1. 静态资源
s, b = call("GET", "/")
check("GET / 首页", s == 200 and b"html" in b[:300])
s, b = call("GET", "/static/app.js", raw=True)
check("GET /static/app.js", s == 200)
s, b = call("GET", "/api/bg/生日", raw=True)
check("GET /api/bg/生日", s == 200 and b[:4] == b"\x89PNG")

# 2. 仪表盘
s, d = call("GET", "/api/dashboard")
need = {"today", "events", "counts", "recent", "channel"}
check("dashboard 结构", s == 200 and need <= set(d))

# 3. 台账 CRUD
s, d = call("GET", "/api/roster")
n0 = len(d["records"])
check("roster 列表", s == 200 and n0 >= 50)
test_rec = {"类别: 1, "企业名称: 1, "所属项目: 1,
            "姓名: 1, "职务: 1, "性别: 1, "节点日期: 1}
