"""Concierge 技術 FAQ — SSOT 参照・深掘り判定の contract テスト。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.content.concierge_runtime_reference import (
    augment_with_runtime_reference,
    wants_runtime_reference,
)
from src.content.concierge_tech_reference import (
    augment_architecture_reference,
    wants_technical_deep_dive,
)
from src.services.concierge_intent import probe_meta_concierge_intent

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FAQ_YAML = FIXTURES / "concierge_technical_faq.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        pytest.skip("PyYAML required: pip install PyYAML")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def faq_doc() -> dict[str, Any]:
    return _load_yaml(FAQ_YAML)


def _scenario_ids(doc: dict[str, Any]) -> list[str]:
    return [s["id"] for s in doc["scenarios"]]


def _build_reference(message: str, *, deep: bool) -> str:
    base = "【エージェント構成（参照）】\n- TriageAgent: 振り分け"
    return augment_architecture_reference(base, deep=deep, user_text=message)


@pytest.mark.parametrize("scenario_id", _scenario_ids(_load_yaml(FAQ_YAML)))
def test_technical_faq_contract(faq_doc: dict[str, Any], scenario_id: str) -> None:
    scenario = next(s for s in faq_doc["scenarios"] if s["id"] == scenario_id)
    message = scenario["message"]
    history = scenario.get("history")

    if scenario.get("expect_deep_dive") is not None:
        assert wants_technical_deep_dive(message, history) is scenario["expect_deep_dive"]

    expected_intent = scenario.get("expected_intent")
    if expected_intent:
        meta = probe_meta_concierge_intent(message)
        assert meta == expected_intent, f"{scenario_id}: intent {meta!r} != {expected_intent!r}"

    if scenario.get("skip_reference"):
        return

    deep = bool(scenario.get("expect_deep_dive"))
    ref = _build_reference(message, deep=deep)

    for needle in scenario.get("reference_must_contain") or []:
        assert needle in ref, f"{scenario_id}: missing {needle!r} in reference"

    if scenario.get("expect_runtime_block"):
        assert wants_runtime_reference(message)
        assert "公開デプロイ情報" in ref
        runtime = ref.split("【公開デプロイ情報", 1)[-1]
        for pattern in faq_doc.get("reference_forbidden_patterns") or []:
            assert pattern not in runtime, (
                f"{scenario_id}: forbidden {pattern!r} in runtime block"
            )


def test_runtime_block_has_no_env_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_COMMIT", "abc123def456")
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://aws.medicine.yutok.dev")
    monkeypatch.setenv("AWS_STAGING", "1")
    block = augment_with_runtime_reference("", "今の commit は？", deep=False)
    assert "abc123" in block
    for forbidden in ("TRANSLATION_PROVIDER", "TTS_PROVIDER", "DATABASE_URL", "GIT_COMMIT"):
        assert forbidden not in block
