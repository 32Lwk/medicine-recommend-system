"""Tests for sage bot response helper."""
from src.services.sage_bot_response import (
    build_bot_response,
    build_counseling_bot,
    build_notice_bot,
    effective_sid,
    sage_content_marker,
)


def test_sage_content_marker():
    assert sage_content_marker({"render": "sage_reco"}) == "sage_reco"
    assert sage_content_marker({"render": "sage_qa"}) == "sage_qa"
    assert sage_content_marker({"render": "sage_status"}) == "sage_status"


def test_build_bot_response_sage():
    session = {"ui_variant": "sage"}
    diag = {"render": "sage_status", "title": "test"}
    out = build_bot_response(session, "sid-1", sage_diagnosis=diag, legacy_content="<html>")
    assert out["content"] == "sage_status"
    assert out["diagnosis"] == diag


def test_build_bot_response_legacy():
    session = {"ui_variant": "legacy"}
    out = build_bot_response(session, "sid-1", sage_diagnosis={"render": "sage_status"}, legacy_content="<html>")
    assert out["content"] == "<html>"
    assert "diagnosis" not in out


def test_build_counseling_bot():
    session = {"ui_variant": "sage"}
    out = build_counseling_bot(session, "sid-1", "カウンセリング本文", kind="counseling")
    assert out["content"] == "sage_status"
    assert out["diagnosis"]["message"] == "カウンセリング本文"
    assert out["counseling"] is True


def test_build_counseling_bot_duplicate_counseling_kwarg():
    """Callers may pass counseling=True; must not raise TypeError."""
    session = {"ui_variant": "sage"}
    out = build_counseling_bot(
        session, "sid-1", "恋の病、しんどいですね。", kind="counseling_initial", counseling=True
    )
    assert out["counseling"] is True


def test_build_notice_bot():
    session = {"ui_variant": "sage"}
    out = build_notice_bot(session, "sid-1", "ブロックされました", kind="security_block", variant="security")
    assert out["content"] == "sage_status"
    assert out["diagnosis"]["kind"] == "security_block"
