"""
入力種別の分類（挨拶/質問/症状）

app.py の index から分離（SRP改善）
"""

import logging
from typing import Literal

from src.utils.input_helpers import is_symptom_input

logger = logging.getLogger(__name__)

# 挨拶キーワード
GREETING_KEYWORDS = [
    'こんにちは', 'こんばんは', 'おはよう', 'おはようございます',
    'はじめまして', '初めまして', 'よろしく', 'よろしくお願いします',
    'お疲れ様', 'おつかれさま', 'おつかれ', 'ご苦労様',
    'さようなら', 'さよなら', 'バイバイ', 'またね',
    'ありがとう', 'ありがとうございます', 'どうも', 'どうもありがとう',
    'すみません', 'すいません', 'ごめんなさい', 'ごめん',
    'hello', 'hi', 'good morning', 'good evening', 'good night',
    'thanks', 'thank you', 'bye', 'goodbye'
]

# 症状キーワード（is_symptom_input と同じリスト）
SYMPTOM_KEYWORDS = [
    '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
    '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
    '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
    '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
    '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
]

# システム紹介キーワード
SYSTEM_INTRO_KEYWORDS = [
    'あなたについて', 'あなたは', 'システムについて', 'どんなシステム',
    '何ができる', '機能', '自己紹介'
]

# 医薬品検索キーワード
MEDICINE_SEARCH_KEYWORDS = [
    'の薬', '薬を', '医薬品', 'について教えて', 'を教えて', 'お勧め', 'おすすめ'
]

# 質問キーワード
QUESTION_KEYWORDS = [
    'ですか', 'でしょうか', 'ですか？', 'でしょうか？',
    'ますか', 'できますか', '利用できますか', '使用できますか', '使えますか',
    '飲めますか', '飲んでも大丈夫ですか', '使用しても大丈夫ですか', '利用しても大丈夫ですか',
    '服用できますか', '服用しても大丈夫ですか', '摂取できますか',
    'ドーピング', '禁止', '禁止物質', '違反', '大丈夫', '安全', '危険',
    '大会前', '競技', 'レース', '試合前', '試合で', 'アンチドーピング', '陽性',
    '当たる', '当たります', '対象', '含まれる', '使える',
    '副作用', '飲み方', '効果', '効き目',
    '教えて', '教えてください', '知りたい', '聞きたい'
]

# 質問接尾辞
QUESTION_SUFFIXES = [
    'ですか', 'でしょうか', 'ますか', 'できますか', '利用できますか',
    '使用できますか', '使えますか', '飲めますか', '飲んでも大丈夫ですか',
    '使用しても大丈夫ですか', '利用しても大丈夫ですか', '服用できますか',
    '服用しても大丈夫ですか', '摂取できますか'
]


def classify_input(
    user_message: str,
    force_question_mode: bool = False
) -> Literal["greeting", "question", "symptom"]:
    """
    ユーザー入力を分類（挨拶/質問/症状）

    Args:
        user_message: ユーザーの入力メッセージ
        force_question_mode: 強制的に質問として扱うフラグ

    Returns:
        "greeting": 挨拶
        "question": 質問（医薬品検索、システム紹介、一般質問など）
        "symptom": 症状入力
    """
    if not user_message or not isinstance(user_message, str):
        return "question"

    user_message = user_message.strip()
    if not user_message:
        return "question"

    if force_question_mode:
        return "question"

    # 挨拶・症状キーワードのチェック
    has_greeting = any(greeting in user_message for greeting in GREETING_KEYWORDS)
    has_symptom = any(symptom in user_message for symptom in SYMPTOM_KEYWORDS)

    # 症状入力の判定（input_helpers と整合）
    is_symptom = is_symptom_input(user_message)

    # 挨拶のみで症状キーワードが含まれていない場合
    if has_greeting and not has_symptom:
        # システム紹介・医薬品検索・質問のいずれかなら「質問」
        is_system_intro = any(kw in user_message for kw in SYSTEM_INTRO_KEYWORDS)
        is_medicine_search = any(kw in user_message for kw in MEDICINE_SEARCH_KEYWORDS)
        has_question_keyword = any(kw in user_message for kw in QUESTION_KEYWORDS)
        message_stripped = user_message.strip()
        has_question_suffix = any(message_stripped.endswith(suffix) for suffix in QUESTION_SUFFIXES)
        ends_with_question_mark = message_stripped.endswith('?') or message_stripped.endswith('？')

        if not (is_system_intro or is_medicine_search or has_question_keyword or
                has_question_suffix or ends_with_question_mark):
            logger.info(f"👋 GREETING DETECTED: {user_message}")
            return "greeting"

    # 症状入力
    if is_symptom:
        return "symptom"

    # 上記以外は質問
    return "question"
