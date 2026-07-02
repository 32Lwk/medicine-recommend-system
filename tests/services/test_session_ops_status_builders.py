"""SessionOps 実データ用ステータスビルダーのテスト。"""
from src.services.status_diagnosis_builder import (
    build_session_history_overview,
    build_session_recorded_items_status,
)


def test_build_session_recorded_items_lists_attributes():
    diag = build_session_recorded_items_status(
        session_snapshot={
            "messages": [{"type": "user"}, {"type": "bot"}],
            "user_attributes": {"age": 40, "allergies": ["卵"]},
        },
        profile={},
    )
    assert diag.kind == "session_recorded_items"
    text = " ".join(item for sec in diag.sections for item in sec.items)
    assert "年齢: 登録あり" in text
    assert "アレルギー: 1件登録" in text
    assert "ユーザー 1件" in text


def test_build_session_history_overview_shows_recent_user_messages():
    diag = build_session_history_overview(
        session_snapshot={
            "messages": [
                {"type": "user", "content": "頭痛い"},
                {"type": "bot", "content": "ok"},
                {"type": "user", "content": "熱もあります"},
            ],
        },
    )
    assert diag.kind == "session_history_overview"
    text = " ".join(item for sec in diag.sections for item in sec.items)
    assert "あなたの発言: 2件" in text
    assert "頭痛い" in text


def test_build_session_history_overview_empty():
    diag = build_session_history_overview(session_snapshot={"messages": []})
    assert "まだ会話履歴はありません" in diag.message
