"""
花粉症・アレルギー性鼻炎向けの候補分類・スコア調整・ユーザー嗜好反映。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.core.candidate_scoring import has_allergic_rhinitis_efficacy

# 血管収縮点鼻（短期・反跳性鼻炎リスク）
VASOCONSTRICTOR_INGREDIENTS = (
    "オキシメタゾリン",
    "キシロメタゾリン",
    "テトラヒドロゾリン",
    "ナファゾリン",
    "トラマゾリン",
    "フェニレフリン",
)

# 第1世代抗ヒスタミン（眠気・口渇が出やすい）
FIRST_GEN_ANTIHISTAMINE_INGREDIENTS = (
    "クロルフェニラミン",
    "ジフェンヒドラミン",
    "クレマスチン",
    "プロメタジン",
    "ジプロフィリン",
    "メクリジン",
)

# 第2世代抗ヒスタミン（非鎮静性が多い）
SECOND_GEN_ANTIHISTAMINE_INGREDIENTS = (
    "フェキソフェナジン",
    "ロラタジン",
    "セチリジン",
    "エバスチン",
    "ビラスチン",
    "オロパタジン",
    "ケトチフェン",
)

STEROID_NASAL_MARKERS = (
    "ベクロメタゾン",
    "フルチカゾン",
    "モメタゾン",
    "デキサメタゾン",
    "季節性アレルギー専用",
)

NASAL_FORM_KEYWORDS = ("点鼻", "鼻腔", "噴霧", "スプレー", "nasal")


def _normalize_ingredients(candidate: Dict) -> str:
    return str(candidate.get("ingredients", "") or "")


def _combined_text(candidate: Dict) -> str:
    return "".join(
        [
            str(candidate.get("product_name", "")),
            str(candidate.get("efficacy", "")),
            str(candidate.get("usage", "")),
        ]
    )


def is_nasal_rhinitis_product(candidate: Dict) -> bool:
    text = _combined_text(candidate)
    if any(kw in text for kw in NASAL_FORM_KEYWORDS):
        return True
    if "点鼻" in str(candidate.get("usage", "")):
        return True
    name = str(candidate.get("product_name", ""))
    return "点鼻" in name or ("スプレー" in name and "鼻炎" in str(candidate.get("medicine_type", "")))


def contains_any(text: str, tokens: Tuple[str, ...]) -> bool:
    return any(t in text for t in tokens)


def classify_pollen_rhinitis_product(candidate: Dict) -> str:
    """
    花粉症文脈での製品クラス。
    oral_2nd_gen | oral_1st_gen | nasal_steroid_allergy | nasal_vasoconstrictor |
    nasal_combo | oral_other | other
    """
    ingredients = _normalize_ingredients(candidate)
    text = _combined_text(candidate)
    is_nasal = is_nasal_rhinitis_product(candidate)
    has_vaso = contains_any(ingredients, VASOCONSTRICTOR_INGREDIENTS)
    has_1st = contains_any(ingredients, FIRST_GEN_ANTIHISTAMINE_INGREDIENTS)
    has_2nd = contains_any(ingredients, SECOND_GEN_ANTIHISTAMINE_INGREDIENTS)
    has_steroid = contains_any(ingredients + text, STEROID_NASAL_MARKERS)

    if is_nasal:
        if has_steroid or "季節性アレルギー" in text:
            return "nasal_steroid_allergy"
        if has_vaso and (has_1st or has_2nd):
            return "nasal_combo"
        if has_vaso:
            return "nasal_vasoconstrictor"
        if has_2nd or has_1st:
            return "nasal_combo"
        return "nasal_other"

    medicine_type = str(candidate.get("medicine_type", ""))
    if "鼻炎" not in medicine_type and "抗アレルギー" not in medicine_type:
        return "other"

    if has_2nd and not has_1st:
        return "oral_2nd_gen"
    if has_1st and not has_2nd:
        return "oral_1st_gen"
    if has_2nd and has_1st:
        return "oral_1st_gen"
    if has_allergic_rhinitis_efficacy(str(candidate.get("efficacy", ""))):
        return "oral_other"
    return "other"


def pollen_symptom_profile(
    symptom_names: List[str], user_text: str = ""
) -> Dict[str, bool]:
    names = set(symptom_names or [])
    text = user_text or ""
    has_congestion = "鼻づまり" in names
    has_rhinorrhea = "鼻水" in names
    has_sneeze = "くしゃみ" in names
    has_eye = "目のかゆみ" in names or (
        "かゆみ" in names and ("目" in text or "眼" in text)
    )
    return {
        "congestion_primary": has_congestion and not has_rhinorrhea,
        "rhinorrhea_sneeze": (has_rhinorrhea or has_sneeze) and not has_congestion,
        "mixed_nasal": has_congestion and (has_rhinorrhea or has_sneeze),
        "has_congestion": has_congestion,
        "has_eye": has_eye,
    }


def estimate_daily_dose_count(usage: str) -> Optional[int]:
    if not usage:
        return None
    m = re.search(r"1日\s*(\d+)\s*回", usage)
    if m:
        return int(m.group(1))
    if "1日1回" in usage or "1回" in usage and "1日2回" not in usage:
        return 1
    if "1日2回" in usage or "朝晩" in usage:
        return 2
    if "1日3回" in usage or "食後" in usage:
        return 3
    return None


def apply_pollen_candidate_adjustments(
    candidate: Dict,
    *,
    focus_pollen: bool,
    symptom_names: List[str],
    user_preferences: Optional[Dict] = None,
    user_text: str = "",
) -> None:
    """候補 dict に pollen_boost / pollen_penalty / flags を付与。"""
    if not focus_pollen:
        return

    prefs = user_preferences or {}
    profile = pollen_symptom_profile(symptom_names, user_text)
    product_class = classify_pollen_rhinitis_product(candidate)
    candidate["pollen_product_class"] = product_class

    boost = float(candidate.get("pollen_boost", 0.0))
    penalty = float(candidate.get("pollen_penalty", 0.0))

    avoid_drowsiness = prefs.get("avoid_drowsiness") or prefs.get("prefer_non_sedating")
    avoid_dry_mouth = prefs.get("avoid_dry_mouth")
    prefer_nasal = prefs.get("prefer_nasal_route")
    avoid_nasal = prefs.get("avoid_nasal_route")
    prefer_fewer_doses = prefs.get("prefer_fewer_daily_doses")
    max_doses = prefs.get("preferred_max_daily_doses")

    # --- 製品クラス別の基礎スコア ---
    if product_class == "oral_2nd_gen":
        boost = max(boost, 0.48)
    elif product_class == "nasal_steroid_allergy":
        boost = max(boost, 0.55)
    elif product_class == "oral_other" and has_allergic_rhinitis_efficacy(
        str(candidate.get("efficacy", ""))
    ):
        boost = max(boost, 0.35)
    elif product_class == "oral_1st_gen":
        boost = max(boost, 0.08 if not avoid_drowsiness else 0.02)
        penalty = min(penalty, -0.32)
        if avoid_drowsiness or avoid_dry_mouth:
            penalty = min(penalty, -0.48)
    elif product_class == "nasal_vasoconstrictor":
        if profile["congestion_primary"] or profile["mixed_nasal"]:
            boost = max(boost, 0.28)
        else:
            boost = max(boost, 0.08)
            penalty = min(penalty, -0.15)
    elif product_class == "nasal_combo":
        if profile["congestion_primary"]:
            boost = max(boost, 0.32)
        elif profile["rhinorrhea_sneeze"]:
            boost = max(boost, 0.18)
        if avoid_drowsiness:
            penalty = min(penalty, -0.22)
    elif product_class == "nasal_other":
        if profile["has_congestion"]:
            boost = max(boost, 0.20)

    # --- 症状プロファイル: 鼻づまり中心は点鼻をやや優先、くしゃみ鼻水中心は内服2世代 ---
    if profile["congestion_primary"] and product_class.startswith("nasal"):
        boost += 0.12
    if profile["rhinorrhea_sneeze"] and product_class == "oral_2nd_gen":
        boost += 0.10
    if profile["mixed_nasal"] and product_class in ("oral_2nd_gen", "nasal_steroid_allergy"):
        boost += 0.08
    if profile["rhinorrhea_sneeze"] and product_class == "nasal_steroid_allergy":
        boost += 0.10

    medicine_type = str(candidate.get("medicine_type", ""))
    if profile["has_eye"] and "目薬" in medicine_type:
        boost = max(boost, 0.38)
        efficacy = str(candidate.get("efficacy", ""))
        if "アレルギー" in efficacy or "結膜" in efficacy or "花粉" in efficacy:
            boost += 0.12

    # --- ユーザー嗜好: 剤形 ---
    if prefer_nasal and product_class.startswith("nasal"):
        boost += 0.15
    if avoid_nasal and product_class.startswith("nasal"):
        penalty = min(penalty, -0.35)

    # --- ユーザー嗜好: 眠気・口渇 ---
    ingredients = _normalize_ingredients(candidate)
    if avoid_drowsiness and contains_any(ingredients, FIRST_GEN_ANTIHISTAMINE_INGREDIENTS):
        penalty = min(penalty, -0.30)
    if avoid_drowsiness and product_class == "oral_2nd_gen":
        boost += 0.08
    if avoid_dry_mouth and (
        contains_any(ingredients, FIRST_GEN_ANTIHISTAMINE_INGREDIENTS)
        or "イソプロパミド" in ingredients
        or "ベラドンナ" in ingredients
    ):
        penalty = min(penalty, -0.18)

    # --- ユーザー嗜好: 1日の服用回数 ---
    dose_count = estimate_daily_dose_count(str(candidate.get("usage", "")))
    if prefer_fewer_doses or max_doses is not None:
        target = max_doses if max_doses is not None else 2
        if dose_count is not None:
            if dose_count <= target:
                boost += 0.10 if dose_count == 1 else 0.06
            elif dose_count > target:
                penalty = min(penalty, -0.12)

    has_vaso = contains_any(ingredients, VASOCONSTRICTOR_INGREDIENTS)
    if has_vaso and is_nasal_rhinitis_product(candidate):
        candidate["has_vasoconstrictor_nasal"] = True

    candidate["pollen_boost"] = boost
    candidate["pollen_penalty"] = penalty


def apply_pollen_preference_bonus(
    candidate: Dict,
    user_preferences: Optional[Dict],
    *,
    focus_pollen: bool,
) -> float:
    """final_score 用の追加ボーナス（嗜好の微調整）。"""
    if not focus_pollen or not user_preferences:
        return 0.0
    return 0.0  # 候補段階の pollen_boost/penalty に集約


VASOCONSTRICTOR_NASAL_WARNING_HTML = (
    "<strong>⚠️ 重要（点鼻・血管収縮成分）：</strong>"
    "本品は鼻づまりの一時的な緩和を目的とした点鼻薬です。"
    "<strong>連用（おおむね3〜7日を超える使用）は避けてください。</strong>"
    "やめたあと鼻づまりが悪化する「反跳性鼻炎」が起こることがあります。"
    "症状が続く場合や毎年繰り返す場合は、医師・薬剤師にご相談ください。"
)


def append_vasoconstrictor_nasal_warning(usage_notes: str, candidate: Dict) -> str:
    if not candidate.get("has_vasoconstrictor_nasal"):
        return usage_notes
    if "反跳" in (usage_notes or "") or "連用" in (usage_notes or ""):
        return usage_notes
    if VASOCONSTRICTOR_NASAL_WARNING_HTML in (usage_notes or ""):
        return usage_notes
    if usage_notes:
        return usage_notes + "\n\n" + VASOCONSTRICTOR_NASAL_WARNING_HTML
    return VASOCONSTRICTOR_NASAL_WARNING_HTML


def mark_vasoconstrictor_flag(candidate: Dict) -> None:
    ingredients = _normalize_ingredients(candidate)
    if contains_any(ingredients, VASOCONSTRICTOR_INGREDIENTS) and is_nasal_rhinitis_product(
        candidate
    ):
        candidate["has_vasoconstrictor_nasal"] = True
