"""
LINE Flex Message JSON ビルダー（純関数・テスト可能）。

hero 画像は v1 では省略（Noimage）。将来は build_medicine_bubble(..., hero_url=...) で拡張可能。
"""
from __future__ import annotations

import copy
import logging
import re
from html.parser import HTMLParser
from typing import Any

from src.handlers.line.line_i18n import (
    carousel_alt_text,
    format_intro,
    format_rank,
    format_score_label,
    get_line_ui_strings,
    normalize_line_lang,
)

logger = logging.getLogger(__name__)

PRIMARY = "#0D9488"
SCORE_MEDIUM = "#CA8A04"
LABEL = "#8c8c8c"
NOTE = "#666666"

TRUNCATE_BULLET = 20
TRUNCATE_EFFICACY = 120
TRUNCATE_REASON = 100

MAX_CAROUSEL_ITEMS = 3
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
    return "low", LABEL, percent


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


def build_medicine_bubble(
    medicine: dict,
    *,
    rank: int,
    ui: dict[str, str],
    hero_url: str | None = None,  # noqa: ARG001 — 将来 hero 画像用
) -> dict[str, Any]:
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


def build_line_messages_from_bot_message(
    bot_message: dict,
    *,
    lang: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    bot メッセージから LINE Messaging API 用 messages 配列を生成する。
    成功時は flex 2件（advice + carousel）。安全系はテキストのみ。
    """
    ui = get_line_ui_strings(lang)
    code = normalize_line_lang(lang)

    if bot_message.get("crisis_support") or bot_message.get("emergency_detected"):
        plain = html_to_plain_text(bot_message.get("content"))
        return [_text_message(plain or ui.get("footer_caution", FOOTER_CAUTION_JA))]

    diagnosis = bot_message.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis = translate_flex_fields(diagnosis, code, session_id=session_id)

    if isinstance(diagnosis, dict):
        status = (diagnosis.get("status") or "").strip()
        if status in _ESCALATION_STATUSES:
            consult = diagnosis.get("doctor_consultation") or ""
            usage = diagnosis.get("usage_notes") or ""
            text = "\n".join(p for p in (consult, usage) if p).strip()
            if not text:
                text = ui.get("pharmacist_fallback", "")
            return [_text_message(text)]

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
            qtext = "\n".join(str(q) for q in questions if q)
            return [_text_message(qtext)]
        plain = html_to_plain_text(bot_message.get("content"))
        if plain:
            return [_text_message(plain)]
        return [_text_message(ui.get("pharmacist_fallback", ""))]

    medicine_type = ""
    if isinstance(diagnosis, dict):
        medicine_type = str(diagnosis.get("medicine_type") or "OTC医薬品")
    intro = format_intro(ui, medicine_type=medicine_type, count=len(medicines[:MAX_CAROUSEL_ITEMS]))
    bullets = build_advice_bullets(medicines, ui)
    footer = ui.get("footer_caution", FOOTER_CAUTION_JA)
    if isinstance(diagnosis, dict) and diagnosis.get("doctor_consultation"):
        footer = f"{footer}\n{truncate_text(diagnosis.get('doctor_consultation'), 200)}"

    advice = build_advice_bubble(intro=intro, bullets=bullets, footer_note=footer, ui=ui)
    carousel = build_recommendation_carousel(medicines, ui)
    return [advice, carousel]
