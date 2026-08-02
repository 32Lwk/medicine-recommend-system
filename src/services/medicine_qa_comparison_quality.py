"""比較 Q&A 応答の構造品質チェック（特定フレーズ依存を避け、ロールベースで検証）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_ACTIONABLE_PICK_RE = re.compile(
    r"向き|優先|検討|マイルド|効き目|胃|バランス|選び|併用|重ね"
)
_DIFFERENTIATION_RE = re.compile(
    r"成分|効き|胃|違|ロキソ|イブ|アスピ|アセトア|解熱|鎮痛"
)
_NOISE_PHRASE_RE = re.compile(
    r"剤形(?:は|が)?(?:この情報|確認でき)"
)
_GENERIC_ONLY_RE = re.compile(
    r"^(?:お近くの)?登録販売者|医師.{0,12}(?:相談|ご相談)"
)


@dataclass
class ComparisonQaQualityReport:
    ok: bool
    issues: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.issues.append(msg)


def assess_comparison_qa_response(
    response: dict[str, Any],
    *,
    medicines: list[dict[str, Any]] | None = None,
    expects_comparison_sections: bool = True,
) -> ComparisonQaQualityReport:
    """比較 Q&A の構造品質を評価（特定製品名のハードコードはしない）。"""
    report = ComparisonQaQualityReport(ok=True)
    answer = str(response.get("answer") or "").strip()
    meds = medicines or []

    if not answer:
        report.add("answer が空")
    elif len(answer) < 20:
        report.add("answer が短すぎる")
    elif _GENERIC_ONLY_RE.search(answer) and not _DIFFERENTIATION_RE.search(answer):
        report.add("answer が相談勧告のみで差別化がない")

    blob = " ".join(str(response.get(k) or "") for k in (
        "answer", "medicine_details", "interactions", "side_effects", "consultation_advice"
    ))
    if _NOISE_PHRASE_RE.search(blob):
        report.add("剤形不明ノイズフレーズが残っている")

    if expects_comparison_sections:
        details = str(response.get("medicine_details") or "")
        if not details.strip():
            report.add("medicine_details が空")
        elif "ui-qa-product-line" not in details and meds:
            report.add("medicine_details に製品行フォーマットがない")
        elif meds:
            named = sum(
                1 for m in meds
                if str(m.get("product_name") or "") and str(m.get("product_name") or "") in details
            )
            if named < min(len(meds), 2):
                report.add("medicine_details に比較対象製品が十分含まれていない")

        pick = str(response.get("consultation_advice") or "")
        if not pick.strip():
            report.add("consultation_advice（選び方）が空")
        elif not _ACTIONABLE_PICK_RE.search(pick):
            report.add("選び方に具体的な判断軸がない")

        inter = str(response.get("interactions") or "")
        side = str(response.get("side_effects") or "")
        if inter and side:
            inter_norm = re.sub(r"\s+", "", inter[:80])
            side_norm = re.sub(r"\s+", "", side[:80])
            if inter_norm and inter_norm in re.sub(r"\s+", "", side):
                report.add("interactions と side_effects が重複")

    report.ok = not report.issues
    return report


def build_comparison_answer_scaffold(
    medicines: list[dict[str, Any]],
    user_message: str = "",
) -> str:
    """LLM 回答が薄いときの汎用フォールバック（成分系統ベース）。"""
    from src.services.medicine_qa_routing import (
        _comparison_scenario_hints,
        _ingredient_comparison_traits,
        _normalize_ws,
    )

    if len(medicines) < 2:
        return ""

    parts: list[str] = []
    classes: list[str] = []
    for med in medicines[:4]:
        name = str(med.get("product_name") or "").strip()
        ing = _normalize_ws(str(med.get("ingredients") or ""), limit=80)
        traits = _ingredient_comparison_traits(ing)
        if name and ing:
            parts.append(f"{name}は{ing}（{traits['potency'] or '解熱鎮痛'}）")
            if traits["class_label"]:
                classes.append(traits["class_label"])

    if not parts:
        return ""

    opener = "、".join(parts[:3]) + "。"
    hints = _comparison_scenario_hints(medicines)
    if hints:
        return opener + hints[0]
    if len(set(classes)) >= 2:
        return opener + "成分系統が異なるため、併用可否は登録販売者に確認してください。"
    return opener + "同系統の解熱鎮痛薬のため、重ねて使わないでください。"


def enrich_thin_comparison_answer(
    response: dict[str, Any],
    medicines: list[dict[str, Any]],
    *,
    user_message: str = "",
) -> dict[str, Any]:
    """比較 answer が薄い・汎用のみのときルールベース要点を補完。"""
    out = dict(response)
    answer = str(out.get("answer") or "").strip()
    if not medicines or len(medicines) < 2:
        return out
    needs_enrich = (
        not answer
        or len(answer) < 40
        or (_GENERIC_ONLY_RE.search(answer) and not _DIFFERENTIATION_RE.search(answer))
        or not _DIFFERENTIATION_RE.search(answer)
    )
    if not needs_enrich:
        return out
    scaffold = build_comparison_answer_scaffold(medicines, user_message)
    if scaffold:
        out["answer"] = scaffold if not answer else f"{answer.rstrip('。')}。{scaffold}"
    return out
