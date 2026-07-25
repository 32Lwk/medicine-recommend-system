"""医薬品 Q&A と副作用 Q&A の意図ベース切り分け。"""
from __future__ import annotations

import re
from typing import Any, Literal

from src.dialogue.routing.context_signals import extract_drug_entities

MedicineQaFocus = Literal[
    "comparison",
    "side_effect",
    "doping",
    "interaction",
    "usage",
    "general",
]

# 副作用 Q&A に限定する話題（高信頼 gate 用）
_SIDE_EFFECT_TOPIC_KEYWORDS = (
    "副作用",
    "眠くなる",
    "眠気",
    "安全",
    "飲んでいい",
    "飲んでもいい",
    "飲んで良い",
    "ダメ",
    "禁忌",
)

_SIDE_EFFECT_QA_RE = re.compile(
    r"(.+?)(?:って|は|の)(?:眠い|眠くなる|眠気|副作用|安全|飲んで(?:も)?(?:いい|良い)|ダメ)",
    re.IGNORECASE,
)

# 質問・説明依頼の最小シグナル（個別ケース列挙はしない）
_QUESTION_INTENT_RE = re.compile(
    r"[?？]|教えて|説明|とは|知りたい|どう|何が|何を|どれ|選び",
    re.IGNORECASE,
)

_SPORTS_KEYWORDS = ("競技", "ドーピング", "陸上", "マラソン", "大会", "レース", "試合")
_INTERACTION_KEYWORDS = ("併用", "一緒に", "飲み合わせ", "相互作用", "同時に")
_USAGE_KEYWORDS = ("飲み方", "用法", "用量", "何錠", "いつ飲")

# テンプレート補足（質問と無関係なときは表示しない）
_GENERIC_BOILERPLATE_MARKERS = (
    "詳細は登録販売者にご確認ください",
    "ドーピング情報を確認してください",
    "風邪薬を複数同時に内服しないでください",
    "眠気・口渇・胃腸障害などが出ることがあります",
    "推奨医薬品の情報では回答できません",
    "詳細情報を取得できませんでした",
    "飲み合わせ情報を取得できませんでした",
    "ドーピング規制の確認ができませんでした",
    "副作用情報を取得できませんでした",
)

_QA_SECTION_KEYS = (
    "medicine_details",
    "interactions",
    "doping_check",
    "side_effects",
    "consultation_advice",
)

_SECTION_TITLES: dict[str, dict[str, str]] = {
    "comparison": {
        "medicine_details": "製品比較",
        "interactions": "併用・重複の注意",
        "side_effects": "副作用の違い",
        "consultation_advice": "選び方のポイント",
    },
    "side_effect": {
        "medicine_details": "医薬品の詳細",
        "side_effects": "副作用情報",
    },
    "doping": {
        "medicine_details": "医薬品の詳細",
        "doping_check": "ドーピングチェック",
    },
    "interaction": {
        "medicine_details": "医薬品の詳細",
        "interactions": "相互作用の注意",
    },
    "usage": {
        "medicine_details": "医薬品の詳細",
        "consultation_advice": "用法の注意",
    },
}


def is_strict_medicine_side_effect_question(text: str) -> bool:
    """副作用・眠気に関する医薬品 Q&A のみ True（gate / early route 用）。"""
    t = (text or "").strip()
    if not t:
        return False
    if _SIDE_EFFECT_QA_RE.search(t):
        return True
    drugs = extract_drug_entities(t)
    if not drugs:
        return False
    if any(k in t for k in _SIDE_EFFECT_TOPIC_KEYWORDS):
        return True
    if "眠い" in t and ("?" in t or t.endswith(("?", "？"))):
        return True
    return False


def is_medicine_information_question(text: str) -> bool:
    """
    医薬品名を含む情報質問（比較・説明・選び方など）。
    副作用 Q&A ではない場合に medicine_qa（LLM）へ振り分ける。
    """
    t = (text or "").strip()
    if not t or not extract_drug_entities(t):
        return False
    if is_strict_medicine_side_effect_question(t):
        return False
    return bool(_QUESTION_INTENT_RE.search(t))


def should_skip_recommendation_for_medicine_qa(text: str) -> bool:
    """明示的な医薬品名 Q&A では症状推奨を走らせない。"""
    return is_medicine_information_question(text) or is_strict_medicine_side_effect_question(
        text
    )


def infer_medicine_qa_focus(user_message: str) -> MedicineQaFocus:
    """質問意図に応じた Q&A 補足セクションの焦点（ルール列挙ではなく少数シグナル）。"""
    t = (user_message or "").strip()
    if len(extract_drug_entities(t)) >= 2:
        return "comparison"
    if is_strict_medicine_side_effect_question(t):
        return "side_effect"
    if any(k in t for k in _SPORTS_KEYWORDS):
        return "doping"
    if any(k in t for k in _INTERACTION_KEYWORDS):
        return "interaction"
    if any(k in t for k in _USAGE_KEYWORDS):
        return "usage"
    return "general"


def is_generic_qa_boilerplate(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    return any(marker in s for marker in _GENERIC_BOILERPLATE_MARKERS)


def _normalize_ws(text: str, *, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()[:limit]


def _ingredient_class_hint(ingredients: str) -> str:
    ing = (ingredients or "").lower()
    if "ロキソプロフェン" in ing or "イブプロフェン" in ing or "アスピリン" in ing:
        if "アセトアミノフェン" in ing and "イブプロフェン" not in ing:
            return "アセトアミノフェン系"
        return "NSAIDs（非ステロイド性消炎鎮痛薬）系"
    if "アセトアミノフェン" in ing:
        return "アセトアミノフェン系"
    return ""


def _comparison_lines(medicines: list[dict[str, Any]], user_message: str) -> str:
    from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

    parts: list[str] = []
    for med in medicines[:4]:
        name = str(med.get("product_name") or "").strip()
        if not name:
            continue
        ingredients = _normalize_ws(str(med.get("ingredients") or ""), limit=120)
        cls = _ingredient_class_hint(ingredients)
        cls_note = f"（{cls}）" if cls else ""
        use_hint = _short_medicine_use_hint(med, user_message)
        parts.append(f"**{name}**{cls_note}：主成分は{ingredients or '要確認'}。{use_hint}")
    return "\n".join(parts)


def _comparison_interaction_note(medicines: list[dict[str, Any]]) -> str:
    classes = {_ingredient_class_hint(str(m.get("ingredients") or "")) for m in medicines}
    classes.discard("")
    if "NSAIDs（非ステロイド性消炎鎮痛薬）系" in classes and len(medicines) >= 2:
        return (
            "ロキソプロフェン・イブプロフェンなど同系統の解熱鎮痛薬を同時期に重ねて使わないでください。"
            "胃腸への負担が増えることがあります。"
        )
    if len(classes) >= 2:
        return "成分系統が異なる製品です。併用の可否は症状・年齢・持病を踏まえ登録販売者にご確認ください。"
    return ""


def _comparison_side_effect_note(medicines: list[dict[str, Any]]) -> str:
    nsaid = any(
        _ingredient_class_hint(str(m.get("ingredients") or "")).startswith("NSAIDs")
        for m in medicines
    )
    acetaminophen = any(
        "アセトアミノフェン系" == _ingredient_class_hint(str(m.get("ingredients") or ""))
        for m in medicines
    )
    notes: list[str] = []
    if nsaid:
        notes.append("NSAIDs 系は胃腸障害（胃痛・胃もたれ等）に注意が必要です。")
    if acetaminophen:
        notes.append("アセトアミノフェン系は過量服用に注意が必要です。")
    if not notes:
        return ""
    notes.append("いずれも一般に強い眠気は主要副作用としては稀ですが、製品により成分追加があります。")
    return " ".join(notes)


def build_focused_qa_sections(
    user_message: str,
    medicines: list[dict[str, Any]] | None,
) -> dict[str, str]:
    """質問意図に沿った補足フィールドのみ返す（空文字 = セクション非表示）。"""
    focus = infer_medicine_qa_focus(user_message)
    meds = medicines or []
    out: dict[str, str] = {k: "" for k in _QA_SECTION_KEYS}

    if focus == "comparison":
        if meds:
            out["medicine_details"] = _comparison_lines(meds, user_message)
            interaction = _comparison_interaction_note(meds)
            if interaction:
                out["interactions"] = interaction
            side = _comparison_side_effect_note(meds)
            if side:
                out["side_effects"] = side
            out["consultation_advice"] = (
                "持病・年齢・他のお薬の服用がある場合は、用途と成分を伝えて登録販売者に相談すると選びやすくなります。"
            )
        return out

    if focus == "side_effect":
        if meds:
            from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

            out["medicine_details"] = "\n".join(
                f"**{m.get('product_name')}**：{_short_medicine_use_hint(m, user_message)}"
                for m in meds[:3]
                if m.get("product_name")
            )
        return out

    if focus == "doping":
        if meds:
            from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

            out["medicine_details"] = "\n".join(
                f"**{m.get('product_name')}**：{_short_medicine_use_hint(m, user_message)}"
                for m in meds[:3]
                if m.get("product_name")
            )
            dop_parts: list[str] = []
            for m in meds[:3]:
                name = str(m.get("product_name") or "")
                dop = str(m.get("doping_prohibited") or "")
                cat = str(m.get("competition_category") or "")
                if "あり" in dop:
                    dop_parts.append(
                        f"**{name}**：禁止物質あり（{cat or '競技会区分要確認'}）。"
                    )
                elif name:
                    dop_parts.append(f"**{name}**：リスト記載の禁止物質なし（大会規定は要確認）。")
            out["doping_check"] = " ".join(dop_parts)
        return out

    if focus == "interaction" and meds:
        from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

        out["medicine_details"] = "\n".join(
            f"**{m.get('product_name')}**：{_short_medicine_use_hint(m, user_message)}"
            for m in meds[:3]
            if m.get("product_name")
        )
        note = _comparison_interaction_note(meds)
        if note:
            out["interactions"] = note
        return out

    if focus == "usage" and meds:
        from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

        out["medicine_details"] = "\n".join(
            f"**{m.get('product_name')}**：{_short_medicine_use_hint(m, user_message)}"
            for m in meds[:3]
            if m.get("product_name")
        )
        usage_bits = [
            _normalize_ws(str(m.get("usage") or ""), limit=160)
            for m in meds[:2]
            if m.get("usage")
        ]
        if usage_bits:
            out["consultation_advice"] = " ".join(usage_bits)
        return out

    # general: 製品情報があるときだけ最小限
    if meds:
        from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

        out["medicine_details"] = "\n".join(
            f"**{m.get('product_name')}**：{_short_medicine_use_hint(m, user_message)}"
            for m in meds[:2]
            if m.get("product_name")
        )
    return out


def prune_qa_response(
    chat_response: dict[str, Any],
    user_message: str,
    *,
    answer: str | None = None,
) -> dict[str, Any]:
    """汎用テンプレ・回答重複・質問と無関係な補足を除去する。"""
    out = dict(chat_response)
    focus = infer_medicine_qa_focus(user_message)
    out["qa_focus"] = focus
    main_answer = _normalize_ws(str(answer or out.get("answer") or ""), limit=500)

    allowed = set(_QA_SECTION_KEYS)
    if focus == "comparison":
        allowed = {"medicine_details", "interactions", "side_effects", "consultation_advice"}
    elif focus == "side_effect":
        allowed = {"medicine_details", "side_effects", "consultation_advice"}
    elif focus == "doping":
        allowed = {"medicine_details", "doping_check", "consultation_advice"}
    elif focus == "interaction":
        allowed = {"medicine_details", "interactions", "consultation_advice"}
    elif focus == "usage":
        allowed = {"medicine_details", "consultation_advice"}
    elif focus == "general":
        allowed = {"medicine_details", "consultation_advice"}

    for key in _QA_SECTION_KEYS:
        val = str(out.get(key) or "").strip()
        if key not in allowed:
            out[key] = ""
            continue
        if not val or is_generic_qa_boilerplate(val):
            out[key] = ""
            continue
        if main_answer and _normalize_ws(val, limit=120) in main_answer:
            out[key] = ""
            continue
        if main_answer and len(val) > 20 and val[:40] in main_answer:
            out[key] = ""
    return out


def section_title_for_focus(focus: str, field_key: str, default: str) -> str:
    return _SECTION_TITLES.get(focus, {}).get(field_key, default)

