"""
Emergency サブタイプ分類（店舗インシデント / メディカル / クライシス）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# 店舗インシデントとして扱う detect_store 種別（第三者・店内事案）
_STORE_INCIDENT_TYPES = frozenset({
    "fire",
    "weapon",
    "violence",
    "injured_person",
    "suspicious_person",
    "theft",
    "unknown",
})

# ユーザー自身の身体的緊急（店舗キーワードより優先しうる）
_MEDICAL_SELF_HINTS = (
    "胸が痛",
    "胸が締",
    "息ができない",
    "呼吸困難",
    "呼吸ができない",
    "動悸",
    "意識がもうろう",
    "意識がない",
    "大量出血",
    "血が止まらない",
    "心臓",
    "心筋梗塞",
    "脳卒中",
    "119",
    "救急車",
    "救急",
)


@dataclass(frozen=True)
class EmergencyClassification:
    subtype: str  # store_incident | medical_self | crisis_language
    priority_tag: str  # critical_crisis | critical_medical | store_high | store_low
    source: str
    store_primary_type: Optional[str] = None
    detected_keywords: Optional[List[str]] = None


def is_emergency_candidate(
    user_text: str,
    *,
    triage_result: Optional[Dict[str, Any]] = None,
    moderation_label: Optional[str] = None,
) -> bool:
    """緊急ディスパッチ対象か（誤検知で常時発火しないためのゲート）。"""
    text = (user_text or "").strip()
    if not text:
        return False
    triage = triage_result or {}
    mod = (moderation_label or triage.get("_moderation_label") or "").lower()
    if mod == "crisis":
        return True
    try:
        from src.core.crisis_detection import detect_crisis_keywords

        if detect_crisis_keywords(text)[0]:
            return True
    except ImportError:
        pass
    try:
        from src.services.store_emergency_handler import detect_store_emergency

        if detect_store_emergency(text):
            return True
    except ImportError:
        pass
    if triage.get("category") == "Emergency" or triage.get("requires_immediate_action"):
        return True
    if any(h in text for h in _MEDICAL_SELF_HINTS):
        return True
    return False


def classify_emergency(
    user_text: str,
    *,
    triage_result: Optional[Dict[str, Any]] = None,
    moderation_label: Optional[str] = None,
) -> EmergencyClassification:
    """
    保守的合成: クライシス > メディカル（自己）> 店舗検出 > triage Emergency > その他
    """
    text = (user_text or "").strip()
    triage = triage_result or {}
    mod = (moderation_label or "").lower()

    if mod == "crisis":
        return EmergencyClassification(
            subtype="crisis_language",
            priority_tag="critical_crisis",
            source="moderation",
        )

    try:
        from src.core.crisis_detection import detect_crisis_keywords

        is_crisis, crisis_kws = detect_crisis_keywords(text)
        if is_crisis:
            return EmergencyClassification(
                subtype="crisis_language",
                priority_tag="critical_crisis",
                source="crisis_keywords",
                detected_keywords=crisis_kws,
            )
    except ImportError:
        pass

    store_hit = None
    try:
        from src.services.store_emergency_handler import detect_store_emergency

        store_hit = detect_store_emergency(text)
    except ImportError:
        store_hit = None

    triage_emergency = (
        triage.get("category") == "Emergency"
        or bool(triage.get("requires_immediate_action"))
    )

    medical_self_hint = any(h in text for h in _MEDICAL_SELF_HINTS)

    if store_hit and store_hit.get("primary_type"):
        primary = store_hit["primary_type"]
        # 店内の傷病人・医療系店舗キーワードは store、ユーザー自身の胸痛等は medical
        if primary == "medical_emergency" and medical_self_hint and not _looks_like_third_party_incident(text):
            return EmergencyClassification(
                subtype="medical_self",
                priority_tag="critical_medical",
                source="medical_hint_over_store",
                detected_keywords=store_hit.get("detected_keywords"),
            )
        if primary in _STORE_INCIDENT_TYPES or primary == "medical_emergency":
            tag = "store_high" if primary in ("fire", "weapon", "violence", "injured_person") else "store_high"
            if primary == "theft":
                tag = "store_low"
            return EmergencyClassification(
                subtype="store_incident",
                priority_tag=tag,
                source="store_detect",
                store_primary_type=primary,
                detected_keywords=store_hit.get("detected_keywords"),
            )

    if triage_emergency or medical_self_hint:
        return EmergencyClassification(
            subtype="medical_self",
            priority_tag="critical_medical",
            source="triage_or_medical_hint",
            detected_keywords=[h for h in _MEDICAL_SELF_HINTS if h in text][:5],
        )

    if store_hit:
        primary = store_hit.get("primary_type") or "unknown"
        return EmergencyClassification(
            subtype="store_incident",
            priority_tag="store_high",
            source="store_detect_fallback",
            store_primary_type=primary,
            detected_keywords=store_hit.get("detected_keywords"),
        )

    return EmergencyClassification(
        subtype="medical_self",
        priority_tag="critical_medical",
        source="default_conservative",
    )


def _looks_like_third_party_incident(text: str) -> bool:
    third_party = (
        "倒れている人",
        "倒れている方",
        "人が倒れ",
        "店内で",
        "お客さんが",
        "お客様が",
        "店員が",
        "誰かが",
    )
    return any(p in text for p in third_party)
