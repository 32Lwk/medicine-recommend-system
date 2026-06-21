"""LINE リッチメニュー定義と Messaging API 登録。"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from config.line_config import get_line_channel_access_token
from src.handlers.line.flex_messages import _public_site_base
from src.handlers.line.line_quick_actions import POSTBACK_PREFIX

logger = logging.getLogger(__name__)

RICH_MENU_API = "https://api.line.me/v2/bot/richmenu"
DEFAULT_MENU_NAME = "medicine-recommend-main"

# 2500x843 PNG（3 分割タップ領域用）。`static/line/` に複数パターンあり。
RICH_MENU_IMAGE_PATTERNS: dict[str, str] = {
    "a-sage-minimal": "static/line/rich-menu-pattern-a-sage-minimal.png",
    "b-clinical": "static/line/rich-menu-pattern-b-clinical.png",
    "c-pamphlet": "static/line/rich-menu-pattern-c-pamphlet.png",
    "d-dark-sage": "static/line/rich-menu-pattern-d-dark-sage.png",
}


def build_rich_menu_definition(*, public_base: str | None = None) -> dict[str, Any]:
    """
    3 分割リッチメニュー（2500x843）。
    - 詳細をWebで見る: postback（都度 handoff トークン発行）
    - 薬剤師に相談: postback（確認 Flex）
    - 使い方: /about へ URI
    """
    base = (public_base or _public_site_base()).rstrip("/")
    about_url = f"{base}/about"
    return {
        "size": {"width": 2500, "height": 843},
        "selected": True,
        "name": DEFAULT_MENU_NAME,
        "chatBarText": "メニュー",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {
                    "type": "postback",
                    "label": "詳細をWebで見る",
                    "data": f"{POSTBACK_PREFIX}|web_detail",
                    "displayText": "詳細をWebで見る",
                },
            },
            {
                "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
                "action": {
                    "type": "postback",
                    "label": "薬剤師に相談",
                    "data": f"{POSTBACK_PREFIX}|pharmacist",
                    "displayText": "薬剤師に相談",
                },
            },
            {
                "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
                "action": {
                    "type": "uri",
                    "label": "使い方",
                    "uri": about_url,
                },
            },
        ],
    }


def register_rich_menu(
    *,
    access_token: str | None = None,
    image_path: str | None = None,
    set_default: bool = True,
) -> dict[str, Any]:
    """
    リッチメニューを LINE に登録し、任意で画像アップロード・デフォルト設定。

    image_path 未指定時はメニュー JSON のみ登録（LINE 管理画面で画像を後付け可能）。
    """
    token = (access_token or get_line_channel_access_token()).strip()
    if not token:
        return {"ok": False, "error": "LINE_CHANNEL_ACCESS_TOKEN not configured"}

    definition = build_rich_menu_definition()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=30.0) as client:
        create_resp = client.post(RICH_MENU_API, headers=headers, content=json.dumps(definition))
        if create_resp.status_code >= 400:
            return {
                "ok": False,
                "error": "create_failed",
                "status": create_resp.status_code,
                "body": create_resp.text,
            }
        rich_menu_id = create_resp.json().get("richMenuId")
        if not rich_menu_id:
            return {"ok": False, "error": "missing_richMenuId", "body": create_resp.text}

        image_uploaded = False
        resolved_image = image_path or os.getenv("LINE_RICH_MENU_IMAGE_PATH", "").strip()
        if resolved_image and os.path.isfile(resolved_image):
            with open(resolved_image, "rb") as img_file:
                upload_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "image/png",
                }
                upload_resp = client.post(
                    f"{RICH_MENU_API}/{rich_menu_id}/content",
                    headers=upload_headers,
                    content=img_file.read(),
                )
            if upload_resp.status_code >= 400:
                return {
                    "ok": False,
                    "error": "image_upload_failed",
                    "richMenuId": rich_menu_id,
                    "status": upload_resp.status_code,
                    "body": upload_resp.text,
                }
            image_uploaded = True

        default_set = False
        if set_default:
            default_resp = client.post(
                f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
                headers=headers,
            )
            if default_resp.status_code >= 400:
                return {
                    "ok": False,
                    "error": "set_default_failed",
                    "richMenuId": rich_menu_id,
                    "status": default_resp.status_code,
                    "body": default_resp.text,
                }
            default_set = True

    logger.info(
        "LINE rich menu registered richMenuId=%s image=%s default=%s",
        rich_menu_id,
        image_uploaded,
        default_set,
    )
    return {
        "ok": True,
        "richMenuId": rich_menu_id,
        "imageUploaded": image_uploaded,
        "defaultSet": default_set,
        "aboutUrl": f"{_public_site_base().rstrip('/')}/about",
    }
