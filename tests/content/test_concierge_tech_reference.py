"""Concierge 技術参照ローダ。"""
from __future__ import annotations

from src.content.concierge_tech_reference import (
    augment_architecture_reference,
    format_concierge_technical_reference_block,
    wants_technical_deep_dive,
)


def test_technical_reference_block_contains_cross_cloud():
    block = format_concierge_technical_reference_block()
    assert "GCP 本番" in block
    assert "AWS ステージング" in block
    assert "Cloudflare R2" in block
    assert "04-data-security.md" in block
    assert "07-observability-ops.md" in block


def test_wants_deep_dive_on_infra_question():
    assert wants_technical_deep_dive("AWS と GCP のデプロイ構成の違いを詳しく", None)


def test_wants_deep_dive_on_follow_up():
    history = [
        {"type": "user", "content": "インフラ構成は？"},
        {
            "type": "bot",
            "content": "sage_status",
            "concierge_intent": "architecture",
        },
    ]
    assert wants_technical_deep_dive("もっと詳しく", history)


def test_augment_architecture_includes_tech_docs():
    base = "【エージェント構成（参照）】\n- TriageAgent: 振り分け"
    out = augment_architecture_reference(
        base, deep=True, user_text="デプロイ commit を詳しく"
    )
    assert "技術ドキュメント参照" in out
    assert "CHANGELOG" in out or "開発履歴" in out
    assert "公開デプロイ情報" in out
