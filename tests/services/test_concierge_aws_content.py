"""Concierge architecture grounding rules（クロスクラウド共通）。"""
from __future__ import annotations

from src.services.concierge_aws_content import (
    architecture_grounding_rule,
    cross_cloud_grounding_rule,
)


def test_cross_cloud_grounding_rule_includes_gcp_and_aws() -> None:
    rule = cross_cloud_grounding_rule()
    assert "GCP 本番" in rule
    assert "AWS ステージング" in rule
    assert "触れない" not in rule


def test_architecture_grounding_rule_same_on_aws(monkeypatch) -> None:
    monkeypatch.setenv("AWS_STAGING", "1")
    rule = architecture_grounding_rule()
    assert "GCP 本番" in rule
    assert "AWS ステージング" in rule
