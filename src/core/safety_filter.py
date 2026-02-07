"""
安全性フィルタ層

禁忌チェック、睡眠薬安全性チェックを担当（rule_based_recommendation から分離・SRP改善）
"""

from typing import Dict, List

from src.core.recommendation_constants import (
    CONTRAINDICATION_RULES,
    DOCTOR_REFERRAL_CONDITIONS,
)


def check_safety_contraindications(user_info: Dict, nlu_result: Dict) -> Dict:
    """
    安全性チェック（禁忌、年齢制限、重症疑い）- 強化版
    妊婦・1週間以上・重症疑いの場合は医師受診を必須とする

    Returns:
        {
            "is_safe": bool,
            "warnings": List[str],
            "exclusions": List[str],
            "requires_escalation": bool,
            "escalation_reason": str,
            "doctor_referral_required": bool,
            "referral_reasons": List[Dict]
        }
    """
    safety_result = {
        "is_safe": True,
        "warnings": [],
        "exclusions": [],
        "requires_escalation": False,
        "escalation_reason": "",
        "doctor_referral_required": False,
        "referral_reasons": []
    }

    # 1. 重症疑い症状チェック（最優先）- 医師受診必須
    if nlu_result.get("needs_escalation", False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = nlu_result.get("escalation_reason", "重症疑い症状が検出されました")
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["severe_symptoms"])
        return safety_result

    # 2. 年齢チェック（強化版）
    age = user_info.get('age')
    if age is not None:
        age_rules = CONTRAINDICATION_RULES["年齢制限"]

        if age_rules["乳児"][0] <= age < age_rules["乳児"][1]:
            safety_result["is_safe"] = False
            safety_result["requires_escalation"] = True
            safety_result["doctor_referral_required"] = True
            safety_result["escalation_reason"] = f"{age}歳の乳児は市販薬の使用ができません。必ず医師の診察を受けてください。"
            safety_result["referral_reasons"].append({
                "description": "乳児（0-3歳）",
                "message": "乳児は市販薬の使用ができません。必ず医師の診察を受けてください。",
                "priority": "critical"
            })
            return safety_result
        elif age_rules["幼児"][0] <= age < age_rules["幼児"][1]:
            safety_result["is_safe"] = False
            safety_result["requires_escalation"] = True
            safety_result["doctor_referral_required"] = True
            safety_result["escalation_reason"] = f"{age}歳の幼児は医師の診察を受けてください。市販薬の使用は医師にご相談ください。"
            safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["age_under_7"])
            return safety_result
        elif age_rules["小児"][0] <= age < age_rules["小児"][1]:
            safety_result["warnings"].append(f"{age}歳の小児は市販薬使用に注意が必要です。保護者の監督下で使用してください。")
        elif age_rules["高齢者"][0] <= age:
            safety_result["warnings"].append(f"{age}歳の高齢者は市販薬使用に注意が必要です。副作用に特に注意してください。")

    # 2.5. 性器周辺症状のチェック
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part == "delicate_area":
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。"
        safety_result["warnings"].append("性器周辺の症状は、性感染症や皮膚疾患の可能性があります。医師の診察を受けることを強く推奨します。")
        safety_result["referral_reasons"].append({
            "description": "性器周辺の症状",
            "message": "性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。",
            "priority": "high"
        })

    # 3. 妊娠中チェック
    if user_info.get('pregnant', False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["pregnancy"])
        pregnancy_restrictions = CONTRAINDICATION_RULES["妊娠中"]
        for medicine_type, restriction in pregnancy_restrictions.items():
            if restriction == "禁忌":
                safety_result["warnings"].append(f"妊娠中は{medicine_type}の使用が禁忌です。")
            elif restriction == "要注意":
                safety_result["warnings"].append(f"妊娠中は{medicine_type}の使用に注意が必要です。")
        return safety_result

    # 3.5. 妊娠の可能性チェック
    pregnancy_possible = user_info.get('pregnancy_possible')
    if not pregnancy_possible:
        nlu_pregnancy_possible = nlu_result.get('pregnancy_possible', {})
        if nlu_pregnancy_possible.get('detected', False):
            confidence = nlu_pregnancy_possible.get('confidence')
            if confidence == 'high':
                pregnancy_possible = 'high'
            elif confidence == 'low':
                pregnancy_possible = 'low'

    if pregnancy_possible == 'high':
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "妊娠の可能性があります。医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["pregnancy_possible"])
        return safety_result
    elif pregnancy_possible == 'low':
        safety_result["warnings"].append("一部の症状は妊娠の可能性を示す場合がありますが、性別情報がないため確定できません。医師にご相談ください。")

    # 4. 授乳中チェック
    if user_info.get('breastfeeding', False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["breastfeeding"])
        breastfeeding_restrictions = CONTRAINDICATION_RULES["授乳中"]
        for medicine_type, restriction in breastfeeding_restrictions.items():
            if restriction == "要注意":
                safety_result["warnings"].append(f"授乳中は{medicine_type}の使用に注意が必要です。")
        return safety_result

    # 5. 症状の期間チェック
    symptoms_over_week = False
    for symptom in nlu_result.get("symptoms", []):
        duration = symptom.get("duration_days")
        if duration is not None and duration >= 7:
            symptoms_over_week = True
            safety_result["warnings"].append(f"症状が{duration}日間続いています。長期化している場合は医師の診察を推奨します。")

    if symptoms_over_week:
        safety_result["doctor_referral_required"] = True
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["symptoms_over_week"])

    # 6. 症状の重症度チェック
    for symptom in nlu_result.get("symptoms", []):
        if symptom.get("severity") == "重度":
            safety_result["warnings"].append(f"重度の{symptom.get('name')}が報告されています。症状が重い場合は医師の診察を推奨します。")

    return safety_result


def check_sleep_medicine_safety(
    user_text: str,
    user_info: Dict,
    nlu_result: Dict,
    medicine_type: str
) -> Dict:
    """
    睡眠改善薬専用の安全性チェック
    """
    import logging
    logger = logging.getLogger(__name__)

    result = {
        "is_safe": True,
        "should_recommend": True,
        "requires_escalation": False,
        "escalation_reason": "",
        "warnings": [],
        "critical_questions": [],
        "alternative_therapies": []
    }

    if medicine_type != "睡眠障害":
        return result

    # 1. 眠気のみの場合は睡眠改善薬を推奨しない
    symptoms = nlu_result.get("symptoms", []) or []
    symptom_names = [s.get("name") for s in symptoms if s.get("name")]
    if symptom_names == ["眠気"] or (len(symptom_names) == 1 and "眠気" in symptom_names):
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = "眠気の症状には睡眠改善薬は適していません。眠気防止薬（カフェイン剤など）や生活習慣の見直しをご検討ください。"
        return result

    # 2. 不眠症と診断されている場合
    insomnia_diagnosed = nlu_result.get("insomnia_diagnosed", False)
    if insomnia_diagnosed:
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = "不眠症と診断されている場合は、市販の睡眠改善薬ではなく、医師による治療を受けることをお勧めします。"
        return result

    # 3. 慢性的な不眠状態
    chronic_insomnia = nlu_result.get("chronic_insomnia", False)
    if chronic_insomnia:
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = "慢性的な不眠状態が続いている場合は、精神科や心療内科、睡眠専門の医療機関への受診をお勧めします。市販の睡眠改善薬は一時的な不眠にのみ効果があります。"
        return result

    # 4. 15歳未満のチェック
    age = user_info.get('age')
    if age is not None and age < 15:
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = f"{age}歳の小児の不眠相談については、医師の診察を受けることをお勧めします。市販の睡眠改善薬は15歳以上が対象です。"
        return result

    # 5. 緑内障・前立腺肥大の疾患チェック
    glaucoma_keywords = ["緑内障", "眼圧", "視野狭窄"]
    prostate_keywords = ["前立腺肥大", "前立腺", "排尿困難", "頻尿"]
    has_glaucoma = any(keyword in user_text for keyword in glaucoma_keywords)
    has_prostate = any(keyword in user_text for keyword in prostate_keywords)

    if has_glaucoma:
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = "緑内障の疾患がある方は、睡眠改善薬の成分である抗ヒスタミン薬の抗コリン作用により、症状が悪化する可能性があります。使用できません。"
        return result

    if has_prostate:
        result["is_safe"] = False
        result["should_recommend"] = False
        result["requires_escalation"] = True
        result["escalation_reason"] = "前立腺肥大の疾患がある方は、睡眠改善薬の成分である抗ヒスタミン薬の抗コリン作用により、症状が悪化する可能性があります。使用できません。"
        return result

    if not has_glaucoma:
        result["critical_questions"].append("緑内障の疾患はありますか？")
    gender = user_info.get('gender', '')
    if not has_prostate and (gender == '男性' or gender == ''):
        result["critical_questions"].append("前立腺肥大の疾患はありますか？")

    # 6. 併用医薬品チェック
    current_medications = user_info.get('current_medications', [])
    if current_medications:
        medication_text = ' '.join(current_medications).lower()
        incompatible_keywords = [
            "かぜ薬", "風邪薬", "総合感冒薬", "感冒薬",
            "解熱鎮痛薬", "痛み止め", "熱冷まし", "鎮痛薬",
            "咳止め", "痰切り", "鎮咳", "去痰",
            "抗ヒスタミン", "アレルギー薬", "抗アレルギー",
            "睡眠薬", "睡眠導入剤", "催眠薬"
        ]
        for keyword in incompatible_keywords:
            if keyword in medication_text:
                result["is_safe"] = False
                result["should_recommend"] = False
                result["requires_escalation"] = True
                result["escalation_reason"] = f"現在服用中の薬（{keyword}を含む）と睡眠改善薬の併用はできません。成分が重なり、副作用などが強く出る恐れがあります。"
                return result

    user_text_lower = user_text.lower()
    incompatible_input_keywords = {
        "かぜ薬": ["かぜ薬", "風邪薬", "総合感冒薬"],
        "解熱鎮痛薬": ["解熱鎮痛薬", "痛み止め", "熱冷まし"],
        "鎮咳去痰薬": ["咳止め", "痰切り", "鎮咳"],
        "抗ヒスタミン剤": ["抗ヒスタミン", "アレルギー薬"],
        "睡眠薬": ["睡眠薬", "処方された睡眠薬", "医師からもらった睡眠薬"]
    }

    for med_type, keywords in incompatible_input_keywords.items():
        for keyword in keywords:
            if keyword in user_text_lower:
                result["is_safe"] = False
                result["should_recommend"] = False
                result["requires_escalation"] = True
                if med_type == "睡眠薬":
                    result["escalation_reason"] = "睡眠薬との併用は避けなければなりません。睡眠改善薬は睡眠薬の代用にはなりません。医師による治療を妨げる恐れがあります。"
                else:
                    result["escalation_reason"] = f"{med_type}との併用はできません。成分が重なり、副作用などが強く出る恐れがあります。"
                return result

    if not current_medications:
        result["critical_questions"].append("現在、かぜ薬、解熱鎮痛薬、鎮咳去痰薬、抗ヒスタミン剤含有薬、または睡眠薬を服用していますか？")

    # 7. アルコール併用警告
    result["warnings"].append("お酒とあわせた服用は危険です。アルコール摂取後は服用しないでください。")
    result["warnings"].append("睡眠改善薬は一時的な不眠にのみ効果があります。常用化を避け、症状が続く場合は医師にご相談ください。")
    result["warnings"].append("睡眠改善薬は医師による治療の代用にはなりません。不眠症と診断されている場合は医師にご相談ください。")

    result["alternative_therapies"] = [
        "ハーブティー（カモミール、バレリアンなど）を就寝前に飲む",
        "ラベンダーの香りを利用したリラックス効果",
        "アロマテラピー（リラックス効果のある香り）",
        "睡眠環境の改善（室温、照明、騒音対策など）"
    ]

    return result
