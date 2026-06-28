"""IntentRouter Stage B LLM テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.routing.intent_router import run_intent_router_llm
from src.dialogue.routing.intent_router_llm import (
    call_intent_router_llm,
    parse_llm_route_response,
    pick_best_route_decision,
)
from src.dialogue.routing.types import RouteDecision


def test_parse_llm_route_response_valid():
    raw = '{"primary_route":"Physical","sub_route":"rule_based_recommend","confidence":0.92,"reasoning":"症状"}'
    d = parse_llm_route_response(raw)
    assert d is not None
    assert d.primary_route == "Physical"
    assert d.resolved_by == "llm"
    assert d.confidence == 0.92


def test_parse_llm_route_response_invalid_primary():
    assert parse_llm_route_response('{"primary_route":"Banana","confidence":0.9}') is None


def test_pick_best_route_decision():
    low = RouteDecision(primary_route="Unknown", confidence=0.2, resolved_by="legacy")
    high = RouteDecision(primary_route="Physical", confidence=0.88, resolved_by="llm")
    assert pick_best_route_decision(low, high) == high


@patch("src.dialogue.routing.intent_router_llm.is_intent_router_llm_enabled", return_value=False)
def test_call_intent_router_llm_flag_off(_flag):
    assert call_intent_router_llm("頭痛い", {}, "line:U1", client=MagicMock()) is None


@patch("src.dialogue.routing.intent_router_llm.is_intent_router_llm_enabled", return_value=True)
@patch("src.core.llm_client.chat_completion_create")
def test_call_intent_router_llm_success(mock_create, _flag):
    mock_create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"primary_route":"Concierge","sub_route":"architecture","confidence":0.91,"reasoning":"tech"}'))]
    )
    d = call_intent_router_llm(
        "技術スタックは？",
        {"messages": []},
        "web:U1",
        client=MagicMock(),
    )
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "architecture"


@patch("src.dialogue.routing.intent_router_llm.call_intent_router_llm")
def test_run_intent_router_llm_prefers_llm_when_higher_conf(mock_llm):
    mock_llm.return_value = RouteDecision(
        primary_route="Concierge",
        sub_route="redirect",
        confidence=0.95,
        resolved_by="llm",
    )
    triage = {"category": "Other", "concierge_intent": "redirect", "confidence": 0.75}
    d = run_intent_router_llm(
        "プリンシプルオブプログラミングとは？",
        {},
        "web:U1",
        triage_result=triage,
        client=MagicMock(),
    )
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.confidence == 0.95


@patch("src.dialogue.routing.intent_router_llm.is_intent_router_llm_enabled", return_value=True)
@patch("src.core.llm_client.chat_completion_create")
@patch("src.dialogue.context_provider.build_context_bundle")
def test_call_intent_router_llm_uses_physical_agent_kind(mock_bundle, mock_create, _flag):
    mock_bundle.return_value = MagicMock(messages=[], memory_block="")
    mock_create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"primary_route":"Physical","sub_route":"rule_based_recommend","confidence":0.9}'
                )
            )
        ]
    )
    call_intent_router_llm(
        "頭痛い",
        {},
        "line:U1",
        triage_result={"category": "Physical", "confidence": 0.9},
        client=MagicMock(),
    )
    mock_bundle.assert_called_once_with({}, "line:U1", agent_kind="physical")


@patch("src.dialogue.routing.intent_router_llm.is_intent_router_llm_enabled", return_value=True)
@patch("src.core.llm_client.chat_completion_create")
@patch("src.dialogue.context_provider.build_context_bundle")
def test_call_intent_router_llm_includes_memory_block(mock_bundle, mock_create, _flag):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "頭痛い"}],
        memory_block="アレルギー: 花粉",
    )
    mock_create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"primary_route":"Physical","confidence":0.9}'
                )
            )
        ]
    )
    call_intent_router_llm("頭痛い", {}, "line:U1", client=MagicMock())
    user_prompt = mock_create.call_args.kwargs["messages"][1]["content"]
    assert "長期記憶" in user_prompt
    assert "花粉" in user_prompt


@patch("src.dialogue.routing.intent_router_llm.call_intent_router_llm", return_value=None)
def test_run_intent_router_llm_falls_back_to_triage(_mock_llm):
    triage = {"category": "Physical", "confidence": 0.88, "subcategory": "headache"}
    d = run_intent_router_llm("頭痛い", {}, "line:U1", triage_result=triage)
    assert d is not None
    assert d.primary_route == "Physical"
