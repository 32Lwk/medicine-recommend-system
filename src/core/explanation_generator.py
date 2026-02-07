"""
推奨理由・使用上の注意の説明生成

rule_based_recommendation から分離（SRP改善）
"""

import json
import logging
import math
import os
import re
from typing import Dict, List

from openai import OpenAI

from src.core.recommendation_constants import IRRITANT_LAXATIVE_INGREDIENTS

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


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

    return " | ".join(explanation_parts)


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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは登録販売者です。効能は詳細に、用法用量の注意は簡潔に要約してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )

        result = response.choices[0].message.content
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "登録販売者として、効能は全文、用法用量注意は2項目以内で簡潔に。年齢制限が複雑な場合は「年齢制限: 用法用量を参照してください」と記載。JSON形式で出力。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=600,
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
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
        logger.warning(f"バッチ処理エラー: {e}。フォールバック: 個別処理に切り替えます")
        individual_notes = []
        for i, med in enumerate(recommended_medicines, 1):
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
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"刺激性下剤の警告を追加（フォールバック）: {med.get('product_name', '')}")

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
                        age_val = int(age_restriction)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
                    except (ValueError, OverflowError):
                        pass

            note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
            if age_restriction_display:
                note_text += f"\n{age_restriction_display}"

            treatment_warning = user_info.get('treatment_mention', False)
            if treatment_warning:
                treatment_warning_message = "\n⚠️ <strong>治療中の方へ</strong>: 現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。重篤な疾患で治療中の方が市販薬を服用する場合、主疾患への影響が重要になります。"
                note_text += treatment_warning_message

            individual_notes.append(note_text)

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

    return {
        "usage_notes": usage_notes_combined,
        "doctor_consultation": doctor_consultation,
        "treatment_warning": treatment_warning
    }


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

    return {
        "usage_notes": '\n'.join(usage_notes_parts),
        "doctor_consultation": '\n'.join(doctor_consultation_parts),
        "treatment_warning": treatment_mention
    }


