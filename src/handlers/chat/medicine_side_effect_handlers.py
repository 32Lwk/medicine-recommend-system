"""推奨履歴なしの医薬品副作用 Q&A ハンドラ（CSV 第一 → KB 補完）。"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from src.core.medicine_data import CSV_PATH
from src.core.scoring_utils import load_side_effects_data, normalize_medicine_name_to_hankaku
from src.services.medicine_side_effect_routing import (
    mentions_drowsiness_side_effect,
    resolve_side_effect_query_subject,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_DROWSINESS_KEYWORDS = ("眠気", "傾眠", "眠くなる", "眠い")
_GI_KEYWORDS = ("胃腸", "胃痛", "下痢", "便秘", "吐き気", "悪心")


def _load_otc_df():
    try:
        import pandas as pd

        if os.path.exists(CSV_PATH):
            return pd.read_csv(CSV_PATH, encoding="utf-8")
    except Exception:
        logger.debug("otc csv load failed", exc_info=True)
    return None


def _find_products_by_name(query: str, medicine_df) -> List[dict]:
    from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query

    if medicine_df is None:
        return []
    return detect_medicine_name_in_query(query, medicine_df)


def _ingredients_for_products(products: List[dict]) -> List[str]:
    ingredients: List[str] = []
    for p in products:
        raw = str(p.get("ingredients") or "")
        for part in raw.replace("\n", ",").split(","):
            part = part.strip()
            if part and part not in ingredients:
                ingredients.append(part)
    return ingredients


def _side_effect_rows_for_ingredients(ingredients: List[str]) -> List[dict]:
    df = load_side_effects_data()
    if df is None or df.empty or not ingredients:
        return []
    rows: List[dict] = []
    for ing in ingredients:
        norm = normalize_medicine_name_to_hankaku(ing).lower()
        for _, row in df.iterrows():
            cell = normalize_medicine_name_to_hankaku(str(row.get("成分名") or "")).lower()
            if norm and (norm in cell or cell in norm):
                rows.append(row.to_dict())
                break
    return rows


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords)


def _build_drowsiness_answer(product_name: str, side_rows: List[dict]) -> str:
    drowsiness_hits = []
    for row in side_rows:
        symptoms = str(row.get("副作用症状") or "")
        if _contains_any(symptoms, _DROWSINESS_KEYWORDS):
            drowsiness_hits.append(str(row.get("成分名") or ""))

    if drowsiness_hits:
        return (
            f"「{product_name}」に含まれる成分（{', '.join(drowsiness_hits[:3])}）では、"
            f"添付文書上「{_join_unique_symptoms(side_rows, _DROWSINESS_KEYWORDS)}」等が報告されています。"
            "個人差があるため、運転・機械操作の前は注意してください。"
        )

    if "ロキソニン" in product_name or any("ロキソプロフェン" in str(r.get("成分名", "")) for r in side_rows):
        return (
            f"「{product_name}」（ロキソプロフェン系）では、一般に強い眠気は主要な副作用として"
            "挙げられていません。ただし個人差や他の成分・併用薬により眠気を感じる場合があります。"
            "運転前や重要な作業前は注意し、気になる症状が続く場合は薬剤師・医師に相談してください。"
        )

    return (
        f"「{product_name}」について、添付文書ベースの情報からは眠気が主要副作用として"
        "明記されていない場合があります。個人差があるため、眠気を感じたら運転等は控え、"
        "薬剤師・医師に相談してください。"
    )


def _join_unique_symptoms(rows: List[dict], keywords: tuple[str, ...]) -> str:
    parts: List[str] = []
    for row in rows:
        symptoms = str(row.get("副作用症状") or "")
        for kw in keywords:
            if kw in symptoms and kw not in parts:
                parts.append(kw)
    return "・".join(parts[:5]) if parts else "眠気"


def _build_side_effect_answer(
    user_message: str,
    *,
    product_name: str,
    products: List[dict],
    side_rows: List[dict],
) -> Dict[str, Any]:
    if mentions_drowsiness_side_effect(user_message):
        answer = _build_drowsiness_answer(product_name, side_rows)
    elif side_rows:
        summaries = []
        for row in side_rows[:3]:
            ing = str(row.get("成分名") or "")
            level = str(row.get("副作用レベル") or "")
            symptoms = str(row.get("副作用症状") or "")[:200]
            summaries.append(f"・{ing}（{level}）: {symptoms}")
        answer = (
            f"「{product_name}」の副作用情報（添付文書・CSV 根拠）:\n"
            + "\n".join(summaries)
            + "\n\n個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。"
        )
    else:
        answer = (
            f"「{product_name}」の副作用情報をデータベースから特定できませんでした。"
            "製品の添付文書をご確認いただくか、薬剤師・医師にご相談ください。"
        )

    side_effects_text = ""
    if side_rows:
        side_effects_text = "; ".join(
            f"{r.get('成分名')}: {str(r.get('副作用症状') or '')[:120]}"
            for r in side_rows[:3]
        )

    return {
        "answer": answer,
        "medicine_details": product_name,
        "side_effects": side_effects_text,
        "consultation_advice": (
            "市販薬の副作用は個人差があります。"
            "既存の疾患・併用薬がある場合は使用前に薬剤師・医師に相談してください。"
        ),
        "source": "medicine_side_effects.csv",
    }


def _try_kb_fallback(user_message: str, product_name: str) -> Optional[str]:
    try:
        from config.llm_flags import is_medicine_side_effect_kb_enabled

        if not is_medicine_side_effect_kb_enabled():
            return None
    except ImportError:
        return None

    try:
        from src.services.bedrock_kb_retrieve import retrieve_medicine_context

        query = f"{product_name} 副作用 {user_message}"
        kb = retrieve_medicine_context(query, recommended_medicines=[{"product_name": product_name}])
        chunks = kb.get("chunks") or []
        if not chunks:
            return None
        snippet = str(chunks[0])[:800].strip()
        uris = kb.get("source_uris") or []
        citation = uris[0] if uris else "Bedrock Knowledge Base"
        return (
            f"「{product_name}」の副作用について（KB 参照）:\n{snippet}\n\n"
            f"出典: {citation}\n\n"
            "個人差があります。気になる症状が続く場合は使用を中止し、"
            "薬剤師・医師にご相談ください。"
        )
    except Exception:
        logger.debug("KB fallback failed", exc_info=True)
        return None


def handle_medicine_side_effect_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
) -> ResponseTuple:
    """副作用 Q&A — 症状推奨フローに入れない。"""
    from src.handlers.chat.chat_medicine_qa_html import finalize_medicine_qa_response

    subject = resolve_side_effect_query_subject(user_message) or user_message
    medicine_df = _load_otc_df()
    products = _find_products_by_name(subject, medicine_df)
    product_name = (
        str(products[0].get("product_name") or subject)
        if products
        else subject
    )
    ingredients = _ingredients_for_products(products) if products else []
    side_rows = _side_effect_rows_for_ingredients(ingredients)

    chat_response = _build_side_effect_answer(
        user_message,
        product_name=product_name,
        products=products,
        side_rows=side_rows,
    )

    if not side_rows:
        kb_answer = _try_kb_fallback(user_message, product_name)
        if kb_answer:
            chat_response["answer"] = kb_answer
            chat_response["source"] = "bedrock_kb"

    msg_count = finalize_medicine_qa_response(
        session,
        client_info,
        sid,
        user_message,
        chat_response,
    )
    if sid and session is not None:
        session.setdefault("messages", [])
        if session["messages"]:
            last = session["messages"][-1]
            if isinstance(last, dict):
                diag = last.setdefault("diagnosis", {})
                if isinstance(diag, dict):
                    diag["kind"] = "medicine_side_effect_qa"
                    diag["render"] = "sage_qa"

    return {"status": "ok", "message_count": msg_count}, 200
