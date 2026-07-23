"""Concierge 出力サニタイズ・深掘り UI のテスト。"""
from __future__ import annotations

from src.services.concierge_output_sanitize import (
    append_symptom_consultation_boundary,
    concierge_source_hint,
    sanitize_concierge_meta_output,
)
from src.services.concierge_templates import structure_concierge_meta_display


def test_sanitize_strips_env_assignment():
    raw = "AWS では TRANSLATION_PROVIDER=translate が設定されています。"
    out = sanitize_concierge_meta_output(raw, intent="architecture")
    assert "TRANSLATION_PROVIDER=" not in out
    assert "translate" not in out or "Amazon Translate" in out or out == ""


def test_sanitize_strips_internal_paths():
    raw = "詳細は docs/concierge/technical/01-cross-cloud-architecture.md を参照。"
    out = sanitize_concierge_meta_output(raw, intent="architecture")
    assert "docs/concierge" not in out
    assert "公開ドキュメント" in out


def test_sanitize_strips_meta_phrases():
    raw = "環境変数を確認したところ、Amazon Translate を利用しています。"
    out = sanitize_concierge_meta_output(raw, intent="architecture")
    assert "環境変数" not in out
    assert "Amazon Translate" in out


def test_append_symptom_boundary_when_symptom_in_question():
    text = "GCP 本番は Cloud Run です。"
    out = append_symptom_consultation_boundary(text, "のどが痛い時のインフラ構成は？")
    assert "症状やお薬" in out


def test_append_symptom_boundary_skips_pure_infra():
    text = "GCP 本番は Cloud Run です。"
    out = append_symptom_consultation_boundary(text, "GCP と AWS の違いは？")
    assert out == text


def test_concierge_source_hints():
    assert concierge_source_hint("architecture", deep=True) == "参照: 公開技術ドキュメント"
    assert concierge_source_hint("doc_changelog") == "参照: 更新履歴"
    assert concierge_source_hint("architecture", deep=False) is None


def test_structure_architecture_deep_topic_sections():
    text = (
        "概要です。\n\n"
        "GCP 本番は Cloud Run で medicine.yutok.dev をホストしています。\n\n"
        "AWS ステージングは ECS で Translate と Polly を使います。\n\n"
        "CodePipeline が main push 毎にデプロイします。"
    )
    message, sections = structure_concierge_meta_display("architecture", text, deep=True)
    titles = [s["title"] for s in sections]
    assert "GCP 本番" in titles
    assert "AWS ステージング" in titles
    assert "デプロイ・CI/CD" in titles
    assert "概要です。" in message
