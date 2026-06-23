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
    build_concierge_app_about_line_flex,
    build_concierge_architecture_line_flex,
    build_concierge_capabilities_line_flex,
    build_concierge_operator_line_flex,
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


def _extract_substantive_user_topics(
    msgs: List[Dict[str, str]],
) -> List[str]:
    """挨拶・お礼以外の、会話の核になりうる user 発話を抽出。"""
    topics: List[str] = []
    for m in msgs:
        if m.get("type") != "user":
            continue
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        intent = classify_concierge_intent(content)
        if intent in ("greeting", "thanks"):
            continue
        topics.append(content[:80])
    return topics[-3:]


def _last_bot_reply_snippet(
    msgs: List[Dict[str, str]],
    *,
    greeting_only: bool = False,
) -> str:
    from src.services.line_memory_context import compress_message_for_llm

    for m in reversed(msgs):
        if m.get("type") != "bot":
            continue
        if greeting_only:
            diag = m.get("diagnosis") or {}
            kind = str(diag.get("kind") or "")
            if not (m.get("greeting") or kind == "concierge_greeting"):
                continue
        compressed = compress_message_for_llm(m)
        snippet = str(compressed.get("content") or "").strip()[:120]
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
                "「こちらにいます」「はい、どうぞ」など軽く応じる"
            )

    topics = _extract_substantive_user_topics(prior)
    if topics:
        lines.append(f"- これまでの話題: {' / '.join(topics)}")
        lines.append(
            "- 話題に自然につなげられるなら1文だけ触れてよい（長く繰り返さない）"
        )
    elif mode == "greeting" and not infer_is_first_greeting_contact(history):
        lines.append(
            "- まだ具体的な相談はない。窓口説明を繰り返さず、様子を見る一言で受け止める"
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

    if mode == "chitchat" and not lines:
        lines.append("- 雑談の流れを踏まえ、前の話題に自然につなげる")

    return "\n".join(lines) if lines else "- 特になし"


def format_concierge_history_block(
    history: Optional[List[Dict[str, str]]],
    user_text: str,
) -> str:
    from src.services.triage_history import format_triage_history_block

    prior = _prior_history_for_prompt(history, user_text)
    return format_triage_history_block(prior[-_CONCIERGE_PROMPT_HISTORY_LIMIT:])


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
    from src.services.concierge_orchestrator import enrich_other_concierge_intent

    text = (user_text or "").strip()
    llm_text = (llm_user_text or text).strip()
    if not text or _is_medicine_consultation(text):
        return None

    from src.services.routing_context import evaluate_store_gate

    if evaluate_store_gate(
        text,
        triage_result=triage_result,
        routing_ctx=routing_ctx,
    ):
        return None

    orchestrated = resolve_intent_from_triage(
        triage_result, session, text, routing_ctx=routing_ctx
    )
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
    if category == "Other" and client is not None and not (triage_result or {}).get("concierge_intent"):
        enriched = enrich_other_concierge_intent(
            dict(triage_result or {}),
            llm_text,
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


_GREETING_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "薬局の相談窓口で、落ち着いて耳を傾けるスタッフのように話します。"
    "会話履歴と文脈メモを読み、毎回言い回しを変えて自然な続きの返答をします。"
    "ユーザーの挨拶の温度感（カジュアルさ・元気さ）にはミラーリングで合わせます。"
    "ただしやや攻撃的・苛立ちのときは、ミラーリングより寄り添い・傾聴を優先し、"
    "批判・説教・突き放し・皮肉にはなりません。"
)

_GREETING_PROMPT_REQUIREMENTS = """【優先順位】
1. 相手を煽らない・責めない・突き放さない
2. ミラーリング（挨拶語・カジュアルさ・温度感）。失礼語・罵倒は繰り返さない
3. やや攻撃的・苛立ちのときは 2 より先に寄り添い・傾聴（受け止め・安心）
4. 初回のみツール説明。継続の呼びかけでは繰り返さない
5. 自然な促し（お気軽に／お聞かせください）

【口調・ブランド】
- ユーザーのトーン・カジュアルさ・温度感に合わせて返す（ミラーリング）。挨拶語（やあ・こんにちは等）のミラーリングは可
- 失礼語・罵倒（おい・ふざけんな等）は繰り返さず、感情（焦り・困惑・呼びかけ）だけを汲み取る
- 薬局の相談窓口として落ち着きと信頼感を保つ。ふざけた・命令的・攻撃的な印象は出さない
- 基本は丁寧語（です・ます）。ユーザーがタメ口・強めの口調のときは、柔らかい丁寧語（〜ですね／〜でしょうか）で距離を縮める

【苛立ち・やや強い口調への対応】
- 少し攻撃的・荒い表現でも、相手を責めたり逆上させたり煽ったりしない
- 「はい、どうしましたか？」のように事務的・突き放し・煽られているように聞こえる言い方は避ける
- 入力の促しは「お気軽にお聞かせください」「お気軽にどうぞ」「教えていただければ」など自然な言い回しにする
- 禁止（不自然・事務的）:「やわらかく書いてください」「短く書いてください」「具体的に書いてください」「〜ですので、〜（説明的）」「気になることがあれば（堅い）」
- 例（短い呼びかけ・苛立ち）:「お声がけありがとうございます。ちゃんと受け止めていますので、何かお困りのことがあればお聞かせください。」「焦らなくて大丈夫です。どうされたいか、ゆっくり教えていただけますか？」
- 例（カジュアル挨拶・初回）:「やあ、こんにちは。こちらは市販薬の相談窓口です。頭痛やのどの痛み、お薬の選び方など、お気軽にご相談ください。」「こんにちは。症状や市販薬のことでお困りでしたら、できる範囲でお手伝いします。まずは気になることをお聞かせください。」
- 例（継続の呼びかけ）:「お声がけありがとうございます。何かお困りのことはありますか？」「はい、こちらにいます。お体のことで気になることがあれば、お聞かせください。」
- 例文はそのままコピーせず、同等の情報量でユーザー入力に合わせて言い換える

【会話の継続】
- 会話履歴と【会話の文脈】を必ず読み、これまでのやり取りに沿って返す
- 会話履歴に直前の挨拶・案内があるとき、市販薬相談ツール・窓口の説明の繰り返しはしない
- 同じ挨拶を連続で受け取ったときは、毎回言い回しを変える（2回目・3回目で同じ定型文にしない）
- 「また来てくれてありがとう」は同じセッション内の連続挨拶では不自然。使わない
- 「おい」「ねえ」「もしもし」など短い呼びかけは会話の続き。まず受け止めてから、困りごとを穏やかに尋ねる
- 以前に触れた症状・話題があれば、自然な範囲で1文だけ思い出す（長く繰り返さない）

【内容・長さ】
- 1文だけの極端に短い返答は避ける（目安: 初回 80〜180 文字・2〜3文、継続 50〜120 文字・2文程度）
- 初回接触が「はい」のときのみ: 挨拶への返答に加え、市販薬相談窓口であることと相談例（頭痛・のどの痛み・飲み合わせ等）を含め、最後に自然な促しを入れる
- 初回接触が「いいえ」のとき: ツール説明・窓口紹介は書かず、受け止め＋穏やかな質問の2文にとどめる
- 医薬品を指すときは必ず「市販薬」を使う。「OTC」「OTC薬」は使わない
- yes/no で本サービスの性質を聞いた場合は挨拶として扱わない。挨拶返答内で医療機関であるかのように「はい」と答えない
- 「病院ではない」「診療所ではない」等の否定説明は書かない
- 診断・処方はしない"""

_CHITCHAT_SYSTEM_PROMPT = (
    "あなたは市販薬相談ツールの案内役です。"
    "会話履歴と文脈メモを踏まえ、雑談にも自然に乗りつつ毎回言い回しを変えます。"
    "ユーザーの温度感にミラーリングで合わせつつ、"
    "苛立ちがあれば寄り添い・傾聴を優先します。説教・突き放し・皮肉にはなりません。"
)

_CHITCHAT_PROMPT_REQUIREMENTS = """【優先順位】
1. 相手を煽らない・責めない
2. 会話履歴・文脈に沿った自然な続き
3. ミラーリング（温度感）。失礼語は繰り返さない
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


def infer_is_first_greeting_contact(
    history: Optional[List[Dict[str, str]]],
) -> bool:
    """挨拶返答用: これまでに Concierge/挨拶 bot 応答がなければ初回接触。"""
    msgs = list(history or [])
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
    is_first = infer_is_first_greeting_contact(history)
    first_label = "はい" if is_first else "いいえ"
    if is_first:
        contact_block = (
            "【初回接触の追加要件】\n"
            "- 2〜3文・80〜180文字を目安に、窓口説明と相談例を含めて返す\n"
            "- 構成の目安: 挨拶への返答 → 市販薬相談窓口であること → "
            "相談例1つ（頭痛・のどの痛み・飲み合わせ等）→ 自然な促し"
        )
        temperature = 0.55
    else:
        contact_block = (
            "【継続接触の追加要件】\n"
            "- 2文・50〜120文字を目安に返す\n"
            "- 窓口説明・市販薬相談ツールの紹介は書かない\n"
            "- 【会話の文脈】と履歴を踏まえ、毎回言い回しを変えて受け止める\n"
            "- 同じ挨拶の連続なら、直前の返答と異なる表現にする"
        )
        temperature = 0.62
    prompt = f"""{get_policy_snippet()}

【会話履歴（参考）】
{hist}

【会話の文脈】
{context}

【初回接触】
{first_label}

{contact_block}

【ユーザーの挨拶】
{user_text}

【要件】
{_GREETING_PROMPT_REQUIREMENTS}
"""
    try:
        resp = concierge_chat(
            client,
            "concierge_agent.greeting",
            [
                {
                    "role": "system",
                    "content": _GREETING_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=temperature,
            session_id=session_id,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text, True
    except Exception as exc:
        logger.warning("Concierge greeting LLM failed: %s", exc)
    return build_greeting_text(user_text), False


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
        return (resp.choices[0].message.content or "").strip()
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

        text = build_thanks_text()
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_text_status(
                text, title="お礼", kind="concierge_thanks"
            ).to_client_dict(),
        }
    if intent == "redirect":
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text = build_redirect_text()
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_text_status(
                text, title="ご案内", kind="concierge_redirect"
            ).to_client_dict(),
        }
    if intent == "capabilities":
        from src.services.status_diagnosis_builder import build_concierge_capabilities_status

        return {
            "content": format_concierge_capabilities_card(feedback_data=fb),
            "content_format": "status_card",
            "line_flex": build_concierge_capabilities_line_flex(),
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_capabilities_status().to_client_dict(),
        }
    if intent == "architecture":
        from src.services.status_diagnosis_builder import build_concierge_architecture_status

        return {
            "content": format_concierge_architecture_card(feedback_data=fb),
            "content_format": "status_card",
            "line_flex": build_concierge_architecture_line_flex(),
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_architecture_status().to_client_dict(),
        }
    if intent == "app_about":
        from src.services.status_diagnosis_builder import build_concierge_app_about_status

        return {
            "content": format_concierge_app_about_card(feedback_data=fb),
            "content_format": "status_card",
            "line_flex": build_concierge_app_about_line_flex(),
            "concierge_intent": intent,
            "llm_used": False,
            "sage_diagnosis": build_concierge_app_about_status().to_client_dict(),
        }
    if intent == "doc_operator":
        return build_doc_operator_payload(
            user_text,
            client,
            session_id=session_id,
            history=history,
            feedback_data=fb,
        )
    if intent in DOC_CONCIERGE_INTENTS:
        from src.services.status_diagnosis_builder import build_concierge_text_status

        text = generate_doc_answer_text(
            client,
            user_text,
            intent,
            session_id=session_id,
            history=history,
        )
        return {
            "content": text,
            "content_format": "text",
            "concierge_intent": intent,
            "llm_used": True,
            "sage_diagnosis": build_concierge_text_status(
                text,
                title="ドキュメント案内",
                kind=f"concierge_{intent}",
            ).to_client_dict(),
        }
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

    text = build_redirect_text()
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
    from src.services.concierge_intent import _is_medicine_consultation
    from src.services.routing_context import evaluate_store_gate

    if not user_text or _is_medicine_consultation(user_text):
        return False

    extra = [t for t in (alt_texts or []) if t]
    routing_source = (triage_result or {}).get("_routing_source_text")
    if routing_source:
        extra.append(routing_source)

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
