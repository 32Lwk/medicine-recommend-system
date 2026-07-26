"""Medicine QA focus — ルールが曖昧／衝突するときの LLM 補完（低コスト・文脈付き）。

単語リストを増やして個別フレーズに合わせるのではなく、
構造的な曖昧さ（短文・指示語・文脈依存・focus 衝突）のときだけ LLM に委ねる。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from src.services.medicine_qa_routing import MedicineQaFocus

logger = logging.getLogger(__name__)

_VALID_FOCUSES = frozenset({
    "comparison",
    "side_effect",
    "doping",
    "interaction",
    "usage",
    "ingredient",
    "age",
    "product_image",
    "general",
})

# ルール同士が同時に立つと誤りの多い組み合わせ（LLM で解く）
_CONFLICT_FOCUS_PAIRS = frozenset({
    frozenset({"side_effect", "usage"}),
    frozenset({"interaction", "comparison"}),
    frozenset({"doping", "usage"}),
    frozenset({"age", "usage"}),
})


def is_medicine_qa_focus_llm_enabled() -> bool:
    """
    MEDICINE_QA_FOCUS_LLM:
      - unset / auto: OpenAI client があれば ON（曖昧時のみ呼ばれる）
      - 1/true/on: 強制 ON
      - 0/false/off: 強制 OFF
    """
    val = os.getenv("MEDICINE_QA_FOCUS_LLM")
    if val is None or str(val).strip().lower() in ("", "auto"):
        try:
            from src.core.openai_client import client as openai_client

            return bool(openai_client)
        except Exception:
            return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _has_openai_client() -> bool:
    try:
        from src.core.openai_client import client as openai_client

        return bool(openai_client)
    except Exception:
        return False


def _looks_structurally_ambiguous(
    user_message: str,
    rule_focuses: list[str],
    *,
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> bool:
    """
    キーワード列挙ではなく構造で曖昧さを見る。
    - general のみ
    - 短文 + 文脈（指示語 follow-up）
    - focus 衝突
    - 発話に固有薬名が薄く、推奨/履歴がある質問
    """
    t = (user_message or "").strip()
    if not t:
        return False

    non_general = [f for f in rule_focuses if f != "general"]
    if not non_general:
        return True

    focus_set = frozenset(non_general)
    for pair in _CONFLICT_FOCUS_PAIRS:
        if pair <= focus_set:
            return True

    has_context = bool(conversation_history) or bool(recommended_medicines)
    if not has_context:
        return False

    from src.services.medicine_qa_routing import (
        _extract_brand_mentions,
        _is_anaphoric_reference,
    )

    short = len(t) <= 56
    anaphora = _is_anaphoric_reference(t)
    # 疑問・心配・依頼の「型」（個別副作用語の列挙ではない）
    questionish = bool(
        re.search(
            r"[?？]|どう|なに|何|教えて|大丈夫|平気|いい|かな|ん？|心配|気になる|知りたい",
            t,
        )
    )
    # 固有ブランド言及の有無だけで thin を見る（会話文の誤エンティティに引っ張られない）
    thin_entity = len(_extract_brand_mentions(t)) == 0

    # 文脈依存の短い follow-up / 指示語質問はルールが脆い → LLM
    if has_context and thin_entity and (anaphora or (short and questionish)):
        return True
    # ルールが単一 focus でも、指示語＋身体変化の「あとで〜」型は誤分類しやすい
    if has_context and anaphora and thin_entity and len(non_general) == 1:
        if re.search(r"(?:あと|後|してき|てきて|なんとなく|なんか)", t):
            return True
    return False


def should_try_focus_llm_enrichment(
    rule_focuses: list[str],
    user_message: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """LLM 補完を試みる条件（コスト抑制: 曖昧・衝突時のみ）。"""
    if not is_medicine_qa_focus_llm_enabled():
        return False
    if not _has_openai_client():
        return False
    return _looks_structurally_ambiguous(
        user_message,
        rule_focuses,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    )


def _format_history(history: list[dict[str, Any]] | None, *, limit: int = 6) -> str:
    if not history:
        return "(なし)"
    lines: list[str] = []
    for m in history[-limit:]:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        content = str(m.get("content") or m.get("message") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(なし)"


def _format_recommended(meds: list[dict[str, Any]] | None) -> str:
    if not meds:
        return "(なし)"
    names = [
        str(m.get("product_name") or m.get("name") or "").strip()
        for m in meds
        if isinstance(m, dict)
    ]
    names = [n for n in names if n]
    return ", ".join(names[:4]) if names else "(なし)"


def _parse_focus_response(raw: str) -> list[MedicineQaFocus]:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 緩いフォールバック: focus 名だけ拾う
        found: list[MedicineQaFocus] = []
        for f in _VALID_FOCUSES:
            if f != "general" and re.search(rf"\b{re.escape(f)}\b", text):
                found.append(f)  # type: ignore[arg-type]
        return found[:3]
    focuses_raw = data.get("focuses") if isinstance(data, dict) else None
    if not isinstance(focuses_raw, list):
        return []
    out: list[MedicineQaFocus] = []
    for item in focuses_raw:
        f = str(item or "").strip()
        if f in _VALID_FOCUSES and f not in out:
            out.append(f)  # type: ignore[arg-type]
    return out


def enrich_medicine_qa_focuses_llm(
    user_message: str,
    rule_focuses: list[str],
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> list[MedicineQaFocus]:
    """LLM で focus を推定。失敗時は rule_focuses をそのまま返す。"""
    if not should_try_focus_llm_enrichment(
        rule_focuses,
        user_message,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return list(rule_focuses)  # type: ignore[arg-type]

    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return list(rule_focuses)  # type: ignore[arg-type]

    if not openai_client:
        return list(rule_focuses)  # type: ignore[arg-type]

    model = os.getenv("MEDICINE_QA_FOCUS_LLM_MODEL", "gpt-4o-mini")
    rule_hint = ", ".join(rule_focuses) if rule_focuses else "general"
    prompt = (
        "あなたは市販薬チャットの意図分類器です。患者の発話と会話文脈だけを見て focus を決める。\n"
        "特定フレーズへの一致ではなく、ユーザーが知りたいことを優先する。\n\n"
        f"ユーザー発話: {user_message}\n"
        f"ルール暫定 focus: {rule_hint}\n"
        f"推奨医薬品: {_format_recommended(recommended_medicines)}\n"
        f"会話履歴:\n{_format_history(conversation_history)}\n\n"
        "focus 候補: comparison, side_effect, doping, interaction, "
        "usage, ingredient, age, product_image, general\n"
        "指針（フレーズ一致ではなくユーザー意図優先）:\n"
        "- 飲むと眠い/だるい/胃がむかむか → side_effect（usage にしない）\n"
        "- 何回/何錠/食前食後/間隔 → usage\n"
        "- お酒・他薬との同時 → interaction（比較語があっても併用意図なら interaction）\n"
        "- 大会/競技の前後で使ってよいか → doping\n"
        "- 履歴に子ども・学年・妊婦・高齢などライフステージがあり、"
        "市販薬/服用の可否を聞いている → age\n"
        "- 症状の追加報告だけ（薬の可否を聞いていない）→ age にしない\n"
        "- 箱/見た目/写真 → product_image\n"
        "- どっち/違い → comparison\n"
        "- 指示語のみで薬が特定できないときは general でもよい\n"
        'JSONのみ: {"focuses": ["..."], "reason": "短い理由"}'
    )
    try:
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path="medicine_qa/focus_llm",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=100,
        )
        parsed = _parse_focus_response(extract_completion_text(resp))
        if parsed and parsed != ["general"]:
            logger.info("medicine_qa_focus_llm: %s -> %s", user_message[:40], parsed)
            return parsed
        if parsed == ["general"] and rule_focuses == ["general"]:
            return parsed
    except Exception:
        logger.warning("medicine_qa_focus_llm failed", exc_info=True)
    return list(rule_focuses)  # type: ignore[arg-type]
