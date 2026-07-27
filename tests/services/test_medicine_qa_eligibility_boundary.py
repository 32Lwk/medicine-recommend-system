"""
medicine_qa_eligibility — 境界・複合意図（医薬品 + 技術/meta）のルーティング。

単語リストではなく文構造（ pivots / 並列節 / 明示優先 / 推奨文脈）で判定する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route


@dataclass(frozen=True)
class BoundaryCase:
    id: str
    text: str
    expected_route: MedicineQaRoute
    recs: Optional[list[dict[str, Any]]] = None
    history: Optional[list[dict[str, Any]]] = None
    use_llm: bool = False


BOUNDARY_CASES = [
    BoundaryCase(
        "bd_symptom_then_tech",
        "のど痛いんだけど、このチャットGPT使ってる？",
        MedicineQaRoute.PHYSICAL,
    ),
    BoundaryCase(
        "bd_reco_and_deploy",
        "推奨してくれた薬の副作用と、デプロイ先も教えて",
        MedicineQaRoute.MEDICINE_QA,
        recs=[{"product_name": "イブ"}],
    ),
    BoundaryCase(
        "bd_meta_first_explicit",
        "頭痛なんだけど、まず技術構成から聞きたい",
        MedicineQaRoute.CONCIERGE,
    ),
    BoundaryCase(
        "bd_medicine_lead_parallel",
        "市販薬相談したい、あとAWSとGCPの違いも",
        MedicineQaRoute.MEDICINE_QA,
    ),
    BoundaryCase(
        "bd_athlete_and_rule_based",
        "競技前に飲む薬と、ルールベース推奨の仕組み",
        MedicineQaRoute.MEDICINE_QA,
    ),
    BoundaryCase(
        "bd_pure_infra",
        "GCP と AWS の違いは？",
        MedicineQaRoute.CONCIERGE,
    ),
    BoundaryCase(
        "bd_hospital_or_otc",
        "病院行った方がいい？それとも市販薬でいける？",
        MedicineQaRoute.MEDICINE_QA,
    ),
    BoundaryCase(
        "bd_thanks_then_reco_followup",
        "ありがとう、じゃあ2番目の薬詳しく",
        MedicineQaRoute.MEDICINE_QA,
        recs=[{"product_name": "A"}, {"product_name": "B"}],
        history=[
            {"type": "user", "content": "頭痛"},
            {
                "type": "bot",
                "content": "推奨",
                "diagnosis": {
                    "recommended_medicines": [
                        {"product_name": "A"},
                        {"product_name": "B"},
                    ]
                },
            },
        ],
    ),
    BoundaryCase(
        "bd_correction_to_medicine",
        "違う、薬の話。先ほどのロキソニン眠くなる？",
        MedicineQaRoute.MEDICINE_QA,
        recs=[{"product_name": "ロキソニン"}],
        history=[
            {"type": "user", "content": "技術スタック教えて"},
            {"type": "bot", "content": "AWS/GCP", "concierge_intent": "architecture"},
        ],
    ),
    BoundaryCase(
        "bd_ambiguous_game_then_medicine",
        "ポケモンの話はいいから、風邪薬教えて",
        MedicineQaRoute.MEDICINE_QA,
        use_llm=True,
    ),
]


@pytest.mark.parametrize("case", BOUNDARY_CASES, ids=lambda c: c.id)
def test_boundary_routing(case: BoundaryCase):
    kwargs: dict[str, Any] = {
        "conversation_history": case.history,
        "recommended_medicines": case.recs,
        "client": None,
    }
    if case.use_llm:
        with patch(
            "src.services.medicine_qa_eligibility.is_medicine_qa_eligibility_llm_enabled",
            return_value=True,
        ), patch(
            "src.services.medicine_qa_eligibility._llm_resolve_concierge_intent",
            return_value=None,
        ):
            kwargs["client"] = MagicMock()
            decision = resolve_medicine_qa_route(case.text, **kwargs)
    else:
        decision = resolve_medicine_qa_route(case.text, **kwargs)

    assert decision.route == case.expected_route, (
        f"[{case.id}] got {decision.route.value} source={decision.source} "
        f"intent={decision.concierge_intent}"
    )
