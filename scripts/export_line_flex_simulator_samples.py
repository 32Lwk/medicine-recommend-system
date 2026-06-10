#!/usr/bin/env python3
"""
Flex Message Simulator 用サンプル JSON を出力する。

https://developers.line.biz/flex-simulator/ に bubble / carousel の contents を貼って調整できます。

使い方:
  python scripts/export_line_flex_simulator_samples.py
  python scripts/export_line_flex_simulator_samples.py --kind status_caution --out caution.json
  python scripts/export_line_flex_simulator_samples.py --list
"""
from __future__ import annotations

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("SECRET_KEY", "export-script")
os.environ.setdefault("PUBLIC_SITE_URL", "https://medicine.yutok.dev")


def _kinds() -> dict[str, callable]:
    from src.handlers.line.flex_messages import (
        build_advice_bubble,
        build_line_messages_from_bot_message,
        build_recommendation_carousel,
        build_status_bubble,
    )
    from src.handlers.line.line_dev_triggers import sample_bot_message_for_kind
    from src.handlers.line.line_i18n import get_line_ui_strings

    ui = get_line_ui_strings("ja")

    def success_advice():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_success"))
        return msgs[0]["contents"]

    def success_carousel():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_success"))
        return msgs[1]["contents"]

    def status_caution():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_escalation"))
        return msgs[0]["contents"]

    def status_critical():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_crisis"))
        return msgs[0]["contents"]

    def status_notice():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_questions"))
        return msgs[0]["contents"]

    def status_pharmacist():
        msgs = build_line_messages_from_bot_message(sample_bot_message_for_kind("flex_safe_error"))
        return msgs[0]["contents"]

    def status_info_demo():
        return build_status_bubble(
            "info",
            title=ui["status_info_title"],
            alt_text=ui["status_info_title"],
            subtitle="カウンセリング・店舗案内などの本文サンプル",
            body_paragraphs=["お困りの症状について、引き続きお手伝いします。"],
            footer_note=ui["footer_caution"],
            ui=ui,
        )["contents"]

    return {
        "success_advice": success_advice,
        "success_carousel": success_carousel,
        "status_caution": status_caution,
        "status_critical": status_critical,
        "status_notice": status_notice,
        "status_pharmacist": status_pharmacist,
        "status_info": status_info_demo,
    }


def main() -> None:
    kinds = _kinds()
    parser = argparse.ArgumentParser(description="Export LINE Flex samples for Flex Simulator")
    parser.add_argument("--kind", choices=sorted(kinds), default="success_advice")
    parser.add_argument("--list", action="store_true", help="List available kinds")
    parser.add_argument("--out", default="", help="Write JSON to file instead of stdout")
    parser.add_argument("--all", action="store_true", help="Write all kinds to tests/fixtures/line_flex_simulator/")
    args = parser.parse_args()

    if args.list:
        for name in sorted(kinds):
            print(name)
        return

    if args.all:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "fixtures", "line_flex_simulator")
        os.makedirs(out_dir, exist_ok=True)
        for name, fn in kinds.items():
            path = os.path.join(out_dir, f"{name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(fn(), f, ensure_ascii=False, indent=2)
            print(path)
        return

    payload = kinds[args.kind]()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
