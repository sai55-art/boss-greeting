# -*- coding: utf-8 -*-
"""boss-greeting 管理前端服务：标准库 HTTP 服务，零新增依赖。

启动: .venv/Scripts/python.exe web/server.py  (默认 http://127.0.0.1:8800)
"""
from __future__ import annotations

import base64
import contextlib
import datetime as dt
import io
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

from src.copywriting import load_templates, render  # noqa: E402
from src.poster import make_poster  # noqa: E402
from src.roster import load_roster, match_date  # noqa: E402
from src.wecom import (WeComError, get_token, send_app_message,  # noqa: E402
                       send_robot, upload_image)

STATIC = Path(__file__).resolve().parent / "static"
ROSTER_COLS = ["类别", "企业名称", "所属项目", "姓名", "职务", "性别", "节点日期"]
TYPE_FILENAME = {"生日": "生日", "成立周年": "成立周年", "入园周年": "入园周年"}
CATEGORIES = ["生日", "成立周年", "入园周年"]
LOCK = threading.Lock()


def load_cfg() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def save_cfg(cfg: dict) -> None:
    (ROOT / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def roster_df() -> pd.DataFrame:
    df = pd.read_excel(ROOT / load_cfg()["roster_path"])
    df["节点日期"] = df["节点日期"].astype(str)
    return df.reindex(columns=ROSTER_COLS)


def save_roster(records: list[dict]) -> None:
    df = pd.DataFrame(records, columns=ROSTER_COLS)
    df.to_excel(ROOT / load_cfg()["roster_path"], index=False)


def read_logs(limit: int = 200) -> list[dict]:
    path = ROOT / "logs" / "sent.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out[-limit:]))


def render_events(day: dt.date, make_images: bool) -> list[dict]:
    cfg = load_cfg()
    events = match_date(load_roster(ROOT / cfg["roster_path"]), day)
    templates = load_templates(ROOT / "templates" / "文案模板.json")
    out = []
    for ev in events:
        sig = cfg.get("project_signature", {}).get(ev["project"], ev["project"] or "产业中天")
        copy = render(ev, templates, sig)
        ftype = TYPE_FILENAME[ev["category"]]
        rel = f"output/{day.isoformat()}/{ev['project']}-{ftype}-{day:%m%d}-{ev['name']}.jpg"
        poster = ROOT / rel
        if make_images and not poster.exists():
            make_poster(ev, copy, cfg["poster"]["backgrounds"].get(ev["category"]),
                        cfg.get("font", {}),
                        (int(cfg["poster"]["width"]), int(cfg["poster"]["height"])),
                        poster)
        out.append({"category": ev["category"], "company": ev["company"],
                    "project": ev["project"], "name": ev["name"],
                    "gender": ev["gender"], "years": ev.get("years"),
                    "copy": copy, "poster": "/" + rel if poster.exists() else None})
    return out


# ---------------------------------------------------------------- handlers

def h_roster(method, body, qs):
    with LOCK:
        if method == "GET":
            df = roster_df().fillna("")
            kw = (qs.get("q", [""])[0] or "").strip()
            records = df.to_dict("records")
            if kw:
                records = [r for r in records if any(kw in str(v) for v in r.values())]
            return 200, {"records": records}
        if method == "POST":
            rec = {c: str(body.get(c, "")) for c in ROSTER_COLS}
            if not rec["类别"] or not rec["企业名称"] or not rec["姓名"] or not rec["节点日期"]:
                return 400, {"error": "类别/企业名称/姓名/节点日期 为必填"}
            if rec["类别"] not in CATEGORIES:
                return 400, {"error": f"类别必须是 {'/'.join(CATEGORIES)}"}
            df = roster_df()
            df.loc[len(df)] = rec
            df.to_excel(ROOT / load_cfg()["roster_path"], index=False)
            return 200, {"ok": True}
        if method == "PUT":
            idx = int(qs["index"][0])
            df = roster_df()
            if not (0 <= idx < len(df)):
                return 404, {"error": "记录不存在"}
            rec = {c: str(body.get(c, df.iat[idx, i])) for i, c in enumerate(ROSTER_COLS)}
            if rec["类别"] not in CATEGORIES:
                return 400, {"error": f"类别必须是 {'/'.join(CATEGORIES)}"}
            for i, c in enumerate(ROSTER_COLS):
                df.iat[idx, i] = rec[c]
            df.to_excel(ROOT / load_cfg()["roster_path"], index=False)
            return 200, {"ok": True}
        if method == "DELETE":
            idx = int(qs["index"][0])
            df = roster_df()
            if not (0 <= idx < len(df)):
                return 404, {"error": "记录不存在"}
            df = df.drop(idx).reset_index(drop=True)
            df.to_excel(ROOT / load_cfg()["roster_path"], index=False)
            return 200, {"ok": True}
    return 405, {"error": "method not allowed"}


def h_roster_import(body):
    raw = base64.b64decode(body.get("data_b64", ""))
    df = pd.read_excel(io.BytesIO(raw))
    df.columns = [str(c).strip() for c in df.columns]
    required = {"类别", "企业名称", "姓名", "节点日期"}
    if not required.issubset(df.columns):
        return 400, {"error": f"导入文件缺少必填列，需要包含：{sorted(required)}（当前列：{list(df.columns)}）"}
    cmap = {c: (c if c in ROSTER_COLS else None) for c in df.columns}
    out = pd.DataFrame(columns=ROSTER_COLS)
    for c in ROSTER_COLS:
        if c in df.columns:
            out[c] = df[c]
    out["类别"] = out["类别"].astype(str).str.strip()
    bad = ~out["类别"].isin(CATEGORIES)
    if bad.any():
        return 400, {"error": f"第 {list(out.index[bad][:5])} 行类别无效（需为 {'/'.join(CATEGORIES)}）"}
    dates = pd.to_datetime(out["节点日期"], errors="coerce")
    if dates.isna().any():
        return 400, {"error": "存在无法解析的节点日期"}
    out["节点日期"] = dates.dt.strftime("%Y-%m-%d")
    for c in ROSTER_COLS:
        out[c] = out[c].fillna("").astype(str).str.strip()
    with LOCK:
        out.to_excel(ROOT / load_cfg()["roster_path"], index=False)
    return 200, {"ok": True, "count": len(out)}


def h_roster_export():
    buf = io.BytesIO()
    with LOCK:
        roster_df().to_excel(buf, index=False)
    return 200, buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", \
        "attachment; filename=guanhuai-taizhang.xlsx"


def h_config(method, body, qs=None):
    if method == "GET":
        cfg = load_cfg()
        if cfg.get("wecom", {}).get("webhook"):
            cfg["wecom"]["webhook_masked"] = cfg["wecom"]["webhook"][:60] + "…"
        return 200, {"config": cfg}
    if method == "PUT":
        with LOCK:
            cfg = load_cfg()
            for section in ("wecom", "font", "poster", "project_signature"):
                if section in body:
                    cfg[section] = body[section]
            save_cfg(cfg)
        return 200, {"ok": True}
    return 405, {"error": "method not allowed"}


def h_config_test():
    cfg = load_cfg()["wecom"]
    text = "【关怀助手】测试消息：通道正常 ✅"
    try:
        if cfg.get("mode") == "robot":
            send_robot(cfg["webhook"], text=text)
        else:
            token = get_token(cfg["corpid"], cfg["secret"])
            send_app_message(token, int(cfg["agentid"]), cfg["touser"], text=text)
        return 200, {"ok": True}
    except WeComError as exc:
        return 502, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": f"{type(exc).__name__}: {exc}"}


def h_templates(method, body, qs=None):
    path = ROOT / "templates" / "文案模板.json"
    if method == "GET":
        return 200, {"templates": load_templates(path)}
    if method == "PUT":
        for key in CATEGORIES + ["英文"]:
            if not str(body.get(key, "")).strip():
                return 400, {"error": f"模板 {key} 不能为空"}
        data = {k: str(body[k]) for k in CATEGORIES + ["英文"]}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return 200, {"ok": True}
    return 405, {"error": "method not allowed"}


def h_poster_bg(body):
    category = body.get("category")
    if category not in CATEGORIES:
        return 400, {"error": "category 无效"}
    try:
        img = Image.open(io.BytesIO(base64.b64decode(body.get("data_b64", "")))).convert("RGB")
    except Exception:  # noqa: BLE001
        return 400, {"error": "图片解析失败，请上传 png/jpg"}
    cfg = load_cfg()["poster"]
    img = img.resize((int(cfg["width"]), int(cfg["height"])), Image.LANCZOS)
    with LOCK:
        (ROOT / "templates" / f"背景-{category}.png").unlink(missing_ok=True)
        img.save(ROOT / "templates" / f"背景-{category}.png")
    return 200, {"ok": True, "size": list(img.size)}


def h_logs():
    return 200, {"logs": read_logs()}


def h_run(body):
    date = body.get("date") or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        return 400, {"error": "日期格式应为 YYYY-MM-DD"}
    argv = ["--date", date]
    if body.get("dry_run", True):
        argv.append("--dry-run")
    buf = io.StringIO()
    from src import main as main_mod
    with contextlib.redirect_stdout(buf):
        code = main_mod.main(argv)
    return 200, {"code": code, "output": buf.getvalue()}


def h_preview(qs):
    date = (qs.get("date") or [dt.date.today().isoformat()])[0]
    try:
        day = dt.date.fromisoformat(date)
    except ValueError:
        return 400, {"error": "日期格式应为 YYYY-MM-DD"}
    return 200, {"date": day.isoformat(), "events": render_events(day, make_images=True)}


def h_dashboard():
    today = dt.date.today()
    cfg = load_cfg()
    counts = roster_df()["类别"].value_counts().to_dict()
    return 200, {
        "today": today.isoformat(),
        "events": render_events(today, make_images=True),
        "counts": counts,
        "recent": read_logs(8),
        "channel": {"mode": cfg["wecom"].get("mode"),
                    "webhook_set": bool(cfg["wecom"].get("webhook"))},
    }


def h_bg(category):
    path = ROOT / "templates" / f"背景-{category}.png"
    if not path.exists():
        return 404, None, None, None
    return 200, path.read_bytes(), "image/png", None


# ---------------------------------------------------------------- server

ROUTES = {
    ("/api/roster",): h_roster,
    ("/api/config",): h_config,
    ("/api/templates",): h_templates,
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: A003
        sys.stderr.write("[web] %s\n" % (fmt % args))

    # -- helpers
    def _json(self, code: int, payload) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, ctype: str, download: str | None = None) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if download:
            self.send_header("Content-Disposition", download)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # -- dispatch
    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)
        try:
            if path == "/" or path == "/index.html":
                return self._file(STATIC / "index.html", "text/html; charset=utf-8")
            if path.startswith("/static/"):
                target = (STATIC / path.removeprefix("/static/")).resolve()
                if not str(target).startswith(str(STATIC)) or not target.is_file():
                    return self._json(404, {"error": "not found"})
                ctype = {"css": "text/css; charset=utf-8",
                         "js": "text/javascript; charset=utf-8",
                         "svg": "image/svg+xml"}.get(target.suffix.lstrip("."), "application/octet-stream")
                return self._file(target, ctype)
            if path.startswith("/output/"):
                target = (ROOT / path.lstrip("/")).resolve()
                root_out = (ROOT / "output").resolve()
                if not str(target).startswith(str(root_out)) or not target.is_file():
                    return self._json(404, {"error": "not found"})
                return self._file(target, "image/jpeg")
            if path == "/api/roster/export" and method == "GET":
                code, data, ctype, dispo = h_roster_export()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Disposition", dispo)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                return self.wfile.write(data)
            if path == "/api/roster/import" and method == "POST":
                code, payload = h_roster_import(self._body())
                return self._json(code, payload)
            if path == "/api/config/test" and method == "POST":
                code, payload = h_config_test()
                return self._json(code, payload)
            if path == "/api/logs" and method == "GET":
                code, payload = h_logs()
                return self._json(code, payload)
            if path == "/api/run" and method == "POST":
                code, payload = h_run(self._body())
                return self._json(code, payload)
            if path == "/api/preview" and method == "GET":
                code, payload = h_preview(qs)
                return self._json(code, payload)
            if path == "/api/dashboard" and method == "GET":
                code, payload = h_dashboard()
                return self._json(code, payload)
            for seg in CATEGORIES:
                if path == f"/api/bg/{seg}" and method == "GET":
                    code, data, ctype, _ = h_bg(seg)
                    if code != 200:
                        return self._json(404, {"error": "未上传该背景"})
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    return self.wfile.write(data)
            for prefix, fn in ROUTES.items():
                if path == prefix[0]:
                    body = self._body() if method in ("POST", "PUT") else {}
                    code, payload = fn(method, body, qs)
                    return self._json(code, payload)
            return self._json(404, {"error": "not found"})
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[web] error {path}: {type(exc).__name__}: {exc}\n")
            try:
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            except Exception:  # noqa: BLE001
                pass

    def do_GET(self):  # noqa: N802
        self._dispatch("GET")

    def do_POST(self):  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self):  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self):  # noqa: N802
        self._dispatch("DELETE")


def main() -> None:
    host, port = "127.0.0.1", 8800
    args = sys.argv[1:]
    if "--host" in args:
        host = args[args.index("--host") + 1]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"boss-greeting 管理端: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
