"""
環境アレルギー情報を user_attributes に反映する。

UI の「アレルギー」欄・Safety Rail は allergies を参照する。
花粉症・アレルギー性鼻炎などは allergies のみに載せ、medical_history には入れない。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

# 入力キーワード → allergies 表示ラベル
_ENV_ALLERGY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("季節性アレルギー性鼻炎", "アレルギー性鼻炎"),
    ("常年性アレルギー性鼻炎", "アレルギー性鼻炎"),
    ("アレルギー性鼻炎", "アレルギー性鼻炎"),
    ("花粉症", "花粉"),
    ("アトピー性皮膚炎", "アトピー"),
    ("アトピー", "アトピー"),
)

# medical_history に残っている場合の移行用（旧データ・LLM 出力の正規化）
_ENV_HISTORY_TO_ALLERGY: dict[str, str] = dict(_ENV_ALLERGY_PATTERNS)


def _append_unique(target: List[str], value: str) -> bool:
    text = (value or "").strip()
    if not text or text in target:
        return False
    target.append(text)
    return True


def is_environmental_allergy_label(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return text in _ENV_HISTORY_TO_ALLERGY or text in _ENV_HISTORY_TO_ALLERGY.values()


def extract_environmental_allergens_from_message(message: str) -> Dict[str, List[str]]:
    """メッセージから環境アレルギーを即時抽出（allergies のみ）。"""
    msg = (message or "").strip()
    if not msg:
        return {}
    allergies: List[str] = []
    for needle, allergy_label in _ENV_ALLERGY_PATTERNS:
        if needle in msg:
            _append_unique(allergies, allergy_label)
    return {"allergies": allergies} if allergies else {}


def normalize_environmental_allergens(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """環境アレルギーを allergies に集約し、medical_history から除去する。"""
    if not attrs or not isinstance(attrs, dict):
        return attrs or {}
    merged = dict(attrs)
    allergies = list(merged.get("allergies") or [])
    history = list(merged.get("medical_history") or [])
    new_history: List[str] = []
    changed = False
    for hist in history:
        text = str(hist).strip()
        if not text:
            continue
        label = _ENV_HISTORY_TO_ALLERGY.get(text)
        if label:
            if _append_unique(allergies, label):
                changed = True
            changed = True
            continue
        if text in _ENV_HISTORY_TO_ALLERGY.values():
            if _append_unique(allergies, text):
                changed = True
            changed = True
            continue
        new_history.append(text)
    if new_history != history:
        merged["medical_history"] = new_history
        changed = True
    if changed or allergies:
        merged["allergies"] = allergies
    return merged


def filter_display_medical_history(history: Iterable) -> List[str]:
    """UI 表示用: 環境アレルギー由来の既往症を除外。"""
    out: List[str] = []
    for item in history or []:
        text = str(item).strip()
        if text and not is_environmental_allergy_label(text):
            out.append(text)
    return out


def is_otc_allergy_consultation_entry(message: str) -> bool:
    """
    「花粉症です」など、環境アレルギーの相談入口のみ（具体症状なし）。
    この場合は推奨せずカウンセリングで症状を聞く。
    """
    msg = (message or "").strip()
    if not msg or not extract_environmental_allergens_from_message(msg):
        return False
    try:
        from config.dialect_dictionary import EMOTIONAL_NEGATIVE_WORDS
        from src.utils.input_helpers import has_explicit_symptom_signal

        if any(word in msg for word in EMOTIONAL_NEGATIVE_WORDS):
            return False
        if has_explicit_symptom_signal(msg):
            return False
        from src.core.diagnosis_detection import is_diagnosis_only

        for needle, _ in _ENV_ALLERGY_PATTERNS:
            if needle in msg and is_diagnosis_only(msg, needle):
                return True
    except ImportError:
        pass
    return False


def merge_chat_user_attributes(
    db_attrs: Dict[str, Any] | None,
    session_attrs: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """チャット POST 終了時: DB と session の user_attributes をマージ。"""
    from src.services.line_user_memory import merge_user_attributes

    db = dict(db_attrs or {})
    session = dict(session_attrs or {})
    merged = merge_user_attributes(db, session)
    for key in ("allergies", "current_medications", "medical_history"):
        combined: List[str] = []
        for src in (db, session):
            for item in src.get(key) or []:
                text = str(item).strip()
                if text and text not in combined:
                    combined.append(text)
        if combined:
            merged[key] = combined
        elif key in merged and not merged.get(key):
            merged[key] = []
    return normalize_environmental_allergens(merged)


def merge_list_attribute(existing: Iterable, incoming) -> tuple[list, bool]:
    """リスト属性を和集合でマージ。"""
    merged = list(existing or [])
    if isinstance(incoming, list):
        new_items = incoming
    elif isinstance(incoming, str) and incoming.strip():
        new_items = [x.strip() for x in incoming.replace("、", ",").split(",") if x.strip()]
    else:
        return merged, False
    if not new_items:
        return merged, False
    changed = False
    for item in new_items:
        text = str(item).strip()
        if text and text not in merged:
            merged.append(text)
            changed = True
    return merged, changed


# 後方互換
mirror_environmental_allergens_to_allergies = normalize_environmental_allergens
