"""persist_session_from_chat_state の user_attributes マージ"""
from unittest.mock import MagicMock, patch

from src.services.session_manager import persist_session_from_chat_state


def test_persist_merges_db_allergies_with_session():
    session = MagicMock()
    session.get.side_effect = lambda k, default=None: {
        "messages": [{"type": "user", "content": "hi"}],
        "user_attributes": {"allergies": [], "medical_history": []},
    }.get(k, default)

    db_data = {
        "messages": [],
        "user_attributes": {
            "allergies": ["花粉"],
            "medical_history": ["花粉症"],
        },
    }

    saved = {}

    def fake_save(sid, data):
        saved.update(data)

    with patch("src.services.session_manager.get_session_from_db", return_value=db_data):
        with patch("src.services.session_manager.ensure_session_persisted") as ensure:
            persist_session_from_chat_state("sid1", session)
            payload = ensure.call_args[0][1]
            assert "花粉" in payload["user_attributes"]["allergies"]
            assert payload["user_attributes"].get("medical_history") == []
