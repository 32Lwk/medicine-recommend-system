"""register_user_attributes_from_message の環境アレルギー即時登録"""
from src.utils.user_attribute_registration import (
    append_user_attribute_registration_notice,
    build_registration_notice_items,
    register_user_attributes_from_message,
    try_early_attribute_registration_ui,
)

def test_register_pollen_sync():
    session = {}
    updated, extracted = register_user_attributes_from_message(
        session,
        "sid-test",
        "花粉症です",
        schedule_async_extraction=False,
    )
    assert updated is True
    ua = session["user_attributes"]
    assert "花粉" in ua["allergies"]
    assert ua.get("medical_history") in ([], None) or "花粉症" not in (ua.get("medical_history") or [])


def test_build_registration_notice_items_new():
    items = build_registration_notice_items(
        {"allergies": ["花粉"]},
        {"allergies": ["花粉"]},
        was_updated=True,
    )
    assert items == ["アレルギー: 花粉"]


def test_build_registration_notice_items_already_registered():
    items = build_registration_notice_items(
        {"allergies": ["花粉"]},
        {"allergies": ["花粉"]},
        was_updated=False,
    )
    assert items == ["アレルギー: 花粉（既に登録済み）"]


def test_append_notice_after_register():
    session = {"messages": [{"type": "user", "content": "花粉症です"}]}
    register_user_attributes_from_message(
        session,
        "sid-test",
        "花粉症です",
        schedule_async_extraction=False,
    )
    assert append_user_attribute_registration_notice(session, "sid-test") is True
    assert len(session["messages"]) == 2
    assert session["messages"][1].get("user_info_notification") is True
    diag = session["messages"][1].get("diagnosis") or {}
    assert "花粉" in (diag.get("message") or "") or any(
        "花粉" in str(s) for s in (diag.get("sections") or [])
    )


def test_early_ui_persists_user_and_notice():
    session = {"messages": []}
    saved = {}

    def _save(sid, data):
        saved["data"] = data

    register_user_attributes_from_message(
        session,
        "sid-early",
        "花粉症です",
        schedule_async_extraction=False,
    )
    assert try_early_attribute_registration_ui(
        session,
        "sid-early",
        "花粉症です",
        save_to_db_fn=_save,
        get_session_from_db_fn=lambda _sid: {"session_id": "sid-early", "messages": []},
    )
    assert session.get("_user_attr_notice_appended") is True
    assert len(session["messages"]) == 2
    assert saved["data"]["user_attributes"]["allergies"] == ["花粉"]
