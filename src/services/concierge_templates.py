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
from src.content.concierge_docs import load_concierge_doc
from src.services.chat_response_service import build_greeting_response
from src.services.html_formatter import format_feedback_buttons, format_status_card

_OPERATOR_BUG_FORM_URL = "https://forms.gle/UB8kZHd4VHenmRUN6"
_OPERATOR_REPO_URL = "https://github.com/32Lwk"
_OPERATOR_EMAIL = "weary-scoots.7y@icloud.com"


def _external_link(url: str, label: str) -> str:
    return (
        f'<a href="{html.escape(url, quote=True)}" target="_blank" '
        f'rel="noopener noreferrer">{html.escape(label)}</a>'
    )


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


def format_concierge_app_about_card(
    *,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    app = get_app_info()
    body = (
        f"<p><strong>{html.escape(app.get('name', ''))}</strong></p>"
        f"<p>{html.escape(app.get('purpose', ''))}</p>"
        f"<p>{html.escape(app.get('audience', ''))}</p>"
    )
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
        hints=["詳細は画面右上の ℹ️ からもご確認いただけます。"],
        footer_html=footer,
    )


def build_greeting_text(user_message: str) -> str:
    return build_greeting_response(user_message)


def format_concierge_operator_card(
    *,
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    """docs/運営者情報.md に基づく固定カード（LLM 不要・リンク付き）。"""
    _title, _doc_body = load_concierge_doc("doc_operator")
    email = _OPERATOR_EMAIL
    body = (
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">運営者</h5>'
        "<ul>"
        "<li><strong>氏名:</strong> 川嶋 宥翔（Kawashima Yuto）</li>"
        "<li><strong>所属:</strong> 名古屋大学 理学部 物理学科 2年</li>"
        "<li><strong>資格:</strong> 登録販売者資格保有</li>"
        f'<li><strong>E-mail:</strong> <a href="mailto:{html.escape(email, quote=True)}">'
        f"{html.escape(email)}</a></li>"
        f"<li><strong>不具合報告フォーム:</strong> "
        f'{_external_link(_OPERATOR_BUG_FORM_URL, "不具合報告フォーム")}</li>'
        f"<li><strong>開発リポジトリ:</strong> "
        f'{_external_link(_OPERATOR_REPO_URL, "GitHub（32Lwk）")}</li>'
        "</ul></section>"
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">免責事項</h5>'
        "<ul>"
        "<li>本システムは試験運用段階のため、動作の保証はありません</li>"
        "<li>医薬品の使用に際しては、必ず薬剤師または登録販売者に相談してください</li>"
        "<li>最終的な判断は、医師や薬剤師の専門的なアドバイスに従うことが重要です</li>"
        "</ul></section>"
    )
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant="notice",
        title="運営者情報",
        body_html=body,
        hints=["詳細は画面右上の ℹ️ からもご確認いただけます。"],
        footer_html=footer,
    )
