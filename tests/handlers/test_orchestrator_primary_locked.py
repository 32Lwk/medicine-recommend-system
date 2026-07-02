"""Phase 4b-3: PRIMARY ON 時 Orchestrator 二重分類スキップ。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_post_pipeline import ChatPostContext
from src.handlers.chat_orchestrator import ChatOrchestrator
from src.utils.chat_http_context import ChatClientInfo


def _ctx_other(*, session_extra: dict | None = None, triage_extra: dict | None = None):
    session = {"messages": [], "user_attributes": {}}
    if session_extra:
        session.update(session_extra)
    triage = {
        "category": "Other",
        "confidence": 0.88,
        "subcategory": "general_other",
        "concierge_intent": "architecture",
        "_intent_router_dispatch": True,
    }
    if triage_extra:
        triage.update(triage_extra)
    return ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="web:primary-lock",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="APIの仕組みを教えて",
        sanitized_message="APIの仕組みを教えて",
        processed_message="APIの仕組みを教えて",
        triage_result=triage,
        trace_id="trace-primary",
        recommendation_client=MagicMock(),
    )


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
def test_is_primary_router_decision_locked_true(_primary):
    ctx = _ctx_other(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "architecture",
            }
        }
    )
    orch = ChatOrchestrator(MagicMock())
    assert orch._is_primary_router_decision_locked(ctx) is True


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=False)
def test_is_primary_router_decision_locked_false_when_primary_off(_primary):
    ctx = _ctx_other(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "architecture",
            }
        }
    )
    orch = ChatOrchestrator(MagicMock())
    assert orch._is_primary_router_decision_locked(ctx) is False


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
def test_route_locked_router_decision_skips_enrich(_primary):
    ctx = _ctx_other(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "architecture",
            }
        }
    )
    orch = ChatOrchestrator(MagicMock(), trace_id="t1")
    with patch.object(orch, "_route_concierge", return_value=({"status": "ok"}, 200)) as mock_c:
        resp = orch._route_locked_router_decision(ctx, MagicMock())
    assert resp is not None
    mock_c.assert_called_once()
    assert ctx.triage_result["concierge_intent"] == "architecture"
    assert ctx.triage_result["concierge_intent_source"] == "router_primary_locked"


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
@patch("src.services.routing_context.evaluate_store_gate", return_value=False)
@patch("src.services.confidence_policy.should_defer_category_routing", return_value=False)
@patch("src.services.concierge_intent.classify_concierge_intent", return_value=None)
@patch("src.agents.triage_agent.resolve_handoff")
def test_route_other_branch_uses_locked_path(
    mock_handoff, _cls, _defer, _store, _primary
):
    mock_handoff.return_value = MagicMock(target="store", payload={})
    ctx = _ctx_other(
        session_extra={
            "_intent_router_dispatch": {
                "primary_route": "Concierge",
                "sub_route": "architecture",
            }
        }
    )
    orch = ChatOrchestrator(MagicMock(), trace_id="t2")
    with patch.object(orch, "_enrich_concierge_intent") as mock_enrich, patch.object(
        orch, "_route_locked_router_decision", return_value=({"status": "ok"}, 200)
    ) as mock_locked:
        result = orch.route(ctx, MagicMock())
    assert result.resolved is True
    mock_locked.assert_called_once()
    mock_enrich.assert_not_called()


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=False)
@patch("src.services.routing_context.evaluate_store_gate", return_value=False)
@patch("src.services.confidence_policy.should_defer_category_routing", return_value=False)
@patch("src.services.concierge_intent.classify_concierge_intent", return_value=None)
@patch("src.agents.triage_agent.resolve_handoff")
def test_route_other_branch_enriches_when_primary_off(
    mock_handoff, _cls, _defer, _store, _primary
):
    mock_handoff.return_value = MagicMock(target="store", payload={})
    ctx = _ctx_other()
    orch = ChatOrchestrator(MagicMock(), trace_id="t3")
    with patch.object(orch, "_enrich_concierge_intent") as mock_enrich, patch.object(
        orch, "_route_concierge", return_value=({"status": "ok"}, 200)
    ):
        orch.route(ctx, MagicMock())
    mock_enrich.assert_called_once()


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
def test_enrich_other_skips_meta_triage_when_primary_locked(_primary):
    from src.services.concierge_orchestrator import enrich_other_concierge_intent

    triage = {
        "category": "Other",
        "concierge_intent": "architecture",
        "_intent_router_dispatch": True,
    }
    with patch(
        "src.services.meta_triage.classify_meta_concierge_intent"
    ) as mock_meta:
        out = enrich_other_concierge_intent(
            triage,
            "APIの仕組みを教えて",
            MagicMock(),
            session_id="web:primary-lock",
        )
    mock_meta.assert_not_called()
    assert out["concierge_intent"] == "architecture"


@patch("config.llm_flags.is_intent_router_primary_enabled", return_value=True)
def test_enrich_resolves_general_other_without_meta_triage(_primary):
    from src.services.concierge_orchestrator import enrich_other_concierge_intent

    triage = {
        "category": "Other",
        "concierge_intent": "general_other",
        "_intent_router_dispatch": True,
    }
    with patch(
        "src.services.meta_triage.classify_meta_concierge_intent"
    ) as mock_meta, patch(
        "src.services.concierge_intent.classify_concierge_intent",
        return_value="redirect",
    ):
        out = enrich_other_concierge_intent(
            triage,
            "このさびすは何ができますか?",
            MagicMock(),
            session_id="web:primary-lock",
        )
    mock_meta.assert_not_called()
    assert out["concierge_intent"] == "redirect"
    assert out["concierge_intent_source"] == "router_primary_resolve"
