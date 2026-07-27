"""質問ルート — QA ゲートでオフトピックを Concierge へ"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_question_route import (
    _gate_medicine_qa_before_execute,
    handle_question_flow,
)
from src.services.routing_context import RoutingContext


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch.dict("os.environ", {"LLM_AGENT_ENABLED": "1"}, clear=False)
@patch("src.services.medicine_discovery_routing.session_is_medical_cold_start", return_value=False)
@patch(
    "src.handlers.chat.chat_question_route._should_route_medicine_discovery_to_recommendation",
    return_value=False,
)
@patch("src.handlers.chat.chat_question_route._execute_medicine_qa_flow")
def test_ask_triage_short_circuits_to_qa(mock_qa, _discovery, _cold, _agent):
    from src.handlers.chat.chat_question_route import QuestionFlowResult

    mock_qa.return_value = QuestionFlowResult(
        response=({"status": "ok", "message_count": 1}, 200),
        is_question=True,
    )
    routing = RoutingContext(
        session_id="s1",
        user_text="陸上競技でも使える風邪薬を教えてください。",
        sanitized_text="陸上競技でも使える風邪薬を教えてください。",
        triage_result={"category": "Ask", "confidence": 0.95},
    )
    session = {"last_triage_result": routing.triage_result}
    client = MagicMock(client_ip="127.0.0.1", user_agent="t")
    result = handle_question_flow(
        session,
        client,
        "s1",
        routing.user_text,
        routing.sanitized_text,
        routing.sanitized_text,
        MagicMock(),
        routing=routing,
    )
    assert result.response is not None
    mock_qa.assert_called_once()


@patch("src.handlers.chat.chat_concierge_route.try_concierge_response")
def test_gate_routes_gitlab_question_to_concierge(mock_concierge):
    mock_concierge.return_value = ({"status": "ok", "message_count": 2}, 200)
    session = {"last_triage_result": {"category": "Ask", "confidence": 0.9}}
    routing = RoutingContext(
        session_id="s1",
        user_text="GitlabとGithubの違いは？",
        sanitized_text="GitlabとGithubの違いは？",
        triage_result=session["last_triage_result"],
    )
    result = _gate_medicine_qa_before_execute(
        session,
        MagicMock(client_ip="127.0.0.1", user_agent="t"),
        "s1",
        "GitlabとGithubの違いは？",
        "GitlabとGithubの違いは？",
        MagicMock(),
        routing=routing,
    )
    assert result is not None
    assert result.response is not None
    mock_concierge.assert_called_once()
    triage_passed = mock_concierge.call_args[0][5]
    assert triage_passed.get("concierge_intent") == "architecture"
