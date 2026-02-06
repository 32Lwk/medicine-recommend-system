"""
緊急事案検出ハンドラーモジュール
不審者、傷病人、刃物などの緊急事案を検出し、適切な案内を提供する
"""

import json
import logging
from typing import Dict, Optional, List, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)

# 緊急事案のキーワード辞書
EMERGENCY_KEYWORDS = {
    "suspicious_person": [
        "不審者", "不審な人", "不審な", "怪しい人", "怪しい", "変な人", "変な", 
        "おかしい人", "おかしい", "不審な行動", "怪しい行動", "不審な動き",
        "尾行", "つけられている", "見られている", "監視されている", "監視",
        "不審な車", "不審な人物", "不審な行動をしている", "怪しい行動をしている",
        "不審な車両", "不審なバイク", "不審な自転車", "不審な人物が",
        "つきまとわれている", "ストーカー", "ストーキング", "つきまとい",
        "不審な視線", "じっと見られている", "見つめられている", "凝視されている"
    ],
    "injured_person": [
        "倒れている", "倒れた", "倒れている人", "倒れている人がいる", "倒れています",
        "倒れている方がいる", "倒れている方が", "倒れている人が", "倒れている人がいます",
        "血が出ている", "血が出た", "出血", "血が", "血だらけ", "血を流している",
        "大出血", "大量出血", "出血している", "出血しています",
        "けがをしている", "けが", "怪我", "負傷", "負傷している", "負傷した",
        "重傷", "軽傷", "けが人", "負傷者", "けがをした", "怪我をした",
        "動かない", "動けていない", "動けません", "動けない", "動けない人が",
        "意識がない", "意識を失っている", "意識を失った", "意識を失いました",
        "意識不明", "意識を失っている人", "意識を失っている方が",
        "助けて", "助けを求めて", "助けが必要", "助けてください", "助けを",
        "救急車", "救急", "119番", "119", "救急車を", "救急車を呼んで",
        "応急処置", "応急手当", "手当てが必要", "手当てを"
    ],
    "weapon": [
        # 一般的な刃物・武器
        "刃物", "ナイフ", "包丁", "ハサミ", "カッター", "カッターナイフ",
        "刀", "剣", "短刀", "小刀", "ナイフを持っている", "刃物を持っている",
        "武器", "凶器", "危険なもの", "危険な物", "武器を持っている",
        "凶器を持っている", "刃物を", "ナイフを", "包丁を",
        # 銃器類
        "銃", "ピストル", "リボルバー", "ハンドガン", "拳銃",
        "ライフル", "ライフル銃", "アサルトライフル", "サブマシンガン",
        "機関銃", "マシンガン", "AK-47", "AK47", "M16", "M4",
        "ショットガン", "スナイパーライフル", "スナイパー",
        "銃を持っている", "ピストルを持っている", "銃を", "ピストルを",
        "発砲", "発砲している", "発砲音", "銃声", "銃撃", "銃撃戦",
        # 爆発物・爆弾
        "爆弾", "爆発物", "手榴弾", "手りゅう弾", "時限爆弾",
        "爆発", "爆発した", "爆発している", "爆発音", "爆破",
        # 現代兵器・軍事装備
        "ドローン", "無人機", "UAV", "軍事ドローン", "攻撃ドローン",
        "イージス艦", "イージス", "護衛艦", "戦艦", "軍艦",
        "空母", "航空母艦", "空母艦", "航空母艦",
        "大砲", "砲", "大砲を", "砲撃", "砲撃している",
        "戦車", "タンク", "装甲車", "戦車を", "タンクを",
        "ミサイル", "ロケット", "ミサイル発射", "ロケット発射",
        "戦闘機", "戦闘機が", "戦闘機を", "軍用機",
        "ヘリコプター", "ヘリ", "軍用ヘリ", "攻撃ヘリ",
        # その他の危険物
        "毒物", "毒", "毒を持っている", "毒を", "毒ガス",
        "化学兵器", "生物兵器", "核兵器", "核", "放射能"
    ],
    "violence": [
        "暴れる", "暴れている", "暴れている人", "暴れています", "暴れている方が",
        "暴行", "暴行されている", "暴行している", "暴行を受けた", "暴行を受けている",
        "暴行を", "暴行をしている", "暴行をしている人",
        "喧嘩", "けんか", "ケンカ", "喧嘩している", "けんかしている",
        "喧嘩を", "けんかを", "ケンカを", "喧嘩が", "けんかが",
        "殴る", "殴っている", "殴られた", "殴られています", "殴られている",
        "殴り", "殴り合い", "殴り合っている", "殴り合いを",
        "蹴る", "蹴っている", "蹴られた", "蹴られています", "蹴られている",
        "蹴り", "蹴りを", "蹴り合い", "蹴り合っている",
        "暴力", "暴力を振るっている", "暴力を受けている", "暴力を振るわれている",
        "暴力を", "暴力が", "暴力行為", "暴力行為を", "暴力行為が",
        "乱暴", "乱暴している", "乱暴されている", "乱暴を", "乱暴が",
        "傷害", "傷害事件", "傷害を", "傷害をしている",
        "殺人", "殺人事件", "殺人を", "殺人をしている", "殺人未遂",
        "脅迫", "脅迫している", "脅迫を", "脅迫が", "脅迫されている"
    ],
    "fire": [
        "火事", "火災", "火が出た", "火が出ている", "火が出ています",
        "火事が", "火災が", "火事を", "火災を", "火事です", "火災です",
        "煙", "煙が出ている", "煙が出ています", "煙が", "煙たい",
        "煙を", "煙が", "煙が立ち込めている", "煙が立ち込めています",
        "燃えている", "燃えています", "燃えてる", "燃えた", "燃えている",
        "燃えている", "燃えている", "燃えている", "燃えている",
        "発火", "発火した", "発火している", "発火しています",
        "火がついている", "火がついた", "火がついています",
        "炎", "炎が出ている", "炎が出ています", "炎が", "炎を",
        "火", "火が", "火の", "火を", "火に", "火です",
        "119", "消防", "消防車", "消火", "消火活動",
        "消防車を", "消防を", "消火を", "消火活動を",
        "延焼", "延焼している", "延焼を", "延焼が",
        "全焼", "半焼", "焼失", "焼失した", "焼失している"
    ],
    "theft": [
        # 基本的な窃盗表現
        "盗まれた", "盗まれました", "盗まれたんです", "盗まれたです",
        "盗まれる", "盗まれている", "盗まれています", "盗まれたものが",
        "盗まれた物が", "盗まれたものが", "盗まれた物を",
        # 万引き関連
        "万引き", "万引きしている", "万引きされた", "万引きされています",
        "万引きを", "万引きが", "万引きをしている", "万引きをしている人",
        "万引き犯", "万引きの", "万引き事件",
        # 泥棒関連
        "泥棒", "泥棒が", "泥棒に", "泥棒に遭った", "泥棒に遭いました",
        "泥棒に", "泥棒を", "泥棒が", "泥棒です", "泥棒が入った",
        "泥棒が入りました", "泥棒に入られた", "泥棒に入られました",
        "空き巣", "空き巣が", "空き巣に", "空き巣に入られた", "空き巣に入られました",
        "空き巣が入った", "空き巣が入りました", "空き巣被害",
        # 窃盗関連
        "窃盗", "窃盗された", "窃盗されました", "窃盗を", "窃盗が",
        "窃盗犯", "窃盗の", "窃盗事件", "窃盗をしている",
        # 盗む関連
        "盗む", "盗み", "盗んでいる", "盗んでいます", "盗まれた",
        "盗みを", "盗みが", "盗みをしている", "盗みをしている人",
        # 取られる関連
        "取られた", "取られました", "取られている", "取られています",
        "取られたものが", "取られた物が", "取られた物を",
        "持っていかれた", "持っていかれました", "持っていかれている",
        "奪われた", "奪われました", "奪われている", "奪われています",
        # 紛失関連（緊急事案として扱う場合）
        "失くした", "なくした", "失くしました", "なくしました",
        "紛失", "紛失した", "紛失しました", "紛失を", "紛失が",
        # その他の窃盗関連表現
        "スリ", "スリに", "スリを", "スリに遭った", "スリに遭いました",
        "ひったくり", "ひったくりに", "ひったくりを", "ひったくりに遭った",
        "置き引き", "置き引きに", "置き引きを", "置き引きに遭った",
        "車上荒らし", "車上荒らしに", "車上荒らしを", "車上荒らしに遭った",
        "自転車泥棒", "自転車が", "自転車を", "自転車が盗まれた",
        "バイク泥棒", "バイクが", "バイクを", "バイクが盗まれた",
        "車泥棒", "車が", "車を", "車が盗まれた", "車が盗まれました"
    ],
    "medical_emergency": [
        "意識がない", "意識を失っている", "意識を失った", "意識を失いました",
        "意識不明", "意識を失っている人", "意識を失っている方が",
        "意識を失っている人が", "意識を失っている人がいます",
        "呼吸困難", "呼吸ができない", "呼吸できない", "息ができない",
        "呼吸が", "呼吸を", "呼吸が止まっている", "呼吸が止まった",
        "心停止", "心停止している", "心停止しています",
        "心肺停止", "心肺停止している", "心肺停止しています",
        "倒れた", "倒れている", "倒れている人", "倒れています",
        "倒れている方が", "倒れている人が", "倒れている人がいます",
        "動かない", "動けていない", "動けません", "動けない", "動けない人が",
        "助けて", "助けを求めて", "助けが必要", "助けてください", "助けを",
        "救急車", "救急", "119番", "119", "救急車を", "救急車を呼んで",
        "救急車を呼んでください", "救急車を呼んで", "救急車が必要",
        "応急処置", "応急手当", "手当てが必要", "手当てを",
        "心臓発作", "心臓発作を", "心臓発作が", "心臓発作を起こした",
        "脳卒中", "脳卒中を", "脳卒中が", "脳卒中を起こした",
        "ショック", "ショック状態", "ショックを", "ショックが"
    ]
}

# 緊急事案の種類ごとのアイコン
EMERGENCY_ICONS = {
    "fire": "🔥",  # 火災（最優先）
    "weapon": "🔪",  # 刃物
    "medical_emergency": "🚑",  # 医療緊急
    "violence": "👊",  # 暴力
    "injured_person": "🚑",  # 傷病人
    "suspicious_person": "🚓",  # 不審者（パトカー）
    "theft": "🚔",  # 窃盗
    "unknown": "🔴"  # フォールバック（種類が特定できない場合）
}

# 緊急事案の優先度（数値が小さいほど優先度が高い）
EMERGENCY_PRIORITY = {
    "fire": 1,  # 最優先
    "weapon": 2,
    "medical_emergency": 3,
    "violence": 4,
    "injured_person": 5,
    "suspicious_person": 6,
    "theft": 7  # 最低優先度
}

# 緊急事案の種類ごとの色
EMERGENCY_COLORS = {
    "fire": "#d32f2f",  # 赤
    "weapon": "#d32f2f",  # 赤
    "violence": "#d32f2f",  # 赤
    "medical_emergency": "#d32f2f",  # 赤
    "injured_person": "#ff9800",  # オレンジ
    "suspicious_person": "#ff9800",  # オレンジ
    "theft": "#fbc02d",  # 黄色
    "unknown": "#d32f2f"  # 赤（フォールバック）
}


# 医療用語（症状名・疾患名）に含まれる「炎」を除外するためのリスト
MEDICAL_TERMS_WITH_EN = [
    '口内炎', '胃炎', '腸炎', '胃腸炎', '膀胱炎', '腎盂腎炎', '尿道炎', '前立腺炎',
    '結膜炎', '咽頭炎', '喉頭炎', '扁桃炎', '副鼻腔炎', '中耳炎', '外耳炎',
    '関節炎', 'リウマチ性関節炎', '腱鞘炎', '滑液包炎',
    '皮膚炎', '接触皮膚炎', 'アトピー性皮膚炎', '脂漏性皮膚炎',
    '膵炎', '肝炎', '胆嚢炎', '胆管炎',
    '肺炎', '気管支炎', '胸膜炎',
    '髄膜炎', '脳炎', '脊髄炎',
    '子宮内膜炎', '卵管炎', '卵巣炎', '腟炎',
    '前立腺炎', '精巣上体炎',
    '虫垂炎', '大腸炎', '直腸炎',
    '甲状腺炎', 'リンパ節炎',
    '歯肉炎', '歯周炎', '舌炎',
    '角膜炎', '強膜炎', 'ぶどう膜炎',
    '心膜炎', '心内膜炎', '心筋炎',
    '静脈炎', '動脈炎', '血管炎',
    '骨髄炎', '骨膜炎',
    '筋炎', '多発性筋炎',
    '神経炎', '多発性神経炎',
    'リンパ管炎', '蜂窩織炎',
    '炎症', '炎症性', '抗炎症'
]

# 誤検知を防ぐための除外パターン（医療相談の文脈）
MEDICAL_CONSULTATION_INDICATORS = [
    # 医療相談を示す表現
    '症状', '症状が', '症状を', '症状は', '症状の', '症状について',
    '市販薬', '薬', '薬を', '薬が', '薬の', '薬について',
    '処方薬', '処方薬の', '処方薬を', '処方薬が',
    '副作用', '副作用で', '副作用が', '副作用の', '副作用を',
    '相談', '相談したい', '相談です', '相談があります',
    '探しています', '欲しい', 'おすすめ', '教えて',
    '診断', '診断名', '診断が', '診断を',
    '治療', '治療中', '治療の', '治療を',
    '持病', '既往症', '既往歴', '基礎疾患',
    '医師', '医者', '病院', 'クリニック',
    '受診', '受診した', '受診しています',
    '服用', '服用中', '服用している', '服用しています',
    '飲んで', '飲んでいる', '飲んでいます',
    'できました', 'できた', 'できています',
    'なりました', 'なった', 'なっています',
    'あります', 'ある', 'ありました',
    # 症状報告の表現（医療相談の文脈として扱う）
    '出ました', '出ています', '出た', '出る',
    'しました', 'しています', 'した', 'する',
    'なりました', 'なっています', 'なった', 'なる',
    'できました', 'できています', 'できた', 'できる',
]

# 一般的な表現（緊急事案ではない）
COMMON_EXPRESSIONS_TO_EXCLUDE = [
    # 時間・曜日
    '火曜日', '火曜', '火曜日に', '火曜日の',
    # 一般的な動作
    '火を使う', '火をつける', '火を消す',
    # 比喩的表現
    '血が出る', '鼻血', '鼻血が出る', '鼻血が出た', '鼻血が出ました',
    '歯茎から血', '歯茎から出血', '歯茎の出血',
    '生理の出血', '生理出血', '月経出血',
    # 医療相談の文脈
    '血圧', '血糖値', '血中', '血液',
    # その他
    '煙草', 'たばこ', 'タバコ', '喫煙',
]

def detect_store_emergency(user_text: str) -> Optional[Dict]:
    """
    緊急事案（不審者、傷病人、刃物など）を検出
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        検出された場合: {
            "is_emergency": True,
            "emergency_types": List[str],  # 検出された緊急事案の種類のリスト
            "primary_type": str,  # 優先度が最も高い種類
            "detected_keywords": List[str],  # 検出されたキーワード
            "icon": str,  # アイコン
            "color": str,  # 色
            "priority_score": int  # 優先度スコア
        }
        検出されなかった場合: None
    """
    logger.info(f"🔍 緊急事案検出開始: {user_text}")
    user_text_lower = user_text.lower()
    detected_types = []
    detected_keywords = []
    
    # 医療相談の文脈かどうかをチェック（誤検知を防ぐため）
    is_medical_consultation = any(indicator in user_text for indicator in MEDICAL_CONSULTATION_INDICATORS)
    
    # 各緊急事案の種類をチェック
    for emergency_type, keywords in EMERGENCY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in user_text_lower:
                # 誤検知を防ぐためのチェック
                should_exclude = False
                keyword_index = user_text_lower.find(keyword)
                
                # キーワードの前後を確認（最大30文字）
                start = max(0, keyword_index - 30)
                end = min(len(user_text), keyword_index + len(keyword) + 30)
                context = user_text[start:end]
                context_lower = context.lower()
                
                # 1. 医療用語（症状名・疾患名）に含まれる「炎」を除外
                if keyword == "炎" or keyword == "炎が" or keyword == "炎を" or keyword == "炎が出ている" or keyword == "炎が出ています":
                    # 医療用語が文脈内に含まれているかチェック
                    for medical_term in MEDICAL_TERMS_WITH_EN:
                        if medical_term in context:
                            # 医療用語が見つかった場合、その位置を確認
                            medical_term_index_in_context = context.find(medical_term)
                            keyword_index_in_context = keyword_index - start
                            
                            # 「炎」が医療用語の一部として使われている場合
                            medical_term_en_index = medical_term.find('炎')
                            if medical_term_en_index != -1:
                                # 医療用語内の「炎」の位置
                                medical_term_en_pos = medical_term_index_in_context + medical_term_en_index
                                # 検出された「炎」の位置との距離が近い場合（5文字以内）
                                if abs(keyword_index_in_context - medical_term_en_pos) <= 5:
                                    should_exclude = True
                                    logger.info(f"🔍 医療用語として除外: {medical_term} (keyword: {keyword})")
                                    break
                
                # 2. 一般的な表現を除外
                if not should_exclude:
                    for common_expr in COMMON_EXPRESSIONS_TO_EXCLUDE:
                        if common_expr in context:
                            should_exclude = True
                            logger.info(f"🔍 一般的な表現として除外: {common_expr} (keyword: {keyword})")
                            break
                
                # 2.5. 「車を」「車が」が「救急車を」「救急車が」の一部として使われている場合は除外
                if not should_exclude and (keyword == "車を" or keyword == "車が"):
                    # 「救急車」が文脈内に含まれているかチェック
                    if "救急車" in context:
                        should_exclude = True
                        logger.info(f"🔍 救急車の一部として除外: {keyword}")
                
                # 3. 医療相談の文脈で、特定のキーワードを除外
                if not should_exclude and is_medical_consultation:
                    # 医療相談の文脈では、以下のキーワードを除外
                    medical_consultation_exclude_keywords = [
                        '血', '血が', '血を', '血の', '出血', '出血が', '出血を',
                        '救急車', '救急車を', '救急車が', '救急車が必要', '救急車を呼ぶ', '救急車を呼ぶべき',
                        '救急', '119', '119番',
                    ]
                    if keyword in medical_consultation_exclude_keywords:
                        # 医療相談の文脈で、症状や相談内容として使われている場合は除外
                        should_exclude = True
                        logger.info(f"🔍 医療相談の文脈として除外: {keyword}")
                    
                    # 「血が出ている」系のキーワードは、自分の症状として使われている場合は除外
                    # ただし、「血が出ている人」のように他人の症状として使われている場合は検出
                    if keyword == "血が出ている" or keyword == "血が出た" or keyword == "血が":
                        # 「人」が含まれていない場合は自分の症状として除外
                        # また、「鼻血」「歯茎から血」などの医療用語が含まれている場合も除外
                        # さらに、症状報告の表現（「出ました」「出ています」など）が含まれている場合も除外
                        medical_blood_terms = ['鼻血', '歯茎', '生理', '月経', '出血', '症状', '副作用', '処方薬', '薬']
                        symptom_report_indicators = ['出ました', '出ています', '出た', 'できました', 'できています', 'できた']
                        has_medical_context = any(term in context for term in medical_blood_terms)
                        has_symptom_report = any(indicator in user_text for indicator in symptom_report_indicators)
                        if "人" not in context or has_medical_context or has_symptom_report:
                            should_exclude = True
                            logger.info(f"🔍 医療相談の文脈として除外: {keyword} (自分の症状または医療用語)")
                    
                    # 「助けて」系のキーワードは、相談の文脈がある場合のみ除外
                    if keyword == '助けて' or keyword == '助けてください' or keyword == '助けを' or keyword == '助けが必要':
                        # 相談の文脈を示す語（「相談」「教えて」「どうすれば」など）が含まれているかチェック
                        consultation_context_words = ['相談', '教えて', 'どうすれば', 'どうしたら', 'すべきか', 'べきか', 'かどうか', 'か教えて', 'どうしたらいい', 'どうすればいい']
                        has_consultation_context = any(word in user_text for word in consultation_context_words)
                        if has_consultation_context:
                            # 相談の文脈がある場合は除外
                            should_exclude = True
                            logger.info(f"🔍 医療相談の文脈として除外: {keyword} (相談の文脈あり)")
                        # 相談の文脈がない場合は緊急事案として扱う（should_excludeはFalseのまま）
                
                if should_exclude:
                    continue  # 除外する場合はスキップ
                
                if emergency_type not in detected_types:
                    detected_types.append(emergency_type)
                detected_keywords.append(keyword)
                logger.info(f"🚨 緊急事案キーワード検出: {emergency_type} - {keyword}")
    
    if not detected_types:
        logger.info(f"🔍 緊急事案検出なし: {user_text}")
        return None
    
    # 優先度が最も高い種類を決定
    primary_type = min(detected_types, key=lambda x: EMERGENCY_PRIORITY.get(x, 999))
    
    return {
        "is_emergency": True,
        "emergency_types": detected_types,
        "primary_type": primary_type,
        "detected_keywords": detected_keywords,
        "icon": EMERGENCY_ICONS.get(primary_type, EMERGENCY_ICONS["unknown"]),
        "color": EMERGENCY_COLORS.get(primary_type, EMERGENCY_COLORS["unknown"]),
        "priority_score": EMERGENCY_PRIORITY.get(primary_type, 999)
    }


def generate_emergency_response(emergency_type: str, language: str = 'ja') -> Dict[str, str]:
    """
    緊急事案応答を生成（構造化されたHTML）
    メッセージの順序: 1. 安全確保・避難、2. スタッフへの連絡、3. 警察への連絡
    
    Args:
        emergency_type: 緊急事案の種類
        language: 言語コード（'ja', 'en', 'ko', 'zh'）
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    # 緊急事案の種類ごとのヘッダーメッセージ
    # 情報提供者向け（火災、武器、暴力、不審者）：ユーザーは目撃者なので「安全を最優先にしてください。」
    # 被害者・当事者向け（医療緊急、傷病人、窃盗、不明）：親切で支援的なメッセージ「お近くのスタッフにご連絡ください」
    emergency_headers = {
        'ja': {
            'fire': '安全を最優先にしてください。',  # 情報提供者向け
            'weapon': '安全を最優先にしてください。',  # 情報提供者向け
            'violence': '安全を最優先にしてください。',  # 情報提供者向け
            'suspicious_person': '安全を最優先にしてください。',  # 情報提供者向け
            'medical_emergency': 'お近くのスタッフにご連絡ください',  # 被害者・当事者向け
            'injured_person': 'お近くのスタッフにご連絡ください',  # 被害者・当事者向け
            'theft': 'お近くのスタッフにご連絡ください',  # 被害者・当事者向け
            'unknown': 'お近くのスタッフにご連絡ください'  # 被害者・当事者向け
        },
        'en': {
            'fire': 'Safety is the top priority.',  # 情報提供者向け
            'weapon': 'Safety is the top priority.',  # 情報提供者向け
            'violence': 'Safety is the top priority.',  # 情報提供者向け
            'suspicious_person': 'Safety is the top priority.',  # 情報提供者向け
            'medical_emergency': 'Please contact a nearby staff member',  # 被害者・当事者向け
            'injured_person': 'Please contact a nearby staff member',  # 被害者・当事者向け
            'theft': 'Please contact a nearby staff member',  # 被害者・当事者向け
            'unknown': 'Please contact a nearby staff member'  # 被害者・当事者向け
        },
        'ko': {
            'fire': '안전 확보를 최우선으로 하세요.',  # 情報提供者向け
            'weapon': '안전 확보를 최우선으로 하세요.',  # 情報提供者向け
            'violence': '안전 확보를 최우선으로 하세요.',  # 情報提供者向け
            'suspicious_person': '안전 확보를 최우선으로 하세요.',  # 情報提供者向け
            'medical_emergency': '가까운 직원에게 연락하세요',  # 被害者・当事者向け
            'injured_person': '가까운 직원에게 연락하세요',  # 被害者・当事者向け
            'theft': '가까운 직원에게 연락하세요',  # 被害者・当事者向け
            'unknown': '가까운 직원에게 연락하세요'  # 被害者・当事者向け
        },
        'zh': {
            'fire': '安全是最优先的。',  # 情報提供者向け
            'weapon': '安全是最优先的。',  # 情報提供者向け
            'violence': '安全是最优先的。',  # 情報提供者向け
            'suspicious_person': '安全是最优先的。',  # 情報提供者向け
            'medical_emergency': '请联系附近的员工',  # 被害者・当事者向け
            'injured_person': '请联系附近的员工',  # 被害者・当事者向け
            'theft': '请联系附近的员工',  # 被害者・当事者向け
            'unknown': '请联系附近的员工'  # 被害者・当事者向け
        }
    }
    
    # 多言語対応のメッセージテンプレート
    messages = {
        'ja': {
            'title': '緊急事案が検出されました',
            'safety_first': '安全確保を最優先にしてください',
            'safety_section': {
                'title': '安全確保・避難',
                'items': [
                    'すぐに安全な場所に避難してください',
                    '落ち着いて行動してください'
                ]
            },
            'staff_section': {
                'title': 'スタッフへの連絡',
                'items': [
                    '店内のスタッフにすぐに連絡してください'
                ]
            },
            'police_section': {
                'title': '警察への連絡',
                'items': [
                    '緊急の場合は、すぐに110番（警察）に連絡してください',
                    '不審者や暴力行為がある場合は、すぐに110番に連絡してください'
                ]
            }
        },
        'en': {
            'title': 'Emergency Detected',
            'safety_first': 'Safety is the top priority',
            'safety_section': {
                'title': 'Safety & Evacuation',
                'items': [
                    'Evacuate to a safe place immediately',
                    'Stay calm and act calmly'
                ]
            },
            'staff_section': {
                'title': 'Contact Staff',
                'items': [
                    'Contact store staff immediately'
                ]
            },
            'police_section': {
                'title': 'Contact Police',
                'items': [
                    'In case of emergency, call 110 (police) immediately',
                    'If there are suspicious persons or acts of violence, call 110 immediately'
                ]
            }
        },
        'ko': {
            'title': '긴급 상황 감지됨',
            'safety_first': '안전 확보를 최우선으로 하세요',
            'safety_section': {
                'title': '안전 확보 및 대피',
                'items': [
                    '즉시 안전한 장소로 대피하세요',
                    '침착하게 행동하세요'
                ]
            },
            'staff_section': {
                'title': '직원 연락',
                'items': [
                    '매장 직원에게 즉시 연락하세요'
                ]
            },
            'police_section': {
                'title': '경찰 연락',
                'items': [
                    '긴급한 경우 즉시 110번(경찰)에 연락하세요',
                    '의심스러운 사람이나 폭력 행위가 있는 경우 즉시 110번에 연락하세요'
                ]
            }
        },
        'zh': {
            'title': '检测到紧急情况',
            'safety_first': '安全是最优先的',
            'safety_section': {
                'title': '安全与疏散',
                'items': [
                    '立即疏散到安全的地方',
                    '保持冷静，冷静行动'
                ]
            },
            'staff_section': {
                'title': '👥 联系员工',
                'items': [
                    '立即联系店内员工'
                ]
            },
            'police_section': {
                'title': '联系 警察',
                'items': [
                    '紧急情况下，请立即拨打110（警察）',
                    '如有可疑人员或暴力行为，请立即拨打110'
                ]
            }
        }
    }
    
    # 言語に応じたメッセージを取得
    msg = messages.get(language, messages['ja'])
    
    # 緊急事案の種類に応じたヘッダーメッセージを取得
    header_messages = emergency_headers.get(language, emergency_headers['ja'])
    header_text = header_messages.get(emergency_type, header_messages['unknown'])
    
    # 緊急事案の種類ごとの追加メッセージ
    type_specific_messages = {
        'suspicious_person': {
            'ja': {
                'safety': ['不審者から距離を取ってください'],
                'staff': ['不審者の特徴や行動をスタッフに伝えてください'],
                'police': ['不審者の特徴や行動を警察に伝えてください']
            }
        },
        'injured_person': {
            'ja': {
                'safety': ['傷病者の近くにいる場合は、安全を確保してください'],
                'staff': ['救急車を呼ぶ必要がある場合は、スタッフに伝えてください'],
                'police': []
            }
        },
        'weapon': {
            'ja': {
                'safety': ['刃物から距離を取ってください', '安全な場所に避難してください'],
                'staff': [],
                'police': ['刃物を持っている人がいる場合は、すぐに110番に連絡してください']
            }
        },
        'violence': {
            'ja': {
                'safety': ['暴力から距離を取ってください', '安全な場所に避難してください'],
                'staff': [],
                'police': ['暴力行為が発生している場合は、すぐに110番に連絡してください']
            }
        },
        'fire': {
            'ja': {
                'safety': ['すぐに避難してください', '煙を吸わないようにしてください'],
                'staff': [],
                'police': ['火災の場合は、119番（消防）に連絡してください']
            }
        },
        'theft': {
            'ja': {
                'safety': ['証拠を保護してください'],
                'staff': ['盗まれた物品や犯人の特徴をスタッフに伝えてください'],
                'police': ['窃盗の場合は、110番に連絡してください']
            }
        },
        'medical_emergency': {
            'ja': {
                'safety': ['応急処置が可能な場合は、安全に配慮して行ってください'],
                'staff': ['救急車を呼ぶ必要がある場合は、スタッフに伝えてください'],
                'police': []
            }
        }
    }
    
    # 種類ごとの追加メッセージを取得
    type_msg = type_specific_messages.get(emergency_type, {}).get(language, {})
    
    # 安全確保セクションのアイテムに追加
    safety_items = msg['safety_section']['items'].copy()
    if type_msg.get('safety'):
        safety_items.extend(type_msg['safety'])
    
    # スタッフセクションのアイテムに追加
    staff_items = msg['staff_section']['items'].copy()
    if type_msg.get('staff'):
        staff_items.extend(type_msg['staff'])
    
    # 警察セクションのアイテムに追加
    police_items = msg['police_section']['items'].copy()
    if type_msg.get('police'):
        police_items.extend(type_msg['police'])
    
    # アイコンを取得
    icon = EMERGENCY_ICONS.get(emergency_type, EMERGENCY_ICONS["unknown"])
    
    # シンプルなメッセージを生成
    simple_message = f"""{icon} {msg['title']}

{msg['safety_first']}

【{msg['safety_section']['title']}】
{chr(10).join(f"・{item}" for item in safety_items)}

【{msg['staff_section']['title']}】
{chr(10).join(f"・{item}" for item in staff_items)}

【{msg['police_section']['title']}】
{chr(10).join(f"・{item}" for item in police_items)}
"""
    
    # 構造化されたHTMLを生成（モダンなデザイン、読みやすさ優先）
    structured_html = f"""
<div class="emergency-response-modern">
    <div class="emergency-header">
        {header_text}
    </div>
    
    <div class="emergency-content">
        <!-- 1. 安全確保・避難 -->
        <div class="emergency-card safety-card">
            <div class="card-header safety-header">
                <span class="card-icon">🛡️</span>
                <h3 class="card-title">{msg['safety_section']['title']}</h3>
            </div>
            <div class="card-body">
                <ul class="card-list">
                    {''.join(f'<li><span class="list-marker">▶</span>{item}</li>' for item in safety_items)}
                </ul>
            </div>
        </div>
        
        <!-- 2. スタッフへの連絡 -->
        <div class="emergency-card staff-card">
            <div class="card-header staff-header">
                <span class="card-icon">👥</span>
                <h3 class="card-title">{msg['staff_section']['title']}</h3>
            </div>
            <div class="card-body">
                <ul class="card-list">
                    {''.join(f'<li><span class="list-marker">▶</span>{item}</li>' for item in staff_items)}
                </ul>
            </div>
        </div>
        
        <!-- 3. 警察への連絡 -->
        <div class="emergency-card police-card">
            <div class="card-header police-header">
                <span class="card-icon">🚔</span>
                <h3 class="card-title">{msg['police_section']['title']}</h3>
            </div>
            <div class="card-body">
                <ul class="card-list">
                    {''.join(f'<li><span class="list-marker">▶</span>{item}</li>' for item in police_items)}
                </ul>
            </div>
        </div>
    </div>
</div>
"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def handle_store_emergency(
    user_text: str,
    client: Optional[OpenAI] = None,
    triage_result: Optional[Dict] = None,
    language: str = 'ja'
) -> Optional[Dict]:
    """
    緊急事案を検出し、応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス（オプション、現在は未使用）
        triage_result: LLMトリアージ結果（オプション）
    
    Returns:
        緊急事案が検出された場合: {
            "is_emergency": True,
            "emergency_type": str,  # 主要な緊急事案の種類
            "emergency_types": List[str],  # 検出されたすべての種類
            "detected_keywords": List[str],
            "icon": str,
            "color": str,
            "priority_score": int,
            "response": {
                "simple_message": str,
                "structured_html": str
            }
        }
        検出されなかった場合: None
    """
    logger.info(f"🔍 handle_store_emergency呼び出し: {user_text}")
    # 緊急事案を検出
    detection_result = detect_store_emergency(user_text)
    
    if not detection_result:
        logger.info(f"🔍 緊急事案検出なし（handle_store_emergency）: {user_text}")
        return None
    
    # 主要な緊急事案の種類を取得
    primary_type = detection_result["primary_type"]
    
    # 応答を生成（言語設定を使用）
    response = generate_emergency_response(primary_type, language)
    
    logger.info(f"🚨 緊急事案検出: {primary_type}, 種類: {detection_result['emergency_types']}")
    
    return {
        "is_emergency": True,
        "emergency_type": primary_type,
        "emergency_types": detection_result["emergency_types"],
        "detected_keywords": detection_result["detected_keywords"],
        "icon": detection_result["icon"],
        "color": detection_result["color"],
        "priority_score": detection_result["priority_score"],
        "response": response,
        "language": language
    }

