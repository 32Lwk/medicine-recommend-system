"""医薬品スレッド継続判定 — ルーター・セッション・LLM を横断（シナリオ別ハードコード最小）。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MEDICINE_ROUTER_SUBS = frozenset({
    "medicine_followup_qa",
    "medicine_qa",
    "medicine_side_effect_qa",
    "rule_based_recommend",
})

_CONTINUATION_LLM_MAX_CHARS = 120


def _is_bot_message(msg: dict[str, Any]) -> bool:
    msg_type = str(msg.get("type") or "").lower()
    if msg_type == "bot":
        return True
    role = str(msg.get("role") or "").lower()
    return role in ("assistant", "bot")


def expand_messages_for_llm(
    messages: list[dict[str, Any]] | None,
    *,
    max_turns: int = 10,
) -> list[dict[str, str]]:
    """Sage マーカーをプレーン展開した履歴（routing / Q&A / RAG 共通）。"""
    from src.utils.sage_message_plain import resolve_bot_user_facing_text

    out: list[dict[str, str]] = []
    for msg in (messages or [])[-max_turns:]:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "").strip().lower()
        if not role:
            msg_type = str(msg.get("type") or "").strip().lower()
            if msg_type == "user":
                role = "user"
            elif msg_type in ("bot", "assistant"):
                role = "assistant"
        if role == "assistant" or str(msg.get("type") or "").lower() == "bot":
            content = resolve_bot_user_facing_text(msg)
        else:
            content = str(msg.get("content") or "").strip()
        if role and content:
            out.append({"role": role, "content": content})
    return out


def format_recent_turns_plain(
    messages: list[dict[str, Any]] | None,
    *,
    max_turns: int = 6,
) -> str:
    lines: list[str] = []
    for turn in expand_messages_for_llm(messages, max_turns=max_turns):
        label = "ユーザー" if turn.get("role") == "user" else "AI"
        lines.append(f"{label}: {turn.get('content', '')[:400]}")
    return "\n".join(lines)


def collect_active_medicine_products(
    session: Any,
    *,
    sid: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """推奨履歴・QA ピン・bot 応答からアクティブな医薬品コンテキストを集約。"""
    products: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(name: str, source: str, **extra: Any) -> None:
        n = (name or "").strip()
        if not n or n in seen:
            return
        seen.add(n)
        products.append({"product_name": n, "source": source, **extra})

    msgs = list(messages or [])
    if not msgs and session is not None:
        msgs = list((session.get("messages") if isinstance(session, dict) else []) or [])
    if sid and not msgs:
        try:
            from src.services.session_manager import get_session_from_db

            msgs = list((get_session_from_db(sid) or {}).get("messages") or [])
        except Exception:
            pass

    from src.dialogue.routing.context_signals import extract_drug_entities
    from src.utils.sage_message_plain import resolve_bot_user_facing_text

    for msg in reversed(msgs):
        if _is_bot_message(msg):
            continue
        plain = str(msg.get("content") or msg.get("message") or "").strip()
        if not plain and str(msg.get("role") or "").lower() == "user":
            plain = str(msg.get("content") or "").strip()
        for entity in extract_drug_entities(plain):
            _add(entity, "history_user_entity")

    try:
        from src.dialogue.context import get_dialogue_thread_state

        for name in get_dialogue_thread_state(session).get("active_products") or []:
            _add(str(name), "dialogue_state")
    except Exception:
        pass

    for med in recommended_medicines or []:
        _add(str(med.get("product_name") or med.get("name") or ""), "recommended")

    try:
        from src.services.medicine_qa_session_pins import get_session_brand_pins

        for pin in get_session_brand_pins(session).values():
            _add(str(pin.get("product_name") or ""), "brand_pin")
    except Exception:
        pass

    for msg in reversed(msgs):
        if not _is_bot_message(msg):
            continue
        diagnosis = msg.get("diagnosis") or {}
        for med in diagnosis.get("recommended_medicines") or []:
            _add(str(med.get("product_name") or ""), "history_reco")
        plain = resolve_bot_user_facing_text(msg)
        for entity in extract_drug_entities(plain):
            _add(entity, "history_bot_entity")
        if len(products) >= 5:
            break

    return products[:5]


def resolve_session_recommended_medicines(
    session: Any,
    *,
    sid: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    max_products: int = 5,
) -> list[dict[str, Any]]:
    """
    推奨履歴・QA 応答エンティティを Local RAG / Q&A 用の医薬品レコードに解決する。
    diagnosis.recommended_medicines が無い sage_qa 等でも会話文脈から複数品目を復元する。
    """
    msgs = list(messages or [])
    if not msgs and session is not None:
        msgs = list((session.get("messages") if isinstance(session, dict) else []) or [])
    if sid and not msgs:
        try:
            from src.services.session_manager import get_session_from_db

            msgs = list((get_session_from_db(sid) or {}).get("messages") or [])
        except Exception:
            pass

    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _merge(recs: list[dict[str, Any]]) -> None:
        for med in recs:
            name = str(med.get("product_name") or med.get("name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                resolved.append(med)

    active = collect_active_medicine_products(session, sid=sid, messages=msgs)
    user_stated = [p for p in active if p.get("source") == "history_user_entity"]

    def _resolve_active_hints(hints: list[dict[str, Any]]) -> None:
        try:
            import pandas as pd

            from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query
            from src.core.medicine_logic import CSV_PATH

            df = pd.read_csv(CSV_PATH)
            for prod in hints:
                hint = str(prod.get("product_name") or "").strip()
                if not hint:
                    continue
                hits = detect_medicine_name_in_query(hint, df, session=session)
                if hits:
                    _merge(hits[:2])
                elif hint not in seen:
                    seen.add(hint)
                    resolved.append({"product_name": hint})
                if len(resolved) >= max_products:
                    return
        except Exception:
            logger.debug("resolve_session_recommended_medicines csv skipped", exc_info=True)
            for prod in hints:
                hint = str(prod.get("product_name") or "").strip()
                if hint and hint not in seen:
                    seen.add(hint)
                    resolved.append({"product_name": hint})

    if user_stated:
        _resolve_active_hints(user_stated)
        if len(resolved) >= max_products:
            return resolved[:max_products]

    for msg in reversed(msgs):
        if not _is_bot_message(msg):
            continue
        diag = msg.get("diagnosis") or {}
        recs = diag.get("recommended_medicines")
        if recs:
            _merge(list(recs))
            if len(resolved) >= max_products:
                return resolved[:max_products]

    if not active:
        return resolved[:max_products]

    try:
        import pandas as pd

        from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query
        from src.core.medicine_logic import CSV_PATH

        df = pd.read_csv(CSV_PATH)
        for prod in active:
            hint = str(prod.get("product_name") or "").strip()
            if not hint:
                continue
            hits = detect_medicine_name_in_query(hint, df, session=session)
            if hits:
                _merge(hits[:2])
            elif hint not in seen:
                seen.add(hint)
                resolved.append({"product_name": hint})
            if len(resolved) >= max_products:
                break
    except Exception:
        logger.debug("resolve_session_recommended_medicines csv skipped", exc_info=True)
        for prod in active:
            hint = str(prod.get("product_name") or "").strip()
            if hint and hint not in seen:
                seen.add(hint)
                resolved.append({"product_name": hint})

    return resolved[:max_products]


def _is_concierge_topic_pivot(text: str) -> bool:
    """医薬品スレッドから Concierge へ話題転換する入力（例: 技術スタック）。"""
    t = (text or "").strip()
    if not t:
        return False
    try:
        from src.services.concierge_agent_history import is_meta_follow_up_utterance
        from src.services.concierge_intent import (
            _PRE_TRIAGE_META_INTENTS,
            classify_concierge_intent,
            probe_meta_concierge_intent,
        )

        if is_meta_follow_up_utterance(t):
            return True
        if probe_meta_concierge_intent(t):
            return True
        fast = classify_concierge_intent(t)
        if fast in _PRE_TRIAGE_META_INTENTS:
            return True
    except Exception:
        logger.debug("concierge topic pivot check skipped", exc_info=True)
    return False


def _intent_router_medicine_sub(session: Any) -> Optional[str]:
    if not session or not isinstance(session, dict):
        return None
    dec = session.get("_intent_router_dispatch") or {}
    sub = str(dec.get("sub_route") or "").strip()
    if sub in _MEDICINE_ROUTER_SUBS:
        return sub
    primary = str(dec.get("primary_route") or dec.get("route") or "").strip()
    if primary == "Physical" and sub:
        return sub
    return None


def _llm_medicine_thread_continuation(
    text: str,
    *,
    recent_turns: str,
    active_products: list[dict[str, Any]],
    client: Any,
) -> bool:
    """曖昧な追質問が直前の医薬品スレッドの継続か LLM で判定。"""
    try:
        from config.llm_flags import is_routing_followup_llm_enabled
    except ImportError:
        return False
    if not is_routing_followup_llm_enabled(None) or client is None:
        return False

    product_names = ", ".join(
        str(p.get("product_name") or "") for p in active_products if p.get("product_name")
    )
    prompt = (
        "あなたは市販薬チャットの文脈分類器です。"
        "ユーザーの発話が、直前の医薬品・市販薬に関する会話の継続（追質問・確認・追加報告）か、"
        "無関係な挨拶・雑談・新トピックかを判定してください。\n"
        "特定フレーズ一致ではなく、会話全体の意図を優先してください。\n\n"
        f"ユーザー発話: {text}\n"
        f"会話で扱っている医薬品: {product_names or '(不明)'}\n"
        f"直近会話:\n{recent_turns or '(なし)'}\n\n"
        "JSON のみ: "
        '{"continues_medicine_thread": true/false, "reason": "短い理由"}'
    )
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text

        resp = chat_completion_create(
            client,
            model_role="router",
            path="medicine_thread/continuation_llm",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        raw = extract_completion_text(resp)
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict):
            return bool(parsed.get("continues_medicine_thread"))
    except Exception:
        logger.debug("medicine_thread continuation LLM failed", exc_info=True)
    return False


def should_continue_medicine_thread(
    text: str,
    *,
    session: Any = None,
    sid: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    client: Any = None,
) -> Optional[str]:
    """
    医薬品スレッド継続と判断できる場合は source 文字列を返す。
    Concierge greeting 等への誤ルーティング抑止に使う。
    """
    t = (text or "").strip()
    if not t:
        return None

    if _is_concierge_topic_pivot(t):
        return None

    from src.services.medicine_qa_routing import should_prioritize_physical_for_symptom

    if should_prioritize_physical_for_symptom(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return None

    router_sub = _intent_router_medicine_sub(session)
    if router_sub in ("medicine_followup_qa", "medicine_qa", "medicine_side_effect_qa"):
        return f"intent_router_{router_sub}"

    try:
        from src.services.medicine_context_routing import resolve_medicine_context_route

        ctx_route = resolve_medicine_context_route(session, sid, t, client=client)
        if ctx_route == "followup_qa":
            return "medicine_context_followup_qa"
    except Exception:
        logger.debug("medicine_context_route skipped", exc_info=True)

    try:
        from src.services.medicine_discovery_routing import session_has_medicine_qa_context

        has_ctx = session_has_medicine_qa_context(session, sid)
    except Exception:
        has_ctx = bool(recommended_medicines)

    active = collect_active_medicine_products(
        session,
        sid=sid,
        messages=conversation_history,
        recommended_medicines=recommended_medicines,
    )
    if not has_ctx and not active:
        return None

    from src.services.concierge_intent import looks_like_inquiry, _is_medicine_consultation
    from src.utils.input_helpers import has_explicit_symptom_signal

    if active and _is_medicine_discussion_continuation(t, active_products=active):
        return "rule_medicine_thread_continuation"

    if _is_medicine_consultation(t) or (
        has_explicit_symptom_signal(t) and not looks_like_inquiry(t)
        and not _is_medicine_discussion_continuation(t, active_products=active)
    ):
        return None

    if looks_like_inquiry(t):
        try:
            from src.services.store_inquiry_handler import is_probable_store_inquiry_any

            if is_probable_store_inquiry_any(t):
                return None
        except Exception:
            pass
        try:
            from src.services.concierge_agent_history import is_meta_follow_up_utterance

            if is_meta_follow_up_utterance(t):
                return None
        except Exception:
            pass
        try:
            from src.services.medicine_qa_routing import is_medicine_information_question

            if is_medicine_information_question(
                t,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines or active,
            ):
                return "medicine_information_question"
        except Exception:
            pass

    recent = format_recent_turns_plain(conversation_history)
    if len(t) <= _CONTINUATION_LLM_MAX_CHARS and (has_ctx or active):
        if _rule_based_medicine_thread_continuation(
            t,
            has_ctx=has_ctx,
            active_products=active,
        ):
            return "rule_medicine_thread_continuation"
        if _llm_medicine_thread_continuation(
            t,
            recent_turns=recent,
            active_products=active,
            client=client,
        ):
            return "llm_medicine_thread_continuation"

    return None


def _is_medicine_discussion_continuation(
    text: str,
    *,
    active_products: list[dict[str, Any]],
) -> bool:
    """
    症状語を含んでも医薬品スレッド内の感想・確認・用法議論とみなす。
    （例: 「痛みが和らぐのはありがたい」「説明書を読んでおこう」）
    """
    t = (text or "").strip()
    if not t or not active_products:
        return False
    if len(t) > _CONTINUATION_LLM_MAX_CHARS:
        return False

    try:
        from src.services.store_inquiry_handler import is_probable_store_inquiry_any

        if is_probable_store_inquiry_any(t):
            return False
    except Exception:
        pass

    medicine_markers = (
        "説明書", "飲み合わせ", "副作用", "効く", "和らぐ", "使う", "試す",
        "ロキソ", "イブ", "市販薬", "飲ん", "服用", "成分", "注意", "平気",
        "併用", "一緒", "量", "錠", "スプレ", "包装", "パッケージ",
        "家に", "うちに", "Sは", "Sが", "見てみ",
    )
    reflective_markers = (
        "うん", "そう", "なるほど", "ありがた", "大事", "気をつけ", "確認",
        "読んで", "間違え", "怖い", "安心", "助か", "ね", "よね", "だね",
    )
    has_med = any(m in t for m in medicine_markers)
    has_reflect = any(m in t for m in reflective_markers)

    new_symptom_report = bool(
        re.search(
            r"(?:頭(?:が|の)?痛(?:い|み(?:が|を)?(?:ある|します|ひど|続))|"
            r"喉(?:が|の)?痛|お腹(?:が|の)?痛|熱(?:が|は)?(?:ある|出|高)|"
            r"咳(?:が|を)?(?:出|ひど)|(?:今|きょう|今日).{0,4}(?:痛|熱|咳))",
            t,
        )
    )
    if new_symptom_report and not has_med:
        return False
    if has_med or (has_reflect and "痛み" in t and "和ら" in t):
        return True
    if has_reflect and has_med:
        return True
    if has_reflect and len(t) <= 80:
        return True
    return False


def _rule_based_medicine_thread_continuation(
    text: str,
    *,
    has_ctx: bool,
    active_products: list[dict[str, Any]],
) -> bool:
    """
    医薬品スレッド内の短い追質問・報告を LLM 前に判定（レイテンシ・コスト削減）。
    明示的新トピック（症状相談・店舗・メタ質問）のみ除外する。
    """
    t = (text or "").strip()
    if not t or len(t) > _CONTINUATION_LLM_MAX_CHARS:
        return False
    if not has_ctx and not active_products:
        return False

    from src.services.concierge_intent import _is_medicine_consultation, looks_like_inquiry
    from src.utils.input_helpers import has_explicit_symptom_signal

    if _is_medicine_consultation(t):
        return False
    if has_explicit_symptom_signal(t) and not looks_like_inquiry(t):
        return False

    try:
        from src.services.store_inquiry_handler import is_probable_store_inquiry_any

        if is_probable_store_inquiry_any(t):
            return False
    except Exception:
        pass

    try:
        from src.services.concierge_agent_history import (
            infer_lost_context_follow_up_intent,
            is_meta_follow_up_utterance,
        )

        if is_meta_follow_up_utterance(t) or infer_lost_context_follow_up_intent(t):
            return False
    except Exception:
        pass

    if looks_like_inquiry(t):
        return True

    followup_short = re.search(
        r"家に|うちに|さっき|それ|Sは|Sが|見てみ|プレミアム|ついて",
        t,
    )
    if followup_short and active_products:
        return True

    return True
