"""
不足情報チェック・質問生成・やけど程度判定

rule_based_recommendation から分離（SRP改善）
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from src.core.recommendation_constants import BURN_SEVERITY_KEYWORDS

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def generate_symptom_detail_questions_with_gpt(
    user_text: str,
    nlu_result: Dict,
    user_info: Dict,
    client: OpenAI
) -> List[Dict[str, str]]:
    """
    ChatGPTを使用して症状詳細に関する追加質問を生成

    Args:
        user_text: ユーザーの入力テキスト
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        client: OpenAI client

    Returns:
        質問リスト（各質問は{"question": str, "priority": str}の形式）
    """
    if not client:
        return []

    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return []

    symptom_names = [s.get("name", "") for s in symptoms if s.get("name")]
    if not symptom_names:
        return []

    basic_info_covered = {
        "age": user_info.get('age') is not None,
        "gender": user_info.get('gender') is not None,
        "pregnant": user_info.get('pregnant') is not None or user_info.get('breastfeeding') is not None,
        "allergies": user_info.get('allergies') is not None and len(user_info.get('allergies', [])) > 0,
        "medications": user_info.get('current_medications') is not None and len(user_info.get('current_medications', [])) > 0,
        "duration": any(s.get('duration_days') is not None for s in symptoms) or user_info.get('symptom_duration_days') is not None
    }

    prompt = f"""ユーザーの症状に関する追加質問を生成してください。

【ユーザーの入力】
{user_text}

【検出された症状】
{', '.join(symptom_names)}

【既に回答済みの基本情報】
- 年齢: {'回答済み' if basic_info_covered['age'] else '未回答'}
- 性別: {'回答済み' if basic_info_covered['gender'] else '未回答'}
- 妊娠・授乳状態: {'回答済み' if basic_info_covered['pregnant'] else '未回答'}
- アレルギー: {'回答済み' if basic_info_covered['allergies'] else '未回答'}
- 服用中薬: {'回答済み' if basic_info_covered['medications'] else '未回答'}
- 症状の期間: {'回答済み' if basic_info_covered['duration'] else '未回答'}

【指示】
1. 症状の詳細（部位、原因、程度、経過など）に関する質問を生成してください
2. 基本情報（年齢、性別、妊娠状態、アレルギー、服用中薬、期間）に関する質問は生成しないでください
3. 各質問に優先度（critical, important, optional）を付与してください
4. 質問数は適切な数（3-5問程度）にしてください
5. JSON形式で返してください

【出力形式】
[
    {{"question": "質問文", "priority": "critical|important|optional"}},
    ...
]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは医薬品推奨システムの質問生成アシスタントです。症状の詳細を把握するための適切な質問を生成してください。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        result = response.choices[0].message.content.strip()

        if result.startswith('```json'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]
        result = result.strip()

        questions = json.loads(result)

        validated_questions = []
        for q in questions:
            if isinstance(q, dict) and "question" in q and "priority" in q:
                priority = q.get("priority", "optional")
                if priority not in ["critical", "important", "optional"]:
                    priority = "optional"
                validated_questions.append({
                    "question": q.get("question", ""),
                    "priority": priority
                })

        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ChatGPTで生成された症状詳細質問: {len(validated_questions)}件")

        return validated_questions

    except Exception as e:
        logger.warning(f"ChatGPTによる質問生成でエラーが発生しました: {e}")
        return []


def check_missing_information(user_info: Dict, nlu_result: Dict, user_text: str = "", client: Optional[OpenAI] = None) -> Dict:
    """
    不足している情報をチェックし、追加質問を生成（あいまい症状対応を含む）

    Returns:
        {
            "has_missing_info": bool,
            "missing_fields": List[str],
            "questions": List[str],
            "critical_questions": List[str],
            "priority": str
        }
    """
    missing_info = {
        "has_missing_info": False,
        "missing_fields": [],
        "questions": [],
        "critical_questions": [],
        "priority": "optional"
    }

    if user_info.get('age') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("age")
        missing_info["questions"].append("年齢を教えてください。（より適切な医薬品選択のため）")
        if missing_info["priority"] != "critical":
            missing_info["priority"] = "important"

    symptoms = nlu_result.get('symptoms', [])
    if not symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptoms")
        missing_info["questions"].append("具体的にどのような症状がありますか？（例：頭痛、発熱、咳、鼻水など）")
        missing_info["priority"] = "critical"

    if user_info.get('gender') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("gender")
        missing_info["questions"].append("性別を教えてください。（男性/女性）")
        if missing_info["priority"] != "critical":
            missing_info["priority"] = "important"

    pregnancy_answered = user_info.get('pregnant') is not None
    breastfeeding_answered = user_info.get('breastfeeding') is not None

    if user_info.get('gender') == '女性' or user_info.get('gender') is None:
        if not pregnancy_answered and not breastfeeding_answered:
            age = user_info.get('age')
            if age is None or (age and 15 <= age <= 50):
                missing_info["has_missing_info"] = True
                missing_info["missing_fields"].append("pregnancy_status")
                missing_info["questions"].append("現在、妊娠中または授乳中ですか？（はい/いいえ）")
                if missing_info["priority"] != "critical":
                    missing_info["priority"] = "important"

    has_duration = any(s.get('duration_days') is not None for s in symptoms) or user_info.get('symptom_duration_days') is not None
    if not has_duration and symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptom_duration")
        missing_info["questions"].append("症状はいつ頃から続いていますか？（例：昨日から、3日前から）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"

    medications = user_info.get('current_medications')
    medications_answered = medications is not None and isinstance(medications, list)

    if not medications_answered:
        if symptoms:
            missing_info["has_missing_info"] = True
            missing_info["missing_fields"].append("current_medications")
            missing_info["questions"].append("現在、他に服用している薬はありますか？（ある場合は薬の名前を教えてください）")
            if missing_info["priority"] not in ["critical", "important"]:
                missing_info["priority"] = "optional"

    allergies = user_info.get('allergies')
    allergies_answered = allergies is not None and isinstance(allergies, list) and len(allergies) > 0

    if not allergies_answered:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("allergies")
        missing_info["questions"].append("薬や食品のアレルギーはありますか？（ある場合は具体的に教えてください）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"

    if client and user_text and symptoms:
        has_critical_missing = (
            user_info.get('age') is None or
            user_info.get('gender') is None or
            (user_info.get('gender') == '女性' and user_info.get('pregnant') is None)
        )

        if has_critical_missing:
            try:
                symptom_detail_questions = generate_symptom_detail_questions_with_gpt(
                    user_text, nlu_result, user_info, client
                )

                for q_dict in symptom_detail_questions:
                    question = q_dict.get("question", "")
                    priority = q_dict.get("priority", "optional")

                    if question:
                        missing_info["has_missing_info"] = True
                        missing_info["missing_fields"].append("symptom_detail")

                        if priority == "critical":
                            missing_info["critical_questions"].append(question)
                            if missing_info["priority"] != "critical":
                                missing_info["priority"] = "critical"
                        elif priority == "important":
                            missing_info["questions"].append(question)
                            if missing_info["priority"] not in ["critical", "important"]:
                                missing_info["priority"] = "important"
                        else:
                            missing_info["questions"].append(question)
                            if missing_info["priority"] == "optional":
                                missing_info["priority"] = "optional"
            except Exception as e:
                logger.warning(f"症状詳細質問生成でエラーが発生しました: {e}")

    return missing_info


def detect_burn_severity(user_text: str) -> Tuple[Optional[str], bool]:
    """
    やけどの程度を判定

    Args:
        user_text: ユーザー入力テキスト

    Returns:
        (severity: "軽度"/"中等度"/"重度"/None, is_doctor_referral: bool)
    """
    user_text_lower = user_text.lower()

    burn_keywords = ["やけど", "火傷", "熱傷", "やけ", "火傷", "熱傷"]
    has_burn_keyword = any(kw in user_text_lower for kw in burn_keywords)

    if not has_burn_keyword:
        return None, False

    severe_keywords = BURN_SEVERITY_KEYWORDS["severe"]
    for keyword in severe_keywords:
        if keyword in user_text_lower:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"やけどの重度キーワード検出（ガードレール）: {keyword}")
            return "重度", True

    return "軽度", False
