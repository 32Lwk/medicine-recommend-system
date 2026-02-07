"""
入力判定ヘルパーモジュール

曖昧入力・操作コマンド・症状入力の判定、
不足属性のチェックを行う。
"""
import re
from typing import Dict, List, Tuple


def is_ambiguous_input(user_text: str, symptoms: List[str], nlu_result: Dict) -> bool:
    """
    曖昧な入力かどうかを判定

    Args:
        user_text: ユーザー入力テキスト
        symptoms: 抽出された症状リスト（文字列のリスト）
        nlu_result: NLU解析結果

    Returns:
        bool: 曖昧な入力の場合True
    """
    symptom_count = len(symptoms) if symptoms else 0
    if symptom_count < 3:
        return False

    text_length = len(user_text.strip())
    if text_length > 30:
        return False

    confidence_score = nlu_result.get('confidence_score', 1.0)
    user_text_lower = user_text.lower()
    explicit_symptoms = []
    symptom_keywords = {
        "発熱": ["発熱", "熱", "高熱", "微熱", "熱がある"],
        "頭痛": ["頭痛", "頭が痛い"],
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず"],
        "のどの痛み": ["のど", "喉", "のどの痛み", "喉が痛い"],
        "くしゃみ": ["くしゃみ"],
        "寒気": ["寒気", "悪寒"]
    }

    for symptom_name, keywords in symptom_keywords.items():
        if any(keyword in user_text_lower for keyword in keywords):
            explicit_symptoms.append(symptom_name)

    if len(explicit_symptoms) >= 2:
        return False

    if confidence_score < 0.5:
        return True

    return True


def check_missing_attributes(user_attributes: Dict) -> Tuple[List[str], str]:
    """不足している属性情報をチェックし、追加質問を生成"""
    missing_questions = []
    missing_priority = 'optional'

    if not user_attributes.get('age'):
        missing_questions.append('年齢を教えてください。（医薬品の適切な選択に必要です）')
        missing_priority = 'critical'

    if not user_attributes.get('gender'):
        missing_questions.append('性別を教えてください。（男性/女性）')
        missing_priority = 'critical'

    if user_attributes.get('gender') == 'female' and user_attributes.get('pregnant') is None:
        missing_questions.append('現在、妊娠中または授乳中ですか？（はい/いいえ）')
        if missing_priority == 'optional':
            missing_priority = 'important'

    if not user_attributes.get('symptom_duration_days'):
        missing_questions.append('症状はいつ頃から続いていますか？（例：昨日から、3日前から）')
        if missing_priority == 'optional':
            missing_priority = 'important'

    symptom_duration = user_attributes.get('symptom_duration_days')
    if symptom_duration and symptom_duration > 7:
        missing_questions.append(
            '⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。'
            '医療機関（病院・クリニック）での受診をお勧めします。'
        )
        missing_priority = 'critical'

    if not user_attributes.get('allergies'):
        missing_questions.append('アレルギーはありますか？（薬物アレルギー、食物アレルギーなど）')

    if not user_attributes.get('current_medications'):
        missing_questions.append('現在服用中の薬はありますか？')

    if not user_attributes.get('medical_history'):
        missing_questions.append('持病や既往歴はありますか？')

    return missing_questions, missing_priority


def is_operation_command(user_message: str) -> bool:
    """
    操作指示を検出（誤検出を防ぐための厳密な検出ロジック）

    セキュリティ対策:
    - 操作指示キーワードが文脈的に操作指示として使われているかを確認
    - 命令形（「更新して」「更新してください」など）を含む場合のみ検出
    - 症状記述（例: 「症状が更新されました」）は誤検出しない
    """
    operation_patterns = [
        r'情報を(足しました|追加しました).*更新',
        r'更新して(ください|くれ)',
        r'再読み込み(してください|してくれ)',
        r'リロード(してください|してくれ)',
        r'reload',
        r'refresh',
        r'更新(してください|してくれ|しろ|せよ)',
        r'情報を更新',
        r'ページを更新',
        r'画面を更新'
    ]

    symptom_patterns = [
        r'症状が更新',
        r'状態が更新',
        r'体調が更新',
        r'痛みが更新'
    ]

    for pattern in symptom_patterns:
        if re.search(pattern, user_message):
            return False

    for pattern in operation_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True

    return False


def is_symptom_input(message: str) -> bool:
    """メッセージが症状入力かどうかを判定"""
    if not message:
        return False

    text = message.strip()
    lower_text = text.lower()

    symptom_keywords = [
        '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
        '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
        '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
        '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
        '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
    ]

    question_keywords = [
        'ですか', 'でしょうか', 'ですか？', 'でしょうか？', 'どう', '何', 'なぜ', 'いつ',
        '副作用', '飲み方', '注意', '効果', '効き目', '時間', '回数', '量', '併用',
        'ドーピング', '禁止', '違反', '大丈夫', '安全', '危険', '問題', '影響',
        '一緒に', '同時に', '飲んで', '使って', '服用', '投与', '飲み合わせ',
        'スポーツ', '競技', '運動', 'トレーニング', '試合', '大会', '検査', '陽性',
        '成分', '効能', '作用', 'メカニズム', '仕組み',
        '飲む', '使う', '摂取', '飲むタイミング', '飲む時間',
        '食前', '食後', '食間', '空腹時', '満腹時', '就寝前', '起床時',
        '他の薬', '併用', '同時', '一緒', '組み合わせ',
        '注意点', '気をつける', '避ける', '控える', '中止', '停止',
        '当たる', '当たります', '対象', '対象外', '含まれる', '含まれない',
        '使える', '使えない', '可能', '不可能', '適切', '不適切',
        '効く', '効かない', '効果的', '効果的でない',
        '副作用が出る', '副作用がある', '副作用がない',
        '安全性', '危険性', 'リスク',
        '教えて', '教えてください', '知りたい', '聞きたい'
    ]

    attribute_keywords = [
        '歳です', '歳、', '男性です', '女性です', '男です', '女です',
        'いいえ', 'はい', 'ありません', 'ないです', 'なしです',
        '妊娠', '授乳', 'アレルギー',
        '昨日から', '今日から', 'きのうから', 'きょうから', '日前から', '週間前から',
        '服用している', '飲んでいる', '続いています',
        'years old', 'male', 'female', 'man', 'woman', 'allergy', 'allergies',
        'pregnant', 'breastfeeding', 'taking', 'medication', 'medicine',
        'started', 'days ago', 'weeks ago', 'months ago', 'yesterday', 'today'
    ]

    has_symptom_keyword = any(keyword in text for keyword in symptom_keywords)
    has_question_keyword = any(keyword in text for keyword in question_keywords)
    has_attribute_keyword = any(keyword in text for keyword in attribute_keywords)
    ends_with_question_mark = text.endswith('？') or text.endswith('?') or lower_text.endswith('?')

    attribute_count = sum(1 for keyword in attribute_keywords if keyword in text)
    symptom_count = sum(1 for keyword in symptom_keywords if keyword in text)

    if attribute_count >= 3 and attribute_count > symptom_count:
        return False

    if has_question_keyword or ends_with_question_mark:
        return False

    if has_symptom_keyword:
        return True

    if has_attribute_keyword:
        return False

    return True
