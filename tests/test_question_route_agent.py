"""質問ルート — エージェント ON + Ask トリアージ"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_question_route import handle_question_flow
from src.services.routing_context import RoutingContext


@patch.dict("os.environ", {"LLM_AGENT_ENABLED": "1"}, clear=False)
@patch("src.handlers.chat.chat_question_route._execute_medicine_qa_flow")
def test_ask_triage_short_circuits_to_qa(mock_qa):
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
