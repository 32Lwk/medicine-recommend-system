"""session_sid ユーティリティのテスト。"""
from __future__ import annotations

from src.utils.session_sid import (
    bind_request_session_sid,
    resolve_effective_session_id,
    session_sid_matches,
    warn_session_sid_mismatch,
)


def test_bind_request_session_sid_sets_id():
    session = {}
    bind_request_session_sid(session, "abc123")
    assert session["_id"] == "abc123"


def test_bind_request_session_sid_rebinds_on_mismatch():
    session = {"_id": "old"}
    bind_request_session_sid(session, "new")
    assert session["_id"] == "new"


def test_session_sid_matches():
    assert session_sid_matches({"_id": "x"}, "x")
    assert not session_sid_matches({"_id": "x"}, "y")


def test_warn_session_sid_mismatch():
    assert warn_session_sid_mismatch({"_id": "a"}, "a", context="t")
    assert not warn_session_sid_mismatch({"_id": "a"}, "b", context="t")


def test_resolve_effective_session_id_prefers_request():
    assert resolve_effective_session_id({"_id": "bound"}, "req") == "req"


def test_resolve_effective_session_id_falls_back_to_session():
    assert resolve_effective_session_id({"_id": "bound"}, None) == "bound"
