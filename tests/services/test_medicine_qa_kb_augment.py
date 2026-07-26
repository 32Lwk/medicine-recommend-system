"""Medicine QA — local provider で KB block がプロンプトに載ること。"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _local_medicine_rag(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")
    monkeypatch.setenv("COMPREHEND_MEDICAL_ENABLED", "0")


def test_augment_medicine_prompt_local_provider_injects_kb(monkeypatch):
    """Phase A: local でも augment が非空 KB block を返す（retrieve を mock）。"""
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "local")
    fake_result = {
        "chunks": ["ロキソプロフェンとワーファリンの併用に注意"],
        "source_uris": ["local/medicine/interactions/ロキソプロフェン-ワーファリン.md"],
    }
    from unittest.mock import patch

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
        return_value=fake_result,
    ):
        from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

        out = augment_medicine_prompt_with_kb(
            "ロキソニンとワーファリン併用",
            "base prompt body",
            recommended_medicines=[{"product_name": "ロキソニン"}],
        )
    assert "base prompt body" in out
    assert "医薬品ナレッジベース参照" in out
    assert "ロキソプロフェン" in out


def test_augment_local_does_not_require_bedrock_flag(monkeypatch):
    """MEDICINE_RAG_PROVIDER=local 時、bedrock フラグなしで retrieve が呼ばれる。"""
    from unittest.mock import patch

    calls = []

    def _fake_retrieve(*args, **kwargs):
        calls.append(kwargs)
        return {"chunks": ["chunk"], "source_uris": ["local/medicine/topics/x.md"]}

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
        side_effect=_fake_retrieve,
    ):
        from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

        out = augment_medicine_prompt_with_kb("用法", "BASE")
    assert calls
    assert "医薬品ナレッジベース参照" in out
