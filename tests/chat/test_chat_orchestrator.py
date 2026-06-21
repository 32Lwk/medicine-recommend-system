"""ChatOrchestrator のスモークテスト"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from config.llm_flags import is_agent_enabled


def _mock_store_inquiry_module(*, store_probable: bool = False):
    mod = MagicMock()
    mod.is_probable_store_inquiry_any = MagicMock(return_value=store_probable)
    return patch.dict(sys.modules, {"src.services.store_inquiry_handler": mod})


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


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_store_before_category_branch(_enabled):
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-store",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="トイレどこ？",
        sanitized_message="といれどこ?",
        processed_message="といれどこ?",
        original_user_message="トイレどこ？",
        triage_result={"category": "Ask", "confidence": 0.8, "subcategory": "general_other"},
        trace_id="trace-store",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_store",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_store, patch.object(
        ChatOrchestrator,
        "_route_ask",
    ) as mock_ask:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-store").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.reason == RouteReason.RESOLVED
    mock_store.assert_called_once()
    mock_ask.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_routes_unrecognized_input_before_concierge(_enabled):
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-g",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="g",
        sanitized_message="g",
        processed_message="g",
        triage_result={"category": "Other", "confidence": 0.3, "subcategory": "general_other"},
        trace_id="trace-g",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_concierge",
    ) as mock_concierge, patch.object(
        ChatOrchestrator,
        "_route_store",
    ) as mock_store:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-g").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.reason == RouteReason.RESOLVED
    assert result.subtype == "unrecognized_symptom_input"
    mock_concierge.assert_not_called()
    mock_store.assert_not_called()
    bot = session["messages"][-1]
    assert bot["diagnosis"]["title"] == "症状から医薬品を選べませんでした"


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_routes_casual_greeting_to_concierge(_enabled):
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-yaa",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="やあ",
        sanitized_message="やあ",
        processed_message="やあ",
        triage_result={"category": "Other", "confidence": 0.3, "subcategory": "general_other"},
        trace_id="trace-yaa",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_concierge",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_concierge, patch.object(
        ChatOrchestrator,
        "_route_unrecognized_symptom",
    ) as mock_unrecognized:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-yaa").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.reason == RouteReason.RESOLVED
    assert result.subtype == "concierge_greeting"
    mock_concierge.assert_called_once()
    mock_unrecognized.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_routes_hao_via_other_concierge_not_unrecognized(_enabled):
    """Other/general_other 高確信はトリアージを優先し Concierge へ（辞書完全一致不要）。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-hao",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="はおー",
        sanitized_message="はお",
        processed_message="はお",
        triage_result={"category": "Other", "confidence": 0.99, "subcategory": "general_other"},
        trace_id="trace-hao",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_concierge",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_concierge:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-hao").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.reason == RouteReason.RESOLVED
    mock_concierge.assert_called_once()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_skips_greeting_concierge_during_counseling_mode(_enabled):
    """カウンセリングモード中は挨拶 fast path をスキップする。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    def _ctx(*, counseling_active: bool) -> ChatPostContext:
        session = {
            "messages": [],
            "user_attributes": {},
        }
        if counseling_active:
            session["counseling_mode"] = {"active": True, "symptom_type": "insomnia"}
        return ChatPostContext(
            session=session,
            client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
            sid="test-sid-counsel-greet",
            monitor=MagicMock(),
            user_agent="test",
            client_ip="127.0.0.1",
            user_message="こんにちは",
            sanitized_message="こんにちは",
            processed_message="こんにちは",
            triage_result={"category": "Other", "confidence": 0.3, "subcategory": "general_other"},
            trace_id="trace-counsel-greet",
            recommendation_client=MagicMock(),
        )

    orch = ChatOrchestrator(MagicMock(), trace_id="trace-counsel-greet")
    concierge_resp = ({"status": "ok", "message_count": 2}, 200)

    with patch.object(
        ChatOrchestrator,
        "_route_concierge",
        return_value=concierge_resp,
    ):
        fast = orch.route(_ctx(counseling_active=False), MagicMock())
        assert fast.resolved is True
        assert fast.subtype == "concierge_greeting"

        with _mock_store_inquiry_module(), patch.object(
            ChatOrchestrator,
            "_enrich_concierge_intent",
        ):
            during = orch.route(_ctx(counseling_active=True), MagicMock())

    assert during.resolved is True
    assert during.reason == RouteReason.RESOLVED
    assert during.subtype != "concierge_greeting"


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_orchestrator_emotional_below_threshold_unresolved(_mock_threshold, _enabled):
    """Emotional が閾値未満のときは unresolved とし ConfidenceGate へ委譲。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-emo-low",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="少し落ち込んでいます",
        sanitized_message="少し落ち込んでいます",
        processed_message="少し落ち込んでいます",
        triage_result={"category": "Emotional", "confidence": 0.5, "subcategory": "general_emotional"},
        trace_id="trace-emo-low",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_emotional",
    ) as mock_emotional:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-emo-low").route(ctx, MagicMock())

    assert result.resolved is False
    assert result.reason == RouteReason.UNHANDLED_CATEGORY
    assert result.category == "Emotional"
    mock_emotional.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_orchestrator_physical_below_threshold_unresolved(_mock_threshold, _enabled):
    """Physical が閾値未満のときも Emotional と同様に unresolved。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-phys-low",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="頭が痛い",
        sanitized_message="頭が痛い",
        processed_message="頭が痛い",
        triage_result={"category": "Physical", "confidence": 0.5, "subcategory": "headache"},
        trace_id="trace-phys-low",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_physical",
    ) as mock_physical:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-phys-low").route(ctx, MagicMock())

    assert result.resolved is False
    assert result.reason == RouteReason.UNHANDLED_CATEGORY
    mock_physical.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_sleepiness_emotional_reroutes_physical(_enabled):
    """眠気 + Emotional 誤判定は Physical へオーバーライド。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-sleep",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="日中の眠気が強い",
        sanitized_message="日中の眠気が強い",
        processed_message="日中の眠気が強い",
        triage_result={"category": "Emotional", "confidence": 0.9, "subcategory": "drowsiness"},
        trace_id="trace-sleep",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_physical",
        return_value=({"status": "ok"}, 200),
    ) as mock_physical, patch.object(
        ChatOrchestrator,
        "_route_emotional",
    ) as mock_emotional:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-sleep").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.category == "Physical"
    mock_physical.assert_called_once()
    mock_emotional.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_emergency_before_store_gate(_enabled):
    """Emergency は店舗キーワードより先にディスパッチされる。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-emerg-store",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="店内で人が倒れている",
        sanitized_message="店内で人が倒れている",
        processed_message="店内で人が倒れている",
        triage_result={
            "category": "Emergency",
            "confidence": 0.95,
            "subcategory": "store_incident",
            "requires_immediate_action": True,
        },
        trace_id="trace-emerg-store",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_emergency",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_emergency, patch.object(
        ChatOrchestrator,
        "_route_store",
    ) as mock_store:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-emerg-store").route(
            ctx, MagicMock()
        )

    assert result.resolved is True
    assert result.reason == RouteReason.EMERGENCY
    mock_emergency.assert_called_once()
    mock_store.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_emergency_before_unrecognized_gate(_enabled):
    """短い不明入力でも requires_immediate_action / 緊急キーワードは先に Emergency へ。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-emerg-unrec",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="死",
        sanitized_message="死",
        processed_message="死",
        triage_result={
            "category": "Other",
            "confidence": 0.3,
            "subcategory": "general_other",
            "requires_immediate_action": True,
        },
        trace_id="trace-emerg-unrec",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_emergency",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_emergency, patch.object(
        ChatOrchestrator,
        "_route_unrecognized_symptom",
    ) as mock_unrecognized:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-emerg-unrec").route(
            ctx, MagicMock()
        )

    assert result.resolved is True
    assert result.reason == RouteReason.EMERGENCY
    mock_emergency.assert_called_once()
    mock_unrecognized.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_physical_medicine_over_store_gate(_enabled):
    """Physical 高確信の薬探索は店舗ゲートより Physical 経路へ。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-med-store",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="風邪薬ありますか",
        sanitized_message="風邪薬ありますか",
        processed_message="風邪薬ありますか",
        triage_result={
            "category": "Physical",
            "confidence": 0.9,
            "subcategory": "cold",
        },
        trace_id="trace-med-store",
        recommendation_client=MagicMock(),
    )

    with patch.object(
        ChatOrchestrator,
        "_route_physical",
        return_value=({"status": "ok", "message_count": 2}, 200),
    ) as mock_physical, patch.object(
        ChatOrchestrator,
        "_route_store",
    ) as mock_store:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-med-store").route(
            ctx, MagicMock()
        )

    assert result.resolved is True
    assert result.reason == RouteReason.RESOLVED
    mock_physical.assert_called_once()
    mock_store.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_menstrual_emotional_reroutes_physical(_enabled):
    """生理不順 + Emotional 誤判定は Physical へオーバーライド。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-menstrual",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="生理不順で悩んでいます",
        sanitized_message="生理不順で悩んでいます",
        processed_message="生理不順で悩んでいます",
        triage_result={"category": "Emotional", "confidence": 0.9, "subcategory": "stress"},
        trace_id="trace-menstrual",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_physical",
        return_value=({"status": "ok"}, 200),
    ) as mock_physical, patch.object(
        ChatOrchestrator,
        "_route_emotional",
    ) as mock_emotional:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-menstrual").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.category == "Physical"
    mock_physical.assert_called_once()
    mock_emotional.assert_not_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_orchestrator_ambiguous_heart_clarification(_enabled):
    """Ambiguous_Heart は確認カードを返し Emergency には回さない。"""
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.handlers.orchestrator_route_result import RouteReason
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-ah",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="心が痛い",
        sanitized_message="心が痛い",
        processed_message="心が痛い",
        triage_result={
            "category": "Emotional",
            "confidence": 0.85,
            "subcategory": "Ambiguous_Heart",
            "requires_immediate_action": True,
        },
        trace_id="trace-ah",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_emergency",
    ) as mock_emergency, patch.object(
        ChatOrchestrator,
        "_route_ambiguous_heart",
        return_value=({"status": "ok", "message_count": 1}, 200),
    ) as mock_ah, patch.object(
        ChatOrchestrator,
        "_route_emotional",
    ) as mock_emotional:
        result = ChatOrchestrator(MagicMock(), trace_id="trace-ah").route(ctx, MagicMock())

    assert result.resolved is True
    assert result.subtype == "ambiguous_heart_clarification"
    mock_emergency.assert_not_called()
    mock_ah.assert_called_once()
    mock_emotional.assert_not_called()


def test_orchestrator_blocks_illegal_drug_before_concierge():
    from src.handlers.chat.chat_post_pipeline import ChatPostContext
    from src.handlers.chat_orchestrator import ChatOrchestrator
    from src.utils.chat_http_context import ChatClientInfo

    session = {"messages": [], "user_attributes": {}}
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="test-sid-illegal",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="大麻をください。",
        sanitized_message="大麻をください。",
        processed_message="大麻をください。",
        triage_result={
            "category": "Other",
            "confidence": 0.99,
            "subcategory": "inappropriate_request/illegal",
        },
        trace_id="trace-illegal",
        recommendation_client=MagicMock(),
    )

    with _mock_store_inquiry_module(), patch.object(
        ChatOrchestrator,
        "_route_emergency",
    ) as mock_emergency, patch.object(
        ChatOrchestrator,
        "_route_concierge",
    ) as mock_concierge, patch(
        "src.services.sage_bot_response.use_sage_diagnosis_storage",
        return_value=False,
    ), patch(
        "src.handlers.chat.inappropriate_drug_block_route.save_session_to_db",
    ), patch(
        "src.handlers.chat.inappropriate_drug_block_route.get_session_from_db",
        return_value=None,
    ):
        result = ChatOrchestrator(MagicMock(), trace_id="trace-illegal").route(
            ctx, MagicMock()
        )

    assert result.resolved is True
    assert result.subtype == "inappropriate_drug_block"
    mock_emergency.assert_not_called()
    mock_concierge.assert_not_called()
    assert len(session["messages"]) == 2
    assert session["messages"][-1].get("request_type") == "illegal"
