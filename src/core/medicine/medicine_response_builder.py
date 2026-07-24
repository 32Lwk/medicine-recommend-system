"""
医薬品詳細・チャット文脈の組み立て

get_medicine_details, detect_medicine_name_in_query, chat_with_medicine_context を提供。
"""

import json
import logging

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


def detect_medicine_name_in_query(user_message, medicine_df):
    """
    ユーザーの質問から医薬品名を検出する
    """
    if medicine_df is None or medicine_df.empty:
        return []
    detected_medicines = []
    user_message_lower = user_message.lower()
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
    unique_medicines = []
    seen_names = set()
    for med in detected_medicines:
        if med["product_name"] not in seen_names:
            unique_medicines.append(med)
            seen_names.add(med["product_name"])
    return unique_medicines[:10]


def _short_medicine_use_hint(med: dict, user_message: str) -> str:
    """競技・ドーピング文脈では効能全文の羅列を避け、用途を短くまとめる。"""
    name = str(med.get("product_name") or "")
    sports_ctx = any(
        k in (user_message or "")
        for k in ("競技", "ドーピング", "陸上", "マラソン", "大会", "レース", "試合")
    )
    if sports_ctx:
        med_type = str(med.get("medicine_type") or "")
        if "外用" in med_type or "スプレ" in name or "のど" in name:
            return "のどの炎症・痛み向けの外用薬です。"
        return "感冒症状の緩和向けの総合感冒薬です。"
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


def _build_structured_qa_from_stream(
    user_message: str,
    recommended_medicines: list,
    streamed_answer: str,
) -> dict:
    """ストリーム済み回答と推奨医薬品メタから構造化 Q&A を組み立てる（重い JSON 生成 LLM を省略）。"""
    md_parts: list[str] = []
    doping_parts: list[str] = []
    has_prohibited = False
    for i, med in enumerate(recommended_medicines or [], 1):
        name = med.get("product_name") or f"{i}つ目"
        ingredients = (med.get("ingredients") or "").replace("\n", "、")[:120]
        use_hint = _short_medicine_use_hint(med, user_message)
        md_parts.append(
            f"**{name}**：主成分は{ingredients}など。{use_hint}"
        )
        dop = str(med.get("doping_prohibited") or "")
        cat = str(med.get("competition_category") or "")
        if "あり" in dop:
            has_prohibited = True
            doping_parts.append(
                f"**{name}**：禁止物質あり（{cat or '競技会区分要確認'}）。"
                "競技前の使用は登録販売者・大会主催者にご確認ください。"
            )
        else:
            doping_parts.append(
                f"**{name}**：リスト記載の禁止物質なし。"
                "外用薬は主に局所作用ですが、大会規定は要確認です。"
            )

    answer = (streamed_answer or "").strip()
    sports_ctx = any(k in (user_message or "") for k in ("競技", "ドーピング", "陸上", "マラソン"))
    if sports_ctx and has_prohibited and answer and "禁止" not in answer:
        answer += (
            " 推奨の内服風邪薬には競技で注意が必要な成分が含まれる場合があります。"
            "のどスプレー単剤など代替も検討し、登録販売者にご確認ください。"
        )

    return _sanitize_qa_result({
        "answer": answer or "お近くの登録販売者にご相談ください。",
        "medicine_details": "".join(md_parts) if md_parts else "詳細は登録販売者にご確認ください。",
        "interactions": (
            "風邪薬を複数同時に内服しないでください。"
            "アセトアミノフェン・抗ヒスタミン薬・交感神経興奮成分などの重複に注意し、併用は登録販売者にご相談ください。"
        ),
        "doping_check": "".join(doping_parts) if doping_parts else "ドーピング情報を確認してください。",
        "side_effects": (
            "眠気・口渇・胃腸障害などが出ることがあります。"
            "症状が強い場合や長引く場合は医師の受診を検討してください。"
        ),
        "consultation_advice": (
            "持病・妊娠・授乳・他の薬の服用がある場合、競技前の使用については登録販売者または医師にご相談ください。"
        ),
    })


def chat_with_medicine_context(
    user_message,
    conversation_history,
    recommended_medicines,
    client=None,
    session_id=None,
    *,
    long_term_memory_block=None,
):
    """
    会話履歴と推奨医薬品の情報をChatGPTに渡して、医薬品に関する質問に回答する
    """
    if client is None:
        client = _default_openai_client
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
    if not recommended_medicines and conversation_history:
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
    # ルールベースで得られず、質問文に明示的な医薬品名がある場合のみCSV検索
    if not recommended_medicines:
        try:
            df = pd.read_csv(CSV_PATH)
            detected_medicines = detect_medicine_name_in_query(
                user_message, df
            )
            if detected_medicines:
                logger.info(
                    "Returning CSV medicine lookup for explicit product names: "
                    f"{len(detected_medicines)} hit(s)"
                )
                medicine_info = ""
                for i, med in enumerate(detected_medicines[:3], 1):
                    medicine_info += f"\n💊 **{i}つ目: {med['product_name']}** ({med['manufacturer']})\n"
                    medicine_info += f"**効能効果:** {med['efficacy']}\n"
                    medicine_info += f"**成分:** {med['ingredients']}\n"
                    if med["age_restriction"]:
                        medicine_info += f"**年齢制限:** {med['age_restriction']}\n"
                    if med["usage"]:
                        medicine_info += f"**用法用量:** {med['usage']}\n"
                    medicine_info += "\n"
                return {
                    "answer": f"🔍 **医薬品検索結果**\n\n{medicine_info}\n⚠️ **ご注意**\n・医薬品の使用前には必ず登録販売者や薬剤師にご相談ください\n・アレルギー体質の方は成分を確認してください\n・用法用量を守ってご使用ください",
                    "medicine_details": "検出された医薬品の情報",
                    "interactions": "医薬品の相互作用については登録販売者にご相談ください",
                    "doping_check": "ドーピング検査については各競技団体にご確認ください",
                    "side_effects": "副作用については登録販売者にご相談ください",
                    "consultation_advice": "お近くの登録販売者にご相談ください",
                }
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
                    history_text += f"AI: {msg.get('content', '')}\n"
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
1. 医薬品の詳細：各医薬品について「製品名・主成分・剤形」と、質問に関連する用途を2〜3文で簡潔に。効能の全文羅列は避ける。
2. 他の医薬品との飲み合わせ（相互作用）
3. スポーツ競技でのドーピング規制対象かどうか
4. 副作用や注意点
5. 医師に相談すべき場合

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
- 飲み合わせについては、一般的な相互作用を説明してください
- ドーピングについては、WADA（世界アンチ・ドーピング機関）の規制を参考にしてください
- 安全性を最優先に考え、不明な点がある場合は医師相談を推奨してください
- 質問の内容が推奨医薬品の情報では回答できない場合は、「お近くの登録販売者にご相談ください」と回答してください
"""
    prompt = augment_medicine_prompt_with_kb(
        user_message,
        prompt_body,
        recommended_medicines=recommended_medicines,
    )
    try:
        from src.core.llm_client import chat_completion_create, chat_completion_stream
        from src.services.sse_emit import (
            emit_qa_delta,
            emit_qa_sections_from_response,
            is_streaming_active,
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
        stream_active = is_streaming_active(session_id)
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
            answer_prompt = augment_medicine_prompt_with_kb(
                user_message,
                answer_prompt,
                recommended_medicines=recommended_medicines,
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
                user_message, recommended_medicines, streamed_answer
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
                    emit_qa_sections_from_response(parsed_result, session_id)
                elif stream_active and session_id:
                    emit_qa_sections_from_response(parsed_result, session_id)
                _append_physical_handoff_hint(parsed_result, user_message)
                return _sanitize_qa_result(parsed_result)
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
