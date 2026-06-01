"""
ユーザー嗜好のマージ（GPT 結果 + 安全キーワード強制）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.core.dictionary_loader import load_preference_keyword_catalog

logger = logging.getLogger(__name__)

PREFERENCE_BOOL_FIELDS = (
    "ingredient_balance",
    "ease_of_taking",
    "accompanying_symptoms",
    "prefers_kampo",
    "prefers_not_kampo",
    "avoid_drowsiness",
    "avoid_dry_mouth",
    "prefer_fewer_daily_doses",
    "prefer_nasal_route",
    "avoid_nasal_route",
)


def default_user_preferences() -> Dict[str, Any]:
    return {
        "ingredient_balance": False,
        "ease_of_taking": False,
        "accompanying_symptoms": False,
        "confidence": 0.0,
        "reasons": [],
        "prefers_kampo": False,
        "prefers_not_kampo": False,
        "avoid_drowsiness": False,
        "prefer_non_sedating": False,
        "avoid_dry_mouth": False,
        "prefer_fewer_daily_doses": False,
        "preferred_max_daily_doses": None,
        "prefer_nasal_route": False,
        "avoid_nasal_route": False,
        "field_sources": {},
    }


def preference_field_confidence(prefs: Dict[str, Any], field: str) -> float:
    if not prefs.get(field):
        return 0.0
    key = f"{field}_confidence"
    if key in prefs and prefs[key] is not None:
        return float(prefs[key])
    return float(prefs.get("confidence", 0.0))


def apply_safety_preference_overrides(prefs: Dict[str, Any], text: str) -> Dict[str, Any]:
    """運転等の安全キーワードで眠気回避を強制。"""
    if not text:
        return prefs
    catalog = load_preference_keyword_catalog()
    lower = text.lower()
    sources = dict(prefs.get("field_sources") or {})
    reasons = list(prefs.get("reasons") or [])
    for kw in catalog.get("safety_hard_keywords", []):
        if kw in lower or kw in text:
            prefs["avoid_drowsiness"] = True
            prefs["prefer_non_sedating"] = True
            prefs["avoid_drowsiness_confidence"] = 1.0
            sources["avoid_drowsiness"] = "safety"
            if "眠気回避: 安全キーワード強制" not in reasons:
                reasons.append("眠気回避: 安全キーワード強制")
            break
    prefs["field_sources"] = sources
    prefs["reasons"] = reasons
    return prefs


def _parse_llm_field(entry: Any) -> tuple[bool, float, Optional[str]]:
    if not isinstance(entry, dict):
        return False, 0.0, None
    value = entry.get("value")
    conf = float(entry.get("confidence", 0.0) or 0.0)
    evidence = entry.get("evidence")
    if isinstance(value, bool):
        return value, conf, str(evidence) if evidence else None
    return False, conf, str(evidence) if evidence else None


def merge_user_preferences(
    llm_raw: Optional[Dict[str, Any]],
    text: str,
    nlu_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    catalog = load_preference_keyword_catalog()
    score_min = float(catalog.get("score_apply_min_confidence", 0.5))
    prefs = default_user_preferences()
    sources: Dict[str, str] = {}
    reasons: List[str] = []
    confidences: List[float] = []

    llm_raw = llm_raw or {}
    for field in PREFERENCE_BOOL_FIELDS:
        entry = llm_raw.get(field)
        if entry is None:
            continue
        val, conf, evidence = _parse_llm_field(entry)
        if val and conf >= score_min:
            prefs[field] = True
            prefs[f"{field}_confidence"] = conf
            sources[field] = "llm"
            if evidence:
                reasons.append(f"{field}: LLM ({evidence[:40]})")
            confidences.append(conf)

    dose_entry = llm_raw.get("preferred_max_daily_doses")
    if isinstance(dose_entry, dict):
        dose_val = dose_entry.get("value")
        dose_conf = float(dose_entry.get("confidence", 0.0) or 0.0)
        if dose_conf >= score_min and dose_val in (1, 2, 3):
            prefs["preferred_max_daily_doses"] = int(dose_val)
            prefs["prefer_fewer_daily_doses"] = True
            prefs["preferred_max_daily_doses_confidence"] = dose_conf
            prefs["prefer_fewer_daily_doses_confidence"] = dose_conf
            sources["preferred_max_daily_doses"] = "llm"

    prefs = apply_safety_preference_overrides(prefs, text)
    sources.update(prefs.get("field_sources") or {})

    if prefs.get("prefers_kampo") and prefs.get("prefers_not_kampo"):
        prefs["prefers_kampo"] = False
        sources["prefers_kampo"] = "llm_resolved"
        reasons.append("漢方希望と忌避の競合: 忌避を優先")

    prefs["prefer_non_sedating"] = prefs.get("avoid_drowsiness", False)
    if confidences:
        prefs["confidence"] = max(confidences)
    prefs["field_sources"] = sources
    prefs["reasons"] = reasons

    logger.info(
        "📋 嗜好マージ: 眠気回避=%s, 口渇回避=%s, 点鼻希望=%s, confidence=%.2f",
        prefs.get("avoid_drowsiness"),
        prefs.get("avoid_dry_mouth"),
        prefs.get("prefer_nasal_route"),
        prefs.get("confidence", 0.0),
    )
    return prefs


def preference_sources_for_debug(prefs: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """DEBUG score_breakdown 用: 有効な嗜好フィールドの source（llm / safety）。"""
    if not prefs:
        return {}
    sources = prefs.get("field_sources") or {}
    out: Dict[str, str] = {}
    for field in PREFERENCE_BOOL_FIELDS:
        if prefs.get(field):
            out[field] = str(sources.get(field, "merged"))
    if prefs.get("preferred_max_daily_doses") is not None:
        out["preferred_max_daily_doses"] = str(
            sources.get("preferred_max_daily_doses", "merged")
        )
    return out


def build_user_preferences_summary(prefs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """API 返却用の平坦サマリ。"""
    if not prefs:
        return {}
    summary: Dict[str, Any] = {"sources": dict(prefs.get("field_sources") or {})}
    for field in PREFERENCE_BOOL_FIELDS:
        summary[field] = bool(prefs.get(field))
        ck = f"{field}_confidence"
        if ck in prefs:
            summary[ck] = prefs[ck]
    if prefs.get("preferred_max_daily_doses") is not None:
        summary["preferred_max_daily_doses"] = prefs["preferred_max_daily_doses"]
    summary["overall_confidence"] = prefs.get("confidence", 0.0)
    return summary
