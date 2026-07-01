"""local_v2_chat_test_runner._kind_route の kind 優先判定を検証する。

MR-1（Phase 0）: 本文の「市販薬 / おすすめ / 記録」を kind より先にスキャンしていた
旧実装が、正しい concierge_* / store_locator / aggressive_input を Physical/SessionOps へ
誤判定し REVIEW を量産していた回帰を防ぐ。
"""
from __future__ import annotations

import importlib
import sys

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_runner = importlib.import_module("scripts.local_v2_chat_test_runner")
_kind_route = _runner._kind_route


def test_concierge_kinds_route_to_concierge():
    assert _kind_route("concierge_greeting", "") == "Concierge"
    assert _kind_route("concierge_architecture", "") == "Concierge"
    assert _kind_route("concierge_capabilities", "") == "Concierge"
    assert _kind_route("concierge_redirect", "") == "Concierge"


def test_security_kinds_route_to_security():
    assert _kind_route("aggressive_input", "") == "Security"
    assert _kind_route("known_attack", "") == "Security"


def test_store_kinds_route_to_store():
    assert _kind_route("store_locator", "") == "Store"
    assert _kind_route("store_facilities", "") == "Store"
    assert _kind_route("store_inventory", "") == "Store"


def test_session_ops_kinds():
    assert _kind_route("session_integrated_status", "") == "SessionOps"
    assert _kind_route("session_summary", "") == "SessionOps"
    assert _kind_route("memory_delete_confirm", "") == "SessionOps"


def test_emergency_and_counseling():
    assert _kind_route("emergency_medical_self", "") == "Emergency"
    assert _kind_route("crisis_support", "") == "Emergency"
    assert _kind_route("counseling_initial", "") == "Counseling"


def test_physical_kinds():
    assert _kind_route("sage_reco", "") == "Physical"
    assert _kind_route("no_recommendation", "") == "Physical"
    assert _kind_route("pediatric_age_required", "") == "Physical"


def test_kind_priority_over_body_content_regression():
    """核心バグ: concierge 応答本文に「市販薬」が含まれても Concierge を維持する。"""
    body = "こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなどお話しできます。"
    assert _kind_route("concierge_greeting", body) == "Concierge"
    # aggressive_input が「市販薬のご相談」を含んでも Security
    assert _kind_route("aggressive_input", "市販薬のご相談があればお書きください。") == "Security"
    # store_facilities が「市販薬（OTC）の購入場所」を含んでも Store
    assert _kind_route("store_facilities", "市販薬（OTC）の購入場所についてご案内します。") == "Store"


def test_empty_kind_medicine_advice_falls_back_to_physical():
    """kind=None でも医薬品助言本文（便秘/目のかゆみ等）は Physical にフォールバック。"""
    constipation = (
        "便秘でつらいですね。すぐに出したい時はグリセリン浣腸A10が使いやすいです。"
        "何日も出ない時は受診してください。"
    )
    assert _kind_route("", constipation) == "Physical"
    assert _kind_route(None, "リビメックスコーワクリームは外用薬です。目やにが強い時は受診を。") == "Physical"


def test_empty_kind_market_keyword():
    assert _kind_route("", "市販薬をおすすめします。") == "Physical"
    assert _kind_route("", "ステータスを表示します。") == "SessionOps"


def test_empty_kind_no_signal_is_unknown():
    assert _kind_route("", "こんにちは。") == "unknown"
