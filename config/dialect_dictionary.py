"""
方言辞書定義モジュール
主要な方言（関西弁、東北弁、九州弁、名古屋弁、和歌山弁など）の表現を標準語にマッピング
"""

import re
from typing import Dict, List, Optional

# 5段階の重症度定義
SEVERITY_LEVELS = {
    "重度": 5,
    "やや重度": 4,
    "中等度": 3,
    "軽度": 2,
    "やや軽度": 1,
    None: 0
}

# escalation_scoreの計算式（重み付き加算）
ESCALATION_SCORE_WEIGHTS = {
    "重度": 2.0,
    "やや重度": 1.5,
    "中等度": 1.0,
    "軽度": 0.5,
    "やや軽度": 0.25
}

# escalation_scoreの閾値（設定可能、デフォルト4.0点）
# 現場の感覚に合わせて4.0に設定（重度×2回分で受診勧奨）
# 特に高齢の方の場合、複数の強調語は「痛みに耐えかねている」シグナル
ESCALATION_THRESHOLD = 4.0

# 変換保留リスト（多義性が高く、変換しない方が安全な語）
CONVERSION_EXCLUSION_LIST = [
    "えらい",  # 「偉い」の意味で使われる可能性が高い
]

# 方言辞書（症状関連を優先的に実装、Phase 2で拡張）
DIALECT_DICTIONARY = {
    "関西弁": {
        "えらい": {
            "standard": "疲れた",
            "standard_tokens": ["疲れた", "苦しい"],
            "symptom_related": True,
            "ambiguity_risk": "high",
            "context_keywords": ["疲", "だる", "しんど", "体調", "症状", "熱", "痛"],
            "exclude_patterns": [
                r"えらい\s*(人|方|先生|医師|こと|事|問題|仕事)",
                r"(先生|医師|人|方).*えらい"
            ],
            "regex_pattern": r"えらい",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "しんどい": {
            "standard": "つらい",
            "standard_tokens": ["つらい", "だるい", "疲れた"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"しんどい",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "きつい": {
            "standard": "つらい",
            "standard_tokens": ["つらい", "苦しい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])きつい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "めっちゃ": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"めっちゃ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "中等度",
            "escalation_score": 1.0
        },
        "めっちゃめちゃ": {
            "standard": "非常に",
            "standard_tokens": ["非常に", "とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"めっちゃめちゃ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "むっちゃ": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"むっちゃ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "中等度",
            "escalation_score": 1.0
        },
        "あかん": {
            "standard": "だめ",
            "standard_tokens": ["だめ", "悪い"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])あかん(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ほんま": {
            "standard": "本当",
            "standard_tokens": ["本当"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ほんま(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "なんでやねん": {
            "standard": "なぜ",
            "standard_tokens": ["なぜ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])なんでやねん(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "おおきに": {
            "standard": "ありがとう",
            "standard_tokens": ["ありがとう"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])おおきに(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "かいい": {
            "standard": "かゆい",
            "standard_tokens": ["かゆい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])かいい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ひやこい": {
            "standard": "冷たい",
            "standard_tokens": ["冷たい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ひやこい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "いびる": {
            "standard": "痛む",
            "standard_tokens": ["痛む", "痛い"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["痛", "傷", "けが"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])いびる(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "はしる": {
            "standard": "しみる",
            "standard_tokens": ["しみる", "痛む"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": ["傷", "傷口"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])はしる(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "むかつく": {
            "standard": "吐き気がする",
            "standard_tokens": ["吐き気", "むかつき"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["吐", "気持ち", "胃"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])むかつく(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "えずく": {
            "standard": "吐きそうになる",
            "standard_tokens": ["吐き気", "嘔気"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])えずく(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "きばる": {
            "standard": "いきむ",
            "standard_tokens": ["いきむ"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": ["便", "排便"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])きばる(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "へたる": {
            "standard": "疲れ果てる",
            "standard_tokens": ["疲れ果てる", "疲れた"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])へたる(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ようけ": {
            "standard": "たくさん",
            "standard_tokens": ["たくさん"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ようけ(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ぼちぼち": {
            "standard": "少しずつ",
            "standard_tokens": ["少しずつ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ぼちぼち(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        }
    },
    "東北弁": {
        "だば": {
            "standard": "だめ",
            "standard_tokens": ["だめ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(だば|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "しゃっこい": {
            "standard": "冷たい",
            "standard_tokens": ["冷たい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])しゃっこい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "なまら": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"なまら(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "こわい": {
            "standard": "体がだるい",
            "standard_tokens": ["体がだるい", "凝っている"],
            "symptom_related": True,
            "ambiguity_risk": "high",
            "context_keywords": ["体", "だる", "凝", "肩", "首"],
            "exclude_patterns": [
                r"こわい\s*(もの|こと|人|話|映画)",
                r"(怖い|恐い).*こわい"
            ],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])こわい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "いがつく": {
            "standard": "胃が痛む",
            "standard_tokens": ["胃痛", "胃が痛い"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])いがつく(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "んだ": {
            "standard": "そうだ",
            "standard_tokens": ["そうだ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(だば|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "んだば": {
            "standard": "そうだよ",
            "standard_tokens": ["そうだよ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(だば|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        }
    },
    "九州弁": {
        "ばい": {
            "standard": "だよ",
            "standard_tokens": ["だよ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [r"ばいきん"],
            "regex_pattern": r"(ばい|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "たい": {
            "standard": "だよ",
            "standard_tokens": ["だよ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(ばい|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ばり": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"ばり(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "中等度",
            "escalation_score": 1.0
        },
        "がばい": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"がばい(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "わっぜ": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"わっぜ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "ばってん": {
            "standard": "だけど",
            "standard_tokens": ["だけど"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ばってん(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "しゃーしか": {
            "standard": "仕方ない",
            "standard_tokens": ["仕方ない"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])しゃーしか(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "だるか": {
            "standard": "だるい",
            "standard_tokens": ["だるい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])だるか(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "よだきい": {
            "standard": "めんどくさい",
            "standard_tokens": ["めんどくさい", "だるい"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])よだきい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "いたぐい": {
            "standard": "痛い",
            "standard_tokens": ["痛い"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])いたぐい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "おなかがおどる": {
            "standard": "お腹が鳴る",
            "standard_tokens": ["お腹が鳴る", "お腹が痛む"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])おなかがおどる(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        }
    },
    "名古屋弁": {
        "だら": {
            "standard": "だよ",
            "standard_tokens": ["だよ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(だば|たい|んだ|やねん|だば)$",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "でら": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"でら(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "どえりゃあ": {
            "standard": "凄まじく",
            "standard_tokens": ["凄まじく", "とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"どえりゃあ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "えらい": {
            "standard": "疲れた",
            "standard_tokens": ["疲れた", "苦しい"],
            "symptom_related": True,
            "ambiguity_risk": "high",
            "context_keywords": ["疲", "だる", "しんど", "体調", "症状", "熱", "痛"],
            "exclude_patterns": [
                r"えらい\s*(人|方|先生|医師|こと|事|問題|仕事)",
                r"(先生|医師|人|方).*えらい"
            ],
            "regex_pattern": r"えらい",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "みゃー": {
            "standard": "みたい",
            "standard_tokens": ["みたい"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])みゃー(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "みゃーみゃー": {
            "standard": "みたいみたい",
            "standard_tokens": ["みたいみたい"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])みゃーみゃー(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ちんちん": {
            "standard": "とても熱い",
            "standard_tokens": ["とても熱い", "熱い"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["熱", "炎症", "患部"],
            "exclude_patterns": [],
            "regex_pattern": r"ちんちん(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "ぬくたい": {
            "standard": "暖かい",
            "standard_tokens": ["暖かい", "微熱"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["熱", "体温"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ぬくたい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        }
    },
    "和歌山弁": {
        "えらい": {
            "standard": "疲れた",
            "standard_tokens": ["疲れた", "苦しい"],
            "symptom_related": True,
            "ambiguity_risk": "high",
            "context_keywords": ["疲", "だる", "しんど", "体調", "症状", "熱", "痛"],
            "exclude_patterns": [
                r"えらい\s*(人|方|先生|医師|こと|事|問題|仕事)",
                r"(先生|医師|人|方).*えらい"
            ],
            "regex_pattern": r"えらい",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "しんどい": {
            "standard": "つらい",
            "standard_tokens": ["つらい", "だるい", "疲れた"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"しんどい",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "にえる": {
            "standard": "打ち身",
            "standard_tokens": ["打ち身", "打撲", "あざ", "青あざ", "あおたん", "筋肉痛", "炎症"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["打", "ぶつ", "痛", "あざ", "青", "筋肉", "あおたん"],
            "exclude_patterns": [],
            "regex_pattern": r"にえ(?:ています|ている|て|た|る)",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0,
            "multiple_symptoms": True,
            "symptom_weights": {
                "打ち身": 0.4,
                "打撲": 0.3,
                "あざ": 0.2,
                "青あざ": 0.1,
                "あおたん": 0.0,  # 同義語として認識されるが重みは低め
                "筋肉痛": 0.0,
                "炎症": 0.0
            }
        },
        "ごっつ": {
            "standard": "非常に",
            "standard_tokens": ["非常に", "とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"ごっつ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "重度",
            "escalation_score": 2.0
        },
        "ほんま": {
            "standard": "本当",
            "standard_tokens": ["本当"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ほんま(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "なんでやねん": {
            "standard": "なぜ",
            "standard_tokens": ["なぜ"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])なんでやねん(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": True,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "めっちゃ": {
            "standard": "とても",
            "standard_tokens": ["とても"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"めっちゃ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "中等度",
            "escalation_score": 1.0
        },
        "あかん": {
            "standard": "だめ",
            "standard_tokens": ["だめ", "悪い"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])あかん(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "おおきに": {
            "standard": "ありがとう",
            "standard_tokens": ["ありがとう"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])おおきに(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "けったい": {
            "standard": "変な",
            "standard_tokens": ["変な"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])けったい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "てんご": {
            "standard": "具合が悪い",
            "standard_tokens": ["具合が悪い", "体調不良"],
            "symptom_related": True,
            "ambiguity_risk": "medium",
            "context_keywords": ["体調", "具合"],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])てんご(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "はなげを出す": {
            "standard": "鼻水を出す",
            "standard_tokens": ["鼻水", "鼻汁"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])はなげを出す(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "おきやま": {
            "standard": "おたふく風邪",
            "standard_tokens": ["おたふく風邪"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])おきやま(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "くろにえ": {
            "standard": "青あざ",
            "standard_tokens": ["青あざ", "打ち身", "内出血"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])くろにえ(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "ちみ切る": {
            "standard": "つねる",
            "standard_tokens": ["つねる", "痛み"],
            "symptom_related": True,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])ちみ切る(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        }
    },
    "その他": {
        "やばい": {
            "standard": "危険",
            "standard_tokens": ["危険", "すごい"],
            "symptom_related": False,
            "ambiguity_risk": "medium",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"(?<![ぁ-んァ-ヶー一-龥])やばい(?![ぁ-んァ-ヶー一-龥])",
            "sentence_end_priority": False,
            "severity_tag": None,
            "escalation_score": 0.0
        },
        "だいぶ": {
            "standard": "かなり",
            "standard_tokens": ["かなり"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"だいぶ(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "中等度",
            "escalation_score": 1.0
        },
        "そうとう": {
            "standard": "相当",
            "standard_tokens": ["相当", "かなり"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"そうとう(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "やや重度",
            "escalation_score": 1.5
        },
        "ちょこっと": {
            "standard": "少し",
            "standard_tokens": ["少し"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"ちょこっと(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "やや軽度",
            "escalation_score": 0.25
        },
        "ちょびっと": {
            "standard": "わずかに",
            "standard_tokens": ["わずかに", "少し"],
            "symptom_related": False,
            "ambiguity_risk": "low",
            "context_keywords": [],
            "exclude_patterns": [],
            "regex_pattern": r"ちょびっと(?!きん)",
            "sentence_end_priority": False,
            "severity_tag": "やや軽度",
            "escalation_score": 0.25
        }
    }
}

# 感情・状態に関する否定語（is_diagnosis_onlyの例外処理用）
EMOTIONAL_NEGATIVE_WORDS = [
    "あかん", "だめ", "悪い", "つらい", "やばい", "しんどい",
    "きつい", "苦しい", "痛い", "辛い", "悲しい", "不安",
    "心配", "怖い", "恐ろしい", "嫌", "いや", "嫌だ",
    "困る", "困った", "大変", "ひどい", "最悪", "絶望",
    "諦め", "無理", "できない", "わからない", "助けて"
]

# 感情・状態に関する否定語のパターン
EMOTIONAL_NEGATIVE_PATTERNS = [
    r"(あかん|だめ|悪い|つらい|やばい|しんどい|きつい|苦しい)",
    r"(痛い|辛い|悲しい|不安|心配|怖い|恐ろしい)",
    r"(嫌|いや|嫌だ|困る|困った|大変|ひどい|最悪)",
    r"(絶望|諦め|無理|できない|わからない|助けて)"
]

# ストップワード保護リスト（2文字以上の名詞・症状語）
PROTECTED_WORDS = [
    "のど", "喉", "頭", "目", "鼻", "口", "歯", "耳",
    "胸", "心臓", "肺", "胃", "腸", "お腹", "腰", "背中",
    "手", "足", "腕", "脚", "関節", "筋肉", "皮膚",
    "頭痛", "腹痛", "胃痛", "歯痛", "関節痛", "筋肉痛",
    "発熱", "咳", "鼻水", "下痢", "便秘", "吐き気",
    "かゆみ", "発疹", "湿疹", "めまい", "疲労感", "倦怠感",
    "生理痛", "月経痛", "月経不順", "つわり"
]

