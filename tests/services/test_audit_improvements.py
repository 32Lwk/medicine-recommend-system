"""監査改善: ルーティング検証ゲート・商品インデックス・chat_worker"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.dedup_store_products import dedup_store_products
from src.services.chat_worker import resolve_chat_max_workers
from src.services.routing_validator import is_verify_routing_enabled, verify_routing_async
from src.services.store_product_index import index_stats


def test_verify_routing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VERIFY_ROUTING_LLM", raising=False)
    assert is_verify_routing_enabled() is False

    with patch("src.services.routing_validator.threading.Thread") as mock_thread:
        verify_routing_async(
            route_kind="triage",
            user_text="頭痛",
            decided_category="Physical",
            client=object(),
        )
    mock_thread.assert_not_called()


def test_verify_routing_enabled_with_env(monkeypatch):
    monkeypatch.setenv("VERIFY_ROUTING_LLM", "1")
    assert is_verify_routing_enabled() is True


def test_chat_worker_default_max_workers(monkeypatch):
    monkeypatch.delenv("CHAT_WORKER_MAX", raising=False)
    monkeypatch.delenv("CHAT_MAX_WORKERS", raising=False)
    monkeypatch.delenv("GUNICORN_WORKERS", raising=False)
    assert resolve_chat_max_workers() == 4


def test_store_products_dedup_dry_run_removes_zero():
    path = Path(__file__).resolve().parents[2] / "data" / "store_products.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    before = sum(
        len(sd.get("products", [])) + len(sd.get("brands", []))
        for cd in raw.values()
        for sd in cd.get("subcategories", {}).values()
    )
    deduped = dedup_store_products(raw)
    after = sum(
        len(sd.get("products", [])) + len(sd.get("brands", []))
        for cd in deduped.values()
        for sd in cd.get("subcategories", {}).values()
    )
    assert before == after


def test_resolve_concierge_intent_uses_store_gate_cache():
    from src.agents.concierge_agent import resolve_concierge_intent
    from src.services.routing_context import RoutingContext

    routing = RoutingContext(
        session_id="line:U1",
        user_text="こんにちは",
        sanitized_text="こんにちは",
        store_probable=True,
        store_gate_evaluated=True,
    )
    with patch("src.agents.concierge_agent.classify_concierge_intent", return_value="greeting"):
        assert (
            resolve_concierge_intent(
                "こんにちは",
                {},
                routing_ctx=routing,
            )
            is None
        )
