"""
推奨理由・使用上の注意の説明生成

rule_based_recommendation から分離（SRP改善）
"""

import json
import logging
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from openai import OpenAI

from src.core.recommendation_constants import IRRITANT_LAXATIVE_INGREDIENTS
from src.services.text_formatter import convert_markdown_bold

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# 使用上の注意生成のキャッシュ（generate_usage_notes 用）
_usage_notes_cache = {}

# バッチ使用上の注意のキャッシュ（generate_usage_notes_and_consultation_with_gpt 用）
# キー: 医薬品セット + リスク関連ユーザー属性 + 症状。個別因子はキーに含めるため
# 誤って個別化を欠いた応答を返さない（"個別因子絡みは都度生成"）。
_batch_notes_cache: dict[str, tuple[float, Dict]] = {}
_BATCH_NOTES_TTL_SEC = 24 * 3600
_BATCH_NOTES_MAX = 200


def _apply_age_policy_to_usage_result(
    result: Dict,
    recommended_medicines: List[Dict],
    user_info: Dict | None,
) -> Dict:
    """P1-6: GPT 生成 usage_notes へ年齢未確認警告を前置。"""
    try:
        from config.llm_flags import is_reco_age_policy_v2_enabled
        from src.core.recommendation.age_policy import (
            build_age_unknown_notice,
            prepend_age_notice_to_usage_notes,
        )

        if not is_reco_age_policy_v2_enabled() or (user_info or {}).get("age") is not None:
            return result
        notice = build_age_unknown_notice(recommended_medicines)
        if not notice:
            return result
        result = dict(result)
        result["usage_notes"] = prepend_age_notice_to_usage_notes(
            result.get("usage_notes") or "",
            notice,
        )
    except ImportError:
        pass
    return result


def _sports_context_instruction(user_text: str = "") -> str:
    try:
        from config.llm_flags import is_reco_sports_doping_filter_enabled
        from src.services.medicine_discovery_routing import has_sports_medicine_context

        if is_reco_sports_doping_filter_enabled() and has_sports_medicine_context(user_text or ""):
            return (
                "\n【競技文脈】ユーザーは競技・大会前後の使用可否に関心があります。"
                "ドーピング規定への配慮と、競技前後の使用上の注意を必ず含めてください。\n"
            )
    except ImportError:
        pass
    return ""


def _batch_notes_cache_key(
    recommended_medicines: List[Dict],
    nlu_result: Dict | None,
    user_info: Dict | None,
) -> str:
    ui = user_info or {}
    names = sorted(str(m.get("product_name", "") or m.get("name", "")) for m in recommended_medicines)
    risk_keys = {
        k: ui.get(k)
        for k in (
            "age", "pregnant", "breastfeeding", "allergies",
            "current_medications", "treatment_mention", "user_body_part",
        )
    }
    symptoms = sorted(_symptom_names((nlu_result or {}).get("symptoms")))
    return json.dumps(
        {"m": names, "u": risk_keys, "s": symptoms},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

# 発熱・高リスク症状の語彙（説明生成のリスク判定用）
_HIGH_RISK_SYMPTOM_TOKENS = ("発熱", "高熱", "熱", "インフル")


def _symptom_names(symptoms) -> List[str]:
    out: List[str] = []
    for s in symptoms or []:
        if isinstance(s, dict):
            name = s.get("name")
            if name:
                out.append(str(name))
        elif s:
            out.append(str(s))
    return out


def assess_explanation_risk(
    user_info: Dict | None,
    nlu_result: Dict | None = None,
    medicines: List[Dict] | None = None,
    symptoms=None,
) -> bool:
    """説明生成を上位モデルで行うべき「高リスク」かを判定する（Phase 1 sub3）。

    高リスク: 小児/高齢/妊娠授乳/持病・治療中/併用薬/アレルギー/発熱・インフル文脈、
    もしくは推奨薬にリスク成分・ドーピング・低スコア警告がある場合。
    低リスク: 上記に該当しない一般的な単一症状。
    """
    ui = user_info or {}
    age = ui.get("age")
    try:
        if age is not None and (int(age) < 15 or int(age) >= 65):
            return True
    except (TypeError, ValueError):
        pass
    if ui.get("pregnant") or ui.get("breastfeeding"):
        return True
    if ui.get("treatment_mention"):
        return True
    meds = ui.get("current_medications")
    if meds and meds not in (["なし"], []):
        return True
    allergies = ui.get("allergies")
    if allergies and allergies not in (["なし"], []):
        return True

    names = _symptom_names(symptoms)
    if nlu_result:
        names += _symptom_names(nlu_result.get("symptoms"))
    if any(tok in name for name in names for tok in _HIGH_RISK_SYMPTOM_TOKENS):
        return True

    for m in medicines or []:
        if not isinstance(m, dict):
            continue
        if m.get("risk_warning") or m.get("risk_ingredient") or m.get("low_score_warning"):
            return True
        if str(m.get("doping_prohibited", "")).strip() == "禁止物質あり":
            return True
    return False


def generate_usage_notes(medicine_name: str, medicine_info: dict, user_info: dict = None, symptoms: list = None) -> str:
    """
    ChatGPTを使用して医薬品の使用上の注意を自動生成（キャッシュ機能付き）

    Args:
        medicine_name: 医薬品名
        medicine_info: 医薬品情報（成分、効能、年齢制限など）
        user_info: ユーザー情報（年齢、妊娠状態など）
        symptoms: ユーザーの症状情報（リスト形式、例：['眠気', '不眠']）

    Returns:
        str: 生成された使用上の注意
    """
    try:
        from src.core.medicine_logic import client
        if client is None:
            return "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。"

        # カフェイン含有の確認（キャッシュキーにも含める）
        ingredients_str = str(medicine_info.get('ingredients', '')).lower()
        efficacy_str = str(medicine_info.get('efficacy', '')).lower()
        contains_caffeine = any(keyword in ingredients_str or keyword in efficacy_str
                               for keyword in ['カフェイン', 'caffeine', '眠気', '眠気の除去', '眠気・倦怠感の除去'])

        # キャッシュキーの生成
        symptoms_str = ','.join(sorted(symptoms)) if symptoms else ''
        cache_key = f"{medicine_name}_{hash(str(user_info))}_{contains_caffeine}_{symptoms_str}"

        if cache_key in _usage_notes_cache:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"📋 使用上の注意をキャッシュから取得: {medicine_name}")
            return _usage_notes_cache[cache_key]

        user_context = ""
        if user_info:
            if user_info.get('age'):
                user_context += f"年齢: {user_info['age']}歳\n"
            if user_info.get('pregnant'):
                user_context += "妊娠中\n"
            if user_info.get('breastfeeding'):
                user_context += "授乳中\n"
            if user_info.get('allergies'):
                user_context += f"アレルギー: {', '.join(user_info['allergies'])}\n"

        doping_info = ""
        if medicine_info.get('doping_prohibited') == '禁止物質あり':
            doping_info = f"""
ドーピング禁止物質情報:
- 禁止物質あり: {medicine_info.get('doping_prohibited', 'なし')}
- 競技会区分: {medicine_info.get('competition_category', '情報なし')}
- 条件: {medicine_info.get('conditions', '情報なし')}
"""

        caffeine_note = ""
        if contains_caffeine:
            caffeine_note = """
【カフェイン剤に関する重要な注意事項】
- 添付文書に記載された服用期間や用法・用量を守り、短期間の服用にとどめるようにしてください
- 1日の摂取量を守ること（過剰摂取は避ける）
- カフェインを多く含む飲料と併用した場合には、カフェインの過量摂取となり、重大な健康被害につながるおそれがあります。そのため、コーヒーやお茶、エナジードリンクなどのカフェイン含有飲料と同時に服用しないでください
- 就寝前の使用は避ける（不眠の原因になる可能性がある）
- 常用化のリスクがあるため、一時的な使用に留める
- 慢性的な眠気の場合は医師にご相談ください

【服用してはいけない方】
- 胃酸過多の症状がある方、胃潰瘍と診断された方（カフェインは胃を刺激して胃酸の分泌をうながす働きがあり、胃を荒らすおそれがあるため）
- 心臓病と診断された方（カフェインは中枢神経に作用して眠気を除去するとともに、心臓の収縮や脈拍数を増やし、心臓に負担をかけて症状を悪化させる可能性があるため）

【悪影響のない1日あたりのカフェイン最大摂取量目安】
- 健康な成人：400mg（コーヒーマグカップ3杯分）
- 妊娠中の方：200〜300mg/日（コーヒーマグカップ2杯分）
- 授乳中の方：200mg/日

【15歳未満の小児について】
市販薬としては販売されていないため、薬以外の眠気を覚ます方法を試すか、生活リズムを整えたり、睡眠を見直してみることをおすすめします。

"""

        caffeine_instruction = ""
        if contains_caffeine:
            caffeine_instruction = """カフェイン剤の場合、以下の内容を必ず含めてください：
- 添付文書に記載された服用期間や用法・用量を守り、短期間の服用にとどめる
- 1日の摂取量上限（健康な成人400mg、妊娠中200-300mg/日、授乳中200mg/日）
- カフェイン含有飲料（コーヒー、お茶、エナジードリンクなど）との併用禁止
- 就寝前の使用を避けること
- 胃酸過多・胃潰瘍、心臓病の方は服用不可
- 15歳未満の小児は市販薬として販売されていない

【重要な注意事項】
- カフェイン剤は眠気覚ましの薬であり、不眠症向けの睡眠改善薬ではありません
- 「睡眠改善薬」や「不眠症」に関する注意事項は含めないでください
- 緑内障や前立腺肥大の禁忌事項は含めないでください（カフェイン剤には一般的に該当しません）
- 「使ってはいけない人」には、胃酸過多・胃潰瘍、心臓病の方のみを含めてください
"""

        caffeine_item = '9. カフェイン剤としての注意事項（1日の摂取量、使用期間、就寝前の使用について）' if contains_caffeine else ''
        system_message = "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"
        if contains_caffeine:
            system_message += " カフェイン剤（眠気覚まし）の場合、不眠症向けの睡眠改善薬に関する注意事項（例：「睡眠改善薬は一時的な不眠にのみ効果があります」「不眠症と診断されている場合は医師にご相談ください」など）は含めないでください。また、緑内障や前立腺肥大の禁忌事項も含めないでください。"

        symptoms_context = ""
        if symptoms:
            symptoms_list = [s.get('name', s) if isinstance(s, dict) else s for s in symptoms]
            symptoms_context = f"ユーザーの症状: {', '.join(symptoms_list)}\n"

        prompt = f"""
以下の医薬品について、使用上の注意を生成してください。

医薬品名: {medicine_name}
成分: {medicine_info.get('ingredients', '情報なし')}
効能・効果: {medicine_info.get('efficacy', '情報なし')}
年齢制限: {medicine_info.get('age_restriction', '情報なし')}
用法・用量: {medicine_info.get('usage', '情報なし')}
{doping_info}
{caffeine_note}

ユーザー情報:
{user_context if user_context else '情報なし'}
{symptoms_context}

以下の形式で使用上の注意を生成してください：
1. 基本的な使用上の注意
2. 年齢・性別による注意点（年齢制限の詳細を含む）
3. 妊娠・授乳中の注意点
4. アレルギーに関する注意点
5. 副作用について
6. 他の薬との相互作用
7. 保存方法・保管上の注意
8. ドーピング禁止物質に関する注意（該当する場合）
{f'{caffeine_item}' if contains_caffeine else ''}

各項目は簡潔で分かりやすく、実際の使用場面で役立つ内容にしてください。
特に年齢制限とドーピング禁止物質については、具体的で明確な注意事項を含めてください。
{symptoms_context and f'ユーザーの症状（{symptoms_context.split(":")[1].strip()}）に合わせた注意事項を含めてください。' or ''}
{caffeine_instruction}
"""

        from src.core.llm_client import chat_completion_create
        from config.llm_config import get_explain_model

        fast_model = get_explain_model(
            assess_explanation_risk(user_info, medicines=[medicine_info], symptoms=symptoms)
        )
        response = chat_completion_create(
            client,
            model_role="explain",
            path="explanation_generator.usage_notes",
            model=fast_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.7,
        )

        usage_notes = response.choices[0].message.content.strip()
        usage_notes = convert_markdown_bold(usage_notes)

        from src.core.recommendation.pollen_rhinitis_scoring import (
            append_vasoconstrictor_nasal_warning,
            mark_vasoconstrictor_flag,
        )

        mark_vasoconstrictor_flag(medicine_info)
        usage_notes = append_vasoconstrictor_nasal_warning(usage_notes, medicine_info)

        if len(_usage_notes_cache) < 100:
            _usage_notes_cache[cache_key] = usage_notes
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"💾 使用上の注意をキャッシュに保存: {medicine_name}")

        return usage_notes

    except Exception as e:
        logger.error(f"使用上の注意生成エラー: {e}")
        return "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。"


def _kb_citation_for_explanation(
    candidate: Dict,
    nlu_result: Dict,
    user_info: Dict,
) -> str:
    """方式 A: retrieve 結果から citation 1–2 文を返す（LLM 追加呼び出しなし）。"""
    from src.services.bedrock_kb_retrieve import retrieve_medicine_context

    user_text = str(
        (user_info or {}).get("user_text")
        or (user_info or {}).get("user_message")
        or ""
    ).strip()
    query_parts = [user_text] if user_text else []
    product = str(candidate.get("product_name") or "").strip()
    if product:
        query_parts.append(product)
    query = " ".join(query_parts).strip() or product
    if not query:
        return ""

    result = retrieve_medicine_context(
        query,
        recommended_medicines=[candidate],
        nlu_result=nlu_result,
        use_cache=True,
    )
    chunks = result.get("chunks") or []
    if not chunks:
        return ""
    snippet = chunks[0][:200].strip().replace("\n", " ")
    uris = result.get("source_uris") or []
    cite = f"KB参照: {snippet}"
    if uris:
        cite += f"（{uris[0].split('/')[-1]}）"
    return cite


def generate_explanation(candidate: Dict, nlu_result: Dict, safety_result: Dict, user_info: Dict) -> str:
    """
    推奨理由の説明を生成（スコア内訳に基づく詳細版）
    """
    explanation_parts = []

    score_breakdown = candidate.get('score_breakdown', {})

    symptom_match = score_breakdown.get('symptom_match', 0)
    if symptom_match > 0.8:
        matched_symptoms = []
        efficacy_text = candidate.get('efficacy', '')
        for symptom in nlu_result.get("symptoms", []):
            symptom_name = symptom.get("name")
            if symptom_name and symptom_name in efficacy_text:
                matched_symptoms.append(symptom_name)

        if matched_symptoms:
            explanation_parts.append(f"✅ 症状に非常によく適合: {', '.join(matched_symptoms)}に特化した効果")
        else:
            explanation_parts.append("✅ 症状に非常によく適合")
    elif symptom_match > 0.6:
        explanation_parts.append("✅ 症状に適度に適合")
    else:
        explanation_parts.append("⚠️ 症状への適合度は中程度")

    efficacy_specificity = score_breakdown.get('efficacy_specificity', 0)
    if efficacy_specificity > 0.7:
        explanation_parts.append("✅ 効能が症状に特化")
    elif efficacy_specificity > 0.5:
        explanation_parts.append("✅ 効能が適度に特化")

    side_effect_risk = score_breakdown.get('side_effect_risk', 0)
    if side_effect_risk < -0.3:
        explanation_parts.append("⚠️ 副作用リスクがやや高め")
    elif side_effect_risk < -0.1:
        explanation_parts.append("⚠️ 軽度の副作用リスク")
    else:
        explanation_parts.append("✅ 副作用リスクは低め")

    interaction_risk = score_breakdown.get('interaction_risk', 0)
    if interaction_risk < -0.2:
        explanation_parts.append("⚠️ 薬物相互作用の可能性")
    elif interaction_risk < -0.1:
        explanation_parts.append("⚠️ 軽度の相互作用リスク")
    else:
        explanation_parts.append("✅ 相互作用リスクは低め")

    age_fit = score_breakdown.get('age_fit', 0)
    if age_fit > 0.8:
        explanation_parts.append("✅ 年齢制限に適合")
    elif age_fit < 0.5:
        age_restriction = candidate.get('age_restriction', '')
        if age_restriction:
            explanation_parts.append(f"⚠️ 年齢制限: {age_restriction}")

    usage_convenience = score_breakdown.get('usage_convenience', 0)
    if usage_convenience > 0.7:
        explanation_parts.append("✅ 服用が簡便")
    elif usage_convenience < 0.3:
        explanation_parts.append("⚠️ 服用回数が多い")

    ingredients = candidate.get('ingredients', '')
    if ingredients:
        ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()][:3]
        if ingredient_list:
            explanation_parts.append(f"主成分: {', '.join(ingredient_list)}")

    medicine_type = candidate.get('medicine_type', '')
    if medicine_type:
        explanation_parts.append(f"{medicine_type}として効果が期待できます")

    symptom_specificity_penalty = score_breakdown.get('symptom_specificity_penalty', 0)
    if symptom_specificity_penalty < -0.2:
        explanation_parts.append("⚠️ 症状への特異性: 複合薬のため、単一症状への適合度はやや低めです")

    risk_ingredient_penalty = score_breakdown.get('risk_ingredient_penalty', 0)
    if risk_ingredient_penalty < -0.2:
        risk_ingredient = candidate.get('risk_ingredient', '')
        if risk_ingredient:
            explanation_parts.append(f"⚠️ リスク成分含有: {risk_ingredient}が含まれています")

    if candidate.get('risk_warning'):
        explanation_parts.append(f"⚠️ {candidate.get('risk_warning')}")

    if candidate.get('low_score_warning'):
        explanation_parts.append("⚠️ 推奨スコアが低めです。使用前に薬剤師または登録販売者にご相談ください。")

    if safety_result.get("warnings"):
        for warning in safety_result['warnings']:
            explanation_parts.append(f"⚠️ {warning}")

    explanation = " | ".join(explanation_parts)
    citation = _kb_citation_for_explanation(candidate, nlu_result, user_info)
    if citation:
        explanation = f"{explanation} | 📚 {citation}"
    return explanation


def generate_individual_usage_notes_with_gpt(
    medicine: Dict,
    client: OpenAI
) -> str:
    """
    個別の医薬品について、CSVのE〜K列を使ってChatGPTで使用上の注意を生成
    """
    prompt = f"""
あなたは登録販売者です。以下の医薬品情報から、使用上の注意を簡潔に生成してください。

【医薬品情報】
製品名: {medicine.get('product_name', '')}
効能効果（E列）: {medicine.get('efficacy', '')}
用法用量（F列）: {medicine.get('usage', '')}
年齢制限（G列）: {medicine.get('age_restriction', '')}
禁止物質（I列）: {medicine.get('doping_prohibited', '')}

【生成ルール】
1. 効能: E列の効能効果を全文記載（省略しない）
2. 用法用量の注意: F列から重要な注意を2〜3項目、100字以内に要約
   - 「用法用量を厳守」は他で記載済みなので省略
   - 小児・乳幼児への注意など、この医薬品特有の注意のみ記載
   - 箇条書き形式
3. 年齢制限: G列にある場合のみ記載
   - 年齢制限が複雑な表現（「1歳以下は1／12量以下」「15歳以下8歳まで：1／2量」など）を含む場合は、「年齢制限: 用法用量を参照してください」と記載してください
   - 単純な表現（「15歳以上」「7歳以上」など）の場合は、そのまま記載してください
4. ドーピング: I列に「禁止物質あり」がある場合のみ記載

【出力形式】
効能: [全文]

用法用量の注意:
・[この医薬品特有の注意1]
・[この医薬品特有の注意2]

年齢制限: [ある場合のみ、複雑な表現の場合は「年齢制限: 用法用量を参照してください」]

ドーピング: [ある場合のみ]

【除外すべき内容】
- 服用方法（＜○○の服用方法＞）
- 一般的な注意（用法用量を厳守、など）
"""
    from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

    query = str(medicine.get("product_name") or "").strip()
    prompt = augment_medicine_prompt_with_kb(
        query,
        prompt,
        recommended_medicines=[medicine],
    )

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="explain",
            path="explanation_generator.individual_usage",
            messages=[
                {"role": "system", "content": "あなたは登録販売者です。効能は詳細に、用法用量の注意は簡潔に要約してください。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )

        from src.core.llm_client import extract_completion_text

        result = extract_completion_text(response)
        return result.strip()

    except Exception as e:
        logger.warning(f"個別使用上の注意生成エラー: {e}")
        notes = []

        efficacy = medicine.get('efficacy', '')
        if efficacy:
            notes.append(f"効能: {efficacy}")

        age_restriction = medicine.get('age_restriction', '')
        if isinstance(age_restriction, float):
            if not math.isnan(age_restriction):
                try:
                    age_val = int(age_restriction)
                    notes.append(f"年齢制限: {age_val}歳以上の方が対象です。")
                except Exception:
                    pass
        elif age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
            notes.append(f"年齢制限: {age_restriction}")

        usage = medicine.get('usage', '')
        if usage and '注意' in usage:
            usage_lines = usage.split('\n')
            caution_items = []
            skip_section = False

            for line in usage_lines:
                line = line.strip()
                if '服用方法' in line:
                    skip_section = True
                    continue
                elif line.startswith('＜') and '注意' in line:
                    skip_section = False
                    continue
                if skip_section or not line:
                    continue
                if re.match(r'^[１-９1-9０-９][\．\.]', line):
                    if '用法・用量を厳守' in line or '用法用量を厳守' in line:
                        continue
                    if '定められた用法・用量' in line:
                        continue
                    content = re.sub(r'^[１-９1-9０-９][\．\.]', '', line).strip()
                    if '小児に服用させる' in content:
                        caution_items.append('小児服用時は保護者の監督が必要')
                    elif '乳幼児' in content and '医師' in content:
                        caution_items.append('2歳未満は医師の診療を優先')
                    elif '分割' in content and '服用' in content:
                        caution_items.append('分割服用は2日以内に使用')
                    elif len(content) > 10:
                        summary = content[:30] + ('...' if len(content) > 30 else '')
                        caution_items.append(summary)

            if caution_items:
                notes.append('\n用法用量の注意:')
                for item in caution_items[:3]:
                    notes.append(f'・{item}')

        doping = medicine.get('doping_prohibited', '')
        competition_category = medicine.get('competition_category', '')
        conditions = medicine.get('conditions', '')

        if doping and '禁止物質あり' in doping:
            doping_note = f"ドーピング禁止物質: {doping}"
            if competition_category:
                doping_note += f"\n競技会区分: {competition_category}"
            if conditions:
                doping_note += f"\n条件: {conditions}"
            notes.append(doping_note)

        return '\n'.join(notes) if notes else '用法用量を守ってご使用ください。'


def generate_usage_notes_and_consultation_with_gpt(
    recommended_medicines: List[Dict],
    nlu_result: Dict,
    user_info: Dict,
    client: OpenAI
) -> Dict:
    """
    選択された医薬品のCSVデータをChatGPTに渡して、
    使用上の注意と医師相談が必要な場合のアドバイスを生成
    3件まとめて1回のAPI呼び出しで処理（高速化）
    """
    # Phase 1 sub4: 同一入力（医薬品セット+リスク属性+症状）のキャッシュ（フラグ ON 時）
    cache_key = None
    try:
        from config.llm_flags import is_explain_cache_enabled

        if is_explain_cache_enabled():
            cache_key = _batch_notes_cache_key(recommended_medicines, nlu_result, user_info)
            hit = _batch_notes_cache.get(cache_key)
            if hit and (time.time() - hit[0]) <= _BATCH_NOTES_TTL_SEC:
                logger.info("📋 バッチ使用上の注意をキャッシュから取得")
                return _apply_age_policy_to_usage_result(
                    dict(hit[1]), recommended_medicines, user_info
                )
    except Exception:
        cache_key = None

    medicines_info = []
    for i, med in enumerate(recommended_medicines, 1):
        age_restriction = med.get('age_restriction', '')
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            age_restriction = ''

        medicines_info.append({
            "number": i,
            "product_name": med.get('product_name', ''),
            "efficacy": med.get('efficacy', ''),
            "usage": med.get('usage', ''),
            "age_restriction": age_restriction if isinstance(age_restriction, str) else str(age_restriction) if age_restriction else '',
            "doping_prohibited": med.get('doping_prohibited', '')
        })

    symptoms_context = ""
    if nlu_result:
        symptoms_list = [s.get("name", "") if isinstance(s, dict) else s for s in nlu_result.get("symptoms", [])]
        if symptoms_list:
            symptoms_context = f"\nユーザーの症状: {', '.join(symptoms_list)}\n"

    prompt = "医薬品情報:\n\n"
    for med_info in medicines_info:
        prompt += f"{med_info['number']}. {med_info['product_name']}\n"
        prompt += f"効能: {med_info['efficacy']}\n"
        prompt += f"用法: {med_info['usage'][:200]}\n"
        if med_info['age_restriction']:
            prompt += f"年齢制限: {med_info['age_restriction']}\n"
        if med_info['doping_prohibited']:
            prompt += f"禁止物質: {med_info['doping_prohibited']}\n"
        prompt += "\n"

    prompt += f"{symptoms_context}"
    user_text = str(
        (user_info or {}).get("user_text")
        or (user_info or {}).get("user_message")
        or ""
    )
    prompt += _sports_context_instruction(user_text)
    from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

    prompt = augment_medicine_prompt_with_kb(
        user_text,
        prompt,
        recommended_medicines=recommended_medicines,
    )
    prompt += """JSON形式で出力:
{
  "medicines": [
    {
      "number": 1,
      "product_name": "製品名",
      "usage_notes": "効能: [全文]\\n\\n用法用量の注意:\\n・[重要な注意2項目以内]\\n\\n[年齢制限・ドーピング情報]"
    }
  ]
}

ルール: 効能は全文、用法用量注意は2項目以内、重要情報のみ記載。
年齢制限が複雑な表現（「1歳以下は1／12量以下」「15歳以下8歳まで：1／2量」など）を含む場合は、「年齢制限: 用法用量を参照してください」と記載してください。
{symptoms_context and f'ユーザーの症状に合わせた注意事項を含めてください。' or ''}"""

    try:
        from src.core.llm_client import chat_completion_create
        from config.llm_config import get_explain_model

        try:
            from config.llm_flags import is_explain_batch_stabilize_enabled

            _batch_stabilize = is_explain_batch_stabilize_enabled()
        except Exception:
            _batch_stabilize = False

        fast_model = get_explain_model(
            assess_explanation_risk(user_info, nlu_result, recommended_medicines)
        )
        _batch_max_tokens = 900 if _batch_stabilize else 600
        response = chat_completion_create(
            client,
            model_role="explain",
            path="explanation_generator.batch_usage_notes",
            model=fast_model,
            messages=[
                {"role": "system", "content": "登録販売者として、効能は全文、用法用量注意は2項目以内で簡潔に。年齢制限が複雑な場合は「年齢制限: 用法用量を参照してください」と記載。JSON形式で出力。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=_batch_max_tokens,
            response_format={"type": "json_object"},
        )

        from src.core.llm_client import extract_completion_text

        result_text = extract_completion_text(response)
        if not result_text and _batch_stabilize:
            logger.info("batch usage_notes empty — retrying with max_tokens=1200")
            response = chat_completion_create(
                client,
                model_role="explain",
                path="explanation_generator.batch_usage_notes",
                model=fast_model,
                messages=[
                    {"role": "system", "content": "登録販売者として、効能は全文、用法用量注意は2項目以内で簡潔に。年齢制限が複雑な場合は「年齢制限: 用法用量を参照してください」と記載。JSON形式で出力。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            result_text = extract_completion_text(response)
        if not result_text:
            raise ValueError("empty completion content")
        result_json = json.loads(result_text)

        individual_notes = []
        medicines_dict = {m['number']: m for m in result_json.get('medicines', [])}

        for i, med in enumerate(recommended_medicines, 1):
            med_result = medicines_dict.get(i)
            ingredients = str(med.get('ingredients', '')).lower()
            usage_notes = med_result.get('usage_notes', '') if med_result else ''

            has_irritant_laxative = any(
                ingredient.lower() in ingredients
                for ingredient in IRRITANT_LAXATIVE_INGREDIENTS
            )

            if has_irritant_laxative:
                warning_text = "刺激性下剤が含まれています"
                if warning_text not in usage_notes and "連用" not in usage_notes:
                    warning_html = '<strong>⚠️ 重要：</strong>本品には刺激性下剤が含まれています。連用により耐性が生じる可能性があるため、3日以上の連用は避けてください。症状が続く場合は医師にご相談ください。'
                    usage_notes = usage_notes + '\n\n' + warning_html if usage_notes else warning_html
                    if med_result:
                        med_result['usage_notes'] = usage_notes
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"刺激性下剤の警告を追加: {med.get('product_name', '')}")

            from src.core.recommendation.pollen_rhinitis_scoring import (
                append_vasoconstrictor_nasal_warning,
                mark_vasoconstrictor_flag,
            )

            mark_vasoconstrictor_flag(med)
            if med.get("has_vasoconstrictor_nasal"):
                usage_notes = append_vasoconstrictor_nasal_warning(usage_notes or "", med)
                if med_result:
                    med_result["usage_notes"] = usage_notes

            if med_result:
                individual_note = med_result.get('usage_notes', '')
            else:
                individual_note = generate_individual_usage_notes_with_gpt(med, client)

            age_restriction = med.get('age_restriction', '')
            age_restriction_display = ''

            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''

            is_complex_age_restriction = False
            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                if re.search(r'\d+[／/]\d+量', age_restriction):
                    is_complex_age_restriction = True
                elif '歳以下' in age_restriction and '量' in age_restriction:
                    is_complex_age_restriction = True
                elif len(re.findall(r'\d+歳', age_restriction)) >= 2:
                    is_complex_age_restriction = True

            if not is_complex_age_restriction:
                if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                    if '15歳未満' in age_restriction:
                        age_restriction_display = '年齢制限: 15歳以上の方が対象です。'
                    elif '7歳未満' in age_restriction:
                        age_restriction_display = '年齢制限: 7歳以上の方が対象です。'
                    elif '12歳未満' in age_restriction:
                        age_restriction_display = '年齢制限: 12歳以上の方が対象です。'
                    else:
                        match = re.search(r'(\d+)歳', age_restriction)
                        if match:
                            age_val = match.group(1)
                            age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
                elif isinstance(age_restriction, (int, float)):
                    if not (isinstance(age_restriction, float) and math.isnan(age_restriction)):
                        try:
                            age_val = int(age_restriction)
                            age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
                        except (ValueError, OverflowError):
                            pass

            note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
            if age_restriction_display and age_restriction_display not in individual_note and not is_complex_age_restriction:
                note_text += f"\n{age_restriction_display}"

            treatment_warning = user_info.get('treatment_mention', False)
            if treatment_warning:
                treatment_warning_message = "\n⚠️ <strong>治療中の方へ</strong>: 現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。重篤な疾患で治療中の方が市販薬を服用する場合、主疾患への影響が重要になります。"
                note_text += treatment_warning_message

            individual_notes.append(note_text)

        usage_notes_individual = '\n\n'.join(individual_notes)

    except Exception as e:
        logger.warning(f"バッチ処理エラー: {e}。フォールバック: 個別並列処理に切り替えます")

        def _build_fallback_note(i_med_tuple):
            i, med = i_med_tuple
            individual_note = generate_individual_usage_notes_with_gpt(med, client)

            ingredients = str(med.get('ingredients', '')).lower()
            has_irritant_laxative = any(
                ingredient.lower() in ingredients
                for ingredient in IRRITANT_LAXATIVE_INGREDIENTS
            )
            if has_irritant_laxative:
                warning_text = "刺激性下剤が含まれています"
                if warning_text not in individual_note and "連用" not in individual_note:
                    warning_html = '<strong>⚠️ 重要：</strong>本品には刺激性下剤が含まれています。連用により耐性が生じる可能性があるため、3日以上の連用は避けてください。症状が続く場合は医師にご相談ください。'
                    individual_note = individual_note + '\n\n' + warning_html if individual_note else warning_html

            from src.core.recommendation.pollen_rhinitis_scoring import (
                append_vasoconstrictor_nasal_warning,
                mark_vasoconstrictor_flag,
            )
            mark_vasoconstrictor_flag(med)
            individual_note = append_vasoconstrictor_nasal_warning(individual_note or "", med)

            age_restriction = med.get('age_restriction', '')
            age_restriction_display = ''
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                if '15歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 15歳以上の方が対象です。'
                elif '7歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 7歳以上の方が対象です。'
                elif '12歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 12歳以上の方が対象です。'
                else:
                    match = re.search(r'(\d+)歳', age_restriction)
                    if match:
                        age_val = match.group(1)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
            elif isinstance(age_restriction, (int, float)):
                if not (isinstance(age_restriction, float) and math.isnan(age_restriction)):
                    try:
                        age_restriction_display = f'年齢制限: {int(age_restriction)}歳以上の方が対象です。'
                    except (ValueError, OverflowError):
                        pass

            note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
            if age_restriction_display:
                note_text += f"\n{age_restriction_display}"
            if user_info.get('treatment_mention', False):
                note_text += "\n⚠️ <strong>治療中の方へ</strong>: 現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。重篤な疾患で治療中の方が市販薬を服用する場合、主疾患への影響が重要になります。"
            return i, note_text

        notes_by_index: dict[int, str] = {}
        meds_indexed = list(enumerate(recommended_medicines, 1))
        max_w = min(3, len(meds_indexed)) if meds_indexed else 1
        with ThreadPoolExecutor(max_workers=max_w) as pool:
            futs = {pool.submit(_build_fallback_note, item): item[0] for item in meds_indexed}
            for fut in as_completed(futs):
                try:
                    idx, note_text = fut.result()
                    notes_by_index[idx] = note_text
                except Exception as exc:
                    logger.warning("Parallel fallback usage_notes task failed: %s", exc)

        individual_notes = [notes_by_index[i] for i in sorted(notes_by_index)]
        usage_notes_individual = '\n\n'.join(individual_notes)

    enhanced_user_info = user_info.copy()
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part:
        enhanced_user_info['user_body_part'] = user_body_part

    general_notes = generate_default_usage_notes_and_consultation(recommended_medicines, enhanced_user_info, nlu_result)

    if user_body_part == "delicate_area":
        delicate_area_note = "\n\n【性器周辺の症状について】\n性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。特に、以下の場合はすぐに医師にご相談ください：\n・症状が3日以上続く場合\n・症状が悪化する場合\n・発疹、水ぶくれ、ただれなどの症状がある場合\n・性行為のパートナーにも症状がある場合"
        doctor_consultation = general_notes['doctor_consultation'] + delicate_area_note
    else:
        doctor_consultation = general_notes['doctor_consultation']

    usage_notes_combined = usage_notes_individual + '\n\n' + general_notes['usage_notes']

    logger.info(f"使用上の注意生成完了: {len(individual_notes)}件")

    treatment_warning = general_notes.get('treatment_warning', False)

    result = {
        "usage_notes": usage_notes_combined,
        "doctor_consultation": doctor_consultation,
        "treatment_warning": treatment_warning
    }

    if cache_key is not None:
        if len(_batch_notes_cache) >= _BATCH_NOTES_MAX:
            oldest = min(_batch_notes_cache, key=lambda k: _batch_notes_cache[k][0])
            _batch_notes_cache.pop(oldest, None)
        _batch_notes_cache[cache_key] = (time.time(), dict(result))

    return _apply_age_policy_to_usage_result(result, recommended_medicines, user_info)


def generate_default_usage_notes_and_consultation(recommended_medicines: List[Dict], user_info: Dict, nlu_result: Dict = None) -> Dict:
    """
    デフォルトの使用上の注意と医師相談アドバイスを生成（フォールバック用）
    """
    usage_notes_parts = []

    is_sleep_medicine = False
    for med in recommended_medicines:
        medicine_type = med.get('medicine_type', '')
        if '睡眠障害' in str(medicine_type):
            is_sleep_medicine = True
            break

    has_insomnia = False
    has_sleepiness = False
    if nlu_result:
        symptom_names = [s.get("name", "") if isinstance(s, dict) else s for s in nlu_result.get("symptoms", [])]
        has_insomnia = any(symptom_name == "不眠" for symptom_name in symptom_names)
        has_sleepiness = any(symptom_name == "眠気" for symptom_name in symptom_names)

    contraindications_parts = ["【使ってはいけない人】"]

    user_age = user_info.get('age')
    if user_age:
        if user_age < 7:
            contraindications_parts.append("・7歳未満のお子様（医師の診察を受けてください）")
        elif user_age < 15:
            contraindications_parts.append("・一部の医薬品は15歳未満の方は使用できません")

    if user_info.get('pregnant'):
        contraindications_parts.append("・妊娠中の方（特にNSAIDs含有製品は禁忌）")
    if user_info.get('breastfeeding'):
        contraindications_parts.append("・授乳中の方（医師にご相談ください）")

    contraindications_parts.extend([
        "・過去に医薬品でアレルギー症状を起こしたことがある方",
        "・医師の治療を受けている方",
        "・高齢者の方（医師や薬剤師にご相談ください）"
    ])

    if is_sleep_medicine and has_insomnia and not has_sleepiness:
        contraindications_parts.append("・緑内障の疾患がある方（抗コリン作用により症状が悪化する可能性があります）")
        contraindications_parts.append("・前立腺肥大の疾患がある方（抗コリン作用により症状が悪化する可能性があります）")

    usage_notes_parts.extend(contraindications_parts)

    usage_notes_parts.extend([
        "",
        "【服用時の注意】",
        "・用法用量を厳守してください",
        "・なるべく空腹時の服用は避けてください",
        "・アレルギー体質の方は成分を確認してください",
        "・服用後、乗り物や機械の運転操作をしないでください（眠気が出る場合があります）"
    ])

    if is_sleep_medicine:
        usage_notes_parts.append("・お酒とあわせた服用は危険です。アルコール摂取後は服用しないでください")

        if has_insomnia and not has_sleepiness:
            usage_notes_parts.append("・睡眠改善薬は一時的な不眠にのみ効果があります。常用化を避け、症状が続く場合は医師にご相談ください")
            usage_notes_parts.append("・睡眠改善薬は医師による治療の代用にはなりません。不眠症と診断されている場合は医師にご相談ください")
            usage_notes_parts.append("・かぜ薬、解熱鎮痛薬、鎮咳去痰薬、抗ヒスタミン剤含有薬、睡眠薬との併用はできません")

    if user_info.get('age') and user_info['age'] < 15:
        usage_notes_parts.append("・小児が服用する場合は保護者の監督のもとで服用してください")

    doctor_consultation_parts = [
        "【以下の場合は医師にご相談ください】",
        "・症状が3日以上続く場合",
        "・症状が悪化する場合",
        "・高熱（38.5度以上）が続く場合",
        "・発疹、発赤、かゆみなどの副作用が現れた場合",
        "・他の症状が現れた場合",
        "・長期連用する場合"
    ]

    if is_sleep_medicine and has_insomnia and not has_sleepiness:
        doctor_consultation_parts.insert(1, "・不眠症と診断されている場合")
        doctor_consultation_parts.insert(2, "・慢性的な不眠状態が続いている場合")
        doctor_consultation_parts.insert(3, "・症状が1週間以上続いている場合")

    if user_info.get('pregnant') or user_info.get('breastfeeding'):
        doctor_consultation_parts.insert(1, "・妊娠中・授乳中の方は事前に医師にご相談ください")

    if user_info.get('user_body_part') == "delicate_area":
        doctor_consultation_parts.insert(1, "・性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。")
        doctor_consultation_parts.insert(2, "・性器周辺のかゆみ、発疹、痛みなどの症状が続く場合は、早めに医師にご相談ください。")

    otc_disclaimer = [
        "",
        "【OTC医薬品について】",
        "・OTC医薬品（市販薬）はあくまで対症療法であり、安静や栄養補給が重要です",
        "・症状が長引く場合や重症化する可能性がある場合は、専門の医師に相談することをお勧めします"
    ]
    usage_notes_parts = otc_disclaimer + usage_notes_parts

    treatment_mention = user_info.get("treatment_mention", False)
    if treatment_mention:
        treatment_warning_header = [
            "⚠️ <strong>治療中の方へ</strong>",
            "現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。",
            "重篤な疾患で治療中の方が市販薬を服用する場合、主疾患への影響（例：腎不全患者へのNSAIDs使用、高血圧患者へのエフェドリン使用など）が重要になります。",
            ""
        ]
        usage_notes_parts = treatment_warning_header + usage_notes_parts

    return _apply_age_policy_to_usage_result(
        {
            "usage_notes": '\n'.join(usage_notes_parts),
            "doctor_consultation": '\n'.join(doctor_consultation_parts),
            "treatment_warning": treatment_mention
        },
        recommended_medicines,
        user_info,
    )


