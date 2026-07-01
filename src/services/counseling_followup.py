"""
相談フォローアップ質問モジュール

counseling_response から分離（SRP改善）。
フォローアップ質問の生成と、質問すべきかの判定を担当。
"""

import json
import logging
import difflib
import re
from typing import Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_DEDUP_SIMILARITY_THRESHOLD = 0.85


def _normalize_question_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def filter_duplicate_counseling_questions(
    questions: List[str],
    prior_questions: List[str],
) -> List[str]:
    """直近に出した質問と重複するフォローアップを除外する。"""
    prior_norm = {_normalize_question_text(q) for q in prior_questions if q}
    filtered: List[str] = []
    for question in questions or []:
        q = (question or "").strip()
        if not q:
            continue
        norm = _normalize_question_text(q)
        if norm in prior_norm:
            continue
        if any(
            norm in p or p in norm
            for p in prior_norm
            if len(p) >= 6 and len(norm) >= 6
        ):
            continue
        if any(
            difflib.SequenceMatcher(None, norm, p).ratio() >= _DEDUP_SIMILARITY_THRESHOLD
            for p in prior_norm
            if len(p) >= 8
        ):
            continue
        if any(
            difflib.SequenceMatcher(None, norm, _normalize_question_text(f)).ratio()
            >= _DEDUP_SIMILARITY_THRESHOLD
            for f in filtered
        ):
            continue
        filtered.append(q)
        prior_norm.add(norm)
    return filtered


def prior_questions_from_history(question_history: List[Dict]) -> List[str]:
    return [
        str(item.get("question") or "").strip()
        for item in (question_history or [])
        if item.get("question")
    ]


def calculate_adaptive_question_limit(
    symptom_type: str,
    collected_info: Dict,
    question_count: int
) -> int:
    """
    適応的な質問上限を計算

    Args:
        symptom_type: 症状タイプ
        collected_info: 収集済み情報
        question_count: 現在の質問回数

    Returns:
        質問上限（最大質問回数）
    """
    medical_symptom_types = ['heart_pain', 'anxiety', 'depression_like']
    if symptom_type in medical_symptom_types:
        base_limit = 7
    else:
        base_limit = 4

    info_count = len(collected_info)
    if info_count >= 3:
        return min(base_limit, question_count + 2)

    return base_limit


def should_ask_question(
    user_response: str,
    collected_info: Dict,
    question_count: int,
    symptom_type: str
) -> Dict:
    """
    質問を返すべきかどうかを判断

    Returns:
        {
            "should_ask": bool,
            "reason": str,
            "response_first": bool  # 返信を先に返すべきか
        }
    """
    if len(collected_info) >= 3:
        return {
            "should_ask": False,
            "reason": "sufficient_info",
            "response_first": True
        }

    adaptive_limit = calculate_adaptive_question_limit(
        symptom_type, collected_info, question_count
    )
    if question_count >= adaptive_limit:
        return {
            "should_ask": False,
            "reason": "question_limit_reached",
            "response_first": True
        }

    if len(user_response) < 20:
        return {
            "should_ask": True,
            "reason": "short_response",
            "response_first": True
        }

    return {
        "should_ask": True,
        "reason": "normal",
        "response_first": True
    }


def generate_follow_up_questions(
    symptom_type: str,
    collected_info: Dict,
    client: OpenAI,
    prior_questions: Optional[List[str]] = None,
) -> List[str]:
    questions = _generate_follow_up_questions_impl(symptom_type, collected_info, client)
    return filter_duplicate_counseling_questions(questions, prior_questions or [])


def _generate_follow_up_questions_impl(
    symptom_type: str,
    collected_info: Dict,
    client: OpenAI,
) -> List[str]:
    """
    フォローアップ質問を生成

    Args:
        symptom_type: 感情的症状タイプまたは不適切な要求タイプ
        collected_info: 収集済み情報
        client: OpenAIクライアントインスタンス

    Returns:
        フォローアップ質問のリスト
    """
    if symptom_type.startswith("inappropriate_request/"):
        request_type = symptom_type.split("/")[1]
        if request_type in ["illegal", "controlled"]:
            return []

        try:
            prompt = f"""
あなたは医薬品相談AIアシスタントです。不適切な要求に対して、より詳しい情報を収集するための
フォローアップ質問を生成してください。

【要求タイプ】
{symptom_type}

【既に収集済みの情報】
{json.dumps(collected_info, ensure_ascii=False, indent=2)}

【質問生成の要件】
- 優しく導くトーンで質問を生成
- ユーザーの理解度に応じた適応的な質問
- 4-6ステップの中程度の対話フローを想定
- システムの制限や代替案について理解を深めるための質問
- 専門家への相談を促すための質問

【回答形式】
JSON形式で回答してください：
{{
    "questions": ["質問1", "質問2", "質問3", "質問4"]
}}

最大4つの質問を生成してください。
"""
            from src.core.llm_client import chat_completion_create
            response = chat_completion_create(
                client,
                model_role="counsel",
                path="counseling_followup",
                messages=[
                    {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。適切なフォローアップ質問を生成してください。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            questions = result.get("questions", [])

            return questions[:4] if questions else []
        except Exception as e:
            logger.error(f"フォローアップ質問生成エラー: {e}")
            return ["他にご質問やご相談はございますか？"]

    if symptom_type == "insomnia":
        has_duration = "duration" in collected_info or "期間" in str(collected_info)
        has_cause = "cause" in collected_info or "原因" in str(collected_info)
        has_relaxation = "relaxation" in collected_info or "リラックス" in str(collected_info)

        questions = []

        if not has_duration:
            questions.append("どのくらいの期間、眠れない状態が続いていますか？")

        if not has_cause and len(questions) < 3:
            questions.append("不眠の原因として、何か心配事やストレスがありますか？")

        if not has_relaxation and len(questions) < 3:
            questions.append("就寝前に何かリラックスできる習慣はありますか？")

        if len(questions) < 2:
            additional_questions = [
                "どのような時間帯に眠れないことが多いですか？",
                "不眠の影響で、日中の生活に支障はありますか？"
            ]
            for q in additional_questions:
                if len(questions) < 3:
                    questions.append(q)

        if not questions:
            questions = ["どのくらいの期間、眠れない状態が続いていますか？"]

        return questions[:3]

    if symptom_type == "drowsiness":
        has_duration = "duration" in collected_info or "期間" in str(collected_info)
        has_cause = "cause" in collected_info or "原因" in str(collected_info)
        has_sleep_pattern = "sleep_pattern" in collected_info or "睡眠パターン" in str(collected_info)

        questions = []

        if not has_duration:
            questions.append("どのくらいの期間、眠気が続いていますか？")

        if not has_cause and len(questions) < 3:
            questions.append("眠気の原因として、何か心当たりはありますか？（睡眠不足、ストレス、生活リズムなど）")

        if not has_sleep_pattern and len(questions) < 3:
            questions.append("普段の睡眠時間はどのくらいですか？")

        if len(questions) < 2:
            additional_questions = [
                "どのような時間帯に特に眠気を感じますか？",
                "日中の眠気で、生活や仕事に支障はありますか？"
            ]
            for q in additional_questions:
                if len(questions) < 3:
                    questions.append(q)

        if not questions:
            questions = ["どのくらいの期間、眠気が続いていますか？"]

        return questions[:3]

    prompt = f"""
    あなたは医薬品相談AIアシスタントです。感情的症状について、より詳しい情報を収集するための
    フォローアップ質問を生成してください。

    【症状タイプ】
    {symptom_type}

    【既に収集済みの情報】
    {json.dumps(collected_info, ensure_ascii=False, indent=2)}

    【質問生成の要件】
    - 開かれた質問（Yes/Noで答えられない質問）を優先する
    - ユーザーが話しやすい質問にする
    - 3つ程度の質問を生成する
    - 質問は自然な会話形式で
    - 「もう少し詳しく教えていただけますか？」という質問は生成しない

    【回答形式】
    JSON形式で回答してください：
    {{
        "questions": ["質問1", "質問2", "質問3"]
    }}
    """

    try:
        from src.core.llm_client import chat_completion_create
        response = chat_completion_create(
            client,
            model_role="counsel",
            path="counseling_followup.alt",
            messages=[
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。自然な会話形式のフォローアップ質問を生成してください。「もう少し詳しく教えていただけますか？」という質問は生成しないでください。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        if "questions" in result:
            questions = result["questions"]
        elif isinstance(result, list):
            questions = result
        else:
            if symptom_type == "anxiety":
                questions = ["どのような場面で不安を感じることが多いですか？"]
            elif symptom_type == "stress":
                questions = ["どのようなストレスを感じていますか？"]
            elif symptom_type == "heart_pain":
                questions = ["どのような状況で心の痛みを感じますか？"]
            else:
                questions = ["もう少し詳しく教えていただけますか？"]

        questions = [q for q in questions if "もう少し詳しく教えていただけますか？" not in q]

        if not questions:
            if symptom_type == "anxiety":
                questions = ["どのような場面で不安を感じることが多いですか？"]
            elif symptom_type == "stress":
                questions = ["どのようなストレスを感じていますか？"]
            elif symptom_type == "heart_pain":
                questions = ["どのような状況で心の痛みを感じますか？"]
            else:
                questions = ["具体的にどのような症状がありますか？"]

        return questions if isinstance(questions, list) else [questions]
    except Exception as e:
        logger.error(f"フォローアップ質問生成エラー: {e}")
        if symptom_type == "insomnia":
            return ["どのくらいの期間、眠れない状態が続いていますか？"]
        elif symptom_type == "anxiety":
            return ["どのような場面で不安を感じることが多いですか？"]
        elif symptom_type == "stress":
            return ["どのようなストレスを感じていますか？"]
        elif symptom_type == "heart_pain":
            return ["どのような状況で心の痛みを感じますか？"]
        else:
            return ["具体的にどのような症状がありますか？"]
