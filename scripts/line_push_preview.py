#!/usr/bin/env python3
"""
LINE Push API で Flex プレビューを送信（Webhook 不要）。

使い方:
  python scripts/line_push_preview.py --dry-run
  python scripts/line_push_preview.py --trigger flex_success --dry-run
  python scripts/line_push_preview.py --user-id Uxxxxxxxx
  python scripts/line_push_preview.py --symptom "頭が痛い" --user-id Uxxxxxxxx
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("SECRET_KEY", "preview-script")


_PREVIEW_KINDS = (
    "flex_success",
    "flex_escalation",
    "flex_crisis",
    "flex_questions",
    "flex_safe_error",
)


async def _push(user_id: str, messages: list[dict]) -> None:
    from src.handlers.line.line_reply import push_messages, set_http_client
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        set_http_client(client)
        for msg in messages:
            ok = await push_messages(user_id, [msg])
            if not ok:
                raise SystemExit("Push failed (check LINE_CHANNEL_ACCESS_TOKEN)")


def main() -> None:
    from config.app_config import load_env

    load_env()

    parser = argparse.ArgumentParser(description="LINE Flex Push preview")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON only, no Push")
    parser.add_argument("--user-id", default="", help="LINE userId (overrides LINE_PUSH_TO_USER_ID)")
    parser.add_argument("--symptom", default="", help="Run chat pipeline with this message")
    parser.add_argument(
        "--trigger",
        choices=_PREVIEW_KINDS,
        default="flex_success",
        help="Dev preview sample kind (default: flex_success)",
    )
    args = parser.parse_args()

    from config.line_config import LINE_PUSH_TO_USER_ID
    from src.handlers.line.flex_messages import build_line_messages_from_bot_message
    from src.handlers.line.line_dev_triggers import sample_bot_message_for_kind

    user_id = (args.user_id or LINE_PUSH_TO_USER_ID).strip()

    if args.symptom:
        from src.handlers.chat_handler import handle_chat_post
        from src.handlers.line.line_session import get_latest_bot_message, line_sid, prime_line_session
        from src.utils.chat_http_context import ChatClientInfo
        from src.utils.performance_monitor import get_global_monitor

        if not user_id:
            raise SystemExit("--user-id or LINE_PUSH_TO_USER_ID required for --symptom")
        session = prime_line_session(user_id)
        sid = line_sid(user_id)
        monitor = get_global_monitor()
        handle_chat_post(session, ChatClientInfo("127.0.0.1", "line-push-preview"), args.symptom, sid, monitor)
        bot = get_latest_bot_message(sid)
        if not bot:
            raise SystemExit("No bot message from pipeline")
        messages = build_line_messages_from_bot_message(bot, lang=session.get("detected_language"), session_id=sid)
    else:
        messages = build_line_messages_from_bot_message(sample_bot_message_for_kind(args.trigger))

    if args.dry_run:
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        return

    if not user_id:
        raise SystemExit("Set --user-id or LINE_PUSH_TO_USER_ID in .env")

    asyncio.run(_push(user_id, messages))
    print(f"Pushed {len(messages)} message(s) to {user_id}")


if __name__ == "__main__":
    main()
