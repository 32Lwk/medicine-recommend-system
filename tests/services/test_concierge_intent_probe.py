"""Concierge meta probe 拡張テスト。"""
from __future__ import annotations

from src.services.concierge_intent import probe_meta_concierge_intent


def test_probe_sage_terrace() -> None:
    assert probe_meta_concierge_intent("Sage Terrace とは？") == "architecture"


def test_probe_rule_based_scoring() -> None:
    assert probe_meta_concierge_intent("ルールベースで薬はどう選ぶ？") == "architecture"


def test_probe_data_storage() -> None:
    assert probe_meta_concierge_intent("データはどこに保存される？") == "architecture"


def test_probe_codepipeline_not_line_account() -> None:
    assert probe_meta_concierge_intent("CodePipeline のデプロイフローを教えて") == "architecture"
