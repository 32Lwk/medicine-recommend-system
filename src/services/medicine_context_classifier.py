"""競技・推奨履歴文脈の LLM 分類（曖昧入力のみ）。"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional

from src.services.medicine_context_routing import MedicineContextRoute

logger = logging.getLogger(__name__)

_VALID_ROUTES = frozenset(
    {"followup_qa", "cold_start_recommend", "symptom_prompt", "none"}
)

_CLASSIFIER_PROMPT = """あなたは市販薬相談チャットのルーティング分類器です。
ユーザーの発話を次のいずれか1つに分類してください。

【ルート】
- followup_qa: 直近に案内した推奨医薬品についての追質問（競技で使えるか、どれを選ぶか、副作用・飲み方など）
- cold_start_recommend: 初回または推奨履歴なしで、症状があり競技/大会条件付きの薬探索（例: 風邪だが明日水泳大会なので使える薬）
- symptom_prompt: 競技・大会の話はあるが症状が不明で、まず症状を聞くべき
- none: 上記以外（通常の症状相談・挨拶など）

【ルール】
- 会話に推奨医薬品の案内があるとき「どれ」「使える」は followup_qa を優先
- 「風邪ですが大会前に」のように症状＋競技が両方ある初回は cold_start_recommend
- 症状なしで「競技前に使える薬は？」のみは symptom_prompt
- 頭痛など症状のみで競技の話がない場合は none

JSON のみ:
{{"route":"...", "confidence":0.0-1.0, "reasoning":"..."}}
"""


def _format_context_hint(session: Any, sid: Optional[str]) -> str:
    from src.services.medicine_discovery_routing import session_has_recommended_medicines

    parts: list[str] = []
    if session_has_recommended_medicines(session, sid):
        parts.append("直近の推奨医薬品の案内あり")
    else:
        parts.append("推奨医薬品の案内なし（初回または未推奨）")

    triage = (session.get("last_triage_result") if session is not None else None) or {}
    if triage.get("category"):
        parts.append(f"legacy_triage={triage.get('category')}")
    return "\n".join(parts)


def parse_medicine_context_response(raw: str | dict | None) -> MedicineContextRoute:
    if raw is None:
        return "none"
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return "none"
    route = str(data.get("route") or "none").strip()
    if route not in _VALID_ROUTES:
        return "none"
    return route  # type: ignore[return-value]


def classify_medicine_context_llm(
    user_text: str,
    session: Any,
    sid: Optional[str],
    *,
    client: Any,
    triage_result: Optional[dict] = None,
) -> MedicineContextRoute:
    """曖昧な競技・推奨文脈を LLM で分類。失敗時は none。"""
    from config.llm_flags import is_intent_router_llm_enabled

    if not is_intent_router_llm_enabled(sid):
        return "none"
    if not client or not (user_text or "").strip():
        return "none"

    context_hint = _format_context_hint(session, sid)
    triage = triage_result or {}
    triage_line = ""
    if triage.get("category"):
        triage_line = (
            f"\n【参考トリアージ】 category={triage.get('category')} "
            f"subcategory={triage.get('subcategory')}\n"
        )

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="triage",
            path="dialogue.medicine_context_classifier",
            messages=[
                {"role": "system", "content": "JSON のみ出力してください。"},
                {
                    "role": "user",
                    "content": (
                        f"{_CLASSIFIER_PROMPT}\n"
                        f"【セッション状況】\n{context_hint}{triage_line}\n"
                        f"【ユーザー入力】\n{user_text.strip()}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        route = parse_medicine_context_response(content)
        try:
            conf = float(json.loads(content).get("confidence", 0))  # type: ignore[arg-type]
        except Exception:
            conf = 0.0
        if conf < 0.55 and route != "none":
            logger.info(
                "medicine_context_classifier: low confidence %.2f route=%s",
                conf,
                route,
            )
            return "none"
        return route
    except Exception:
        logger.warning("medicine_context_classifier failed", exc_info=True)
        return "none"
