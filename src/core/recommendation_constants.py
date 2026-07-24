"""
ルールベース医薬品推奨システム用の定数・データ構造定義

rule_based_recommendation.py から分離（SRP改善）
"""

import re
import logging
from typing import Dict

# キーワードリストのインポート
try:
    from config.keywords import URGENT_SYMPTOM_KEYWORDS
except ImportError:
    URGENT_SYMPTOM_KEYWORDS = []
    logging.warning("config/keywords.pyが見つかりません。URGENT_SYMPTOM_KEYWORDSを使用できません。")

# スコアリングウェイト（強化版）
try:
    from src.security.enhanced_safety_checker import enhanced_scoring_weights
    SCORING_WEIGHTS = enhanced_scoring_weights()
except ImportError:
    SCORING_WEIGHTS = {}
    logging.warning("enhanced_safety_checkerが見つかりません。SCORING_WEIGHTSは空です。")

DEFAULT_ADULT_AGE = 20

PEDIATRIC_KEYWORDS = [
    "小児",
    "小児用",
    "こども",
    "子ども",
    "子供",
    "キッズ",
    "ジュニア",
    "ベビー",
    "ドライシロップ",  # ドライシロップは小児向け形状
]

PEDIATRIC_USAGE_KEYWORDS = [
    "坐剤",
    "座剤",
    "坐薬",
    "座薬"
]

# 重症疑い症状（赤旗：Red Flag）- 即座にエスカレーション
RED_FLAG_SYMPTOMS = {
    "呼吸困難": ["呼吸が苦しい", "息苦しい", "呼吸困難", "息ができない", "息切れ"],
    "高熱": ["38.5度以上", "39度", "40度", "高熱", "熱が下がらない"],
    "胸痛": ["胸が痛い", "胸の痛み", "胸部痛", "胸が締め付けられる"],
    "心臓の痛み": [
        "心臓が痛い", "心臓部分が痛い", "心臓が痛む",
        "心臓部が痛い", "心臓のあたりが痛い", "心臓付近が痛い"
    ],
    "動悸・不整脈": [
        "動悸", "動悸が止まらない", "ドキドキが止まらない",
        "脈が飛ぶ", "不整脈", "脈が速い", "脈が遅い", "脈が不規則"
    ],
    "意識障害": ["意識がもうろう", "意識がない", "気を失う", "意識不明", "ぼーっとする"],
    "激しい頭痛": ["激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛", "頭が割れる", "耐えられない頭痛"],
    "血便": ["血便", "便に血が混じる", "黒い便", "タール便"],
    "喀血": ["血を吐く", "喀血", "吐血"],
    "激しい腹痛": ["激しい腹痛", "お腹が痛くて動けない", "耐えられない腹痛"],
    "顔面麻痺": ["顔面麻痺", "顔が動かない", "口が曲がる", "顔の半分が動かない"],
    "手足の麻痺": ["手足の麻痺", "手足が動かない", "力が入らない", "しびれが続く"],
    "持続する嘔吐": ["持続する嘔吐", "何度も吐く", "止まらない嘔吐", "嘔吐が続く"]
}

# URGENT_SYMPTOM_KEYWORDSと統合（緊急症状の拡張）
if URGENT_SYMPTOM_KEYWORDS:
    if "緊急症状" not in RED_FLAG_SYMPTOMS:
        RED_FLAG_SYMPTOMS["緊急症状"] = []
    for keyword in URGENT_SYMPTOM_KEYWORDS:
        if keyword not in RED_FLAG_SYMPTOMS["緊急症状"]:
            RED_FLAG_SYMPTOMS["緊急症状"].append(keyword)

# 医師受診推奨条件
# 妊娠の可能性を示す症状辞書
PREGNANCY_SYMPTOMS = {
    "生理の遅れ": {
        "weight": 3.0,
        "synonyms": [
            "生理が遅れている", "月経が来ない", "生理が来ない",
            "予定日を過ぎた", "いつもより遅い", "生理が遅い",
            "月経遅延", "生理が来ていない",
            "月経が遅れている", "生理予定日を過ぎた"
        ]
    },
    "つわり": {
        "weight": 2.0,
        "synonyms": ["つわり", "悪阻", "吐き気", "嘔吐", "匂いに敏感", "匂いが気になる"]
    },
    "だるさ": {
        "weight": 1.0,
        "synonyms": ["だるい", "倦怠感", "疲れやすい", "体がだるい", "全身倦怠感"]
    },
    "眠気": {
        "weight": 1.0,
        "synonyms": ["眠い", "眠気", "だるい", "眠たい", "眠気が強い", "いつも眠い"]
    },
    "胸の張り": {
        "weight": 1.5,
        "synonyms": ["胸が張る", "胸の張り", "乳房の張り", "胸が痛い", "胸が敏感", "乳房が痛い"]
    },
    "頻尿": {
        "weight": 1.0,
        "synonyms": ["頻尿", "トイレが近い", "おしっこが近い", "尿が近い", "トイレに行く回数が多い"]
    },
    "便秘": {
        "weight": 0.5,
        "synonyms": ["便秘", "便が出ない", "便通がない"]
    },
    "微熱": {
        "weight": 0.5,
        "synonyms": ["微熱", "微かな熱", "微熱が続く"]
    },
    "情緒不安定": {
        "weight": 0.5,
        "synonyms": ["情緒不安定", "イライラ", "不安", "気分が変わりやすい", "感情の起伏が激しい"]
    },
    "おりものの変化": {
        "weight": 1.0,
        "synonyms": ["おりもの", "おりものが増えた", "おりものが変わった", "おりものの量が増えた", "おりものの色が変わった"]
    },
    "着床出血": {
        "weight": 1.5,
        "synonyms": ["少量の出血", "着床出血", "軽い出血", "茶色いおりもの", "薄い出血", "軽い生理のような出血"]
    }
}

# 女性特有の症状辞書（性別自動判定用）
FEMALE_SPECIFIC_SYMPTOMS = {
    "つわり": {
        "confidence": "high",
        "synonyms": ["つわり", "悪阻", "吐き気", "嘔吐", "匂いに敏感", "匂いが気になる"]
    },
    "生理の遅れ": {
        "confidence": "high",
        "synonyms": [
            "生理が遅れている", "月経が来ない", "生理が来ない",
            "予定日を過ぎた", "いつもより遅い", "生理が遅い",
            "月経遅延", "生理不順", "月経不順", "生理が来ていない",
            "月経が遅れている", "生理予定日を過ぎた",
            "最近生理が遅れています", "最近生理が遅れている", "最近生理が遅い",
            "最近月経が遅れています", "最近月経が遅れている", "最近月経が遅い",
            "生理が遅れています", "月経が遅れています"
        ]
    },
    "生理痛": {
        "confidence": "high",
        "synonyms": ["生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理痛が続く"]
    },
    "月経不順": {
        "confidence": "high",
        "synonyms": ["月経不順", "生理不順", "月経異常", "生理周期が乱れている"]
    },
    "更年期症状": {
        "confidence": "high",
        "synonyms": ["更年期", "更年期障害", "ホットフラッシュ", "のぼせ", "ほてり"]
    },
    "胸の張り": {
        "confidence": "high",
        "synonyms": ["胸が張る", "胸の張り", "乳房の張り", "胸が痛い", "胸が敏感", "乳房が痛い"]
    },
    "着床出血": {
        "confidence": "high",
        "synonyms": ["少量の出血", "着床出血", "軽い出血", "茶色いおりもの", "薄い出血", "軽い生理のような出血"]
    },
    "おりものの変化": {
        "confidence": "high",
        "synonyms": ["おりもの", "おりものが増えた", "おりものが変わった", "おりものの量が増えた", "おりものの色が変わった"]
    }
}

DOCTOR_REFERRAL_CONDITIONS = {
    "pregnancy": {
        "description": "妊娠中",
        "message": "妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
        "priority": "critical"
    },
    "pregnancy_possible": {
        "description": "妊娠の可能性",
        "message": "妊娠の可能性があります。医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
        "priority": "critical"
    },
    "breastfeeding": {
        "description": "授乳中",
        "message": "授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
        "priority": "critical"
    },
    "symptoms_over_week": {
        "description": "症状が1週間以上続いている",
        "message": "症状が1週間以上続いている場合は、医師の診断を受けることをお勧めします。",
        "priority": "high"
    },
    "severe_symptoms": {
        "description": "重症疑い症状",
        "message": "重症の疑いがある症状がみられます。速やかに医師の診断を受けてください。",
        "priority": "critical"
    },
    "age_under_7": {
        "description": "7歳未満",
        "message": "7歳未満のお子様は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
        "priority": "critical"
    }
}

# 禁忌チェックルール（強化版）
CONTRAINDICATION_RULES = {
    "年齢制限": {
        "乳児": (0, 3),
        "幼児": (3, 7),
        "小児": (7, 15),
        "成人": (15, 65),
        "高齢者": (65, 150)
    },
    "妊娠中": {
        "風邪薬": "要注意",
        "解熱鎮痛薬": "禁忌（特にNSAIDs）",
        "鼻炎用薬": "要注意",
        "胃腸薬": "要注意",
        "外用薬": "要注意",
        "目薬": "要注意"
    },
    "授乳中": {
        "風邪薬": "要注意",
        "解熱鎮痛薬": "要注意",
        "鼻炎用薬": "要注意",
        "胃腸薬": "要注意",
        "外用薬": "要注意",
        "目薬": "要注意"
    }
}

# リスク成分リスト（減点対象、詳細症状がない場合は注意喚起）
RISK_INGREDIENTS_EXCLUDE = {
    "ヒマシ油": {
        "name": "ヒマシ油",
        "aliases": ["ヒマシ油", "加香ヒマシ油", "カストル油"],
        "penalty_score": -0.4,
        "warning": "ヒマシ油が含まれています。腸の炎症、激しい腹痛、吐き気・嘔吐、妊娠中の方は使用できません。使用前に必ず薬剤師または登録販売者にご相談ください。"
    },
    "センナ": {
        "name": "センナ",
        "aliases": ["センナ", "センノシド", "センナエキス"],
        "penalty_score": -0.3,
        "warning": "センナが含まれています。長期連用や妊娠中は避けてください。使用は短期間に限り、症状が続く場合は医師にご相談ください。"
    },
    "アロエエキス": {
        "name": "アロエエキス",
        "aliases": ["アロエエキス", "アロエ", "アロエエキス末"],
        "penalty_score": -0.3,
        "warning": "アロエエキスが含まれています。妊娠中は使用できません。長期連用は避けてください。"
    },
    "ビサコジル": {
        "name": "ビサコジル",
        "aliases": ["ビサコジル", "ピコスルファート"],
        "penalty_score": -0.25,
        "warning": "ビサコジルが含まれています。妊娠中・授乳中、15歳未満の方は使用前に医師にご相談ください。"
    },
    "アスピリン": {
        "name": "アスピリン",
        "aliases": ["アスピリン", "アセチルサリチル酸", "ASA"],
        "penalty_score": -0.5,
        "warning": "アスピリンが含まれています。インフルエンザや水痘の患者、特に小児ではライ症候群のリスクがあるため使用できません。"
    },
    "トラマドール": {
        "name": "トラマドール",
        "aliases": ["トラマドール", "トラマドール塩酸塩"],
        "penalty_score": -0.4,
        "warning": "トラマドールが含まれています。依存性の可能性があるため、長期連用は避けてください。15歳未満、妊娠中・授乳中の方は使用できません。"
    },
}

# 下痢止め成分インジケーター（腹痛単独時には慎重に扱う）
ANTIDIARRHEAL_INGREDIENTS = [
    "ロートエキス",
    "ロートエキス散",
    "タンニン酸アルブミン",
    "タンニン酸ベルベリン",
    "ベルベリン",
    "ベルベリン塩酸塩",
    "ベルベリン硫酸塩",
    "ロペラミド",
    "ロペラミド塩酸塩",
    "ブチルスコポラミン",
    "ブチルスコポラミン臭化物"
]

ANTIDIARRHEAL_KEYWORDS = [
    "止瀉薬",
    "止瀉剤",
    "下痢止め",
    "下痢を抑える",
    "止瀉作用",
    "止瀉効果"
]

MIN_SYMPTOM_MATCH_SINGLE = 0.35
MIN_SYMPTOM_MATCH_MULTI = 0.2

# Phase 3 (p3-headache-reco): 単独症状で OTC 推奨を慎重に保留する症状（変更時はテスト必須）
CAUTION_DEFER_SINGLE_SYMPTOMS = frozenset({
    "めまい",
})

# 特殊用途医薬品パターン（効能効果が特定の用途に限定されている）
SPECIFIC_USE_PATTERNS = {
    "食あたり": {
        "pattern": re.compile(r"食あたり|食中毒|食中り", re.IGNORECASE),
        "required_symptoms": ["下痢", "腹痛", "吐き気"],
        "medicine_types": ["胃腸薬"]
    },
    "便秘限定": {
        "pattern": re.compile(r"^便秘[。、]?$|便秘のみ|便秘だけ", re.IGNORECASE),
        "required_symptoms": ["便秘"],
        "medicine_types": ["胃腸薬"],
        "exclude_symptoms": ["下痢", "腹痛"]
    },
    "腸内容物排除": {
        "pattern": re.compile(r"腸内容物の急速な排除|腸管洗浄|検査前処置", re.IGNORECASE),
        "required_symptoms": [],
        "medicine_types": ["胃腸薬"],
        "strict": True
    }
}

# 特殊用途医薬品の除外キーワード（一般的な症状には不適切な特殊用途医薬品）
SPECIFIC_USE_EXCLUSION_KEYWORDS = {
    "ホルモン": ["ホルモン", "テストステロン", "エストロゲン", "プロゲステロン", "メチルテストステロン"],
    "男性器": ["男性器", "ペニス", "陰茎", "性器", "オットピン", "内股"],
    "女性器": ["女性器", "膣", "おりもの", "デリケートゾーン"],
    "特殊用途": ["勃起", "性機能", "更年期障害", "ホルモン補充", "記憶力減退"]
}

# 複合薬識別パターン（複数の効能を持つ医薬品）
COMPOUND_MEDICINE_INDICATORS = {
    "風邪薬": {
        "patterns": [
            re.compile(r"総合感冒薬|総合かぜ薬|総合感冒|かぜ薬総合", re.IGNORECASE),
            re.compile(r"解熱.*鎮痛.*鎮咳|解熱.*鎮痛.*去痰", re.IGNORECASE),
            re.compile(r"風邪薬.*複数|複数の.*風邪症状", re.IGNORECASE)
        ],
        "required_symptoms_count": 2
    },
    "総合胃腸薬": {
        "patterns": [
            re.compile(r"総合胃腸薬|胃腸薬総合", re.IGNORECASE),
            re.compile(r"胃痛.*下痢|下痢.*胃痛", re.IGNORECASE)
        ],
        "required_symptoms_count": 2
    }
}

# 部位特異的製品のキーワード辞書
BODY_PART_SPECIFIC_KEYWORDS = {
    "delicate_area": {
        "product_name_keywords": ["カブレーナ", "デリケート", "おりもの", "ナプキン", "性器", "陰部", "局部"],
        "efficacy_keywords": ["おむつかぶれ", "蒸れ", "デリケート部位", "おりもの", "性器", "陰部", "局部", "陰茎"],
        "usage_keywords": ["デリケート部位", "蒸れ", "おりもの", "性器", "陰部", "局部"]
    },
    "scalp": {
        "product_name_keywords": ["頭皮", "フケ", "スカルプ"],
        "efficacy_keywords": ["頭皮", "フケ", "頭のかゆみ"],
        "usage_keywords": ["頭皮", "頭部"]
    },
    "throat": {
        "product_name_keywords": ["のど", "喉", "トローチ"],
        "efficacy_keywords": ["のどの痛み", "喉の痛み"],
        "usage_keywords": ["のど", "喉"]
    }
}

# 症状カテゴリ間優先表
SYMPTOM_CATEGORY_PENALTY = {
    "発熱": {"風邪薬": -0.5, "解熱鎮痛薬": 0.0, "鼻炎用薬": -0.5},
    "のどの痛み": {"外用薬（のど）": 0.15, "外用薬（皮膚）": 0.10, "解熱鎮痛薬": 0.0, "風邪薬": -0.15, "鼻炎用薬": -0.4},
    "咳": {"風邪薬": -0.2, "解熱鎮痛薬": -0.5, "鼻炎用薬": -0.3},
    "頭痛": {"風邪薬": -0.5, "解熱鎮痛薬": 0.0, "鼻炎用薬": -0.5},
    "筋肉痛": {"風邪薬": -0.5, "外用薬（皮膚）": 0.2, "解熱鎮痛薬": 0.0},
    "鼻水": {"風邪薬": -0.1, "鼻炎用薬": 0.0, "解熱鎮痛薬": -0.5},
    "腹痛": {"胃腸薬": 0.0, "風邪薬": -0.5, "解熱鎮痛薬": -0.5},
    "下痢": {"胃腸薬": 0.0, "風邪薬": -0.5, "解熱鎮痛薬": -0.5},
    "便秘": {"胃腸薬": 0.0, "風邪薬": -0.5, "解熱鎮痛薬": -0.5}
}

# 複数症状の組み合わせによる調整
MULTI_SYMPTOM_COMBINATIONS = {
    frozenset({"のどの痛み", "発熱"}): {"風邪薬": 0.25, "解熱鎮痛薬": 0.0},
    frozenset({"発熱", "咳"}): {"風邪薬": 0.15, "解熱鎮痛薬": -0.1},
    frozenset({"発熱", "鼻水"}): {"風邪薬": 0.15, "解熱鎮痛薬": -0.1},
    frozenset({"咳", "痰"}): {"風邪薬": 0.18, "解熱鎮痛薬": -0.1},
    frozenset({"鼻水", "鼻づまり"}): {"鼻炎用薬": 0.2, "風邪薬": 0.1},
    frozenset({"のどの痛み", "咳"}): {"風邪薬": 0.18, "解熱鎮痛薬": -0.1},
    frozenset({"咳", "鼻水"}): {"風邪薬": 0.15, "鼻炎用薬": 0.1},
    frozenset({"頭痛", "発熱"}): {"解熱鎮痛薬": 0.12, "風邪薬": 0.15},
    frozenset({"腹痛", "下痢"}): {"胃腸薬": 0.2, "風邪薬": -0.1},
    frozenset({"吐き気", "腹痛"}): {"胃腸薬": 0.18, "風邪薬": -0.1}
}

# 症状パターンごとの最適化定義
SYMPTOM_PATTERN_OPTIMIZATION = {
    frozenset({"のどの痛み", "発熱"}): {
        "priority_order": ["総合感冒薬（喉向き）", "解熱鎮痛薬", "外用薬（のど）", "葛根湯"],
        "bonuses": {
            "総合感冒薬（喉向き・成分あり）": 0.50,
            "総合感冒薬（喉向き・効能のみ）": 0.40,
            "解熱鎮痛薬": 0.45,
            "外用薬（のど）": 0.45,
            "葛根湯": -0.2
        }
    },
    frozenset({"頭痛", "発熱"}): {"priority_order": ["解熱鎮痛薬", "総合感冒薬"], "bonuses": {"解熱鎮痛薬": 0.15, "総合感冒薬": 0.10}},
    frozenset({"咳", "痰"}): {"priority_order": ["風邪薬（鎮咳去痰薬）", "総合感冒薬"], "bonuses": {"風邪薬": 0.20, "総合感冒薬": 0.10}},
    frozenset({"鼻水", "鼻づまり"}): {"priority_order": ["鼻炎用薬", "総合感冒薬"], "bonuses": {"鼻炎用薬": 0.20, "総合感冒薬": 0.10}},
    frozenset({"胃痛", "胸やけ"}): {"priority_order": ["胃薬", "総合胃腸薬"], "bonuses": {"胃薬": 0.15, "総合胃腸薬": 0.10}},
    frozenset({"便秘"}): {"priority_order": ["便秘薬"], "bonuses": {"便秘薬": 0.15}, "penalties": {"リスク成分（センナ、ヒマシ油）": -0.20}},
    frozenset({"下痢"}): {"priority_order": ["下痢止め薬"], "bonuses": {"下痢止め薬": 0.15}},
    frozenset({"ニキビ"}): {"priority_order": ["外用薬（皮膚）", "内服薬"], "bonuses": {"外用薬（皮膚）": 0.15, "内服薬": 0.15}},
    frozenset({"やけど"}): {"priority_order": ["外用薬（皮膚）のやけど専用薬"], "bonuses": {"外用薬（皮膚）": 0.25}},
    frozenset({"切り傷"}): {"priority_order": ["外用薬（皮膚）の創傷保護剤"], "bonuses": {"外用薬（皮膚）": 0.25}},
    frozenset({"頭痛", "むくみ", "だるさ"}): {"priority_order": ["五苓散", "L-システイン含有医薬品"], "bonuses": {"五苓散": 0.20, "L-システイン含有医薬品": 0.15}},
    frozenset({"吐き気", "胃もたれ", "むかつき"}): {"priority_order": ["生薬配合の胃腸薬・健胃消化薬"], "bonuses": {"生薬配合の胃腸薬": 0.15}},
    frozenset({"頭痛", "むくみ"}): {"priority_order": ["五苓散", "L-システイン含有医薬品"], "bonuses": {"五苓散": 0.20, "L-システイン含有医薬品": 0.15}},
    frozenset({"頭痛", "だるさ"}): {"priority_order": ["五苓散", "L-システイン含有医薬品"], "bonuses": {"五苓散": 0.20, "L-システイン含有医薬品": 0.15}},
    frozenset({"むくみ", "だるさ"}): {"priority_order": ["五苓散", "L-システイン含有医薬品"], "bonuses": {"五苓散": 0.20, "L-システイン含有医薬品": 0.15}},
    frozenset({"頭痛", "吐き気"}): {"priority_order": ["五苓散", "生薬配合の胃腸薬"], "bonuses": {"五苓散": 0.15, "生薬配合の胃腸薬": 0.12}},
    frozenset({"頭痛", "だるさ", "吐き気"}): {"priority_order": ["五苓散", "生薬配合の胃腸薬"], "bonuses": {"五苓散": 0.18, "生薬配合の胃腸薬": 0.12}},
    frozenset({"悪寒", "発熱"}): {"priority_order": ["葛根湯", "総合感冒薬"], "bonuses": {"葛根湯": 0.15, "総合感冒薬": 0.10}},
    frozenset({"月経不順", "イライラ"}): {
        "priority_order": ["加味逍遙散", "命の母ホワイト", "ラムールQ", "ルナエール", "ルナフェミン", "桂枝茯苓丸"],
        "bonuses": {"加味逍遙散": 0.30, "命の母ホワイト": 0.30, "ラムールQ": 0.28, "ルナエール": 0.25, "ルナフェミン": 0.25, "桂枝茯苓丸": 0.25, "解熱鎮痛薬": 0.10}
    },
    frozenset({"月経不順", "冷え症"}): {"priority_order": ["当帰芍薬散"], "bonuses": {"当帰芍薬散": 0.20, "解熱鎮痛薬": 0.10}},
    frozenset({"月経不順", "ニキビ"}): {"priority_order": ["桂枝茯苓丸", "命の母ホワイト"], "bonuses": {"桂枝茯苓丸": 0.20, "命の母ホワイト": 0.20, "解熱鎮痛薬": 0.10}}
}

# 漢方薬が適切なシナリオ（これらの症状がある場合は漢方薬ペナルティを無効化）
# 生理痛・月経不順、二日酔い、頻尿・排尿困難、慢性的な不眠、冷え症、胃腸虚弱、更年期症状
KAMPO_PREFERRED_SYMPTOMS = frozenset([
    # 生理痛・月経不順
    "生理痛", "月経痛", "月経不順", "生理不順", "生理異常", "月経異常", "血の道症", "血の道",
    # 二日酔い（症状パターンは別途 SYMPTOM_PATTERN_OPTIMIZATION で判定）
    "二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔",
    # 頻尿・排尿
    "頻尿", "トイレが近い", "排尿困難", "残尿感", "夜間尿", "尿が近い",
    # 慢性的な不眠
    "不眠", "眠れない", "慢性的な不眠", "長期間の不眠",
    # 冷え症
    "冷え症", "冷え性", "手足の冷え", "しもやけ", "冷え",
    # 胃腸虚弱
    "胃もたれ", "むかつき", "胃腸虚弱", "胃虚弱",
    # 更年期症状
    "更年期", "更年期障害", "のぼせ", "ほてり", "ホットフラッシュ",
])


def _get_normalize_text():
    """scoring_utils.normalize_text を遅延インポート（循環参照回避）"""
    from src.core.scoring_utils import normalize_text
    return normalize_text


# THROAT_SYMPTOM_TOKENS, THROAT_KEYWORD_TOKENS, THROAT_LIQUID_TOKENS は
# normalize_text に依存するため、モジュールロード時に動的に生成
def _build_throat_tokens():
    normalize_text = _get_normalize_text()
    return {
        "THROAT_SYMPTOM_TOKENS": {normalize_text(term) for term in ["のどの痛み", "喉の痛み", "咽頭痛", "のどの不快感", "声がれ"]},
        "THROAT_KEYWORD_TOKENS": {normalize_text(term) for term in ["のど", "喉", "咽頭", "トローチ", "うがい", "うがい薬", "含嗽", "声がれ"]},
        "THROAT_LIQUID_TOKENS": {normalize_text(term) for term in ["シロップ", "液", "内服液", "ドリンク", "鎮咳液", "咳止め液"]},
    }


_throat_tokens = _build_throat_tokens()
THROAT_SYMPTOM_TOKENS = _throat_tokens["THROAT_SYMPTOM_TOKENS"]
THROAT_KEYWORD_TOKENS = _throat_tokens["THROAT_KEYWORD_TOKENS"]
THROAT_LIQUID_TOKENS = _throat_tokens["THROAT_LIQUID_TOKENS"]

# 喉向き総合感冒薬の識別用成分リスト
THROAT_SPECIFIC_INGREDIENTS = [
    "トラネキサム酸", "カンゾウエキス", "グリチルリチン酸",
    "アズレンスルホン酸ナトリウム", "アズレン", "ポビドンヨード"
]

# 胃粘膜保護成分リスト
STOMACH_MUCOSAL_PROTECTANTS = [
    "スクラルファート", "スクラルファート水和物", "アルサノン", "スクラート",
    "テプレノン", "セルベックス", "レバミピド", "ムコスタ", "レバミピド末",
    "エコラビド", "セトラキサート", "セトラキサート塩酸塩", "ノイエル",
    "ゲファルナート", "ゲファニール", "ソフラコン",
    "アズレンスルホン酸", "アズレンスルホン酸ナトリウム", "水溶性アズレン",
    "銅クロロフィリン", "銅クロロフィリンナトリウム", "アルジオキサ", "アランサ"
]

# 胃薬・胃腸薬の症状別成分優先順位
STOMACH_MEDICINE_PRIORITY = {
    "胃痛": {
        "制酸薬": {"ingredients": ["炭酸水素ナトリウム", "酸化マグネシウム", "水酸化アルミニウム", "炭酸マグネシウム", "炭酸カルシウム"], "boost": 0.15},
        "胃粘膜保護": {"ingredients": STOMACH_MUCOSAL_PROTECTANTS, "boost": 0.20, "condition": "空腹時"}
    },
    "胸やけ": {
        "H2ブロッカー": {"ingredients": ["ファモチジン", "ラニチジン", "シメチジン", "ニザチジン"], "boost": 0.18},
        "制酸薬": {"ingredients": ["炭酸水素ナトリウム", "酸化マグネシウム", "水酸化アルミニウム"], "boost": 0.12}
    },
    "胃もたれ": {"健胃消化薬": {"ingredients": ["生薬", "健胃", "消化"], "boost": 0.15}},
    "吐き気": {"制吐薬": {"ingredients": ["ジメンヒドリナート", "メトクロプラミド", "ドンペリドン"], "boost": 0.15}}
}

# 便秘薬の成分優先順位
CONSTIPATION_MEDICINE_PRIORITY = {
    "高優先度（安全性重視）": {"ingredients": ["酸化マグネシウム", "ラクツロース", "ラクチトール", "ポリカルボフィルカルシウム"], "boost": 0.20},
    "中優先度（効果重視だがリスクあり）": {"ingredients": ["センナ", "ヒマシ油", "ビサコジル", "ピコスルファート"], "boost": 0.10}
}

# 刺激性下剤の成分リスト
IRRITANT_LAXATIVE_INGREDIENTS = [
    "センナ", "センノシド", "センナエキス", "ビサコジル", "ピコスルファート",
    "ヒマシ油", "加香ヒマシ油", "カストル油"
]

# 主要解熱鎮痛薬リスト
MAJOR_ANALGESIC_MEDICINES = [
    'カロナールＡ', 'カロナールA', 'カロナール', 'ロキソニンＳ', 'ロキソニンS', 'ロキソニン',
    'タイレノールＡ', 'タイレノールA', 'タイレノール', 'イブ', 'EVE', 'イブプロフェ',
    'ブファリン', 'バファリン', 'バファリンA'
]

# 推奨候補から除外する製品（otc_medicine_data.csv には残す）
# ジェネリック名のみ・EC 未掲載・商品画像なし等、消費者向け推奨に不向きな品目
RECOMMENDATION_EXCLUDED_PRODUCTS = [
    'イブプロフェン錠２００Ｓ',
    'イブプロフェン錠200S',
    'イブプロフェン錠２００ＳＣ',
    'イブプロフェン錠200SC',
]

# 解熱鎮痛薬の成分優先順位
ANALGESIC_PRIORITY = {
    "高優先度（胃に優しい）": {"ingredients": ["アセトアミノフェン", "パラセタモール", "タイレノール"], "boost": 0.15},
    "中優先度（バランス型）": {"ingredients": ["イブプロフェン", "イブ", "ブルフェン"], "boost": 0.10},
    "中優先度（効果高いが胃への影響あり）": {"ingredients": ["ロキソプロフェン", "ロキソニン", "ジクロフェナク", "ボルタレン"], "boost": 0.08}
}

# 月経不順向け成分優先順位
MENSTRUAL_MEDICINE_PRIORITY = {
    "高優先度（当帰芍薬散）": {"ingredients": ["当帰芍薬散", "トウキシャクヤクサン"], "boost": 0.25},
    "高優先度（当帰+芍薬の組み合わせ）": {"ingredients": ["当帰", "トウキ", "芍薬", "シャクヤク"], "requires_both": True, "boost": 0.20},
    "中優先度（当帰または芍薬単独）": {"ingredients": ["当帰", "トウキ", "芍薬", "シャクヤク"], "boost": 0.15}
}

# 外用薬（喉）の成分優先順位
THROAT_TOPICAL_PRIORITY = {
    "高優先度": {"ingredients": ["ポビドンヨード", "イソジン", "アズレンスルホン酸ナトリウム", "アズレン", "水溶性アズレン"], "boost": 0.20},
    "中優先度": {"ingredients": ["グリチルリチン酸", "カンゾウエキス"], "boost": 0.12}
}

# 睡眠障害（眠気）向け成分優先順位
SLEEP_DISORDER_PRIORITY = {
    "高優先度（ビタミン剤配合カフェイン製剤）": {"product_names": ["エスタロン", "エスタロンモカ", "トメルミン"], "boost": 0.20},
    "中優先度（カフェイン単独製剤）": {"ingredients": ["カフェイン", "無水カフェイン", "カフェイン水和物", "クエン酸カフェイン"], "boost": 0.15}
}

# 切り傷・擦り傷の成分・剤形優先順位
WOUND_MEDICINE_PRIORITY = {
    "成分": {"ingredients": ["イソジン", "オキシドール", "過酸化水素", "ワセリン", "白色ワセリン"], "boost": 0.15},
    "剤形": {"forms": ["絆創膏", "軟膏", "スプレー", "クリーム"], "boost": 0.10}
}

# やけどの重度判定キーワード
BURN_SEVERITY_KEYWORDS = {
    "severe": ["水ぶくれ", "水疱", "痛くない", "3度熱傷", "顔面", "広範囲", "重度", "激しい"]
}

# calculate_final_score 用：生理痛専用医薬品の製品名リスト（製品名ベースで判定）
MENSTRUAL_ONLY_PRODUCTS = [
    "ノーシンピュア", "オトナノーシンピュア", "ノーシン", "ノーシンホワイト",
    "エルペインコーワ", "バファリンルナ", "バファリンルナi", "バファリンルナJ",
    "A錠EX", "イブA錠EX", "イントウェル", "ウラック", "メディペイン", "ユニトップファースト",
    "マルコミンEV", "ノーチカ", "クミアイ新頭痛錠"
]

# 生理痛専用効能判定時、含まれていれば「一般用」とみなす効能キーワード
MENSTRUAL_GENERAL_EFFICACY_KEYWORDS = [
    "頭痛", "発熱", "解熱", "歯痛", "咽喉痛", "のどの痛み", "筋肉痛", "関節痛", "腰痛", "神経痛"
]

# 生理痛関連ユーザー入力・症状キーワード
MENSTRUAL_SYMPTOM_KEYWORDS = [
    "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理中",
    "月経不順", "生理不順", "生理", "月経"
]

# 水痘・インフルエンザ関連（アスピリン除外判定用）
CHICKENPOX_KEYWORDS = [
    "水痘", "みずぼうそう", "水疱瘡", "帯状疱疹", "ヘルペス",
    "発疹", "水ぶくれ", "水疱"
]

# 信頼性の高いメーカーリスト（スコアボーナス用）
TRUSTED_MANUFACTURERS = [
    "第一三共", "第一三共ヘルスケア",
    "大正製薬", "エスエス製薬", "ライオン", "シオノギ", "シオノギヘルスケア",
    "興和", "Kowa", "ロート製薬", "小林製薬", "武田", "タケダ", "アリナミン製薬",
    "佐藤製薬", "久光製薬", "グラクソ", "GSK", "ジョンソン", "J&J"
]

# 強力・著名な製品ブランドリスト（スコアボーナス用）
STRONG_PRODUCTS = [
    "ロキソニン", "カロナール", "タイレノール", "イブ", "EVE", "バファリン", "セデス", "ナロン", "リングル",
    "ガスター", "ボルタレン", "フェイタス", "バンテリン", "サロンパス",
    "アレグラ", "アレジオン", "クラリチン"
]

# 強力な成分リスト（スコアボーナス用）
STRONG_INGREDIENTS = [
    "ロキソプロフェン", "アセトアミノフェン", "イブプロフェン",
    "ジクロフェナク", "フェルビナク", "インドメタシン",
    "ファモチジン", "フェキソフェナジン", "ロラタジン"
]

# 成分重複チェック用リスク成分マスター
RISK_INGREDIENTS_OVERLAP = {
    "アセトアミノフェン": {"canonical_name": "アセトアミノフェン", "synonyms": ["アセトアミノフェン", "アセトアミノフェン水和物", "パラセタモール"], "overlap_warning": True, "category": "analgesic", "severity": "red", "warning_message": "アセトアミノフェン", "side_effects": ["肝機能障害", "過剰摂取"], "max_daily_dose": 4000},
    "エテンザミド": {"canonical_name": "エテンザミド", "synonyms": ["エテンザミド"], "overlap_warning": True, "category": "analgesic", "severity": "red", "warning_message": "エテンザミド", "side_effects": ["過剰摂取"]},
    "イブプロフェン": {"canonical_name": "イブプロフェン", "synonyms": ["イブプロフェン", "イブプロフェン錠"], "overlap_warning": True, "category": "nsaid", "severity": "red", "warning_message": "イブプロフェン（NSAIDs）", "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"], "note": "ロキソプロフェン等、他のNSAIDsとの併用は避けてください"},
    "クロルフェニラミン": {"canonical_name": "クロルフェニラミン", "synonyms": ["クロルフェニラミン", "クロルフェニラミンマレイン酸塩", "クロルフェニラミン塩酸塩", "d-クロルフェニラミンマレイン酸塩"], "overlap_warning": True, "category": "antihistamine", "severity": "yellow", "warning_message": "クロルフェニラミン", "side_effects": ["眠気", "口渇", "閉尿"], "focus_side_effect": "眠気"},
    "ジフェンヒドラミン": {"canonical_name": "ジフェンヒドラミン", "synonyms": ["ジフェンヒドラミン", "ジフェンヒドラミン塩酸塩", "ジフェンヒドラミンサリチル酸塩"], "overlap_warning": True, "category": "antihistamine", "severity": "yellow", "warning_message": "ジフェンヒドラミン", "side_effects": ["眠気", "口渇", "閉尿"], "focus_side_effect": "眠気"},
    "クレマスチン": {"canonical_name": "クレマスチン", "synonyms": ["クレマスチン", "クレマスチンフマル酸塩"], "overlap_warning": True, "category": "antihistamine", "severity": "yellow", "warning_message": "クレマスチン", "side_effects": ["眠気", "口渇", "閉尿"], "focus_side_effect": "眠気"},
    "プロメタジン": {"canonical_name": "プロメタジン", "synonyms": ["プロメタジン", "プロメタジン塩酸塩", "プロメタジンマレイン酸塩"], "overlap_warning": True, "category": "antihistamine", "severity": "yellow", "warning_message": "プロメタジン", "side_effects": ["眠気", "口渇", "閉尿"], "focus_side_effect": "眠気"},
    "アスピリン": {"canonical_name": "アスピリン", "synonyms": ["アスピリン", "アセチルサリチル酸", "アセチルサリチル酸アルミニウム", "アセチルサリチル酸カルシウム", "アセチルサリチル酸リジン"], "overlap_warning": True, "category": "nsaid", "severity": "red", "warning_message": "アスピリン（サリチル酸系）", "side_effects": ["胃腸障害", "出血傾向", "過剰摂取", "ライ症候群（小児）"], "max_daily_dose": 4000, "note": "他の解熱鎮痛薬との併用不可"},
    "ロキソプロフェン": {"canonical_name": "ロキソプロフェン", "synonyms": ["ロキソプロフェン", "ロキソプロフェンナトリウム", "ロキソプロフェンナトリウム水和物"], "overlap_warning": True, "category": "nsaid", "severity": "red", "warning_message": "ロキソプロフェン（NSAIDs）", "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"], "max_daily_dose": 180, "note": "イブプロフェン等、他のNSAIDsとの併用は避けてください"},
    "イソプロピルアンチピリン": {"canonical_name": "イソプロピルアンチピリン", "synonyms": ["イソプロピルアンチピリン", "イソプロピルアンチピリン錠"], "overlap_warning": True, "category": "pyralozone", "severity": "red", "warning_message": "イソプロピルアンチピリン（ピリン系）", "side_effects": ["過剰摂取", "アレルギー反応", "顆粒球減少症", "ピリン疹（薬疹）", "ショック"], "note": "ピリン系アレルギーの既往がある場合は厳禁"},
    "メフェナム酸": {"canonical_name": "メフェナム酸", "synonyms": ["メフェナム酸", "メフェナム酸錠"], "overlap_warning": True, "category": "nsaid", "severity": "red", "warning_message": "メフェナム酸（NSAIDs）", "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"], "note": "ロキソプロフェン、イブプロフェン等、他のNSAIDsとの併用は避けてください"},
    "カフェイン": {"canonical_name": "カフェイン", "synonyms": ["カフェイン", "無水カフェイン", "カフェイン水和物", "クエン酸カフェイン", "安息香酸ナトリウムカフェイン"], "overlap_warning": True, "category": "xanthine", "severity": "yellow", "warning_message": "カフェイン", "side_effects": ["不眠", "動悸", "頭痛", "過剰摂取", "振戦", "胃荒れ"], "max_daily_dose": 400, "note": "風邪薬、鎮痛薬、眠気防止薬、栄養ドリンクでの重複が非常に起きやすい"},
    "デキストロメトルファン": {"canonical_name": "デキストロメトルファン", "synonyms": ["デキストロメトルファン", "デキストロメトルファン臭化水素酸塩", "デキストロメトルファン臭化水素酸塩水和物"], "overlap_warning": True, "category": "antitussive_non_narcotic", "severity": "yellow", "warning_message": "デキストロメトルファン", "side_effects": ["眠気", "めまい", "過剰摂取", "消化器症状"], "note": "非麻薬性だが、重複すると副作用が強く出る"},
    "ジヒドロコデイン": {"canonical_name": "ジヒドロコデイン", "synonyms": ["ジヒドロコデイン", "ジヒドロコデインリン酸塩", "ジヒドロコデインリン酸塩水和物"], "overlap_warning": True, "category": "antitussive_narcotic", "severity": "red", "warning_message": "ジヒドロコデイン（麻薬性鎮咳成分）", "side_effects": ["依存性", "眠気", "便秘", "過剰摂取", "呼吸抑制"], "note": "12歳未満は使用禁止。風邪薬と咳止めで重複しやすい"},
    "コデイン": {"canonical_name": "コデイン", "synonyms": ["コデイン", "コデインリン酸塩水和物", "リン酸コデイン"], "overlap_warning": True, "category": "antitussive_narcotic", "severity": "red", "warning_message": "コデイン類（麻薬性鎮咳成分）", "side_effects": ["呼吸抑制", "便秘", "眠気", "依存性"], "note": "12歳未満は使用禁止。重複により呼吸抑制リスク増大"},
    "プソイドエフェドリン": {"canonical_name": "プソイドエフェドリン", "synonyms": ["プソイドエフェドリン", "プソイドエフェドリン塩酸塩", "dl-プソイドエフェドリン塩酸塩"], "overlap_warning": True, "category": "sympathomimetic", "severity": "red", "warning_message": "プソイドエフェドリン", "side_effects": ["不眠", "動悸", "血圧上昇", "過剰摂取", "排尿困難"], "note": "鼻炎薬と風邪薬での重複が非常に多い。高血圧・心臓病の人は要注意"},
    "メチルエフェドリン": {"canonical_name": "メチルエフェドリン", "synonyms": ["メチルエフェドリン", "dl-メチルエフェドリン塩酸塩", "メチルエフェドリンサッカリン塩"], "overlap_warning": True, "category": "sympathomimetic", "severity": "yellow", "warning_message": "メチルエフェドリン", "side_effects": ["動悸", "血圧上昇", "震え"], "note": "咳止めや風邪薬に含まれる。交感神経刺激作用の重複に注意"},
    "トラネキサム酸": {"canonical_name": "トラネキサム酸", "synonyms": ["トラネキサム酸", "トラネキサム酸錠"], "overlap_warning": True, "category": "hemostatic", "severity": "yellow", "warning_message": "トラネキサム酸", "side_effects": ["血栓症", "過剰摂取"]},
    "ビタミンA": {"canonical_name": "ビタミンA", "synonyms": ["ビタミンA", "レチノール", "レチノールパルミチン酸エステル", "レチノール酢酸エステル", "β-カロテン"], "overlap_warning": True, "category": "vitamin", "severity": "yellow", "warning_message": "ビタミンA", "side_effects": ["肝機能障害", "頭痛", "過剰摂取"], "max_daily_dose": 5000},
    "ビタミンD": {"canonical_name": "ビタミンD", "synonyms": ["ビタミンD", "ビタミンD2", "ビタミンD3", "エルゴカルシフェロール", "コレカルシフェロール"], "overlap_warning": True, "category": "vitamin", "severity": "yellow", "warning_message": "ビタミンD", "side_effects": ["高カルシウム血症", "腎機能障害", "過剰摂取"], "max_daily_dose": 4000},
    "アルミニウム": {"canonical_name": "アルミニウム", "synonyms": ["アルミニウム", "水酸化アルミニウム", "アルミニウムゲル", "合成ケイ酸アルミニウム", "ケイ酸アルミニウムマグネシウム", "炭酸アルミニウム", "リン酸アルミニウムゲル"], "overlap_warning": True, "category": "antacid", "severity": "yellow", "warning_message": "アルミニウム含有製剤", "side_effects": ["便秘", "リン吸着", "長期使用によるリスク"]},
    "マグネシウム": {"canonical_name": "マグネシウム", "synonyms": ["マグネシウム", "酸化マグネシウム", "水酸化マグネシウム", "炭酸マグネシウム", "ケイ酸アルミニウムマグネシウム"], "overlap_warning": True, "category": "antacid", "severity": "yellow", "warning_message": "マグネシウム含有製剤", "side_effects": ["下痢", "長期使用によるリスク"]},
    "グアヤコールスルホン酸カリウム": {"canonical_name": "グアヤコールスルホン酸カリウム", "synonyms": ["グアヤコールスルホン酸カリウム", "グアイフェネシン"], "overlap_warning": True, "category": "expectorant", "severity": "yellow", "warning_message": "グアヤコールスルホン酸カリウム", "side_effects": ["胃腸障害", "過剰摂取"]},
    "ブロムヘキシン": {"canonical_name": "ブロムヘキシン", "synonyms": ["ブロムヘキシン", "ブロムヘキシン塩酸塩"], "overlap_warning": True, "category": "expectorant", "severity": "yellow", "warning_message": "ブロムヘキシン", "side_effects": ["胃腸障害", "過剰摂取"]},
    "カルボシステイン": {"canonical_name": "カルボシステイン", "synonyms": ["カルボシステイン", "L-カルボシステイン"], "overlap_warning": True, "category": "expectorant", "severity": "yellow", "warning_message": "カルボシステイン", "side_effects": ["胃腸障害", "過剰摂取"]},
    "ベラドンナ総アルカロイド": {"canonical_name": "ベラドンナ総アルカロイド", "synonyms": ["ベラドンナ総アルカロイド", "ベラドンナエキス"], "overlap_warning": True, "category": "anticholinergic", "severity": "red", "warning_message": "ベラドンナ総アルカロイド（抗コリン成分）", "side_effects": ["口渇", "便秘", "眼圧上昇", "排尿困難"], "note": "鼻炎薬と胃腸鎮痛鎮痙薬での重複が多い。緑内障・前立腺肥大の人はリスク大"},
    "ヨウ化イソプロパミド": {"canonical_name": "ヨウ化イソプロパミド", "synonyms": ["ヨウ化イソプロパミド"], "overlap_warning": True, "category": "anticholinergic", "severity": "yellow", "warning_message": "ヨウ化イソプロパミド（抗コリン成分）", "side_effects": ["口渇", "便秘", "眼圧上昇"], "note": "鼻炎薬によく含まれる。作用時間が長い"},
    "スコポラミン": {"canonical_name": "スコポラミン", "synonyms": ["スコポラミン", "スコポラミン臭化水素酸塩水和物", "ロートエキス"], "overlap_warning": True, "category": "anticholinergic", "severity": "yellow", "warning_message": "スコポラミン・ロートエキス（抗コリン成分）", "side_effects": ["眠気", "口渇", "目のかすみ"], "note": "乗り物酔い止め、胃薬、風邪薬での重複に注意"},
    "ブロモバレリル尿素": {"canonical_name": "ブロモバレリル尿素", "synonyms": ["ブロモバレリル尿素", "ブロムワレリル尿素"], "overlap_warning": True, "category": "sedative", "severity": "red", "warning_message": "ブロモバレリル尿素（鎮静成分）", "side_effects": ["強い眠気", "依存性", "ふらつき"], "note": "「アリルイソプロピルアセチル尿素」との重複も鎮静作用増強のため注意"},
    "アリルイソプロピルアセチル尿素": {"canonical_name": "アリルイソプロピルアセチル尿素", "synonyms": ["アリルイソプロピルアセチル尿素"], "overlap_warning": True, "category": "sedative", "severity": "yellow", "warning_message": "アリルイソプロピルアセチル尿素", "side_effects": ["眠気", "だるさ"], "note": "解熱鎮痛薬によく配合されている。乗り物酔い薬等との重複で眠気が増強"}
}
