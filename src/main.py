# -*- coding: utf-8 -*-
"""入口：匹配当天节点 -> 生成文案与海报 -> 推送企微。

用法:
  python -m src.main --date 2026-03-05 --dry-run   # 只生成不推送
  python -m src.main                                # 今天，真实推送
  python -m src.main --date 2026-03-05 --force      # 忽略防重复记录重发
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from .copywriting import load_templates, render
from .dingtalk import (DingTalkError, get_access_token, get_userid_by_mobile,
                       send_work_notification, upload_media)
from .poster import make_poster
from .roster import TYPE_FILENAME, load_roster, match_date
from .wecom import (WeComError, get_token, send_app_message, send_robot,
                    upload_image)

ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="老板生日/周年关怀推送")
    p.add_argument("--config", default=str(ROOT / "config.json"))
    p.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天")
    p.add_argument("--dry-run", action="store_true", help="只生成，不推送")
    p.add_argument("--force", action="store_true", help="忽略防重复记录")
    return p.parse_args(argv)


def log_line(log_dir: Path, payload: dict) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "sent.jsonl", "a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def sent_keys(log_dir: Path, day: str) -> set[str]:
    path = log_dir / "sent.jsonl"
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("date") == day and rec.get("status") == "ok":
            keys.add(rec["key"])
    return keys


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[error] 缺少配置文件 {config_path}（可从 config.example.json 复制）")
        return 2
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    day = today.isoformat()
    events = match_date(load_roster(ROOT / cfg["roster_path"]), today)
    if not events:
        print(f"[info] {day} 无命中节点，结束")
        return 0

    templates = load_templates(ROOT / "templates" / "文案模板.json")
    signatures = cfg.get("project_signature", {})
    font_cfg = cfg.get("font", {})
    pw = cfg.get("poster", {})
    size = (int(pw.get("width", 1242)), int(pw.get("height", 2760)))
    out_dir = ROOT / cfg.get("output_dir", "output") / day
    log_dir = ROOT / cfg.get("log_dir", "logs")
    done = set() if args.force else sent_keys(log_dir, day)

    wecom_cfg = cfg.get("wecom", {})
    dt_cfg = cfg.get("dingtalk", {})
    mode = wecom_cfg.get("mode", "app")
    if mode == "robot":
        dry_run = args.dry_run or not wecom_cfg.get("webhook")
    elif mode == "dingtalk":
        dry_run = args.dry_run or not dt_cfg.get("appkey") or "YOUR_" in str(dt_cfg.get("appkey", ""))
    else:
        dry_run = args.dry_run or not wecom_cfg.get("corpid") or "YOUR_" in str(wecom_cfg.get("corpid", ""))
    if not dry_run and mode == "app":
        token = get_token(wecom_cfg["corpid"], wecom_cfg["secret"])

    def push_once(text: str, out_path: Path) -> None:
        """按配置的三种通道推送一条（文案 + 海报）。"""
        if mode == "robot":
            send_robot(wecom_cfg["webhook"], text=text, image_path=out_path)
        elif mode == "dingtalk":
            token = get_access_token(dt_cfg["appkey"], dt_cfg["appsecret"])
            userid = dt_cfg.get("touser_userid")
            if not userid and dt_cfg.get("to_mobile"):
                userid = get_userid_by_mobile(token, dt_cfg["to_mobile"])
            if not userid:
                raise DingTalkError("缺少收件人配置：touser_userid 或 to_mobile")
            media_id = upload_media(token, out_path, out_path.name)
            send_work_notification(token, int(dt_cfg["agentid"]), userid, text=text)
            send_work_notification(token, int(dt_cfg["agentid"]), userid, media_id=media_id)
        else:
            media_id = upload_image(token, out_path, out_path.name)
            send_app_message(token, int(wecom_cfg["agentid"]),
                             wecom_cfg["touser"], text=text)
            send_app_message(token, int(wecom_cfg["agentid"]),
                             wecom_cfg["touser"], media_id=media_id)

    failures = 0
    for ev in events:
        signature = signatures.get(ev["project"], ev["project"] or "产业中天")
        text = render(ev, templates, signature)
        ftype = TYPE_FILENAME[ev["category"]]
        out_path = out_dir / f"{ev['project']}-{ftype}-{today:%m%d}-{ev['name']}.jpg"
        make_poster(ev, text, pw.get("backgrounds", {}).get(ev["category"]),
                    font_cfg, size, out_path)
        key = f"{day}|{ev['name']}|{ev['category']}|{ev['company']}"
        if key in done:
            print(f"[skip] 今日已发送: {key}")
            continue

        if dry_run:
            print(f"[dry-run] 已生成 {out_path.name}")
            print("-" * 40)
            print(text)
            print("-" * 40)
            status, err = "dry-run", ""
        else:
            status, err = "ok", ""
            try:
                push_once(text, out_path)
            except (WeComError, DingTalkError) as exc:  # 重试一次
                time.sleep(3)
                try:
                    push_once(text, out_path)
                except (WeComError, DingTalkError) as exc2:
                    status, err = "fail", str(exc2)
                    failures += 1
            log_line(log_dir, {"ts": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               "date": day, "key": key, "name": ev["name"],
                               "category": ev["category"], "company": ev["company"],
                               "status": status, "error": err,
                               "poster": str(out_path.relative_to(ROOT))})
            print(f"[{status}] {key}" + (f" 错误: {err}" if err else ""))

    if failures:
        print(f"[error] {failures} 条推送失败，请查看日志")
        return 1
    print(f"[info] {day} 处理完成：{len(events)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
