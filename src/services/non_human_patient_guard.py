"""非人間（ペット等）への市販薬相談 — 獣医師案内へリダイレクト。"""
from __future__ import annotations

import re

_PET_SUBJECT_RE = re.compile(
    r"(?:"
    r"うちの|我が家の|飼(?:って|えて)?(?:い|る)|"
    r"(?:犬|猫|ペット|うさぎ|鳥|ハムスタ|フェレット)(?:が|の|に|を)"
    r")"
    r"|人間の(?:風邪|市販|薬)"
    r"|(?:犬|猫|ペット).{0,24}(?:薬|市販|風邪|咳|熱|あげ|飲ま)"
)

_HUMAN_OWNER_SYMPTOM_RE = re.compile(
    r"(?:私|自分|僕|俺|飼い主|飼主).{0,16}(?:アレルギ|花粉|鼻炎|咳|熱|風邪)"
)


def is_non_human_patient_query(text: str) -> bool:
    """ペット等への人間用市販薬相談か（飼い主自身の症状相談は除外）。"""
    t = (text or "").strip()
    if not t:
        return False
    if _HUMAN_OWNER_SYMPTOM_RE.search(t):
        return False
    return bool(_PET_SUBJECT_RE.search(t))


def build_non_human_patient_redirect_text() -> str:
    return (
        "人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。"
        "ペットの症状がある場合は、獣医師に相談するのが安全です。"
        "緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。"
    )
