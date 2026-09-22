"""Sleep-medicine / controlled acquisition intent classification (R7-C).

Does NOT default ambiguous requests to illegal. Never short-circuits to SessionOps.
"""
from __future__ import annotations

from typing import Literal, Optional

SleepMedKind = Literal[
    "acquisition_request",
    "general_information",
    "prescription_request",
    "named_controlled_acquisition",
    "ambiguous_sleep_medicine_request",
    "explicit_illegal",
]


def classify_sleep_or_controlled_intent(text: str) -> Optional[SleepMedKind]:
    t = (text or "").strip()
    if not t:
        return None
    low = t.lower()

    illegal_cues = (
        "違法薬物",
        "覚せい剤",
        "覚醒剤",
        "ヘロイン",
        "コカイン",
        "mdma",
        "違法な薬",
    )
    if any(c in t or c in low for c in illegal_cues):
        if any(v in t for v in ("買", "入手", "ください", "くれ", "売って", "欲しい")):
            return "explicit_illegal"
        return "explicit_illegal"

    named_controlled = (
        "モルヒネ",
        "フェンタニル",
        "オキシコドン",
        "フルニトラゼパム",
        "トリアゾラム",
        "向精神薬",
    )
    acquisition_verbs = ("ください", "欲しい", "ほしい", "売って", "入手", "買", "くれ")
    info_cues = ("教えて", "について知りたい", "とは", "副作用", "効能", "情報")
    prescribed_cues = ("医師から処方", "処方された", "処方箋で")

    has_sleep = "睡眠薬" in t
    has_named = any(n in t for n in named_controlled)

    if "処方" in t and (has_sleep or has_named or "薬" in t):
        # 「処方箋なしで…入手」は処方案内ではなく入手要求
        if "処方箋なし" in t or "処方箋が不要" in t:
            if has_sleep and any(v in t for v in acquisition_verbs + ("入手",)):
                return "acquisition_request"
        if any(v in t for v in ("処方して", "処方してください")):
            return "prescription_request"

    if has_named and any(v in t for v in acquisition_verbs):
        return "named_controlled_acquisition"

    if has_named and any(c in t for c in info_cues):
        return "general_information"

    if has_sleep:
        if any(c in t for c in prescribed_cues) and any(c in t for c in info_cues):
            return "general_information"
        if "処方箋なし" in t and any(v in t for v in acquisition_verbs + ("入手",)):
            return "acquisition_request"
        if any(v in t for v in acquisition_verbs):
            return "ambiguous_sleep_medicine_request"
        if any(c in t for c in info_cues):
            return "general_information"
        return "ambiguous_sleep_medicine_request"

    return None


def sleep_intent_to_policy_flags(kind: SleepMedKind | None) -> dict:
    """Map classification → additive signal flags (never illegal default for ambiguous)."""
    if kind is None:
        return {}
    if kind == "explicit_illegal":
        return {
            "controlled_or_illegal_block": True,
            "policy_subtype": "illegal",
        }
    if kind == "named_controlled_acquisition":
        return {
            "controlled_or_illegal_block": True,
            "policy_subtype": "controlled",
        }
    if kind == "prescription_request":
        return {
            "prescription_block": True,
            "policy_subtype": "prescription_request",
        }
    if kind == "general_information":
        # Not a policy block — allow normal routing / QA
        return {"policy_subtype": "general_information"}
    if kind in ("acquisition_request", "ambiguous_sleep_medicine_request"):
        return {
            "ambiguous_policy": True,
            "policy_subtype": "unknown_controlled_policy",
        }
    return {}
