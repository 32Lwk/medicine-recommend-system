"""Phase 3 (p3-store-procurement): OTC/市販薬 購入先クエリの Store ルーティング補完。

「OTCを買える店」(store-03) / 「市販薬の購入先」(store-06) が counseling_unknown_request /
Physical に誤流入する回帰への対応を検証する。根本原因は classify_medicine_procurement_route が
明示的な処方箋文脈を要求し、それが無いと None を返していたこと（flag ON で otc_store をデフォルト化）。
"""
from __future__ import annotations

import sys

import pytest

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.counseling_triage import classify_medicine_procurement_route
from src.services.store_inquiry_handler import (
    has_unambiguous_store_intent,
    is_probable_store_inquiry,
)
from src.dialogue.routing.gate import _has_pharmacy_location_intent


_TRIAGE_GENERAL = {"category": "Other", "confidence": 0.9, "subcategory": "general_other"}


# ---------------------------------------------------------------------------
# classify_medicine_procurement_route: flag OFF（既定）= 現状維持
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "OTCを買える店",
        "市販薬の購入先",
    ],
)
def test_flag_off_ambiguous_otc_query_returns_none(monkeypatch, text):
    """flag OFF: 処方箋文脈が明示されていない OTC 購入先クエリは従来どおり None（現状維持）。"""
    monkeypatch.delenv("ROUTING_STORE_PROCUREMENT", raising=False)
    assert classify_medicine_procurement_route(text) is None


# ---------------------------------------------------------------------------
# classify_medicine_procurement_route: flag ON = otc_store デフォルト化
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "OTCを買える店",
        "市販薬の購入先",
        "市販薬を買える店はどこ",
        "OTCを買いたい",
        "OTCが購入できる店を教えて",
    ],
)
def test_flag_on_otc_procurement_defaults_to_otc_store(monkeypatch, text):
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    assert classify_medicine_procurement_route(text) == "otc_store"


def test_flag_on_still_respects_explicit_prescription_context(monkeypatch):
    """flag ON でも、明示的な処方箋文脈は従来どおり pharmacy_prescription を優先。"""
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    assert classify_medicine_procurement_route("処方箋の購入先") == "pharmacy_prescription"
    assert classify_medicine_procurement_route("処方箋なしの購入先") == "otc_store"


def test_flag_on_unrelated_procurement_still_none(monkeypatch):
    """flag ON でも、procurement intent 自体が無い/OTC文脈が無い入力は None のまま。"""
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    assert classify_medicine_procurement_route("こんにちは") is None
    assert classify_medicine_procurement_route("頭が痛い") is None
    # 既存回帰: 規制薬物の購入先は OTC 文脈なし・処方文脈なしのため引き続き None
    assert classify_medicine_procurement_route("向精神薬の購入先") is None


# ---------------------------------------------------------------------------
# is_probable_store_inquiry / has_unambiguous_store_intent への波及
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["OTCを買える店", "市販薬の購入先"])
def test_flag_off_store03_06_not_probable(monkeypatch, text):
    monkeypatch.delenv("ROUTING_STORE_PROCUREMENT", raising=False)
    assert is_probable_store_inquiry(text, _TRIAGE_GENERAL) is False
    assert has_unambiguous_store_intent(text) is False


@pytest.mark.parametrize("text", ["OTCを買える店", "市販薬の購入先"])
def test_flag_on_store03_06_becomes_probable(monkeypatch, text):
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    assert is_probable_store_inquiry(text, _TRIAGE_GENERAL) is True
    assert has_unambiguous_store_intent(text) is True


# ---------------------------------------------------------------------------
# gate.py: _has_pharmacy_location_intent
# ---------------------------------------------------------------------------

def test_gate_otc_wording_already_covered_by_existing_keywords(monkeypatch):
    """"OTCを買える店" は _PHARMACY_LOCATION_KEYWORDS に既存の "otc" + 位置語"買える"の
    組み合わせで、本タスクの変更前から True（既存カバレッジ）。flag に関わらず True を維持する。"""
    monkeypatch.delenv("ROUTING_STORE_PROCUREMENT", raising=False)
    assert _has_pharmacy_location_intent("OTCを買える店") is True
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    assert _has_pharmacy_location_intent("OTCを買える店") is True


def test_gate_market_medicine_wording_unaffected_by_flag(monkeypatch):
    """既存の「市販薬」+購入語の判定は flag に関わらず従来どおり True。"""
    monkeypatch.delenv("ROUTING_STORE_PROCUREMENT", raising=False)
    assert _has_pharmacy_location_intent("市販薬の購入先") is True


# ---------------------------------------------------------------------------
# store-01/02/04 (既存 Store シナリオ) の is_probable_store_inquiry 回帰なし
# store-05（マツキヨ）は is_probable_store_inquiry 以外の経路で解決されるため対象外
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "近くの薬局を教えて",
        "処方箋なしで買える場所",
    ],
)
def test_existing_store_scenarios_unaffected_by_flag(monkeypatch, text):
    monkeypatch.delenv("ROUTING_STORE_PROCUREMENT", raising=False)
    before = is_probable_store_inquiry(text, _TRIAGE_GENERAL)
    monkeypatch.setenv("ROUTING_STORE_PROCUREMENT", "true")
    after = is_probable_store_inquiry(text, _TRIAGE_GENERAL)
    assert before is True
    assert after is True

