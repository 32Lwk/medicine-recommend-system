"""症状名の正規化ユーティリティ。"""
from __future__ import annotations

from typing import Any, Iterable, List


def normalize_symptom_names(symptoms: Iterable[Any]) -> List[str]:
    """
    NLU / analysis の symptoms をハッシュ可能な文字列リストに正規化する。
    dict 要素は name / symptom キーを優先。
    """
    names: List[str] = []
    for item in symptoms or []:
        if item is None:
            continue
        if isinstance(item, str):
            s = item.strip()
            if s:
                names.append(s)
            continue
        if isinstance(item, dict):
            for key in ("name", "symptom", "label", "text"):
                val = item.get(key)
                if isinstance(val, str) and val.strip():
                    names.append(val.strip())
                    break
            continue
        s = str(item).strip()
        if s and s != "{}":
            names.append(s)
    return names
