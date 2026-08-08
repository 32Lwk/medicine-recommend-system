"""Physical route 向け no-candidates 時の文脈付きガイダンス（ルールベース）。"""
from __future__ import annotations

import re
from typing import Any, Optional

from src.services.reco_error_messages import ERROR_MESSAGES
from src.utils.symptom_helpers import normalize_symptom_names

_TOPIC_GUIDANCE: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"蕁麻疹|じんましん|発疹|かぶれ|湿疹|皮膚|痒|かゆ|吹き出物"),
        (
            "皮膚の症状ですね、つらいですね。"
            "かゆみ止めの内服や外用で様子を見られることもあります。"
            "広がる・呼吸が苦しい・唇や顔が腫れる場合は、すぐに医療機関へ。"
            "出始めた時期や範囲を教えていただくと、より安全な市販薬をご案内できます。"
        ),
    ),
    (
        re.compile(r"耳(?:が|の)?痛|みみ(?:が|の)?痛|耳鳴|難聴"),
        (
            "耳の痛みですね、つらいですね。"
            "解熱鎮痛薬で一時的に和らぐこともありますが、"
            "発熱・聞こえにくさ・膿・強い痛みがある場合は早めに耳鼻咽喉科を受診してください。"
            "いつから・片耳か両耳かも教えていただけると安心です。"
        ),
    ),
    (
        re.compile(r"口内炎|口(?:が|の)?痛|口の中"),
        (
            "口の中の痛みですね。"
            "口内炎用の貼り薬や塗り薬が使えることもあります。"
            "広がる・高熱・飲み込みにくい場合は受診をおすすめします。"
        ),
    ),
]


def build_physical_no_reco_message(
    user_message: str,
    recommendation_result: Optional[dict[str, Any]] = None,
) -> str:
    """候補 0 件でもユーザー意図を汲んだ短文ガイダンスを返す。"""
    text = (user_message or "").strip()
    nlu = (recommendation_result or {}).get("nlu_result") or {}
    symptom_blob = " ".join(normalize_symptom_names(nlu.get("symptoms") or []))
    probe = f"{text} {symptom_blob}".strip()

    doctor = ((recommendation_result or {}).get("doctor_consultation") or "").strip()
    if doctor:
        return doctor

    for pattern, guidance in _TOPIC_GUIDANCE:
        if pattern.search(probe):
            return guidance

    default = ERROR_MESSAGES["no_candidates"]["main_message"]
    hints = ERROR_MESSAGES["no_candidates"].get("recommendations") or []
    if hints:
        return f"{default} {hints[0]}"
    return default
