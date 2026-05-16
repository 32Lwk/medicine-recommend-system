"""ChatOrchestrator のスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.llm_flags import is_agent_enabled


@pytest.fixture
def ctx():
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    return ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-orch",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="頭が痛い",
        sanitized_message="頭が痛い",
        processed_message="頭が痛い",
        triage_result={
            "category": "Physical",
            "confidence": 0.9,
            "subcategory": "headache",
        },
        trace_id="trace-test",
        recommendation_client=MagicMock(),
    )


@patch("src.handlers.chat_orchestrator.is_agent_enabled", return_value=True)
@patch("src.handlers.chat_orchestrator.ChatOrchestrator")
def test_try_orchestrator_route_delegates(mock_orch_cls, _enabled, ctx):
    from src.handlers.orchestrator_route_result import OrchestratorRouteResult, RouteReason

    mock_orch_cls.return_value.route.return_value = OrchestratorRouteResult(
        resolved=True,
        response=({"status": "ok", "message_count": 1}, 200),
        reason=RouteReason.RESOLVED,
    )
    from src.handlers.chat_orchestrator import try_orchestrator_route

    resp = try_orchestrator_route(ctx, MagicMock())
    assert resp is not None
    assert resp[0]["status"] == "ok"
    mock_orch_cls.return_value.route.assert_called_once()


@patch("src.handlers.chat_orchestrator.is_agent_enabled", return_value=False)
def test_try_orchestrator_disabled(_mock, ctx):
    from src.handlers.chat_orchestrator import try_orchestrator_route

    assert try_orchestrator_route(ctx, MagicMock()) is None
