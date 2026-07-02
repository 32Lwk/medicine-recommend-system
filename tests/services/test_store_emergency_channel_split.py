"""Phase 2 (p2-emergency-channel): 緊急応答のチャネル別文言出し分け。

Web/LINE ユーザーに「店内スタッフに連絡」系の文言が出るのは不適切なため、
フラグ SAFETY_EMERGENCY_CHANNEL_SPLIT ON 時は公的窓口（119/110/受診）文言に
出し分ける。店頭キオスク（EMERGENCY_KIOSK_MODE=true）はスタッフ文言を維持する。
"""
from __future__ import annotations

import sys

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.store_emergency_handler import (
    generate_emergency_response,
    resolve_emergency_channel,
)

_STAFF_PHRASE = "店内のスタッフ"


# ---------------------------------------------------------------------------
# フラグ OFF（既定）: 現状維持
# ---------------------------------------------------------------------------

def test_flag_off_web_channel_keeps_staff_wording(monkeypatch):
    monkeypatch.delenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", raising=False)
    resp = generate_emergency_response("medical_emergency", "ja", channel="web")
    assert _STAFF_PHRASE in resp["simple_message"]
    # header（構造化 HTML のみに出現）も従来どおり
    assert "お近くのスタッフにご連絡ください" in resp["structured_html"]


# ---------------------------------------------------------------------------
# フラグ ON: web/line は公的窓口文言、スタッフ文言なし
# ---------------------------------------------------------------------------

def test_flag_on_web_channel_no_staff_wording_uses_public_contact(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("medical_emergency", "ja", channel="web")
    assert _STAFF_PHRASE not in resp["simple_message"]
    assert "119" in resp["simple_message"]
    assert "110" in resp["simple_message"]
    assert "お近くのスタッフにご連絡ください" not in resp["simple_message"]


def test_flag_on_line_channel_no_staff_wording(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("injured_person", "ja", channel="line")
    assert _STAFF_PHRASE not in resp["simple_message"]
    assert "救急車を呼ぶ必要がある場合は、スタッフに伝えてください" not in resp["simple_message"]
    assert "119" in resp["simple_message"]


def test_flag_on_web_channel_witness_types_no_staff_wording(monkeypatch):
    """fire/weapon/violence/suspicious_person は元々ヘッダーは安全優先だが、
    スタッフセクションの本文は公的窓口文言に置き換わる。"""
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    for etype in ("fire", "weapon", "violence", "suspicious_person"):
        resp = generate_emergency_response(etype, "ja", channel="web")
        assert _STAFF_PHRASE not in resp["simple_message"], etype
        # header（構造化 HTML）は元々チャネル非依存で「安全を最優先にしてください」のまま
        assert "安全を最優先にしてください" in resp["structured_html"], etype


def test_flag_on_structured_html_no_staff_wording(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("theft", "ja", channel="web")
    assert _STAFF_PHRASE not in resp["structured_html"]
    assert "盗まれた物品や犯人の特徴をスタッフに伝えてください" not in resp["structured_html"]


# ---------------------------------------------------------------------------
# フラグ ON でもキオスクはスタッフ文言を維持
# ---------------------------------------------------------------------------

def test_flag_on_kiosk_channel_keeps_staff_wording(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("medical_emergency", "ja", channel="kiosk")
    assert _STAFF_PHRASE in resp["simple_message"]
    assert "お近くのスタッフにご連絡ください" in resp["structured_html"]


# ---------------------------------------------------------------------------
# 多言語（en）でも同様に出し分け
# ---------------------------------------------------------------------------

def test_flag_on_english_web_channel_no_staff_wording(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("medical_emergency", "en", channel="web")
    assert "staff" not in resp["simple_message"].lower()
    assert "119" in resp["simple_message"]
    assert "110" in resp["simple_message"]


def test_flag_on_english_kiosk_keeps_staff_wording(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("medical_emergency", "en", channel="kiosk")
    assert "staff" in resp["simple_message"].lower()


# ---------------------------------------------------------------------------
# 安全上の中核情報（110/119案内・安全確保手順）はチャネルに関わらず維持
# ---------------------------------------------------------------------------

def test_flag_on_police_section_unaffected(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp_web = generate_emergency_response("weapon", "ja", channel="web")
    resp_kiosk = generate_emergency_response("weapon", "ja", channel="kiosk")
    assert "110番" in resp_web["simple_message"]
    assert "110番" in resp_kiosk["simple_message"]
    assert "刃物を持っている人がいる場合は、すぐに110番に連絡してください" in resp_web["simple_message"]


def test_flag_on_safety_section_unaffected(monkeypatch):
    monkeypatch.setenv("SAFETY_EMERGENCY_CHANNEL_SPLIT", "true")
    resp = generate_emergency_response("fire", "ja", channel="web")
    assert "すぐに避難してください" in resp["simple_message"]


# ---------------------------------------------------------------------------
# resolve_emergency_channel
# ---------------------------------------------------------------------------

def test_resolve_emergency_channel_kiosk_override(monkeypatch):
    monkeypatch.setenv("EMERGENCY_KIOSK_MODE", "true")
    assert resolve_emergency_channel("web-session-123") == "kiosk"
    assert resolve_emergency_channel(None) == "kiosk"


def test_resolve_emergency_channel_line_vs_web(monkeypatch):
    monkeypatch.delenv("EMERGENCY_KIOSK_MODE", raising=False)
    assert resolve_emergency_channel("line:U1234567890") == "line"
    assert resolve_emergency_channel("web-session-abc") == "web"
    assert resolve_emergency_channel(None) == "web"
