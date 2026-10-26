# -*- coding: utf-8 -*-
"""钉钉企业内部应用推送：工作通知单发给指定人。仅用标准库。

权限要求：qyapi_base（工作通知，默认开通）、qyapi_get_member（手机号查 userid）。
"""
from __future__ import annotations

import json
import urllib.request
import uuid

_OAPI = "https://oapi.dingtalk.com"


class DingTalkError(RuntimeError):
    pass


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("errcode"):
        raise DingTalkError(f"{data.get('errcode')}: {data.get('errmsg')}")
    return data


def get_access_token(appkey: str, appsecret: str) -> str:
    req = urllib.request.Request(f"{_OAPI}/gettoken?appkey={appkey}&appsecret={appsecret}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("errcode"):
        raise DingTalkError(f"获取 access_token 失败: {data}")
    return data["access_token"]


def get_userid_by_mobile(token: str, mobile: str) -> str:
    result = _post_json(f"{_OAPI}/topapi/v2/user/getbymobile?access_token={token}",
                        {"mobile": mobile})
    return result["result"]["userid"]


def upload_media(token: str, image_path: str | bytes, filename: str = "poster.jpg") -> str:
    data = image_path if isinstance(image_path, bytes) else open(image_path, "rb").read()
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: image/jpeg\r\n\r\n",
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{_OAPI}/media/upload?access_token={token}&type=image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("errcode"):
        raise DingTalkError(f"上传素材失败: {result}")
    return result["media_id"]


def send_work_notification(token: str, agent_id: int, userid: str,
                           text: str | None = None, media_id: str | None = None) -> dict:
    """工作通知单发。text 与 image 都给则分两条。"""
    results = []
    if text is not None:
        payload = {"agent_id": agent_id, "userid_list": userid,
                   "msg": {"msgtype": "markdown",
                           "markdown": {"title": "关怀提醒", "text": text}}}
        results.append(_post_json(
            f"{_OAPI}/topapi/message/corpconversation/asyncsend_v2?access_token={token}",
            payload))
    if media_id is not None:
        payload = {"agent_id": agent_id, "userid_list": userid,
                   "msg": {"msgtype": "image", "image": {"media_id": media_id}}}
        results.append(_post_json(
            f"{_OAPI}/topapi/message/corpconversation/asyncsend_v2?access_token={token}",
            payload))
    return results[-1] if results else {}
