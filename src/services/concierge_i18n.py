"""Concierge 応答の多言語化（問い合わせ言語へ Translate / DeepL）。"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _translate_text(text: str, lang: str, *, session_id: Optional[str] = None) -> str:
    if not text or lang == "ja":
        return text
    from src.core.translation_service import translate_medicine_recommendation

    out = translate_medicine_recommendation(text, lang, session_id=session_id)
    return out if out else text


def _translate_diagnosis(diag: Dict[str, Any], lang: str, *, session_id: Optional[str] = None) -> Dict[str, Any]:
    out = dict(diag)
    for key in ("message", "title", "subtitle"):
        if out.get(key):
            out[key] = _translate_text(str(out[key]), lang, session_id=session_id)
    hints = out.get("hints")
    if isinstance(hints, list):
        out["hints"] = [
            _translate_text(str(h), lang, session_id=session_id) for h in hints if h
        ]
    sections = out.get("sections")
    if isinstance(sections, list):
        new_sections = []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            s = dict(sec)
            if s.get("title"):
                s["title"] = _translate_text(str(s["title"]), lang, session_id=session_id)
            items = s.get("items")
            if isinstance(items, list):
                s["items"] = [
                    _translate_text(str(i), lang, session_id=session_id) for i in items if i
                ]
            new_sections.append(s)
        out["sections"] = new_sections
    return out


def apply_concierge_payload_i18n(
    session: Any,
    payload: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """セッション言語が ja 以外のとき sage_diagnosis / テキスト本文を翻訳する。"""
    from src.core.language_utils import resolve_session_language

    lang = resolve_session_language(session)
    if lang == "ja":
        return payload

    out = dict(payload)
    if out.get("content_format") == "text" and isinstance(out.get("content"), str):
        out["content"] = _translate_text(out["content"], lang, session_id=session_id)

    diag = out.get("sage_diagnosis")
    if isinstance(diag, dict):
        out["sage_diagnosis"] = _translate_diagnosis(diag, lang, session_id=session_id)

    intent = str(out.get("concierge_intent") or "")
    message = ""
    if isinstance(out.get("sage_diagnosis"), dict):
        message = str(out["sage_diagnosis"].get("message") or "")
    if message and intent:
        try:
            from src.services.concierge_templates import build_dynamic_concierge_line_flex

            hints = []
            if isinstance(out.get("sage_diagnosis"), dict):
                raw_hints = out["sage_diagnosis"].get("hints")
                if isinstance(raw_hints, list):
                    hints = [str(h) for h in raw_hints if h]
            title = str(out["sage_diagnosis"].get("title") or "ご案内")
            out["line_flex"] = build_dynamic_concierge_line_flex(
                title=title,
                body_text=message,
                hints=hints,
                intent=intent.replace("concierge_", ""),
            )
        except Exception:
            pass
    return out
