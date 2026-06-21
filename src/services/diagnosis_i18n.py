"""Field-level translation for diagnosis v1 payloads."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_TRANSLATABLE_FIELDS = (
    "personalized_advice",
    "doctor_consultation",
    "message",
    "title",
    "subtitle",
)


def translate_diagnosis_fields(
    diagnosis: dict[str, Any],
    lang: str,
    client: Any,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Translate plain-text diagnosis fields into diagnosis.i18n[lang]."""
    if not diagnosis or lang in ("ja", "", None):
        return diagnosis
    if lang == "ja":
        return diagnosis

    out = dict(diagnosis)
    i18n_bucket: dict[str, Any] = {}
    render = out.get("render")

    try:
        from src.core.translation_service import translate_medicine_recommendation as translate_text_field
    except ImportError:
        logger.warning("translation_service unavailable; skipping diagnosis i18n")
        return out

    if render == "sage_reco":
        for key in ("personalized_advice", "doctor_consultation"):
            val = out.get(key)
            if val and isinstance(val, str):
                translated = translate_text_field(val, lang, client, session_id=session_id)
                if translated:
                    i18n_bucket[key] = translated
        err = out.get("error")
        if isinstance(err, dict):
            err_i18n = dict(err)
            for key in ("title", "message"):
                if err.get(key):
                    translated = translate_text_field(
                        str(err[key]), lang, client, session_id=session_id
                    )
                    if translated:
                        err_i18n[key] = translated
            if err_i18n != err:
                i18n_bucket["error"] = err_i18n
        for sec in out.get("usage_sections") or []:
            if not isinstance(sec, dict):
                continue
            items = sec.get("items") or []
            if items:
                sec_i18n = []
                for item in items:
                    if isinstance(item, str) and item.strip():
                        sec_i18n.append(
                            translate_text_field(item, lang, client, session_id=session_id)
                            or item
                        )
                    else:
                        sec_i18n.append(item)
                sec.setdefault("_i18n", {})[lang] = {"items": sec_i18n}

    elif render in ("sage_status", "sage_qa"):
        for key in ("title", "subtitle", "message"):
            val = out.get(key)
            if val and isinstance(val, str):
                translated = translate_text_field(val, lang, client, session_id=session_id)
                if translated:
                    i18n_bucket[key] = translated
        hints = out.get("hints") or []
        if hints:
            i18n_bucket["hints"] = [
                translate_text_field(str(h), lang, client, session_id=session_id) or str(h)
                for h in hints
            ]

    if i18n_bucket:
        existing = out.get("i18n") or {}
        existing[lang] = {**(existing.get(lang) or {}), **i18n_bucket}
        out["i18n"] = existing
    return out
