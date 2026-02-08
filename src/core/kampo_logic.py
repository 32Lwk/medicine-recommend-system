"""
漢方証判定

rule_based_recommendation から分離（SRP改善）。
虚証・実証・中間証の判定を行う。
"""

import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def determine_kampo_sho(user_info: Dict, nlu_result: Dict, user_message: str = "") -> Dict:
    """
    漢方の証（体質）を判定（虚証、実証、中間証）
    確信度ベースの動的重み付けを含む

    Args:
        user_info: ユーザー情報
        nlu_result: NLU解析結果
        user_message: ユーザーのメッセージ

    Returns:
        {
            "sho": "虚証" | "実証" | "中間証" | "不明",
            "confidence": 0.0-1.0,
            "reasons": List[str],
            "kyo_indicators": List[str],
            "jitsu_indicators": List[str]
        }
    """
    user_message_lower = (user_message or "").lower()
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]

    kyo_indicators = []  # 虚証の指標
    jitsu_indicators = []  # 実証の指標

    # 虚証（Kyo-sho）の指標: 体力虚弱、冷え性、疲れやすい、顔色が悪い、など
    kyo_keywords = {
        "体力虚弱": ["体力がない", "体力が弱い", "虚弱", "弱い", "疲れやすい", "疲れが取れない", "だるい", "倦怠感"],
        "冷え性": ["冷え性", "冷え", "冷える", "手足が冷たい", "寒がり"],
        "顔色": ["顔色が悪い", "顔色が悪い", "青白い", "血色が悪い"],
        "食欲不振": ["食欲がない", "食欲不振", "食べられない"],
        "下痢傾向": ["下痢しやすい", "下痢", "軟便", "便が緩い"],
        "めまい": ["めまい", "立ちくらみ", "ふらつき"],
        "貧血傾向": ["貧血", "血が足りない", "血が少ない"]
    }

    # 実証（Jitsu-sho）の指標: 体力充実、便秘、のぼせ、イライラ、など
    jitsu_keywords = {
        "体力充実": ["体力がある", "体力が充実", "元気", "丈夫", "がっちり"],
        "便秘": ["便秘", "便が出ない", "便が硬い", "便秘しがち"],
        "のぼせ": ["のぼせ", "ほてり", "熱感", "顔が赤い"],
        "イライラ": ["イライラ", "ストレス", "怒りっぽい", "神経質"],
        "頭痛": ["頭痛", "頭が痛い", "ズキズキ"],
        "肩こり": ["肩こり", "肩が凝る", "首肩が痛い"],
        "ニキビ": ["ニキビ", "吹き出物", "肌荒れ"]
    }

    # ユーザーメッセージと症状から指標を検出
    for category, keywords in kyo_keywords.items():
        for keyword in keywords:
            if keyword in user_message_lower or any(keyword in name.lower() for name in symptom_names):
                kyo_indicators.append(f"{category}: {keyword}")

    for category, keywords in jitsu_keywords.items():
        for keyword in keywords:
            if keyword in user_message_lower or any(keyword in name.lower() for name in symptom_names):
                jitsu_indicators.append(f"{category}: {keyword}")

    # 証の判定
    kyo_count = len(kyo_indicators)
    jitsu_count = len(jitsu_indicators)

    # 確信度の計算
    total_indicators = kyo_count + jitsu_count
    if total_indicators == 0:
        # 指標が全くない場合: 情報不足
        return {
            "sho": "不明",
            "confidence": 0.0,
            "reasons": ["情報不足のため証を判定できません"],
            "kyo_indicators": [],
            "jitsu_indicators": []
        }

    # 確信度: 指標の数と明確さに基づく
    max_indicators = max(kyo_count, jitsu_count)
    if max_indicators >= 5:
        confidence = min(1.0, 0.7 + (max_indicators - 5) * 0.05)
    elif max_indicators >= 3:
        confidence = 0.5 + (max_indicators - 3) * 0.1
    elif max_indicators >= 1:
        confidence = 0.3 + (max_indicators - 1) * 0.1
    else:
        confidence = 0.0

    # 証の判定ロジック
    if kyo_count > jitsu_count * 1.5:  # 虚証の指標が実証の1.5倍以上
        sho = "虚証"
        reasons = [f"虚証の指標が{kyo_count}個検出されました（実証: {jitsu_count}個）"]
        reasons.extend(kyo_indicators[:3])  # 上位3つを理由として追加
    elif jitsu_count > kyo_count * 1.5:  # 実証の指標が虚証の1.5倍以上
        sho = "実証"
        reasons = [f"実証の指標が{jitsu_count}個検出されました（虚証: {kyo_count}個）"]
        reasons.extend(jitsu_indicators[:3])  # 上位3つを理由として追加
    elif abs(kyo_count - jitsu_count) <= 1 and total_indicators >= 2:
        # 指標の数がほぼ同じ場合: 中間証
        sho = "中間証"
        reasons = [f"虚証と実証の指標がほぼ同数です（虚証: {kyo_count}個、実証: {jitsu_count}個）"]
    else:
        # 判定不能
        sho = "不明"
        reasons = [f"証の判定に十分な情報がありません（虚証: {kyo_count}個、実証: {jitsu_count}個）"]
        confidence = max(0.0, confidence - 0.2)  # 確信度を下げる

    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"🔍 証判定: {sho} (確信度: {confidence:.2f}, 虚証指標: {kyo_count}個, 実証指標: {jitsu_count}個)")
        logger.debug(f"証判定の詳細: {reasons}")

    return {
        "sho": sho,
        "confidence": confidence,
        "reasons": reasons,
        "kyo_indicators": kyo_indicators,
        "jitsu_indicators": jitsu_indicators
    }
