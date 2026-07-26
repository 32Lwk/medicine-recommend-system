"""
競技・ドーピング文脈と推奨履歴に基づくルーティング判定。

- followup_qa: 直近推奨への追質問（競技可否・どれを選ぶか等）
- cold_start_recommend: 初回で症状＋競技/薬探索 → 推奨フロー
- symptom_prompt: 初回で競技のみ・症状なし → 症状確認
- none: 通常ルーティングへ委譲
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from src.services.medicine_discovery_routing import (
    has_medicine_discovery_intent,
    has_sports_medicine_context,
    session_has_recommended_medicines,
    session_is_medical_cold_start,
    should_route_medicine_discovery_to_recommendation,
)

logger = logging.getLogger(__name__)

MedicineContextRoute = Literal[
    "followup_qa",
    "cold_start_recommend",
    "symptom_prompt",
    "cold_symptom_chip_prompt",
    "none",
]

_SYMPTOM_HINTS = (
    "痛", "熱", "咳", "鼻水", "頭痛", "風邪", "のど", "喉", "発熱",
    "だる", "寒気", "くしゃみ", "鼻づま", "咽", "鼻みず", "痰", "息苦",
    "めまい", "吐", "下痢", "便秘", "痒", "かゆ",
)

_POST_RECO_MARKERS = (
    "どれ",
    "どちら",
    "先ほど",
    "さっき",
    "この薬",
    "推奨された",
    "推奨の",
    "案内された",
    "案内の",
    "提示された",
    "さきほど",
)

_USAGE_QUESTION_KEYWORDS = (
    "使える",
    "飲める",
    "服用",
    "大丈夫",
    "ドーピング",
    "禁止",
    "陽性",
    "アンチドーピング",
)

_INFORMATIONAL_FOLLOWUP_KEYWORDS = (
    "副作用",
    "飲み方",
    "用法",
    "用量",
    "併用",
    "飲み合わせ",
    "相互作用",
    "ドーピング",
    "禁止物質",
    "陽性",
    "成分",
    "年齢",
    "写真",
    "パッケージ",
    "外観",
    "見せて",
)

_QUESTION_MARKERS = ("？", "?", "ですか", "でしょうか", "ますか", "教えて")


def is_informational_reco_followup(user_message: str) -> bool:
    msg = (user_message or "").strip()
    if not msg:
        return False
    if not any(k in msg for k in _INFORMATIONAL_FOLLOWUP_KEYWORDS):
        return False
    return any(q in msg for q in _QUESTION_MARKERS) or msg.endswith(("?", "？"))


def has_symptom_for_recommendation(user_message: str) -> bool:
    """推奨フローに進める程度の症状シグナルがあるか。"""
    msg = (user_message or "").strip()
    if not msg:
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal

        if has_explicit_symptom_signal(msg):
            return True
    except ImportError:
        pass
    return any(k in msg for k in _SYMPTOM_HINTS)


def is_post_reco_followup_reference(user_message: str) -> bool:
    """直近の推奨結果を指して聞いているか（ルールベース）。"""
    msg = (user_message or "").strip()
    if not msg:
        return False
    if any(m in msg for m in _POST_RECO_MARKERS):
        return True
    sports = has_sports_medicine_context(msg)
    usage = any(k in msg for k in _USAGE_QUESTION_KEYWORDS)
    question = any(q in msg for q in _QUESTION_MARKERS)
    if sports and usage and question:
        return True
    return False


def resolve_medicine_context_route_rule(
    session: object,
    sid: Optional[str],
    user_message: str,
) -> MedicineContextRoute:
    """決定論的ルート判定。曖昧時は none を返し LLM に委譲。"""
    msg = (user_message or "").strip()
    if not msg:
        return "none"

    has_reco = session_has_recommended_medicines(session, sid)
    cold = session_is_medical_cold_start(session, sid)
    sports = has_sports_medicine_context(msg)
    has_symptom = has_symptom_for_recommendation(msg)

    if has_reco:
        if is_post_reco_followup_reference(msg):
            return "followup_qa"
        if is_informational_reco_followup(msg):
            return "followup_qa"
        if sports and not has_medicine_discovery_intent(msg):
            return "followup_qa"
        if sports and has_symptom and not has_medicine_discovery_intent(msg):
            return "followup_qa"
        # 推奨後の「競技で使える風邪薬を教えて」→ 既存推奨を踏まえた Q&A
        if sports and has_medicine_discovery_intent(msg):
            return "followup_qa"

    if cold:
        try:
            from config.llm_flags import is_reco_cold_nlu_v2_enabled
            from src.core.recommendation.cold_symptom_expansion import should_prompt_cold_symptoms

            if is_reco_cold_nlu_v2_enabled() and should_prompt_cold_symptoms(msg):
                return "cold_symptom_chip_prompt"
        except ImportError:
            pass
        if sports and not has_symptom:
            if has_medicine_discovery_intent(msg) or any(
                k in msg for k in ("使える", "飲める", "薬", "市販")
            ):
                return "symptom_prompt"
        if has_symptom and (
            should_route_medicine_discovery_to_recommendation(
                session, sid, msg, triage_category="Ask"
            )
            or should_route_medicine_discovery_to_recommendation(
                session, sid, msg, triage_category="Physical"
            )
        ):
            return "cold_start_recommend"

    return "none"


def is_ambiguous_medicine_context(
    session: object,
    sid: Optional[str],
    user_message: str,
) -> bool:
    """ルールで確定できず LLM 判定が有用な境界ケース。"""
    if resolve_medicine_context_route_rule(session, sid, user_message) != "none":
        return False

    msg = (user_message or "").strip()
    if not msg:
        return False

    has_reco = session_has_recommended_medicines(session, sid)
    sports = has_sports_medicine_context(msg)
    question = any(q in msg for q in _QUESTION_MARKERS)
    discovery = has_medicine_discovery_intent(msg)
    has_symptom = has_symptom_for_recommendation(msg)

    if has_reco and (sports or discovery) and question:
        return True
    if sports and question and not has_symptom:
        return True
    if has_reco and question and any(k in msg for k in _USAGE_QUESTION_KEYWORDS):
        return True
    return False


def resolve_medicine_context_route(
    session: object,
    sid: Optional[str],
    user_message: str,
    *,
    client: object = None,
    triage_result: Optional[dict] = None,
) -> MedicineContextRoute:
    """ルール優先。曖昧時のみ LLM classifier を呼ぶ。"""
    rule_route = resolve_medicine_context_route_rule(session, sid, user_message)
    if rule_route != "none":
        return rule_route

    if not is_ambiguous_medicine_context(session, sid, user_message):
        return "none"

    if client is None:
        return "none"

    try:
        from src.services.medicine_context_classifier import classify_medicine_context_llm

        llm_route = classify_medicine_context_llm(
            user_message,
            session,
            sid,
            client=client,
            triage_result=triage_result,
        )
        if llm_route and llm_route != "none":
            logger.info(
                "medicine_context: LLM resolved route=%s sid=%s",
                llm_route,
                sid,
            )
            return llm_route
    except Exception:
        logger.debug("medicine_context LLM classifier skipped", exc_info=True)

    return "none"
