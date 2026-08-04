"""ConciergeAgent 応答テンプレート・ステータスカード生成"""
from __future__ import annotations

import html
import re
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


def build_thanks_text(user_message: str = "") -> str:
    """LLM 失敗時のフォールバック。ユーザーの感謝の丁寧さに合わせる。"""
    text = (user_message or "").strip()
    if "ございます" in text or "ありがとうござい" in text:
        return (
            "こちらこそありがとうございます。"
            "ほかにご質問や気になる症状があれば、お気軽にお聞かせください。"
        )
    if re.search(r"(サンキュー|thanks|thank\s*you)", text, re.I):
        return (
            "どういたしまして！"
            "ほかに気になることがあれば、お気軽にどうぞ。"
        )
    return (
        "どういたしまして。ほかにご質問や症状がございましたら、"
        "お気軽にお聞かせください。"
    )


def build_redirect_text() -> str:
    return (
        "こちらは一般用医薬品（OTC）の相談窓口です。"
        "頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。"
    )


def build_redirect_followup_text(prior_topic: str = "") -> str:
    """redirect の同文ループ回避（p3-followup-hotfix）。

    直前ターンも concierge_redirect だった場合に使う続きの案内文。
    脱線トピックへの言及は繰り返さず、OTC の具体例（rule_based 推奨）を示して
    同一メッセージの単純反復を避ける。
    """
    topic = (prior_topic or "").strip()
    if topic:
        intro = f"「{topic}」については、こちらでは専門外のためお答えできません。"
    else:
        intro = "そのご質問については、こちらでは専門外のためお答えできません。"
    return (
        f"{intro}"
        "具体例としては、本アプリでは症状や年齢などの条件をもとに、"
        "rule_based（ルールベース）の推奨ロジックで市販薬の候補をお選びしています。"
        "頭痛・のどの痛み・お薬の選び方など、気になる症状があれば具体的にお書きください。"
    )


def _split_japanese_sentences(text: str) -> List[str]:
    """句点・感嘆符で文を分割（区切り文字は各文末尾に残す）。"""
    raw = (text or "").strip()
    if not raw:
        return []
    parts = re.split(r"(?<=[。！？!?])\s*", raw)
    return [p.strip() for p in parts if p.strip()]


def split_dynamic_body_paragraphs(text: str) -> List[str]:
    """LLM プレーンテキストを status / LINE Flex 用段落に分割する。"""
    raw = (text or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if len(parts) <= 1:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) > 1 and all(ln.startswith(("・", "-", "•")) for ln in lines):
            return lines
        parts = [raw]

    out: List[str] = []
    for part in parts:
        if len(part) > 100 or ("。" in part and part.count("。") >= 2):
            out.extend(_split_japanese_sentences(part))
        else:
            out.append(part)
    return out


_AGENT_BULLET_INLINE_RE = re.compile(
    r"[、，]?\s*・\s*"
    r"([A-Za-z][A-Za-z0-9]*(?:Agent|Orchestrator|Manager|Router))"
    r"\s*[：:]\s*"
    r"([^・]+?)"
    r"(?=(?:[、，]\s*・\s*[A-Za-z])|[。！？!?]|$)"
)


def _normalize_agent_bullet(name: str, desc: str) -> str:
    clean_desc = (desc or "").strip().rstrip("、，,.")
    return f"{name}：{clean_desc}"


def extract_inline_agent_bullets(text: str) -> tuple[str, List[str]]:
    """文中に埋め込まれた「・TriageAgent：…」を prose と箇条書きに分離する。"""
    raw = (text or "").strip()
    if not raw or "・" not in raw:
        return raw, []
    bullets: List[str] = []
    for match in _AGENT_BULLET_INLINE_RE.finditer(raw):
        bullets.append(_normalize_agent_bullet(match.group(1), match.group(2)))
    if not bullets:
        return raw, []

    prose = _AGENT_BULLET_INLINE_RE.sub("", raw)
    prose = re.sub(r"[、，]\s*$", "", prose.strip())
    prose = re.sub(r"^[、，]\s*", "", prose)
    prose = re.sub(r"\s{2,}", " ", prose)
    prose = re.sub(r"(?:たとえば|例えば|例として)\s*$", "", prose).strip()
    prose = re.sub(r"、\s*という形です。?$", "。", prose)
    if prose and not prose.endswith(("。", "！", "？")):
        prose += "。"
    return prose, bullets


_DEEP_ARCH_TOPIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("GCP 本番", re.compile(r"GCP|Cloud\s*Run|medicine\.yutok\.dev|DeepL|Google Cloud", re.I)),
    (
        "AWS ステージング",
        re.compile(
            r"AWS|ECS|aws\.medicine|Translate|Polly|Bedrock|ElastiCache|Personalize",
            re.I,
        ),
    ),
    (
        "デプロイ・CI/CD",
        re.compile(r"CodePipeline|CodeBuild|ECR|デプロイ|cloudbuild|ingestion", re.I),
    ),
    ("LINE", re.compile(r"\bLINE\b|Messaging API", re.I)),
    ("画像・CDN", re.compile(r"Cloudflare|R2|images\.yutok|CloudFront|\bCDN\b", re.I)),
]


def _is_follow_up_offer_paragraph(paragraph: str) -> bool:
    text = (paragraph or "").strip()
    if not text or not _FOLLOW_UP_OFFER_RE.search(text):
        return False
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[。．!！?？])\s*", text)
        if part.strip()
    ]
    non_offer = [
        sentence
        for sentence in sentences
        if not _FOLLOW_UP_OFFER_RE.search(sentence)
    ]
    return len(non_offer) == 0


def _split_message_paragraphs(message: str) -> List[str]:
    return [part.strip() for part in (message or "").split("\n\n") if part.strip()]


def _is_weak_architecture_intro(intro_parts: List[str]) -> bool:
    substantive = [
        part
        for part in intro_parts
        if not _is_follow_up_offer_paragraph(part)
        and not _GENERIC_ARCHITECTURE_BOILERPLATE_RE.search(part)
    ]
    return len(substantive) == 0


def _append_other_section_items(
    sections: List[Dict[str, Any]],
    items: List[str],
) -> List[Dict[str, Any]]:
    extra = [item.strip() for item in items if item.strip()]
    if not extra:
        return sections
    for sec in sections:
        if sec.get("title") == "その他":
            sec["items"] = list(sec.get("items") or []) + extra
            return sections
    return [*sections, {"title": "その他", "items": extra}]


def _repair_architecture_intro_if_weak(
    user_text: str,
    message: str,
    sections: List[Dict[str, Any]],
) -> tuple[str, List[Dict[str, Any]]]:
    """intro がフォローアップ提案だけ等で弱いとき、セクションから本文を復元する。"""
    intro_parts = _split_message_paragraphs(message)
    offer_parts = [part for part in intro_parts if _is_follow_up_offer_paragraph(part)]
    intro_parts = [part for part in intro_parts if not _is_follow_up_offer_paragraph(part)]

    if _is_weak_architecture_intro(intro_parts):
        priority_titles = _priority_section_titles_for_question(user_text)
        promoted: List[str] = []
        new_sections: List[Dict[str, Any]] = []
        for sec in sections:
            title = str(sec.get("title") or "")
            items = [
                str(item).strip()
                for item in (sec.get("items") or [])
                if str(item).strip() and not _is_follow_up_offer_paragraph(str(item))
            ]
            if not items:
                continue
            should_promote = (
                not priority_titles
                or title in priority_titles
                or title == "その他"
            )
            if should_promote:
                if title == "その他":
                    limit = 4
                elif priority_titles and title == priority_titles[0]:
                    limit = 3
                else:
                    limit = 2
                promoted.extend(items[:limit])
                remainder = items[limit:]
                if remainder:
                    new_sections.append({"title": title, "items": remainder})
            else:
                new_sections.append({**sec, "items": items})
        if promoted:
            intro_parts = promoted
            sections = new_sections

    sections = _append_other_section_items(sections, offer_parts)
    message = "\n\n".join(intro_parts)
    return message, sections


def _bucket_architecture_deep_paragraphs(
    paragraphs: List[str],
) -> tuple[List[str], List[Dict[str, Any]]]:
    """深掘り architecture 本文をトピック別セクションに分割する。"""
    buckets: dict[str, List[str]] = {title: [] for title, _ in _DEEP_ARCH_TOPIC_RULES}
    intro: List[str] = []

    for para in paragraphs:
        if _is_follow_up_offer_paragraph(para):
            intro.append(para)
            continue
        assigned = False
        for title, pattern in _DEEP_ARCH_TOPIC_RULES:
            if pattern.search(para):
                buckets[title].append(para)
                assigned = True
                break
        if not assigned:
            intro.append(para)

    sections: List[Dict[str, Any]] = []
    for title, _ in _DEEP_ARCH_TOPIC_RULES:
        items = buckets[title]
        if items:
            sections.append({"title": title, "items": items})
    return intro, sections


_GENERIC_ARCHITECTURE_BOILERPLATE_RE = re.compile(
    r"(?:"
    r"マルチエージェント|"
    r"ルールベース(?:のスコアリング|のアルゴリズム)?|"
    r"専門担当|役割分担|振り分け|"
    r"症状やお薬の選び方については、具体的な症状"
    r")",
    re.I,
)

_FOLLOW_UP_OFFER_RE = re.compile(
    r"(?:"
    r"もし必要なら|"
    r"必要なら(?:、|,)?次に|"
    r"次に[「『].+[」』].*(?:説明|お伝え)(?:できます|可能です)|"
    r"(?:もう少し|さらに).*(?:説明|お伝え)(?:できます|可能です)"
    r")",
    re.I,
)

_QUESTION_SECTION_PRIORITIES: list[tuple[re.Pattern[str], list[str]]] = [
    (
        re.compile(r"GCP.*AWS|AWS.*GCP|クロスクラウド|違い|cross[- ]cloud", re.I),
        ["GCP 本番", "AWS ステージング"],
    ),
    (
        re.compile(r"CodePipeline|デプロイ.*流れ|CI/CD|pipeline", re.I),
        ["デプロイ・CI/CD", "AWS ステージング"],
    ),
    (
        re.compile(r"Cloud\s*Run|GCP\s*本番|medicine\.yutok\.dev", re.I),
        ["GCP 本番"],
    ),
    (
        re.compile(
            r"ECS|aws\.medicine|AWS\s*ステージング|Translate|Bedrock",
            re.I,
        ),
        ["AWS ステージング"],
    ),
    (
        re.compile(r"Cloudflare|R2|CDN|CloudFront|images\.yutok", re.I),
        ["画像・CDN"],
    ),
    (re.compile(r"\bLINE\b|Messaging API", re.I), ["LINE"]),
]

_ARCH_SECTION_TITLE_ORDER = {title: idx for idx, (title, _) in enumerate(_DEEP_ARCH_TOPIC_RULES)}


def _priority_section_titles_for_question(user_text: str) -> list[str]:
    text = (user_text or "").strip()
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for pattern, titles in _QUESTION_SECTION_PRIORITIES:
        if pattern.search(text):
            for title in titles:
                if title not in seen:
                    seen.add(title)
                    out.append(title)
    return out


def _is_generic_architecture_intro(intro_parts: List[str]) -> bool:
    if not intro_parts:
        return True
    non_generic = [
        part
        for part in intro_parts
        if not _GENERIC_ARCHITECTURE_BOILERPLATE_RE.search(part)
    ]
    return len(non_generic) == 0


def _paragraph_matches_question(user_text: str, paragraph: str) -> bool:
    text = (user_text or "").strip()
    para = (paragraph or "").strip()
    if not text or not para or _is_follow_up_offer_paragraph(para):
        return False
    for title in _priority_section_titles_for_question(text):
        for rule_title, pattern in _DEEP_ARCH_TOPIC_RULES:
            if rule_title == title and pattern.search(para):
                return True
    for pattern, _ in _QUESTION_SECTION_PRIORITIES:
        if pattern.search(text) and pattern.search(para):
            return True
    return False


def _rebalance_architecture_deep_display(
    user_text: str,
    intro_parts: List[str],
    sections: List[Dict[str, Any]],
) -> tuple[List[str], List[Dict[str, Any]]]:
    """質問意図に合う段落をカード本文へ昇格し、一般論は補足へ退避する。"""
    if not sections:
        return intro_parts, sections

    priority_titles = _priority_section_titles_for_question(user_text)
    generic_intro = _is_generic_architecture_intro(intro_parts)
    if not priority_titles and not generic_intro:
        return intro_parts, sections
    if not priority_titles:
        priority_titles = [
            str(sec.get("title") or "")
            for sec in sections
            if sec.get("items")
        ]

    promoted: List[str] = []
    demoted_sections: List[Dict[str, Any]] = []
    for sec in sections:
        title = str(sec.get("title") or "")
        items = list(sec.get("items") or [])
        if not items:
            continue
        if title in priority_titles:
            limit = 3 if title == priority_titles[0] else 2
            promoted.extend(
                item
                for item in items[:limit]
                if not _is_follow_up_offer_paragraph(item)
            )
            remainder = items[limit:]
            if remainder:
                demoted_sections.append({"title": title, "items": remainder})
        else:
            demoted_sections.append(sec)

    if not promoted:
        return intro_parts, sections

    new_intro = list(promoted)
    if intro_parts:
        relevant = [
            part
            for part in intro_parts
            if _paragraph_matches_question(user_text, part)
        ]
        irrelevant = [
            part
            for part in intro_parts
            if not _paragraph_matches_question(user_text, part)
        ]
        if relevant:
            new_intro = relevant + new_intro
        elif generic_intro:
            demoted_sections.append(
                {"title": "このサービスの概要", "items": intro_parts}
            )
        elif irrelevant:
            demoted_sections.append({"title": "その他", "items": irrelevant})

    demoted_sections.sort(
        key=lambda sec: _ARCH_SECTION_TITLE_ORDER.get(str(sec.get("title") or ""), 999)
    )
    return new_intro, demoted_sections


_DOC_PLAIN_DISPLAY_INTENTS = frozenset(
    {
        "doc_privacy",
        "doc_terms",
        "doc_consultation",
        "doc_app_overview",
        "doc_changelog",
    }
)


def structure_concierge_meta_display(
    intent: str,
    body_text: str,
    *,
    deep: bool = False,
    user_text: str = "",
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Web Sage / LINE 向けに読みやすく整形。
    Returns (message_with_paragraph_breaks, sections_for_sage_ui).
    """
    plain = (body_text or "").strip()
    if intent in _DOC_PLAIN_DISPLAY_INTENTS:
        return plain, []

    paragraphs = split_dynamic_body_paragraphs(body_text)
    sections: List[Dict[str, Any]] = []
    all_bullets: List[str] = []
    prose_parts: List[str] = []

    bullet_prefixes = ("・", "-", "•")
    for part in paragraphs:
        if part.startswith(bullet_prefixes):
            all_bullets.append(part.lstrip("・-• ").strip())
            continue
        prose, inline_bullets = extract_inline_agent_bullets(part)
        if inline_bullets:
            all_bullets.extend(inline_bullets)
            if prose:
                prose_parts.append(prose)
        else:
            prose_parts.append(part)

    if all_bullets and intent in ("architecture", "capabilities"):
        deduped: List[str] = []
        seen: set[str] = set()
        for item in all_bullets:
            key = item.split("：", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        sections.append(
            {
                "title": "担当の役割" if intent == "architecture" else "できること",
                "items": deduped,
            }
        )

    if intent == "architecture" and deep and prose_parts:
        intro_parts, topic_sections = _bucket_architecture_deep_paragraphs(prose_parts)
        if topic_sections:
            intro_parts, topic_sections = _rebalance_architecture_deep_display(
                user_text,
                intro_parts,
                topic_sections,
            )
            prose_parts = intro_parts
            sections = topic_sections + sections

    message = "\n\n".join(prose_parts) if prose_parts else (body_text or "").strip()
    if intent == "architecture" and deep:
        message, sections = _repair_architecture_intro_if_weak(
            user_text,
            message,
            sections,
        )
    return message, sections


def build_agent_roster_items() -> List[str]:
    """concierge_knowledge のエージェント一覧（表示用）。"""
    from src.content.concierge_knowledge import get_agents

    items: List[str] = []
    for agent in get_agents():
        name = str(agent.get("name_ja") or agent.get("id") or "").strip()
        role = str(agent.get("role_one_liner") or "").strip()
        if name and role:
            items.append(f"{name}：{role}")
    return items


def merge_agent_roster_section(
    sections: List[Dict[str, Any]],
    *,
    title: str = "担当の役割",
) -> List[Dict[str, Any]]:
    """architecture 説明時に SSOT のエージェント一覧セクションを付与する。"""
    roster = build_agent_roster_items()
    if not roster:
        return sections
    for spec in sections:
        if spec.get("title") == title:
            return sections
    return [*sections, {"title": title, "items": roster}]


def format_dynamic_concierge_meta_card(
    *,
    title: str,
    body_text: str,
    subtitle: str = "",
    hints: Optional[List[str]] = None,
    feedback_data: Optional[Dict[str, Any]] = None,
    variant: str = "notice",
    intent: str = "",
    include_agent_roster: bool = False,
    deep: bool = False,
    user_text: str = "",
) -> str:
    """LLM 生成本文から Web 用 status カード HTML を組み立てる。"""
    display_message, section_specs = structure_concierge_meta_display(
        intent or "app_about",
        body_text,
        deep=deep,
        user_text=user_text,
    )
    if include_agent_roster and (intent or "") == "architecture":
        section_specs = merge_agent_roster_section(section_specs)
    paragraphs = split_dynamic_body_paragraphs(display_message)
    body_html = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    for spec in section_specs:
        items = spec.get("items") or []
        if items:
            body_html += _list_section(str(spec.get("title") or ""), items)
    footer = ""
    if feedback_data:
        footer = format_feedback_buttons(
            feedback_data,
            question="このご案内は分かりやすかったですか？",
        )
    return format_status_card(
        variant=variant,
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        hints=hints or [],
        footer_html=footer,
    )


_LINE_CONCIERGE_BODY_MAX_CHARS = 4200
_LINE_SHALLOW_BODY_MAX_CHARS = 1100
_LINE_SHALLOW_MAX_PARAGRAPHS = 4


def _apply_line_channel_body_limits(
    paragraphs: List[str],
    *,
    channel: str = "web",
    deep: bool = False,
) -> List[str]:
    """LINE 非 deep 時は概要のみ（Q4 チャネル別深さ）。"""
    if channel != "line":
        return _truncate_line_body_paragraphs(paragraphs)
    if deep:
        return _truncate_line_body_paragraphs(paragraphs)

    import os

    total = 0
    out: List[str] = []
    for para in paragraphs[:_LINE_SHALLOW_MAX_PARAGRAPHS]:
        chunk = (para or "").strip()
        if not chunk:
            continue
        if total + len(chunk) > _LINE_SHALLOW_BODY_MAX_CHARS:
            remain = _LINE_SHALLOW_BODY_MAX_CHARS - total
            if remain > 60:
                out.append(chunk[: remain - 1].rstrip() + "…")
            break
        out.append(chunk)
        total += len(chunk)

    truncated = (
        len(paragraphs) > len(out)
        or sum(len(p) for p in paragraphs) > _LINE_SHALLOW_BODY_MAX_CHARS
    )
    if truncated:
        site = (os.getenv("PUBLIC_SITE_URL") or "https://medicine.yutok.dev").rstrip("/")
        out.append(f"続きは Web チャット（{site}）または「詳しく」と送ってください。")
    return out


def _truncate_line_body_paragraphs(paragraphs: List[str]) -> List[str]:
    """LINE Flex 上限対策 — 切り詰め + Web 誘導（深掘り medium 用）。"""
    import os

    total = 0
    out: List[str] = []
    for para in paragraphs:
        chunk = (para or "").strip()
        if not chunk:
            continue
        if total + len(chunk) > _LINE_CONCIERGE_BODY_MAX_CHARS:
            remain = _LINE_CONCIERGE_BODY_MAX_CHARS - total
            if remain > 80:
                out.append(chunk[: remain - 1].rstrip() + "…")
            site = (
                os.getenv("PUBLIC_SITE_URL") or "https://medicine.yutok.dev"
            ).rstrip("/")
            out.append(f"続きの詳しい説明は Web チャット（{site}）でご覧ください。")
            return out
        out.append(chunk)
        total += len(chunk)
    return out


def build_dynamic_concierge_line_flex(
    *,
    title: str,
    body_text: str,
    subtitle: str = "",
    hints: Optional[List[str]] = None,
    variant: str = "notice",
    intent: str = "",
    include_agent_roster: bool = False,
    deep: bool = False,
    channel: str = "web",
    user_text: str = "",
) -> Dict[str, Any]:
    """LLM 生成本文から LINE status Flex スペックを組み立てる。"""
    display_message, section_specs = structure_concierge_meta_display(
        intent or "app_about",
        body_text,
        deep=deep,
        user_text=user_text,
    )
    if include_agent_roster and (intent or "") == "architecture":
        section_specs = merge_agent_roster_section(section_specs)
    body = split_dynamic_body_paragraphs(display_message)
    for spec in section_specs:
        title_label = str(spec.get("title") or "").strip()
        items = spec.get("items") or []
        if title_label and items:
            body.append(title_label)
            body.extend(items)
    body = _apply_line_channel_body_limits(body, channel=channel, deep=deep)
    return {
        "variant": variant,
        "title": title,
        "subtitle": subtitle,
        "body_paragraphs": body,
        "hints": list(hints or []),
    }


def _list_section(title: str, items: List[str]) -> str:
    lis = "".join(f"<li>{html.escape(x)}</li>" for x in items)
    return (
        f'<section class="chat-status-card__section">'
        f'<h5 class="chat-status-card__section-title">{html.escape(title)}</h5>'
        f"<ul>{lis}</ul></section>"
    )


def build_line_account_intro_text(*, line_url: str) -> str:
    if line_url:
        return (
            "LINE 公式アカウントからも、Web と同じ仕組みで市販薬の相談ができます。\n"
            "下のリンクまたは QR コードから友だち追加のうえ、お困りの症状をメッセージでお送りください。"
        )
    return (
        "LINE 連携は GCP 本番環境（medicine.yutok.dev）で提供しています。\n"
        "現在の画面から LINE リンクを取得できない場合は、しばらくしてから再度お試しいただくか、"
        "画面右上 ℹ️ のお問い合わせ窓口をご利用ください。"
    )


def _line_account_section_html(*, line_url: str, qr_url: str = "") -> str:
    parts = [
        "<p>スマートフォンの LINE アプリで友だち追加できます。</p>",
        '<div class="ui-line-account__actions">',
    ]
    if qr_url:
        parts.append(
            f'<p class="ui-line-account__qr-wrap">'
            f'<img src="{html.escape(qr_url, quote=True)}" alt="LINE QRコード" '
            f'class="ui-crisis-resource__qr-img" width="120" height="120" loading="lazy" decoding="async" '
            f"onerror=\"if(!this.dataset.fallback){{this.dataset.fallback='1';"
            f"this.src='https://images.yutok.dev/line/line-official-qr.png';}}else{{"
            f"this.style.display='none';"
            f"this.closest('.ui-line-account__qr-wrap')?.classList.add('ui-line-account__qr-wrap--missing');}}\">"
            f"</p>"
        )
    if line_url:
        parts.append(
            f'<p class="ui-line-account__link-wrap">'
            f'<a href="{html.escape(line_url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">LINE 公式アカウントを開く</a></p>'
        )
    parts.append("</div>")
    return "".join(parts)


def build_line_account_line_flex(*, line_url: str, intro_text: str = "", qr_url: str = "") -> Dict[str, Any]:
    body = [p.strip() for p in (intro_text or build_line_account_intro_text(line_url=line_url)).split("\n") if p.strip()]
    if line_url:
        body.append(f"友だち追加: {line_url}")
    if qr_url:
        body.append("QR コードは Web 画面の案内カードをご確認ください。")
    body.append("Web ブラウザでも同じ相談ができます（現在ご覧の画面）。")
    return {
        "variant": "notice",
        "title": "LINE で相談する",
        "subtitle": "友だち追加してチャットを始められます",
        "body_paragraphs": body,
        "hints": ["症状やお薬について、具体的にお書きください。"],
    }


def format_line_account_card(
    *,
    line_url: str,
    qr_url: str = "",
    intro_text: str = "",
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    intro = intro_text or build_line_account_intro_text(line_url=line_url)
    body_parts = [_intro_paragraphs_html(intro)]
    if line_url or qr_url:
        body_parts.append(
            '<section class="chat-status-card__section">'
            '<h5 class="chat-status-card__section-title">友だち追加</h5>'
            + _line_account_section_html(line_url=line_url, qr_url=qr_url)
            + "</section>"
        )
    body_parts.append(
        _list_section(
            "ご案内",
            [
                "LINE でも Web と同じ市販薬相談フローが利用できます",
                "長期記憶や Web 引き継ぎなど LINE 向け機能も提供しています",
                "医療行為・診断・処方の代替ではありません",
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
        title="LINE で相談する",
        subtitle="友だち追加してチャットを始められます",
        body_html="".join(body_parts),
        hints=["症状やお薬について、具体的にお書きください。"],
        footer_html=footer,
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


def build_operator_contact_sections_html() -> str:
    """Sage status カード用 — お問い合わせ・サービス概要（個人属性なし）。"""
    email = _OPERATOR_EMAIL
    return (
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">このサービスについて</h5>'
        "<ul>"
        "<li>研究・検証目的の <strong>β 版（試験運用）</strong> です</li>"
        "<li><strong>医療行為・診断・処方の代替ではありません</strong></li>"
        "<li>運営は個人による開発・運用です</li>"
        "<li>運営者の<strong>氏名・所属・資格など個人を特定しうる情報は開示しません</strong></li>"
        "</ul></section>"
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">お問い合わせ</h5>'
        "<ul>"
        f'<li><strong>E-mail:</strong> <a href="mailto:{html.escape(email, quote=True)}">'
        f"{html.escape(email)}</a></li>"
        f"<li><strong>不具合・お問い合わせフォーム:</strong> "
        f'{_external_link(_OPERATOR_BUG_FORM_URL, "不具合報告フォーム")}</li>'
        "<li>画面上の <strong>🐛</strong> ボタンからも同じフォームに進めます</li>"
        "</ul></section>"
        + _list_section(
            "ご利用上の注意",
            [
                "試験運用のため、動作・表示内容の正確性・安全性を保証しません",
                "お薬の使用は薬剤師・登録販売者・医師などの専門家にご相談ください",
                "詳細な規約は画面右上 ℹ️ の免責事項・利用規約をご確認ください",
            ],
        )
    )


def format_concierge_operator_card(
    *,
    intro_text: str = "",
    feedback_data: Optional[Dict[str, Any]] = None,
) -> str:
    """docs/concierge/お問い合わせ・試験運用.md に基づくカード（リンク付き・個人属性なし）。"""
    body_parts = [_intro_paragraphs_html(intro_text)]
    body_parts.append(build_operator_contact_sections_html())
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
