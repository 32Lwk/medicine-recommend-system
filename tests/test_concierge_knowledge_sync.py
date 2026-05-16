"""Concierge ナレッジ SSOT の主要事実テスト"""
from src.content.concierge_knowledge import key_facts_for_sync_test, load_concierge_knowledge


def test_knowledge_loads():
    data = load_concierge_knowledge()
    assert data["app"]["name"]
    assert len(data["capabilities"]) >= 3
    assert len(data["agents"]) >= 5


def test_key_facts():
    facts = key_facts_for_sync_test()
    assert facts["otc_only"]
    assert facts["no_diagnosis"]
    assert facts["multilingual"]
