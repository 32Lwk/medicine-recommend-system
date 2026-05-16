"""
ConciergeAgent — 挨拶・メタ質問・軽い雑談・Physical ハンドオフ案内
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from src.content.concierge_docs import DOC_CONCIERGE_INTENTS, load_concierge_doc
from src.content.concierge_knowledge import get_handoff_intro_physical, get_policy_snippet
from src.services.concierge_intent import ConciergeIntent, classify_concierge_intent
from src.services.concierge_orchestrator import resolve_intent_from_triage
from src.services.concierge_llm import concierge_chat
from src.services.concierge_templates import (
    build_greeting_text,
    build_redirect_text,
    build_thanks_text,
    format_concierge_app_about_card,
    format_concierge_architecture_card,
    format_concierge_capabilities_card,
    format_concierge_operator_card,
)

logger = logging.getLogger(__name__)

ResponsePayload = Dict[str, Any]

# 参照ドキュメントの要約のみ返す intent（末尾の相談促し・免責定型文は付けない）
_DOC_REFERENCE_ONLY_INTENTS = frozenset(
    {"doc_privacy", "doc_terms", "doc_consultation", "doc_app_overview"}
)


def get_concierge_state(session: Any) -> Dict[str, Any]:
    state = session.get("concierge_state")
    if not isinstance(state, dict):
        state = {"off_topic_turns": 0, "last_intent": None}
        session["concierge_state"] = state
    return state


def update_concierge_state(session: Any, intent: str, *, reset_off_topic: bool = False) -> None:
    state = get_concierge_state(session)
    if reset_off_topic:
        state["off_topic_turns"] = 0
    elif intent == "chitchat":
        state["off_topic_turns"] = int(state.get("off_topic_turns") or 0) + 1
    else:
        state["off_topic_turns"] = 0
    state["last_intent"] = intent


def resolve_concierge_intent(
    user_text: str,
    session: Any,
    *,
    triage_result: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAI] = None,
    session_id: Optional[str] = None,
    conversation_history: Optional[list] = None,
) -> Optional[ConciergeIntent]:
    from src.services.concierge_intent import _is_medicine_consultation
    from src.services.concierge_orchestrator import enrich_other_concierge_intent

    text = (user_text or "").strip()
    if not text or _is_medicine_consultation(text):
        return None

    orchestrated = resolve_intent_from_triage(triage_result, session, text)
    if orchestrated:
        return orchestrated

    base = classify_concierge_intent(text)
    if base == "chitchat":
        state = get_concierge_state(session)
        if int(state.get("off_topic_turns") or 0) >= 2:
            return "redirect"
        return "chitchat"
    if base in ("greeting", "thanks"):
        return base

    category = (triage_result or {}).get("category", "")
    if category == "Other" and client is not None:
        enriched = enrich_other_concierge_intent(
            dict(triage_result or {}),
            text,
            client,
            conversation_history=conversation_history,
            session_id=session_id,
        )
        resolved = resolve_intent_from_triage(enriched, session, text)
        if resolved:
            return resolved
        if enriched.get("concierge_intent") == "redirect":
            return "redirect"

    return None


def _feedback_data(user_text: str, intent: str) -> Dict[str, Any]:
    return {
        "user_message": user_text,
        "ai_response": f"concierge:{intent}",
        "concierge_intent": intent,
    }


def generate_doc_answer_text(
    client: OpenAI,
    user_text: str,
    intent: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """公式 docs/*.md を参照し、Concierge LLM で正確に回答する。"""
    title, doc_body = load_concierge_doc(intent)
    hist = ""
    if history:
        lines = []
        for m in history[-6:]:
            role = m.get("type") or m.get("role") or "user"
            content = (m.get("content") or "")[:200]
            lines.append(f"{role}: {content}")
        hist = "\n".join(lines)
    if intent in _DOC_REFERENCE_ONLY_INTENTS:
        requirements = """【要件】
- 上記ドキュメントに書かれた内容のみに基づいて回答する（推測・補完しない）
- ドキュメントにない事項だけ「ドキュメントに記載がありません」と明記する
- 連絡先・URL・禁止事項などはドキュメントの表記を変えず正確に伝える
- 箇条書きまたは短い段落で分かりやすく（Markdown は使わずプレーンテキスト）
- ドキュメント本文に無い免責・診断不可・相談促しなどの定型文は付けない
"""
    else:
        requirements = f"""{get_policy_snippet()}

【要件】
- 上記ドキュメントに書かれた内容のみに基づいて回答する（推測・補完しない）
- ドキュメントにない事項は「ドキュメントに記載がありません」と明記する
- 連絡先・URL・禁止事項などはドキュメントの表記を変えず正確に伝える
- 箇条書きまたは短い段落で分かりやすく（Markdown は使わずプレーンテキスト）
- 医療診断・処方は行わない
- 市販薬の候補選定はルールベースのみである点は、質問に関係する場合のみ簡潔に触れる
- 最後に、症状やお薬の相談があれば具体的にお書きいただくよう1文で促す
"""
    prompt = f"""【参照ドキュメント名】
{title}

【参照ドキュメント全文（唯一の根拠）】
{doc_body}

【会話履歴（参考）】
{hist or "（なし）"}

【ユーザーの質問】
{user_text}

{requirements}
"""
    try:
        resp = concierge_chat(
            client,
            f"concierge_agent.{intent}",
            [
                {
                    "role": "system",
                    "content": (
                        "あなたは医薬品相談ツールの案内役です。"
                        "与えられた公式ドキュメント以外の情報で回答してはいけません。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            temperature=0.2,
            session_id=session_id,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.warning("Concierge doc answer LLM failed (%s): %s", intent, exc)
    return (
        f"「{title}」についてのご質問ありがとうございます。"
        "現在詳細を取得できませんでした。画面右上の ℹ️ から各種ドキュメントをご確認ください。"
        "お体の不調やお薬のことでしたら、具体的な症状をお書きください。"
    )


def generate_chitchat_text(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    hist = ""
    if history:
        lines = []
        for m in history[-6:]:
            role = m.get("type") or m.get("role") or "user"
            content = (m.get("content") or "")[:200]
            lines.append(f"{role}: {content}")
        hist = "\n".join(lines)
    prompt = f"""{get_policy_snippet()}

【会話履歴（参考）】
{hist or "（なし）"}

【ユーザーの発言】
{user_text}

【要件】
- 1〜2文で短く返答
- 医療診断・処方はしない
- 最後に症状やお薬の相談を軽く促す
"""
    try:
        resp = concierge_chat(
            client,
            "concierge_agent.chitchat",
            [
                {
                    "role": "system",
                    "content": "あなたは医薬品相談ツールの案内役です。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=180,
            temperature=0.6,
            session_id=session_id,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Concierge chitchat LLM failed: %s", exc)
        return (
            "お話ありがとうございます。お体の不調やお薬のことでしたら、"
            "具体的な症状を教えてください。"
        )


def build_concierge_payload(
    intent: ConciergeIntent,
    user_text: str,
    client: OpenAI,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> ResponsePayload:
    fb = _feedback_data(user_text, intent)

    if intent == "greeting":
        return {
            "content": build_greeting_text(user_text),
            "content_format": "text",
            "concierge_intent": intent,
            "greeting": True,
            "llm_used": False,
        }
    if intent == "thanks":
        return {
            "content": build_thanks_text(),
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent == "redirect":
        return {
            "content": build_redirect_text(),
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent == "capabilities":
        return {
            "content": format_concierge_capabilities_card(feedback_data=fb),
            "content_format": "status_card",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent == "architecture":
        return {
            "content": format_concierge_architecture_card(feedback_data=fb),
            "content_format": "status_card",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent == "app_about":
        return {
            "content": format_concierge_app_about_card(feedback_data=fb),
            "content_format": "status_card",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent == "doc_operator":
        return {
            "content": format_concierge_operator_card(feedback_data=fb),
            "content_format": "status_card",
            "concierge_intent": intent,
            "llm_used": False,
        }
    if intent in DOC_CONCIERGE_INTENTS:
        return {
            "content": generate_doc_answer_text(
                client,
                user_text,
                intent,
                session_id=session_id,
                history=history,
            ),
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": True,
        }
    if intent == "chitchat":
        return {
            "content": generate_chitchat_text(
                client, user_text, session_id=session_id, history=history
            ),
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": True,
        }
    if intent == "medical_handoff":
        return {
            "content": get_handoff_intro_physical(),
            "content_format": "text",
            "concierge_intent": intent,
            "concierge_handoff_to": "physical",
            "llm_used": False,
        }
    return {
        "content": build_redirect_text(),
        "content_format": "text",
        "concierge_intent": "redirect",
        "llm_used": False,
    }


def should_concierge_handle(user_text: str, triage_result: Optional[Dict[str, Any]]) -> bool:
    """Other または挨拶・感謝・雑談のみ Concierge。医薬品・Emergency・Physical は除外。"""
    from src.services.concierge_intent import _is_medicine_consultation

    if not user_text or _is_medicine_consultation(user_text):
        return False
    cat = (triage_result or {}).get("category", "")
    if cat in ("Emergency", "Physical", "Ask"):
        return False
    fast = classify_concierge_intent(user_text)
    if fast in ("greeting", "thanks", "chitchat"):
        return True
    return cat == "Other"
