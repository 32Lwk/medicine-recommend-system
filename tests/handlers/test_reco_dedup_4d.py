"""p3-correction-sessionops 4d: 推奨重複抑制 + 終了意図検出（UX_RECO_DEDUP）。"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.reco_dedup import (
    build_recommendation_closing_response,
    build_recommendation_summary_response,
    is_recommendation_end_intent,
    medicine_list_signature,
    try_reco_flow_entry_short_circuit,
    try_skip_duplicate_medicine_list,
)

_MEDS_A = [
    {"product_name": "イブA錠"},
    {"product_name": "ロキソニンS"},
    {"product_name": "バファリン"},
]
_MEDS_B = [
    {"product_name": "イブA錠"},
    {"product_name": "ロキソニンS"},
    {"product_name": "セデス"},
]


def _session_with_prior_reco(meds: list | None = None) -> dict:
    meds = meds if meds is not None else _MEDS_A
    return {
        "messages": [
            {"type": "user", "content": "頭痛がします"},
            {
                "type": "bot",
                "content": "sage_reco",
                "diagnosis": {
                    "render": "sage_reco",
                    "symptoms": ["頭痛"],
                    "recommended_medicines": meds,
                },
            },
        ],
    }


def test_medicine_list_signature_order_independent() -> None:
    sig1 = medicine_list_signature(_MEDS_A)
    sig2 = medicine_list_signature(list(reversed(_MEDS_A)))
    assert sig1 == sig2
    assert medicine_list_signature(_MEDS_B) != sig1


def test_end_intent_positive_and_negative() -> None:
    assert is_recommendation_end_intent("ありがとう、これで終わり")
    assert is_recommendation_end_intent("どうもありがとうございました")
    assert is_recommendation_end_intent("もう大丈夫です")
    assert not is_recommendation_end_intent("頭痛が続きます")
    assert not is_recommendation_end_intent("イブは飲んでも大丈夫ですか")
    assert not is_recommendation_end_intent("ありがとう、まだ頭痛いです")


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_flag_on_end_intent_no_sage_reco(_get, _save, monkeypatch) -> None:
    monkeypatch.setenv("UX_RECO_DEDUP", "true")
    session = _session_with_prior_reco()
    resp, code = try_reco_flow_entry_short_circuit(session, "sid-1", "ありがとう、これで終わり")
    assert code == 200
    assert resp is not None
    bot = session["messages"][-1]
    assert bot["diagnosis"]["render"] != "sage_reco"
    assert bot["diagnosis"].get("kind") == "recommendation_closing"


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_flag_on_duplicate_medicine_list_skips_reco(_get, _save, monkeypatch) -> None:
    monkeypatch.setenv("UX_RECO_DEDUP", "true")
    session = _session_with_prior_reco()
    early = try_skip_duplicate_medicine_list(
        session, "sid-1", _MEDS_A, user_message="頭痛がします"
    )
    assert early is not None
    bot = session["messages"][-1]
    assert bot["diagnosis"]["render"] != "sage_reco"
    assert bot["diagnosis"].get("kind") == "recommendation_summary"


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_flag_on_different_medicine_list_not_skipped(_get, _save, monkeypatch) -> None:
    monkeypatch.setenv("UX_RECO_DEDUP", "true")
    session = _session_with_prior_reco()
    assert try_skip_duplicate_medicine_list(
        session, "sid-1", _MEDS_B, user_message="頭痛がします"
    ) is None


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_flag_off_no_short_circuit(_get, _save, monkeypatch) -> None:
    monkeypatch.delenv("UX_RECO_DEDUP", raising=False)
    session = _session_with_prior_reco()
    assert try_reco_flow_entry_short_circuit(session, "sid-1", "ありがとう") is None
    assert try_skip_duplicate_medicine_list(
        session, "sid-1", _MEDS_A, user_message="頭痛"
    ) is None


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_closing_response_kind(_get, _save) -> None:
    session: dict = {"messages": []}
    _, code = build_recommendation_closing_response(session, "sid-1", user_message="終わり")
    assert code == 200
    diag = session["messages"][-1]["diagnosis"]
    assert diag.get("kind") == "recommendation_closing"
    assert diag.get("render") != "sage_reco"


@patch("src.handlers.chat.reco_dedup.save_session_to_db")
@patch("src.handlers.chat.reco_dedup.get_session_from_db", return_value=None)
def test_summary_response_mentions_prior_meds(_get, _save) -> None:
    session = _session_with_prior_reco()
    _, code = build_recommendation_summary_response(session, "sid-1", user_message="頭痛")
    assert code == 200
    diag = session["messages"][-1]["diagnosis"]
    message = diag.get("message") or session["messages"][-1].get("content") or ""
    assert "イブA錠" in message or "ロキソニンS" in message
    assert diag.get("kind") == "recommendation_summary"
