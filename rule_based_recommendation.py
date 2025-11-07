"""
ルールベース医薬品推奨システム
風邪薬、解熱鎮痛薬、鼻炎用薬の3種類に特化

ChatGPT APIはNLU（症状抽出）のみに使用し、
医薬品推奨は登録販売者の判断を再現するルールベース/スコアリング型アルゴリズムで実装
"""

import pandas as pd
import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

# ロガー設定
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# ================================================================================
# 1. データ構造と定数定義
# ================================================================================

# 症状辞書（全医薬品種類に対応）
SYMPTOM_DICTIONARY = {
    # 風邪関連症状
    "発熱": {
        "canonical_name": "発熱",
        "synonyms": ["熱がある", "熱っぽい", "高熱", "微熱", "体温が高い", "熱"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.9
    },
    "頭痛": {
        "canonical_name": "頭痛",
        "synonyms": ["頭が痛い", "ズキズキする", "頭が重い", "偏頭痛"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.85
    },
    "のどの痛み": {
        "canonical_name": "のどの痛み",
        "synonyms": ["喉が痛い", "喉の痛み", "のどが痛い", "咽頭痛", "喉の腫れ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬", "外用薬（のど）"],
        "weight": 0.9
    },
    "咳": {
        "canonical_name": "咳",
        "synonyms": ["せき", "咳が出る", "咳込む", "空咳"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.85
    },
    "痰": {
        "canonical_name": "痰",
        "synonyms": ["たん", "痰が絡む", "痰が出る"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.8
    },
    "鼻水": {
        "canonical_name": "鼻水",
        "synonyms": ["鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.85
    },
    "鼻づまり": {
        "canonical_name": "鼻づまり",
        "synonyms": ["鼻詰まり", "鼻が詰まる", "鼻閉"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.85
    },
    "くしゃみ": {
        "canonical_name": "くしゃみ",
        "synonyms": ["クシャミ", "くしゃみが出る"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.8
    },
    "悪寒": {
        "canonical_name": "悪寒",
        "synonyms": ["寒気", "さむけ", "ゾクゾクする", "悪寒がする"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.85
    },
    "関節痛": {
        "canonical_name": "関節痛",
        "synonyms": ["関節の痛み", "節々が痛い", "関節が痛い"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.8
    },
    "筋肉痛": {
        "canonical_name": "筋肉痛",
        "synonyms": ["筋肉の痛み", "体が痛い", "筋肉が痛い"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.75
    },
    # 解熱鎮痛薬関連症状
    "生理痛": {
        "canonical_name": "生理痛",
        "synonyms": ["月経痛", "生理の痛み", "下腹部痛"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],
        "weight": 0.95
    },
    "歯痛": {
        "canonical_name": "歯痛",
        "synonyms": ["歯が痛い", "歯の痛み"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],
        "weight": 0.9
    },
    # 鼻炎用薬関連症状
    "鼻汁過多": {
        "canonical_name": "鼻汁過多",
        "synonyms": ["鼻水が多い", "鼻水がとまらない"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["鼻炎用薬"],
        "weight": 0.9
    },
    "なみだ目": {
        "canonical_name": "なみだ目",
        "synonyms": ["涙目"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["鼻炎用薬"],
        "weight": 0.7
    },
    # 胃腸薬関連症状
    "胃痛": {
        "canonical_name": "胃痛",
        "synonyms": ["胃が痛い", "胃の痛み", "胃部痛", "みぞおちの痛み"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "腹痛": {
        "canonical_name": "腹痛",
        "synonyms": ["お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "下痢": {
        "canonical_name": "下痢",
        "synonyms": ["下痢", "軟便", "水様便", "便がゆるい"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "便秘": {
        "canonical_name": "便秘",
        "synonyms": ["便秘", "便が出ない", "便通がない", "便が硬い"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "吐き気": {
        "canonical_name": "吐き気",
        "synonyms": ["吐き気", "むかつき", "気持ち悪い", "嘔吐感"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "胸やけ": {
        "canonical_name": "胸やけ",
        "synonyms": ["胸やけ", "胸焼け", "胃もたれ", "胃の重い感じ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.85
    },
    "胃もたれ": {
        "canonical_name": "胃もたれ",
        "synonyms": ["胃もたれ", "胃の重い感じ", "消化が悪い", "胃の不快感"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.85
    },
    # 外用薬関連症状
    "かゆみ": {
        "canonical_name": "かゆみ",
        "synonyms": ["かゆい", "痒み", "かゆみ", "皮膚のかゆみ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "発疹": {
        "canonical_name": "発疹",
        "synonyms": ["発疹", "ブツブツ", "赤い斑点", "皮膚の異常"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "湿疹": {
        "canonical_name": "湿疹",
        "synonyms": ["湿疹", "皮膚炎", "かぶれ", "皮膚の炎症"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "水虫": {
        "canonical_name": "水虫",
        "synonyms": ["水虫", "白癬", "足の水虫", "指の間のかゆみ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.95
    },
    "打撲": {
        "canonical_name": "打撲",
        "synonyms": ["打撲", "打ち身", "青あざ", "内出血"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "捻挫": {
        "canonical_name": "捻挫",
        "synonyms": ["捻挫", "くじいた", "関節の痛み", "靭帯損傷"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "肩こり": {
        "canonical_name": "肩こり",
        "synonyms": ["肩こり", "肩の凝り", "肩の痛み", "首肩の痛み"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）", "筋肉痛"],
        "weight": 0.85
    },
    # 目薬関連症状
    "目の充血": {
        "canonical_name": "目の充血",
        "synonyms": ["目の充血", "目が赤い", "充血", "目の血走り"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["目薬"],
        "weight": 0.9
    },
    "目の疲れ": {
        "canonical_name": "目の疲れ",
        "synonyms": ["目の疲れ", "眼精疲労", "目が疲れる", "目の重い感じ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["目薬"],
        "weight": 0.85
    },
    "目のかゆみ": {
        "canonical_name": "目のかゆみ",
        "synonyms": ["目のかゆみ", "目がかゆい", "目の痒み", "目のかゆみ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["目薬"],
        "weight": 0.9
    },
    # 睡眠・精神関連症状
    "不眠": {
        "canonical_name": "不眠",
        "synonyms": ["不眠", "眠れない", "睡眠不足", "寝つきが悪い"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["睡眠障害"],
        "weight": 0.9
    },
    "めまい": {
        "canonical_name": "めまい",
        "synonyms": ["めまい", "眩暈", "ふらつき", "立ちくらみ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.8
    },
    "疲労感": {
        "canonical_name": "疲労感",
        "synonyms": ["疲労感", "疲れ", "だるい", "倦怠感"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.7
    },
    "イライラ": {
        "canonical_name": "イライラ",
        "synonyms": ["イライラ", "いらいら", "焦燥感", "落ち着かない"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.8
    },
    "不安": {
        "canonical_name": "不安",
        "synonyms": ["不安", "心配", "憂鬱", "落ち込み"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.8
    },
    "ストレス": {
        "canonical_name": "ストレス",
        "synonyms": ["ストレス", "ストレス", "緊張", "プレッシャー"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.7
    }
}

# 重症疑い症状（赤旗：Red Flag）- 即座にエスカレーション
RED_FLAG_SYMPTOMS = {
    "呼吸困難": ["呼吸が苦しい", "息苦しい", "呼吸困難", "息ができない", "息切れ"],
    "高熱": ["38.5度以上", "39度", "40度", "高熱", "熱が下がらない"],
    "胸痛": ["胸が痛い", "胸の痛み", "胸部痛", "心臓が痛い", "胸が締め付けられる"],
    "意識障害": ["意識がもうろう", "意識がない", "気を失う", "意識不明", "ぼーっとする"],
    "激しい頭痛": ["激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛", "頭が割れる", "耐えられない頭痛"],
    "血便": ["血便", "便に血が混じる", "黒い便", "タール便"],
    "喀血": ["血を吐く", "喀血", "吐血"],
    "激しい腹痛": ["激しい腹痛", "お腹が痛くて動けない", "耐えられない腹痛"],
    "顔面麻痺": ["顔面麻痺", "顔が動かない", "口が曲がる", "顔の半分が動かない"],
    "手足の麻痺": ["手足の麻痺", "手足が動かない", "力が入らない", "しびれが続く"],
    "持続する嘔吐": ["持続する嘔吐", "何度も吐く", "止まらない嘔吐", "嘔吐が続く"]
}

# 医師受診推奨条件
DOCTOR_REFERRAL_CONDITIONS = {
    "pregnancy": {
        "description": "妊娠中",
        "message": "妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
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
        "乳児": (0, 3),      # 0-3歳: 絶対禁忌
        "幼児": (3, 7),      # 3-7歳: 医師相談必須
        "小児": (7, 15),     # 7-15歳: 注意が必要
        "成人": (15, 65),    # 15-65歳: 通常使用可能
        "高齢者": (65, 150)  # 65歳以上: 注意が必要
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

# スコアリングウェイト（強化版）
from enhanced_safety_checker import enhanced_scoring_weights
SCORING_WEIGHTS = enhanced_scoring_weights()

# リスク成分リスト（減点対象、詳細症状がない場合は注意喚起）
RISK_INGREDIENTS_EXCLUDE = {
    # 下剤・緩下剤関連（使用条件が厳しい）
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
    # 解熱鎮痛薬関連（インフルエンザ時や特定条件下でリスク）
    "アスピリン": {
        "name": "アスピリン",
        "aliases": ["アスピリン", "アセチルサリチル酸", "ASA"],
        "penalty_score": -0.5,  # インフルエンザ時は除外
        "warning": "アスピリンが含まれています。インフルエンザや水痘の患者、特に小児ではライ症候群のリスクがあるため使用できません。"
    },
    "トラマドール": {
        "name": "トラマドール",
        "aliases": ["トラマドール", "トラマドール塩酸塩"],
        "penalty_score": -0.4,
        "warning": "トラマドールが含まれています。依存性の可能性があるため、長期連用は避けてください。15歳未満、妊娠中・授乳中の方は使用できません。"
    },
}

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
        "exclude_symptoms": ["下痢", "腹痛"]  # 下痢や腹痛がある場合は除外
    },
    "腸内容物排除": {
        "pattern": re.compile(r"腸内容物の急速な排除|腸管洗浄|検査前処置", re.IGNORECASE),
        "required_symptoms": [],
        "medicine_types": ["胃腸薬"],
        "strict": True  # 完全一致が必要
    }
}

# 複合薬識別パターン（複数の効能を持つ医薬品）
COMPOUND_MEDICINE_INDICATORS = {
    "風邪薬": {
        "patterns": [
            re.compile(r"総合感冒薬|総合かぜ薬|総合感冒|かぜ薬総合", re.IGNORECASE),
            re.compile(r"解熱.*鎮痛.*鎮咳|解熱.*鎮痛.*去痰", re.IGNORECASE),
            re.compile(r"風邪薬.*複数|複数の.*風邪症状", re.IGNORECASE)
        ],
        "required_symptoms_count": 2  # 複数の症状が必要
    },
    "総合胃腸薬": {
        "patterns": [
            re.compile(r"総合胃腸薬|胃腸薬総合", re.IGNORECASE),
            re.compile(r"胃痛.*下痢|下痢.*胃痛", re.IGNORECASE)
        ],
        "required_symptoms_count": 2
    }
}

# 曖昧症状リスト（詳細情報が必要な症状）
AMBIGUOUS_SYMPTOMS = {
    "腹痛": {
        "canonical_name": "腹痛",
        "clarification_questions": [
            "痛みの場所を教えてください（例：みぞおち、下腹部、全体など）",
            "痛みのきっかけはありますか？（例：食後、空腹時、下痢を伴うなど）",
            "他に症状はありますか？（例：下痢、便秘、発熱、吐き気など）"
        ],
        "priority": "critical"
    },
    "頭痛": {
        "canonical_name": "頭痛",
        "clarification_questions": [
            "頭痛の種類を教えてください（例：ズキズキする、締めつけられる、重い感じなど）",
            "頭痛のきっかけはありますか？（例：緊張時、生理中、風邪の初期症状など）",
            "他に症状はありますか？（例：発熱、吐き気、めまいなど）"
        ],
        "priority": "critical"
    },
    "咳": {
        "canonical_name": "咳",
        "clarification_questions": [
            "咳の種類を教えてください（例：乾いた咳、痰がからむ、夜間に出るなど）",
            "咳はいつから続いていますか？",
            "他に症状はありますか？（例：発熱、のどの痛み、鼻水など）"
        ],
        "priority": "important"
    },
    "のどの痛み": {
        "canonical_name": "のどの痛み",
        "clarification_questions": [
            "のどのどのあたりが痛みますか？",
            "発熱や咳はありますか？",
            "他に症状はありますか？（例：鼻水、頭痛など）"
        ],
        "priority": "important"
    },
    "胸やけ": {
        "canonical_name": "胸やけ",
        "clarification_questions": [
            "胸やけのきっかけはありますか？（例：食後、脂っこい食事後など）",
            "他に症状はありますか？（例：胃もたれ、胃痛など）"
        ],
        "priority": "optional"
    },
    "胃もたれ": {
        "canonical_name": "胃もたれ",
        "clarification_questions": [
            "胃もたれのきっかけはありますか？（例：食後、食べ過ぎなど）",
            "他に症状はありますか？（例：胸やけ、胃痛など）"
        ],
        "priority": "optional"
    }
}

# 症状カテゴリ間優先表（症状×医薬品種類のペナルティ設定）
SYMPTOM_CATEGORY_PENALTY = {
    "発熱": {
        "風邪薬": -0.3,  # 単一症状の場合は複合薬にペナルティ
        "解熱鎮痛薬": 0.0,  # 単一症状の場合は特化薬を優先
        "鼻炎用薬": -0.5  # 発熱のみでは鼻炎薬は不適切
    },
    "咳": {
        "風邪薬": -0.2,  # 咳のみの場合は総合感冒薬より鎮咳薬を優先
        "解熱鎮痛薬": -0.5,
        "鼻炎用薬": -0.3
    },
    "頭痛": {
        "風邪薬": -0.2,  # 頭痛のみの場合は解熱鎮痛薬を優先
        "解熱鎮痛薬": 0.0,
        "鼻炎用薬": -0.5
    },
    "鼻水": {
        "風邪薬": -0.1,  # 鼻水のみでも風邪薬は許容（軽微なペナルティ）
        "鼻炎用薬": 0.0,
        "解熱鎮痛薬": -0.5
    },
    "腹痛": {
        "胃腸薬": 0.0,  # 腹痛は胃腸薬が適切だが、詳細情報が必要
        "風邪薬": -0.5,
        "解熱鎮痛薬": -0.5
    },
    "下痢": {
        "胃腸薬": 0.0,
        "風邪薬": -0.5,
        "解熱鎮痛薬": -0.5
    },
    "便秘": {
        "胃腸薬": 0.0,
        "風邪薬": -0.5,
        "解熱鎮痛薬": -0.5
    }
}

# 複数症状の組み合わせによる調整（ボーナス/ペナルティ）
MULTI_SYMPTOM_COMBINATIONS = {
    frozenset({"のどの痛み", "発熱"}): {
        "風邪薬": 0.2,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"発熱", "咳"}): {
        "風邪薬": 0.15,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"発熱", "鼻水"}): {
        "風邪薬": 0.15,
        "解熱鎮痛薬": -0.1
    }
}

# ================================================================================
# 2. NLU関数（ChatGPT APIで症状抽出のみ）
# ================================================================================

# NLUキャッシュ（セッションごとの症状抽出結果を保存）
_nlu_cache = {}
_max_cache_size = 50  # 最大50セッション分を保持

def get_cached_nlu_result(user_text: str, session_id: str = None) -> Optional[Dict]:
    """
    NLUキャッシュから結果を取得
    
    Args:
        user_text: ユーザーの症状入力
        session_id: セッションID（オプション）
    
    Returns:
        キャッシュされたNLU結果、またはNone
    """
    if not session_id:
        return None
    
    cache_key = f"{session_id}:{hash(user_text)}"
    return _nlu_cache.get(cache_key)

def set_cached_nlu_result(user_text: str, nlu_result: Dict, session_id: str = None):
    """
    NLUキャッシュに結果を保存
    
    Args:
        user_text: ユーザーの症状入力
        nlu_result: NLU結果
        session_id: セッションID（オプション）
    """
    if not session_id:
        return
    
    # キャッシュサイズ制限
    if len(_nlu_cache) >= _max_cache_size:
        # 古いエントリを削除（FIFO）
        oldest_key = next(iter(_nlu_cache))
        del _nlu_cache[oldest_key]
    
    cache_key = f"{session_id}:{hash(user_text)}"
    _nlu_cache[cache_key] = nlu_result
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"NLUキャッシュに保存: {cache_key}")

def clear_nlu_cache():
    """NLUキャッシュをクリア"""
    global _nlu_cache
    _nlu_cache.clear()
    logger.info("NLUキャッシュをクリアしました")

def simple_pattern_matching_nlu(user_text: str, user_info: Dict) -> Dict:
    """
    強化されたルールベースNLU（正規表現、重症度推定、期間抽出）
    """
    import re
    
    text_lower = user_text.lower()
    detected_symptoms = []
    red_flags = []
    
    # 重症度修飾語のパターン（拡張版）
    severity_patterns = {
        "重度": [
            r"激しい", r"ひどい", r"重い", r"酷い", r"深刻", r"重症", r"強烈", r"猛烈",
            r"耐えられない", r"我慢できない", r"今までにない", r"異常に", r"非常に",
            r"緊急", r"救急", r"命に関わる", r"危険", r"危篤", r"重症化"
        ],
        "軽度": [
            r"少し", r"軽い", r"軽微", r"微か", r"弱い", r"軽度", r"軽い",
            r"ちょっと", r"やや", r"わずか", r"軽く", r"微か", r"軽微"
        ],
        "中等度": [
            r"中程度", r"普通", r"まあまあ", r"そこそこ", r"それなりに",
            r"そこそこ", r"普通程度", r"一般的", r"標準的"
        ]
    }
    
    # 期間表現のパターン（拡張版）
    duration_patterns = [
        r'(\d+)\s*(日|日間|日前)',
        r'(昨日|今日|一昨日|おととい)',
        r'(先週|今週|先月|今月)',
        r'(数日|数日前|数週間|数ヶ月|長期間|慢性的)',
        r'(今朝|昨夜|今晩|今午後)',
        r'(先ほど|さっき|つい先ほど)',
        r'(ずっと|継続的に|持続的に)'
    ]
    
    # 症状の組み合わせパターン
    SYMPTOM_COMBINATIONS = {
        '風邪': {
            'required': ['発熱', '咳'],
            'optional': ['鼻水', 'のどの痛み', '悪寒'],
            'confidence_boost': 0.2
        },
        'インフルエンザ': {
            'required': ['高熱', '頭痛'],
            'optional': ['関節痛', '悪寒', '筋肉痛'],
            'confidence_boost': 0.3
        },
        '胃腸炎': {
            'required': ['下痢', '腹痛'],
            'optional': ['吐き気', '嘔吐', '発熱'],
            'confidence_boost': 0.25
        },
        'アレルギー性鼻炎': {
            'required': ['鼻水', 'くしゃみ'],
            'optional': ['鼻づまり', '目のかゆみ'],
            'confidence_boost': 0.2
        }
    }
    
    # 症状辞書から同義語でマッチング（強化版）
    for symptom_name, symptom_data in SYMPTOM_DICTIONARY.items():
        # 正規化名でチェック
        if symptom_data["canonical_name"] in user_text:
            detected_symptoms.append({
                "name": symptom_name,
                "severity": "中等度",  # デフォルト
                "duration_days": None
            })
            continue
        
        # 同義語でチェック（部分一致も含む）
        for synonym in symptom_data["synonyms"]:
            if synonym in user_text:
                detected_symptoms.append({
                    "name": symptom_name,
                    "severity": "中等度",
                    "duration_days": None
                })
                break
    
    # 重症疑い症状のチェック（強化版）
    for flag_name, flag_keywords in RED_FLAG_SYMPTOMS.items():
        for keyword in flag_keywords:
            if keyword in user_text:
                red_flags.append(flag_name)
                break
    
    # 重症度の推定（強化版）
    for symptom in detected_symptoms:
        symptom_text = user_text
        severity = "中等度"  # デフォルト
        
        # 重症度修飾語の検出
        for severity_level, patterns in severity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, symptom_text):
                    severity = severity_level
                    break
            if severity != "中等度":
                break
        
        symptom["severity"] = severity
    
    # 期間の推定（強化版）
    duration_days = None
    
    # 数値表現の期間
    for pattern in duration_patterns:
        match = re.search(pattern, user_text)
        if match:
            if pattern.startswith(r'(\d+)'):
                duration_days = int(match.group(1))
            elif "昨日" in match.group(0):
                duration_days = 1
            elif "一昨日" in match.group(0):
                duration_days = 2
            elif "先週" in match.group(0):
                duration_days = 7
            elif "数日" in match.group(0):
                duration_days = 3  # 推定値
            elif "数週間" in match.group(0):
                duration_days = 14  # 推定値
            break
    
    # 期間を全症状に適用
    if duration_days is not None:
        for symptom in detected_symptoms:
            symptom["duration_days"] = duration_days
    
    # 症状の組み合わせパターン認識
    symptom_names = [s['name'] for s in detected_symptoms]
    combination_boost = 0.0
    
    for pattern_name, pattern_data in SYMPTOM_COMBINATIONS.items():
        required_symptoms = pattern_data['required']
        optional_symptoms = pattern_data['optional']
        boost = pattern_data['confidence_boost']
        
        # 必須症状のチェック
        required_matched = sum(1 for req in required_symptoms if req in symptom_names)
        if required_matched == len(required_symptoms):
            # オプション症状のボーナス
            optional_matched = sum(1 for opt in optional_symptoms if opt in symptom_names)
            combination_boost = boost + (optional_matched * 0.05)
            break
    
    # 症状の信頼度を計算（強化版）
    confidence_score = 0.0
    if detected_symptoms:
        # 症状数による信頼度
        confidence_score += min(len(detected_symptoms) * 0.3, 0.6)
        
        # 重症度の明確性による信頼度
        severity_specificity = sum(1 for s in detected_symptoms if s["severity"] != "中等度")
        confidence_score += severity_specificity * 0.1
        
        # 期間の明確性による信頼度
        if duration_days is not None:
            confidence_score += 0.2
        
        # 症状組み合わせによる信頼度向上
        confidence_score += combination_boost
    
    needs_escalation = len(red_flags) > 0
    escalation_reason = f"重症疑い症状が検出されました: {', '.join(red_flags)}" if needs_escalation else ""
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"=== 強化NLU結果 ===")
        logger.debug(f"検出された症状: {[s['name'] for s in detected_symptoms]}")
        logger.debug(f"重症疑い: {red_flags}")
        logger.debug(f"エスカレーション必要: {needs_escalation}")
        logger.debug(f"信頼度スコア: {confidence_score:.2f}")
    
    return {
        "symptoms": detected_symptoms,
        "red_flags": red_flags,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason,
        "confidence_score": confidence_score
    }

def hybrid_nlu_extraction(user_text: str, user_info: Dict, client: OpenAI, session_id: str = None) -> Dict:
    """
    ハイブリッドNLU（ルールベース優先、ChatGPT APIフォールバック）
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、性別など）
        client: OpenAI client
        session_id: セッションID（キャッシュ用）
    
    Returns:
        構造化された症状データ
    """
    # 1. キャッシュチェック
    cached_result = get_cached_nlu_result(user_text, session_id)
    if cached_result:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("NLUキャッシュから結果を取得")
        return cached_result
    
    # 2. ルールベースNLUを実行
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug("ルールベースNLUを実行")
    rule_based_result = simple_pattern_matching_nlu(user_text, user_info)
    
    # 3. 信頼度チェック
    confidence_score = rule_based_result.get('confidence_score', 0.0)
    symptoms_count = len(rule_based_result.get('symptoms', []))
    
    # 信頼度が低い場合（症状0個または信頼度0.3未満）のみChatGPT APIを呼び出し
    if symptoms_count == 0 or confidence_score < 0.3:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ルールベースNLUの信頼度が低いため、ChatGPT APIを呼び出し（信頼度: {confidence_score:.2f}）")
        gpt_result = extract_symptoms_with_gpt(user_text, user_info, client)
        
        # 結果をキャッシュに保存
        set_cached_nlu_result(user_text, gpt_result, session_id)
        return gpt_result
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ルールベースNLUの信頼度が十分（信頼度: {confidence_score:.2f}）")
        # 結果をキャッシュに保存
        set_cached_nlu_result(user_text, rule_based_result, session_id)
        return rule_based_result

def extract_symptoms_with_gpt(user_text: str, user_info: Dict, client: OpenAI) -> Dict:
    """
    ChatGPT APIを使用してユーザーの自由入力から症状を抽出・構造化
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、性別など）
        client: OpenAI client
    
    Returns:
        構造化された症状データ
    """
    # セキュリティ検証の追加
    from security_validator import validate_user_input
    from security_config import should_block_input, get_block_threshold
    from security_logger import log_input_validation
    
    # 入力検証
    is_safe, risk_score, warnings, sanitized_text = validate_user_input(
        user_text, context='symptom'
    )
    
    # ログ記録
    log_input_validation(
        user_id=user_info.get('user_id', 'unknown'),
        input_text=user_text,
        risk_score=risk_score,
        is_safe=is_safe,
        warnings=warnings,
        sanitized_text=sanitized_text
    )
    
    # ブロック判定
    if should_block_input(risk_score):
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"⚠️ 入力がブロックされました: リスクスコア {risk_score}")
        return {
            "symptoms": [],
            "red_flags": ["入力検証エラー"],
            "needs_escalation": True,
            "escalation_reason": "入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。"
        }
    
    # 高リスク入力の場合は症状抽出を停止
    if risk_score >= 80:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"⚠️ 高リスク入力のため症状抽出を停止: リスクスコア {risk_score}")
        return {
            "symptoms": [],
            "red_flags": ["高リスク入力"],
            "needs_escalation": True,
            "escalation_reason": "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。"
        }
    
    # 症状リストを作成
    all_symptoms = []
    for symptom_name, symptom_data in SYMPTOM_DICTIONARY.items():
        all_symptoms.append(symptom_name)
        all_symptoms.extend(symptom_data["synonyms"])
    
    prompt = f"""
あなたは医療NLUシステムです。ユーザーの症状文から以下の情報を抽出してください。

【ユーザー入力】
{sanitized_text}

【ユーザー情報】
年齢: {user_info.get('age', '不明')}
性別: {user_info.get('gender', '不明')}
妊娠中: {user_info.get('pregnant', False)}
授乳中: {user_info.get('breastfeeding', False)}

【抽出すべき情報】
1. 症状リスト（以下から該当するものを選択）
   {', '.join(list(SYMPTOM_DICTIONARY.keys()))}

2. 各症状の重症度（軽度/中等度/重度）
3. 症状の期間（何日前から）
4. 重症疑い症状の有無（呼吸困難、高熱38.5度以上、胸痛、意識障害など）

【回答形式】
以下のJSON形式で回答してください：
{{
    "symptoms": [
        {{
            "name": "症状名",
            "severity": "軽度 or 中等度 or 重度",
            "duration_days": 数値（不明なら null）
        }}
    ],
    "red_flags": ["重症疑い症状1", "重症疑い症状2"],
    "needs_escalation": true or false,
    "escalation_reason": "エスカレーションが必要な理由"
}}

注意：
- 症状名は必ず上記のリストから選択してください
- 重症疑い症状がある場合は必ず needs_escalation を true にしてください
- 情報が不明な場合は null を使用してください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、red_flagsに「インフルエンザ疑い」を追加してください
- 体温情報がある場合は、38.5度以上の場合は「高熱」としてred_flagsに追加してください
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """あなたは医療NLUシステムです。症状文から正確に情報を抽出してください。

重要な注意事項：
- 高熱（38.5度以上）と複数の風邪症状がある場合は、red_flagsに「インフルエンザ疑い」を追加してください
- 体温情報を正確に抽出し、38.5度以上の場合は「高熱」として扱ってください
- 症状名は必ずSYMPTOM_DICTIONARYに定義されている症状名から選択してください
- 重症疑い症状がある場合は必ずneeds_escalationをtrueにしてください"""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        
        result = response.choices[0].message.content
        
        # 安全なJSON解析
        from json_validator import safe_json_parse
        try:
            parsed_result = safe_json_parse(result, schema='symptom_analysis')
        except Exception as e:
            logger.warning(f"JSON解析エラー: {e}")
            return {
                "symptoms": [],
                "red_flags": [],
                "needs_escalation": False,
                "escalation_reason": ""
            }
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"=== NLU結果 ===")
            logger.debug(f"抽出された症状: {parsed_result.get('symptoms', [])}")
            logger.debug(f"重症疑い: {parsed_result.get('red_flags', [])}")
            logger.debug(f"エスカレーション必要: {parsed_result.get('needs_escalation', False)}")
        
        return parsed_result
            
    except Exception as e:
        logger.warning(f"NLU処理エラー: {e}")
        logger.info(f"フォールバック: 簡易パターンマッチングに切り替えます")
        
        # フォールバック: 簡易パターンマッチング
        return simple_pattern_matching_nlu(user_text, user_info)

# ================================================================================
# 3. 安全性フィルタ層
# ================================================================================

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
            # 0-3歳: 絶対禁忌
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
            # 3-7歳: 医師相談必須
            safety_result["is_safe"] = False
            safety_result["requires_escalation"] = True
            safety_result["doctor_referral_required"] = True
            safety_result["escalation_reason"] = f"{age}歳の幼児は医師の診察を受けてください。市販薬の使用は医師にご相談ください。"
            safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["age_under_7"])
            return safety_result
        elif age_rules["小児"][0] <= age < age_rules["小児"][1]:
            # 7-15歳: 注意が必要
            safety_result["warnings"].append(f"{age}歳の小児は市販薬使用に注意が必要です。保護者の監督下で使用してください。")
        elif age_rules["高齢者"][0] <= age:
            # 65歳以上: 注意が必要
            safety_result["warnings"].append(f"{age}歳の高齢者は市販薬使用に注意が必要です。副作用に特に注意してください。")
    
    # 3. 妊娠中チェック（医師受診必須）
    if user_info.get('pregnant', False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["pregnancy"])
        
        # 妊娠中の医薬品種類別制限を追加
        pregnancy_restrictions = CONTRAINDICATION_RULES["妊娠中"]
        for medicine_type, restriction in pregnancy_restrictions.items():
            if restriction == "禁忌":
                safety_result["warnings"].append(f"妊娠中は{medicine_type}の使用が禁忌です。")
            elif restriction == "要注意":
                safety_result["warnings"].append(f"妊娠中は{medicine_type}の使用に注意が必要です。")
        
        return safety_result
    
    # 4. 授乳中チェック（医師受診必須）
    if user_info.get('breastfeeding', False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["breastfeeding"])
        
        # 授乳中の医薬品種類別制限を追加
        breastfeeding_restrictions = CONTRAINDICATION_RULES["授乳中"]
        for medicine_type, restriction in breastfeeding_restrictions.items():
            if restriction == "要注意":
                safety_result["warnings"].append(f"授乳中は{medicine_type}の使用に注意が必要です。")
        
        return safety_result
    
    # 5. 症状の期間チェック（1週間以上で医師受診推奨）
    symptoms_over_week = False
    for symptom in nlu_result.get("symptoms", []):
        duration = symptom.get("duration_days")
        if duration is not None and duration >= 7:
            symptoms_over_week = True
            safety_result["warnings"].append(f"症状が{duration}日間続いています。長期化している場合は医師の診察を推奨します。")
    
    # 1週間以上の症状がある場合は医師受診推奨
    if symptoms_over_week:
        safety_result["doctor_referral_required"] = True
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["symptoms_over_week"])
    
    # 6. 症状の重症度チェック
    for symptom in nlu_result.get("symptoms", []):
        if symptom.get("severity") == "重度":
            safety_result["warnings"].append(f"重度の{symptom.get('name')}が報告されています。症状が重い場合は医師の診察を推奨します。")
    
    return safety_result

# ================================================================================
# 4. 候補薬取得とスコアリング
# ================================================================================

def _is_symptom_matching_specific_use(efficacy: str, symptoms: List[Dict], pattern_name: str) -> bool:
    """
    症状が特殊用途パターンと一致するかチェック
    
    Args:
        efficacy: 効能効果テキスト
        symptoms: 検出された症状リスト
        pattern_name: パターン名（SPECIFIC_USE_PATTERNSのキー）
    
    Returns:
        一致する場合True
    """
    if pattern_name not in SPECIFIC_USE_PATTERNS:
        return False
    
    pattern_info = SPECIFIC_USE_PATTERNS[pattern_name]
    pattern = pattern_info.get("pattern")
    
    if not pattern or not pattern.search(efficacy):
        return False
    
    # strictフラグがTrueの場合は完全一致が必要
    if pattern_info.get("strict", False):
        return True
    
    # required_symptomsのチェック
    required_symptoms = pattern_info.get("required_symptoms", [])
    if required_symptoms:
        symptom_names = [s.get("name") for s in symptoms]
        if not all(req in symptom_names for req in required_symptoms):
            return False
    
    # exclude_symptomsのチェック
    exclude_symptoms = pattern_info.get("exclude_symptoms", [])
    if exclude_symptoms:
        symptom_names = [s.get("name") for s in symptoms]
        if any(excl in symptom_names for excl in exclude_symptoms):
            return False
    
    return True

def _contains_risk_ingredient(ingredients: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    リスク成分が含まれているかチェック
    
    Args:
        ingredients: 成分テキスト
    
    Returns:
        (contains_risk, ingredient_name, risk_info): リスク成分の有無、成分名、リスク情報
    """
    if not ingredients or not isinstance(ingredients, str):
        return False, None, None
    
    ingredients_upper = ingredients.upper()
    
    for risk_name, risk_info in RISK_INGREDIENTS_EXCLUDE.items():
        aliases = risk_info.get("aliases", [])
        for alias in aliases:
            if alias.upper() in ingredients_upper:
                return True, risk_name, risk_info
    
    return False, None, None


def extract_main_ingredients(ingredients: str, max_count: int = 3) -> List[str]:
    """成分表から主要成分を抽出し、比較用に正規化する"""
    if not ingredients or not isinstance(ingredients, str):
        return []

    parts = re.split(r"[\n、,/，／・]+", ingredients)
    normalized = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        normalized.append(token.lower())
        if len(normalized) >= max_count:
            break
    return normalized


def ensure_ingredient_diversity(candidates: List[Dict], top_n: int = 3, similarity_threshold: float = 0.5) -> List[Dict]:
    """主要成分が重複しすぎないように候補を再選別する"""
    if len(candidates) <= top_n:
        return candidates

    selected: List[Dict] = []
    selected_sets: List[set] = []
    fallback: List[Tuple[Dict, set]] = []

    for candidate in candidates:
        main_ingredients = set(extract_main_ingredients(candidate.get("ingredients", "")))

        overlap = False
        for existing_set in selected_sets:
            if not existing_set or not main_ingredients:
                continue
            intersection = existing_set & main_ingredients
            if not intersection:
                continue
            overlap_ratio = len(intersection) / float(min(len(existing_set), len(main_ingredients)))
            if overlap_ratio >= similarity_threshold:
                overlap = True
                break

        if not overlap and len(selected) < top_n:
            selected.append(candidate)
            selected_sets.append(main_ingredients)
        else:
            fallback.append((candidate, main_ingredients))

    # まだ不足している場合は重複を許容して埋める
    if len(selected) < top_n:
        for candidate, ingredient_set in fallback:
            if candidate in selected:
                continue
            selected.append(candidate)
            selected_sets.append(ingredient_set)
            if len(selected) >= top_n:
                break

    return selected[:top_n]

def get_candidate_medicines(nlu_result: Dict, medicine_df: pd.DataFrame, user_text: str = "", influenza_risk: bool = False) -> List[Dict]:
    """
    症状に基づいて候補医薬品を取得（フィルタリング機能付き）
    
    Args:
        nlu_result: NLU解析結果
        medicine_df: 医薬品データフレーム
        user_text: ユーザーの入力テキスト（オプション）
        influenza_risk: インフルエンザリスクの有無
    
    Returns:
        フィルタリングされた候補医薬品リスト
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return []
    
    symptom_names = [s.get("name") for s in symptoms]
    is_single_symptom = len(symptom_names) == 1
    
    # 症状から医薬品の種類を推定
    medicine_types = set()
    for symptom in symptoms:
        symptom_name = symptom.get("name")
        if symptom_name in SYMPTOM_DICTIONARY:
            types = SYMPTOM_DICTIONARY[symptom_name]["medicine_types"]
            medicine_types.update(types)
    
    logger.info(f"推定された医薬品の種類: {medicine_types}")

    def _sanitize_text(value) -> str:
        if value is None:
            return ''
        text = str(value)
        if text.lower() == 'nan':
            return ''
        return text

    candidates: List[Dict] = []
    existing_keys: set = set()

    def append_candidate(row: pd.Series):
        product_name = _sanitize_text(row.get('製品名', ''))
        manufacturer = _sanitize_text(row.get('メーカー名', ''))
        key = (product_name, manufacturer)

        if not product_name and not manufacturer:
            return
        if key in existing_keys:
            return

        efficacy = row.get('効能効果', '')
        ingredients = row.get('成分', '')

        # 特殊用途医薬品のチェック
        for pattern_name in SPECIFIC_USE_PATTERNS.keys():
            if _is_symptom_matching_specific_use(efficacy, symptoms, pattern_name):
                pattern_info = SPECIFIC_USE_PATTERNS[pattern_name]
                required_symptoms = pattern_info.get("required_symptoms", [])
                if required_symptoms and not all(req in symptom_names for req in required_symptoms):
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"特殊用途医薬品を除外: {product_name} (パターン: {pattern_name}, 症状不足)"
                        )
                    return

        # インフルエンザ時のアスピリン除外
        if influenza_risk:
            contains_aspirin, _, _ = _contains_risk_ingredient(ingredients)
            if contains_aspirin and "アスピリン" in ingredients:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"インフルエンザリスクのためアスピリン含有医薬品を除外: {product_name}")
                return

        # リスク成分のチェック（単一症状の場合は除外、複数症状の場合は減点のみ）
        contains_risk, risk_name, risk_info = _contains_risk_ingredient(ingredients)
        if contains_risk and is_single_symptom:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"単一症状のためリスク成分含有医薬品を除外: {product_name} (成分: {risk_name})")
            return

        # 年齢制限の整形
        age_restriction = row.get('年齢制限', '')
        if not age_restriction and hasattr(row, 'iloc') and len(row) > 6:
            age_restriction = row.iloc[6]
        if age_restriction and isinstance(age_restriction, str):
            age_match = re.search(r'(\d+)歳', age_restriction)
            if age_match:
                age_restriction = f"{age_match.group(1)}歳以上"

        usage_full = row.get('用法用量', '') or ''
        usage_notes = ''
        if '注意' in usage_full or '＜' in usage_full:
            parts = usage_full.split('\n')
            note_parts = [p for p in parts if '注意' in p or '＜' in p or '用法' in p]
            usage_notes = '\n'.join(note_parts[:3])

        candidate = {
            'medicine_id': len(candidates),
            'product_name': product_name,
            'manufacturer': manufacturer,
            'medicine_type': _sanitize_text(row.get('医薬品の種類', '')),
            'classification': _sanitize_text(row.get('分類', '')),
            'efficacy': efficacy,
            'usage': row.get('用法用量', ''),
            'age_restriction': age_restriction,
            'ingredients': ingredients,
            'doping_prohibited': _sanitize_text(row.get('禁止物質あり', '')),
            'competition_category': _sanitize_text(row.get('競技会区分', '')),
            'conditions': _sanitize_text(row.get('条件', '')),
            'usage_notes': usage_notes if usage_notes else '用法用量を守ってご使用ください。',
            'base_score': 0.0
        }

        if contains_risk and risk_info:
            candidate['risk_ingredient'] = risk_name
            candidate['risk_warning'] = risk_info.get("warning", "")
            candidate['risk_penalty'] = risk_info.get("penalty_score", -0.3)

        candidates.append(candidate)
        existing_keys.add(key)

    for medicine_type in medicine_types:
        matched = medicine_df[medicine_df['医薬品の種類'] == medicine_type]
        for _, row in matched.iterrows():
            append_candidate(row)

    # のどの痛みがある場合は局所治療薬も候補に追加
    has_throat_pain = "のどの痛み" in symptom_names
    if has_throat_pain:
        throat_keyword_pattern = r"(のど|喉|咽頭)"
        product_keyword_pattern = r"(のど|喉|咽|トローチ|スプレー|うがい|キャンディ|飴)"

        throat_mask = (
            medicine_df['効能効果'].astype(str).str.contains(throat_keyword_pattern, na=False) |
            medicine_df['製品名'].astype(str).str.contains(product_keyword_pattern, na=False) |
            medicine_df['医薬品の種類'].astype(str).str.contains(throat_keyword_pattern, na=False)
        )

        throat_candidates = medicine_df[throat_mask]
        for _, row in throat_candidates.iterrows():
            append_candidate(row)

    logger.info(f"候補医薬品数: {len(candidates)} (フィルタリング後)")
    return candidates

def calculate_symptom_match_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状適合度スコアを計算
    """
    症状スコア = 0.0
    症状数 = len(nlu_result.get("symptoms", []))
    
    if 症状数 == 0:
        return 0.0
    
    efficacy_text = candidate.get('efficacy', '').lower()
    
    for symptom in nlu_result.get("symptoms", []):
        symptom_name = symptom.get("name")
        
        # 効能効果テキストに症状名が含まれるかチェック
        if symptom_name and symptom_name in efficacy_text:
            # 症状辞書の重みを使用
            weight = SYMPTOM_DICTIONARY.get(symptom_name, {}).get("weight", 0.5)
            症状スコア += weight
    
    return 症状スコア / 症状数

def calculate_age_fit_score(candidate: Dict, user_info: Dict) -> float:
    """
    年齢適合性スコアを計算
    """
    age = user_info.get('age')
    if age is None:
        # 年齢不明の場合は成人として扱う（スコアリングのみ）
        age = 30
        return 0.5  # 年齢不明の場合は中立スコア
    
    age_restriction = candidate.get('age_restriction', '')
    
    # NaN（欠損値）のチェック
    import math
    if isinstance(age_restriction, float) and math.isnan(age_restriction):
        age_restriction = ''
    
    # 年齢制限が数値の場合は文字列に変換
    if isinstance(age_restriction, (int, float)):
        try:
            age_restriction = str(int(age_restriction))
        except (ValueError, OverflowError):
            age_restriction = ''
    
    # 年齢制限が文字列でない場合は空文字列に
    if not isinstance(age_restriction, str):
        age_restriction = ''
    
    # 年齢制限の解析（簡易版）
    if '15歳未満' in age_restriction and age < 15:
        return 0.0  # 服用不可
    elif '7歳未満' in age_restriction and age < 7:
        return 0.0  # 服用不可
    elif age >= 15:
        return 1.0  # 成人は問題なし
    else:
        return 0.7  # 小児は減点

def calculate_final_score(candidate: Dict, nlu_result: Dict, user_info: Dict) -> Dict:
    """
    最終スコアを計算（全スコアを統合）
    
    Returns:
        {
            "total_score": float,
            "score_breakdown": {
                "symptom_match": float,
                "efficacy_specificity": float,
                "age_fit": float,
                "usage_convenience": float,
                "side_effect_risk": float,
                "interaction_risk": float
            }
        }
    """
    # スコアリングユーティリティをインポート
    from scoring_utils import (
        calculate_efficacy_specificity_score,
        calculate_side_effect_risk_score,
        calculate_interaction_risk_score,
        calculate_usage_convenience_score,
        check_allergy_contraindication,
        check_drug_interactions
    )
    
    # 各スコアを計算
    symptom_score = calculate_symptom_match_score(candidate, nlu_result)
    efficacy_specificity_score = calculate_efficacy_specificity_score(candidate, nlu_result)
    age_score = calculate_age_fit_score(candidate, user_info)
    usage_score = calculate_usage_convenience_score(candidate)
    side_effect_score = calculate_side_effect_risk_score(candidate, user_info)
    interaction_score = calculate_interaction_risk_score(candidate, user_info)
    
    # アレルギー成分チェック
    is_allergic, allergy_ingredient = check_allergy_contraindication(candidate, user_info)
    if is_allergic:
        # アレルギー成分がある場合はスコアを0に設定
        return {
            "total_score": 0.0,
            "score_breakdown": {
                "symptom_match": 0.0,
                "efficacy_specificity": 0.0,
                "age_fit": 0.0,
                "usage_convenience": 0.0,
                "side_effect_risk": 0.0,
                "interaction_risk": 0.0
            },
            "allergy_warning": f"アレルギー成分 '{allergy_ingredient}' が含まれています"
        }
    
    # 相互作用チェック
    has_interaction, interaction_warnings = check_drug_interactions(candidate, user_info)
    if has_interaction:
        # 相互作用がある場合は大幅減点
        interaction_score = min(interaction_score, -0.5)
    
    # 症状特異性ペナルティを計算
    symptom_specificity_penalty = calculate_symptom_specificity_penalty(candidate, nlu_result)
    
    # リスク成分の減点（複数症状の場合は減点のみ、単一症状の場合は既に除外済み）
    risk_penalty = 0.0
    if candidate.get('risk_ingredient'):
        risk_penalty = candidate.get('risk_penalty', -0.3)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"リスク成分ペナルティ: {candidate.get('risk_ingredient')} = {risk_penalty}")
    
    # 最終スコア計算（症状特異性ペナルティとリスク成分ペナルティを追加）
    total_score = (
        SCORING_WEIGHTS["症状適合度"] * symptom_score +
        SCORING_WEIGHTS["効能特異性"] * efficacy_specificity_score +
        SCORING_WEIGHTS["年齢適合性"] * age_score +
        SCORING_WEIGHTS["用法簡便性"] * usage_score +
        SCORING_WEIGHTS["副作用リスク"] * side_effect_score +
        SCORING_WEIGHTS["相互作用リスク"] * interaction_score +
        symptom_specificity_penalty +  # 症状特異性ペナルティ
        risk_penalty  # リスク成分ペナルティ
    )
    
    result = {
        "total_score": max(0.0, min(1.0, total_score)),  # 0.0-1.0の範囲に制限
        "score_breakdown": {
            "symptom_match": symptom_score,
            "efficacy_specificity": efficacy_specificity_score,
            "age_fit": age_score,
            "usage_convenience": usage_score,
            "side_effect_risk": side_effect_score,
            "interaction_risk": interaction_score,
            "symptom_specificity_penalty": symptom_specificity_penalty,  # スコア内訳に追加
            "risk_ingredient_penalty": risk_penalty  # リスク成分ペナルティ
        }
    }
    
    # 相互作用警告がある場合は追加
    if has_interaction:
        result["interaction_warnings"] = interaction_warnings
    
    return result

# ================================================================================
# 4.5 症状特異性ペナルティ計算関数
# ================================================================================

def calculate_symptom_specificity_penalty(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状特異性に基づくペナルティを計算
    効能特異性に応じてペナルティを緩和する
    
    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果
    
    Returns:
        ペナルティスコア（負の値、0.0が最大）
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return 0.0
    
    symptom_names = [s.get("name") for s in symptoms]
    medicine_type = candidate.get("medicine_type", "")
    
    # 効能特異性スコアを計算（外部関数を使用）
    from scoring_utils import calculate_efficacy_specificity_score
    efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)
    
    # 単一症状の場合
    if len(symptom_names) == 1:
        symptom_name = symptom_names[0]
        
        # 症状カテゴリ間優先表からペナルティを取得
        if symptom_name in SYMPTOM_CATEGORY_PENALTY:
            penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
            if medicine_type in penalty_table:
                base_penalty = penalty_table[medicine_type]
                # 効能特異性に応じてペナルティを緩和
                if efficacy_specificity >= 0.95:
                    penalty = base_penalty * 0.17  # -0.3 * 0.17 ≈ -0.05
                elif efficacy_specificity >= 0.8:
                    penalty = base_penalty * 0.5   # -0.3 * 0.5 = -0.15
                else:
                    penalty = base_penalty
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状特異性ペナルティ: {symptom_name} + {medicine_type} = {base_penalty} → {penalty:.2f} (効能特異性{efficacy_specificity:.2f})")
                return penalty
        
        # 複合薬識別パターンによるチェック
        # 単一症状なのに複合薬（風邪薬など）が推奨される場合
        if medicine_type in COMPOUND_MEDICINE_INDICATORS:
            compound_info = COMPOUND_MEDICINE_INDICATORS[medicine_type]
            required_count = compound_info.get("required_symptoms_count", 2)
            if len(symptom_names) < required_count:
                # デフォルトペナルティ（カテゴリ間優先表にない場合）
                base_penalty = -0.3
                # 効能特異性に応じてペナルティを緩和
                if efficacy_specificity >= 0.95:
                    penalty = base_penalty * 0.17
                elif efficacy_specificity >= 0.8:
                    penalty = base_penalty * 0.5
                else:
                    penalty = base_penalty
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"複合薬ペナルティ: 単一症状({symptom_name})に対して複合薬({medicine_type}) = {base_penalty} → {penalty:.2f} (効能特異性{efficacy_specificity:.2f})")
                return penalty
    
    # 複数症状の場合
    elif len(symptom_names) >= 2:
        from itertools import combinations

        total_adjustment = 0.0

        # 複数症状がある場合は、症状カテゴリ間優先表から最も適切なペナルティを適用
        penalties = []
        for symptom_name in symptom_names:
            if symptom_name in SYMPTOM_CATEGORY_PENALTY:
                penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
                if medicine_type in penalty_table:
                    penalties.append(penalty_table[medicine_type])

        if penalties:
            base_penalty = max(penalties)
            if base_penalty < 0:
                if efficacy_specificity >= 0.95:
                    base_penalty *= 0.17
                elif efficacy_specificity >= 0.8:
                    base_penalty *= 0.5
                total_adjustment += base_penalty
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"症状特異性ペナルティ（複数症状）: {medicine_type} = {penalties} → {base_penalty:.2f} (効能特異性{efficacy_specificity:.2f})"
                    )

        # 複数症状の組み合わせによるボーナス/ペナルティ
        for combo in combinations(symptom_names, 2):
            combo_key = frozenset(combo)
            adjustments = MULTI_SYMPTOM_COMBINATIONS.get(combo_key)
            if adjustments and medicine_type in adjustments:
                adjustment = adjustments[medicine_type]
                total_adjustment += adjustment
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"複数症状ボーナス: {combo_key} × {medicine_type} = {adjustment:+.2f}"
                    )

        if total_adjustment != 0.0:
            return total_adjustment

    return 0.0

# ================================================================================
# 4.6 推奨後の検証関数（責務分離）
# ================================================================================

def _recheck_risk_ingredients(candidates: List[Dict], nlu_result: Dict) -> List[Dict]:
    """
    リスク成分の再チェック
    
    Args:
        candidates: 候補医薬品リスト
        nlu_result: NLU解析結果
    
    Returns:
        検証済み候補リスト（リスク警告を追加）
    """
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    is_single_symptom = len(symptom_names) == 1
    
    validated = []
    for candidate in candidates:
        ingredients = candidate.get('ingredients', '')
        contains_risk, risk_name, risk_info = _contains_risk_ingredient(ingredients)
        
        if contains_risk:
            # リスク成分情報を追加
            if 'risk_ingredient' not in candidate:
                candidate['risk_ingredient'] = risk_name
                candidate['risk_warning'] = risk_info.get("warning", "") if risk_info else ""
            
            # 単一症状の場合は警告を強化
            if is_single_symptom:
                candidate['risk_warning'] = f"⚠️ {candidate.get('risk_warning', '')} 単一症状のため、より安全な医薬品の検討をお勧めします。"
        
        validated.append(candidate)
    
    return validated

def _check_influenza_compatibility(candidates: List[Dict], influenza_risk: bool) -> List[Dict]:
    """
    インフルエンザ適合性チェック
    
    Args:
        candidates: 候補医薬品リスト
        influenza_risk: インフルエンザリスクの有無
    
    Returns:
        検証済み候補リスト（アスピリン含有医薬品を除外）
    """
    if not influenza_risk:
        return candidates
    
    validated = []
    for candidate in candidates:
        ingredients = candidate.get('ingredients', '')
        contains_aspirin, _, _ = _contains_risk_ingredient(ingredients)
        
        if contains_aspirin and "アスピリン" in ingredients:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"検証処理: インフルエンザリスクのためアスピリン含有医薬品を除外: {candidate.get('product_name', '')}")
            continue  # インフルエンザ時はアスピリン含有医薬品を除外
        
        validated.append(candidate)
    
    return validated

def _finalize_recommendations(candidates: List[Dict], nlu_result: Dict, influenza_risk: bool) -> List[Dict]:
    """
    最終推奨の確定処理（責務を統合）
    
    Args:
        candidates: 候補医薬品リスト
        nlu_result: NLU解析結果
        influenza_risk: インフルエンザリスクの有無
    
    Returns:
        最終確定された候補リスト
    """
    # 1. インフルエンザ適合性チェック
    validated = _check_influenza_compatibility(candidates, influenza_risk)
    
    # 2. リスク成分の再チェック
    validated = _recheck_risk_ingredients(validated, nlu_result)
    
    # 3. スコアが0.3未満の候補を警告付きで残す（完全には除外しない）
    final_candidates = []
    for candidate in validated:
        score = candidate.get('final_score', 0.0)
        if score < 0.3:
            candidate['low_score_warning'] = True
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"⚠️ 低スコア警告: {candidate.get('product_name', '')} (スコア: {score:.3f})")
        final_candidates.append(candidate)
    
    return final_candidates

# ================================================================================
# 4.7 インフルエンザリスク検出関数
# ================================================================================

def detect_influenza_risk(nlu_result: Dict, user_text: str = "") -> Tuple[bool, str]:
    """
    インフルエンザの可能性を検出
    
    Args:
        nlu_result: NLU解析結果
        user_text: ユーザーの入力テキスト（オプション）
    
    Returns:
        (is_influenza_risk, reason): インフルエンザリスクの有無と理由
    """
    symptoms = nlu_result.get("symptoms", [])
    
    # 条件1: 「インフルエンザ」という単語が入力に含まれている
    if user_text and ("インフルエンザ" in user_text or "influenza" in user_text.lower()):
        return True, "入力文にインフルエンザの記載があります"
    
    # 条件2: 高熱（38.5度以上）+ 複数の風邪症状
    has_high_fever = False
    fever_symptom = None
    
    # 高熱の検出
    for symptom in symptoms:
        symptom_name = symptom.get("name", "")
        severity = symptom.get("severity", "")
        
        # 発熱症状のチェック
        if symptom_name == "発熱":
            fever_symptom = symptom
            # 重症度が「重度」の場合は高熱の可能性
            if severity == "重度":
                has_high_fever = True
            # ユーザー入力から体温情報を抽出
            if user_text:
                # 38.5度以上のパターンを検索
                temp_pattern = re.compile(r"(38\.5|39|40|41|42)[度°]?", re.IGNORECASE)
                if temp_pattern.search(user_text):
                    has_high_fever = True
    
    # RED_FLAG_SYMPTOMSの「高熱」もチェック
    if not has_high_fever and user_text:
        for flag_keyword in RED_FLAG_SYMPTOMS.get("高熱", []):
            if flag_keyword in user_text:
                has_high_fever = True
                break
    
    # 風邪関連症状のカウント
    cold_symptoms = ["発熱", "頭痛", "関節痛", "筋肉痛", "悪寒", "のどの痛み", "咳", "鼻水", "鼻づまり"]
    detected_cold_symptoms = [s for s in symptoms if s.get("name") in cold_symptoms]
    
    # 高熱 + 複数の風邪症状（2つ以上）でインフルエンザリスクと判定
    if has_high_fever and len(detected_cold_symptoms) >= 2:
        symptom_names = [s.get("name") for s in detected_cold_symptoms]
        return True, f"高熱（38.5度以上の可能性）と複数の風邪症状（{', '.join(symptom_names)}）が確認されました"
    
    # 高熱はないが、発熱 + 複数の全身症状（頭痛、関節痛、筋肉痛、悪寒）の組み合わせ
    if fever_symptom and len(detected_cold_symptoms) >= 3:
        systemic_symptoms = ["頭痛", "関節痛", "筋肉痛", "悪寒"]
        has_systemic = any(s.get("name") in systemic_symptoms for s in detected_cold_symptoms)
        if has_systemic:
            symptom_names = [s.get("name") for s in detected_cold_symptoms]
            return True, f"発熱と全身症状（{', '.join(symptom_names)}）が確認されました"
    
    return False, ""

# ================================================================================
# 5. 不足情報のチェックと質問生成
# ================================================================================

def check_missing_information(user_info: Dict, nlu_result: Dict) -> Dict:
    """
    不足している情報をチェックし、追加質問を生成（あいまい症状対応を含む）
    
    Returns:
        {
            "has_missing_info": bool,
            "missing_fields": List[str],
            "questions": List[str],
            "critical_questions": List[str],  # 優先度が高い質問
            "priority": str  # "critical", "important", "optional"
        }
    """
    missing_info = {
        "has_missing_info": False,
        "missing_fields": [],
        "questions": [],
        "critical_questions": [],  # 新規追加
        "priority": "optional"
    }
    
    # あいまい症状のチェック
    symptoms = nlu_result.get('symptoms', [])
    for symptom in symptoms:
        symptom_name = symptom.get("name", "")
        if symptom_name in AMBIGUOUS_SYMPTOMS:
            ambiguous_info = AMBIGUOUS_SYMPTOMS[symptom_name]
            questions = ambiguous_info.get("clarification_questions", [])
            priority = ambiguous_info.get("priority", "important")
            
            missing_info["has_missing_info"] = True
            missing_info["missing_fields"].append(f"ambiguous_symptom_{symptom_name}")
            
            # 優先度に応じて分類
            if priority == "critical":
                missing_info["critical_questions"].extend(questions)
                if missing_info["priority"] != "critical":
                    missing_info["priority"] = "critical"
            else:
                missing_info["questions"].extend(questions)
                if missing_info["priority"] not in ["critical", "important"] and priority == "important":
                    missing_info["priority"] = "important"
    
    # 1. 年齢チェック（重要だが推奨は継続）
    if user_info.get('age') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("age")
        missing_info["questions"].append("年齢を教えてください。（より適切な医薬品選択のため）")
        # 年齢不明でも推奨は継続（importantレベルに変更）
        if missing_info["priority"] != "critical":
            missing_info["priority"] = "important"
    
    # 2. 症状が検出されない場合（criticalのまま維持）
    symptoms = nlu_result.get('symptoms', [])
    if not symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptoms")
        missing_info["questions"].append("具体的にどのような症状がありますか？（例：頭痛、発熱、咳、鼻水など）")
        missing_info["priority"] = "critical"
    
    # 3. 性別チェック
    if user_info.get('gender') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("gender")
        missing_info["questions"].append("性別を教えてください。（男性/女性）")
        if missing_info["priority"] != "critical":
            missing_info["priority"] = "important"
    
    # 4. 妊娠・授乳状態の確認（女性または性別不明の場合）
    # 妊娠・授乳の両方が未回答の場合のみ質問（どちらか一方でも回答済みなら質問しない）
    pregnancy_answered = user_info.get('pregnant') is not None
    breastfeeding_answered = user_info.get('breastfeeding') is not None
    
    if user_info.get('gender') == '女性' or user_info.get('gender') is None:
        if not pregnancy_answered and not breastfeeding_answered:
            # 年齢から妊娠可能性を判断
            age = user_info.get('age')
            # 年齢が不明でも念のため確認（または15-50歳の範囲）
            if age is None or (age and 15 <= age <= 50):
                missing_info["has_missing_info"] = True
                missing_info["missing_fields"].append("pregnancy_status")
                missing_info["questions"].append("現在、妊娠中または授乳中ですか？（はい/いいえ）")
                if missing_info["priority"] != "critical":
                    missing_info["priority"] = "important"
    
    # 5. 症状の期間チェック
    # user_infoのsymptom_duration_daysもチェック
    has_duration = any(s.get('duration_days') is not None for s in symptoms) or user_info.get('symptom_duration_days') is not None
    if not has_duration and symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptom_duration")
        missing_info["questions"].append("症状はいつ頃から続いていますか？（例：昨日から、3日前から）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"
    
    # 6. 現在服用中の薬の確認
    # current_medicationsが未設定、または空リストの場合のみ質問
    medications = user_info.get('current_medications')
    medications_answered = medications is not None and isinstance(medications, list)
    
    if not medications_answered:
        # 症状がある場合は確認
        if symptoms:
            missing_info["has_missing_info"] = True
            missing_info["missing_fields"].append("current_medications")
            missing_info["questions"].append("現在、他に服用している薬はありますか？（ある場合は薬の名前を教えてください）")
            if missing_info["priority"] not in ["critical", "important"]:
                missing_info["priority"] = "optional"
    
    # 7. アレルギーの確認
    # allergiesが未設定、または空リストの場合のみ質問
    allergies = user_info.get('allergies')
    allergies_answered = allergies is not None and isinstance(allergies, list) and len(allergies) > 0
    
    if not allergies_answered:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("allergies")
        missing_info["questions"].append("薬や食品のアレルギーはありますか？（ある場合は具体的に教えてください）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"
    
    return missing_info

# ================================================================================
# 6. メイン推奨関数
# ================================================================================

def rule_based_recommendation(
    user_text: str,
    user_info: Dict,
    medicine_df: pd.DataFrame,
    client: OpenAI,
    top_n: int = 3,
    session_id: str = None
) -> Dict:
    """
    ルールベース医薬品推奨システムのメイン関数（全医薬品種類対応）
    
    Args:
        user_text: ユーザーの症状入力
        user_info: {
            'age': int,
            'gender': str,
            'pregnant': bool,
            'breastfeeding': bool,
            'current_medications': List[str],
            'allergies': List[str]
        }
        medicine_df: 医薬品データフレーム
        client: OpenAI client
        top_n: 推奨する医薬品の数
    
    Returns:
        推奨結果
    """
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n{'='*80}")
        logger.debug(f"ルールベース医薬品推奨システム 開始")
        logger.debug(f"{'='*80}")
        logger.debug(f"症状文: {user_text}")
        logger.debug(f"ユーザー情報: {user_info}")
    
    # ステップ1: NLU（症状抽出）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1: NLU（症状抽出） ---")
    nlu_result = hybrid_nlu_extraction(user_text, user_info, client, session_id)
    
    # confidenceチェック（0.4未満の場合はGPTフォールバックを検討）
    confidence_score = nlu_result.get('confidence_score', 0.0)
    symptoms_count = len(nlu_result.get("symptoms", []))
    
    logger.info(f"NLU信頼度スコア: {confidence_score:.2f}, 検出症状数: {symptoms_count}")
    
    # ステップ1.5: 不足情報のチェック
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1.5: 不足情報のチェック ---")
    missing_info_result = check_missing_information(user_info, nlu_result)
    
    if missing_info_result["has_missing_info"]:
        priority = missing_info_result["priority"]
        logger.info(f"不足情報検出（優先度: {priority}）")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"不足フィールド: {missing_info_result['missing_fields']}")
        
        # 症状が検出されていない場合のみ推奨を中断
        # 曖昧症状の質問だけがcriticalの場合は推奨を継続
        missing_fields = missing_info_result.get('missing_fields', [])
        if "symptoms" in missing_fields:
            # 症状が検出されていない場合のみ推奨を中断
            logger.warning(f"症状が検出されていないため推奨を中断します")
            return {
                "status": "missing_critical_info",
                "reason": "症状が検出されていません",
                "missing_fields": missing_info_result['missing_fields'],
                "questions": missing_info_result['questions'],
                "critical_questions": missing_info_result.get('critical_questions', []),
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 曖昧症状の質問がある場合でも推奨は継続
            logger.info(f"推奨は続行しますが、追加質問も表示します")
    
    # ステップ2: インフルエンザリスク検出
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ2: インフルエンザリスク検出 ---")
    influenza_risk, influenza_reason = detect_influenza_risk(nlu_result, user_text)
    if influenza_risk:
        logger.warning(f"インフルエンザの可能性: {influenza_reason}")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"インフルエンザリスク: なし")
    
    # ステップ3: 安全性チェック
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ3: 安全性チェック ---")
    safety_result = check_safety_contraindications(user_info, nlu_result)
    
    if safety_result["requires_escalation"]:
        logger.warning(f"エスカレーション必要: {safety_result['escalation_reason']}")
        return {
            "status": "escalation_required",
            "reason": safety_result["escalation_reason"],
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "influenza_risk": influenza_risk,
            "influenza_reason": influenza_reason,
            "timestamp": datetime.now().isoformat()
        }
    
    # ステップ4: 候補医薬品取得（インフルエンザリスクを考慮）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ4: 候補医薬品取得 ---")
    candidates = get_candidate_medicines(nlu_result, medicine_df, user_text, influenza_risk)
    
    if not candidates:
        logger.warning("該当する候補医薬品が見つかりませんでした")
        return {
            "status": "no_candidates",
            "reason": "該当する医薬品が見つかりませんでした",
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "confidence_score": confidence_score,  # confidence_scoreを追加
            "timestamp": datetime.now().isoformat()
        }
    
    # ステップ5: 二段階スコアリング（高速化）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5: スコアリング（二段階方式） ---")
    else:
        logger.info("ステップ5: スコアリング開始")
    
    # ステップ5.1: 簡易スコアリング（高速）
    def calculate_quick_score(candidate: Dict, nlu_result: Dict, user_info: Dict) -> float:
        """簡易スコア（症状マッチ、効能特異性、年齢適合性を含む）"""
        from scoring_utils import calculate_efficacy_specificity_score
        symptom_score = calculate_symptom_match_score(candidate, nlu_result)
        efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
        age_score = calculate_age_fit_score(candidate, user_info)
        # 年齢適合性も含めて精度向上（重みは症状:効能:年齢 = 0.5:0.3:0.2）
        return (symptom_score * 0.5 + efficacy_score * 0.3 + age_score * 0.2)
    
    # 簡易スコアで上位N×10件を選別（精度向上のため15件から30件に増加）
    # 候補数が少ない場合は全件を詳細スコアリング（精度確保）
    selection_count = min(top_n * 30, len(candidates))
    quick_scores = [(calculate_quick_score(c, nlu_result, user_info), c) for c in candidates]
    quick_scores_sorted = sorted(quick_scores, key=lambda x: x[0], reverse=True)
    top_candidates_for_scoring = quick_scores_sorted[:selection_count]
    
    # 簡易スコアが0.3以上の場合も含める（閾値ベースの選別）
    threshold_candidates = [(score, c) for score, c in quick_scores if score >= 0.3]
    if len(threshold_candidates) > selection_count:
        # 閾値を超える候補が多い場合は、それらも含める
        top_candidates_for_scoring = sorted(threshold_candidates, key=lambda x: x[0], reverse=True)
        logger.info(f"閾値ベース選別: 簡易スコア0.3以上の候補 {len(top_candidates_for_scoring)}件を選別")
    
    logger.info(f"簡易スコアリング完了: {len(candidates)}件 → 上位{len(top_candidates_for_scoring)}件を選別")
    
    # ステップ5.2: 詳細スコアリング（選別された候補のみ）
    for score, candidate in top_candidates_for_scoring:
        score_result = calculate_final_score(candidate, nlu_result, user_info)
        candidate['final_score'] = score_result['total_score']
        candidate['score_breakdown'] = score_result['score_breakdown']
        if 'allergy_warning' in score_result:
            candidate['allergy_warning'] = score_result['allergy_warning']
        if 'interaction_warnings' in score_result:
            candidate['interaction_warnings'] = score_result['interaction_warnings']
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"{candidate['product_name']}: {candidate['final_score']:.3f}")
    
    # ステップ5.3: 詳細スコアで上位N件を選択
    candidates_sorted = sorted([c for _, c in top_candidates_for_scoring], 
                              key=lambda x: x['final_score'], reverse=True)
    top_candidates = ensure_ingredient_diversity(candidates_sorted, top_n=top_n)
    
    logger.info(
        f"詳細スコアリング完了: {len(top_candidates_for_scoring)}件 → 上位{len(top_candidates)}件を選択（成分多様性考慮）"
    )
    
    # ステップ5.5: 推奨後の検証処理
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5.5: 推奨後の検証処理 ---")
    validated_candidates = _finalize_recommendations(top_candidates, nlu_result, influenza_risk)
    
    # ステップ6: 説明生成
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ6: 説明生成 ---")
    recommendations = []
    for i, candidate in enumerate(validated_candidates, 1):
        explanation = generate_explanation(candidate, nlu_result, safety_result, user_info)
        
        recommendation_item = {
            "rank": i,
            "number": i,  # ChatGPTベース互換性のため追加
            "product_name": candidate['product_name'],
            "manufacturer": candidate['manufacturer'],
            "medicine_type": candidate['medicine_type'],
            "classification": candidate.get('classification', ''),  # C列
            "efficacy": candidate['efficacy'],  # E列
            "usage": candidate['usage'],  # F列
            "age_restriction": candidate.get('age_restriction', ''),  # G列
            "ingredients": candidate['ingredients'],  # H列
            "doping_prohibited": candidate.get('doping_prohibited', ''),  # I列
            "competition_category": candidate.get('competition_category', ''),  # J列
            "conditions": candidate.get('conditions', ''),  # K列
            "usage_notes": candidate.get('usage_notes', '用法用量を守ってご使用ください。'),
            "score": candidate['final_score'],
            "score_breakdown": candidate.get('score_breakdown', {}),
            "explanation": explanation,
            "reason": explanation,  # ChatGPTベース互換性のため追加
            "allergy_warning": candidate.get('allergy_warning', ''),
            "interaction_warnings": candidate.get('interaction_warnings', [])
        }
        
        # リスク警告を追加
        if candidate.get('risk_warning'):
            recommendation_item['risk_warning'] = candidate['risk_warning']
        if candidate.get('low_score_warning'):
            recommendation_item['low_score_warning'] = True
        
        recommendations.append(recommendation_item)
    
    # ステップ7: 使用上の注意と医師相談アドバイスをChatGPTで生成
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ7: 使用上の注意と医師相談アドバイスの生成 ---")
    usage_and_consultation = generate_usage_notes_and_consultation_with_gpt(
        recommendations, nlu_result, user_info, client
    )
    
    logger.info(f"推奨完了: {len(recommendations)}件の医薬品を推奨")
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"{'='*80}")
    
    # score_breakdownのJSON出力（デバッグ・トレース用）
    score_breakdown_json = None
    if recommendations:
        try:
            score_breakdowns = [r.get('score_breakdown', {}) for r in recommendations]
            score_breakdown_json = json.dumps(score_breakdowns, ensure_ascii=False, indent=2)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"📊 Score Breakdown JSON:\n{score_breakdown_json}")
        except Exception as e:
            logger.warning(f"Score breakdown JSON化エラー: {e}")
    
    # 不足情報の質問を追加（すべての優先度で表示）
    additional_questions = []
    missing_priority = None
    if missing_info_result.get("has_missing_info"):
        additional_questions = missing_info_result.get("questions", [])
        missing_priority = missing_info_result.get("priority")
    
    return {
        "status": "success",
        "recommended_medicines": recommendations,
        "warnings": safety_result["warnings"],
        "usage_notes": usage_and_consultation.get('usage_notes', ''),
        "doctor_consultation": usage_and_consultation.get('doctor_consultation', ''),
        "additional_questions": additional_questions,
        "critical_questions": missing_info_result.get("critical_questions", []),  # 新規追加
        "missing_priority": missing_priority,
        "nlu_result": nlu_result,
        "influenza_risk": influenza_risk,  # 新規追加
        "influenza_reason": influenza_reason,  # 新規追加
        "confidence_score": confidence_score,  # confidence_scoreを追加
        "score_breakdown_json": score_breakdown_json,  # デバッグ用JSON出力
        "timestamp": datetime.now().isoformat()
    }

def generate_explanation(candidate: Dict, nlu_result: Dict, safety_result: Dict, user_info: Dict) -> str:
    """
    推奨理由の説明を生成（スコア内訳に基づく詳細版）
    """
    explanation_parts = []
    
    # スコア内訳に基づく詳細説明
    score_breakdown = candidate.get('score_breakdown', {})
    
    # 症状適合度の説明
    symptom_match = score_breakdown.get('symptom_match', 0)
    if symptom_match > 0.8:
        matched_symptoms = []
        efficacy_text = candidate.get('efficacy', '')
        for symptom in nlu_result.get("symptoms", []):
            symptom_name = symptom.get("name")
            if symptom_name and symptom_name in efficacy_text:
                matched_symptoms.append(symptom_name)
        
        if matched_symptoms:
            explanation_parts.append(f"✅ 症状に非常によく適合: {', '.join(matched_symptoms)}に特化した効果")
        else:
            explanation_parts.append("✅ 症状に非常によく適合")
    elif symptom_match > 0.6:
        explanation_parts.append("✅ 症状に適度に適合")
    else:
        explanation_parts.append("⚠️ 症状への適合度は中程度")
    
    # 効能特異性の説明
    efficacy_specificity = score_breakdown.get('efficacy_specificity', 0)
    if efficacy_specificity > 0.7:
        explanation_parts.append("✅ 効能が症状に特化")
    elif efficacy_specificity > 0.5:
        explanation_parts.append("✅ 効能が適度に特化")
    
    # 副作用リスクの説明
    side_effect_risk = score_breakdown.get('side_effect_risk', 0)
    if side_effect_risk < -0.3:
        explanation_parts.append("⚠️ 副作用リスクがやや高め")
    elif side_effect_risk < -0.1:
        explanation_parts.append("⚠️ 軽度の副作用リスク")
    else:
        explanation_parts.append("✅ 副作用リスクは低め")
    
    # 相互作用リスクの説明
    interaction_risk = score_breakdown.get('interaction_risk', 0)
    if interaction_risk < -0.2:
        explanation_parts.append("⚠️ 薬物相互作用の可能性")
    elif interaction_risk < -0.1:
        explanation_parts.append("⚠️ 軽度の相互作用リスク")
    else:
        explanation_parts.append("✅ 相互作用リスクは低め")
    
    # 年齢適合性の説明
    age_fit = score_breakdown.get('age_fit', 0)
    user_age = user_info.get('age')
    if age_fit > 0.8:
        explanation_parts.append("✅ 年齢制限に適合")
    elif age_fit < 0.5:
        age_restriction = candidate.get('age_restriction', '')
        if age_restriction:
            explanation_parts.append(f"⚠️ 年齢制限: {age_restriction}")
    
    # 用法簡便性の説明
    usage_convenience = score_breakdown.get('usage_convenience', 0)
    if usage_convenience > 0.7:
        explanation_parts.append("✅ 服用が簡便")
    elif usage_convenience < 0.3:
        explanation_parts.append("⚠️ 服用回数が多い")
    
    # 主要成分の説明
    ingredients = candidate.get('ingredients', '')
    if ingredients:
        ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()][:3]
        if ingredient_list:
            explanation_parts.append(f"主成分: {', '.join(ingredient_list)}")
    
    # 医薬品の種類
    medicine_type = candidate.get('medicine_type', '')
    if medicine_type:
        explanation_parts.append(f"{medicine_type}として効果が期待できます")
    
    # 症状特異性ペナルティの説明
    symptom_specificity_penalty = score_breakdown.get('symptom_specificity_penalty', 0)
    if symptom_specificity_penalty < -0.2:
        explanation_parts.append(f"⚠️ 症状への特異性: 複合薬のため、単一症状への適合度はやや低めです")
    
    # リスク成分ペナルティの説明
    risk_ingredient_penalty = score_breakdown.get('risk_ingredient_penalty', 0)
    if risk_ingredient_penalty < -0.2:
        risk_ingredient = candidate.get('risk_ingredient', '')
        if risk_ingredient:
            explanation_parts.append(f"⚠️ リスク成分含有: {risk_ingredient}が含まれています")
    
    # リスク警告がある場合（candidateから取得）
    if candidate.get('risk_warning'):
        explanation_parts.append(f"⚠️ {candidate.get('risk_warning')}")
    
    # 低スコア警告
    if candidate.get('low_score_warning'):
        explanation_parts.append("⚠️ 推奨スコアが低めです。使用前に薬剤師または登録販売者にご相談ください。")
    
    # 警告がある場合
    if safety_result.get("warnings"):
        for warning in safety_result['warnings']:
            explanation_parts.append(f"⚠️ {warning}")
    
    return " | ".join(explanation_parts)

# ================================================================================
# 6. ChatGPTによる使用上の注意と医師相談アドバイスの生成
# ================================================================================

def generate_individual_usage_notes_with_gpt(
    medicine: Dict,
    client: OpenAI
) -> str:
    """
    個別の医薬品について、CSVのE〜K列を使ってChatGPTで使用上の注意を生成
    """
    prompt = f"""
あなたは登録販売者です。以下の医薬品情報から、使用上の注意を簡潔に生成してください。

【医薬品情報】
製品名: {medicine.get('product_name', '')}
効能効果（E列）: {medicine.get('efficacy', '')}
用法用量（F列）: {medicine.get('usage', '')}
年齢制限（G列）: {medicine.get('age_restriction', '')}
禁止物質（I列）: {medicine.get('doping_prohibited', '')}

【生成ルール】
1. 効能: E列の効能効果を全文記載（省略しない）
2. 用法用量の注意: F列から重要な注意を2〜3項目、100字以内に要約
   - 「用法用量を厳守」は他で記載済みなので省略
   - 小児・乳幼児への注意など、この医薬品特有の注意のみ記載
   - 箇条書き形式
3. 年齢制限: G列にある場合のみ記載
4. ドーピング: I列に「禁止物質あり」がある場合のみ記載

【出力形式】
効能: [全文]

用法用量の注意:
・[この医薬品特有の注意1]
・[この医薬品特有の注意2]

年齢制限: [ある場合のみ]

ドーピング: [ある場合のみ]

【除外すべき内容】
- 服用方法（＜○○の服用方法＞）
- 一般的な注意（用法用量を厳守、など）
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは登録販売者です。効能は詳細に、用法用量の注意は簡潔に要約してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        
        result = response.choices[0].message.content
        return result.strip()
        
    except Exception as e:
        logger.warning(f"個別使用上の注意生成エラー: {e}")
        # フォールバック - CSVデータから完全な情報を取得
        notes = []
        
        # 効能
        efficacy = medicine.get('efficacy', '')
        if efficacy:
            # 全文表示
            notes.append(f"効能: {efficacy}")
        
        # 年齢制限
        age_restriction = medicine.get('age_restriction', '')
        import math
        if isinstance(age_restriction, float):
            if not math.isnan(age_restriction):
                try:
                    age_val = int(age_restriction)
                    notes.append(f"年齢制限: {age_val}歳以上の方が対象です。")
                except:
                    pass
        elif age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
            notes.append(f"年齢制限: {age_restriction}")
        
        # F列（用法用量）から注意事項を抽出（服用方法と一般的な注意は除外）
        usage = medicine.get('usage', '')
        if usage and '注意' in usage:
            usage_lines = usage.split('\n')
            caution_items = []
            skip_section = False
            
            for i, line in enumerate(usage_lines):
                line = line.strip()
                
                # 服用方法セクションはスキップ
                if '服用方法' in line:
                    skip_section = True
                    continue
                elif line.startswith('＜') and '注意' in line:
                    skip_section = False
                    continue
                
                if skip_section or not line:
                    continue
                
                # 番号付きリストを検出（１．、２．など）
                if re.match(r'^[１-９1-9０-９][\．\.]', line):
                    # 一般的な注意を除外
                    if '用法・用量を厳守' in line or '用法用量を厳守' in line:
                        continue
                    if '定められた用法・用量' in line:
                        continue
                    
                    # 特有の注意のみ抽出して簡潔に
                    content = re.sub(r'^[１-９1-9０-９][\．\.]', '', line).strip()
                    
                    # 長い文を要約
                    if '小児に服用させる' in content:
                        caution_items.append('小児服用時は保護者の監督が必要')
                    elif '乳幼児' in content and '医師' in content:
                        caution_items.append('2歳未満は医師の診療を優先')
                    elif '分割' in content and '服用' in content:
                        caution_items.append('分割服用は2日以内に使用')
                    elif len(content) > 10:  # その他の重要な注意
                        # 30字以内に要約
                        summary = content[:30] + ('...' if len(content) > 30 else '')
                        caution_items.append(summary)
            
            # 箇条書きで追加（最大3項目）
            if caution_items:
                notes.append('\n用法用量の注意:')
                for item in caution_items[:3]:
                    notes.append(f'・{item}')
        
        # ドーピング情報
        doping = medicine.get('doping_prohibited', '')
        competition_category = medicine.get('competition_category', '')
        conditions = medicine.get('conditions', '')
        
        if doping and '禁止物質あり' in doping:
            doping_note = f"ドーピング禁止物質: {doping}"
            if competition_category:
                doping_note += f"\n競技会区分: {competition_category}"
            if conditions:
                doping_note += f"\n条件: {conditions}"
            notes.append(doping_note)
        
        return '\n'.join(notes) if notes else '用法用量を守ってご使用ください。'

def generate_usage_notes_and_consultation_with_gpt(
    recommended_medicines: List[Dict],
    nlu_result: Dict,
    user_info: Dict,
    client: OpenAI
) -> Dict:
    """
    選択された医薬品のCSVデータをChatGPTに渡して、
    使用上の注意と医師相談が必要な場合のアドバイスを生成
    
    3件まとめて1回のAPI呼び出しで処理（高速化）
    """
    import math
    
    # 3件の医薬品情報を構造化してプロンプトに含める
    medicines_info = []
    for i, med in enumerate(recommended_medicines, 1):
        age_restriction = med.get('age_restriction', '')
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            age_restriction = ''
        
        medicines_info.append({
            "number": i,
            "product_name": med.get('product_name', ''),
            "efficacy": med.get('efficacy', ''),
            "usage": med.get('usage', ''),
            "age_restriction": age_restriction if isinstance(age_restriction, str) else str(age_restriction) if age_restriction else '',
            "doping_prohibited": med.get('doping_prohibited', '')
        })
    
    # バッチ処理用のプロンプト
    prompt = f"""
あなたは登録販売者です。以下の3つの医薬品について、それぞれの使用上の注意を簡潔に生成してください。

【医薬品情報】

"""
    
    for med_info in medicines_info:
        prompt += f"""
{med_info['number']}つ目：{med_info['product_name']}
効能効果: {med_info['efficacy']}
用法用量: {med_info['usage']}
年齢制限: {med_info['age_restriction'] if med_info['age_restriction'] else 'なし'}
禁止物質: {med_info['doping_prohibited'] if med_info['doping_prohibited'] else 'なし'}

"""
    
    prompt += """
【生成ルール】
1. 各医薬品ごとに「{number}つ目：{product_name}」として明確に分離してください
2. 効能: 効能効果を全文記載（省略しない）
3. 用法用量の注意: 用法用量から重要な注意を2〜3項目、100字以内に要約
   - 「用法用量を厳守」は他で記載済みなので省略
   - 小児・乳幼児への注意など、この医薬品特有の注意のみ記載
   - 箇条書き形式
4. 年齢制限: 年齢制限がある場合のみ記載
5. ドーピング: 禁止物質がある場合のみ記載

【出力形式】
以下のJSON形式で回答してください：
{
  "medicines": [
    {{
      "number": 1,
      "product_name": "製品名",
      "usage_notes": "効能: [全文]\\n\\n用法用量の注意:\\n・[注意1]\\n・[注意2]\\n\\n年齢制限: [ある場合のみ]\\n\\nドーピング: [ある場合のみ]"
    }},
    {{
      "number": 2,
      "product_name": "製品名",
      "usage_notes": "..."
    }},
    {{
      "number": 3,
      "product_name": "製品名",
      "usage_notes": "..."
    }}
  ]
}

注意：
- 各医薬品の情報は必ず分離してください
- JSON形式で正確に出力してください
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは登録販売者です。効能は詳細に、用法用量の注意は簡潔に要約してください。JSON形式で正確に出力してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # 個別の使用上の注意を整形
        individual_notes = []
        medicines_dict = {m['number']: m for m in result_json.get('medicines', [])}
        
        for i, med in enumerate(recommended_medicines, 1):
            med_result = medicines_dict.get(i)
            if med_result:
                individual_note = med_result.get('usage_notes', '')
            else:
                # フォールバック: 個別生成関数を使用
                individual_note = generate_individual_usage_notes_with_gpt(med, client)
            
            # 年齢制限の表示（G列から）
            age_restriction = med.get('age_restriction', '')
            age_restriction_display = ''
            
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            
            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                if '15歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 15歳以上の方が対象です。'
                elif '7歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 7歳以上の方が対象です。'
                elif '12歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 12歳以上の方が対象です。'
                else:
                    import re
                    match = re.search(r'(\d+)歳', age_restriction)
                    if match:
                        age_val = match.group(1)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
            elif isinstance(age_restriction, (int, float)):
                if not (isinstance(age_restriction, float) and math.isnan(age_restriction)):
                    try:
                        age_val = int(age_restriction)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
                    except (ValueError, OverflowError):
                        pass
            
            # 個別の注意を整形
            note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
            if age_restriction_display and age_restriction_display not in individual_note:
                note_text += f"\n{age_restriction_display}"
            
            individual_notes.append(note_text)
        
        # 個別の使用上の注意を結合
        usage_notes_individual = '\n\n'.join(individual_notes)
        
    except Exception as e:
        logger.warning(f"バッチ処理エラー: {e}。フォールバック: 個別処理に切り替えます")
        # フォールバック: 個別処理
        individual_notes = []
        for i, med in enumerate(recommended_medicines, 1):
            individual_note = generate_individual_usage_notes_with_gpt(med, client)
            
            # 年齢制限の表示（G列から）
            age_restriction = med.get('age_restriction', '')
            age_restriction_display = ''
            
            import math
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            
            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                if '15歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 15歳以上の方が対象です。'
                elif '7歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 7歳以上の方が対象です。'
                elif '12歳未満' in age_restriction:
                    age_restriction_display = '年齢制限: 12歳以上の方が対象です。'
                else:
                    import re
                    match = re.search(r'(\d+)歳', age_restriction)
                    if match:
                        age_val = match.group(1)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
            elif isinstance(age_restriction, (int, float)):
                if not (isinstance(age_restriction, float) and math.isnan(age_restriction)):
                    try:
                        age_val = int(age_restriction)
                        age_restriction_display = f'年齢制限: {age_val}歳以上の方が対象です。'
                    except (ValueError, OverflowError):
                        pass
            
            # 個別の注意を整形
            note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
            if age_restriction_display:
                note_text += f"\n{age_restriction_display}"
            
            individual_notes.append(note_text)
        
        usage_notes_individual = '\n\n'.join(individual_notes)
    
    # 全体の使用上の注意を生成（共通の禁忌事項）
    general_notes = generate_default_usage_notes_and_consultation(recommended_medicines, user_info)
    
    # 個別の注意 + 共通の注意を結合
    usage_notes_combined = usage_notes_individual + '\n\n' + general_notes['usage_notes']
    doctor_consultation = general_notes['doctor_consultation']
    
    logger.info(f"使用上の注意生成完了: {len(individual_notes)}件")
    
    return {
        "usage_notes": usage_notes_combined,
        "doctor_consultation": doctor_consultation
    }

def generate_default_usage_notes_and_consultation(recommended_medicines: List[Dict], user_info: Dict) -> Dict:
    """
    デフォルトの使用上の注意と医師相談アドバイスを生成（フォールバック用）
    推奨医薬品のCSVデータから禁忌情報を抽出（年齢制限は個別に表示するので除く）
    """
    usage_notes_parts = []
    
    # 使ってはいけない人の情報を追加（年齢制限は個別表示なので除く）
    contraindications_parts = ["【使ってはいけない人】"]
    
    # 年齢に基づく禁忌
    user_age = user_info.get('age')
    if user_age:
        if user_age < 7:
            contraindications_parts.append("・7歳未満のお子様（医師の診察を受けてください）")
        elif user_age < 15:
            contraindications_parts.append("・一部の医薬品は15歳未満の方は使用できません")
    
    # 妊娠・授乳
    if user_info.get('pregnant'):
        contraindications_parts.append("・妊娠中の方（特にNSAIDs含有製品は禁忌）")
    if user_info.get('breastfeeding'):
        contraindications_parts.append("・授乳中の方（医師にご相談ください）")
    
    # 一般的な禁忌
    contraindications_parts.extend([
        "・過去に医薬品でアレルギー症状を起こしたことがある方",
        "・医師の治療を受けている方",
        "・高齢者の方（医師や薬剤師にご相談ください）"
    ])
    
    usage_notes_parts.extend(contraindications_parts)
    
    # 一般的な使用上の注意
    usage_notes_parts.extend([
        "",
        "【服用時の注意】",
        "・用法用量を厳守してください",
        "・なるべく空腹時の服用は避けてください",
        "・アレルギー体質の方は成分を確認してください",
        "・服用後、乗り物や機械の運転操作をしないでください（眠気が出る場合があります）"
    ])
    
    if user_info.get('age') and user_info['age'] < 15:
        usage_notes_parts.append("・小児が服用する場合は保護者の監督のもとで服用してください")
    
    # 医師相談が必要な場合
    doctor_consultation_parts = [
        "【以下の場合は医師にご相談ください】",
        "・症状が3日以上続く場合",
        "・症状が悪化する場合",
        "・高熱（38.5度以上）が続く場合",
        "・発疹、発赤、かゆみなどの副作用が現れた場合",
        "・他の症状が現れた場合",
        "・長期連用する場合"
    ]
    
    if user_info.get('pregnant') or user_info.get('breastfeeding'):
        doctor_consultation_parts.insert(1, "・妊娠中・授乳中の方は事前に医師にご相談ください")
    
    return {
        "usage_notes": '\n'.join(usage_notes_parts),
        "doctor_consultation": '\n'.join(doctor_consultation_parts)
    }

# ================================================================================
# 7. ロギング関数
# ================================================================================

def log_recommendation_session(user_text: str, user_info: Dict, result: Dict, log_file: str = "recommendation_log.jsonl"):
    """
    推奨セッションをログに保存（監査用）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_text": user_text,
        "user_info": user_info,
        "result": result
    }
    
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(log_dir, "log", log_file)
    
    # logディレクトリがなければ作成
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ログ保存完了: {log_path}")

# ================================================================================
# 7. ラッパー関数（app.pyから呼び出し用）
# ================================================================================

def rule_based_medicine_recommendation(
    user_text: str,
    user_info: Dict,
    client: OpenAI,
    top_n: int = 3,
    session_id: str = None
) -> Dict:
    """
    ルールベース医薬品推奨システムのラッパー関数（app.pyから呼び出し用）
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報
        client: OpenAI client
        top_n: 推奨医薬品数
        session_id: セッションID（キャッシュ用）
    
    Returns:
        推奨結果
    """
    # CSVデータを読み込み
    medicine_df = pd.read_csv('otc_medicine_data.csv')
    
    # メイン関数を呼び出し
    result = rule_based_recommendation(
        user_text=user_text,
        user_info=user_info,
        medicine_df=medicine_df,
        client=client,
        top_n=top_n,
        session_id=session_id
    )
    
    return result
