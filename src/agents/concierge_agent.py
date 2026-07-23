"""
ConciergeAgent — 挨拶・メタ質問・軽い雑談・Physical ハンドオフ案内
"""
from __future__ import annotations

import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from src.content.concierge_docs import DOC_CONCIERGE_INTENTS, load_concierge_doc
from src.content.concierge_knowledge import (
    get_handoff_intro_physical,
    get_policy_snippet,
    get_service_identity_block,
)
from src.services.concierge_intent import ConciergeIntent, classify_concierge_intent
from src.services.concierge_orchestrator import resolve_intent_from_triage
from src.services.concierge_llm import concierge_chat
from src.services.concierge_templates import (
    build_concierge_app_about_line_flex,
    build_concierge_architecture_line_flex,
    build_concierge_capabilities_line_flex,
    build_concierge_operator_line_flex,
    build_dynamic_concierge_line_flex,
    structure_concierge_meta_display,
    split_dynamic_body_paragraphs,
    build_greeting_text,
    build_redirect_text,
    build_redirect_followup_text,
    build_thanks_text,
    format_concierge_app_about_card,
    format_concierge_architecture_card,
    format_concierge_capabilities_card,
    format_dynamic_concierge_meta_card,
    format_concierge_operator_card,
)

logger = logging.getLogger(__name__)

ResponsePayload = Dict[str, Any]

# 参照ドキュメントの要約のみ返す intent（末尾の相談促し・免責定型文は付けない）
_DOC_REFERENCE_ONLY_INTENTS = frozenset(
    {"doc_privacy", "doc_terms", "doc_consultation", "doc_app_overview", "doc_changelog"}
)

_CONCIERGE_PROMPT_HISTORY_LIMIT = 10


def _prior_history_for_prompt(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
) -> List[Dict[str, str]]:
    """プロンプト用: 末尾の今回 user 発話（未応答分）を履歴から除外。"""
    msgs = [m for m in (history or []) if isinstance(m, dict)]
    text = (user_text or "").strip()
    if msgs and text and msgs[-1].get("type") == "user":
        if str(msgs[-1].get("content") or "").strip() == text:
            return msgs[:-1]
    return msgs


def count_same_greeting_exchange_rounds(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
) -> int:
    """同一挨拶のやり取りが何巡目か（今回の送信を含む）。"""
    prior = _prior_history_for_prompt(history, user_text)
    text = (user_text or "").strip()
    rounds = 1
    i = len(prior) - 1
    while i >= 0:
        if prior[i].get("type") != "bot":
            break
        i -= 1
        if i < 0 or prior[i].get("type") != "user":
            break
        if str(prior[i].get("content") or "").strip() != text:
            break
        rounds += 1
        i -= 1
    return rounds


def _is_greeting_like_user_message(content: str) -> bool:
    """挨拶・一声の呼びかけは話題抽出から除外する。"""
    if classify_concierge_intent(content) in ("greeting", "thanks"):
        return True
    if is_short_impatient_callout(content):
        return True
    try:
        from src.services.concierge_intent import infer_structural_concierge_intent

        if infer_structural_concierge_intent(content) == "greeting":
            return True
    except ImportError:
        pass
    return False


def _extract_substantive_user_topics(
    msgs: List[Dict[str, str]],
) -> List[str]:
    """挨拶・お礼以外の、会話の核になりうる user 発話を抽出。"""
    topics: List[str] = []
    for m in msgs:
        if m.get("type") != "user":
            continue
        content = str(m.get("content") or "").strip()
        if not content or _is_greeting_like_user_message(content):
            continue
        topics.append(content[:80])
    return topics[-3:]


_TECH_STACK_TOPIC_RE = re.compile(r"スタック", re.IGNORECASE)


def _prior_topic_mentions_tech_stack(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
) -> bool:
    """直前の実質的な話題に「スタック」への言及があったか（p3-followup-hotfix）。"""
    prior = _prior_history_for_prompt(history, user_text)
    topics = _extract_substantive_user_topics(prior)
    return any(_TECH_STACK_TOPIC_RE.search(t) for t in topics)


def _append_tech_stack_reminder(text: str) -> str:
    """architecture フォローアップで技術スタックの話題が抜け落ちた場合の補足追記。"""
    addendum = (
        "技術スタックの補足としては、フロントエンドが HTML/CSS/バニラ JS、"
        "バックエンドは FastAPI です。"
    )
    return f"{text}\n\n{addendum}" if text else addendum


def _resolve_redirect_text(
    user_text: str,
    history: Optional[List[Dict[str, str]]],
) -> str:
    """redirect の同文ループ回避（p3-followup-hotfix, ROUTING_CONCIERGE_FOLLOWUP ON 限定）。

    直前 bot も concierge_redirect だった場合のみ、直前の脱線トピックを踏まえた
    具体例つきの案内に差し替える。フラグ OFF または初回の redirect は従来どおり固定文。
    """
    try:
        from config.llm_flags import is_concierge_followup_routing_enabled

        if not is_concierge_followup_routing_enabled():
            return build_redirect_text()
    except ImportError:
        return build_redirect_text()

    from src.services.concierge_agent_history import resolve_last_concierge_intent

    prior = _prior_history_for_prompt(history, user_text)
    if resolve_last_concierge_intent(prior) != "redirect":
        return build_redirect_text()

    topics = _extract_substantive_user_topics(prior)
    prior_topic = topics[-1] if topics else ""
    return build_redirect_followup_text(prior_topic)


def _last_bot_reply_snippet(
    msgs: List[Dict[str, str]],
    *,
    greeting_only: bool = False,
) -> str:
    from src.utils.sage_message_plain import resolve_bot_user_facing_text

    for m in reversed(msgs):
        if m.get("type") != "bot":
            continue
        if greeting_only:
            diag = m.get("diagnosis") or {}
            kind = str(diag.get("kind") or "")
            if not (m.get("greeting") or kind == "concierge_greeting"):
                continue
        snippet = resolve_bot_user_facing_text(m)[:120]
        if snippet:
            return snippet
    return ""


def format_concierge_context_block(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
    *,
    mode: str = "greeting",
) -> str:
    """挨拶・雑談向け: 履歴から会話の文脈メモを生成。"""
    prior = _prior_history_for_prompt(history, user_text)
    lines: List[str] = []
    text = (user_text or "").strip()

    if mode == "greeting":
        rounds = count_same_greeting_exchange_rounds(history, user_text)
        if rounds >= 2:
            lines.append(
                f"- 同じ挨拶「{text}」は今回で {rounds} 回目。"
                "直前の返答と同じ言い回し・同じ促し文は使わない"
            )
        if rounds >= 3:
            lines.append(
                "- 同じセッション内の連続挨拶なので「また来てくれて」等の再来訪表現は不自然。"
                "「お声がけありがとうございます」など軽く応じる"
            )

    topics = _extract_substantive_user_topics(prior)
    if topics:
        lines.append(f"- これまでの話題: {' / '.join(topics)}")
        lines.append(
            "- 話題に自然につなげられるなら1文だけ触れてよい（長く繰り返さない）"
        )
    elif mode == "greeting" and not infer_is_first_greeting_contact(history, user_text=user_text):
        lines.append(
            "- まだ具体的な相談はない。窓口説明を繰り返さず、様子を見る一言で受け止める"
        )

    if is_short_impatient_callout(text):
        lines.append("- 短い呼びかけへの返答は2文程度・60〜120文字")
        lines.append(
            "- 挑発的・失礼な言い回し（おい、ねえ、もしもし等）は真似せず、柔らかい丁寧語で受け止める"
        )

    last_bot = _last_bot_reply_snippet(
        prior,
        greeting_only=(mode == "greeting"),
    )
    if not last_bot and mode == "chitchat":
        last_bot = _last_bot_reply_snippet(prior, greeting_only=False)
    if last_bot:
        lines.append(f"- 直前の bot 返答: {last_bot}")
        lines.append("- 上記と同じフレーズ・構成は繰り返さない")

    if mode == "thanks":
        lines.append(
            f"- ユーザーの感謝「{text}」の言い回し・丁寧さに合わせて返す"
        )

    if mode == "chitchat" and not lines:
        lines.append("- 雑談の流れを踏まえ、前の話題に自然につなげる")

    return "\n".join(lines) if lines else "- 特になし"


def format_concierge_history_block(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
) -> str:
    from src.services.concierge_agent_history import format_concierge_agent_history_block

    prior = _prior_history_for_prompt(history, user_text)
    return format_concierge_agent_history_block(
        prior[-_CONCIERGE_PROMPT_HISTORY_LIMIT:]
    )


def format_meta_concierge_context_block(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
    *,
    intent: str,
) -> str:
    """メタ質問（仕組み・誰が答えているか等）向けの文脈メモ。"""
    from src.services.concierge_agent_history import (
        is_agent_roster_question,
        is_architecture_explanation_question,
        is_multi_agent_concept_question,
        is_who_is_answering_question,
        resolve_last_responding_agent,
    )

    prior = _prior_history_for_prompt(history, user_text)
    lines: List[str] = []
    who_question = is_who_is_answering_question(user_text)
    roster_question = is_agent_roster_question(user_text)
    multi_agent_question = is_multi_agent_concept_question(user_text)

    if who_question:
        last_agent = resolve_last_responding_agent(prior)
        if last_agent:
            lines.append(f"- 直前の返信担当（推定）: {last_agent}")
        lines.append(
            "- ユーザーは「いま誰が答えているか」を聞いている。"
            "直前の返信担当名を最初の1文で明示し、その返信文はAIが生成していることも短く述べる"
        )
        if last_agent:
            lines.append(
                f"- 回答の第一文は「いまの案内は{last_agent}が担当しています」"
                "のように担当名から始める"
            )
    elif intent == "architecture":
        if roster_question:
            lines.append(
                "- ユーザーはマルチエージェントの構成・役割分担について聞いている"
            )
            lines.append(
                "- 本文は導入2〜4文のみ。エージェント一覧はシステムが別カードで表示するため本文に列挙しない"
            )
            lines.append(
                "- 「いま誰が答えているか」「ConciergeAgentが担当」など担当宣言から答えを始めない"
            )
            lines.append(
                "- 会話履歴に既出の説明があれば補足にとどめ、同じ説明の繰り返しを避ける"
            )
        elif multi_agent_question:
            lines.append(
                "- ユーザーはマルチエージェントの意味・このサービスの役割分担について聞いている"
            )
            lines.append(
                "- 「いま誰が答えているか」「ConciergeAgentが担当」など担当宣言から答えを始めない"
            )
            lines.append(
                "- マルチエージェント＝複数の専門担当が連携する仕組みであることを中心に説明する"
            )
        else:
            lines.append(
                "- ユーザーは仕組み・技術・構成について聞いている（担当者の確認ではない）"
            )
            lines.append(
                "- 聞かれていない限り、担当エージェント名や「いま誰が答えているか」から答えを始めない"
            )
        lines.append(
            "- エージェントの役割一覧は本文に箇条書きで埋め込まない"
            "（前置きの説明文のみ。一覧はシステムが別表示する）"
        )

    topics = _extract_substantive_user_topics(prior)
    if topics:
        lines.append(f"- これまでの話題: {' / '.join(topics)}")

    last_bot = _last_bot_reply_snippet(prior, greeting_only=False)
    if last_bot:
        lines.append(f"- 直前の bot 返答: {last_bot}")
        lines.append("- 直前と同じ説明の繰り返しは避ける")

    return "\n".join(lines) if lines else "- 特になし"


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
    routing_ctx: Optional[Any] = None,
    llm_user_text: Optional[str] = None,
) -> Optional[ConciergeIntent]:
    from src.services.concierge_intent import _is_medicine_consultation
    from src.services.concierge_orchestrator import (
        enrich_other_concierge_intent,
        resolve_intent_from_triage,
    )

    text = (user_text or "").strip()
    llm_text = (llm_user_text or text).strip()
    if not text:
        return None

    from src.services.routing_context import evaluate_store_gate

    router_dispatch = bool((triage_result or {}).get("_intent_router_dispatch"))
    if not router_dispatch and evaluate_store_gate(
        text,
        triage_result=triage_result,
        routing_ctx=routing_ctx,
    ):
        return None

    from src.services.concierge_agent_history import (
        resolve_concierge_follow_up_intent,
        resolve_last_bot_message,
        resolve_prior_meta_intent,
    )

    last_bot = resolve_last_bot_message(conversation_history or [])
    prior = resolve_prior_meta_intent(
        session=session,
        conversation_history=conversation_history,
        sid=session_id,
    )
    follow = resolve_concierge_follow_up_intent(text, prior, last_bot=last_bot)
    if follow:
        return follow  # type: ignore[return-value]

    orchestrated = resolve_intent_from_triage(
        triage_result, session, text, sid=session_id, routing_ctx=routing_ctx
    )
    if orchestrated:
        return orchestrated

    if _is_medicine_consultation(text):
        return None

    base = classify_concierge_intent(text)
    if base == "chitchat":
        from src.dialogue.concierge_context import resolve_off_topic_turns

        if resolve_off_topic_turns(session, session_id) >= 2:
            return "redirect"
        return "chitchat"
    if base in ("greeting", "thanks"):
        return base

    category = (triage_result or {}).get("category", "")
    if category == "Other" and client is not None and not (triage_result or {}).get("concierge_intent"):
        enriched = enrich_other_concierge_intent(
            dict(triage_result or {}),
            llm_text,
            client,
            conversation_history=conversation_history,
            session_id=session_id,
            session=session,
            routing_ctx=routing_ctx,
        )
        resolved = resolve_intent_from_triage(enriched, session, text, sid=session_id)
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
    # 公式ドキュメント（特に privacy/terms）は md のみを根拠とする。KB 補助は meta 系のみ。
    reference_body = doc_body
    hist = ""
    if history:
        lines = []
        for m in history[-6:]:
            role = m.get("type") or m.get("role") or "user"
            content = (m.get("content") or "")[:200]
            lines.append(f"{role}: {content}")
        hist = "\n".join(lines)
    if intent in _DOC_REFERENCE_ONLY_INTENTS:
        from src.services.concierge_intent import is_legal_compliance_meta_question

        legal_q = intent == "doc_terms" and is_legal_compliance_meta_question(user_text)
        legal_extra = ""
        if legal_q:
            legal_extra = """
- 薬機法・景表法等について「問題ない」「合法」と断言しない
- 法令遵守条項および目的・免責条項に基づき、本サービスの位置づけ（OTC参考案内・診断処方なし・β版）を説明する
- 症状やお薬の相談を促す締めの文は付けない"""
        requirements = f"""【要件】
- 上記ドキュメントに書かれた内容のみに基づいて回答する（推測・補完しない）
- 回答は要点を5〜8項目の箇条書き（「・」1行1項目）にまとめる。全文の写し出しはしない
- ユーザーの質問に直接関係する要点を優先する
- ドキュメントにない事項は「ドキュメントに記載がありません」と明記する
- 連絡先・URL・禁止事項などはドキュメントの表記を変えず正確に伝える
- 詳細は画面右上の ℹ️（情報）から各種ドキュメントの全文を確認できる旨を最後に1文で案内する
- ドキュメント本文に無い免責・診断不可・相談促しなどの定型文は付けない{legal_extra}
"""
    elif intent == "doc_operator":
        requirements = f"""{get_policy_snippet()}

【要件】
- 上記ドキュメントに書かれた内容のみに基づいて回答する（推測・補完しない）
- 運営者の氏名・所属・学年・資格など個人を特定しうる属性は、ユーザーが直接尋ねても回答に含めない
- 「運営者は誰？」「大学はどこ？」などと聞かれた場合は、個人名や所属は開示せず、試験運用（β版）の個人開発であることと、ドキュメント記載の問い合わせ窓口（メール・不具合報告フォーム）を案内する
- ドキュメントにない事項は「ドキュメントに記載がありません」と明記する
- 連絡先・URL・メールアドレスはドキュメントの表記を変えず正確に伝える
- 箇条書きまたは短い段落で分かりやすく（Markdown は使わずプレーンテキスト）
- 医療診断・処方は行わない
- 最後に、症状やお薬の相談があれば具体的にお書きいただくよう1文で促す
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
{reference_body}

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
            max_tokens=550,
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


_DOC_OPERATOR_INTRO_FALLBACK = (
    "お問い合わせいただきありがとうございます。"
    "本ツールは、一般用医薬品の選び方を支援する研究・検証目的の β 版（試験運用）として、"
    "個人で開発・運営しています。"
    "プライバシー保護のため、運営者の氏名・所属など個人を特定しうる情報は"
    "チャット上ではお伝えしておりませんが、下記のメールまたは不具合報告フォームから"
    "いつでもご連絡いただけます。"
)


def generate_doc_operator_intro(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """お問い合わせカード上部用の短い LLM 導入文（URL はカード側に任せる）。"""
    title, doc_body = load_concierge_doc("doc_operator")
    hist = ""
    if history:
        lines = []
        for m in history[-6:]:
            role = m.get("type") or m.get("role") or "user"
            content = (m.get("content") or "")[:200]
            lines.append(f"{role}: {content}")
        hist = "\n".join(lines)
    requirements = f"""{get_policy_snippet()}

【要件】
- 上記ドキュメントに基づき、ユーザーの質問に直接答える **3〜5文** の導入文のみ書く
- **丁寧で温かみのある敬体**（「〜です／〜ます」）。事務的・断定的すぎる言い回しは避ける
- 冒頭で質問へのお礼（「お問い合わせありがとうございます」等）を述べる
- 試験運用（β版）の位置づけと、個人開発・運用であることをやさしく説明する
- 氏名・所属を開示しない理由は「プライバシー保護のため」等、利用者に配慮した表現で1文触れる
- 「運営者は誰？」「大学はどこ？」などは、個人名・所属はお伝えできない旨を丁寧に述べ、**直後の案内カード**に連絡先があることを促す
- **メールアドレス・URL・リンク・箇条書きは書かない**（直後のカードに記載される）
- Markdown は使わずプレーンテキスト
- 医療診断・処方は行わない
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
            "concierge_agent.doc_operator_intro",
            [
                {
                    "role": "system",
                    "content": (
                        "あなたは医薬品相談ツールの窓口担当です。"
                        "利用者が安心できるよう、丁寧で親しみやすい日本語で案内します。"
                        "与えられた公式ドキュメント以外の情報で回答してはいけません。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=320,
            temperature=0.35,
            session_id=session_id,
            allow_stream=False,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.warning("Concierge doc_operator intro LLM failed: %s", exc)
    return _DOC_OPERATOR_INTRO_FALLBACK


def build_doc_operator_payload(
    user_text: str,
    client: OpenAI,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> ResponsePayload:
    intro = generate_doc_operator_intro(
        client,
        user_text,
        session_id=session_id,
        history=history,
    )
    from src.services.status_diagnosis_builder import build_concierge_operator_status

    return {
        "content": format_concierge_operator_card(
            intro_text=intro,
            feedback_data=feedback_data,
        ),
        "content_format": "status_card",
        "line_flex": build_concierge_operator_line_flex(intro_text=intro),
        "concierge_intent": "doc_operator",
        "llm_used": True,
        "sage_diagnosis": build_concierge_operator_status(intro).to_client_dict(),
    }


_CHANGELOG_INTRO_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "最近のアップデートについて、利用者向けに短く親しみやすい導入文だけを書きます。"
    "プロンプト・要件・参照データの説明、内部用語、ファイルパスは出力に含めません。"
    "箇条書きは書きません（詳細は画面の別欄に表示されます）。"
)


def generate_changelog_intro_text(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, bool]:
    from src.content.changelog_digest import (
        changelog_fallback_intro,
        changelog_unavailable_user_message,
        format_build_meta_block,
        format_changelog_llm_reference,
        load_changelog_digest,
    )
    from src.utils.sage_message_plain import strip_concierge_prompt_leakage

    header_date, releases = load_changelog_digest(max_releases=4)
    if not releases:
        return changelog_unavailable_user_message(), False

    hist = ""
    if history:
        lines = []
        for m in history[-4:]:
            role = m.get("type") or m.get("role") or "user"
            content = (m.get("content") or "")[:160]
            lines.append(f"{role}: {content}")
        hist = "\n".join(lines)

    reference = "\n\n".join(
        [
            format_build_meta_block(),
            format_changelog_llm_reference(releases, header_date),
        ]
    )
    prompt = f"""【参照情報（事実のみ。ユーザーにそのまま見せない）】
{reference}

【会話履歴（参考）】
{hist or "（なし）"}

【ユーザーの質問】
{user_text}

【要件】
- 参照情報の事実のみに基づく（創作しない）
- **2〜3文**の自然な導入文のみ。敬体で柔らかく
- 箇条書き・「・」は使わない。具体的な変更の列挙はしない（カードで表示する）
- 「CHANGELOG」「要約」「intent」「ドキュメントに記載がありません」等のメタ表現は使わない
- 内部コード名（doc_changelog 等）やファイルパスは使わない
- 利用者が「最近何が変わったか」わかるトーンにする
"""
    try:
        resp = concierge_chat(
            client,
            "concierge_agent.doc_changelog_intro",
            [
                {"role": "system", "content": _CHANGELOG_INTRO_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.45,
            session_id=session_id,
            allow_stream=False,
        )
        text = strip_concierge_prompt_leakage(
            (resp.choices[0].message.content or "").strip()
        )
        if text:
            return text, True
    except Exception as exc:
        logger.warning("Concierge changelog intro LLM failed: %s", exc)

    return changelog_fallback_intro(header_date, releases), False


def build_changelog_payload(
    user_text: str,
    client: OpenAI,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> ResponsePayload:
    from src.content.changelog_digest import (
        build_changelog_ui_sections,
        changelog_doc_title,
        changelog_unavailable_user_message,
        format_changelog_deploy_subtitle,
        load_changelog_digest,
        wants_changelog_detail,
    )
    from src.services.status_diagnosis_builder import StatusSection, build_notice_status

    header_date, releases = load_changelog_digest(max_releases=4)
    fb = feedback_data if feedback_data is not None else _feedback_data(user_text, "doc_changelog")

    if not releases:
        intro = changelog_unavailable_user_message()
        diag = build_notice_status(
            intro,
            title=changelog_doc_title(),
            kind="concierge_doc_changelog",
            show_feedback=True,
            feedback_context=fb,
        )
        return {
            "content": intro,
            "content_format": "text",
            "concierge_intent": "doc_changelog",
            "llm_used": False,
            "sage_diagnosis": diag.to_client_dict(),
        }

    intro, llm_used = generate_changelog_intro_text(
        client,
        user_text,
        session_id=session_id,
        history=history,
    )
    detailed = wants_changelog_detail(user_text, history)
    section_specs = build_changelog_ui_sections(
        releases,
        detailed=detailed,
    )
    sections = [
        StatusSection(
            title=s["title"],
            items=s["items"],
            commit=str(s.get("commit") or ""),
        )
        for s in section_specs
        if s.get("title") and s.get("items")
    ]
    subtitle = format_changelog_deploy_subtitle(header_date)

    diag = build_notice_status(
        intro,
        title=changelog_doc_title(),
        subtitle=subtitle,
        hints=[],
        sections=sections,
        kind="concierge_doc_changelog",
        show_feedback=True,
        feedback_context=fb,
    )
    plain_body = intro
    if sections:
        plain_body += "\n\n" + "\n\n".join(
            f"{s.title}\n" + "\n".join(f"・{item}" for item in s.items)
            for s in sections
        )
    return {
        "content": format_dynamic_concierge_meta_card(
            title=changelog_doc_title(),
            body_text=plain_body,
            subtitle=subtitle,
            hints=[],
            feedback_data=fb,
            intent="doc_changelog",
        ),
        "content_format": "status_card",
        "line_flex": build_dynamic_concierge_line_flex(
            title=changelog_doc_title(),
            body_text=plain_body,
            subtitle=subtitle,
            hints=[],
            intent="doc_changelog",
        ),
        "concierge_intent": "doc_changelog",
        "llm_used": llm_used,
        "sage_diagnosis": diag.to_client_dict(),
    }


_GREETING_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "薬局の相談窓口のスタッフのように、会話の流れを読んで自然な続きの返答をします。"
    "毎回言い回しを変え、説教・突き放し・皮肉にはなりません。"
)

_GREETING_PROMPT_REQUIREMENTS = """【方針】
- 【ユーザーの挨拶】の言い回し・丁寧さ・温度感にミラーリングして返す（例:「やあ」→「やあ！」、「おはようございます」→丁寧な朝の挨拶）
- 挑発的・失礼な短い呼びかけ（おい、ねえ、もしもし等）は口調・言葉を真似せず、柔らかい丁寧語で落ち着いて受け止める。罵倒は繰り返さない
- 会話履歴と文脈を踏まえ、状況に合った自然な日本語で返す
- 2〜3文・60〜120文字程度（1文だけの極端に短い返答は避ける）
- 直前の bot 返答と同じ言い回し・同じ構成は使わない
- 焦りや呼びかけには落ち着いて応じる
- 医薬品は「市販薬」と表記。「OTC」は使わない
- 初回接触では市販薬相談窓口であることと相談例を簡潔に含める。継続の呼びかけでは窓口説明を繰り返さない
- 内部ラベル（[ステータス]、[Q&A]、bot[...]、HTML/Markdown）を出力に含めない"""

_THANKS_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "感謝の言葉にはユーザーの口調・丁寧さに合わせて自然に返し、毎回言い回しを変えます。"
    "説教・突き放し・皮肉にはなりません。"
)

_THANKS_PROMPT_REQUIREMENTS = """【方針】
- 【ユーザーの感謝】の言い回し・丁寧さにミラーリングして返す（例:「ありがとう」→「どういたしまして」、「ありがとうございます」→「こちらこそありがとうございます」）
- 会話履歴と文脈を踏まえ、直前の相談内容があれば1文だけ自然に触れてよい
- 1〜2文・40〜100文字程度
- 直前の bot 返答と同じ言い回し・同じ構成は使わない
- 医薬品は「市販薬」と表記。「OTC」は使わない
- ほかに相談があれば自然に促す（毎回同じ定型句にしない）"""

_GREETING_MIN_CHARS_FIRST = 60
_GREETING_MIN_CHARS_CONTINUED = 60
_GREETING_MAX_CHARS = 130
_GREETING_LLM_MAX_TOKENS = 512
_GREETING_MAX_LLM_ATTEMPTS = 3

_GREETING_SANITIZE_OPENINGS = (
    "お声がけありがとうございます。",
    "呼びかけありがとうございます。",
    "承知しました。",
)

_CHITCHAT_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "会話履歴と文脈メモを踏まえ、雑談にも自然に乗りつつ毎回言い回しを変えます。"
    "ユーザーの温度感にミラーリングで合わせつつ、"
    "苛立ちがあれば寄り添い・傾聴を優先します。説教・突き放し・皮肉にはなりません。"
)

_CHITCHAT_PROMPT_REQUIREMENTS = """【優先順位】
1. 相手を煽らない・責めない
2. 会話履歴・文脈に沿った自然な続き
3. ミラーリング（温度感）。挑発的・失礼な呼びかけ（おい、ねえ等）は口調を真似しない。失礼語は繰り返さない
4. 苛立ちがあれば寄り添い・傾聴を優先

【口調】
- ユーザーの温度感にミラーリングで合わせつつ、柔らかい丁寧語で返す
- 直前の bot 返答と同じフレーズは使わない
- 苛立ち・強い口調があっても責めず、寄り添い・傾聴で受け止めてから穏やかに話を戻す
- 禁止:「やわらかく書いてください」「短く書いてください」「具体的に書いてください」「〜ですので、〜」

【会話の継続】
- 【会話履歴】と【会話の文脈】を読み、前の話題に自然につなげる
- これまでに触れた症状・相談があれば、無理なく1文だけ参照してよい

【内容・長さ】
- 2〜3文、目安80〜160文字（1文だけの極端に短い返答は避ける）
- 医薬品は「市販薬」と表記。「OTC」は使わない
- 医療診断・処方はしない
- お薬の相談へ戻すときは「お気軽にお聞かせください」等の自然な言い回しで促す"""

_SHORT_CALLOUT_EXACT = frozenset({
    "おい",
    "ねえ",
    "ねぇ",
    "もしもし",
    "あの",
    "なあ",
    "なぁ",
})

_RUDE_MIRROR_PREFIXES = ("おい", "ねえ", "ねぇ", "もしもし", "ふざけんな")

# 挑発的呼びかけの書き出し除去用（「おい、」だけでなく「おい！」も対象）
_CALLOUT_OPENING_PUNCT = r"[、，,。．.\s!！?？…~～]+"

# 挑発的呼びかけへのカジュアル返し（元気かい？・教えてね 等）
_CASUAL_MIRROR_TONE_RE = re.compile(
    r"(元気かい|教えてね|だよね|じゃん|ってば|聞いてよ|どうしたの)"
)

_SHORT_CALLOUT_FALLBACK = (
    "お声がけありがとうございます。"
    "何かお困りのことがあれば、お気軽にお聞かせください。"
)

_SHORT_CALLOUT_FIRST_POOL = [
    (
        "お声がけありがとうございます。"
        "こちらは市販薬の相談窓口です。頭痛やのどの痛み、鼻水など、お気軽にご相談ください。"
    ),
    (
        "こんにちは。市販薬の相談をお手伝いします。"
        "頭痛・のどの痛み・胃の不調など、気になる症状をそのまま教えてください。"
    ),
]

_SHORT_CALLOUT_CONTINUED_POOL = [
    (
        "お声がけありがとうございます。"
        "何かお困りのことがあれば、症状やいつからかを短くでもお聞かせください。"
    ),
    (
        "呼びかけありがとうございます。"
        "続きのご相談があれば、気になる点をそのままお書きください。"
    ),
    (
        "お待たせしました。"
        "お体のことで気になる点があれば、市販薬の候補を一緒に見ていきます。"
    ),
    (
        "承知しました。"
        "ほかにご質問や気になる症状があれば、お気軽にお聞かせください。"
    ),
]


def _normalize_callout_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def is_short_impatient_callout(text: str) -> bool:
    """焦り・呼びかけの短い入力（失礼語ミラーリング対象外）。"""
    return _normalize_callout_text(text) in _SHORT_CALLOUT_EXACT


def build_short_callout_greeting_text(*, is_first: bool, exclude: str = "") -> str:
    """短い呼びかけの LLM 失敗時・重複回避フォールバック。"""
    pool = list(_SHORT_CALLOUT_FIRST_POOL if is_first else _SHORT_CALLOUT_CONTINUED_POOL)
    random.shuffle(pool)
    for candidate in pool:
        if exclude and greeting_responses_too_similar(candidate, exclude):
            continue
        return candidate
    return pool[0] if pool else _SHORT_CALLOUT_FALLBACK


def _normalize_greeting_compare_text(text: str) -> str:
    return re.sub(r"[\s　、。,.!?！？]", "", (text or "").strip())


def greeting_response_too_short(text: str, *, is_first: bool) -> bool:
    minimum = _GREETING_MIN_CHARS_FIRST if is_first else _GREETING_MIN_CHARS_CONTINUED
    return len((text or "").strip()) < minimum


def greeting_response_too_long(text: str) -> bool:
    return len((text or "").strip()) > _GREETING_MAX_CHARS


def _greeting_opening_signature(text: str) -> str:
    first = re.split(r"[。.!?！？\n]", (text or "").strip(), maxsplit=1)[0]
    return _normalize_greeting_compare_text(first)[:16]


def _pick_sanitize_opening(*, avoid: str = "") -> str:
    avoid_sig = _greeting_opening_signature(avoid)
    candidates = list(_GREETING_SANITIZE_OPENINGS)
    random.shuffle(candidates)
    for opening in candidates:
        if avoid_sig and _greeting_opening_signature(opening) == avoid_sig:
            continue
        return opening
    return candidates[0]


def is_provocative_short_callout(user_text: str) -> bool:
    """おい・ねえ等、口調ミラーリングを避ける短い呼びかけ。"""
    return _normalize_callout_text(user_text) in frozenset(_RUDE_MIRROR_PREFIXES)


def greeting_response_mirrors_provocative_callout(text: str, user_text: str) -> bool:
    """挑発的・失礼な短い呼びかけの口調を bot が繰り返していないか。"""
    if not is_short_impatient_callout(user_text):
        return False
    word = _normalize_callout_text(user_text)
    if not word:
        return False
    stripped = (text or "").strip()
    if not stripped:
        return False
    if re.match(
        rf"^{re.escape(word)}{_CALLOUT_OPENING_PUNCT}",
        _normalize_callout_text(stripped),
    ):
        return True
    opening = _greeting_opening_signature(stripped)
    if opening and opening == _normalize_greeting_compare_text(word):
        return True
    if is_provocative_short_callout(user_text) and _CASUAL_MIRROR_TONE_RE.search(
        stripped
    ):
        return True
    return False


def _starts_with_safe_callout_opening(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    for opening in _GREETING_SANITIZE_OPENINGS:
        if t.startswith(opening):
            return True
    for prefix in ("こんにちは", "おはよう", "こんばんは", "はじめまして", "初めまして"):
        if t.startswith(prefix):
            return True
    return False


def _strip_provocative_mirror_opening(result: str, user_text: str) -> str:
    """返答先頭の挑発的ミラーリング（おい！ 等）を除去する。"""
    if not is_short_impatient_callout(user_text):
        return result
    word = _normalize_callout_text(user_text)
    stripped = (result or "").strip()
    if word:
        stripped = re.sub(
            rf"^{re.escape(word)}{_CALLOUT_OPENING_PUNCT}?",
            "",
            stripped,
            count=1,
        )
    for prefix in _RUDE_MIRROR_PREFIXES:
        stripped = re.sub(
            rf"^{re.escape(prefix)}{_CALLOUT_OPENING_PUNCT}?",
            "",
            stripped,
            count=1,
        )
    return stripped.strip()


def greeting_response_needs_retry(
    text: str,
    *,
    is_first: bool,
    last_bot: str = "",
    user_text: str = "",
) -> bool:
    if not (text or "").strip():
        return True
    if greeting_response_too_short(text, is_first=is_first):
        return True
    if greeting_response_too_long(text):
        return True
    if last_bot and greeting_responses_too_similar(text, last_bot):
        return True
    if user_text and greeting_response_mirrors_provocative_callout(text, user_text):
        return True
    return False


def _greeting_service_context_block() -> str:
    """挨拶 LLM 用: ポリシーと本ツールの立場・制限（SSOT）。"""
    identity = get_service_identity_block()
    parts = [get_policy_snippet()]
    if identity:
        parts.append(f"【本ツールについて（遵守）】\n{identity}")
    return "\n\n".join(parts)


def greeting_responses_too_similar(a: str, b: str) -> bool:
    """挨拶返答が直前と実質同じか。"""
    na = _normalize_greeting_compare_text(a)
    nb = _normalize_greeting_compare_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 12 and shorter in longer:
        return True
    sig_a = _greeting_opening_signature(a)
    sig_b = _greeting_opening_signature(b)
    if sig_a and sig_b and len(sig_a) >= 8 and sig_a == sig_b:
        return True
    return False


def sanitize_greeting_response(
    text: str,
    user_text: str,
    *,
    avoid_opening: str = "",
) -> str:
    """LLM 挨拶返答の最小限の後処理（失礼語ミラーリング等）。"""
    result = (text or "").strip()
    if not result:
        return result

    replacement_opening = _pick_sanitize_opening(avoid=avoid_opening)
    if is_short_impatient_callout(user_text):
        result = _strip_provocative_mirror_opening(result, user_text)

    result = re.sub(
        r"はい、こちらにいます[。.]?\s*",
        replacement_opening,
        result,
    )
    if is_short_impatient_callout(user_text):
        result = re.sub(
            r"^はい、どうぞ[、，,。.]?\s*",
            replacement_opening,
            result,
        )
        if result and not _starts_with_safe_callout_opening(result):
            result = replacement_opening + result

    if is_short_impatient_callout(user_text) and not result:
        result = _SHORT_CALLOUT_FALLBACK
    from src.utils.sage_message_plain import strip_internal_llm_prefix

    return strip_internal_llm_prefix(result.strip())


def infer_is_first_greeting_contact(
    history: Optional[List[Dict[str, str]]],
    *,
    user_text: str = "",
) -> bool:
    """挨拶返答用: これまでに Concierge/挨拶 bot 応答がなければ初回接触。"""
    prior = _prior_history_for_prompt(history, user_text)
    if _extract_substantive_user_topics(prior):
        return False
    msgs = list(prior or [])
    if not msgs:
        return True
    for msg in reversed(msgs):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        if msg.get("greeting") or msg.get("concierge"):
            return False
        diag = msg.get("diagnosis") or {}
        kind = str(diag.get("kind") or "")
        if kind.startswith("concierge_"):
            return False
    return True


def _invoke_greeting_llm(
    client: OpenAI,
    prompt: str,
    *,
    session_id: Optional[str],
    temperature: float,
) -> str:
    from src.core.llm_client import chat_completion_create, extract_completion_text

    resp = chat_completion_create(
        client,
        model_role="concierge_greeting",
        path="concierge_agent.greeting",
        messages=[
            {"role": "system", "content": _GREETING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=_GREETING_LLM_MAX_TOKENS,
        temperature=temperature,
    )
    return extract_completion_text(resp)


def _greeting_retry_hint(
    *,
    attempt: int,
    is_first: bool,
    last_bot: str,
    prior_text: str,
    user_text: str = "",
) -> str:
    hints: List[str] = []
    if prior_text and greeting_response_too_short(prior_text, is_first=is_first):
        hints.append(
            "【重要】前の返答が短すぎました。必ず60〜120文字・2〜3文で書き直してください。"
        )
    if prior_text and greeting_response_too_long(prior_text):
        hints.append(
            "【重要】前の返答が長すぎました。120文字以内・2〜3文に収めて書き直してください。"
        )
    if prior_text and last_bot and greeting_responses_too_similar(prior_text, last_bot):
        hints.append(
            "【重要】直前の bot 返答と同じ書き出し・構成は不可。別の自然な表現で書き直してください。"
        )
    if prior_text and user_text and greeting_response_mirrors_provocative_callout(
        prior_text, user_text
    ):
        hints.append(
            "【重要】挑発的・失礼な呼びかけ（おい、ねえ等）の口調は真似しないでください。"
            "「おい！」などで書き出さず、柔らかい丁寧語で受け止めて書き直してください。"
        )
    if attempt >= 2:
        hints.append(
            "【重要】毎回書き出しを変え、具体例を1つ入れて、読みやすい2〜3文にしてください。"
        )
    if is_first and attempt >= 1:
        hints.append(
            "【重要】初回接触です。市販薬相談窓口であることと、相談例（頭痛・のどの痛み等）を含めてください。"
        )
    return "\n".join(hints)


def _build_greeting_user_prompt(
    *,
    hist: str,
    context: str,
    first_label: str,
    contact_block: str,
    user_text: str,
    variation_hint: str = "",
) -> str:
    variation_section = f"\n{variation_hint}\n" if variation_hint else ""
    return f"""{_greeting_service_context_block()}

【会話履歴（参考）】
{hist}

【会話の文脈】
{context}

【初回接触】
{first_label}

{contact_block}
{variation_section}
【ユーザーの挨拶】
{user_text}

【要件】
{_GREETING_PROMPT_REQUIREMENTS}
"""


def generate_greeting_text(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, bool]:
    """挨拶返答。既定は LLM。失敗時のみ build_greeting_text にフォールバック。"""
    hist = format_concierge_history_block(history, user_text)
    context = format_concierge_context_block(history, user_text, mode="greeting")
    is_first = infer_is_first_greeting_contact(history, user_text=user_text)
    first_label = "はい" if is_first else "いいえ"
    rounds = count_same_greeting_exchange_rounds(history, user_text)
    prior = _prior_history_for_prompt(history, user_text)
    last_bot = _last_bot_reply_snippet(prior, greeting_only=True)

    if is_first:
        contact_block = (
            "【今回の要点】\n"
            "- 挨拶への返答、市販薬相談窓口であること、相談例（頭痛・のどの痛み等）を含める\n"
            "- 2〜3文・60〜120文字程度"
        )
    else:
        contact_block = (
            "【今回の要点】\n"
            "- 窓口説明は繰り返さず、会話の続きとして受け止める\n"
            "- 2文・60〜120文字程度"
        )
    if rounds >= 2:
        contact_block += (
            f"\n- 同じ入力「{user_text.strip()}」の {rounds} 回目。"
            "直前の bot 返答と異なる言い回しにする"
        )

    temperature = min(0.62 + (rounds - 1) * 0.08, 0.86)
    try:
        best_text = ""
        prior_text = ""
        for attempt in range(_GREETING_MAX_LLM_ATTEMPTS):
            variation_hint = _greeting_retry_hint(
                attempt=attempt,
                is_first=is_first,
                last_bot=last_bot or "",
                prior_text=prior_text,
                user_text=user_text,
            )
            prompt = _build_greeting_user_prompt(
                hist=hist,
                context=context,
                first_label=first_label,
                contact_block=contact_block,
                user_text=user_text,
                variation_hint=variation_hint,
            )
            attempt_temp = min(temperature + attempt * 0.1, 0.95)
            raw = _invoke_greeting_llm(
                client,
                prompt,
                session_id=session_id,
                temperature=attempt_temp,
            )
            text = sanitize_greeting_response(
                raw,
                user_text,
                avoid_opening=last_bot or best_text,
            )
            prior_text = text
            if text and len(text) > len(best_text):
                best_text = text
            if text and not greeting_response_needs_retry(
                text,
                is_first=is_first,
                last_bot=last_bot or "",
                user_text=user_text,
            ):
                return text, True

        if best_text and not greeting_response_needs_retry(
            best_text,
            is_first=is_first,
            last_bot=last_bot or "",
            user_text=user_text,
        ):
            return best_text, True

        if is_short_impatient_callout(user_text):
            alt = build_short_callout_greeting_text(
                is_first=is_first,
                exclude=last_bot or best_text,
            )
            return sanitize_greeting_response(
                alt,
                user_text,
                avoid_opening=last_bot or "",
            ), False
        if best_text and not greeting_response_mirrors_provocative_callout(
            best_text, user_text
        ):
            return best_text, True
        if is_provocative_short_callout(user_text):
            alt = build_short_callout_greeting_text(
                is_first=is_first,
                exclude=last_bot or best_text,
            )
            return sanitize_greeting_response(
                alt,
                user_text,
                avoid_opening=last_bot or "",
            ), False
    except Exception as exc:
        logger.warning("Concierge greeting LLM failed: %s", exc)
    if is_short_impatient_callout(user_text):
        fallback = build_short_callout_greeting_text(
            is_first=is_first, exclude=last_bot or ""
        )
    else:
        fallback = build_greeting_text(user_text)
    return sanitize_greeting_response(
        fallback,
        user_text,
        avoid_opening=last_bot or "",
    ), False


def generate_thanks_text(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, bool]:
    """感謝返答。合成テキスト（スタンプ解釈含む）の口調を踏まえ LLM で返す。"""
    hist = format_concierge_history_block(history, user_text)
    context = format_concierge_context_block(history, user_text, mode="thanks")
    prompt = f"""{get_policy_snippet()}

【会話履歴（参考）】
{hist}

【会話の文脈】
{context}

【ユーザーの感謝】
{user_text}

【要件】
{_THANKS_PROMPT_REQUIREMENTS}
"""
    try:
        resp = concierge_chat(
            client,
            "concierge_agent.thanks",
            [
                {"role": "system", "content": _THANKS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=180,
            temperature=0.58,
            session_id=session_id,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            from src.utils.sage_message_plain import strip_internal_llm_prefix

            return strip_internal_llm_prefix(text), True
    except Exception as exc:
        logger.warning("Concierge thanks LLM failed: %s", exc)
    return build_thanks_text(user_text), False


_META_LLM_INTENTS = frozenset({"capabilities", "architecture", "app_about"})

_META_CARD_TITLES: dict[str, str] = {
    "capabilities": "できること",
    "architecture": "仕組み・技術",
    "app_about": "このツールについて",
    "doc_app_overview": "アプリ概要",
    "doc_changelog": "更新履歴",
    "doc_privacy": "プライバシー",
    "doc_terms": "利用規約・免責",
    "doc_consultation": "相談先・窓口",
}

# メタ質問カードでは「次に試すこと」ヒントを出さない（フィードバックのみ）
_META_CARD_HINTS: dict[str, list[str]] = {
    "capabilities": [],
    "architecture": [],
    "app_about": [],
    "doc_app_overview": [],
    "doc_changelog": [],
    "doc_privacy": [],
    "doc_terms": [],
    "doc_consultation": [],
}

_META_STATIC_LINE_FLEX = {
    "capabilities": build_concierge_capabilities_line_flex,
    "architecture": build_concierge_architecture_line_flex,
    "app_about": build_concierge_app_about_line_flex,
}

_META_INTENT_REQUIREMENTS = {
    "capabilities": """【要件】
- このツールでできること・できないことを、ユーザーの質問に直接答える
- 会話履歴に既に触れた内容は繰り返さず、今回の質問に必要な範囲だけ補足する
- 2〜5文・プレーンテキスト（Markdown不可）
- 話題が変わるときは空行を1行入れる
- 箇条書きにする場合は「・」で1項目1行
- 処方・診断は行わない旨を必要なときだけ簡潔に触れる
- 内部ラベル（[ステータス]、[Q&A]、bot[...]、HTML/Markdown）を出力に含めない""",
    "architecture": """【要件】
- ユーザーの質問の主題（マルチエージェントの意味、技術構成、仕組み、誰が答えたか等）に直接答える
- マルチエージェント＝複数の専門担当が連携する仕組みであることを、聞かれたときは中心に説明する
- 市販薬候補がルールベースで選ばれることは、質問に関係するときだけ簡潔に触れる
- 技術スタック・開発環境・デプロイ構成の質問には、参照情報の技術一覧に基づいて答える
- 会話履歴（直前の説明など）を踏まえ、同じ説明の繰り返しを避ける
- 2〜6文・プレーンテキスト（Markdown不可）
- 話題が変わるときは空行を1行入れる
- エージェントの役割一覧は本文に「・」箇条書きで書かない（前置きの説明のみ）
- 内部ラベル（[ステータス]、[Q&A]、bot[...]、HTML/Markdown）を出力に含めない""",
    "app_about": """【要件】
- このチャットが何であるか・何でないか（病院・診察・処方ではない）を、ユーザーの質問形式に合わせて答える
- 「今誰が答えているか」は app_about ではなく architecture の話題 — その場合は AI 返信と役割分担を答える
- yes/no 確認には医療機関のように「はい」と答えず、本ツールの性質を短く説明する
- 会話履歴を踏まえ、既出の窓口説明を丸ごと繰り返さない
- 2〜5文・プレーンテキスト（Markdown不可）
- 話題が変わるときは空行を1行入れる""",
}


def _meta_reference_block(intent: str) -> str:
    from src.content.concierge_knowledge import (
        get_agents,
        get_capabilities,
        get_limitations,
        get_service_identity_block,
        load_concierge_knowledge,
    )

    kb = load_concierge_knowledge()
    app = kb.get("app") or {}
    lines = [get_service_identity_block(), ""]
    if intent == "capabilities":
        lines.append("【できること（参照）】")
        for cap in get_capabilities():
            lines.append(f"- {cap.get('title')}: {cap.get('body')}")
    elif intent == "architecture":
        lines.append("【エージェント構成（参照）】")
        for agent in get_agents():
            lines.append(
                f"- {agent.get('name_ja')}: {agent.get('role_one_liner')}"
            )
        try:
            from src.content.about_i18n import get_about_bundle

            tech = get_about_bundle("index", "ja")
            bullets = tech.get("tech_bullets") or []
            if bullets:
                lines.append("")
                lines.append("【技術スタック（参照）】")
                for item in bullets:
                    lines.append(f"- {item}")
        except Exception:
            pass

        # Phase 3 (p3-concierge, 前半): API/SSE/rule_based の技術詳細は
        # ROUTING_CONCIERGE_INTENT ON かつ development ランタイム限定で追加開示する
        # （production は上記の既存抽象コンテンツのみで変更なし）。
        try:
            from config.llm_flags import is_concierge_intent_routing_enabled

            if is_concierge_intent_routing_enabled():
                from config.app_config import is_development_runtime

                if is_development_runtime():
                    from src.content.concierge_knowledge import get_technical_details

                    details = get_technical_details()
                    ordered_keys = (
                        "api_description",
                        "sse_description",
                        "rule_based_description",
                    )
                    detail_lines = [details[k] for k in ordered_keys if details.get(k)]
                    if detail_lines:
                        lines.append("")
                        lines.append("【技術詳細（開発環境限定・参照）】")
                        for item in detail_lines:
                            lines.append(f"- {item}")
        except Exception:
            pass
    else:
        lines.append(f"【ツール概要（参照）】")
        lines.append(f"名称: {app.get('name')}")
        lines.append(f"目的: {app.get('purpose')}")
        lines.append(f"対象: {app.get('audience')}")
    lines.append("")
    lines.append("【制限（参照）】")
    for lim in get_limitations():
        lines.append(f"- {lim}")
    return "\n".join(lines)


def _meta_requirements_for(user_text: str, intent: str) -> str:
    """intent 共通要件に、今回の質問タイプ限定の追記を付ける。"""
    from src.services.concierge_agent_history import (
        is_agent_roster_question,
        is_multi_agent_concept_question,
        is_who_is_answering_question,
    )

    base = _META_INTENT_REQUIREMENTS[intent]
    if intent != "architecture":
        return base
    if is_who_is_answering_question(user_text):
        return (
            base
            + """

【今回の質問に限定】
- 「誰が答えているか」「誰が回答したか」への直接回答とする
- 会話履歴の【直前の返信担当】を第一文で明示する（例: 「いまの案内は ConciergeAgent が担当しています」）
- 続けて、このチャットの返信文はAIが生成していること、市販薬候補選定はルールベースであることを短く述べる"""
        )
    if is_agent_roster_question(user_text):
        return (
            base
            + """

【今回の質問に限定】
- マルチエージェントの意味と、このサービスでの役割分担・構成を、ユーザーの聞き方に合わせて説明する
- 本文は導入2〜4文にとどめる（エージェント一覧はシステムが別表示するため本文に列挙しない）
- 「いま誰が答えているか」「ConciergeAgentが担当」など担当宣言から答えを始めない
- 会話履歴を踏まえ、既出説明の繰り返しや長いフロー例（「たとえば A→B→C」）は避ける
- 市販薬がルールベースで選ばれることは1文だけ触れてよい"""
        )
    if is_multi_agent_concept_question(user_text):
        return (
            base
            + """

【今回の質問に限定】
- マルチエージェントの意味と、このサービスでの役割分担を説明する
- 「いま誰が答えているか」「ConciergeAgentが担当」など担当宣言から答えを始めない
- 一般論＋このツールでの例（振り分け→専門担当）を簡潔に述べる"""
        )
    return (
        base
        + """

【今回の質問に限定】
- 担当エージェント名や「いま誰が答えているか」から答えを始めない（ユーザーが明示的に聞いていない限り）"""
    )


def _invoke_meta_concierge_llm(
    client: OpenAI,
    user_text: str,
    intent: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    hist = format_concierge_history_block(history, user_text)
    context = format_meta_concierge_context_block(history, user_text, intent=intent)
    requirements = _meta_requirements_for(user_text, intent)
    reference = _meta_reference_block(intent)
    from src.services.bedrock_kb_retrieve import augment_reference_with_kb

    reference = augment_reference_with_kb(user_text, reference)
    prompt = f"""{get_policy_snippet()}

{reference}

【会話履歴（参考）】
{hist}

【会話の文脈】
{context}

【ユーザーの質問】
{user_text}

{requirements}
"""
    resp = concierge_chat(
        client,
        f"concierge_agent.meta_{intent}",
        [
            {
                "role": "system",
                "content": (
                    "あなたは市販薬相談ツールの案内役です。"
                    "参照情報と会話履歴に基づき、正確で自然な続きの回答をします。"
                    "薬名の創作や処方の約束はしません。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=520,
        temperature=0.35,
        session_id=session_id,
    )
    from src.utils.sage_message_plain import strip_internal_llm_prefix

    return strip_internal_llm_prefix((resp.choices[0].message.content or "").strip())


def _meta_concierge_fallback_card(user_text: str, intent: str) -> str:
    fb = _feedback_data(user_text, intent)
    if intent == "capabilities":
        return format_concierge_capabilities_card(feedback_data=fb)
    if intent == "architecture":
        return format_concierge_architecture_card(feedback_data=fb)
    return format_concierge_app_about_card(feedback_data=fb)


def generate_meta_concierge_text(
    client: OpenAI,
    user_text: str,
    intent: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, bool]:
    """capabilities / architecture / app_about を履歴付き LLM で回答する。"""
    if intent not in _META_LLM_INTENTS:
        raise ValueError(f"unsupported meta intent: {intent}")

    for attempt in range(2):
        try:
            text = _invoke_meta_concierge_llm(
                client,
                user_text,
                intent,
                session_id=session_id,
                history=history,
            )
            if text:
                if intent == "architecture" and _prior_topic_mentions_tech_stack(
                    history, user_text
                ) and not _TECH_STACK_TOPIC_RE.search(text):
                    text = _append_tech_stack_reminder(text)
                return text, True
            logger.warning(
                "Concierge meta LLM empty (%s), attempt=%s",
                intent,
                attempt + 1,
            )
        except Exception as exc:
            logger.warning(
                "Concierge meta LLM failed (%s), attempt=%s: %s",
                intent,
                attempt + 1,
                exc,
            )

    return _meta_concierge_fallback_card(user_text, intent), False


def _assemble_dynamic_concierge_payload(
    *,
    intent: str,
    user_text: str,
    body_text: str,
    llm_used: bool,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> ResponsePayload:
    """
    メタ質問・ドキュメント案内など、LLM 動的本文を Web カード + LINE Flex で返す。
    LLM 失敗時は静的カード（intent ごとのフォールバック HTML）を使う。
    """
    from src.services.status_diagnosis_builder import build_notice_status

    title = _META_CARD_TITLES.get(intent, "ご案内")
    hints = _META_CARD_HINTS.get(intent, [])
    kind = f"concierge_{intent}"
    fb = feedback_data if feedback_data is not None else _feedback_data(user_text, intent)

    if llm_used:
        from src.services.concierge_agent_history import is_agent_roster_question

        plain = (body_text or "").strip()
        include_roster = (
            intent == "architecture" and is_agent_roster_question(user_text)
        )
        from src.services.concierge_templates import merge_agent_roster_section

        display_message, section_specs = structure_concierge_meta_display(intent, plain)
        if include_roster:
            section_specs = merge_agent_roster_section(section_specs)
        from src.services.status_diagnosis_builder import StatusSection

        sections = [
            StatusSection(title=s["title"], items=s["items"])
            for s in section_specs
            if s.get("title") and s.get("items")
        ]
        return {
            "content": format_dynamic_concierge_meta_card(
                title=title,
                body_text=plain,
                hints=hints,
                feedback_data=fb,
                intent=intent,
                include_agent_roster=include_roster,
            ),
            "content_format": "status_card",
            "line_flex": build_dynamic_concierge_line_flex(
                title=title,
                body_text=body_text,
                hints=hints,
                intent=intent,
                include_agent_roster=include_roster,
            ),
            "concierge_intent": intent,
            "llm_used": True,
            "sage_diagnosis": build_notice_status(
                display_message,
                title=title,
                hints=hints,
                sections=sections,
                kind=kind,
                show_feedback=True,
                feedback_context=fb,
            ).to_client_dict(),
        }

    static_html = (body_text or "").strip()
    line_flex_builder = _META_STATIC_LINE_FLEX.get(intent)
    line_flex = line_flex_builder() if line_flex_builder else build_dynamic_concierge_line_flex(
        title=title,
        body_text=html_to_plain_from_card(static_html) if "chat-status-card" in static_html else static_html,
        hints=hints,
    )
    plain_message = (
        html_to_plain_from_card(static_html)
        if "chat-status-card" in static_html
        else static_html
    )
    return {
        "content": static_html,
        "content_format": "status_card",
        "line_flex": line_flex,
        "concierge_intent": intent,
        "llm_used": False,
        "sage_diagnosis": build_notice_status(
            plain_message,
            title=title,
            hints=hints,
            kind=kind,
            show_feedback=True,
            feedback_context=fb,
        ).to_client_dict(),
    }


def html_to_plain_from_card(html_content: str) -> str:
    from src.handlers.line.flex_messages import html_to_plain_text

    return html_to_plain_text(html_content)


def generate_chitchat_text(
    client: OpenAI,
    user_text: str,
    *,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    from src.services.medical_examination_request import (
        resolve_medical_examination_request_type,
    )
    from src.services.counseling.counseling_templates import (
        generate_medical_examination_boundary_message,
    )

    if resolve_medical_examination_request_type(user_text):
        return generate_medical_examination_boundary_message()

    hist = format_concierge_history_block(history, user_text)
    context = format_concierge_context_block(history, user_text, mode="chitchat")
    prompt = f"""{get_policy_snippet()}

【会話履歴（参考）】
{hist}

【会話の文脈】
{context}

【ユーザーの発言】
{user_text}

【要件】
{_CHITCHAT_PROMPT_REQUIREMENTS}
"""
    try:
        from src.utils.sage_message_plain import strip_internal_llm_prefix

        resp = concierge_chat(
            client,
            "concierge_agent.chitchat",
            [
                {
                    "role": "system",
                    "content": _CHITCHAT_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=280,
            temperature=0.62,
            session_id=session_id,
        )
        return strip_internal_llm_prefix((resp.choices[0].message.content or "").strip())
    except Exception as exc:
        logger.warning("Concierge chitchat LLM failed: %s", exc)
        return (
            "お話ありがとうございます。こちらは市販薬の相談窓口です。"
            "お体の不調やお薬の選び方でお困りのことがあれば、ゆっくりお聞かせください。"
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
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text, greeting_llm_used = generate_greeting_text(
            client, user_text, session_id=session_id, history=history
        )
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "greeting": True,
            "llm_used": greeting_llm_used,
            "sage_diagnosis": build_concierge_text_status(
                text, title="ご挨拶", kind="concierge_greeting"
            ).to_client_dict(),
        }
    if intent == "thanks":
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text, thanks_llm_used = generate_thanks_text(
            client, user_text, session_id=session_id, history=history
        )
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": thanks_llm_used,
            "sage_diagnosis": build_concierge_text_status(
                text, title="お礼", kind="concierge_thanks"
            ).to_client_dict(),
        }
    if intent == "redirect":
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text = _resolve_redirect_text(user_text, history)
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_text_status(
                text, title="ご案内", kind="concierge_redirect"
            ).to_client_dict(),
        }
    if intent in _META_LLM_INTENTS:
        text, meta_llm_used = generate_meta_concierge_text(
            client,
            user_text,
            intent,
            session_id=session_id,
            history=history,
        )
        return _assemble_dynamic_concierge_payload(
            intent=intent,
            user_text=user_text,
            body_text=text,
            llm_used=meta_llm_used,
            feedback_data=fb,
        )
    if intent == "doc_operator":
        return build_doc_operator_payload(
            user_text,
            client,
            session_id=session_id,
            history=history,
            feedback_data=fb,
        )
    if intent == "doc_changelog":
        return build_changelog_payload(
            user_text,
            client,
            session_id=session_id,
            history=history,
            feedback_data=fb,
        )
    if intent in DOC_CONCIERGE_INTENTS:
        text = generate_doc_answer_text(
            client,
            user_text,
            intent,
            session_id=session_id,
            history=history,
        )
        return _assemble_dynamic_concierge_payload(
            intent=intent,
            user_text=user_text,
            body_text=text,
            llm_used=True,
            feedback_data=fb,
        )
    if intent == "chitchat":
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text = generate_chitchat_text(
            client, user_text, session_id=session_id, history=history
        )
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": True,
            "sage_diagnosis": build_concierge_text_status(
                text, title="お話", kind="concierge_chitchat"
            ).to_client_dict(),
        }
    if intent == "medical_handoff":
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text = get_handoff_intro_physical()
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "concierge_handoff_to": "physical",
            "llm_used": False,
            "sage_diagnosis": build_concierge_text_status(
                text,
                title="症状のご相談へ",
                kind="concierge_medical_handoff",
            ).to_client_dict(),
        }
    from src.services.status_diagnosis_builder import build_concierge_text_status

    text = _resolve_redirect_text(user_text, history)
    return {
        "content": text,
        "content_format": "text",
        "concierge_intent": "redirect",
        "llm_used": False,
        "sage_diagnosis": build_concierge_text_status(
            text, title="ご案内", kind="concierge_redirect"
        ).to_client_dict(),
    }


def should_concierge_handle(
    user_text: str,
    triage_result: Optional[Dict[str, Any]] = None,
    *,
    alt_texts: Optional[list] = None,
) -> bool:
    """Other または挨拶・感謝・雑談のみ Concierge。医薬品・Emergency・Physical は除外。"""
    from src.services.concierge_intent import (
        CONCIERGE_META_INTENTS,
        _is_medicine_consultation,
        is_legal_compliance_meta_question,
        probe_meta_concierge_intent,
        triage_has_concierge_meta_intent,
    )
    from src.services.routing_context import evaluate_store_gate

    if not user_text:
        return False

    if (triage_result or {}).get("concierge_intent") == "session_ops":
        return False

    extra = [t for t in (alt_texts or []) if t]
    routing_source = (triage_result or {}).get("_routing_source_text")
    if routing_source:
        extra.append(routing_source)

    def _concierge_meta_allowed() -> bool:
        return (triage_result or {}).get("category") != "Emergency"

    for candidate in (user_text, *extra):
        text = (candidate or "").strip()
        if not text:
            continue
        probed = probe_meta_concierge_intent(text)
        if probed in CONCIERGE_META_INTENTS:
            if evaluate_store_gate(
                user_text,
                *extra,
                triage_result=triage_result,
                routing_ctx=None,
            ):
                return False
            return _concierge_meta_allowed()
        if is_legal_compliance_meta_question(text):
            if evaluate_store_gate(
                user_text,
                *extra,
                triage_result=triage_result,
                routing_ctx=None,
            ):
                return False
            return _concierge_meta_allowed()

    if triage_has_concierge_meta_intent(triage_result):
        if evaluate_store_gate(
            user_text,
            *extra,
            triage_result=triage_result,
            routing_ctx=None,
        ):
            return False
        return (triage_result or {}).get("category") != "Emergency"

    if _is_medicine_consultation(user_text):
        triage = triage_result or {}
        if triage.get("_intent_router_dispatch"):
            probed = probe_meta_concierge_intent(user_text)
            if probed in CONCIERGE_META_INTENTS:
                return _concierge_meta_allowed()
        return False

    if evaluate_store_gate(
        user_text,
        *extra,
        triage_result=triage_result,
        routing_ctx=None,
    ):
        return False
    cat = (triage_result or {}).get("category", "")
    fast = classify_concierge_intent(user_text)
    if fast in ("greeting", "thanks"):
        return cat != "Emergency"
    if cat in ("Emergency", "Physical", "Ask"):
        return False
    if fast == "chitchat":
        return True
    return cat == "Other"
