# -*- coding: utf-8 -*-
"""企业微信推送：应用单发（优先）与群机器人 webhook（降级）。仅用标准库。"""
from __future__ import annotations

import json
import urllib.request
import uuid

_API = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComError(RuntimeError):
    pass


def _post(url: str, data: bytes, content_type: str) -> dict:
    req = urllib.request.Request(url, data=data, headers={"Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_token(corpid: str, secret: str) -> str:
    url = f"{_API}/gettoken?corpid={corpid}&corpsecret={secret}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("errcode"):
        raise WeComError(f"获取 access_token 失败: {data}")
    return data["access_token"]


def upload_image(token: str, image_path: str | bytes, filename: str = "poster.jpg") -> str:
    """上传临时图片素材，返回 media_id（3 天有效）。"""
    data = image_path if isinstance(image_path, bytes) else open(image_path, "rb").read()
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: image/jpeg\r\n\r\n",
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    url = f"{_API}/media/upload?access_token={token}&type=image"
    result = _post(url, body, f"multipart/form-data; boundary={boundary}")
    if result.get("errcode"):
        raise WeComError(f"上传素材失败: {result}")
    return result["media_id"]


def send_app_message(token: str, agentid: int, touser: str,
                     text: str | None = None, media_id: str | None = None) -> dict:
    """应用单发：text 与 image 二选一（都给则发两条）。"""
    results = []
    if text is not None:
        payload = {"touser": touser, "msgtype": "text", "agentid": agentid,
                   "text": {"content": text}}
        results.append(_post(f"{_API}/message/send?access_token={token}",
                             json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             "application/json; charset=utf-8"))
    if media_id is not None:
        payload = {"touser": touser, "msgtype": "image", "agentid": agentid,
                   "image": {"media_id": media_id}}
        results.append(_post(f"{_API}/message/send?access_token={token}",
                             json.dumps(payload).encode("utf-8"),
                             "application/json; charset=utf-8"))
    for r in results:
        if r.get("errcode"):
            raise WeComError(f"发送失败: {r}")
    return results[-1] if results else {}


def send_robot(webhook: str, text: str | None = None,
               image_path: str | bytes | None = None) -> None:
    """群机器人降级通道：markdown 文案 + base64 图片。"""
    import base64

    if text is not None:
        payload = {"msgtype": "markdown", "markdown": {"content": text.replace("\n", "\n")}}
        req = urllib.request.Request(webhook, data=json.dumps(
            payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("errcode"):
            raise WeComError(f"机器人发送失败: {data}")
    if image_path is not None:
        raw = image_path if isinstance(image_path, bytes) else open(image_path, "rb").read()
        payload = {"msgtype": "image", "image": {
            "base64": base64.b64encode(raw).decode(), "md5": __import__("hashlib").md5(raw).hexdigest()}}
        req = urllib.request.Request(webhook, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("errcode"):
            raise WeComError(f"机器人发图失败: {data}")
