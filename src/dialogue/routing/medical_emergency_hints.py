"""Shared medical-emergency keyword hints for gate + pre-route signals.

Single source of truth to prevent production / eligibility cue drift (BE-H2).
"""
from __future__ import annotations

MEDICAL_EMERGENCY_HINTS: tuple[str, ...] = (
    "痙攣",
    "引きつけ",
    "けいれん",
    "意識がもうろう",
    "意識がない",
    "意識を失",
    "呼吸が苦しい",
    "呼吸困難",
    "呼吸ができない",
    "息ができない",
    "息が苦しい",
    "胸が痛",
    "胸痛",
    "胸を押さ",
    "脳卒中",
    "脳梗塞",
    "半身麻痺",
    "半身が動か",
    "ろれつが回ら",
    "顔が歪",
    "薬を大量",
    "大量に飲",
    "飲みすぎ",
    "過量服薬",
)

HYPOTHETICAL_SIDE_EFFECT_MARKERS: tuple[str, ...] = (
    "出ることがある",
    "出たら",
    "もし",
    "場合",
    "ことがある",
    "症状が出",
    "副作用",
    "アレルギー",
    "教えて",
    "説明",
    "心配",
    "使用をやめ",
    "相談した方が",
)


def is_hypothetical_side_effect_discussion(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if not any(h in t for h in MEDICAL_EMERGENCY_HINTS):
        return False
    return any(m in t for m in HYPOTHETICAL_SIDE_EFFECT_MARKERS)


def medical_emergency_hint_hit(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if not any(h in t for h in MEDICAL_EMERGENCY_HINTS):
        return False
    return not is_hypothetical_side_effect_discussion(t)


__all__ = [
    "HYPOTHETICAL_SIDE_EFFECT_MARKERS",
    "MEDICAL_EMERGENCY_HINTS",
    "is_hypothetical_side_effect_discussion",
    "medical_emergency_hint_hit",
]
