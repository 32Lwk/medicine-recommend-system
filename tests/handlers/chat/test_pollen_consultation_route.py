"""環境アレルギー相談入口のカウンセリングルート"""
from unittest.mock import MagicMock

from src.handlers.chat.chat_pollen_consultation_route import (
    build_allergy_entry_response,
    run_otc_allergy_consultation_entry,
)
from src.utils.user_attribute_registration import (
    register_user_attributes_from_message,
    try_early_attribute_registration_ui,
)


def test_build_allergy_entry_response_pollen():
    text = build_allergy_entry_response("花粉症です")
    assert "花粉でお困り" in text
    assert "鼻水" in text
    assert "市販薬の相談窓口" not in text


def test_pollen_entry_returns_counseling_not_reco():
    session = {"messages": [], "user_attributes": {"allergies": []}}
    client = MagicMock()
    mock_client = MagicMock()

    register_user_attributes_from_message(
        session,
        "sid1",
        "花粉症です",
        schedule_async_extraction=False,
    )
    try_early_attribute_registration_ui(
        session,
        "sid1",
        "花粉症です",
        save_to_db_fn=lambda *_a, **_k: None,
        get_session_from_db_fn=lambda _sid: {"session_id": "sid1", "messages": []},
    )

    body, status = run_otc_allergy_consultation_entry(
        session, client, "sid1", "花粉症です", mock_client
    )

    assert status == 200
    assert body["message_count"] >= 2
    assert session.get("counseling_mode", {}).get("active") is True
    notif_count = sum(1 for m in session["messages"] if m.get("user_info_notification"))
    assert notif_count == 1
    last = session["messages"][-1]
    assert last.get("counseling") or last.get("type") == "bot"
    content = (last.get("diagnosis") or {}).get("message") or ""
    assert "花粉でお困り" in content
    assert "市販薬の相談窓口" not in content
