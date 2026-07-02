"""Phase 3 (p3-concierge, 前半): 意図分類拡張 + APP_ENV 開示ゲート。

「APIの仕組みを教えて」(concierge-06) / 「SSEについて」/ 「rule_basedとは」(concierge-11) が
挨拶フォールバックに落ちる回帰への対応を検証する。
「医薬品推奨の仕組み」(concierge-10) は既存の LLM meta_triage 経路で元々正しく解決済み
（route_mismatch は Phase 0 で修正済みの _kind_route バグのみが原因）のため対象外。
フォローアップ文脈維持（MR-4）は対象外。
"""
from __future__ import annotations

import sys

import pytest

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.concierge_intent import probe_meta_concierge_intent


# ---------------------------------------------------------------------------
# probe_meta_concierge_intent: flag OFF（既定）= 現状維持
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "APIの仕組みを教えて",
        "SSEについて",
        "rule_basedとは",
    ],
)
def test_flag_off_new_technical_queries_not_detected(monkeypatch, text):
    """flag OFF: 新規パターンは無効。現状の挙動（未検出）を維持する。"""
    monkeypatch.delenv("ROUTING_CONCIERGE_INTENT", raising=False)
    assert probe_meta_concierge_intent(text) is None


# ---------------------------------------------------------------------------
# probe_meta_concierge_intent: flag ON = architecture として検出
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "APIの仕組みを教えて",
        "APIについて教えて",
        "SSEについて",
        "Server-Sent Eventsとは",
        "rule_basedとは",
        "rule_based の詳細",
    ],
)
def test_flag_on_new_technical_queries_detected_as_architecture(monkeypatch, text):
    monkeypatch.setenv("ROUTING_CONCIERGE_INTENT", "true")
    assert probe_meta_concierge_intent(text) == "architecture"


def test_flag_on_medicine_consultation_still_takes_precedence(monkeypatch):
    """医薬品相談文脈は flag ON でも technical probe より優先して None（安全維持）。"""
    monkeypatch.setenv("ROUTING_CONCIERGE_INTENT", "true")
    # "API" や "SSE" 等を含まない通常の症状相談は非対象（回帰確認）
    assert probe_meta_concierge_intent("頭痛がします") is None


# ---------------------------------------------------------------------------
# 既存パターンは無変更（回帰）
# ---------------------------------------------------------------------------

def test_existing_patterns_unaffected_by_flag(monkeypatch):
    monkeypatch.delenv("ROUTING_CONCIERGE_INTENT", raising=False)
    assert probe_meta_concierge_intent("Sage Terrace とは？") == "architecture"
    assert probe_meta_concierge_intent("ルールベースで薬はどう選ぶ？") == "architecture"
    assert probe_meta_concierge_intent("データはどこに保存される？") == "architecture"
    assert probe_meta_concierge_intent("インフラ構成を教えて") == "architecture"

    monkeypatch.setenv("ROUTING_CONCIERGE_INTENT", "true")
    assert probe_meta_concierge_intent("Sage Terrace とは？") == "architecture"
    assert probe_meta_concierge_intent("ルールベースで薬はどう選ぶ？") == "architecture"
    assert probe_meta_concierge_intent("データはどこに保存される？") == "architecture"
    assert probe_meta_concierge_intent("インフラ構成を教えて") == "architecture"


# ---------------------------------------------------------------------------
# APP_ENV 開示ゲート: get_technical_details / _meta_reference_block
# ---------------------------------------------------------------------------

def test_get_technical_details_returns_expected_keys():
    from src.content.concierge_knowledge import get_technical_details

    details = get_technical_details()
    assert "api_description" in details
    assert "sse_description" in details
    assert "rule_based_description" in details


def test_meta_reference_block_dev_with_flag_includes_technical_details(monkeypatch):
    monkeypatch.setenv("ROUTING_CONCIERGE_INTENT", "true")
    monkeypatch.setenv("APP_ENV", "development")
    from src.agents.concierge_agent import _meta_reference_block

    block = _meta_reference_block("architecture")
    assert "技術詳細" in block
    assert "SSE" in block or "Server-Sent" in block


def test_meta_reference_block_production_excludes_technical_details_even_with_flag(monkeypatch):
    """production は flag ON でも技術詳細を含めない（抽象化維持）。"""
    monkeypatch.setenv("ROUTING_CONCIERGE_INTENT", "true")
    monkeypatch.setenv("APP_ENV", "production")
    from src.agents.concierge_agent import _meta_reference_block

    block = _meta_reference_block("architecture")
    assert "技術詳細（開発環境限定" not in block


def test_meta_reference_block_dev_without_flag_excludes_technical_details(monkeypatch):
    """flag OFF は development でも技術詳細を追加しない（現状維持）。"""
    monkeypatch.delenv("ROUTING_CONCIERGE_INTENT", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    from src.agents.concierge_agent import _meta_reference_block

    block = _meta_reference_block("architecture")
    assert "技術詳細（開発環境限定" not in block


def test_meta_reference_block_still_includes_existing_tech_bullets_regardless(monkeypatch):
    """既存の tech_bullets（抽象コンテンツ）は flag/環境に関わらず維持される。"""
    monkeypatch.delenv("ROUTING_CONCIERGE_INTENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    from src.agents.concierge_agent import _meta_reference_block

    block = _meta_reference_block("architecture")
    assert "技術スタック" in block
