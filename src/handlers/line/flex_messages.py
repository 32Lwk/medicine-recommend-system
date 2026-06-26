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
from src.handlers.line.flex_status_spec import _normalize_variant, resolve_status_flex_spec
from src.services.recommendation_diagnosis_builder import SAGE_RECO_MARKER
from src.services.status_diagnosis_builder import SAGE_QA_MARKER, SAGE_STATUS_MARKER
from src.handlers.line.line_i18n import (
    carousel_alt_text,
    format_intro,
    format_medicines_summary,
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

TRUNCATE_BULLET = 36
TRUNCATE_MEDICINES_SUMMARY = 220
TRUNCATE_EFFICACY = 140
TRUNCATE_REASON = 140
TRUNCATE_INGREDIENTS = 90
TRUNCATE_PERSONAL_ADVICE = 380
TRUNCATE_OVERLAP = 100

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


_SAGE_CONTENT_MARKERS = frozenset({SAGE_RECO_MARKER, SAGE_STATUS_MARKER, SAGE_QA_MARKER})


def _is_sage_content_marker(text: str | None) -> bool:
    return (text or "").strip() in _SAGE_CONTENT_MARKERS


def _diagnosis_plain_message(diagnosis: dict[str, Any]) -> str:
    from src.utils.sage_message_plain import diagnosis_plain_message

    return diagnosis_plain_message(diagnosis)


def _resolve_bot_plain_text(bot_message: dict[str, Any]) -> str:
    """Sage マーカー保存時は diagnosis から LINE 用プレーンテキストを復元する。"""
    plain = html_to_plain_text(bot_message.get("content"))
    if not _is_sage_content_marker(plain):
        return plain
    diagnosis = bot_message.get("diagnosis")
    if isinstance(diagnosis, dict):
        return _diagnosis_plain_message(diagnosis)
    return ""


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
        rank = med.get("rank")
        if rank is None:
            rank = len(bullets) + 1
        name = med.get("product_name") or ""
        reason = truncate_text(
            med.get("explanation") or med.get("reason"),
            TRUNCATE_BULLET,
        )
        rank_text = format_rank(ui, int(rank))
        if reason:
            bullets.append(f"・{rank_text} {name} — {reason}")
        else:
            angle = _extract_bullet_angle(med.get("explanation") or med.get("reason"), ui)
            bullets.append(f"・{rank_text} {name}（{angle}）")
    return bullets


def _ingredient_blob(med: dict) -> str:
    return " ".join(
        str(med.get(key) or "")
        for key in ("ingredients", "product_name", "efficacy", "explanation")
    ).lower()


def _ingredient_family(med: dict) -> tuple[str, str]:
    blob = _ingredient_blob(med)
    if any(token in blob for token in ("アセトアミノフェン", "acetaminophen", "パラセタモール")):
        return "acetaminophen", "アセトアミノフェン系"
    if any(token in blob for token in ("イブプロフェン", "ibuprofen")):
        return "ibuprofen", "イブプロフェン系"
    if any(token in blob for token in ("ロキソプロフェン", "loxoprofen")):
        return "loxoprofen", "ロキソプロフェン系"
    if any(token in blob for token in ("アスピリン", "aspirin", "サリチル")):
        return "aspirin", "アスピリン系"
    return "other", ""


def _format_medicine_names(medicines: list[dict]) -> str:
    names = [str(m.get("product_name") or "").strip() for m in medicines[:MAX_CAROUSEL_ITEMS]]
    names = [n for n in names if n]
    if not names:
        return ""
    return "、".join(f"「{name}」" for name in names)


def _build_ingredient_group_line(medicines: list[dict], ui: dict[str, str]) -> str:
    groups: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    for med in medicines[:MAX_CAROUSEL_ITEMS]:
        key, label = _ingredient_family(med)
        name = str(med.get("product_name") or "").strip()
        if not name or key == "other":
            continue
        groups.setdefault(key, []).append(name)
        labels[key] = label

    if not groups:
        return ui.get("medicines_difference_fallback", "")

    if len(groups) == 1 and len(medicines) > 1:
        only_label = next(iter(labels.values()))
        hint = ui.get("medicines_same_family_hint", "")
        if hint:
            return hint.format(family=only_label)

    joiner = ui.get("medicines_group_joiner", "と")
    suffix = ui.get("medicines_group_suffix", "")
    parts = [f"{labels[key]}（{'、'.join(names)}）" for key, names in groups.items()]
    line = joiner.join(parts)
    return f"{line}{suffix}" if suffix else line


def build_fallback_personalized_advice(
    symptoms: list[str],
    ui: dict[str, str],
) -> str:
    symptom_text = "・".join(symptoms[:3]) if symptoms else "症状"
    template = ui.get(
        "personalized_advice_fallback",
        "お身体の状態を考慮して、安全に使える市販薬を選んでいます。",
    )
    try:
        return template.format(symptoms=symptom_text)
    except (KeyError, ValueError):
        return template


def build_consolidated_medicines_lines(
    medicines: list[dict],
    ui: dict[str, str],
    *,
    medicine_type: str,
    symptoms: list[str],
) -> list[str]:
    """順位別ではなく、候補をまとめて紹介する文言。"""
    items = medicines[:MAX_CAROUSEL_ITEMS]
    if not items:
        return []

    lines: list[str] = []
    summary = format_medicines_summary(
        ui,
        medicine_type=medicine_type,
        count=len(items),
        symptoms=symptoms,
    )
    if summary:
        lines.append(summary)

    names_line = _format_medicine_names(items)
    if names_line:
        lines.append(names_line)

    group_line = truncate_text(_build_ingredient_group_line(items, ui), TRUNCATE_MEDICINES_SUMMARY)
    if group_line:
        lines.append(group_line)

    carousel_hint = ui.get("medicines_carousel_hint", "")
    if carousel_hint:
        lines.append(carousel_hint)

    return lines


def _symptom_labels(diagnosis: dict | None) -> list[str]:
    if not isinstance(diagnosis, dict):
        return []
    labels: list[str] = []
    for item in diagnosis.get("symptoms") or []:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("symptom") or "").strip()
            if name:
                labels.append(name)
    if labels:
        return labels[:6]
    for med in diagnosis.get("recommended_medicines") or []:
        if not isinstance(med, dict):
            continue
        for key in ("symptoms", "matched_symptoms"):
            raw = med.get(key)
            if isinstance(raw, list) and raw:
                return [str(s).strip() for s in raw if str(s).strip()][:6]
    return []


def _personalized_advice_text(diagnosis: dict | None, bot_message: dict | None = None) -> str:
    if isinstance(diagnosis, dict):
        text = str(diagnosis.get("personalized_advice") or "").strip()
        if text:
            return text
    if bot_message:
        content = bot_message.get("content") or ""
        match = re.search(
            r'aria-label="あなたに合わせたアドバイス"[^>]*>.*?<p[^>]*>(.*?)</p>',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return html_to_plain_text(match.group(1))
    return ""


def _overlap_display_lines(diagnosis: dict | None) -> list[dict[str, str]]:
    if not isinstance(diagnosis, dict):
        return []
    overlap = diagnosis.get("ingredient_overlap")
    if isinstance(overlap, dict):
        severity = str(overlap.get("severity") or "blue")
        badge = {"red": "重複禁止", "yellow": "注意", "blue": "情報"}.get(severity, "注意")
        title = str(overlap.get("title") or "成分の重複について")
        lines: list[dict[str, str]] = []
        for summary in overlap.get("summaries") or []:
            text = truncate_text(str(summary), TRUNCATE_OVERLAP)
            if text:
                lines.append({"badge": badge, "title": title, "text": text})
        if lines:
            return lines[:3]
    return []


def _advice_footer_note(diagnosis: dict | None, ui: dict[str, str]) -> str:
    footer = ui.get("footer_caution", FOOTER_CAUTION_JA)
    if isinstance(diagnosis, dict) and diagnosis.get("doctor_consultation"):
        footer = f"{footer}\n{truncate_text(diagnosis.get('doctor_consultation'), 220)}"
    return footer


def build_recommendation_advice_bubble(
    *,
    diagnosis: dict | None,
    medicines: list[dict],
    ui: dict[str, str],
    bot_message: dict | None = None,
) -> dict[str, Any]:
    """推奨成功時のアドバイス Flex（個別アドバイス → 候補のまとめ → 重複警告）。"""
    medicine_type = ""
    if isinstance(diagnosis, dict):
        medicine_type = str(diagnosis.get("medicine_type") or "OTC医薬品")

    symptoms = _symptom_labels(diagnosis)
    body_contents: list[dict[str, Any]] = []

    advice_text = truncate_text(
        _personalized_advice_text(diagnosis, bot_message),
        TRUNCATE_PERSONAL_ADVICE,
    )
    if not advice_text:
        advice_text = build_fallback_personalized_advice(symptoms, ui)
    body_contents.append(_flex_text(advice_text, size="sm", margin="none"))

    consolidated = build_consolidated_medicines_lines(
        medicines,
        ui,
        medicine_type=medicine_type,
        symptoms=symptoms,
    )
    if consolidated:
        body_contents.append(
            _flex_text(
                ui.get("medicines_intro_label", "おすすめの市販薬"),
                size="xs",
                color=LABEL,
                weight="bold",
                margin="lg",
            )
        )
        for i, line in enumerate(consolidated):
            is_hint = i == len(consolidated) - 1
            body_contents.append(
                _flex_text(
                    line,
                    size="xs" if is_hint else "sm",
                    color=NOTE if is_hint else None,
                    margin="sm" if i == 0 else "xs",
                )
            )

    for overlap in _overlap_display_lines(diagnosis):
        body_contents.append(
            _flex_text(
                f"{overlap['badge']} {overlap['title']}",
                size="xs",
                color="#C62828" if overlap["badge"] == "重複禁止" else "#E65100" if overlap["badge"] == "注意" else LABEL,
                weight="bold",
                margin="md",
            )
        )
        body_contents.append(_flex_text(overlap["text"], size="xs", margin="xs"))

    web_hint = ui.get("web_detail_hint", "")
    if web_hint:
        body_contents.append(_flex_text(web_hint, size="xxs", color=NOTE, margin="md"))

    body_contents.append(
        _flex_text(_advice_footer_note(diagnosis, ui), size="xs", color=NOTE, margin="md")
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


def append_web_handoff_messages(
    messages: list[dict[str, Any]],
    *,
    session_id: str | None,
    ui: dict[str, str],
) -> list[dict[str, Any]]:
    """LINE セッション向けに Web 詳細確認リンク Flex を末尾追加。"""
    if not session_id:
        return messages
    from src.handlers.line.line_session import is_line_session_id

    if not is_line_session_id(session_id):
        return messages
    from src.handlers.line.line_web_handoff import issue_handoff_token

    token = issue_handoff_token(session_id)
    if not token:
        return messages
    resume_url = f"{_public_site_base()}/resume/{token}"
    return [*messages, build_web_continue_flex(resume_url, ui)]


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
    ingredients = truncate_text(medicine.get("ingredients"), TRUNCATE_INGREDIENTS)
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
    ]
    if ingredients:
        body_contents.extend([
            {
                "type": "text",
                "text": ui.get("ingredients_label", "主な成分"),
                "size": "xs",
                "color": LABEL,
                "weight": "bold",
                "margin": "md",
            },
            {"type": "text", "text": ingredients, "size": "xs", "wrap": True, "margin": "xs", "color": NOTE},
        ])
    body_contents.extend([
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
    ])

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


def build_web_continue_flex(resume_url: str, ui: dict[str, str]) -> dict[str, Any]:
    """LINE から Web へ引き継ぐ URI ボタン付き Flex。"""
    label = ui.get("web_continue_label", "詳細をブラウザで見る")
    title = ui.get("web_continue_title", "詳細をブラウザで確認")
    body = ui.get("web_continue_body", "")
    detail_items = ui.get("web_continue_details", "")
    body_contents: list[dict[str, Any]] = [
        {"type": "text", "text": title, "weight": "bold", "size": "sm", "wrap": True},
        {"type": "text", "text": body, "size": "xs", "color": "#666666", "wrap": True, "margin": "sm"},
    ]
    if detail_items:
        body_contents.append(
            {"type": "text", "text": detail_items, "size": "xxs", "color": NOTE, "wrap": True, "margin": "sm"}
        )
    body_contents.append(
        {
            "type": "button",
            "style": "primary",
            "height": "sm",
            "color": PRIMARY,
            "action": {"type": "uri", "label": label, "uri": resume_url},
        }
    )
    return {
        "type": "flex",
        "altText": label,
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "12px",
                "contents": body_contents,
            },
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


_PLAIN_TEXT_CONCIERGE_INTENTS = frozenset(
    {"greeting", "thanks", "chitchat", "redirect", "medical_handoff"}
)


def _try_sage_diagnosis_status_flex(
    bot_message: dict[str, Any],
    *,
    footer: str,
    ui: dict[str, str],
) -> list[dict[str, Any]] | None:
    diagnosis = bot_message.get("diagnosis")
    if not isinstance(diagnosis, dict):
        return None
    if diagnosis.get("render") not in ("sage_status", "sage_qa"):
        return None
    if diagnosis.get("layout") == "plain":
        return None
    title = str(diagnosis.get("title") or "").strip()
    if not title:
        return None
    message = _diagnosis_plain_message(diagnosis)
    hints = [str(h).strip() for h in (diagnosis.get("hints") or []) if str(h).strip()]
    return _status_flex_message(
        _normalize_variant(str(diagnosis.get("variant") or "info")),
        title=title,
        alt_text=title,
        subtitle=str(diagnosis.get("subtitle") or "").strip(),
        body_paragraphs=[message] if message else None,
        hints=hints or None,
        footer_note=footer,
        ui=ui,
    )


def _plain_text_line_messages(bot_message: dict) -> list[dict[str, Any]] | None:
    """
    挨拶・雑談・カウンセリング・医薬品Q&Aなど、Flex 化しない会話はテキストで返す。
    """
    plain = _resolve_bot_plain_text(bot_message)
    if bot_message.get("greeting") or bot_message.get("counseling") or bot_message.get("ask"):
        if not plain:
            return None
        return _text_messages_from_plain(plain, footer="")

    if bot_message.get("concierge"):
        intent = (bot_message.get("concierge_intent") or "").strip()
        fmt = (bot_message.get("content_format") or "text").strip()
        if fmt == "text" or intent in _PLAIN_TEXT_CONCIERGE_INTENTS:
            if not plain:
                return None
            return _text_messages_from_plain(plain, footer="")
        return None

    if "diagnosis" in bot_message and bot_message.get("diagnosis") is None:
        if not plain:
            return None
        return _text_messages_from_plain(plain, footer="")

    return None


def _status_flex_message(
    variant: str,
    *,
    title: str,
    alt_text: str,
    subtitle: str = "",
    body_paragraphs: list[str] | None = None,
    hints: list[str] | None = None,
    footer_note: str,
    ui: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        build_status_bubble(
            variant,
            title=title,
            alt_text=alt_text,
            subtitle=subtitle,
            body_paragraphs=body_paragraphs,
            hints=hints,
            footer_note=footer_note,
            ui=ui,
        )
    ]


def _status_flex_from_spec(
    spec: dict[str, Any],
    *,
    default_footer: str,
    ui: dict[str, str],
) -> list[dict[str, Any]]:
    return _status_flex_message(
        str(spec.get("variant") or "info"),
        title=str(spec.get("title") or ""),
        alt_text=str(spec.get("alt_text") or spec.get("title") or ""),
        subtitle=str(spec.get("subtitle") or ""),
        body_paragraphs=list(spec.get("body_paragraphs") or []),
        hints=list(spec.get("hints") or []),
        footer_note=str(spec.get("footer_note") or default_footer),
        ui=ui,
    )


def _try_resolved_status_flex(
    bot_message: dict[str, Any],
    *,
    footer: str,
    ui: dict[str, str],
) -> list[dict[str, Any]] | None:
    spec = resolve_status_flex_spec(bot_message)
    if not spec:
        return None
    return _status_flex_from_spec(spec, default_footer=footer, ui=ui)


def build_line_messages_from_bot_message(
    bot_message: dict,
    *,
    lang: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    bot メッセージから LINE Messaging API 用 messages 配列を生成する。
    挨拶・雑談等はテキスト。推奨成功時は flex 2件（advice + carousel）。
    エスカレーション・追加質問等は status Flex bubble 1件。
    """
    ui = get_line_ui_strings(lang)
    code = normalize_line_lang(lang)
    footer = ui.get("footer_caution", FOOTER_CAUTION_JA)

    plain_messages = _plain_text_line_messages(bot_message)
    if plain_messages is not None:
        return plain_messages

    if bot_message.get("crisis_support") or bot_message.get("emergency_detected"):
        plain = _resolve_bot_plain_text(bot_message)
        title = ui.get("status_critical_title", "")
        return _status_flex_message(
            "critical",
            title=title,
            alt_text=title,
            body_paragraphs=[plain] if plain else None,
            hints=[
                ui.get("status_critical_hint_1", ""),
                ui.get("status_critical_hint_2", ""),
            ],
            footer_note=footer,
            ui=ui,
        )

    diagnosis = bot_message.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis = translate_flex_fields(diagnosis, code, session_id=session_id)

    if isinstance(diagnosis, dict):
        status = (diagnosis.get("status") or "").strip()
        if status in _ESCALATION_STATUSES:
            consult = str(diagnosis.get("doctor_consultation") or "").strip()
            usage = str(diagnosis.get("usage_notes") or "").strip()
            body_paragraphs = [p for p in (consult, usage) if p]
            if not body_paragraphs:
                body_paragraphs = [ui.get("pharmacist_fallback", "")]
            variant = "critical" if status == "escalation_required" else "caution"
            title = ui.get(
                "status_critical_title" if variant == "critical" else "status_caution_title",
                "",
            )
            hints = (
                [ui.get("status_escalation_hint_1", ""), ui.get("status_escalation_hint_2", "")]
                if variant == "critical"
                else [ui.get("status_caution_hint_1", ""), ui.get("status_caution_hint_2", "")]
            )
            subtitle = ui.get("status_escalation_subtitle", "") if variant == "critical" else ""
            return _status_flex_message(
                variant,
                title=title,
                alt_text=title,
                subtitle=subtitle,
                body_paragraphs=body_paragraphs,
                hints=hints,
                footer_note=footer,
                ui=ui,
            )

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
            title = ui.get("status_notice_title", "")
            return _status_flex_message(
                "notice",
                title=title,
                alt_text=title,
                body_paragraphs=[ui.get("status_questions_intro", "")],
                hints=q_lines,
                footer_note=footer,
                ui=ui,
            )
        resolved = _try_resolved_status_flex(bot_message, footer=footer, ui=ui)
        if resolved:
            return resolved
        sage_status = _try_sage_diagnosis_status_flex(bot_message, footer=footer, ui=ui)
        if sage_status:
            return sage_status
        plain = _resolve_bot_plain_text(bot_message)
        if plain and not _is_sage_content_marker(plain):
            title = ui.get("status_info_title", "")
            return _status_flex_message(
                "info",
                title=title,
                alt_text=title,
                body_paragraphs=[plain],
                footer_note=footer,
                ui=ui,
            )
        title = ui.get("status_caution_title", "")
        return _status_flex_message(
            "caution",
            title=title,
            alt_text=title,
            body_paragraphs=[ui.get("pharmacist_fallback", "")],
            hints=[ui.get("status_caution_hint_2", "")],
            footer_note=footer,
            ui=ui,
        )

    advice = build_recommendation_advice_bubble(
        diagnosis=diagnosis if isinstance(diagnosis, dict) else None,
        medicines=medicines,
        ui=ui,
        bot_message=bot_message,
    )
    carousel = build_recommendation_carousel(medicines, ui)
    messages: list[dict[str, Any]] = [advice, carousel]
    return append_web_handoff_messages(messages, session_id=session_id, ui=ui)
