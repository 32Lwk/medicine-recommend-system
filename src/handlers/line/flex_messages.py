"""
LINE Flex Message JSON ビルダー（純関数・テスト可能）。

商品画像がない場合は hero に No Image プレースホルダー（static/line/medicine-noimage-hero.png）を表示する。
"""
from __future__ import annotations

import copy
import logging
import os
import re
from html.parser import HTMLParser
from typing import Any

from config.line_config import LINE_HERO_PLACEHOLDER_URL
from src.handlers.line.line_i18n import (
    carousel_alt_text,
    format_intro,
    format_rank,
    format_score_label,
    get_line_ui_strings,
    normalize_line_lang,
)

logger = logging.getLogger(__name__)

# パステル寄り sage / pamphlet パレット（LINE Flex）
PRIMARY = "#5AB8A8"
SCORE_MEDIUM = "#C9A84C"
SCORE_LOW = "#8FA3AD"
LABEL = "#7A8F94"
NOTE = "#5F7278"

_STATUS_HEADER: dict[str, str] = {
    "caution": "#E8C97A",
    "critical": "#E8A0A8",
    "notice": "#8EB8E8",
    "info": PRIMARY,
    "error": "#E8A0A0",
}

_LINE_HERO_PLACEHOLDER_PATH = "/static/line/medicine-noimage-hero.png"
_DEFAULT_PUBLIC_SITE_URL = "https://medicine.yutok.dev"


def _public_site_base() -> str:
    return (os.getenv("PUBLIC_SITE_URL") or _DEFAULT_PUBLIC_SITE_URL).strip().rstrip("/")

TRUNCATE_BULLET = 20
TRUNCATE_EFFICACY = 120
TRUNCATE_REASON = 100

MAX_CAROUSEL_ITEMS = 3
LINE_TEXT_MAX = 5000
FOOTER_CAUTION_JA = "用法用量を守り、症状が続く場合は医師・薬剤師にご相談ください。"

_ESCALATION_STATUSES = frozenset(
    {"escalation_required", "no_candidates", "error", "blocked"}
)


def truncate_text(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    s = str(text).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._parts)).strip()


def html_to_plain_text(html: str | None) -> str:
    if not html:
        return ""
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return re.sub(r"<[^>]+>", "", html).strip()
    return parser.get_text()


def _score_tier(display_score: float | int | None) -> tuple[str, str, int]:
    """Returns (level, color, percent_int)."""
    if display_score is None:
        return "medium", SCORE_MEDIUM, 0
    try:
        score = float(display_score)
    except (TypeError, ValueError):
        return "medium", SCORE_MEDIUM, 0
    if score <= 10:
        percent = int(round(score * 10))
    else:
        percent = int(round(score))
    percent = max(0, min(100, percent))
    if percent >= 80:
        return "high", PRIMARY, percent
    if percent >= 60:
        return "medium", SCORE_MEDIUM, percent
    return "low", SCORE_LOW, percent


def _extract_bullet_angle(explanation: str | None, ui: dict[str, str]) -> str:
    text = (explanation or "").strip()
    if not text:
        return ui.get("bullet_fallback_angle", "おすすめ")
    for sep in ("。", "、", ",", "・", "；", ";"):
        if sep in text:
            clause = text.split(sep)[0].strip()
            if clause:
                return truncate_text(clause, TRUNCATE_BULLET)
    return truncate_text(text, TRUNCATE_BULLET)


def build_advice_bullets(medicines: list[dict], ui: dict[str, str]) -> list[str]:
    bullets: list[str] = []
    for med in medicines[:MAX_CAROUSEL_ITEMS]:
        reason = med.get("explanation") or med.get("reason") or ""
        angle = _extract_bullet_angle(reason, ui)
        name = med.get("product_name") or ""
        bullets.append(f"・{angle}:{name}")
    return bullets


def translate_flex_fields(
    diagnosis: dict | None,
    lang: str | None,
    *,
    session_id: str | None = None,
) -> dict | None:
    if not diagnosis:
        return diagnosis
    code = normalize_line_lang(lang)
    if code == "ja":
        return diagnosis

    from src.core.translation_service import translate_medicine_recommendation

    def _tr(text: str | None) -> str:
        if not text:
            return ""
        try:
            out = translate_medicine_recommendation(text, code, session_id=session_id)
            return out if out else text
        except Exception:
            logger.warning("LINE flex field translation failed", exc_info=True)
            return text

    result = copy.deepcopy(diagnosis)
    meds_out: list[dict] = []
    for med in result.get("recommended_medicines") or []:
        nm = dict(med)
        for field in ("product_name", "efficacy", "explanation", "reason", "usage_notes"):
            if nm.get(field):
                nm[field] = _tr(str(nm[field]))
        meds_out.append(nm)
    result["recommended_medicines"] = meds_out
    for field in ("usage_notes", "doctor_consultation", "medicine_type"):
        if result.get(field):
            result[field] = _tr(str(result[field]))
    return result


def _flex_text(
    text: str,
    *,
    size: str = "sm",
    color: str | None = None,
    weight: str | None = None,
    margin: str = "none",
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "text",
        "text": text,
        "wrap": True,
        "size": size,
        "margin": margin,
    }
    if color:
        block["color"] = color
    if weight:
        block["weight"] = weight
    return block


def build_status_bubble(
    variant: str,
    *,
    title: str,
    alt_text: str,
    subtitle: str = "",
    body_paragraphs: list[str] | None = None,
    hints: list[str] | None = None,
    footer_note: str = "",
    ui: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Web の chat-status-card 風ステータス bubble（Flex Message 1件）。
    Flex Simulator 用: scripts/export_line_flex_simulator_samples.py
    """
    header_color = _STATUS_HEADER.get(variant, PRIMARY)
    body_contents: list[dict[str, Any]] = []
    if subtitle:
        body_contents.append(_flex_text(subtitle, size="xs", color=LABEL, margin="none"))
    for i, para in enumerate(body_paragraphs or []):
        if not para:
            continue
        body_contents.append(
            _flex_text(para, size="sm", weight="bold" if i == 0 and variant == "critical" else None, margin="md" if body_contents else "none")
        )
    hint_items = [h for h in (hints or []) if h]
    if hint_items:
        hints_label = (ui or {}).get("status_hints_label", "次にできること")
        body_contents.append(_flex_text(hints_label, size="xs", color=LABEL, weight="bold", margin="md"))
        for j, hint in enumerate(hint_items):
            body_contents.append(_flex_text(f"・{hint}", size="xs", margin="xs" if j else "sm"))
    if footer_note:
        body_contents.append(_flex_text(footer_note, size="xs", color=NOTE, margin="md"))
    if not body_contents:
        body_contents.append(_flex_text("—", size="sm"))

    return {
        "type": "flex",
        "altText": alt_text,
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": header_color,
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff",
                        "align": "center",
                        "wrap": True,
                    }
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": body_contents,
            },
        },
    }


def build_advice_bubble(
    *,
    intro: str,
    bullets: list[str],
    footer_note: str,
    ui: dict[str, str],
) -> dict[str, Any]:
    body_contents: list[dict[str, Any]] = [
        {"type": "text", "text": intro, "wrap": True, "size": "sm", "margin": "none"},
    ]
    for i, bullet in enumerate(bullets):
        body_contents.append(
            {
                "type": "text",
                "text": bullet,
                "wrap": True,
                "size": "sm",
                "margin": "md" if i == 0 else "xs",
            }
        )
    body_contents.append(
        {
            "type": "text",
            "text": footer_note,
            "wrap": True,
            "size": "xs",
            "color": NOTE,
            "margin": "md",
        }
    )
    return {
        "type": "flex",
        "altText": ui.get("advice_alt", "あなたに合わせたアドバイス"),
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": PRIMARY,
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": ui.get("advice_header", "あなたに合わせたアドバイス"),
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff",
                        "align": "center",
                    }
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": body_contents,
            },
        },
    }


def resolve_medicine_hero_url(medicine: dict) -> str:
    """商品画像 URL があればそれを、なければ No Image プレースホルダーを返す。"""
    for key in ("image_url", "hero_url", "product_image_url"):
        val = (medicine.get(key) or "").strip()
        if val.startswith("https://"):
            return val
    if LINE_HERO_PLACEHOLDER_URL.startswith("https://"):
        return LINE_HERO_PLACEHOLDER_URL
    return f"{_public_site_base()}{_LINE_HERO_PLACEHOLDER_PATH}"


def build_medicine_bubble(
    medicine: dict,
    *,
    rank: int,
    ui: dict[str, str],
    hero_url: str | None = None,
) -> dict[str, Any]:  # hero_url はテスト・上書き用
    product_name = medicine.get("product_name") or ""
    manufacturer = medicine.get("manufacturer") or ""
    efficacy = truncate_text(medicine.get("efficacy"), TRUNCATE_EFFICACY)
    reason = truncate_text(
        medicine.get("explanation") or medicine.get("reason"),
        TRUNCATE_REASON,
    )
    usage = truncate_text(medicine.get("usage_notes"), TRUNCATE_REASON)
    level, score_color, percent = _score_tier(
        medicine.get("display_score") if medicine.get("display_score") is not None else medicine.get("score")
    )
    score_text = format_score_label(ui, level, percent)
    rank_text = format_rank(ui, rank)

    body_contents: list[dict[str, Any]] = [
        {"type": "text", "text": rank_text, "size": "xs", "color": PRIMARY, "weight": "bold", "margin": "none"},
        {"type": "text", "text": product_name, "weight": "bold", "size": "lg", "wrap": True, "margin": "sm"},
        {"type": "text", "text": manufacturer, "size": "xs", "color": LABEL, "wrap": True, "margin": "xs"},
        {"type": "separator", "margin": "sm"},
        {
            "type": "text",
            "text": ui.get("efficacy_label", "効能・効果"),
            "size": "xs",
            "color": LABEL,
            "weight": "bold",
            "margin": "sm",
        },
        {"type": "text", "text": efficacy or "—", "size": "sm", "wrap": True, "margin": "xs"},
        {
            "type": "text",
            "text": ui.get("reason_label", "推奨理由"),
            "size": "xs",
            "color": LABEL,
            "weight": "bold",
            "margin": "md",
        },
        {"type": "text", "text": reason or "—", "size": "sm", "wrap": True, "margin": "xs"},
        {
            "type": "box",
            "layout": "baseline",
            "margin": "md",
            "contents": [
                {"type": "text", "text": ui.get("score_label", "おすすめ度"), "size": "xs", "color": LABEL, "flex": 0},
                {
                    "type": "text",
                    "text": score_text,
                    "size": "sm",
                    "color": score_color,
                    "weight": "bold",
                    "flex": 0,
                },
            ],
        },
        {
            "type": "text",
            "text": f"{ui.get('usage_prefix', '使用上の注意')}: {usage or ui.get('footer_caution', FOOTER_CAUTION_JA)}",
            "size": "xs",
            "color": NOTE,
            "wrap": True,
            "margin": "sm",
        },
    ]

    bubble: dict[str, Any] = {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    bubble["hero"] = {
        "type": "image",
        "url": hero_url or resolve_medicine_hero_url(medicine),
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover",
    }
    return bubble


def build_recommendation_carousel(medicines: list[dict], ui: dict[str, str]) -> dict[str, Any]:
    items = medicines[:MAX_CAROUSEL_ITEMS]
    bubbles = [
        build_medicine_bubble(med, rank=i + 1, ui=ui) for i, med in enumerate(items)
    ]
    return {
        "type": "flex",
        "altText": carousel_alt_text(ui, len(bubbles)),
        "contents": {
            "type": "carousel",
            "contents": bubbles,
        },
    }


def _text_message(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _text_messages_from_plain(text: str, *, footer: str = "") -> list[dict[str, Any]]:
    """Web の本文相当を LINE テキストメッセージにする（5000 文字で分割）。"""
    body = (text or "").strip()
    if footer:
        body = f"{body}\n\n{footer}".strip() if body else footer.strip()
    if not body:
        body = "—"
    out: list[dict[str, Any]] = []
    pos = 0
    while pos < len(body):
        out.append(_text_message(body[pos : pos + LINE_TEXT_MAX]))
        pos += LINE_TEXT_MAX
    return out


def _text_with_hints(
    plain: str,
    hints: list[str],
    *,
    footer: str,
    ui: dict[str, str],
) -> list[dict[str, Any]]:
    parts: list[str] = []
    if plain:
        parts.append(plain.strip())
    hint_items = [h for h in hints if h]
    if hint_items:
        label = ui.get("status_hints_label", "次にできること")
        parts.append(label)
        parts.extend(f"・{h}" for h in hint_items)
    return _text_messages_from_plain("\n".join(parts), footer=footer)


def build_line_messages_from_bot_message(
    bot_message: dict,
    *,
    lang: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    bot メッセージから LINE Messaging API 用 messages 配列を生成する。
    推奨成功時は flex 2件（advice + carousel）。それ以外の本文はテキストメッセージ。
    """
    ui = get_line_ui_strings(lang)
    code = normalize_line_lang(lang)
    footer = ui.get("footer_caution", FOOTER_CAUTION_JA)

    if bot_message.get("crisis_support") or bot_message.get("emergency_detected"):
        plain = html_to_plain_text(bot_message.get("content"))
        return _text_with_hints(
            plain,
            [
                ui.get("status_critical_hint_1", ""),
                ui.get("status_critical_hint_2", ""),
            ],
            footer=footer,
            ui=ui,
        )

    diagnosis = bot_message.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis = translate_flex_fields(diagnosis, code, session_id=session_id)

    if isinstance(diagnosis, dict):
        status = (diagnosis.get("status") or "").strip()
        if status in _ESCALATION_STATUSES:
            consult = diagnosis.get("doctor_consultation") or ""
            usage = diagnosis.get("usage_notes") or ""
            body = "\n".join(p for p in (consult, usage) if p).strip()
            if not body:
                body = ui.get("pharmacist_fallback", "")
            variant = "critical" if status == "escalation_required" else "caution"
            hints = (
                [ui.get("status_escalation_hint_1", ""), ui.get("status_escalation_hint_2", "")]
                if variant == "critical"
                else [ui.get("status_caution_hint_1", ""), ui.get("status_caution_hint_2", "")]
            )
            subtitle = ui.get("status_escalation_subtitle", "") if variant == "critical" else ""
            parts = [p for p in (subtitle, body) if p]
            return _text_with_hints("\n".join(parts), hints, footer=footer, ui=ui)

    medicines: list[dict] = []
    if isinstance(diagnosis, dict):
        raw = diagnosis.get("recommended_medicines")
        if isinstance(raw, list):
            medicines = [m for m in raw if isinstance(m, dict)]

    if not medicines:
        questions = []
        if isinstance(diagnosis, dict):
            questions = diagnosis.get("additional_questions") or diagnosis.get("critical_questions") or []
        if questions:
            q_lines = [str(q) for q in questions if q]
            return _text_with_hints(
                ui.get("status_questions_intro", ""),
                q_lines,
                footer=footer,
                ui=ui,
            )
        plain = html_to_plain_text(bot_message.get("content"))
        if plain:
            return _text_messages_from_plain(plain, footer=footer)
        return _text_with_hints(
            ui.get("pharmacist_fallback", ""),
            [ui.get("status_caution_hint_2", "")],
            footer=footer,
            ui=ui,
        )

    medicine_type = ""
    if isinstance(diagnosis, dict):
        medicine_type = str(diagnosis.get("medicine_type") or "OTC医薬品")
    intro = format_intro(ui, medicine_type=medicine_type, count=len(medicines[:MAX_CAROUSEL_ITEMS]))
    bullets = build_advice_bullets(medicines, ui)
    advice_footer = ui.get("footer_caution", FOOTER_CAUTION_JA)
    if isinstance(diagnosis, dict) and diagnosis.get("doctor_consultation"):
        advice_footer = f"{advice_footer}\n{truncate_text(diagnosis.get('doctor_consultation'), 200)}"

    advice = build_advice_bubble(intro=intro, bullets=bullets, footer_note=advice_footer, ui=ui)
    carousel = build_recommendation_carousel(medicines, ui)
    return [advice, carousel]
