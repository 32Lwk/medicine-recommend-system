"""LINE webhook 去重のテスト。"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.handlers.line import line_dedup


@pytest.fixture(autouse=True)
def _reset_dedup(tmp_path, monkeypatch):
    line_dedup.reset_dedup_cache_for_tests()
    monkeypatch.setenv("LINE_LOCK_DIR", str(tmp_path))


def test_extract_webhook_dedup_key_prefers_event_id():
    event = {
        "webhookEventId": "evt-1",
        "replyToken": "tok",
        "message": {"id": "m1"},
        "source": {"userId": "U1"},
    }
    assert line_dedup.extract_webhook_dedup_key(event) == "wev:evt-1"


def test_extract_webhook_dedup_key_falls_back_to_message_id():
    event = {
        "replyToken": "tok",
        "message": {"id": "m1"},
        "source": {"userId": "U1"},
    }
    assert line_dedup.extract_webhook_dedup_key(event) == "msg:U1:m1"


def test_mark_webhook_event_seen_detects_duplicate_in_process():
    key = "wev:evt-dup"
    assert line_dedup.mark_webhook_event_seen(key) is False
    assert line_dedup.mark_webhook_event_seen(key) is True


@pytest.mark.skipif(os.name == "nt", reason="ファイル去重は Linux 向け")
def test_mark_webhook_event_seen_detects_duplicate_across_claim(tmp_path):
    key = "wev:evt-file"
    assert line_dedup.mark_webhook_event_seen(key) is False
    line_dedup.reset_dedup_cache_for_tests()
    assert line_dedup.mark_webhook_event_seen(key) is True
    marker = tmp_path / f"line-wh-{key.replace(':', '_')}.marker"
    assert marker.exists()
