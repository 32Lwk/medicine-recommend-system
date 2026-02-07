"""
ユーザー属性抽出モジュール

多言語対応のユーザー属性（年齢、性別、妊娠中、アレルギー等）を
GPT で抽出する責務を持つ。
"""
import json
import logging
import os

logger = logging.getLogger(__name__)


def create_multilingual_attribute_extraction_prompt(user_text, language, user_info=None):
    """
    言語に応じたユーザー属性抽出プロンプトを作成

    Args:
        user_text (str): ユーザーの入力テキスト
        language (str): 検出された言語コード
        user_info (dict): 既存のユーザー情報

    Returns:
        str: プロンプトテキスト
    """
    prompts = {
        'ja': f"""
あなたは医薬品推奨システムです。ユーザーのメッセージから以下の属性情報を抽出してください。

【ユーザーのメッセージ】
{user_text}

【既存のユーザー情報】
{user_info if user_info else 'なし'}

【抽出すべき属性】
- age: 年齢（数値）
- gender: 性別（男性/女性）
- pregnant: 妊娠中かどうか（true/false）
- breastfeeding: 授乳中かどうか（true/false）
- allergies: アレルギー（リスト）
- current_medications: 服用中の薬（リスト）
- medical_history: 既往症（リスト）
- symptom_duration_days: 症状の期間（日数）
- other_info: その他の情報（文字列）

【回答形式】
以下のJSON形式で回答してください：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["なし"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "その他の情報があれば"
}}

情報が不明な場合は null を返してください。
""",

        'en': f"""
You are a medicine recommendation system. Extract the following attribute information from the user's message.

【User's Message】
{user_text}

【Existing User Information】
{user_info if user_info else 'None'}

【Attributes to Extract】
- age: Age (number)
- gender: Gender (Male/Female)
- pregnant: Whether pregnant (true/false)
- breastfeeding: Whether breastfeeding (true/false)
- allergies: Allergies (list)
- current_medications: Current medications (list)
- medical_history: Medical history (list)
- symptom_duration_days: Duration of symptoms (days)
- other_info: Other information (string)

【Response Format】
Please respond in the following JSON format:
{{
    "age": 30,
    "gender": "Male",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["None"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "Other information if any"
}}

Return null for unknown information.
""",

        'ko': f"""
당신은 의약품 추천 시스템입니다. 사용자의 메시지에서 다음 속성 정보를 추출해주세요.

【사용자의 메시지】
{user_text}

【기존 사용자 정보】
{user_info if user_info else '없음'}

【추출해야 할 속성】
- age: 나이 (숫자)
- gender: 성별 (남성/여성)
- pregnant: 임신 여부 (true/false)
- breastfeeding: 수유 여부 (true/false)
- allergies: 알레르기 (목록)
- current_medications: 복용 중인 약 (목록)
- medical_history: 병력 (목록)
- symptom_duration_days: 증상 지속 기간 (일수)
- other_info: 기타 정보 (문자열)

【응답 형식】
다음 JSON 형식으로 응답해주세요:
{{
    "age": 30,
    "gender": "남성",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["없음"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "기타 정보가 있다면"
}}

정보를 모르는 경우 null을 반환하세요.
""",

        'zh': f"""
您是药品推荐系统。请从用户消息中提取以下属性信息。

【用户消息】
{user_text}

【现有用户信息】
{user_info if user_info else '无'}

【要提取的属性】
- age: 年龄（数字）
- gender: 性别（男性/女性）
- pregnant: 是否怀孕（true/false）
- breastfeeding: 是否哺乳（true/false）
- allergies: 过敏（列表）
- current_medications: 正在服用的药物（列表）
- medical_history: 病史（列表）
- symptom_duration_days: 症状持续时间（天数）
- other_info: 其他信息（字符串）

【回答格式】
请以以下JSON格式回答：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["无"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "如有其他信息"
}}

未知信息请返回null。
"""
    }

    return prompts.get(language, prompts['ja'])


def extract_user_attributes_multilingual(user_text, client=None, user_info=None):
    """
    多言語対応のユーザー属性抽出

    Args:
        user_text (str): ユーザーの入力テキスト
        client: OpenAIクライアント
        user_info (dict): 既存のユーザー情報

    Returns:
        dict: 抽出された属性情報
    """
    if client is None:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {}
        client = OpenAI(api_key=api_key)

    from src.core.language_utils import detect_language

    detected_language = detect_language(user_text)
    prompt = create_multilingual_attribute_extraction_prompt(user_text, detected_language, user_info)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical AI assistant that extracts user attributes from text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )

        result = response.choices[0].message.content
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
            logger.debug(f"ChatGPT属性抽出応答 ({detected_language}): {result}")

        try:
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                parsed_result['detected_language'] = detected_language
                return parsed_result
            else:
                return {"detected_language": detected_language}
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            return {"detected_language": detected_language}

    except Exception as e:
        logger.error(f"ChatGPT API呼び出しエラー: {e}")
        return {"detected_language": detected_language}
