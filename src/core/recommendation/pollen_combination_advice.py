"""
花粉症・アレルギー性鼻炎の top3 併用に関する注意文を生成する。
"""
from __future__ import annotations

from typing import Dict, List

from src.core.recommendation.pollen_rhinitis_scoring import (
    classify_pollen_rhinitis_product,
)

ORAL_ANTIHISTAMINE_CLASSES = frozenset({"oral_1st_gen", "oral_2nd_gen", "oral_other"})
NASAL_VASO_CLASSES = frozenset({"nasal_vasoconstrictor", "nasal_combo"})


def _product_class(item: Dict) -> str:
    cls = item.get("pollen_product_class")
    if cls:
        return str(cls)
    return classify_pollen_rhinitis_product(item)


def build_pollen_combination_advice(recommendations: List[Dict]) -> str:
    """上位推奨の併用可否・注意（HTML 断片）。"""
    if len(recommendations) < 2:
        return ""

    classes = [_product_class(r) for r in recommendations]
    vaso_count = sum(
        1
        for r, cls in zip(recommendations, classes)
        if cls in NASAL_VASO_CLASSES or r.get("has_vasoconstrictor_nasal")
    )
    oral_ah = [cls for cls in classes if cls in ORAL_ANTIHISTAMINE_CLASSES]

    notes: List[str] = []

    if vaso_count >= 2:
        notes.append(
            "血管収縮作用の点鼻薬を複数同時に使わないでください。"
            "反跳性鼻炎のリスクがあります。"
        )

    if len(oral_ah) >= 2:
        notes.append(
            "抗ヒスタミン系の内服薬を2種類同時に服用しないでください。"
            "眠気・口渇などの副作用が強くなるおそれがあります。"
        )

    has_steroid = "nasal_steroid_allergy" in classes
    has_oral_2nd = "oral_2nd_gen" in classes
    has_oral_1st = "oral_1st_gen" in classes
    has_vaso = bool(NASAL_VASO_CLASSES.intersection(classes)) or vaso_count >= 1

    if has_oral_1st and has_oral_2nd:
        notes.append(
            "第1世代と第2世代の抗ヒスタミン内服を同時に使わないでください。"
        )

    if has_steroid and has_oral_2nd:
        notes.append(
            "ステロイド点鼻と第2世代抗ヒスタミン内服の併用は、"
            "説明書の範囲で行われることがあります。"
            "用法・使用期間を守り、不明点は薬剤師にご相談ください。"
        )

    if has_steroid and has_vaso and vaso_count >= 1:
        notes.append(
            "ステロイド点鼻と血管収縮点鼻を併用する場合は、"
            "使い分け・連用日数に注意し、薬剤師または医師にご相談ください。"
        )

    if has_vaso and has_oral_2nd and vaso_count == 1 and len(oral_ah) == 1:
        notes.append(
            "血管収縮点鼻（主に鼻づまり向け）と内服鼻炎薬は目的が異なる場合があります。"
            "点鼻は短期間に留め、おおむね3〜7日を超える連用は避けてください。"
        )

    if not notes:
        return ""

    items_html = "".join(f"<li>{n}</li>" for n in notes)
    return (
        "<p><strong>【花粉症・鼻炎薬の併用について】</strong></p>"
        f"<ul>{items_html}</ul>"
    )
