"""
ユーザー属性抽出パターンモジュール

正規表現ベースでメッセージから属性を抽出する責務を持つ。
漢数字・英語・既往症・アレルギー・性別推論などに対応。
"""
import re
from typing import Dict, List, Any, Optional

from src.utils.kanji_numbers import parse_kanji_age


# 妊娠・授乳
PREGNANT_TRUE = [
    r'妊娠中です', r'妊娠中', r'妊娠しています', r'妊娠しました',
    r'妊娠してます', r'妊娠した', r'妊婦です', r'pregnant', r'i\'m pregnant'
]
PREGNANT_FALSE = [
    r'妊娠していません', r'妊娠中ではありません', r'妊娠していない', r'妊娠してない',
    r'not pregnant', r'i\'m not pregnant'
]
BREASTFEEDING_TRUE = [
    r'授乳中です', r'授乳中', r'授乳しています', r'授乳しました', r'授乳してます',
    r'breastfeeding', r'nursing'
]
BREASTFEEDING_FALSE = [
    r'授乳していません', r'授乳中ではありません', r'授乳していない',
    r'not breastfeeding'
]

# 性別: (pattern, gender) または (pattern, None) で後続チェック
GENDER_PATTERNS = [
    (r'私は(?:女性|女)です', '女性'),
    (r'私は(?:男性|男)です', '男性'),
    (r'性別は(?:女性|女)', '女性'),
    (r'性別は(?:男性|男)', '男性'),
    (r'^(?:女性|女)です', '女性'),
    (r'^(?:男性|男)です', '男性'),
    (r'^(?:女|男)です', None),
    (r'\b(?:female|woman)\b', '女性'),
    (r'\b(?:male|man)\b', '男性'),
    (r'i\'m (?:a )?female', '女性'),
    (r'i\'m (?:a )?male', '男性'),
]

# 女性特有の症状・部位 → 性別推論
FEMALE_SPECIFIC_TERMS = [
    '生理', '月経', '妊娠', '妊婦', '授乳', 'つわり', '更年期', '婦人科',
    '子宮', '卵巣', '乳房', '乳首', '膣', '腟', 'おりもの', 'PMS',
    'menstrual', 'period', 'pregnant', 'pregnancy', 'menopause', 'ovary',
    'uterus', 'breast'
]

# 男性特有の症状・部位 → 性別推論（医学的に男性を示す表現、俗語含む）
# 医薬品推奨では性別が重要であるため、俗語でも男性を示す表現は抽出する
MALE_SPECIFIC_TERMS = [
    '前立腺', '精巣', '睾丸', '勃起', 'ED', '摂護腺',
    'prostate', 'erectile', 'testicle',
    # 俗語（医学的には男性を示す有用な情報。応答では使用しない）
    'ちんこ', 'チンコ', 'ちんぽ', 'チンポ', 'ぽこ', 'ぽっこ',
    'おちんちん', 'オチンチン', 'ぽっきん',
    'penis', 'dick', 'cock',
]


def extract_regex_attributes(message: str) -> Dict[str, Any]:
    """
    メッセージから正規表現でユーザー属性を抽出する。
    漢数字・英語・既往症・アレルギー・性別推論に対応。
    """
    attrs = {}
    msg = message.strip()
    if not msg:
        return attrs

    msg_lower = msg.lower()

    # 妊娠
    if any(re.search(p, msg, re.IGNORECASE) for p in PREGNANT_FALSE):
        attrs['pregnant'] = False
    elif any(re.search(p, msg, re.IGNORECASE) for p in PREGNANT_TRUE):
        attrs['pregnant'] = True

    # 授乳
    if any(re.search(p, msg, re.IGNORECASE) for p in BREASTFEEDING_FALSE):
        attrs['breastfeeding'] = False
    elif any(re.search(p, msg, re.IGNORECASE) for p in BREASTFEEDING_TRUE):
        attrs['breastfeeding'] = True

    # 性別: 明示パターン
    for pattern, gender in GENDER_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            if gender:
                attrs['gender'] = gender
            elif any(t in msg or t in msg_lower for t in ('女', 'female', 'woman')):
                attrs['gender'] = '女性'
            elif any(t in msg or t in msg_lower for t in ('男', 'male', 'man')):
                attrs['gender'] = '男性'
            break

    # 性別: 女性/男性特有の症状・部位から推論
    if 'gender' not in attrs:
        if any(term in msg or term in msg_lower for term in FEMALE_SPECIFIC_TERMS):
            attrs['gender'] = '女性'
        elif any(term in msg or term in msg_lower for term in MALE_SPECIFIC_TERMS):
            attrs['gender'] = '男性'

    # 年齢: 漢数字・アラビア数字
    age = parse_kanji_age(msg)
    if age is not None:
        attrs['age'] = age
    else:
        # アラビア数字 + years old
        m = re.search(r'(\d+)\s*years?\s*old', msg, re.IGNORECASE)
        if m:
            v = int(m.group(1))
            if 0 < v < 150:
                attrs['age'] = v

    # アレルギー
    allergy_attrs = _extract_allergies(msg, msg_lower)
    if allergy_attrs:
        attrs['allergies'] = allergy_attrs

    # 既往症
    history_attrs = _extract_medical_history(msg, msg_lower)
    if history_attrs:
        attrs['medical_history'] = history_attrs

    # 服用中の薬
    med_attrs = _extract_current_medications(msg, msg_lower)
    if med_attrs:
        attrs['current_medications'] = med_attrs

    return attrs


def _extract_allergies(msg: str, msg_lower: str) -> Optional[List[str]]:
    """アレルギー情報を抽出"""
    # 「アレルギーなし」「ありません」など
    if re.search(r'アレルギー(?:は)?(?:ありません|なし|ない)', msg):
        return ['なし']
    if re.search(r'(?:no|not)\s*(?:any\s+)?allerg(?:y|ies)', msg_lower):
        return ['なし']

    # 具体的なアレルギー: 〇〇アレルギー、allergy to X
    allergens = re.findall(r'([ぁ-んァ-ヶーa-zA-Z0-9]+)アレルギー', msg)
    if not allergens:
        m = re.search(r'allerg(?:y|ic)\s+to\s+([^,.\s]+)', msg_lower)
        if m:
            allergens = [m.group(1).strip()]
    if not allergens:
        m = re.search(r'アレルギー[はが]?\s*([^。、]+)', msg)
        if m:
            part = m.group(1).strip()
            allergens = [x.strip() for x in re.split(r'[、,]', part) if x.strip()]
    return allergens if allergens else None


def _extract_medical_history(msg: str, msg_lower: str) -> Optional[List[str]]:
    """既往症を抽出"""
    # 「既往症はありません」
    if re.search(r'既往症(?:は)?(?:ありません|なし|ない)', msg):
        return []
    if re.search(r'(?:no|not)\s*medical\s*history', msg_lower):
        return []

    # 既往症: 〇〇があります、持病は〇〇
    history = []
    m = re.search(r'(?:既往症|持病)[はが]?\s*([^。、]+)', msg)
    if m:
        part = m.group(1).strip()
        history = [x.strip() for x in re.split(r'[、,]', part) if x.strip() and len(x.strip()) > 1]
    if not history:
        for term in ['糖尿病', '高血圧', '喘息', 'アトピー', '心臓病', '肝臓病', '腎臓病', '甲状腺',
                     'diabetes', 'hypertension', 'asthma', 'heart disease']:
            if term in msg or term in msg_lower:
                history.append(term)
                break
    return history if history else None


def _extract_current_medications(msg: str, msg_lower: str) -> Optional[List[str]]:
    """服用中の薬を抽出"""
    if re.search(r'(?:服用中の薬|飲んでいる薬)(?:は)?(?:ありません|なし|ない)', msg):
        return []
    if re.search(r'(?:not\s*taking|no\s*medication)', msg_lower):
        return []

    meds = []
    m = re.search(r'(?:服用中|飲んでいる|内服中)[の]?薬[はが]?\s*([^。、]+)', msg)
    if m:
        part = m.group(1).strip()
        meds = [x.strip() for x in re.split(r'[、,]', part) if x.strip() and len(x.strip()) > 1]
    return meds if meds else None
