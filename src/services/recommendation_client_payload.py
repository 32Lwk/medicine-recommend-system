"""推奨結果を Web クライアント（Sage Terrace / SSE）向けに正規化する。"""
from __future__ import annotations

from typing import Any


def is_sage_web_ui(session: Any) -> bool:
    """Web チャットで Sage UI カード描画を使うか。"""
    from config.ui_config import UI_SAGE_TERRACE_ENABLED, UI_VARIANT_SAGE

    if session is not None:
        variant = session.get("ui_variant")
        if variant:
            return variant == UI_VARIANT_SAGE
    return bool(UI_SAGE_TERRACE_ENABLED)


def _symptom_names(symptoms: list[Any] | None) -> list[str]:
    if not symptoms:
        return []
    out: list[str] = []
    for s in symptoms:
        if isinstance(s, str) and s.strip():
            out.append(s.strip())
        elif isinstance(s, dict):
            name = s.get("name") or s.get("symptom") or ""
            if name:
                out.append(str(name).strip())
        elif s is not None:
            out.append(str(s).strip())
    return out[:8]


def enrich_recommended_medicines(
    medicines: list[dict[str, Any]] | None,
    *,
    medicine_type: str | None = None,
    symptoms: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """diagnosis / SSE 用に医薬品 dict を補完（インプレースではなくコピーを返す）。"""
    if not medicines:
        return []
    symptom_list = _symptom_names(symptoms)
    enriched: list[dict[str, Any]] = []
    for med in medicines:
        row = dict(med)
        if medicine_type and not row.get("medicine_type"):
            row["medicine_type"] = medicine_type
        if symptom_list and not row.get("symptoms") and not row.get("matched_symptoms"):
            row["symptoms"] = symptom_list
        if not row.get("score_breakdown"):
            row["score_breakdown"] = row.get("scores") or row.get("score_breakdown")
        if not row.get("image_url"):
            for key in ("imageUrl", "hero_url", "product_image_url"):
                if row.get(key):
                    row["image_url"] = row[key]
                    break
        enriched.append(row)
    return enriched
