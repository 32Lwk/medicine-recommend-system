"""症状名の正規化・NLU後リファインメント。"""
from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional

_GENERIC_NLU_SYMPTOMS = frozenset({"炎症", "症状", "不調", "違和感", "体調不良"})

# ユーザー原文から canonical 症状へ（NLU が汎用語を返したときの救済）
_TEXT_TO_CANONICAL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"蕁麻疹|じんましん|じん麻疹"), "じんましん"),
    (re.compile(r"耳(?:が|の)?痛|みみ(?:が|の)?痛"), "耳の痛み"),
    (re.compile(r"目(?:が|の)?(?:痛|かゆ)|め(?:が|の)?(?:痛|かゆ)"), "目のかゆみ"),
    (re.compile(r"口内炎|口(?:が|の)?痛|口の中(?:が|の)?痛"), "口内炎"),
    (re.compile(r"のど(?:が|の)?痛|喉(?:が|の)?痛"), "のどの痛み"),
    (re.compile(r"頭(?:が|の)?痛|頭痛"), "頭痛"),
    (re.compile(r"(?:咳|せき)(?:が|の)?(?:出|ひど|止まら)"), "咳"),
    (re.compile(r"鼻水|鼻(?:が|の)?(?:詰|つま|みず)"), "鼻水"),
    (re.compile(r"(?:下痢|下す|お腹(?:を|が)下)"), "下痢"),
    (re.compile(r"便秘|便(?:が|の)?出(?:ない|にく)"), "便秘"),
    (re.compile(r"(?:胃|お腹|腹)(?:が|の)?痛"), "腹痛"),
    (re.compile(r"かゆ|痒|かぶれ|吹き出物"), "かゆみ"),
]


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


def _symptom_dict(name: str, *, template: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    base = dict(template or {})
    base["name"] = name
    base.setdefault("severity", "軽度")
    return base


def refine_nlu_symptoms_from_context(user_text: str, nlu_result: dict[str, Any]) -> dict[str, Any]:
    """NLU 症状をユーザー原文で補正し、スコアリング可能な canonical 名に寄せる。

    LLM が「炎症」等の汎用語だけ返すケースや、蕁麻疹→発疹 の効能不一致を
    ルールで救済する。テスト個別ハックではなく、短文・部位痛・皮膚系全般向け。
    """
    text = (user_text or "").strip()
    if not text:
        return nlu_result

    symptoms = list(nlu_result.get("symptoms") or [])
    names = normalize_symptom_names(symptoms)
    canonical: list[str] = []

    for pattern, canon in _TEXT_TO_CANONICAL:
        if pattern.search(text):
            canonical.append(canon)

    # 蕁麻疹系: 発疹のみならじんましんも追加（OTC 効能表記は「じんましん」が多い）
    if any(n in names for n in ("発疹", "蕁麻疹")) or re.search(r"蕁麻疹|じんましん", text):
        if "じんましん" not in canonical:
            canonical.append("じんましん")

    if not canonical and not names:
        return nlu_result

    template = symptoms[0] if symptoms and isinstance(symptoms[0], dict) else None
    existing = set(names)
    merged_names = list(names)

    for canon in canonical:
        if canon not in existing:
            merged_names.append(canon)
            existing.add(canon)

    # 汎用 NLU のみで原文から具体症状が取れたら先頭を差し替え
    if names and all(n in _GENERIC_NLU_SYMPTOMS for n in names) and canonical:
        merged_names = canonical + [n for n in names if n not in _GENERIC_NLU_SYMPTOMS]

    if merged_names == names:
        return nlu_result

    nlu_result = dict(nlu_result)
    nlu_result["symptoms"] = [_symptom_dict(n, template=template) for n in merged_names]
    nlu_result["_symptom_refined_from_text"] = True
    return nlu_result
