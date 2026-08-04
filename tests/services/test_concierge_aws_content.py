"""AWS ステージング向け GCP 除去のテスト。"""
from __future__ import annotations

import pytest

from src.services.concierge_aws_content import (
    filter_architecture_sections_for_aws,
    skip_gcp_technical_doc,
    strip_gcp_mentions,
)


def test_strip_gcp_mentions_noop_off_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_STAGING", raising=False)
    monkeypatch.delenv("PUBLIC_SITE_URL", raising=False)
    text = "GCP 本番は Cloud Run です。"
    assert strip_gcp_mentions(text) == text


def test_strip_gcp_mentions_on_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_STAGING", "1")
    text = (
        "AWS ステージングは ECS です。\n\n"
        "GCP 本番は Cloud Run です。\n\n"
        "Amazon Translate を利用します。"
    )
    out = strip_gcp_mentions(text)
    assert "GCP" not in out
    assert "Cloud Run" not in out
    assert "ECS" in out
    assert "Amazon Translate" in out


def test_skip_gcp_technical_doc_on_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_STAGING", "1")
    assert skip_gcp_technical_doc("01-cross-cloud-architecture.md") is True
    assert skip_gcp_technical_doc("04-data-security.md") is False


def test_filter_architecture_sections_for_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_STAGING", "1")
    sections = [
        {"title": "GCP 本番", "items": ["Cloud Run 上で動作"]},
        {"title": "AWS ステージング", "items": ["ECS で Translate"]},
    ]
    out = filter_architecture_sections_for_aws(sections)
    assert [s["title"] for s in out] == ["AWS ステージング"]
