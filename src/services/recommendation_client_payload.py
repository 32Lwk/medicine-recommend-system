"""推奨結果を Web クライアント（Sage Terrace / SSE）向けに正規化する。"""
from __future__ import annotations

from typing import Any

from src.services.medicine_image_urls import enrich_medicine_image_url


def is_sage_web_ui(session: Any) -> bool:
    """Web チャットで Sage UI カード描画を使うか。"""
    from config.ui_config import UI_VARIANT_SAGE

    if session is not None:
        variant = session.get("ui_variant")
        if variant:
            return variant == UI_VARIANT_SAGE
    return True


def use_sage_web_ui(session: Any, sid: str | None) -> bool:
    """Sage Web 向け diagnosis v1 パス（LINE 除外）。"""
    from src.handlers.line.line_session import is_line_session_id

    return bool(sid and is_sage_web_ui(session) and not is_line_session_id(sid))


def should_skip_reco_progressive_sse(session: Any, sid: str | None) -> bool:
    """Sage Web: 推奨 UI は diagnosis 一括返却のため cards/reco_detail 等の途中 SSE を省略。"""
    return use_sage_web_ui(session, sid)


def use_sage_diagnosis_storage(session: Any, sid: str | None) -> bool:
    """bot メッセージを Sage diagnosis v1 + マーカーで永続化するか（Web + LINE 引き継ぎ用）。"""
    from src.handlers.line.line_session import is_line_session_id

    if not sid:
        return False
    if is_line_session_id(sid):
        return True
    return is_sage_web_ui(session)


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
    session_id: str | None = None,
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
        row = enrich_medicine_image_url(row)
        enriched.append(row)
    from src.services.personalize_ranker import rerank_if_enabled

    return rerank_if_enabled(enriched, session_id=session_id)
