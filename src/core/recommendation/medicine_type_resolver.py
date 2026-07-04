"""medicine_type 判定のヒント補完。"""
from __future__ import annotations

from typing import Any, Dict, Optional


def resolve_medicine_type_from_hints(
    user_message: str,
    analysis_result: Optional[Dict[str, Any]],
    nlu_result: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    medicine_type = (analysis_result or {}).get("medicine_type")
    if medicine_type and medicine_type != "その他":
        return medicine_type

    if "風邪薬" in (user_message or ""):
        return "風邪薬"

    if not nlu_result:
        return None

    try:
        from src.core.dictionary_loader import load_symptom_dictionary

        symptom_dict = load_symptom_dictionary()
    except ImportError:
        return None

    detected: set[str] = set()
    for symptom in nlu_result.get("symptoms") or []:
        name = symptom.get("name") if isinstance(symptom, dict) else str(symptom)
        if name and name in symptom_dict:
            detected.update(symptom_dict[name].get("medicine_types") or [])

    if detected:
        return next(iter(detected))
    return None
