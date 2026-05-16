"""
処理中バブル: 担当エージェント名・時間のかかる処理の注記
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

# (flow_id, step_id, detail_code) -> 1行目直下の待機注記（空 flow_id は任意フロー）
_SLOW_HINTS: Dict[Tuple[str, str, str], str] = {
    ("", "symptom_analysis", "llm_classify"): "AIでの分析のため、少々お待ちください",
    ("physical", "symptom_analysis", "llm_classify"): "AIでの分析のため、少々お待ちください",
    ("", "medicine_qa", "answer_compose"): "回答を作成しています。少々お待ちください",
    ("", "medicine_qa", "answer_draft"): "回答を作成しています。少々お待ちください",
    ("ask_qa", "medicine_qa", "answer_compose"): "回答を作成しています。少々お待ちください",
    ("ask_qa", "medicine_qa", "answer_draft"): "回答を作成しています。少々お待ちください",
    ("", "medicine_select", "scoring"): "候補が多い場合、評価に少々時間がかかります",
    ("physical", "medicine_select", "scoring"): "候補が多い場合、評価に少々時間がかかります",
    ("", "medicine_select", "candidate_search"): "データベースを検索しています。少々お待ちください",
    ("physical", "medicine_select", "candidate_search"): "データベースを検索しています。少々お待ちください",
    ("", "medicine_select", "explanation"): "おすすめの理由を生成しています。少々お待ちください",
    ("physical", "medicine_select", "explanation"): "おすすめの理由を生成しています。少々お待ちください",
    ("", "attributes", "nlu"): "症状の整理に少々お待ちください",
    ("physical", "attributes", "nlu"): "症状の整理に少々お待ちください",
}


def user_agent_display(
    agent_name: Optional[str],
    step_id: str,
    detail_code: Optional[str],
    flow_id: str,
) -> Optional[str]:
    if agent_name:
        return f"担当: {agent_name}"
    return None


def slow_hint_for_phase(
    flow_id: str,
    step_id: str,
    detail_code: Optional[str],
) -> Optional[str]:
    dc = (detail_code or "").strip()
    if not dc:
        return None
    return _SLOW_HINTS.get((flow_id, step_id, dc)) or _SLOW_HINTS.get(("", step_id, dc))
