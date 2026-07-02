"""Phase 2 (p2-counseling, Subtask A): counseling 文脈維持のルールベースガード。

「1ヶ月ほどです」「残業が続いています」等の期間・状況フォローアップが、
triage の Physical 誤判定によって no_recommendation 受診テンプレへ落ちる回帰
（counseling-ctx-03 相当）への対応を検証する。
"""
from __future__ import annotations

import sys

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.handlers.chat.chat_counseling_flow import (
    _looks_like_counseling_continuation,
    run_counseling_flow,
)


def _active_counseling_mode(with_question: bool = True) -> dict:
    mode = {
        "active": True,
        "symptom_type": "anxiety",
        "collected_info": {},
        "current_question_index": 0,
    }
    mode["question_history"] = (
        [{"question": "どんな場面やきっかけが多いですか？", "asked_at": "t0", "question_type": "initial"}]
        if with_question
        else []
    )
    return mode


# ---------------------------------------------------------------------------
# _looks_like_counseling_continuation（ルールベース判定単体）
# ---------------------------------------------------------------------------

def test_duration_followup_is_continuation():
    mode = _active_counseling_mode()
    assert _looks_like_counseling_continuation("1ヶ月ほどです", mode) is True


def test_situational_followup_is_continuation():
    mode = _active_counseling_mode()
    assert _looks_like_counseling_continuation("残業が続いています", mode) is True
    assert _looks_like_counseling_continuation("2週間くらいです", mode) is True


def test_explicit_physical_symptom_is_not_continuation():
    """明確な身体症状（頭痛・発熱等）はガード対象外＝Physicalへの切り替えを維持。"""
    mode = _active_counseling_mode()
    assert _looks_like_counseling_continuation("頭痛がします", mode) is False
    assert _looks_like_counseling_continuation("熱が38度あります", mode) is False
    assert _looks_like_counseling_continuation("背中が痛いです", mode) is False


def test_no_question_history_is_not_continuation():
    """まだ質問を1件も出していない段階は新規トピックの可能性が高いため対象外。"""
    mode = _active_counseling_mode(with_question=False)
    assert _looks_like_counseling_continuation("1ヶ月ほどです", mode) is False


def test_empty_text_is_not_continuation():
    mode = _active_counseling_mode()
    assert _looks_like_counseling_continuation("", mode) is False
    assert _looks_like_counseling_continuation(None, mode) is False


# ---------------------------------------------------------------------------
# run_counseling_flow: flag OFF/ON の分岐（counseling-ctx-03 Turn2 相当）
# ---------------------------------------------------------------------------

class _FakeSession(dict):
    """session.modified 属性を持つ dict（Flask セッション互換の最小モック）。"""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.modified = False


def test_flag_off_physical_triage_exits_counseling_as_before(monkeypatch):
    """flag OFF（既定）: 現状維持。triage=Physical で即座にカウンセリング終了。"""
    monkeypatch.delenv("UX_COUNSELING_CONTEXT_MAINTAIN", raising=False)
    session = _FakeSession(counseling_mode=_active_counseling_mode(), messages=[])
    triage_result = {"category": "Physical", "confidence": 0.6}

    response, out_triage = run_counseling_flow(
        session, None, "sid-1", "1ヶ月ほどです", "1ヶ月ほどです", triage_result, None
    )

    assert response is None
    assert session["counseling_mode"]["active"] is False


def test_flag_on_duration_followup_continues_counseling(monkeypatch):
    """flag ON: 期間フォローアップは counseling_mode.active を維持し、
    handle_user_input_in_counseling_mode 経由の処理へフォールスルーする。"""
    monkeypatch.setenv("UX_COUNSELING_CONTEXT_MAINTAIN", "true")
    session = _FakeSession(counseling_mode=_active_counseling_mode(), messages=[])
    triage_result = {"category": "Physical", "confidence": 0.6}

    calls = {}

    def _fake_handle(user_text, sess, client, session_id=None):
        calls["called_with"] = user_text
        return {
            "type": "counseling_response_with_question",
            "counseling_response": "1ヶ月ほど続いているのですね。",
            "question": "最近、眠りの質はいかがですか？",
        }

    monkeypatch.setattr(
        "src.services.counseling_response.handle_user_input_in_counseling_mode",
        _fake_handle,
    )

    response, out_triage = run_counseling_flow(
        session, None, "sid-2", "1ヶ月ほどです", "1ヶ月ほどです", triage_result, None
    )

    # counseling_mode は維持されたまま（早期終了していない）
    assert session["counseling_mode"]["active"] is True
    assert calls.get("called_with") == "1ヶ月ほどです"
    # カウンセリング応答として処理され、通常の Physical フローには委譲されない
    assert response is not None
    body, status = response
    assert status == 200
    # 追加されたメッセージが counseling 系であること（no_recommendation ではない）
    last_msg = session["messages"][-1]
    assert last_msg.get("counseling") is True


def test_flag_on_explicit_symptom_still_exits_counseling(monkeypatch):
    """flag ON でも、明確な身体症状（頭痛等）は従来どおり Physical へ切り替える（回帰）。"""
    monkeypatch.setenv("UX_COUNSELING_CONTEXT_MAINTAIN", "true")
    session = _FakeSession(counseling_mode=_active_counseling_mode(), messages=[])
    triage_result = {"category": "Physical", "confidence": 0.9}

    response, out_triage = run_counseling_flow(
        session, None, "sid-3", "頭痛がします", "頭痛がします", triage_result, None
    )

    assert response is None
    assert session["counseling_mode"]["active"] is False


def test_flag_on_no_pending_question_still_exits_counseling(monkeypatch):
    """flag ON でも、質問未提示（開始直後）の Physical 判定は従来どおり終了する。"""
    monkeypatch.setenv("UX_COUNSELING_CONTEXT_MAINTAIN", "true")
    session = _FakeSession(counseling_mode=_active_counseling_mode(with_question=False), messages=[])
    triage_result = {"category": "Physical", "confidence": 0.9}

    response, out_triage = run_counseling_flow(
        session, None, "sid-4", "1ヶ月ほどです", "1ヶ月ほどです", triage_result, None
    )

    assert response is None
    assert session["counseling_mode"]["active"] is False


def test_flag_on_emergency_category_unaffected(monkeypatch):
    """flag ON でも Emergency カテゴリの扱いには一切影響しない（安全維持）。"""
    monkeypatch.setenv("UX_COUNSELING_CONTEXT_MAINTAIN", "true")
    session = _FakeSession(counseling_mode=_active_counseling_mode(), messages=[])
    triage_result = {"category": "Emergency", "confidence": 0.95}

    def _fake_handle(user_text, sess, client, session_id=None):
        return {"type": "topic_shift", "new_category": "Emergency", "topic_shift_result": {}}

    monkeypatch.setattr(
        "src.services.counseling_response.handle_user_input_in_counseling_mode",
        _fake_handle,
    )

    response, out_triage = run_counseling_flow(
        session, None, "sid-5", "死にたい", "死にたい", triage_result, None
    )

    assert response is not None
    body, status = response
    assert status == 200
    assert session["messages"][-1].get("emergency") is True
