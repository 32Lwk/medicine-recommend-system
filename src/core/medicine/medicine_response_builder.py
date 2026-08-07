"""
医薬品詳細・チャット文脈の組み立て

get_medicine_details, detect_medicine_name_in_query, chat_with_medicine_context を提供。
"""

import json
import logging
import re
from typing import Any

import pandas as pd

from src.core.medicine_data import CSV_PATH
from src.core.openai_client import client as _default_openai_client

logger = logging.getLogger(__name__)


def _safe_get(value):
    if value is None or str(value) == "nan":
        return ""
    return value


def get_medicine_details(recommended_medicines, medicine_list):
    """
    推奨医薬品の詳細情報（使用上の注意など）を取得
    """
    detailed_medicines = []
    for rec in recommended_medicines:
        product_name = rec.get("product_name", "")
        manufacturer = rec.get("manufacturer", "")
        if product_name is None or str(product_name) == "nan":
            product_name = ""
        if manufacturer is None or str(manufacturer) == "nan":
            manufacturer = ""
        matched_medicine = None
        for medicine in medicine_list:
            csv_product = medicine.get("製品名", "")
            csv_manufacturer = medicine.get("メーカー名", "")
            if csv_product is None or str(csv_product) == "nan":
                csv_product = ""
            if csv_manufacturer is None or str(csv_manufacturer) == "nan":
                csv_manufacturer = ""
            if product_name == csv_product and manufacturer == csv_manufacturer:
                matched_medicine = medicine
                break
        if not matched_medicine:
            for medicine in medicine_list:
                csv_product = medicine.get("製品名", "")
                if csv_product is None or str(csv_product) == "nan":
                    csv_product = ""
                if product_name == csv_product:
                    matched_medicine = medicine
                    break
        if matched_medicine:
            usage_notes = rec.get("usage_notes")
            if not usage_notes:
                usage_notes = matched_medicine.get("使用上の注意", "")

            def calculate_medicine_score(medicine_data, rec_data, notes):
                score = 0
                max_score = 100
                rank_score = max(0, 30 - (rec_data.get("number", 1) - 1) * 5)
                score += rank_score
                efficacy = _safe_get(medicine_data.get("効能効果", ""))
                if efficacy and len(efficacy) > 50:
                    score += 20
                elif efficacy and len(efficacy) > 20:
                    score += 10
                ingredients = _safe_get(medicine_data.get("成分", ""))
                if ingredients and len(ingredients) > 30:
                    score += 15
                elif ingredients and len(ingredients) > 10:
                    score += 8
                usage_notes_safe = _safe_get(notes)
                if usage_notes_safe and len(usage_notes_safe) > 50:
                    score += 15
                elif usage_notes_safe and len(usage_notes_safe) > 20:
                    score += 8
                doping = _safe_get(medicine_data.get("禁止物質あり", ""))
                if doping and doping != "":
                    score += 10
                reason = _safe_get(rec_data.get("reason", ""))
                if reason and len(reason) > 30:
                    score += 10
                elif reason and len(reason) > 10:
                    score += 5
                return min(score, max_score)

            medicine_score = calculate_medicine_score(
                matched_medicine, rec, usage_notes
            )
            detailed_medicine = {
                "number": rec.get("number", 0),
                "product_name": _safe_get(
                    matched_medicine.get("製品名", product_name)
                ),
                "manufacturer": _safe_get(
                    matched_medicine.get("メーカー名", manufacturer)
                ),
                "reason": _safe_get(rec.get("reason", "")),
                "efficacy": _safe_get(matched_medicine.get("効能効果", "")),
                "ingredients": _safe_get(matched_medicine.get("成分", "")),
                "usage_notes": _safe_get(usage_notes),
                "doping_prohibited": _safe_get(
                    matched_medicine.get("禁止物質あり", "")
                ),
                "competition_category": _safe_get(
                    matched_medicine.get("競技会区分", "")
                ),
                "doping_conditions": _safe_get(
                    matched_medicine.get("条件", "")
                ),
                "score": (medicine_score / 100.0),
            }
            detailed_medicines.append(detailed_medicine)
            print(
                f"医薬品詳細情報取得: {product_name} ({manufacturer}) -> {matched_medicine.get('製品名', '')} ({matched_medicine.get('メーカー名', '')})"
            )
        else:
            print(f"医薬品詳細情報が見つかりません: {product_name} ({manufacturer})")
            usage_notes = rec.get("usage_notes")
            if not usage_notes:
                usage_notes = "詳細情報が見つかりませんでした"

            def calculate_fallback_score(rec_data):
                score = 0
                rank_score = max(0, 30 - (rec_data.get("number", 1) - 1) * 5)
                score += rank_score
                reason = _safe_get(rec_data.get("reason", ""))
                if reason and len(reason) > 30:
                    score += 20
                elif reason and len(reason) > 10:
                    score += 10
                return min(score, 50)

            fallback_score = calculate_fallback_score(rec)
            detailed_medicine = {
                "number": rec.get("number", 0),
                "product_name": _safe_get(product_name),
                "manufacturer": _safe_get(manufacturer),
                "reason": _safe_get(rec.get("reason", "")),
                "efficacy": "詳細情報が見つかりませんでした",
                "ingredients": "詳細情報が見つかりませんでした",
                "usage_notes": _safe_get(usage_notes),
                "doping_prohibited": "詳細情報が見つかりませんでした",
                "competition_category": "詳細情報が見つかりませんでした",
                "doping_conditions": "詳細情報が見つかりませんでした",
                "score": (fallback_score / 100.0),
            }
            detailed_medicines.append(detailed_medicine)
    return detailed_medicines


def detect_medicine_name_in_query(user_message, medicine_df, *, session=None):
    """
    ユーザーの質問から医薬品名を検出する。

    session がある場合はセッション内ブランドピンを優先する。
    """
    if medicine_df is None or medicine_df.empty:
        return []
    detected_medicines: list[dict] = []
    user_message_lower = user_message.lower()

    # ブランド通称（ロキソニン・イブ等）— 先頭一致 + 成分エイリアス + session pin
    try:
        from src.services.medicine_brand_resolve import resolve_brand_hints_in_query

        detected_medicines.extend(
            resolve_brand_hints_in_query(
                user_message, medicine_df, session=session
            )
        )
    except ImportError:
        pass

    for _, row in medicine_df.iterrows():
        ingredients = str(row.get("成分", "")).lower()
        if ingredients:
            ingredient_list = [ing.strip() for ing in ingredients.split(",")]
            for ingredient in ingredient_list:
                if ingredient and ingredient in user_message_lower:
                    detected_medicines.append({
                        "product_name": row.get("製品名", ""),
                        "manufacturer": row.get("メーカー名", ""),
                        "efficacy": row.get("効能効果", ""),
                        "usage": row.get("用法用量", ""),
                        "age_restriction": row.get("年齢制限", ""),
                        "ingredients": row.get("成分", ""),
                        "doping_prohibited": row.get("禁止物質あり", ""),
                        "medicine_type": row.get("医薬品の種類", ""),
                    })
                    break
    for _, row in medicine_df.iterrows():
        product_name = str(row.get("製品名", "")).lower()
        if product_name and any(
            word in product_name
            for word in user_message_lower.split()
            if len(word) > 2
        ):
            detected_medicines.append({
                "product_name": row.get("製品名", ""),
                "manufacturer": row.get("メーカー名", ""),
                "efficacy": row.get("効能効果", ""),
                "usage": row.get("用法用量", ""),
                "age_restriction": row.get("年齢制限", ""),
                "ingredients": row.get("成分", ""),
                "doping_prohibited": row.get("禁止物質あり", ""),
                "medicine_type": row.get("医薬品の種類", ""),
            })
    unique_medicines: list[dict] = []
    seen_names: set[str] = set()
    seen_hints: set[str] = set()
    brand_hints = []
    try:
        from src.dialogue.routing.context_signals import extract_drug_entities
        from src.services.medicine_brand_resolve import _brand_prefix_match

        brand_hints = extract_drug_entities(user_message)
    except ImportError:
        _brand_prefix_match = None  # type: ignore[assignment]

    for med in detected_medicines:
        name = str(med.get("product_name") or "")
        if not name or name in seen_names:
            continue
        hint_key = name
        if brand_hints and _brand_prefix_match:
            for hint in brand_hints:
                if _brand_prefix_match(hint, name):
                    hint_key = hint.lower()
                    break
        elif brand_hints:
            for hint in brand_hints:
                if name == hint or name.startswith(hint):
                    hint_key = hint.lower()
                    break
        if hint_key in seen_hints:
            continue
        unique_medicines.append(med)
        seen_names.add(name)
        seen_hints.add(hint_key)
    return unique_medicines[:10]


def _short_medicine_use_hint(med: dict, user_message: str) -> str:
    """競技・ドーピング文脈では効能全文の羅列を避け、用途を短くまとめる。"""
    name = str(med.get("product_name") or "")
    ingredients = str(med.get("ingredients") or "").replace("\n", " ")
    sports_ctx = any(
        k in (user_message or "")
        for k in ("競技", "ドーピング", "陸上", "マラソン", "大会", "レース", "試合")
    )
    if sports_ctx:
        med_type = str(med.get("medicine_type") or "")
        if "外用" in med_type or "スプレ" in name or "のど" in name:
            return "のどの炎症・痛み向けの外用薬です。"
        return "感冒症状の緩和向けの総合感冒薬です。"
    if "ロキソプロフェン" in ingredients:
        return "解熱鎮痛薬で、頭痛・歯痛・生理痛などに用いられます。"
    if "イブプロフェン" in ingredients:
        return "解熱鎮痛薬で、頭痛・歯痛・生理痛などに用いられます。"
    if "アセトアミノフェン" in ingredients and "イブプロフェン" not in ingredients:
        return "解熱鎮痛薬で、熱・痛みの緩和に用いられます。"
    efficacy = (med.get("efficacy") or "").replace("\n", " ").strip()
    if not efficacy:
        return "一般用医薬品です。"
    if len(efficacy) > 60:
        return f"{efficacy[:60]}…などの症状緩和に用いる一般用医薬品です。"
    return f"{efficacy}などの症状緩和に用いる一般用医薬品です。"


def _append_physical_handoff_hint(result: dict, user_message: str) -> None:
    """Ask Q&A 後に症状ベース推奨へ誘導するヒント"""
    hints = ("競技", "ドーピング", "風邪", "症状", "痛", "熱", "咳")
    if not any(h in (user_message or "") for h in hints):
        return
    advice = (result.get("consultation_advice") or "").strip()
    extra = (
        "より症状に合わせた市販薬の候補を挙げることもできます。"
        "具体的な症状（いつから・どのような痛み等）を教えていただければ、推奨フローでもご案内します。"
    )
    if extra not in advice:
        result["consultation_advice"] = f"{advice}\n\n{extra}".strip() if advice else extra


def _sanitize_qa_result(result: dict) -> dict:
    """Ask 回答の文字列フィールドから内部表現を除去。"""
    from src.services.concierge_output_sanitize import sanitize_medicine_ask_output

    if not isinstance(result, dict):
        return result
    out = dict(result)
    for key in (
        "answer",
        "medicine_details",
        "interactions",
        "doping_check",
        "side_effects",
        "consultation_advice",
    ):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = sanitize_medicine_ask_output(val)
    return out


def _apply_product_image_answer(
    parsed: dict,
    *,
    qa_focuses: list[str],
    recommended_medicines: list,
    user_message: str = "",
) -> dict:
    if "product_image" not in qa_focuses or not recommended_medicines:
        return parsed
    if not str(parsed.get("product_images_html") or "").strip():
        return parsed
    from src.services.medicine_qa_images import build_product_image_answer_text

    out = dict(parsed)
    out["answer"] = build_product_image_answer_text(
        recommended_medicines,
        user_message=user_message,
    )
    return out


def _finalize_structured_qa_response(
    parsed: dict,
    user_message: str,
    recommended_medicines: list,
    *,
    qa_focuses: list[str] | None = None,
    conversation_history: list | None = None,
    user_attributes: dict[str, Any] | None = None,
    answer: str | None = None,
) -> dict:
    from src.services.medicine_qa_routing import infer_medicine_qa_focuses, prune_qa_response
    from src.services.medicine_qa_images import attach_product_images_to_response

    fs = qa_focuses or infer_medicine_qa_focuses(
        user_message,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
        user_attributes=user_attributes,
    )
    out = prune_qa_response(parsed, user_message, focuses=fs, answer=answer)
    if "comparison" in fs and recommended_medicines:
        from src.services.medicine_qa_comparison_quality import enrich_thin_comparison_answer

        out = enrich_thin_comparison_answer(
            out,
            recommended_medicines,
            user_message=user_message,
        )
    if "product_image" in fs and recommended_medicines:
        out = attach_product_images_to_response(out, recommended_medicines)
        out = _apply_product_image_answer(
            out,
            qa_focuses=fs,
            recommended_medicines=recommended_medicines,
            user_message=user_message,
        )
    return _sanitize_qa_result(out)


def _apply_user_correction_pivot(
    user_message: str,
    recommended_medicines: list,
    qa_focuses: list[str],
    *,
    session: Any = None,
) -> tuple[list, list[str]]:
    """訂正発話時は comparison を外し、言及品目に絞る。"""
    from src.utils.input_helpers import detect_correction_intent

    if not detect_correction_intent(user_message):
        return recommended_medicines, qa_focuses

    from src.dialogue.routing.context_signals import extract_drug_entities

    entities = extract_drug_entities(user_message or "")
    focuses = [f for f in qa_focuses if f != "comparison"]
    if not focuses:
        focuses = ["ingredient", "side_effect"]

    if not entities:
        return recommended_medicines, focuses

    try:
        df = pd.read_csv(CSV_PATH)
        narrowed: list = []
        for ent in entities[:2]:
            hits = detect_medicine_name_in_query(ent, df, session=session)
            if hits:
                narrowed.append(hits[0])
        if narrowed:
            return narrowed[:3], focuses
    except Exception:
        logger.debug("correction pivot narrow skipped", exc_info=True)
    return recommended_medicines, focuses


def _try_fast_comparison_qa_response(
    user_message: str,
    recommended_medicines: list,
    *,
    qa_focuses: list[str] | None = None,
    conversation_history: list | None = None,
    user_attributes: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict | None:
    """2〜4製品比較は CSV メタ + ルールベースセクションで即応答（KB/重い JSON LLM を省略）。"""
    from src.utils.input_helpers import detect_correction_intent

    if detect_correction_intent(user_message):
        return None
    focuses = list(qa_focuses or [])
    if "comparison" not in focuses or len(recommended_medicines or []) < 2:
        return None
    from src.services.medicine_qa_comparison_quality import build_comparison_answer_scaffold

    answer = build_comparison_answer_scaffold(recommended_medicines, user_message)
    if not answer:
        return None
    if session_id:
        try:
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(session_id, "ask_qa")
            mark_processing_step(session_id, "medicine_qa", detail_code="answer_compose")
            mark_processing_step(session_id, "medicine_qa", detail_code="format_response")
        except Exception:
            pass
    return _build_structured_qa_from_stream(
        user_message,
        recommended_medicines,
        answer,
        qa_focuses=focuses,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
    )


def _try_fast_product_image_qa_response(
    user_message: str,
    recommended_medicines: list,
    *,
    qa_focuses: list[str] | None = None,
    conversation_history: list | None = None,
    user_attributes: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict | None:
    """製品画像 QA は LLM / KB 拡張を省略して即応答（SSE 暫定表示なし）。"""
    focuses = list(qa_focuses or [])
    if "product_image" not in focuses or not recommended_medicines:
        return None
    if session_id:
        try:
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(session_id, "ask_qa")
            mark_processing_step(session_id, "medicine_qa", detail_code="answer_compose")
            mark_processing_step(session_id, "medicine_qa", detail_code="format_response")
        except Exception:
            pass
    parsed = _build_structured_qa_from_stream(
        user_message,
        recommended_medicines,
        "",
        qa_focuses=focuses,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
    )
    return parsed


_HOME_INVENTORY_FOLLOWUP_RE = re.compile(
    r"家に|うちに|うちにも|"
    r"(?:家|うち).{0,12}持って|"
    r"持って.{0,12}(?:家|うち)|"
    r"あるわ|あるね|あるよ|あるん",
)
_S_VARIANT_FOLLOWUP_RE = re.compile(r"Sは|Sが|プレミアム|ついて|ついてい")


def _prefer_user_stated_medicines_for_interaction(
    user_message: str,
    recommended_medicines: list,
    *,
    conversation_history: list | None,
    session: Any = None,
    session_id: str | None = None,
) -> list:
    """併用・飲酒フォローアップではユーザー申告品目を bot 推奨より優先。"""
    if not conversation_history:
        return recommended_medicines or []
    try:
        from src.services.medicine_qa_routing import _has_interaction_intent
        from src.services.medicine_thread_context import (
            collect_active_medicine_products,
            resolve_session_recommended_medicines,
        )

        if not _has_interaction_intent(
            user_message,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return recommended_medicines or []
        active = collect_active_medicine_products(
            session,
            sid=session_id,
            messages=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if not any(p.get("source") == "history_user_entity" for p in active):
            return recommended_medicines or []
        resolved = resolve_session_recommended_medicines(
            session,
            sid=session_id,
            messages=conversation_history,
        )
        return resolved or recommended_medicines or []
    except Exception:
        logger.debug("prefer user-stated interaction meds skipped", exc_info=True)
        return recommended_medicines or []


def _try_fast_travel_import_qa_response(
    user_message: str,
    recommended_medicines: list | None,
    *,
    conversation_history: list | None = None,
) -> dict | None:
    """旅行・持ち込みの初回相談（推奨履歴なし）— reject テンプレを避ける。"""
    t = (user_message or "").strip()
    if not t:
        return None

    travel_context = False
    thread_followup = False
    try:
        from src.services.medicine_qa_routing import is_travel_import_context
        from src.services.reco_followup_signals import is_travel_thread_followup

        thread_followup = is_travel_thread_followup(
            t,
            conversation_history=conversation_history,
        )
        travel_context = is_travel_import_context(t) or thread_followup
    except ImportError:
        try:
            from src.services.medicine_qa_routing import is_travel_import_context

            travel_context = is_travel_import_context(t)
        except ImportError:
            return None
    if not travel_context:
        return None
    if recommended_medicines and not thread_followup:
        return None

    from src.dialogue.routing.context_signals import extract_drug_entities

    blob_all = t
    if conversation_history:
        blob_all += " " + " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-8:]
            if isinstance(m, dict)
        )

    drug_names = extract_drug_entities(t) or extract_drug_entities(blob_all)
    if not drug_names:
        m = re.search(
            r"ロキソニン|バファリン|カロナール|タイレノール|イブ|パブロン|"
            r"アドビル|セデス|PL|pl",
            blob_all,
            re.I,
        )
        drug_label = m.group(0) if m else "お持ちのお薬"
    else:
        drug_label = drug_names[0]

    dest = "海外"
    if "タイ" in blob_all:
        dest = "タイ"
    elif "韓国" in blob_all:
        dest = "韓国"

    if thread_followup:
        if re.search(r"診断書|処方箋|書類", t):
            answer = (
                f"{drug_label}のような市販薬を{dest}へ持ち込む場合、"
                "診断書や処方箋は必須ではないことが多いです。"
                "ただし処方薬に該当する場合や、入国審査で使用目的の説明を"
                "求められたときは、医師のメモや処方箋写しがあると安心です。"
                "市販薬でも元包装と成分表記ラベルは必ず残してください。"
            )
        elif re.search(r"量|どれくらい|何個|何錠|止められ|空港", t):
            answer = (
                f"{drug_label}を{dest}へ持ち込む目安として、"
                "旅行期間の個人使用分（おおむね1〜2箱・1〜2週間分程度）に"
                "収めるのが無難です。大量や業者のような量は別審査になりやすく、"
                "空港・税関で止められるリスクが上がります。"
                "不安なら元包装のまま、使用目的メモを英語または現地語で"
                "用意し、申告を求められたら正直に申告してください。"
            )
        else:
            answer = (
                f"{drug_label}を{dest}へ持ち込む際の一般的な注意点です。"
                "① 元の包装・成分表記ラベルを残す "
                "② 個人使用の量に収める（大量持ち込みは別審査になりやすい） "
                "③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 "
                "④ 入国カードや税関で申告が求められる場合がある "
                "⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。"
                "不安があれば出発前に登録販売者や航空会社にもご確認ください。"
            )
        doping = ""
    else:
        answer = (
            f"{drug_label}を{dest}へ持ち込む場合、入国規制・量・包装・成分表記は"
            "国・地域ごとに異なります。市販の解熱鎮痛薬は個人使用の範囲で持参される"
            "ことが多いですが、大量持ち込みや処方薬に該当する場合は別扱いになる"
            "ことがあります。成分表記のわかる包装、必要に応じて医師の診断書や"
            "処方箋の写しを用意し、税関・入国審査の最新情報は外務省や渡航先の"
            "公的機関、お近くの登録販売者でもご確認ください。"
        )
        doping = (
            f"{drug_label}は一般のスポーツ競技におけるドーピング禁止物質リスト上、"
            "典型的な市販品では大きな問題にならないことが多いです。"
            "ただし海外入国規制とは別問題です。"
        )
    empty = ""
    return {
        "answer": answer,
        "medicine_details": empty,
        "interactions": empty,
        "doping_check": doping,
        "side_effects": empty,
        "consultation_advice": "渡航先の最新規制は必ずご自身でご確認ください。",
    }


def _try_fast_thread_inventory_qa_response(
    user_message: str,
    recommended_medicines: list,
    *,
    conversation_history: list | None = None,
    session: Any = None,
    session_id: str | None = None,
) -> dict | None:
    """「家に/うちにも」「Sは〜」等 — スレッド維持の短い報告に定型拒否せず応答。"""
    t = (user_message or "").strip()
    try:
        from src.services.medicine_qa_routing import is_travel_import_context

        if is_travel_import_context(t):
            return None
    except Exception:
        pass
    is_home = bool(_HOME_INVENTORY_FOLLOWUP_RE.search(t))
    is_s_variant = bool(_S_VARIANT_FOLLOWUP_RE.search(t))
    if not t or not (is_home or is_s_variant):
        return None
    try:
        from src.services.medicine_thread_context import (
            collect_active_medicine_products,
            should_continue_medicine_thread,
        )

        if not should_continue_medicine_thread(
            t,
            session=session,
            sid=session_id,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
            client=None,
        ):
            return None
        active = collect_active_medicine_products(
            session,
            sid=session_id,
            messages=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        product = str(
            (active[0] if active else (recommended_medicines or [{}])[0]).get("product_name")
            or "お手元の市販薬"
        )
        if is_s_variant:
            answer = (
                f"「{product}」で S 表記の有無についてですね。"
                "市販ではロキソニンSやロキソニンSプレミアムが一般的です。"
                "お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。"
            )
        else:
            if re.search(r"うち|あるわ", t):
                answer = (
                    f"うちにも{product}があるんですね。"
                    "同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。"
                    "他に気になることがあれば、いつでも聞いてください。"
                )
            else:
                answer = (
                    f"おうちにも{product}があるのですね。"
                    "同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。"
                    "他に気になることがあれば、いつでも聞いてください。"
                )
        empty = ""
        return {
            "answer": answer,
            "medicine_details": empty,
            "interactions": empty,
            "doping_check": empty,
            "side_effects": empty,
            "consultation_advice": empty,
        }
    except Exception:
        logger.debug("fast thread inventory qa skipped", exc_info=True)
        return None


def _try_fast_interaction_followup_qa_response(
    user_message: str,
    recommended_medicines: list,
    *,
    qa_focuses: list[str] | None = None,
    conversation_history: list | None = None,
    session: Any = None,
    session_id: str | None = None,
) -> dict | None:
    """併用・「それと一緒に」フォロー — 文脈品目を明示し拒否テンプレを避ける。"""
    try:
        from src.services.medicine_qa_routing import _has_interaction_intent
        from src.services.medicine_thread_context import collect_active_medicine_products

        if not _has_interaction_intent(
            user_message,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return None
        active = collect_active_medicine_products(
            session,
            sid=session_id,
            messages=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if not active:
            return None
        product = str(active[0].get("product_name") or "").strip()
        if not product:
            return None
        um = user_message or ""
        alcohol_kw = ("お酒", "飲酒", "アルコール", "酒", "ビール", "wine", "beer")
        if any(k in um for k in alcohol_kw):
            answer = (
                f"「{product}」を飲酒後に使ってよいかは、成分によって注意が異なります。"
                "一般にアセトアミノフェン系はアルコール摂取後の服用で肝障害リスクが上がることがあり、"
                "NSAIDs系は胃への負担が増すことがあります。"
                "飲酒直後や大量飲酒後は自己判断を避え、お近くの登録販売者に成分名を伝えてご相談ください。"
            )
        else:
            answer = (
                f"「{product}」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。"
                "一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。"
                "不安がある場合は、お近くの登録販売者にご相談ください。"
            )
        empty = ""
        return {
            "answer": answer,
            "medicine_details": empty,
            "interactions": answer,
            "doping_check": empty,
            "side_effects": empty,
            "consultation_advice": empty,
        }
    except Exception:
        logger.debug("fast interaction followup qa skipped", exc_info=True)
        return None


def _build_structured_qa_from_stream(
    user_message: str,
    recommended_medicines: list,
    streamed_answer: str,
    *,
    qa_focuses: list[str] | None = None,
    conversation_history: list | None = None,
    user_attributes: dict[str, Any] | None = None,
) -> dict:
    """ストリーム済み回答と推奨医薬品メタから構造化 Q&A を組み立てる（重い JSON 生成 LLM を省略）。"""
    from src.services.medicine_qa_routing import build_focused_qa_sections

    answer = (streamed_answer or "").strip()
    sports_ctx = any(k in (user_message or "") for k in ("競技", "ドーピング", "陸上", "マラソン"))
    has_prohibited = any("あり" in str(m.get("doping_prohibited") or "") for m in recommended_medicines or [])
    if sports_ctx and has_prohibited and answer and "禁止" not in answer:
        answer += (
            " 推奨の内服風邪薬には競技で注意が必要な成分が含まれる場合があります。"
            "のどスプレー単剤など代替も検討し、登録販売者にご確認ください。"
        )

    focused = build_focused_qa_sections(
        user_message,
        recommended_medicines or [],
        conversation_history=conversation_history,
        user_attributes=user_attributes,
    )
    merged = {
        "answer": answer or "お近くの登録販売者にご相談ください。",
        **focused,
    }
    return _finalize_structured_qa_response(
        merged,
        user_message,
        recommended_medicines or [],
        qa_focuses=qa_focuses,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
        answer=answer,
    )


def _last_assistant_plain(conversation_history: list | None) -> str:
    from src.utils.sage_message_plain import resolve_bot_user_facing_text

    for msg in reversed(conversation_history or []):
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or msg.get("type") or "").lower()
        if role in ("assistant", "bot"):
            return resolve_bot_user_facing_text(msg)
    return ""


def _clarify_qa_response(user_message: str) -> dict[str, str]:
    msg = (user_message or "").strip()
    if re.search(r"飲み合わせ|併用|一緒に", msg):
        lead = "どのお薬同士の飲み合わせか教えていただけますか？"
    else:
        lead = "どのお薬についてのご質問か教えていただけますか？"
    answer = f"{lead}お薬名が分かれば、こちらで一般的な情報をお伝えします。"
    empty = ""
    return {
        "answer": answer,
        "medicine_details": empty,
        "interactions": empty,
        "doping_check": empty,
        "side_effects": empty,
        "consultation_advice": empty,
    }


def _should_clarify_instead_of_reject(
    user_message: str,
    recommended_medicines: list | None,
    *,
    session: Any = None,
    session_id: str | None = None,
    conversation_history: list | None = None,
) -> bool:
    """品目未特定・一般論 — 拒否テンプレより Clarify を優先。"""
    msg = (user_message or "").strip()
    if not msg:
        return False
    if recommended_medicines:
        return False
    try:
        from src.services.medicine_thread_context import collect_active_medicine_products

        active = collect_active_medicine_products(
            session,
            sid=session_id,
            messages=conversation_history,
        )
        if active:
            return False
    except Exception:
        pass
    if re.search(r"飲み合わせ|併用|一緒に|他の薬", msg):
        return True
    try:
        from src.services.concierge_intent import looks_like_conversational_request, _is_medicine_consultation

        if looks_like_conversational_request(msg) and not _is_medicine_consultation(msg):
            return True
    except Exception:
        pass
    try:
        from src.services.medicine_qa_routing import is_travel_import_context

        if is_travel_import_context(msg):
            return True
    except Exception:
        pass
    return False


def _maybe_regenerate_on_comparison_loop(
    parsed_result: dict[str, Any],
    *,
    user_message: str,
    recommended_medicines: list | None,
    conversation_history: list | None,
    user_attributes: dict | None,
    qa_focuses: list | None,
) -> dict[str, Any]:
    """直前 bot と answer が酷似する場合、焦点セクションを再生成。"""
    try:
        from src.services.e2e_turn_eval import text_similarity
        from src.services.medicine_qa_routing import build_focused_qa_sections, merge_focused_qa_sections

        prior = _last_assistant_plain(conversation_history)
        answer = str(parsed_result.get("answer") or "")
        if not prior or text_similarity(answer, prior) < 0.85:
            return parsed_result
        focused = build_focused_qa_sections(
            user_message,
            recommended_medicines or [],
            conversation_history=conversation_history,
            user_attributes=user_attributes or {},
        )
        merged = merge_focused_qa_sections(parsed_result, focused, qa_focuses or [])
        if str(merged.get("answer") or "") == answer and focused:
            hint = str(focused.get("answer") or focused.get("medicine_details") or "")[:400]
            if hint and hint != answer:
                merged["answer"] = hint
        return merged
    except Exception:
        logger.debug("comparison loop regen skipped", exc_info=True)
        return parsed_result


def chat_with_medicine_context(
    user_message,
    conversation_history,
    recommended_medicines,
    client=None,
    session_id=None,
    *,
    long_term_memory_block=None,
    session=None,
):
    """
    会話履歴と推奨医薬品の情報をChatGPTに渡して、医薬品に関する質問に回答する
    """
    if client is None:
        client = _default_openai_client

    # session_id から session を補完（ブランドピン永続化用）
    if session is None and session_id:
        try:
            from src.services.session_manager import get_session_from_db

            session = get_session_from_db(session_id)
        except Exception:
            session = None

    system_intro_keywords = [
        "あなたについて",
        "あなたは",
        "システムについて",
        "どんなシステム",
        "何ができる",
        "機能",
        "自己紹介",
        "自己紹介して",
        "自己紹介してください",
    ]
    is_system_intro = any(
        keyword in user_message for keyword in system_intro_keywords
    )
    if is_system_intro and not recommended_medicines:
        answer_text = (
            "🏥 医薬品推奨システムについて\n"
            "このシステムは、症状に基づいて適切な市販薬（OTC医薬品）を提示するサポートを行います。\n\n"
            "📋 主な機能\n"
            "・症状に基づく医薬品の推奨\n"
            "・効能や用法用量などの基本情報の提示\n"
            "・相互作用や副作用に関する注意喚起\n"
            "・競技者向けのドーピング観点の補足\n\n"
            "🔍 できること\n"
            "・「頭痛がする」「のどが痛い」などの症状で検索\n"
            "・医薬品名での検索や質問\n"
            "・推奨結果についての追加質問\n\n"
            "⚠️ ご注意\n"
            "本システムは参考情報の提供を目的としており、最終判断は登録販売者・薬剤師などの専門家にご相談ください。"
        )
        return {
            "answer": answer_text,
            "medicine_details": "",
            "interactions": "",
            "doping_check": "",
            "side_effects": "",
            "consultation_advice": "",
        }

    early_travel = _try_fast_travel_import_qa_response(
        user_message,
        recommended_medicines,
        conversation_history=conversation_history,
    )
    if early_travel is not None:
        return early_travel

    try:
        from src.services.medicine_qa_routing import is_travel_import_context

        travel_cold = is_travel_import_context(user_message) and not recommended_medicines
    except ImportError:
        travel_cold = False

    if not travel_cold:
        # 発話にブランド通称がある場合は、履歴推奨より先にブランド解決+セッションピンを適用
        # 比較 intent 時はセッション文脈の複数系統を上書きしない
        try:
            from src.dialogue.routing.context_signals import extract_drug_entities
            from src.services.medicine_qa_routing import _has_comparison_intent

            comparison_intent = _has_comparison_intent(
                user_message,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines,
            )
            if extract_drug_entities(user_message) and not comparison_intent:
                df_early = pd.read_csv(CSV_PATH)
                brand_hits = detect_medicine_name_in_query(
                    user_message, df_early, session=session
                )
                if brand_hits:
                    recommended_medicines = brand_hits[:5]
                    logger.info(
                        "Using brand-resolved (+session pin) medicines as Q&A context: %s",
                        [m.get("product_name") for m in recommended_medicines],
                    )
                    if session is not None and session_id:
                        try:
                            from src.services.session_manager import save_session_to_db

                            save_session_to_db(session_id, session)
                        except Exception:
                            logger.debug("qa_brand_pins persist skipped", exc_info=True)
        except Exception as e:
            logger.debug("early brand resolve skipped: %s", e)
    else:
        logger.info("Skipping brand pin for travel/import cold-start Q&A")

    recommended_medicines = _prefer_user_stated_medicines_for_interaction(
        user_message,
        recommended_medicines or [],
        conversation_history=conversation_history,
        session=session,
        session_id=session_id,
    )

    if not recommended_medicines and conversation_history:
        try:
            from src.services.medicine_thread_context import resolve_session_recommended_medicines

            restored = resolve_session_recommended_medicines(
                session,
                sid=session_id,
                messages=conversation_history,
            )
            if restored:
                recommended_medicines = restored
                logger.info(
                    "Restored %s medicine(s) from session context for Q&A/RAG",
                    len(recommended_medicines),
                )
        except Exception as e:
            logger.debug("session medicine context restore skipped: %s", e)
        if not recommended_medicines:
            try:
                for hist in reversed(conversation_history):
                    diag = hist.get("diagnosis") if isinstance(hist, dict) else None
                    if isinstance(diag, dict) and diag.get("recommended_medicines"):
                        recommended_medicines = diag.get(
                            "recommended_medicines", []
                        ) or []
                        if recommended_medicines:
                            print(
                                f"会話履歴から推奨医薬品を復元: {len(recommended_medicines)}件"
                            )
                            break
            except Exception as e:
                print(f"履歴復元エラー: {e}")
    # 推奨医薬品がない場合はルールベース推奨を優先（症状・競技条件などを考慮）
    if not recommended_medicines:
        from src.services.medicine_qa_routing import should_skip_recommendation_for_medicine_qa

        skip_rule_based = should_skip_recommendation_for_medicine_qa(user_message)
        if not skip_rule_based:
            try:
                from src.core.rule_based_recommendation import (
                    rule_based_medicine_recommendation,
                )

                logger.info(
                    "No recommended_medicines provided. "
                    "Running rule_based_medicine_recommendation in chat_with_medicine_context."
                )
                rule_based_result = rule_based_medicine_recommendation(
                    user_text=user_message,
                    user_info={},
                    client=client,
                    top_n=3,
                    session_id=session_id,
                )
                if rule_based_result:
                    rb_medicines = rule_based_result.get("recommended_medicines") or []
                    if rb_medicines:
                        recommended_medicines = rb_medicines
                        logger.info(
                            f"rule_based_medicine_recommendation returned "
                            f"{len(recommended_medicines)} medicines for Q&A context."
                        )
            except Exception as e:
                logger.error(
                    f"rule_based_medicine_recommendation error in chat_with_medicine_context: {e}"
                )
        else:
            logger.info(
                "Skipping rule_based_medicine_recommendation for explicit medicine Q&A: %s",
                user_message[:80],
            )
    # ルールベースで得られず、質問文に明示的な医薬品名がある場合は CSV から文脈を組み立て LLM へ
    if not recommended_medicines:
        try:
            df = pd.read_csv(CSV_PATH)
            detected_medicines = detect_medicine_name_in_query(
                user_message, df, session=session
            )
            if detected_medicines:
                recommended_medicines = detected_medicines[:5]
                logger.info(
                    "Using CSV-detected medicines as LLM Q&A context: %s hit(s)",
                    len(recommended_medicines),
                )
                if session is not None and session_id:
                    try:
                        from src.services.session_manager import save_session_to_db

                        save_session_to_db(session_id, session)
                    except Exception:
                        logger.debug("qa_brand_pins persist skipped", exc_info=True)
        except Exception as e:
            print(f"医薬品検索エラー: {e}")
    def _mark_qa(detail_code: str) -> None:
        if not session_id:
            return
        try:
            from src.services.processing_status import mark_processing_step

            mark_processing_step(session_id, "medicine_qa", detail_code=detail_code)
        except Exception:
            pass

    _mark_qa("history_read")
    history_text = ""
    if conversation_history is not None:
        from src.utils.sage_message_plain import resolve_bot_user_facing_text

        recent_messages = conversation_history[-5:]
        for msg in recent_messages:
            if msg.get("type") == "user":
                history_text += f"ユーザー: {msg.get('content', '')}\n"
            elif msg.get("type") == "bot":
                diagnosis = msg.get("diagnosis")
                if diagnosis is not None and diagnosis.get(
                    "recommended_medicines"
                ):
                    medicines = diagnosis.get("recommended_medicines", [])
                    history_text += f"AI: 推奨医薬品: {', '.join([m.get('product_name', '') for m in medicines])}\n"
                else:
                    plain = resolve_bot_user_facing_text(msg)
                    if plain:
                        history_text += f"AI: {plain}\n"
    _mark_qa("question_parse")
    medicines_text = ""
    if recommended_medicines:
        _mark_qa("context_load")
        for i, medicine in enumerate(recommended_medicines, 1):
            medicines_text += f"""
{i}つ目: {medicine.get('product_name', '')}
- メーカー: {medicine.get('manufacturer', '')}
- 効能効果: {medicine.get('efficacy', '')}
- 成分: {medicine.get('ingredients', '')}
- 使用上の注意: {medicine.get('usage_notes', '')}
- ドーピング禁止物質: {medicine.get('doping_prohibited', '')}
- 競技会区分: {medicine.get('competition_category', '')}
- ドーピング条件: {medicine.get('doping_conditions', '')}
"""
    memory_section = ""
    if long_term_memory_block:
        memory_section = f"\n{long_term_memory_block.strip()}\n"
    from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

    from src.dialogue.routing.context_signals import extract_drug_entities
    from src.services.medicine_qa_routing import (
        infer_medicine_qa_focuses,
        is_comparison_pick_question,
        _has_product_image_intent,
    )

    user_attributes: dict[str, Any] = {}
    if session_id:
        try:
            from src.services.session_manager import get_session_from_db

            sd = get_session_from_db(session_id) or {}
            user_attributes = sd.get("user_attributes") or {}
        except Exception:
            pass

    qa_focuses = infer_medicine_qa_focuses(
        user_message,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
        user_attributes=user_attributes,
        use_llm_enrichment=not _has_product_image_intent(user_message),
    )
    recommended_medicines, qa_focuses = _apply_user_correction_pivot(
        user_message,
        recommended_medicines or [],
        qa_focuses,
        session=session,
    )
    if "comparison" in qa_focuses and recommended_medicines:
        from src.services.medicine_qa_comparison_quality import expand_medicines_for_comparison

        recommended_medicines = expand_medicines_for_comparison(
            user_message,
            recommended_medicines,
            conversation_history=conversation_history,
            session=session,
        )
    fast_product_image = _try_fast_product_image_qa_response(
        user_message,
        recommended_medicines,
        qa_focuses=qa_focuses,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
        session_id=session_id,
    )
    if fast_product_image is not None:
        return fast_product_image

    fast_travel = _try_fast_travel_import_qa_response(
        user_message,
        recommended_medicines,
        conversation_history=conversation_history,
    )
    if fast_travel is not None:
        return fast_travel

    fast_inventory = _try_fast_thread_inventory_qa_response(
        user_message,
        recommended_medicines,
        conversation_history=conversation_history,
        session=session,
        session_id=session_id,
    )
    if fast_inventory is not None:
        return fast_inventory

    fast_interaction = _try_fast_interaction_followup_qa_response(
        user_message,
        recommended_medicines,
        qa_focuses=qa_focuses,
        conversation_history=conversation_history,
        session=session,
        session_id=session_id,
    )
    if fast_interaction is not None:
        return fast_interaction

    fast_comparison = _try_fast_comparison_qa_response(
        user_message,
        recommended_medicines,
        qa_focuses=qa_focuses,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
        session_id=session_id,
    )
    if fast_comparison is not None:
        prior = _last_assistant_plain(conversation_history)
        ans = str(fast_comparison.get("answer") or "")
        try:
            from src.services.e2e_turn_eval import text_similarity

            if prior and text_similarity(ans, prior) >= 0.85:
                fast_comparison = None
        except Exception:
            pass
    if fast_comparison is not None:
        return fast_comparison

    drug_entities = extract_drug_entities(user_message)
    comparison_hint = ""
    if len(drug_entities) >= 2:
        pinned_names = ", ".join(
            str(m.get("product_name") or "")
            for m in (recommended_medicines or [])
            if m.get("product_name")
        )
        pin_note = (
            f"\n- 本ターンで比較対象として確定した製品: {pinned_names}。"
            "会話中にユーザーが別製品を明示しない限り、この製品ラインを維持してください。"
            if pinned_names
            else ""
        )
        if is_comparison_pick_question(user_message) and len(drug_entities) == 2:
            comparison_hint = (
                "\n- 2製品の比較で「どちらが良い」系の質問です。"
                "条件別（胃に優しい/効き目/就寝前等）の選び方を示しつつ、"
                "個人差があるため断定せず登録販売者相談を促してください。"
                f"{pin_note}\n"
            )
        else:
            comparison_hint = (
                "\n- ユーザーは複数の医薬品について質問しています。"
                "比較・違い・選び方などの意図を読み取り、各製品の主成分・作用・用途の違いを"
                "質問に直接答える形で整理してください（羅列だけにしない）。"
                f"{pin_note}\n"
            )

    age_note = ""
    age_val = user_attributes.get("age")
    if age_val and "age" in qa_focuses:
        age_note = f"\n- ユーザー年齢（セッション）: {age_val}歳 — 年齢制限と照合して回答してください。\n"

    focus_note = f"\n- 検出された質問焦点: {', '.join(qa_focuses)}\n"
    focus_note += "- 質問に直接関係ない JSON フィールドは空文字 \"\" にしてください。\n"
    is_comparison = "comparison" in qa_focuses
    if is_comparison:
        comparison_hint += (
            "\n- 【比較質問】answer のみ記述してください。"
            "medicine_details / interactions / side_effects / consultation_advice は必ず空文字 \"\" にしてください"
            "（補足セクションはサーバー側で自動生成します）。\n"
            "- answer では各製品の主成分の違いに加え、"
            "効き目の強さ・胃への負担・使い分けの目安を2〜3文で簡潔に述べてください。\n"
            "- 併用注意・副作用の詳細・登録販売者への相談勧告は answer に書かないでください"
            "（補足セクションに任せます）。\n"
            "- 剤形がデータ上不明な場合は「確認できません」と書かず省略してください。\n"
        )
    prompt_body = f"""
あなたは医薬品推奨システムです。ユーザーの医薬品に関する質問に、推奨医薬品の情報を基に回答してください。
{memory_section}
【会話履歴（直近）】
{history_text}

【推奨医薬品の詳細情報】
{medicines_text}

【ユーザーの質問】
{user_message}

以下の点について回答してください：
1. 医薬品の詳細：各医薬品について「製品名・主成分」と、質問に関連する用途を2〜3文で簡潔に。効能の全文羅列は避ける。
2. 他の医薬品との飲み合わせ（相互作用）
3. スポーツ競技でのドーピング規制対象かどうか
4. 副作用や注意点
5. 医師に相談すべき場合
{comparison_hint}{age_note}{focus_note}
回答は以下の形式で構造化してください：
{{
    "answer": "ユーザーへの直接的な回答",
    "medicine_details": "医薬品ごとに2〜3文で簡潔に（製品名・主成分・質問に関係する用途のみ。効能の列挙はしない）",
    "interactions": "飲み合わせ・相互作用の説明",
    "doping_check": "ドーピング規制の確認結果",
    "side_effects": "副作用・注意点",
    "consultation_advice": "医師相談のアドバイス"
}}

注意：
- medicine_details では効能効果を箇条書きで羅列せず、質問に応じて「何に使えるか」を短くまとめてください。
- 推奨医薬品の情報を基に具体的に回答してください
- 質問に直接関係しない項目（interactions / doping_check / side_effects / consultation_advice / medicine_details）は空文字 "" にしてください。無関係な定型文は書かないでください。
- 比較質問では answer に成分差・効き目・胃負担・使い分けの要点のみ書き、詳細セクションは空にしてください。
- 飲み合わせについては、質問された場合のみ一般的な相互作用を説明してください
- ドーピングについては、競技・ドーピングの文脈がある場合のみ説明してください
- 安全性を最優先に考え、不明な点がある場合は医師相談を推奨してください
- 剤形がデータ上不明な場合は「確認できません」と書かず省略してください
- 質問の内容が推奨医薬品の情報では回答できない場合は、「お近くの登録販売者にご相談ください」と回答してください
"""
    from src.services.sse_emit import is_streaming_active

    stream_active = is_streaming_active(session_id)
    if stream_active:
        prompt = prompt_body
    else:
        prompt = augment_medicine_prompt_with_kb(
            user_message,
            prompt_body,
            recommended_medicines=recommended_medicines,
            conversation_history=conversation_history,
            qa_focuses=qa_focuses,
        )
    try:
        from src.core.llm_client import chat_completion_create, chat_completion_stream
        from src.services.sse_emit import (
            emit_qa_delta,
            emit_qa_sections_from_response,
        )

        system_msg = (
            "あなたは医薬品推奨システムです。医薬品の安全性と効果について正確な情報を提供してください。"
            "医薬品の詳細（medicine_details）は、効能の全文羅列ではなく、製品名・主成分・質問に関係する用途を2〜3文で簡潔に書いてください。"
            "推奨医薬品の情報で回答できない質問については、お近くの登録販売者にご相談するよう推奨してください。"
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        _mark_qa("interaction_check")
        _mark_qa("doping_check")
        _mark_qa("side_effect_check")
        streamed_answer = ""
        if stream_active and session_id:
            try:
                from src.services.processing_status import set_processing_flow

                set_processing_flow(session_id, "ask_qa")
            except Exception:
                pass

            _mark_qa("answer_compose")
            answer_prompt = f"""
【会話履歴】
{history_text}

【推奨医薬品】
{medicines_text}

【質問】
{user_message}

上記を踏まえ、ユーザーへの直接的な回答のみを200字以内で自然な日本語で書いてください。JSONや見出しは不要です。
"""
            if "comparison" in qa_focuses:
                answer_prompt += (
                    "\n【比較質問】主成分の違いに加え、"
                    "効き目の強さ・胃への負担・使い分けの目安を簡潔に述べてください。"
                    "併用注意・副作用の詳細・登録販売者への相談勧告は書かないでください"
                    "（補足セクションに自動表示されます）。"
                    "剤形が不明な場合は触れないでください。\n"
                )
            if "product_image" in qa_focuses:
                answer_prompt += (
                    "\n【重要】パッケージ画像は回答の下に別セクションで表示されます。"
                    "回答文はサーバー側で自動生成するため、ここでは空文字でも構いません。"
                    "「画像を見せられない」「この画面では表示できない」等とは書かないでください。"
                    "画像が未整備の場合は「まだ準備できていません」と表現してください。\n"
                )
            answer_prompt = augment_medicine_prompt_with_kb(
                user_message,
                answer_prompt,
                recommended_medicines=recommended_medicines,
                conversation_history=conversation_history,
                qa_focuses=qa_focuses,
            )
            streamed_answer = chat_completion_stream(
                client,
                model_role="explain",
                path="medicine_response_builder.chat_context.answer_stream",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": answer_prompt},
                ],
                on_delta=lambda c: emit_qa_delta(c, session_id, section="answer"),
                session_id=session_id,
                temperature=0.3,
                max_tokens=400,
            ).strip()

        if stream_active and session_id and streamed_answer:
            _mark_qa("format_response")
            parsed = _build_structured_qa_from_stream(
                user_message,
                recommended_medicines,
                streamed_answer,
                qa_focuses=qa_focuses,
                conversation_history=conversation_history,
                user_attributes=user_attributes,
            )
            emit_qa_sections_from_response(parsed, session_id)
            _append_physical_handoff_hint(parsed, user_message)
            return parsed

        _mark_qa("answer_draft")
        response = chat_completion_create(
            client,
            model_role="explain",
            path="medicine_response_builder.chat_context",
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )
        from src.core.llm_client import extract_completion_text

        result = extract_completion_text(response)
        print(f"ChatGPT応答: {result}")
        try:
            json_start = result.find("{") if result else -1
            json_end = result.rfind("}") + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                answer = parsed_result.get("answer", "")
                if any(
                    keyword in answer.lower()
                    for keyword in [
                        "分からない",
                        "不明",
                        "確認できません",
                        "情報がありません",
                        "回答できません",
                    ]
                ):
                    if _should_clarify_instead_of_reject(
                        user_message,
                        recommended_medicines,
                        session=session,
                        session_id=session_id,
                        conversation_history=conversation_history,
                    ):
                        return _clarify_qa_response(user_message)
                    try:
                        from src.services.medicine_qa_routing import (
                            should_prioritize_physical_for_symptom,
                        )

                        if should_prioritize_physical_for_symptom(
                            user_message,
                            conversation_history=conversation_history,
                            recommended_medicines=recommended_medicines,
                        ):
                            return _clarify_qa_response(
                                "症状の変化について承知しました。"
                                "咳の状態に合わせた市販薬を改めてご案内しますので、"
                                "痰の有無など分かる範囲で教えてください。"
                            )
                    except ImportError:
                        pass
                    return {
                        "answer": "申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。",
                        "medicine_details": "推奨医薬品の情報では回答できません",
                        "interactions": "推奨医薬品の情報では回答できません",
                        "doping_check": "推奨医薬品の情報では回答できません",
                        "side_effects": "推奨医薬品の情報では回答できません",
                        "consultation_advice": "お近くの登録販売者にご相談ください",
                    }
                if stream_active and session_id and streamed_answer:
                    parsed_result["answer"] = streamed_answer
                from src.services.medicine_qa_routing import (
                    build_focused_qa_sections,
                    merge_focused_qa_sections,
                )

                focused = build_focused_qa_sections(
                    user_message,
                    recommended_medicines or [],
                    conversation_history=conversation_history,
                    user_attributes=user_attributes,
                )
                parsed_result = merge_focused_qa_sections(
                    parsed_result,
                    focused,
                    qa_focuses,
                )
                parsed_result = _finalize_structured_qa_response(
                    parsed_result,
                    user_message,
                    recommended_medicines or [],
                    qa_focuses=qa_focuses,
                    conversation_history=conversation_history,
                    user_attributes=user_attributes,
                    answer=str(parsed_result.get("answer") or streamed_answer or ""),
                )
                parsed_result = _maybe_regenerate_on_comparison_loop(
                    parsed_result,
                    user_message=user_message,
                    recommended_medicines=recommended_medicines,
                    conversation_history=conversation_history,
                    user_attributes=user_attributes,
                    qa_focuses=qa_focuses,
                )
                if stream_active and session_id:
                    emit_qa_sections_from_response(parsed_result, session_id)
                _append_physical_handoff_hint(parsed_result, user_message)
                return parsed_result
            else:
                fallback = {
                    "answer": result,
                    "medicine_details": "詳細情報を取得できませんでした",
                    "interactions": "飲み合わせ情報を取得できませんでした",
                    "doping_check": "ドーピング規制の確認ができませんでした",
                    "side_effects": "副作用情報を取得できませんでした",
                    "consultation_advice": "お近くの登録販売者にご相談ください",
                }
                if stream_active and session_id:
                    if streamed_answer:
                        fallback["answer"] = streamed_answer
                    emit_qa_sections_from_response(fallback, session_id)
                return _sanitize_qa_result(fallback)
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return _sanitize_qa_result({
                "answer": result,
                "medicine_details": "詳細情報を取得できませんでした",
                "interactions": "飲み合わせ情報を取得できませんでした",
                "doping_check": "ドーピング規制の確認ができませんでした",
                "side_effects": "副作用情報を取得できませんでした",
                "consultation_advice": "お近くの登録販売者にご相談ください",
            })
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        return {
            "answer": "申し訳ございません。システムエラーが発生しました。お近くの登録販売者にご相談ください。",
            "medicine_details": "詳細情報を取得できませんでした",
            "interactions": "飲み合わせ情報を取得できませんでした",
            "doping_check": "ドーピング規制の確認ができませんでした",
            "side_effects": "副作用情報を取得できませんでした",
            "consultation_advice": "お近くの登録販売者にご相談ください",
        }
