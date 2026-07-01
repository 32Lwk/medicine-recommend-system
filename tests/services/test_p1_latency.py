"""Phase 1 レイテンシ最適化の回帰テスト。

- sub1: トリアージ統合（フラグ ON=1 call / OFF=2 call, 既定 OFF で従来挙動）
- sub3: 低リスク高速モデルルーティング（get_explain_model / assess_explanation_risk）
- sub4: バッチ使用上の注意キャッシュキーの安定性
"""
from __future__ import annotations

import json
import sys

import pytest

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _FakeMsg:
    def __init__(self, content: str):
        self.message = type("M", (), {"content": content})()


class _FakeResp:
    def __init__(self, content: str):
        self.choices = [_FakeMsg(content)]


# ---------------------------------------------------------------------------
# sub3: fast-model routing
# ---------------------------------------------------------------------------

def test_assess_explanation_risk_low_and_high():
    from src.core.explanation_generator import assess_explanation_risk

    assert assess_explanation_risk({}, {}, []) is False
    assert assess_explanation_risk({"allergies": ["なし"]}, {}, []) is False

    assert assess_explanation_risk({"age": 10}, {}, []) is True
    assert assess_explanation_risk({"age": 70}, {}, []) is True
    assert assess_explanation_risk({"pregnant": True}, {}, []) is True
    assert assess_explanation_risk({"breastfeeding": True}, {}, []) is True
    assert assess_explanation_risk({"treatment_mention": True}, {}, []) is True
    assert assess_explanation_risk({"current_medications": ["ワルファリン"]}, {}, []) is True
    assert assess_explanation_risk({"allergies": ["ペニシリン"]}, {}, []) is True


def test_assess_explanation_risk_fever_and_medicine_flags():
    from src.core.explanation_generator import assess_explanation_risk

    assert assess_explanation_risk({}, {"symptoms": [{"name": "発熱"}]}, []) is True
    assert assess_explanation_risk({}, {}, [{"risk_warning": "注意"}]) is True
    assert assess_explanation_risk({}, {}, [{"doping_prohibited": "禁止物質あり"}]) is True
    assert assess_explanation_risk({}, {}, [{"product_name": "普通の薬"}]) is False


def test_get_explain_model_flag_off_returns_none(monkeypatch):
    monkeypatch.delenv("LATENCY_EXPLAIN_FAST_LOWRISK", raising=False)
    from config.llm_config import get_explain_model

    assert get_explain_model(False) is None
    assert get_explain_model(True) is None


def test_get_explain_model_flag_on_lowrisk_uses_fast(monkeypatch):
    monkeypatch.setenv("LATENCY_EXPLAIN_FAST_LOWRISK", "true")
    monkeypatch.delenv("OPENAI_MODEL_EXPLAIN_FAST", raising=False)
    from config.llm_config import get_explain_model

    # 低リスク → 高速モデル（mini 系）。高リスク → None（既定 explain 維持）
    assert get_explain_model(False)  # not None
    assert "mini" in get_explain_model(False)
    assert get_explain_model(True) is None


def test_get_explain_model_override(monkeypatch):
    monkeypatch.setenv("LATENCY_EXPLAIN_FAST_LOWRISK", "true")
    monkeypatch.setenv("OPENAI_MODEL_EXPLAIN_FAST", "gpt-custom-fast")
    from config.llm_config import get_explain_model

    assert get_explain_model(False) == "gpt-custom-fast"


# ---------------------------------------------------------------------------
# sub4: batch usage-notes cache key
# ---------------------------------------------------------------------------

def test_batch_notes_cache_key_stable_and_sensitive():
    from src.core.explanation_generator import _batch_notes_cache_key

    meds = [{"product_name": "A"}, {"product_name": "B"}]
    nlu = {"symptoms": [{"name": "頭痛"}]}
    k1 = _batch_notes_cache_key(meds, nlu, {"age": None})
    k2 = _batch_notes_cache_key(list(reversed(meds)), nlu, {"age": None})
    assert k1 == k2  # 医薬品順序に依存しない

    # 個別因子（年齢）が変わればキーも変わる（都度生成のため）
    k3 = _batch_notes_cache_key(meds, nlu, {"age": 10})
    assert k1 != k3


# ---------------------------------------------------------------------------
# sub1: triage single-call merge (call-count equivalence)
# ---------------------------------------------------------------------------

def _patch_triage_fast_paths(monkeypatch):
    import src.services.llm_triage as t
    import src.services.medical_examination_request as mer
    import src.services.concierge_intent as ci
    import src.services.budget_guard as bg

    monkeypatch.setattr(t, "detect_illegal_or_controlled_drug", lambda *_a, **_k: None)
    monkeypatch.setattr(t, "_session_admin_fast_path", lambda *_a, **_k: None)
    monkeypatch.setattr(t, "_concierge_fast_path_hint", lambda *_a, **_k: None)
    monkeypatch.setattr(mer, "detect_medical_examination_request_exact", lambda *_a, **_k: False)
    monkeypatch.setattr(ci, "looks_like_service_identity_question", lambda *_a, **_k: False)
    monkeypatch.setattr(bg, "check_llm_allowed", lambda *_a, **_k: (True, ""))


def test_triage_single_call_flag_on_makes_one_call(monkeypatch):
    monkeypatch.setenv("LATENCY_TRIAGE_SINGLE_CALL", "true")
    _patch_triage_fast_paths(monkeypatch)

    calls: list[str] = []
    import src.core.llm_client as llm_client

    def _fake(client, *, model_role, path, messages, model=None, **kw):
        calls.append(path)
        return _FakeResp(json.dumps({
            "category": "Other",
            "confidence": 0.9,
            "subcategory": "store_inquiry/inventory",
            "requires_immediate_action": False,
            "reasoning": "combined",
        }))

    monkeypatch.setattr(llm_client, "chat_completion_create", _fake)

    from src.services.llm_triage import llm_triage

    result = llm_triage("在庫はありますか", client=object(), use_cache=False)
    assert len(calls) == 1
    assert calls[0] == "llm_triage.combined"
    assert result["subcategory"] == "store_inquiry/inventory"


def test_triage_two_stage_flag_off_makes_two_calls(monkeypatch):
    monkeypatch.setenv("LATENCY_TRIAGE_SINGLE_CALL", "false")
    _patch_triage_fast_paths(monkeypatch)

    calls: list[str] = []
    import src.core.llm_client as llm_client

    def _fake(client, *, model_role, path, messages, model=None, **kw):
        calls.append(path)
        if path == "llm_triage.stage1":
            return _FakeResp(json.dumps({
                "category": "Other",
                "confidence": 0.6,
                "subcategory": "general_other",
                "requires_immediate_action": False,
                "reasoning": "stage1",
            }))
        return _FakeResp(json.dumps({
            "subcategory": "store_inquiry/inventory",
            "confidence": 0.8,
            "reasoning": "stage2",
        }))

    monkeypatch.setattr(llm_client, "chat_completion_create", _fake)

    from src.services.llm_triage import llm_triage

    result = llm_triage("在庫はありますか", client=object(), use_cache=False)
    assert calls == ["llm_triage.stage1", "llm_triage.stage2"]
    assert result["subcategory"] == "store_inquiry/inventory"
