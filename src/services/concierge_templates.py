"""ConciergeAgent 応答テンプレート・ステータスカード生成"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from src.content.concierge_knowledge import (
    get_agents,
    get_app_info,
    get_capabilities,
    get_limitations,
)
from src.services.chat_response_service import build_greeting_response
from src.services.html_formatter import format_feedback_buttons, format_status_card

_OPERATOR_BUG_FORM_URL = "https://forms.gle/UB8kZHd4VHenmRUN6"
_OPERATOR_EMAIL = "weary-scoots.7y@icloud.com"


def _external_link(url: str, label: str) -> str:
    return (
        f'<a href="{html.escape(url, quote=True)}" target="_blank" '
        f'rel="noopener noreferrer">{html.escape(label)}</a>'
    )


def _intro_paragraphs_html(intro_text: str) -> str:
    parts = [p.strip() for p in (intro_text or "").split("\n") if p.strip()]
    if not parts:
        return ""
    return "".join(f"<p>{html.escape(p)}</p>" for p in parts)


def build_thanks_text() -> str:
    return (
        "どういたしまして。ほかにご質問や症状がございましたら、"
        "お気軽にお聞かせください。"
    )


def build_redirect_text() -> str:
    return (
        "こちらは一般用医薬品（OTC）の相談窓口です。"
        "頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。"
    )


def _list_section(title: str, items: List[str]) -> str:
    lis = "".join(f"<li>{html.escape(x)}</li>" for x in items)
    return (
        f'<section class="chat-status-card__section">'
        f'<h5 class="chat-status-card__section-title">{html.escape(title)}</h5>'
        f"<ul>{lis}</ul></section>"
    )


def build_concierge_capabilities_line_flex() -> Dict[str, Any]:
    app = get_app_info()
    caps = get_capabilities()
    limits = get_limitations()
    body = [str(app.get("purpose", "")).strip()]
    body.extend(f"{c.get('title', '')}: {c.get('body', '')}" for c in caps if c.get("title"))
    if limits:
        body.append("できないこと・ご注意: " + " / ".join(limits[:4]))
    return {
        "variant": "notice",
        "title": "このチャットでできること（β版）",
        "subtitle": app.get("name", ""),
        "body_paragraphs": [p for p in body if p],
        "hints": ["症状やお薬について、具体的にお書きください。"],
    }


def format_concierge_capabilities_card(
    *,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    app = get_app_info()
    caps = get_capabilities()
    limits = get_limitations()
    cap_items = [f"{c.get('title', '')}: {c.get('body', '')}" for c in caps]
    body_parts = [
        f"<p>{html.escape(app.get('purpose', ''))}</p>",
        _list_section("できること", cap_items),
        _list_section("できないこと・ご注意", limits),
    ]
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant="notice",
        title="このチャットでできること（β版）",
        subtitle=app.get("name", ""),
        body_html="".join(body_parts),
        hints=["症状やお薬について、具体的にお書きください。"],
        footer_html=footer,
    )


def build_concierge_architecture_line_flex() -> Dict[str, Any]:
    agents = get_agents()
    body = [
        "一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。"
        "AI（LLM）が自由に薬名を創作して決めることはありません。",
    ]
    body.extend(
        f"{a.get('name_ja', '')}: {a.get('role_one_liner', '')}"
        for a in agents
        if a.get("name_ja")
    )
    body.append(
        "症状の相談は PhysicalOrchestrator が、"
        "挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。"
    )
    return {
        "variant": "notice",
        "title": "このチャットの仕組み（β版）",
        "subtitle": "トリアージ後に専門のエージェントが応答します",
        "body_paragraphs": body,
        "hints": ["お体の不調やお薬のことでしたら、症状を教えてください。"],
    }


def format_concierge_architecture_card(
    *,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    agents = get_agents()
    items = [
        f"{a.get('name_ja', '')}: {a.get('role_one_liner', '')}"
        for a in agents
    ]
    body = (
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">市販薬の選び方</h5>'
        "<p>一般用医薬品（OTC）の<strong>候補選定はルールベースのアルゴリズムのみ</strong>で行います。"
        "AI（LLM）が自由に薬名を創作して決めることはありません。"
        "お話の分類・説明文の生成・質問への回答などに AI を使います。</p>"
        "</section>"
    )
    body += _list_section("役割分担（マルチエージェント）", items)
    body += (
        "<p>症状の相談は PhysicalOrchestrator が、"
        "挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。</p>"
    )
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant="notice",
        title="このチャットの仕組み（β版）",
        subtitle="トリアージ後に専門のエージェントが応答します",
        body_html=body,
        hints=["お体の不調やお薬のことでしたら、症状を教えてください。"],
        footer_html=footer,
    )


def build_concierge_app_about_line_flex() -> Dict[str, Any]:
    app = get_app_info()
    return {
        "variant": "notice",
        "title": "このツールについて",
        "body_paragraphs": [
            p
            for p in (
                app.get("explicitly_not", ""),
                app.get("service_nature", ""),
                app.get("name", ""),
                app.get("purpose", ""),
                app.get("audience", ""),
            )
            if p
        ],
        "hints": ["症状やお薬のことがあれば、具体的にお書きください。"],
    }


def format_concierge_app_about_card(
    *,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    app = get_app_info()
    nature = str(app.get("service_nature") or "").strip().rstrip("。")
    not_a = str(app.get("explicitly_not") or "").strip().rstrip("。")
    purpose = str(app.get("purpose") or "").strip().rstrip("。")
    audience = str(app.get("audience") or "").strip().rstrip("。")
    body = f"<p><strong>{html.escape(app.get('name', ''))}</strong></p>"
    lead_parts = []
    if nature:
        lead_parts.append(f"こちらは{html.escape(nature)}です")
    if not_a:
        lead_parts.append(html.escape(not_a))
    if lead_parts:
        body += f"<p>{'。'.join(lead_parts)}。</p>"
    if purpose:
        body += f"<p>{html.escape(purpose)}。</p>"
    if audience:
        body += f"<p>{html.escape(audience)}。</p>"
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant="notice",
        title="このツールについて",
        body_html=body,
        hints=["症状やお薬のことがあれば、具体的にお書きください。"],
        footer_html=footer,
    )


def build_greeting_text(user_message: str) -> str:
    """LLM 失敗時のフォールバック（通常は generate_greeting_text を使用）。"""
    return build_greeting_response(user_message)


def build_concierge_operator_line_flex(*, intro_text: str = "") -> Dict[str, Any]:
    email = _OPERATOR_EMAIL
    body = [p.strip() for p in (intro_text or "").split("\n") if p.strip()]
    body.extend(
        [
            "このサービスは研究・検証目的の β 版（試験運用）です。医療行為・診断・処方の代替ではありません。",
            f"お問い合わせ E-mail: {email}",
            f"不具合・お問い合わせフォーム: {_OPERATOR_BUG_FORM_URL}",
        ]
    )
    return {
        "variant": "notice",
        "title": "お問い合わせ・試験運用について",
        "subtitle": "研究・検証目的の β 版（試験運用）",
        "body_paragraphs": body,
        "hints": [
            "症状やお薬のことは、具体的にお書きください。",
            "プライバシーポリシー等は画面右上 ℹ️ からご確認いただけます。",
        ],
    }


def format_concierge_operator_card(
    *,
    intro_text: str = "",
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    """docs/concierge/お問い合わせ・試験運用.md に基づくカード（リンク付き・個人属性なし）。"""
    email = _OPERATOR_EMAIL
    body_parts = [_intro_paragraphs_html(intro_text)]
    body_parts.append(
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">このサービスについて</h5>'
        "<ul>"
        "<li>研究・検証目的の <strong>β 版（試験運用）</strong> です</li>"
        "<li><strong>医療行為・診断・処方の代替ではありません</strong></li>"
        "<li>運営は個人による開発・運用です</li>"
        "<li>運営者の<strong>氏名・所属・資格など個人を特定しうる情報は開示しません</strong></li>"
        "</ul></section>"
    )
    body_parts.append(
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">お問い合わせ</h5>'
        "<ul>"
        f'<li><strong>E-mail:</strong> <a href="mailto:{html.escape(email, quote=True)}">'
        f"{html.escape(email)}</a></li>"
        f"<li><strong>不具合・お問い合わせフォーム:</strong> "
        f'{_external_link(_OPERATOR_BUG_FORM_URL, "不具合報告フォーム")}</li>'
        "<li>画面上の <strong>🐛</strong> ボタンからも同じフォームに進めます</li>"
        "</ul></section>"
    )
    body_parts.append(
        _list_section(
            "ご利用上の注意",
            [
                "試験運用のため、動作・表示内容の正確性・安全性を保証しません",
                "お薬の使用は薬剤師・登録販売者・医師などの専門家にご相談ください",
                "詳細な規約は画面右上 ℹ️ の免責事項・利用規約をご確認ください",
            ],
        )
    )
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant="notice",
        title="お問い合わせ・試験運用について",
        subtitle="研究・検証目的の β 版（試験運用）",
        body_html="".join(body_parts),
        hints=[
            "症状やお薬のことは、具体的にお書きください。",
            "プライバシーポリシー等は画面右上 ℹ️ からご確認いただけます。",
        ],
        footer_html=footer,
        aria_label="お問い合わせ・試験運用について",
    )
