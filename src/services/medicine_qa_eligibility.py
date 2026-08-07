"""医薬品 Q&A 直行の適格性 — 文脈シグナル優先、曖昧時のみ LLM（meta_triage 再利用）。"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_THREAD_INVENTORY_FOLLOWUP_RE = re.compile(
    r"家に|うちに|うちにも|"
    r"(?:家|うち).{0,12}持って|"
    r"持って.{0,12}(?:家|うち)|"
    r"あるわ|あるね|あるよ|Sは|Sが|ついてい",
)


def _resolve_thread_inventory_medicine_qa(
    text: str,
    *,
    session: Any,
    sid: str | None,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> Optional[MedicineQaRouteDecision]:
    """家に/うちにも/S表記 — 医薬品スレッド継続を Concierge greeting より優先。"""
    try:
        from src.services.medicine_qa_routing import is_travel_import_context

        if is_travel_import_context(text or ""):
            return None
    except Exception:
        pass
    if not _THREAD_INVENTORY_FOLLOWUP_RE.search(text or ""):
        return None
    try:
        from src.services.medicine_thread_context import collect_active_medicine_products

        active = collect_active_medicine_products(
            session,
            sid=sid,
            messages=conversation_history,
            recommended_medicines=recommended_medicines,
        )
    except Exception:
        active = []
    if active:
        return MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            "rule_medicine_thread_inventory_early",
        )
    # active 抽出失敗時: 直前 bot が medicine_qa ならスレッド継続（greeting 誤判定防止）
    raw_msgs: list[dict[str, Any]] = []
    if conversation_history and isinstance(conversation_history[0], dict):
        if conversation_history[0].get("type") in ("user", "bot"):
            raw_msgs = list(conversation_history)
    if not raw_msgs and session is not None:
        raw_msgs = list((session.get("messages") if isinstance(session, dict) else []) or [])
    if not raw_msgs and sid:
        try:
            from src.services.session_manager import get_session_from_db

            raw_msgs = list((get_session_from_db(sid) or {}).get("messages") or [])
        except Exception:
            raw_msgs = []

    for msg in reversed(raw_msgs):
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("type") or msg.get("role") or "").lower()
        if role not in ("bot", "assistant"):
            continue
        diagnosis = msg.get("diagnosis") if isinstance(msg.get("diagnosis"), dict) else {}
        kind = str(diagnosis.get("kind") or "")
        content = str(msg.get("content") or "")
        if kind == "medicine_qa" or content in ("sage_qa", "sage_status"):
            return MedicineQaRouteDecision(
                MedicineQaRoute.MEDICINE_QA,
                "rule_medicine_thread_inventory_last_bot_qa",
            )
        break

    # expand_messages_for_llm 形式（role/content のみ）のフォールバック
    for turn in reversed(conversation_history or []):
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").lower()
        if role != "assistant":
            continue
        plain = str(turn.get("content") or "")
        try:
            from src.dialogue.routing.context_signals import extract_drug_entities

            if extract_drug_entities(plain):
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "rule_medicine_thread_inventory_last_bot_qa",
                )
        except Exception:
            pass
        break

    return None


def looks_like_medicine_thread_inventory_followup(
    text: str,
    *,
    session: Any = None,
    sid: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """家に/うちにも/S表記 — medicine_qa 継続シグナル（Concierge greeting 抑止用）。"""
    return _resolve_thread_inventory_medicine_qa(
        text,
        session=session,
        sid=sid,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ) is not None


_CONCIERGE_META_INTENTS = frozenset({
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "doc_changelog",
    "chitchat",
    "greeting",
    "thanks",
    "redirect",
    "session_ops",
})


class MedicineQaRoute(str, Enum):
    MEDICINE_QA = "medicine_qa"
    CONCIERGE = "concierge"
    PHYSICAL = "physical"
    DEFER = "defer"


@dataclass(frozen=True)
class MedicineQaRouteDecision:
    route: MedicineQaRoute
    source: str
    concierge_intent: Optional[str] = None


_FOCUS_LLM_SKIP_SOURCES = (
    "rule_medicine_thread",
    "rule_medicine_thread_inventory",
    "medicine_information_question",
    "medicine_context_followup",
    "intent_router_medicine_side_effect_qa",
    "intent_router_medicine_followup_qa",
    "intent_router_medicine_qa",
    "fast_medicine_signal",
    "medicine_context_short",
)


def should_skip_focus_llm_enrichment(decision: MedicineQaRouteDecision) -> bool:
    """ルート確定済みなら focus LLM 補完を省略（レイテンシ削減）。"""
    if decision.route in (MedicineQaRoute.CONCIERGE, MedicineQaRoute.PHYSICAL):
        return True
    if decision.route != MedicineQaRoute.MEDICINE_QA:
        return False
    src = decision.source or ""
    return any(src.startswith(prefix) or prefix in src for prefix in _FOCUS_LLM_SKIP_SOURCES)


def is_medicine_qa_eligibility_llm_enabled() -> bool:
    """
    MEDICINE_QA_ELIGIBILITY_LLM:
      unset / auto: OpenAI が利用可能なら ON（曖昧な質問形式のみ）
      1/true/on: 強制 ON
      0/false/off: 強制 OFF（probe / 文脈シグナルのみ）
    """
    val = os.getenv("MEDICINE_QA_ELIGIBILITY_LLM")
    if val is None or str(val).strip().lower() in ("", "auto"):
        try:
            from src.core.openai_client import client as openai_client

            return bool(openai_client)
        except Exception:
            return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _extract_recommended_medicines(
    session: Any,
    conversation_history: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    messages = conversation_history
    if messages is None:
        messages = (session.get("messages") if session else None) or []
    for msg in reversed(messages):
        if msg.get("type") != "bot":
            continue
        diagnosis = msg.get("diagnosis") or {}
        recs = diagnosis.get("recommended_medicines")
        if recs:
            return list(recs)
    return []


def _has_medicine_qa_fast_signals(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> bool:
    """
    医薬品 Q&A 直行の構造シグナル。
    個別キーワード列挙ではなく、既存の consultation / focus / entity / 文脈 gate を再利用する。
    """
    from src.services.medicine_qa_routing import (
        infer_medicine_qa_focuses,
        is_medicine_information_question,
        is_strict_medicine_side_effect_question,
        should_prioritize_physical_for_symptom,
    )
    from src.services.concierge_intent import _is_medicine_consultation, looks_like_inquiry
    from src.dialogue.routing.context_signals import extract_drug_entities

    t = (text or "").strip()
    if not t:
        return False

    if should_prioritize_physical_for_symptom(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return False

    if _is_medicine_consultation(t):
        return True

    focuses = infer_medicine_qa_focuses(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
        use_llm_enrichment=False,
    )
    if looks_like_inquiry(t) and focuses and focuses != ["general"]:
        return True

    if looks_like_inquiry(t) and is_medicine_information_question(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return True

    has_entity = bool(extract_drug_entities(t))
    has_reco = bool(recommended_medicines)
    has_history = bool(conversation_history)

    if has_entity or has_reco or has_history:
        if is_medicine_information_question(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True
        if is_strict_medicine_side_effect_question(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True

    if has_reco and any(
        kw in t for kw in ("それ", "この", "その", "あれ", "先ほど", "さっき", "1番", "2番")
    ):
        return True

    return False


_EXPLICIT_MEDICINE_FIRST_RE = re.compile(
    r"(まず|最初に|先に|優先して).{0,16}(薬|症状|市販|相談|頭痛|のど|痛|飲|副作用|推奨|体調)",
    re.I,
)
_EXPLICIT_META_FIRST_RE = re.compile(
    r"(まず|最初に|先に|優先して).{0,16}(技術|インフラ|構成|デプロイ|アプリ|"
    r"このチャット|AWS|GCP|GitHub|GitLab|仕組み|更新|CHANGELOG)",
    re.I,
)
_SYMPTOM_THEN_PIVOT_RE = re.compile(
    r"^(.+?)(?:だけど|けど|が、)(.+)$",
    re.I,
)
_PARALLEL_CLAUSE_RE = re.compile(r"(?:と、|と|、あと|それから|も教えて|も聞きたい)", re.I)
_SYSTEM_MECHANISM_RE = re.compile(
    r"(推奨|おすすめ).{0,12}(機能|仕組み|ロジック|方法|アルゴリズム)|"
    r"(ルールベース|rule[_\s-]?based).{0,16}(推奨|仕組み|機能|選)|"
    r"(機能|仕組み).{0,12}(AI|LLM|ルール|ベース)",
    re.I,
)


def _is_system_mechanism_question(text: str) -> bool:
    """市販薬の推奨機能・選び方の仕組みについてのメタ質問（薬の相談ではない）。"""
    return bool(_SYSTEM_MECHANISM_RE.search((text or "").strip()))


def _has_parallel_medicine_signal(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> bool:
    """複合発話内に医薬品・症状の並行トピックがあるか。"""
    from src.services.concierge_intent import _is_medicine_consultation
    from src.utils.input_helpers import has_explicit_symptom_signal

    t = (text or "").strip()
    if not t:
        return False
    if _is_system_mechanism_question(t):
        if _PARALLEL_CLAUSE_RE.search(t):
            lead = _PARALLEL_CLAUSE_RE.split(t, maxsplit=1)[0]
            if not (
                _is_medicine_consultation(lead)
                or has_explicit_symptom_signal(lead)
            ):
                return False
        else:
            return False
    if _is_medicine_consultation(t) or has_explicit_symptom_signal(t):
        return True
    if _has_medicine_qa_fast_signals(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return True

    pivot = _SYMPTOM_THEN_PIVOT_RE.match(t)
    if pivot and (
        has_explicit_symptom_signal(pivot.group(1))
        or _is_medicine_consultation(pivot.group(1))
    ):
        return True

    if _PARALLEL_CLAUSE_RE.search(t):
        lead = _PARALLEL_CLAUSE_RE.split(t, maxsplit=1)[0]
        if has_explicit_symptom_signal(lead) or _is_medicine_consultation(lead):
            return True
        if _has_medicine_qa_fast_signals(
            lead,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True

    return False


def _resolve_medicine_or_physical_route(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
    source: str,
) -> MedicineQaRouteDecision:
    from src.services.concierge_intent import looks_like_inquiry
    from src.utils.input_helpers import has_explicit_symptom_signal

    if _has_medicine_qa_fast_signals(
        text,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return MedicineQaRouteDecision(MedicineQaRoute.MEDICINE_QA, source)
    if has_explicit_symptom_signal(text) and not looks_like_inquiry(text):
        return MedicineQaRouteDecision(MedicineQaRoute.PHYSICAL, source)
    return MedicineQaRouteDecision(MedicineQaRoute.MEDICINE_QA, source)


def _resolve_compound_route_override(
    text: str,
    meta_intent: str,
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
    client: OpenAI | None,
) -> Optional[MedicineQaRouteDecision]:
    """
    医薬品/症状 + メタ（技術・構成等）が同一発話に含まれるとき、
    ユーザー明示の優先順位・文構造・会話文脈で medicine/physical を優先する。
    """
    from src.services.concierge_intent import looks_like_inquiry
    from src.utils.input_helpers import has_explicit_symptom_signal

    t = (text or "").strip()
    if not t or meta_intent not in _CONCIERGE_META_INTENTS:
        return None
    if not _has_parallel_medicine_signal(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return None

    if _EXPLICIT_META_FIRST_RE.search(t):
        return None

    if _EXPLICIT_MEDICINE_FIRST_RE.search(t):
        return _resolve_medicine_or_physical_route(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
            source="compound_medicine_first",
        )

    pivot = _SYMPTOM_THEN_PIVOT_RE.match(t)
    if pivot and has_explicit_symptom_signal(pivot.group(1)):
        return MedicineQaRouteDecision(
            MedicineQaRoute.PHYSICAL,
            "compound_symptom_pivot",
        )

    if recommended_medicines and re.search(
        r"副作用|推奨|薬|それ|この|その|1番|2番|先ほど",
        t,
    ):
        return MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            "compound_reco_context",
        )

    if _PARALLEL_CLAUSE_RE.search(t):
        lead = _PARALLEL_CLAUSE_RE.split(t, maxsplit=1)[0]
        if _has_parallel_medicine_signal(
            lead,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return _resolve_medicine_or_physical_route(
                t,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines,
                source="compound_medicine_lead_clause",
            )

    if client is not None and is_medicine_qa_eligibility_llm_enabled() and looks_like_inquiry(t):
        llm_intent = _llm_resolve_concierge_intent(
            t,
            client,
            conversation_history=conversation_history,
        )
        if llm_intent is None:
            return _resolve_after_meta_none(
                t,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines,
            )

    return None


def _resolve_after_meta_none(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> MedicineQaRouteDecision:
    """
    meta_triage が none（医薬品・症状・店舗は Concierge 管轄外）と判断した後のルート。
    一律 redirect せず、構造シグナルで medicine_qa / physical / defer を選ぶ。
    """
    from src.services.concierge_intent import looks_like_inquiry
    from src.utils.input_helpers import has_explicit_symptom_signal

    if _has_medicine_qa_fast_signals(
        text,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            "llm_meta_none_medicine",
        )
    if has_explicit_symptom_signal(text) and not looks_like_inquiry(text):
        return MedicineQaRouteDecision(
            MedicineQaRoute.PHYSICAL,
            "llm_meta_none_symptom",
        )
    return MedicineQaRouteDecision(
        MedicineQaRoute.DEFER,
        "llm_meta_none_defer",
    )


def _resolve_concierge_meta_intent(
    text: str,
    *,
    session: Any = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> Optional[str]:
    """probe / 確定分類 / 本人確認 / 会話フォローアップ（構造挨拶は除く）。"""
    from src.services.concierge_intent import (
        classify_concierge_intent,
        looks_like_conversational_request,
        looks_like_service_identity_question,
        probe_meta_concierge_intent,
        probe_session_admin_intent,
        _is_medicine_consultation,
    )
    from src.services.concierge_agent_history import (
        is_meta_follow_up_utterance,
        resolve_concierge_follow_up_intent,
        resolve_last_bot_message,
        resolve_prior_meta_intent,
    )

    t = (text or "").strip()
    if not t:
        return None

    if looks_like_service_identity_question(t):
        return "app_about"

    if looks_like_conversational_request(t) and not _is_medicine_consultation(t):
        return "chitchat"

    if probe_session_admin_intent(t):
        return "session_ops"

    from src.services.contact_channel_intent import (
        classify_contact_channel_question,
        contact_channel_to_concierge_intent,
    )

    channel = classify_contact_channel_question(t, history=conversation_history)
    if channel:
        mapped = contact_channel_to_concierge_intent(channel)
        if mapped:
            return mapped

    prior = resolve_prior_meta_intent(
        session=session,
        conversation_history=conversation_history,
    )
    last_bot = resolve_last_bot_message(conversation_history or [])

    if conversation_history and is_meta_follow_up_utterance(t):
        follow = resolve_concierge_follow_up_intent(t, prior, last_bot=last_bot)
        if follow:
            return follow

    fast = classify_concierge_intent(t)
    if fast in _CONCIERGE_META_INTENTS:
        return fast

    probed = probe_meta_concierge_intent(t, history=conversation_history)
    if probed:
        return probed

    return None


def _resolve_structural_ack_intent(
    text: str,
    *,
    session: Any = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> Optional[str]:
    """短い相槌・一声のみ。医薬品/症状/メタ質問の後段フォールバック。"""
    from src.services.concierge_intent import infer_structural_concierge_intent
    from src.services.concierge_agent_history import resolve_prior_meta_intent

    t = (text or "").strip()
    if not t:
        return None

    prior = resolve_prior_meta_intent(
        session=session,
        conversation_history=conversation_history,
    )
    structural = infer_structural_concierge_intent(
        t,
        prior_meta_intent=prior,
        conversation_history=conversation_history,
    )
    if structural in _CONCIERGE_META_INTENTS:
        return structural
    return None


def _resolve_concierge_from_triage(triage_result: dict[str, Any] | None) -> Optional[str]:
    if not triage_result:
        return None
    intent = triage_result.get("concierge_intent")
    if intent in _CONCIERGE_META_INTENTS:
        return str(intent)
    return None


def _llm_resolve_concierge_intent(
    text: str,
    client: OpenAI,
    *,
    conversation_history: list[dict[str, Any]] | None,
) -> Optional[str]:
    from src.services.meta_triage import classify_meta_concierge_intent

    intent = classify_meta_concierge_intent(
        text,
        client,
        conversation_history=conversation_history,
    )
    if intent in _CONCIERGE_META_INTENTS:
        return intent
    return None


def resolve_medicine_qa_route(
    text: str,
    *,
    session: Any = None,
    sid: str | None = None,
    triage_result: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    client: OpenAI | None = None,
) -> MedicineQaRouteDecision:
    """
    医薬品 Q&A に直行すべきか、Concierge / Physical へ回すかを判定する。

    優先順位:
    1. triage / 構造メタ / probe / フォローアップ → concierge
    2. 医薬品文脈シグナル → medicine_qa
    3. 明示的症状 → physical
    4. 情報要求形式で曖昧 → LLM（meta_triage 再利用）
    5. それ以外 → defer
    """
    from src.services.concierge_intent import looks_like_inquiry
    from src.utils.input_helpers import has_explicit_symptom_signal

    t = (text or "").strip()
    if not t:
        return MedicineQaRouteDecision(MedicineQaRoute.DEFER, "empty")

    from src.agents.session_agent import probe_session_admin_intent

    if probe_session_admin_intent(t):
        return MedicineQaRouteDecision(
            MedicineQaRoute.CONCIERGE,
            "session_ops_early",
            concierge_intent="session_ops",
        )

    from src.services.concierge_intent import (
        _is_medicine_consultation,
        looks_like_conversational_request,
        looks_like_reflective_health_chitchat,
    )

    if looks_like_reflective_health_chitchat(t):
        return MedicineQaRouteDecision(
            MedicineQaRoute.CONCIERGE,
            "reflective_health_chitchat",
            concierge_intent="chitchat",
        )

    inv_early = _resolve_thread_inventory_medicine_qa(
        t,
        session=session,
        sid=sid,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    )
    if inv_early:
        return inv_early

    if (
        looks_like_conversational_request(t)
        and not _is_medicine_consultation(t)
        and not has_explicit_symptom_signal(t)
    ):
        try:
            from src.services.medicine_thread_context import collect_active_medicine_products

            _early_active = collect_active_medicine_products(
                session,
                sid=sid,
                messages=conversation_history,
                recommended_medicines=recommended_medicines,
            )
        except Exception:
            _early_active = []
        if not _early_active and not recommended_medicines:
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "general_chitchat_no_product",
                concierge_intent="chitchat",
            )

    if re.search(r"飲み合わせ|併用|一緒に|他の薬", t):
        brand_in_text = bool(re.search(
            r"ロキソニン|バファリン|カロナール|タイレノール|イブ|セデス|パブロン",
            t,
            re.I,
        ))
        if not brand_in_text and not recommended_medicines:
            try:
                from src.services.medicine_thread_context import collect_active_medicine_products

                _amb_active = collect_active_medicine_products(
                    session,
                    sid=sid,
                    messages=conversation_history,
                )
            except Exception:
                _amb_active = []
            if not _amb_active:
                try:
                    from src.dialogue.sync_legacy import update_dialogue_turn_state

                    update_dialogue_turn_state(
                        session,
                        sid,
                        user_text=t,
                        user_goal="clarify",
                        pending_clarification="drug_name_for_interaction",
                    )
                except Exception:
                    logger.debug("clarify dialogue_state skipped", exc_info=True)
                return MedicineQaRouteDecision(
                    MedicineQaRoute.CONCIERGE,
                    "ambiguous_drug_clarify",
                    concierge_intent="chitchat",
                )

    from src.services.contact_channel_intent import (
        classify_contact_channel_question,
        contact_channel_to_concierge_intent,
    )

    channel = classify_contact_channel_question(t, history=conversation_history)
    if channel:
        mapped = contact_channel_to_concierge_intent(channel)
        if mapped:
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "contact_channel_context",
                concierge_intent=mapped,
            )

    recs = recommended_medicines
    if recs is None:
        recs = _extract_recommended_medicines(session, conversation_history)

    from src.services.medicine_thread_context import (
        _is_concierge_topic_pivot,
        collect_active_medicine_products,
        expand_messages_for_llm,
        should_continue_medicine_thread,
    )

    raw_messages = conversation_history or (session.get("messages") if session else None)
    llm_history = expand_messages_for_llm(raw_messages)

    triage_intent = _resolve_concierge_from_triage(triage_result)
    if triage_intent:
        return MedicineQaRouteDecision(
            MedicineQaRoute.CONCIERGE,
            "triage_concierge_intent",
            concierge_intent=triage_intent,
        )

    try:
        from src.services.medicine_qa_routing import is_travel_import_context
        from src.services.reco_followup_signals import is_travel_thread_followup

        if is_travel_import_context(t) or is_travel_thread_followup(
            t,
            conversation_history=llm_history or raw_messages,
        ):
            return MedicineQaRouteDecision(
                MedicineQaRoute.MEDICINE_QA,
                "travel_import_thread",
            )
    except ImportError:
        pass

    if _is_concierge_topic_pivot(t):
        meta_intent = _resolve_concierge_meta_intent(
            t,
            session=session,
            conversation_history=llm_history or raw_messages,
        )
        if meta_intent:
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "topic_pivot_concierge",
                concierge_intent=meta_intent,
            )

    from src.services.concierge_agent_history import is_meta_follow_up_utterance

    if llm_history and is_meta_follow_up_utterance(t):
        meta_intent = _resolve_concierge_meta_intent(
            t,
            session=session,
            conversation_history=llm_history or raw_messages,
        )
        if meta_intent:
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "meta_follow_up_concierge",
                concierge_intent=meta_intent,
            )

    meta_intent = _resolve_concierge_meta_intent(
        t,
        session=session,
        conversation_history=llm_history or raw_messages,
    )
    if meta_intent:
        compound = _resolve_compound_route_override(
            t,
            meta_intent,
            conversation_history=llm_history or raw_messages,
            recommended_medicines=recs,
            client=client,
        )
        if compound:
            return compound
        return MedicineQaRouteDecision(
            MedicineQaRoute.CONCIERGE,
            "fast_concierge_meta",
            concierge_intent=meta_intent,
        )

    from src.services.medicine_qa_routing import should_prioritize_physical_for_symptom

    recs_early = recommended_medicines
    if recs_early is None:
        recs_early = _extract_recommended_medicines(session, conversation_history)

    if should_prioritize_physical_for_symptom(
        t,
        conversation_history=llm_history or raw_messages,
        recommended_medicines=recs_early,
    ):
        return MedicineQaRouteDecision(
            MedicineQaRoute.PHYSICAL,
            "symptom_physical_priority",
        )

    thread_source = should_continue_medicine_thread(
        t,
        session=session,
        sid=sid,
        conversation_history=llm_history or raw_messages,
        recommended_medicines=recs,
        client=client,
    )
    if thread_source:
        return MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            thread_source,
        )

    active_products = collect_active_medicine_products(
        session,
        sid=sid,
        messages=raw_messages,
        recommended_medicines=recs,
    )
    if sid:
        try:
            from src.services.dialogue_turn_trace import append_dialogue_turn_trace

            prompt_turns = len(llm_history) if llm_history else 0
            product_names: list[str] = []
            for p in active_products or []:
                if isinstance(p, dict):
                    product_names.append(
                        str(p.get("product_name") or p.get("name") or "")
                    )
                else:
                    product_names.append(str(p))
            product_names = [n for n in product_names if n][:8]
            rag_tier = ""
            try:
                from src.services.local_rag_context import resolve_rag_tier

                rag_tier = resolve_rag_tier(
                    t,
                    conversation_history=llm_history or raw_messages,
                    recommended_medicines=recs,
                    session=session,
                )
            except Exception:
                logger.debug("resolve_rag_tier skipped", exc_info=True)
            append_dialogue_turn_trace(
                session_id=str(sid),
                user_message=t,
                route="medicine_qa_eligibility",
                active_products=product_names,
                prompt_turns=prompt_turns,
                rag_tier=rag_tier,
                source="resolve_medicine_qa_route",
            )
            try:
                from src.services.turn_user_goal import resolve_turn_user_goal
                from src.dialogue.sync_legacy import update_dialogue_turn_state

                goal = resolve_turn_user_goal(
                    t,
                    conversation_history=llm_history or raw_messages,
                    active_products=product_names,
                )
                update_dialogue_turn_state(
                    session,
                    sid,
                    user_text=t,
                    user_goal=goal,
                    active_products=product_names,
                    thread_topic=product_names[0] if product_names else None,
                )
            except Exception:
                logger.debug("dialogue_state turn update skipped", exc_info=True)
        except Exception:
            logger.debug("dialogue_turn_trace skipped", exc_info=True)
    if active_products and not recs:
        recs = active_products

    from src.services.medicine_qa_routing import (
        is_symptom_recommendation_followup,
        is_travel_import_context,
    )

    if is_symptom_recommendation_followup(
        t,
        conversation_history=llm_history or raw_messages,
        recommended_medicines=recs,
    ):
        return MedicineQaRouteDecision(
            MedicineQaRoute.PHYSICAL,
            "symptom_thread_recommendation",
        )

    if (recs or active_products) and client is not None:
        try:
            from src.services.conversation_followup_resolver import (
                FollowupIntent,
                resolve_ambiguous_followup_intent,
            )

            intent = resolve_ambiguous_followup_intent(
                t,
                session=session,
                sid=sid,
                conversation_history=llm_history or raw_messages,
                recommended_medicines=recs,
                client=client,
            )
            if intent == FollowupIntent.RESCORE:
                return MedicineQaRouteDecision(
                    MedicineQaRoute.PHYSICAL,
                    "llm_followup_rescore",
                )
            if intent in (FollowupIntent.MEDICINE_QA, FollowupIntent.CONTINUE_THREAD):
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "llm_followup_medicine_qa",
                )
            if intent == FollowupIntent.TRAVEL:
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "llm_followup_travel",
                )
        except ImportError:
            pass

    if (
        _THREAD_INVENTORY_FOLLOWUP_RE.search(t)
        and active_products
        and not is_travel_import_context(t)
    ):
        return MedicineQaRouteDecision(
            MedicineQaRoute.MEDICINE_QA,
            "rule_medicine_thread_inventory_fallback",
        )

    def _after_meta_none() -> MedicineQaRouteDecision:
        return _resolve_after_meta_none(
            t,
            conversation_history=llm_history or raw_messages,
            recommended_medicines=recs,
        )

    if _has_medicine_qa_fast_signals(
        t,
        conversation_history=llm_history or raw_messages,
        recommended_medicines=recs,
    ):
        from src.services.store_inquiry_handler import is_probable_store_inquiry_any

        if is_probable_store_inquiry_any(t, triage_result=triage_result):
            return MedicineQaRouteDecision(MedicineQaRoute.DEFER, "store_over_medicine_qa")
        return MedicineQaRouteDecision(MedicineQaRoute.MEDICINE_QA, "fast_medicine_signal")

    if has_explicit_symptom_signal(t) and not looks_like_inquiry(t):
        return MedicineQaRouteDecision(MedicineQaRoute.PHYSICAL, "explicit_symptom")

    if not looks_like_inquiry(t):
        try:
            from src.services.medicine_discovery_routing import session_has_medicine_qa_context

            if session_has_medicine_qa_context(session, sid) or active_products:
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "medicine_context_short_utterance",
                )
        except Exception:
            pass
        ack_intent = _resolve_structural_ack_intent(
            t,
            session=session,
            conversation_history=llm_history or raw_messages,
        )
        if ack_intent:
            if (
                ack_intent == "greeting"
                and active_products
                and _THREAD_INVENTORY_FOLLOWUP_RE.search(t)
            ):
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "rule_medicine_thread_inventory_fallback",
                )
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "structural_ack",
                concierge_intent=ack_intent,
            )
        return MedicineQaRouteDecision(MedicineQaRoute.DEFER, "not_inquiry_form")

    if client is not None and is_medicine_qa_eligibility_llm_enabled():
        llm_intent = _llm_resolve_concierge_intent(
            t,
            client,
            conversation_history=llm_history or raw_messages,
        )
        if llm_intent:
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "llm_meta_triage",
                concierge_intent=llm_intent,
            )
        return _after_meta_none()

    if not looks_like_inquiry(t):
        try:
            from src.services.medicine_discovery_routing import session_has_medicine_qa_context

            if session_has_medicine_qa_context(session, sid) or active_products:
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "medicine_context_short_utterance",
                )
        except Exception:
            pass
        ack_intent = _resolve_structural_ack_intent(
            t,
            session=session,
            conversation_history=llm_history or raw_messages,
        )
        if ack_intent:
            if (
                ack_intent == "greeting"
                and active_products
                and _THREAD_INVENTORY_FOLLOWUP_RE.search(t)
            ):
                return MedicineQaRouteDecision(
                    MedicineQaRoute.MEDICINE_QA,
                    "rule_medicine_thread_inventory_fallback",
                )
            return MedicineQaRouteDecision(
                MedicineQaRoute.CONCIERGE,
                "structural_ack",
                concierge_intent=ack_intent,
            )

    return MedicineQaRouteDecision(
        MedicineQaRoute.CONCIERGE,
        "inquiry_no_medicine_fallback",
        concierge_intent="redirect",
    )


def should_route_medicine_information_qa(
    text: str,
    *,
    session: Any = None,
    triage_result: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    client: OpenAI | None = None,
) -> bool:
    """
    早期 medicine_qa 直行（chat_post_pipeline / dispatcher / unified_router）の可否。

    ``is_medicine_information_question`` が True でも Concierge / Physical 意図なら False。
    """
    decision = resolve_medicine_qa_route(
        text,
        session=session,
        triage_result=triage_result,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
        client=client,
    )
    return decision.route == MedicineQaRoute.MEDICINE_QA
