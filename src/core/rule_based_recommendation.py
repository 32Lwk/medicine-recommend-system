"""
ルールベース医薬品推奨システム

ChatGPT APIはNLU（症状抽出）のみに使用し、
医薬品推奨は登録販売者の判断を再現するルールベース/スコアリング型アルゴリズムで実装

後方互換のため、以下のシンボルは他モジュールから再エクスポートされています:
- 定数: recommendation_constants から import
- キャッシュ: nlu_service から import
- 安全性: safety_filter から import
- ログ: recommendation_logger から import
"""

# 後方互換のため再エクスポート（他モジュールから import 可能）
__all__ = [
    "rule_based_medicine_recommendation",
    "rule_based_recommendation",
    "detect_influenza_risk",
    "check_missing_information",
    "hybrid_nlu_extraction",
    "extract_symptoms_with_gpt",
    "simple_pattern_matching_nlu",
    "generate_explanation",
    "generate_usage_notes_and_consultation_with_gpt",
    "generate_default_usage_notes_and_consultation",
    "check_safety_contraindications",
    "check_sleep_medicine_safety",
    "log_recommendation_session",
    "get_cached_nlu_result",
    "set_cached_nlu_result",
    "clear_nlu_cache",
    "get_candidate_medicines",
    "filter_by_efficacy_symptom_match",
    "calculate_final_score",
    "calculate_medicine_score",
    "calculate_ingredient_based_boost",
    "check_ingredient_overlap",
    "classify_medicine_mechanism",
    "DEBUG_MODE",
    "SYMPTOM_DICTIONARY",
]

import pandas as pd
import os
import json
import re
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from src.core.scoring_utils import normalize_text

# ロガー設定
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# CSVファイルのパス設定（プロジェクトルート基準）
from src import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "otc_medicine_data.csv")

# 定数・データ構造は recommendation_constants からインポート（SRP改善）
from src.core.recommendation_constants import (
    DEFAULT_ADULT_AGE,
    PEDIATRIC_KEYWORDS,
    PEDIATRIC_USAGE_KEYWORDS,
    RED_FLAG_SYMPTOMS,
    PREGNANCY_SYMPTOMS,
    FEMALE_SPECIFIC_SYMPTOMS,
    DOCTOR_REFERRAL_CONDITIONS,
    CONTRAINDICATION_RULES,
    SCORING_WEIGHTS,
    RISK_INGREDIENTS_EXCLUDE,
    ANTIDIARRHEAL_INGREDIENTS,
    ANTIDIARRHEAL_KEYWORDS,
    MIN_SYMPTOM_MATCH_SINGLE,
    MIN_SYMPTOM_MATCH_MULTI,
    SPECIFIC_USE_PATTERNS,
    SPECIFIC_USE_EXCLUSION_KEYWORDS,
    COMPOUND_MEDICINE_INDICATORS,
    BODY_PART_SPECIFIC_KEYWORDS,
    SYMPTOM_CATEGORY_PENALTY,
    MULTI_SYMPTOM_COMBINATIONS,
    SYMPTOM_PATTERN_OPTIMIZATION,
    THROAT_SYMPTOM_TOKENS,
    THROAT_KEYWORD_TOKENS,
    THROAT_LIQUID_TOKENS,
    THROAT_SPECIFIC_INGREDIENTS,
    STOMACH_MUCOSAL_PROTECTANTS,
    STOMACH_MEDICINE_PRIORITY,
    CONSTIPATION_MEDICINE_PRIORITY,
    IRRITANT_LAXATIVE_INGREDIENTS,
    MAJOR_ANALGESIC_MEDICINES,
    ANALGESIC_PRIORITY,
    MENSTRUAL_MEDICINE_PRIORITY,
    THROAT_TOPICAL_PRIORITY,
    SLEEP_DISORDER_PRIORITY,
    WOUND_MEDICINE_PRIORITY,
    BURN_SEVERITY_KEYWORDS,
    RISK_INGREDIENTS_OVERLAP,
)

from src.core.dictionary_loader import load_ingredient_dictionary, load_symptom_dictionary

# 後方互換: app.py 等から SYMPTOM_DICTIONARY として参照される
SYMPTOM_DICTIONARY = load_symptom_dictionary()
from src.core.missing_info_service import (
    check_missing_information,
    generate_symptom_detail_questions_with_gpt,
    detect_burn_severity,
)
from src.core.explanation_generator import (
    generate_explanation,
    generate_individual_usage_notes_with_gpt,
    generate_usage_notes_and_consultation_with_gpt,
    generate_default_usage_notes_and_consultation,
)
from src.core.candidate_scoring import (
    _candidate_has_throat_liquid_signature,
    _has_motion_sickness_symptom,
    _is_kakkonto_medicine,
    _is_motion_sickness_medicine,
    _is_pediatric_specific,
    is_specific_use_medicine,
    is_comprehensive_cold_medicine,
    _is_symptom_matching_specific_use,
    _contains_risk_ingredient,
    _extract_min_age_value,
    _has_antidiarrheal_signal,
    _filter_antidiarrheal_without_diarrhea,
    has_symptom_in_efficacy,
    filter_by_efficacy_symptom_match,
    get_candidate_medicines,
    is_exact_product_match,
    _detect_body_part_specificity,
    calculate_symptom_match_score,
    calculate_age_fit_score,
    calculate_body_part_match_score,
    calculate_ingredient_based_boost,
    is_contraindicated,
    ensure_score_difference,
    calculate_display_score,
    calculate_display_score_absolute,
    extract_main_ingredients,
    check_ingredient_overlap,
    classify_medicine_mechanism,
    _recheck_risk_ingredients,
    _check_influenza_compatibility,
    detect_influenza_risk,
)

# ================================================================================
# 1. ヘルパー関数（候補取得・スコアリング関連は candidate_scoring から import）
# ================================================================================

# 部位特異的製品のキーワード辞書
BODY_PART_SPECIFIC_KEYWORDS = {
    "delicate_area": {  # デリケート部位（性器周辺を含む）
        "product_name_keywords": ["カブレーナ", "デリケート", "おりもの", "ナプキン", "性器", "陰部", "局部"],
        "efficacy_keywords": ["おむつかぶれ", "蒸れ", "デリケート部位", "おりもの", "性器", "陰部", "局部", "陰茎"],
        "usage_keywords": ["デリケート部位", "蒸れ", "おりもの", "性器", "陰部", "局部"]
    },
    "scalp": {  # 頭皮
        "product_name_keywords": ["頭皮", "フケ", "スカルプ"],
        "efficacy_keywords": ["頭皮", "フケ", "頭のかゆみ"],
        "usage_keywords": ["頭皮", "頭部"]
    },
    "throat": {  # のど
        "product_name_keywords": ["のど", "喉", "トローチ"],
        "efficacy_keywords": ["のどの痛み", "喉の痛み"],
        "usage_keywords": ["のど", "喉"]
    }
}

# 症状カテゴリ間優先表（症状×医薬品種類のペナルティ設定）
# 注意: AMBIGUOUS_SYMPTOMSは削除されました。症状詳細質問はChatGPTで生成します。
SYMPTOM_CATEGORY_PENALTY = {
    "発熱": {
        "風邪薬": -0.5,  # 単一症状の場合は複合薬にペナルティ（-0.3から-0.5に強化）
        "解熱鎮痛薬": 0.0,  # 単一症状の場合は特化薬を優先
        "鼻炎用薬": -0.5  # 発熱のみでは鼻炎薬は不適切
    },
    "のどの痛み": {
        "外用薬（のど）": 0.15,  # のど専用外用薬を最優先
        "外用薬（皮膚）": 0.10,  # のどスプレー等が含まれる可能性
        "解熱鎮痛薬": 0.0,  # のど痛に効果がある
        "風邪薬": -0.15,  # 単一症状では総合感冒薬は過剰
        "鼻炎用薬": -0.4  # のど痛のみでは鼻炎薬は不適切
    },
    "咳": {
        "風邪薬": -0.2,  # 咳のみの場合は総合感冒薬より鎮咳薬を優先
        "解熱鎮痛薬": -0.5,
        "鼻炎用薬": -0.3
    },
    "頭痛": {
        "風邪薬": -0.5,  # 頭痛のみの場合は解熱鎮痛薬を優先（-0.2から-0.5に強化）
        "解熱鎮痛薬": 0.0,
        "鼻炎用薬": -0.5
    },
    "筋肉痛": {
        "風邪薬": -0.5,  # 単一症状の場合は複合薬にペナルティ（新規追加）
        "外用薬（皮膚）": 0.2,  # 筋肉痛には外用薬（湿布・テープ剤）を優先（新規追加）
        "解熱鎮痛薬": 0.0  # 内服薬も適切だが、外用薬を優先
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
        "風邪薬": 0.25,  # 総合感冒薬を優先するが、過度なボーナスは避ける
        "解熱鎮痛薬": 0.0  # ペナルティなし（効能特異性の差で自然に順位が決まる）
    },
    frozenset({"発熱", "咳"}): {
        "風邪薬": 0.15,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"発熱", "鼻水"}): {
        "風邪薬": 0.15,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"咳", "痰"}): {
        "風邪薬": 0.18,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"鼻水", "鼻づまり"}): {
        "鼻炎用薬": 0.2,
        "風邪薬": 0.1
    },
    frozenset({"のどの痛み", "咳"}): {
        "風邪薬": 0.18,
        "解熱鎮痛薬": -0.1
    },
    frozenset({"咳", "鼻水"}): {
        "風邪薬": 0.15,
        "鼻炎用薬": 0.1
    },
    frozenset({"頭痛", "発熱"}): {
        "解熱鎮痛薬": 0.12,
        "風邪薬": 0.15
    },
    frozenset({"腹痛", "下痢"}): {
        "胃腸薬": 0.2,
        "風邪薬": -0.1
    },
    frozenset({"吐き気", "腹痛"}): {
        "胃腸薬": 0.18,
        "風邪薬": -0.1
    }
}

# 症状パターンごとの最適化定義
SYMPTOM_PATTERN_OPTIMIZATION = {
    # のど痛み+発熱
    frozenset({"のどの痛み", "発熱"}): {
        "priority_order": ["総合感冒薬（喉向き）", "解熱鎮痛薬", "外用薬（のど）", "葛根湯"],
        "bonuses": {
            "総合感冒薬（喉向き・成分あり）": 0.50,  # 0.40から0.50に増加（最優先）
            "総合感冒薬（喉向き・効能のみ）": 0.40,  # 0.30から0.40に増加
            "解熱鎮痛薬": 0.45,  # 0.35から0.45に増加（2位優先のため強化）
            "外用薬（のど）": 0.45,  # 0.35から0.45に増加（3位優先のため強化）
            "葛根湯": -0.2  # ペナルティを-0.1から-0.2に強化（4位以降に配置するため）
        }
    },
    # 頭痛+発熱
    frozenset({"頭痛", "発熱"}): {
        "priority_order": ["解熱鎮痛薬", "総合感冒薬"],
        "bonuses": {
            "解熱鎮痛薬": 0.15,
            "総合感冒薬": 0.10
        }
    },
    # 咳+痰
    frozenset({"咳", "痰"}): {
        "priority_order": ["風邪薬（鎮咳去痰薬）", "総合感冒薬"],
        "bonuses": {
            "風邪薬": 0.20,
            "総合感冒薬": 0.10
        }
    },
    # 鼻水+鼻づまり
    frozenset({"鼻水", "鼻づまり"}): {
        "priority_order": ["鼻炎用薬", "総合感冒薬"],
        "bonuses": {
            "鼻炎用薬": 0.20,
            "総合感冒薬": 0.10
        }
    },
    # 胃痛+胸やけ
    frozenset({"胃痛", "胸やけ"}): {
        "priority_order": ["胃薬", "総合胃腸薬"],
        "bonuses": {
            "胃薬": 0.15,
            "総合胃腸薬": 0.10
        }
    },
    # 便秘（単一症状）
    frozenset({"便秘"}): {
        "priority_order": ["便秘薬"],
        "bonuses": {
            "便秘薬": 0.15
        },
        "penalties": {
            "リスク成分（センナ、ヒマシ油）": -0.20
        }
    },
    # 下痢（単一症状）
    frozenset({"下痢"}): {
        "priority_order": ["下痢止め薬"],
        "bonuses": {
            "下痢止め薬": 0.15
        }
    },
    # ニキビ（単一症状）
    frozenset({"ニキビ"}): {
        "priority_order": ["外用薬（皮膚）", "内服薬"],
        "bonuses": {
            "外用薬（皮膚）": 0.15,
            "内服薬": 0.15
        }
    },
    # やけど（単一症状）
    frozenset({"やけど"}): {
        "priority_order": ["外用薬（皮膚）のやけど専用薬"],
        "bonuses": {
            "外用薬（皮膚）": 0.25
        }
    },
    # 切り傷（単一症状）
    frozenset({"切り傷"}): {
        "priority_order": ["外用薬（皮膚）の創傷保護剤"],
        "bonuses": {
            "外用薬（皮膚）": 0.25
        }
    },
    # 二日酔い（頭痛+むくみ+だるさ）
    frozenset({"頭痛", "むくみ", "だるさ"}): {
        "priority_order": ["五苓散", "L-システイン含有医薬品"],
        "bonuses": {
            "五苓散": 0.20,
            "L-システイン含有医薬品": 0.15
        }
    },
    # 二日酔い（吐き気+胃もたれ+むかつき）
    frozenset({"吐き気", "胃もたれ", "むかつき"}): {
        "priority_order": ["生薬配合の胃腸薬・健胃消化薬"],
        "bonuses": {
            "生薬配合の胃腸薬": 0.15
        }
    },
    # 二日酔い（複数症状の組み合わせ）
    frozenset({"頭痛", "むくみ"}): {
        "priority_order": ["五苓散", "L-システイン含有医薬品"],
        "bonuses": {
            "五苓散": 0.20,
            "L-システイン含有医薬品": 0.15
        }
    },
    frozenset({"頭痛", "だるさ"}): {
        "priority_order": ["五苓散", "L-システイン含有医薬品"],
        "bonuses": {
            "五苓散": 0.20,
            "L-システイン含有医薬品": 0.15
        }
    },
    frozenset({"むくみ", "だるさ"}): {
        "priority_order": ["五苓散", "L-システイン含有医薬品"],
        "bonuses": {
            "五苓散": 0.20,
            "L-システイン含有医薬品": 0.15
        }
    },
    # 二日酔い（頭痛+吐き気）- よくある組み合わせ
    frozenset({"頭痛", "吐き気"}): {
        "priority_order": ["五苓散", "生薬配合の胃腸薬"],
        "bonuses": {
            "五苓散": 0.15,
            "生薬配合の胃腸薬": 0.12
        }
    },
    # 二日酔い（頭痛+だるさ+吐き気）- 複合症状
    frozenset({"頭痛", "だるさ", "吐き気"}): {
        "priority_order": ["五苓散", "生薬配合の胃腸薬"],
        "bonuses": {
            "五苓散": 0.18,
            "生薬配合の胃腸薬": 0.12
        }
    },
    # 風邪の初期症状（悪寒+発熱）
    frozenset({"悪寒", "発熱"}): {
        "priority_order": ["葛根湯", "総合感冒薬"],
        "bonuses": {
            "葛根湯": 0.15,
            "総合感冒薬": 0.10
        }
    },
    # 月経不順+イライラ
    frozenset({"月経不順", "イライラ"}): {
        "priority_order": ["加味逍遙散", "命の母ホワイト", "ラムールQ", "ルナエール", "ルナフェミン", "桂枝茯苓丸"],
        "bonuses": {
            "加味逍遙散": 0.30,  # 0.25から0.30に増加
            "命の母ホワイト": 0.30,  # 0.25から0.30に増加
            "ラムールQ": 0.28,  # 0.23から0.28に増加
            "ルナエール": 0.25,  # 0.20から0.25に増加
            "ルナフェミン": 0.25,  # 0.20から0.25に増加
            "桂枝茯苓丸": 0.25,  # 新規追加
            "解熱鎮痛薬": 0.10
        }
    },
    # 月経不順+冷え症
    frozenset({"月経不順", "冷え症"}): {
        "priority_order": ["当帰芍薬散"],
        "bonuses": {
            "当帰芍薬散": 0.20,
            "解熱鎮痛薬": 0.10
        }
    },
    # 月経不順+ニキビ
    frozenset({"月経不順", "ニキビ"}): {
        "priority_order": ["桂枝茯苓丸", "命の母ホワイト"],
        "bonuses": {
            "桂枝茯苓丸": 0.20,  # 0.15から0.20に増加
            "命の母ホワイト": 0.20,  # 新規追加
            "解熱鎮痛薬": 0.10
        }
    }
}

THROAT_SYMPTOM_TOKENS = {normalize_text(term) for term in [
    "のどの痛み",
    "喉の痛み",
    "咽頭痛",
    "のどの不快感",
    "声がれ"
]}

THROAT_KEYWORD_TOKENS = {normalize_text(term) for term in [
    "のど",
    "喉",
    "咽頭",
    "トローチ",
    "うがい",
    "うがい薬",
    "含嗽",
    "声がれ"
]}

THROAT_LIQUID_TOKENS = {normalize_text(term) for term in [
    "シロップ",
    "液",
    "内服液",
    "ドリンク",
    "鎮咳液",
    "咳止め液"
]}

# 喉向き総合感冒薬の識別用成分リスト
THROAT_SPECIFIC_INGREDIENTS = [
    "トラネキサム酸",
    "カンゾウエキス",
    "グリチルリチン酸",
    "アズレンスルホン酸ナトリウム",
    "アズレン",
    "ポビドンヨード"
]

# 胃粘膜保護成分リスト（別名含む、製品名と成分列の両方でチェック）
STOMACH_MUCOSAL_PROTECTANTS = [
    # スクラルファート系
    "スクラルファート", "スクラルファート水和物", "アルサノン", "スクラート",
    # テプレノン系
    "テプレノン", "セルベックス",
    # レバミピド系
    "レバミピド", "ムコスタ", "レバミピド末",
    # エコラビド系
    "エコラビド",
    # セトラキサート系
    "セトラキサート", "セトラキサート塩酸塩", "ノイエル",
    # ゲファルナート系
    "ゲファルナート", "ゲファニール",
    # ソフラコン系
    "ソフラコン",
    # アズレンスルホン酸系
    "アズレンスルホン酸", "アズレンスルホン酸ナトリウム", "水溶性アズレン",
    # 銅クロロフィリン系
    "銅クロロフィリン", "銅クロロフィリンナトリウム",
    # アルジオキサ系
    "アルジオキサ", "アランサ"
]

# 胃薬・胃腸薬の症状別成分優先順位
STOMACH_MEDICINE_PRIORITY = {
    "胃痛": {
        "制酸薬": {
            "ingredients": ["炭酸水素ナトリウム", "酸化マグネシウム", "水酸化アルミニウム", "炭酸マグネシウム", "炭酸カルシウム"],
            "boost": 0.15
        },
        "胃粘膜保護": {
            "ingredients": STOMACH_MUCOSAL_PROTECTANTS,
            "boost": 0.20,  # 空腹時痛の場合、制酸薬より高く
            "condition": "空腹時"  # 空腹時痛の場合に適用
        }
    },
    "胸やけ": {
        "H2ブロッカー": {
            "ingredients": ["ファモチジン", "ラニチジン", "シメチジン", "ニザチジン"],
            "boost": 0.18
        },
        "制酸薬": {
            "ingredients": ["炭酸水素ナトリウム", "酸化マグネシウム", "水酸化アルミニウム"],
            "boost": 0.12
        }
    },
    "胃もたれ": {
        "健胃消化薬": {
            "ingredients": ["生薬", "健胃", "消化"],  # 効能効果のキーワード
            "boost": 0.15
        }
    },
    "吐き気": {
        "制吐薬": {
            "ingredients": ["ジメンヒドリナート", "メトクロプラミド", "ドンペリドン"],
            "boost": 0.15
        }
    }
}

# 便秘薬の成分優先順位
CONSTIPATION_MEDICINE_PRIORITY = {
    "高優先度（安全性重視）": {
        "ingredients": ["酸化マグネシウム", "ラクツロース", "ラクチトール", "ポリカルボフィルカルシウム"],
        "boost": 0.20
    },
    "中優先度（効果重視だがリスクあり）": {
        "ingredients": ["センナ", "ヒマシ油", "ビサコジル", "ピコスルファート"],
        "boost": 0.10
    }
}

# 刺激性下剤の成分リスト
IRRITANT_LAXATIVE_INGREDIENTS = [
    "センナ", "センノシド", "センナエキス",
    "ビサコジル", "ピコスルファート",
    "ヒマシ油", "加香ヒマシ油", "カストル油"
]

# 主要解熱鎮痛薬リスト（第一選択として推奨されるべき医薬品）
MAJOR_ANALGESIC_MEDICINES = [
    'カロナールＡ', 'カロナールA', 'カロナール',
    'ロキソニンＳ', 'ロキソニンS', 'ロキソニン',
    'タイレノールＡ', 'タイレノールA', 'タイレノール',
    'イブ', 'EVE', 'イブプロフェン',
    'ブファリン', 'バファリン', 'バファリンA'
]

# 解熱鎮痛薬の成分優先順位
ANALGESIC_PRIORITY = {
    "高優先度（胃に優しい）": {
        "ingredients": ["アセトアミノフェン", "パラセタモール", "タイレノール"],
        "boost": 0.15
    },
    "中優先度（バランス型）": {
        "ingredients": ["イブプロフェン", "イブ", "ブルフェン"],
        "boost": 0.10
    },
    "中優先度（効果高いが胃への影響あり）": {
        "ingredients": ["ロキソプロフェン", "ロキソニン", "ジクロフェナク", "ボルタレン"],
        "boost": 0.08
    }
}

# 月経不順向け成分優先順位
MENSTRUAL_MEDICINE_PRIORITY = {
    "高優先度（当帰芍薬散）": {
        "ingredients": ["当帰芍薬散", "トウキシャクヤクサン"],
        "boost": 0.25
    },
    "高優先度（当帰+芍薬の組み合わせ）": {
        "ingredients": ["当帰", "トウキ", "芍薬", "シャクヤク"],
        "requires_both": True,  # 当帰と芍薬の両方が必要
        "boost": 0.20
    },
    "中優先度（当帰または芍薬単独）": {
        "ingredients": ["当帰", "トウキ", "芍薬", "シャクヤク"],
        "boost": 0.15
    }
}

# 外用薬（喉）の成分優先順位
THROAT_TOPICAL_PRIORITY = {
    "高優先度": {
        "ingredients": ["ポビドンヨード", "イソジン", "アズレンスルホン酸ナトリウム", "アズレン", "水溶性アズレン"],
        "boost": 0.20
    },
    "中優先度": {
        "ingredients": ["グリチルリチン酸", "カンゾウエキス"],
        "boost": 0.12
    }
}

# 睡眠障害（眠気）向け成分優先順位
SLEEP_DISORDER_PRIORITY = {
    "高優先度（ビタミン剤配合カフェイン製剤）": {
        "product_names": ["エスタロン", "エスタロンモカ", "トメルミン"],
        "boost": 0.20
    },
    "中優先度（カフェイン単独製剤）": {
        "ingredients": ["カフェイン", "無水カフェイン", "カフェイン水和物", "クエン酸カフェイン"],
        "boost": 0.15
    }
}

# 切り傷・擦り傷の成分・剤形優先順位
WOUND_MEDICINE_PRIORITY = {
    "成分": {
        "ingredients": ["イソジン", "オキシドール", "過酸化水素", "ワセリン", "白色ワセリン"],
        "boost": 0.15
    },
    "剤形": {
        "forms": ["絆創膏", "軟膏", "スプレー", "クリーム"],
        "boost": 0.10
    }
}

# やけどの重度判定キーワード（ガードレール）
BURN_SEVERITY_KEYWORDS = {
    "severe": ["水ぶくれ", "水疱", "痛くない", "3度熱傷", "顔面", "広範囲", "重度", "激しい"]
}

# ================================================================================
# 2. NLU関数（ChatGPT APIで症状抽出のみ）
# ================================================================================

# NLUキャッシュ・NLU関数は nlu_service に移行（SRP改善）
from src.core.nlu_service import (
    get_cached_nlu_result,
    set_cached_nlu_result,
    clear_nlu_cache,
    get_cached_medicine_type,
    set_cached_medicine_type,
    get_cached_translation,
    set_cached_translation,
    simple_pattern_matching_nlu,
    _extract_body_part_from_user_text,
    hybrid_nlu_extraction,
    extract_symptoms_with_gpt,
)

# 症状パターンマッチングキャッシュ（rule_based_recommendation 内で使用）
_symptom_pattern_cache = {}
_max_symptom_pattern_cache_size = 200


# ================================================================================
# 3. 安全性フィルタ層（safety_filter からインポート）
# ================================================================================

from src.core.safety_filter import (
    check_safety_contraindications,
    check_sleep_medicine_safety,
)

# ================================================================================
# 4. 候補薬取得とスコアリング（filter_by_efficacy_symptom_match, get_candidate_medicines は candidate_scoring から import）
# ================================================================================

# (filter_by_efficacy_symptom_match は candidate_scoring に移行済み)
def _enforce_symptom_match_threshold(
    candidates: List[Dict],
    nlu_result: Dict
) -> List[Dict]:
    """
    症状適合度スコアの最低閾値を適用し、症状との関連が乏しい候補を除外
    """
    if not candidates:
        return candidates
    
    symptoms = nlu_result.get("symptoms", []) or []
    symptom_names = {s.get("name") for s in symptoms if s.get("name")}
    symptom_names_list = list(symptom_names)
    is_single_symptom = len(symptom_names) == 1
    threshold = MIN_SYMPTOM_MATCH_SINGLE if is_single_symptom else MIN_SYMPTOM_MATCH_MULTI
    
    filtered: List[Dict] = []
    for candidate in candidates:
        score_breakdown = candidate.get('score_breakdown', {}) or {}
        symptom_match = score_breakdown.get('symptom_match')
        
        # 主要解熱鎮痛薬の場合は除外しない（発熱のみの場合）
        product_name = candidate.get('product_name', '')
        is_major_analgesic = any(
            major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
        )
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for s in symptoms if s.get("name") in cold_symptoms)
        is_fever_only = cold_symptom_count == 1 and any(s.get("name") == "発熱" for s in symptoms)
        
        if is_fever_only and is_major_analgesic and '解熱鎮痛薬' in candidate.get('medicine_type', ''):
            # 主要解熱鎮痛薬は発熱のみの場合、症状適合度が低くても除外しない
            filtered.append(candidate)
            if logger.level <= logging.INFO:
                logger.info(f"✅ 主要解熱鎮痛薬のため症状適合度チェックをスキップ: {product_name} (symptom_match={symptom_match})")
            continue
        
        # 二日酔いブーストがある医薬品は、症状適合度が低くても除外しない
        hangover_boost = score_breakdown.get('hangover_boost', 0.0)
        is_hangover_medicine = candidate.get('is_hangover', False)
        
        # 月経不順症状で成分ブーストがある場合の閾値緩和
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
        symptom_names_set = {s.get("name") for s in symptoms if s.get("name")}
        has_menstrual_symptom = any(symptom in symptom_names_set for symptom in menstrual_symptoms)
        
        # 成分ブーストの確認（当帰・芍薬を含む場合）
        ingredients = str(candidate.get('ingredients', '')).lower()
        has_ingredient_boost = False
        if has_menstrual_symptom:
            toki_keywords = ["トウキ", "当帰", "とうき", "トウキ末", "トウキ流エキス", "トウキエキス", "トウキ乾燥エキス"]
            shakuyaku_keywords = ["シャクヤク", "芍薬", "しゃくやく", "シャクヤク末", "シャクヤクエキス", "シャクヤク乾燥エキス"]
            has_toki = any(kw.lower() in ingredients for kw in toki_keywords)
            has_shakuyaku = any(kw.lower() in ingredients for kw in shakuyaku_keywords)
            product_name = str(candidate.get('product_name', '')).upper()
            efficacy = str(candidate.get('efficacy', '')).upper()
            has_toki_shakuyaku_san = "当帰芍薬散" in candidate.get('product_name', '') or "トウキシャクヤクサン" in product_name or "当帰芍薬散" in efficacy
            has_ingredient_boost = (has_toki and has_shakuyaku) or has_toki_shakuyaku_san
        
        if hangover_boost > 0 or is_hangover_medicine:
            # 二日酔い向け医薬品は閾値を下げる
            adjusted_threshold = 0.0  # 二日酔いブーストがあれば症状適合度チェックをスキップ
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"二日酔い医薬品のため閾値を0.0に調整: {candidate.get('product_name', '')} (boost={hangover_boost:.3f})")
        elif has_menstrual_symptom and has_ingredient_boost:
            # 月経不順症状で成分ブーストがある場合、閾値を緩和
            adjusted_threshold = max(0.0, threshold - 0.15)  # 閾値を0.15下げる（例：0.35→0.20）
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"月経不順症状+成分ブーストのため閾値を{threshold:.2f}から{adjusted_threshold:.2f}に緩和: {candidate.get('product_name', '')}")
        else:
            adjusted_threshold = threshold
        
        # 効能に症状が含まれている場合は閾値を緩和（保険として維持）
        # 効能効果に症状が含まれていない場合は、症状適合度に関係なく除外するか、厳格に判定
        if symptom_match is not None and symptom_match < adjusted_threshold:
            # 効能チェックによる閾値緩和（0.21 = 0.3の30%緩和）
            # ただし、効能効果に症状が含まれていない場合は緩和しない（厳格に判定）
            has_efficacy_match = has_symptom_in_efficacy(candidate, symptom_names_list)
            if has_efficacy_match:
                adjusted_threshold = 0.21  # 30%緩和
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"効能に症状が含まれているため閾値を{threshold:.2f}から{adjusted_threshold:.2f}に緩和: {candidate.get('product_name', '')}")
        
        if symptom_match is not None and symptom_match < adjusted_threshold:
            if logger.level <= logging.INFO:
                logger.info(
                    f"🚫 症状適合度が閾値未満のため候補を除外 (score={symptom_match:.2f}, threshold={adjusted_threshold:.2f}): "
                    f"{candidate.get('product_name', '')}"
                )
            continue
        filtered.append(candidate)
    
    return filtered


def determine_life_stage(user_info: Dict, nlu_result: Dict) -> str:
    """
    ライフステージ（年齢層）の分類
    
    Args:
        user_info: ユーザー情報
        nlu_result: NLU解析結果
    
    Returns:
        ライフステージ: "若年層", "中間層", "更年期前後", "不明"
    """
    age = user_info.get('age')
    
    # 年齢情報から判定
    if age is not None:
        if 10 <= age <= 29:
            return "若年層"
        elif 30 <= age <= 49:
            return "中間層"
        elif age >= 50:
            return "更年期前後"
    
    # 年齢情報が取得できない場合: 症状から推測
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    
    # ニキビがある場合は若年層と推測
    if "ニキビ" in symptom_names:
        return "若年層"
    
    # 更年期関連の症状がある場合は更年期前後と推測
    if any(kw in str(symptom_names) for kw in ['更年期', 'ほてり', 'のぼせ']):
        return "更年期前後"
    
    # デフォルト: 不明
    return "不明"

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
    # 指標が1-2個: 低確信度 (0.3-0.5)
    # 指標が3-4個: 中確信度 (0.5-0.7)
    # 指標が5個以上: 高確信度 (0.7-1.0)
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
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"🔍 証判定: {sho} (確信度: {confidence:.2f}, 虚証指標: {kyo_count}個, 実証指標: {jitsu_count}個)")
        logger.debug(f"証判定の詳細: {reasons}")
    
    return {
        "sho": sho,
        "confidence": confidence,
        "reasons": reasons,
        "kyo_indicators": kyo_indicators,
        "jitsu_indicators": jitsu_indicators
    }

def apply_user_preference_bonus(candidate: Dict, user_preferences: Dict, nlu_result: Dict = None) -> float:
    """
    ユーザーの要望に基づくスコア調整
    
    Args:
        candidate: 候補医薬品情報
        user_preferences: ユーザー要望（extract_user_preferencesの結果）
        nlu_result: NLU解析結果（オプション）
    
    Returns:
        ボーナススコア（0.0-0.25）
    """
    if not user_preferences:
        return 0.0
    
    bonus = 0.0
    product_name = candidate.get('product_name', '')
    ingredients = str(candidate.get('ingredients', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    medicine_type = candidate.get('medicine_type', '')
    
    # 成分・バランス重視: 配合成分数、ビタミン類の配合、漢方のバランスに応じたボーナス（0.0-0.25）
    if user_preferences.get('ingredient_balance', False):
        confidence = user_preferences.get('confidence', 0.0)
        
        # ビタミン類の配合チェック
        vitamin_keywords = ['ビタミン', 'vitamin', 'ビタミンe', 'ビタミンb', 'トコフェロール', '酢酸トコフェロール']
        has_vitamin = any(vitamin in ingredients for vitamin in vitamin_keywords)
        
        # 複数の成分が含まれているかチェック（成分数のカウント）
        ingredient_count = len([ing for ing in ingredients.split(',') if ing.strip()]) if ingredients else 0
        
        # 総合的な医薬品（命の母、ラムールQなど）のチェック
        is_comprehensive = any(kw in product_name.lower() for kw in ['命の母', 'ラムール', 'ルナエール', 'ルナフェミン'])
        
        # 漢方のバランス（複数の生薬成分が含まれているか）
        kampo_ingredients = ['トウキ', '当帰', 'シャクヤク', '芍薬', 'ブクリョウ', '茯苓', 'サイコ', '柴胡', 'ケイヒ', '桂枝']
        kampo_count = sum(1 for kampo in kampo_ingredients if kampo.lower() in ingredients)
        
        ingredient_balance_score = 0.0
        if has_vitamin:
            ingredient_balance_score += 0.08
        if ingredient_count >= 5:
            ingredient_balance_score += 0.05
        if is_comprehensive:
            ingredient_balance_score += 0.10
        if kampo_count >= 3:
            ingredient_balance_score += 0.07
        
        # 確信度に応じて重み付け
        ingredient_balance_bonus = min(0.25, ingredient_balance_score) * confidence
        bonus += ingredient_balance_bonus
        
        if ingredient_balance_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 成分・バランス重視ボーナス: {product_name} = +{ingredient_balance_bonus:.2f} (確信度: {confidence:.2f})")
    
    # 飲みやすさ重視: 錠剤タイプ、服用回数の少なさに応じたボーナス（0.0-0.20）
    if user_preferences.get('ease_of_taking', False):
        confidence = user_preferences.get('confidence', 0.0)
        
        # 錠剤タイプのチェック
        is_tablet = any(token in usage.lower() or token in product_name.lower() for token in ['錠', '錠剤', 'カプセル'])
        
        # 服用回数のチェック（1日1回、1日2回が最優先）
        usage_lower = usage.lower()
        dosage_frequency_score = 0.0
        if any(kw in usage_lower for kw in ['1日1回', '1回', '1日1度']):
            dosage_frequency_score = 0.10
        elif any(kw in usage_lower for kw in ['1日2回', '2回', '朝晩']):
            dosage_frequency_score = 0.08
        elif any(kw in usage_lower for kw in ['1日3回', '3回', '食後']):
            dosage_frequency_score = 0.05
        
        ease_of_taking_score = 0.0
        if is_tablet:
            ease_of_taking_score += 0.10
        ease_of_taking_score += dosage_frequency_score
        
        # 確信度に応じて重み付け
        ease_of_taking_bonus = min(0.20, ease_of_taking_score) * confidence
        bonus += ease_of_taking_bonus
        
        if ease_of_taking_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 飲みやすさ重視ボーナス: {product_name} = +{ease_of_taking_bonus:.2f} (確信度: {confidence:.2f})")
    
    # 随伴症状対応: 効能効果の範囲の広さ、特定の症状の組み合わせに対応する製品にボーナス（0.0-0.20）
    if user_preferences.get('accompanying_symptoms', False):
        confidence = user_preferences.get('confidence', 0.0)
        
        # 効能効果の範囲の広さをチェック
        efficacy_keywords = ['月経不順', '生理不順', '生理痛', '月経痛', 'イライラ', 'ニキビ', '肌荒れ', '腰痛', '頭痛', 'めまい', '冷え症', 'むくみ']
        efficacy_coverage = sum(1 for kw in efficacy_keywords if kw in efficacy)
        
        # 複数の症状に対応しているかチェック
        if nlu_result:
            symptoms = nlu_result.get('symptoms', [])
            symptom_names = [s.get('name', '') for s in symptoms]
            symptom_coverage = sum(1 for symptom in symptom_names if symptom in efficacy)
        else:
            symptom_coverage = 0
        
        # 随伴症状対応スコア
        accompanying_symptoms_score = 0.0
        if efficacy_coverage >= 3:
            accompanying_symptoms_score += 0.10
        if symptom_coverage >= 2:
            accompanying_symptoms_score += 0.10
        
        # 確信度に応じて重み付け
        accompanying_symptoms_bonus = min(0.20, accompanying_symptoms_score) * confidence
        bonus += accompanying_symptoms_bonus
        
        if accompanying_symptoms_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 随伴症状対応ボーナス: {product_name} = +{accompanying_symptoms_bonus:.2f} (確信度: {confidence:.2f})")
    
    return min(0.25, bonus)  # 最大0.25まで

def ensure_ingredient_diversity(candidates: List[Dict], top_n: int = 3, similarity_threshold: float = 0.2, nlu_result: Dict = None, user_info: Dict = None) -> List[Dict]:
    """主要成分が重複しすぎないように候補を再選別する（剤形多様性も考慮）
    
    改善点：
    - similarity_thresholdを0.3から0.2に下げる（より厳格に重複を避ける）
    - 異なる成分の医薬品にボーナスを付与
    """
    if len(candidates) <= top_n:
        return candidates

    # 期待される医薬品をスコアフィルタリングから保護（計画要件: 期待される医薬品の優先確保）
    priority_medicine_names_for_protection = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
    protected_candidates = []
    for candidate in candidates:
        product_name = candidate.get('product_name', '')
        # 期待される医薬品かどうかをチェック（部分一致も許可）
        is_priority = any(
            is_exact_product_match(product_name, [name]) or name in product_name 
            for name in priority_medicine_names_for_protection
        )
        if is_priority:
            protected_candidates.append(candidate)
            logger.debug(f"🔒 期待される医薬品をスコアフィルタリングから保護: {product_name}")
    
    # スコアフィルタリング: スコア0の候補を除外（期待される医薬品は保護）
    filtered_candidates = [c for c in candidates if c.get('final_score', 0.0) > 0.0]
    
    # 保護された期待される医薬品を追加（スコアが0でも含める）
    for protected_candidate in protected_candidates:
        if protected_candidate not in filtered_candidates:
            filtered_candidates.append(protected_candidate)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔒 期待される医薬品をスコアフィルタリングから保護: {protected_candidate.get('product_name', '')} (スコア: {protected_candidate.get('final_score', 0.0)})")
    
    if len(filtered_candidates) < top_n:
        # スコア0以外の候補が不足する場合は、スコア0.3以上の候補を追加
        additional_candidates = [c for c in candidates if c.get('final_score', 0.0) >= 0.3 and c not in filtered_candidates]
        filtered_candidates.extend(additional_candidates)
    
    # フィルタリング後の候補が不足する場合は元の候補リストを使用
    if len(filtered_candidates) < top_n:
        filtered_candidates = candidates
    
    if len(filtered_candidates) <= top_n:
        return filtered_candidates[:top_n]

    # 二日酔い特化：五苓散とL-システイン含有医薬品を優先確保
    reserved_goreisan = None
    reserved_cysteine = None
    
    # 五苓散を最優先で確保
    for candidate in filtered_candidates:
        product_name = candidate.get('product_name', '')
        efficacy = candidate.get('efficacy', '')
        if "五苓散" in product_name or "五苓散" in efficacy:
            reserved_goreisan = candidate
            break
    
    # L-システイン含有医薬品を確保（二日酔い関連効能がある場合）
    for candidate in filtered_candidates:
        if candidate == reserved_goreisan:
            continue
        ingredients = str(candidate.get('ingredients', '')).lower()
        efficacy = str(candidate.get('efficacy', '')).lower()
        
        # L-システイン含有で二日酔い関連効能がある場合
        has_cysteine = "l-システイン" in ingredients or "システイン" in ingredients or "lシステイン" in ingredients
        has_hangover_related = any(kw in efficacy for kw in ["倦怠", "疲労", "肝", "解毒", "二日酔", "宿酔"])
        
        # 美容主体（しみ・そばかす）を除外
        is_beauty_primary = any(kw in efficacy[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])
        
        if has_cysteine and has_hangover_related and not is_beauty_primary:
            reserved_cysteine = candidate
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"L-システイン優先枠を確保: {candidate.get('product_name', '')}")
            break
    
    # 美容主体でないL-システイン製品が見つからない場合でも、美容主体は推奨しない
    # （二日酔い推奨として不適切なため）
    if not reserved_cysteine:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("L-システイン優先枠: 美容主体でない製品が見つかりませんでした（美容主体は二日酔いに不適切なため除外）")
    
    # 月経不順+イライラの症状パターンで、期待される医薬品を優先確保
    reserved_menstrual_medicines = []
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        # 症状名の正規化（「生理不順」→「月経不順」）
        normalized_symptom_names_list = []
        symptom_mapping = {
            "生理不順": "月経不順",
            "生理異常": "月経不順",
        }
        for name in symptom_names_list:
            normalized_name = symptom_mapping.get(name, name)
            normalized_symptom_names_list.append(normalized_name)
        
        symptom_set = frozenset(normalized_symptom_names_list)
        is_menstrual_irritability_pattern = symptom_set == frozenset({"月経不順", "イライラ"}) or symptom_set.issubset(frozenset({"月経不順", "イライラ"}))
        
        if is_menstrual_irritability_pattern:
            # 期待される医薬品を優先確保（計画要件: 製品名マッチングの改善）
            priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
            
            # 期待される医薬品を検索（filtered_candidatesとcandidatesの両方から）
            # 製品名マッチングをより柔軟にする（部分一致を強化）
            for candidate in filtered_candidates + candidates:
                if candidate == reserved_goreisan or candidate == reserved_cysteine or candidate in reserved_menstrual_medicines:
                    continue
                product_name = candidate.get('product_name', '')
                product_name_lower = product_name.lower()
                
                # 製品名マッチング（より柔軟な方法）
                for priority_name in priority_medicine_names:
                    priority_name_lower = priority_name.lower()
                    
                    # 1. 完全一致
                    if product_name_lower == priority_name_lower:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（完全一致）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 2. 部分一致（製品名に検索名が含まれる、または検索名に製品名が含まれる）
                    if priority_name_lower in product_name_lower or product_name_lower in priority_name_lower:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（部分一致）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 3. 厳密な製品名マッチング
                    if is_exact_product_match(product_name, [priority_name]):
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（厳密マッチ）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 4. 特殊文字を除去して比較（「ラムールＱ」と「ラムールQ」など）
                    import re
                    product_name_normalized = re.sub(r'[ＱｑQq]', 'Q', product_name_lower)
                    priority_name_normalized = re.sub(r'[ＱｑQq]', 'Q', priority_name_lower)
                    if priority_name_normalized in product_name_normalized or product_name_normalized in priority_name_normalized:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（正規化後一致）: {product_name} (検索名: {priority_name})")
                        break
                
                # 最大3件まで確保
                if len(reserved_menstrual_medicines) >= 3:
                    break
            
            # 期待される医薬品が見つからない場合のログ
            if len(reserved_menstrual_medicines) == 0:
                logger.warning(f"⚠️ 期待される医薬品が候補に見つかりませんでした（検索名: {priority_medicine_names}）")
                # デバッグ用: 実際の候補の製品名をログに出力
                candidate_names = [c.get('product_name', '') for c in (filtered_candidates[:20] if filtered_candidates else candidates[:20])]
                logger.warning(f"デバッグ: 候補の上位20件の製品名: {candidate_names}")
    
    # 液剤を最初に1件確保（剤形多様性）
    liquid_candidate = None
    for candidate in filtered_candidates:
        if candidate == reserved_goreisan or candidate == reserved_cysteine or candidate in reserved_menstrual_medicines:
            continue
        if _candidate_has_throat_liquid_signature(candidate):
            liquid_candidate = candidate
            break

    selected: List[Dict] = []
    selected_sets: List[set] = []
    fallback: List[Tuple[Dict, set]] = []

    # 特別枠を保留
    reserved_liquid = liquid_candidate

    # 葛根湯系の同一成分グループを識別する関数
    def _is_kakkonto_group(ingredients: set) -> bool:
        """葛根湯系の成分グループかどうかを判定"""
        kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
        ingredients_str = ' '.join(ingredients).lower()
        return any(kw.lower() in ingredients_str for kw in kakkonto_keywords)
    
    # 五苓散系の同一成分グループを識別する関数
    def _is_goreisan_group(ingredients: set) -> bool:
        """五苓散系の成分グループかどうかを判定"""
        goreisan_keywords = ["タクシャ", "チョレイ", "ビャクジュツ", "ブクリョウ", "ケイヒ", "インチンコウ"]
        ingredients_str = ' '.join(ingredients).lower()
        # 五苓散の主要成分（タクシャ、チョレイ、ブクリョウ）のうち2つ以上含まれていれば五苓散系
        core_ingredients = ["タクシャ", "チョレイ", "ブクリョウ"]
        core_count = sum(1 for kw in core_ingredients if kw.lower() in ingredients_str)
        return core_count >= 2

    for candidate in filtered_candidates:
        # 保留中の特別枠はスキップ
        if reserved_liquid and candidate == reserved_liquid:
            continue
        if reserved_goreisan and candidate == reserved_goreisan:
            continue
        if reserved_cysteine and candidate == reserved_cysteine:
            continue
        if candidate in reserved_menstrual_medicines:
            continue

        main_ingredients = set(extract_main_ingredients(candidate.get("ingredients", "")))

        overlap = False
        for existing_set in selected_sets:
            if not existing_set or not main_ingredients:
                continue
            
            # 五苓散系・葛根湯系の同一成分グループチェック（最優先）
            if _is_goreisan_group(existing_set) and _is_goreisan_group(main_ingredients):
                overlap = True
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"五苓散系の同一成分グループとして重複を検出: {candidate.get('product_name', '')}")
                break
            
            if _is_kakkonto_group(existing_set) and _is_kakkonto_group(main_ingredients):
                overlap = True
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯系の同一成分グループとして重複を検出: {candidate.get('product_name', '')} (既に選択済み: {[c.get('product_name') for c in selected]})")
                break
            
            # 製品名で葛根湯の重複をチェック（成分抽出が失敗した場合のフォールバック）
            existing_product_names = [c.get('product_name', '') for c in selected]
            candidate_product_name = candidate.get('product_name', '')
            if "葛根湯" in candidate_product_name:
                if any("葛根湯" in name for name in existing_product_names):
                    overlap = True
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"葛根湯製品名による重複を検出: {candidate_product_name} (既に選択済み: {[name for name in existing_product_names if '葛根湯' in name]})")
                    break
            
            # 通常の成分重複チェック
            intersection = existing_set & main_ingredients
            if intersection:
                overlap_ratio = len(intersection) / float(min(len(existing_set), len(main_ingredients)))
                if overlap_ratio >= similarity_threshold:
                    overlap = True
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"成分重複を検出（重複率: {overlap_ratio:.2f}）: {candidate.get('product_name', '')}")
                    break

        if not overlap and len(selected) < (top_n - 1 if reserved_liquid else top_n):
            selected.append(candidate)
            selected_sets.append(main_ingredients)
        else:
            fallback.append((candidate, main_ingredients))

    # 特別枠を優先順位で追加
    # 1. 期待される医薬品（月経不順+イライラの症状パターン、最優先）
    if reserved_menstrual_medicines:
        for menstrual_medicine in reserved_menstrual_medicines:
            # 既にselectedに含まれている場合はスキップ
            if menstrual_medicine in selected:
                logger.info(f"⭐ 期待される医薬品は既に最終推奨に含まれています: {menstrual_medicine.get('product_name', '')}")
                continue
            if len(selected) < top_n:
                selected.insert(0, menstrual_medicine)  # 最上位に挿入
                selected_sets.insert(0, set(extract_main_ingredients(menstrual_medicine.get("ingredients", ""))))
                logger.info(f"⭐ 期待される医薬品を最終推奨に追加: {menstrual_medicine.get('product_name', '')}")
            else:
                # top_nに達している場合でも、期待される医薬品を最優先で置き換える
                # 最低スコアの候補を削除して、期待される医薬品を追加
                if selected:
                    min_score_candidate = min(selected, key=lambda c: c.get('final_score', 0.0))
                    min_score = min_score_candidate.get('final_score', 0.0)
                    menstrual_score = menstrual_medicine.get('final_score', 0.0)
                    # 期待される医薬品のスコアが最低スコアより高い場合、または最低スコアが0.5未満の場合に置き換え
                    if menstrual_score > min_score or min_score < 0.5:
                        selected.remove(min_score_candidate)
                        selected.insert(0, menstrual_medicine)
                        selected_sets.insert(0, set(extract_main_ingredients(menstrual_medicine.get("ingredients", ""))))
                        logger.info(f"⭐ 期待される医薬品を最終推奨に追加（置き換え）: {menstrual_medicine.get('product_name', '')}")
    
    # 期待される医薬品が見つからなかった場合、候補から直接検索して追加（フォールバック）
    if not reserved_menstrual_medicines and is_menstrual_irritability_pattern:
        logger.warning(f"⚠️ reserved_menstrual_medicinesが空です。候補から直接検索します...")
        priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
        for candidate in filtered_candidates + candidates:
            if candidate in selected or candidate == reserved_goreisan or candidate == reserved_cysteine:
                continue
            product_name = candidate.get('product_name', '')
            product_name_lower = product_name.lower()
            for priority_name in priority_medicine_names:
                priority_name_lower = priority_name.lower()
                if priority_name_lower in product_name_lower or product_name_lower in priority_name_lower:
                    if len(selected) < top_n:
                        selected.insert(0, candidate)
                        selected_sets.insert(0, set(extract_main_ingredients(candidate.get("ingredients", ""))))
                        logger.info(f"⭐ 期待される医薬品を最終推奨に追加（フォールバック）: {product_name}")
                        break
            if len(selected) >= top_n:
                break
    
    # 2. 五苓散（2番目の優先度）
    if reserved_goreisan and len(selected) < top_n:
        insert_pos = min(len(reserved_menstrual_medicines), len(selected))
        selected.insert(insert_pos, reserved_goreisan)
        selected_sets.insert(insert_pos, set(extract_main_ingredients(reserved_goreisan.get("ingredients", ""))))
    
    # 3. L-システイン含有医薬品（3番目の優先度）
    if reserved_cysteine and len(selected) < top_n:
        # 期待される医薬品と五苓散の後に挿入
        insert_pos = min(len(reserved_menstrual_medicines) + (1 if reserved_goreisan else 0), len(selected))
        selected.insert(insert_pos, reserved_cysteine)
        selected_sets.insert(insert_pos, set(extract_main_ingredients(reserved_cysteine.get("ingredients", ""))))
    
    # 3. 液剤を最後に追加（成分重複に関わらず）
    if reserved_liquid and len(selected) < top_n:
        selected.append(reserved_liquid)
        selected_sets.append(set(extract_main_ingredients(reserved_liquid.get("ingredients", ""))))

    # まだ不足している場合は重複を許容して埋める
    # ただし、葛根湯の重複は避ける
    if len(selected) < top_n:
        for candidate, ingredient_set in fallback:
            if candidate in selected:
                continue
            # 葛根湯の重複チェック
            candidate_product_name = candidate.get('product_name', '')
            if "葛根湯" in candidate_product_name:
                # 既に選択されている候補に葛根湯がある場合はスキップ
                existing_product_names = [c.get('product_name', '') for c in selected]
                if any("葛根湯" in name for name in existing_product_names):
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"葛根湯の重複を回避: {candidate_product_name} (既に選択済み: {[name for name in existing_product_names if '葛根湯' in name]})")
                    continue
            selected.append(candidate)
            selected_sets.append(ingredient_set)
            if len(selected) >= top_n:
                break

    # 漢方+解熱鎮痛剤の組み合わせ保護（多様性チェックの後に適用、補完的に保護）
    # 痛みが主訴の場合、漢方1件+解熱鎮痛剤1件を最優先ペアとして保護
    if nlu_result:
        from src.core.user_detection import determine_pain_urgency
        user_message = nlu_result.get('user_message', '') or ''
        pain_urgency = determine_pain_urgency(user_message, nlu_result)
        
        if pain_urgency.get("is_primary", False):
            # 痛みが主訴の場合
            has_kampo = False
            has_analgesic = False
            kampo_candidate = None
            analgesic_candidate = None
            
            # 選択済みの候補から漢方と解熱鎮痛剤を確認
            for candidate in selected:
                medicine_type = candidate.get('medicine_type', '')
                from src.core.scoring_utils import _is_kampo_or_herbal_medicine
                if _is_kampo_or_herbal_medicine(candidate):
                    has_kampo = True
                    kampo_candidate = candidate
                elif '解熱鎮痛薬' in medicine_type:
                    has_analgesic = True
                    analgesic_candidate = candidate
            
            # 漢方と解熱鎮痛剤の両方が含まれていない場合、追加する
            if not has_kampo or not has_analgesic:
                # 漢方がない場合、候補から漢方を探す
                if not has_kampo:
                    for candidate in filtered_candidates:
                        if candidate in selected:
                            continue
                        from src.core.scoring_utils import _is_kampo_or_herbal_medicine
                        if _is_kampo_or_herbal_medicine(candidate):
                            # 月経不順関連の症状がある場合は、月経不順向けの漢方を優先
                            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
                            has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
                            
                            if has_menstrual_symptom:
                                # 月経不順向けの漢方を優先（桂枝茯苓丸など）
                                product_name = candidate.get('product_name', '')
                                efficacy = str(candidate.get('efficacy', '')).lower()
                                if any(kw in product_name or kw in efficacy for kw in ['桂枝茯苓丸', '加味逍遙散', '当帰芍薬散', '命の母']):
                                    kampo_candidate = candidate
                                    break
                            else:
                                kampo_candidate = candidate
                                break
                
                # 解熱鎮痛剤がない場合、候補から解熱鎮痛剤を探す
                if not has_analgesic:
                    for candidate in filtered_candidates:
                        if candidate in selected or candidate == kampo_candidate:
                            continue
                        medicine_type = candidate.get('medicine_type', '')
                        if '解熱鎮痛薬' in medicine_type:
                            analgesic_candidate = candidate
                            break
                
                # 漢方と解熱鎮痛剤を追加（既に選択済みの候補を置き換えるか、追加する）
                if kampo_candidate and kampo_candidate not in selected and len(selected) < top_n:
                    selected.append(kampo_candidate)
                    selected_sets.append(set(extract_main_ingredients(kampo_candidate.get("ingredients", ""))))
                    logger.info(f"💊 漢方+解熱鎮痛剤の組み合わせ保護: 漢方を追加 {kampo_candidate.get('product_name', '')}")
                
                if analgesic_candidate and analgesic_candidate not in selected and len(selected) < top_n:
                    selected.append(analgesic_candidate)
                    selected_sets.append(set(extract_main_ingredients(analgesic_candidate.get("ingredients", ""))))
                    logger.info(f"💊 漢方+解熱鎮痛剤の組み合わせ保護: 解熱鎮痛剤を追加 {analgesic_candidate.get('product_name', '')}")
    
    # 最終選定ロジックの改善: 上位2件はスコア順、3件目は作用機序の多様性を考慮
    # まず、スコア順にソート
    # 注意: 総合風邪薬の優先配置は、後続の風邪症状がある場合の特別なロジック（4365-4412行目）で処理するため、
    # ここでは単純にスコア順にソートする
    selected_sorted = sorted(selected, key=lambda x: x.get('final_score', 0.0), reverse=True)
    
    # 外用薬（のど）の重複を防ぐ: 1つまでに制限
    external_throat_medicines = [c for c in selected_sorted if '外用薬（のど）' in c.get('medicine_type', '')]
    if len(external_throat_medicines) > 1:
        # スコアが最も高い外用薬（のど）を1つだけ残す
        best_external_throat = max(external_throat_medicines, key=lambda x: x.get('final_score', 0.0))
        # 他の外用薬（のど）を除外
        selected_sorted = [c for c in selected_sorted if c not in external_throat_medicines or c == best_external_throat]
        # スコア順に再ソート
        selected_sorted = sorted(selected_sorted, key=lambda x: x.get('final_score', 0.0), reverse=True)
        logger.info(f"🔒 外用薬（のど）の重複を防止: {len(external_throat_medicines)}件から1件（{best_external_throat.get('product_name', '')}）に制限")
    
    # のどの痛みがある場合、外用薬（のど）のスロットを確保（3位以内に必ず1つ含める）
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_throat_pain = any("のど" in name or "喉" in name for name in symptom_names_list)
        
        if has_throat_pain:
            # 既に選択されている候補に外用薬（のど）があるかチェック
            has_external_throat = any('外用薬（のど）' in c.get('medicine_type', '') for c in selected_sorted[:3])
            
            if not has_external_throat:
                # 外用薬（のど）を優先的に追加
                remaining_candidates = [c for c in filtered_candidates if c not in selected_sorted[:3]]
                for candidate in remaining_candidates:
                    if '外用薬（のど）' in candidate.get('medicine_type', ''):
                        # 3位以内に確保（既に3位以上ある場合は、3位の候補と置き換え）
                        if len(selected_sorted) >= 3:
                            # 3位の候補を削除して外用薬（のど）を追加
                            selected_sorted = selected_sorted[:2] + [candidate]
                            logger.info(f"🔒 外用薬（のど）のスロット確保: {candidate.get('product_name', '')} を3位に配置")
                        else:
                            selected_sorted.append(candidate)
                            logger.info(f"🔒 外用薬（のど）のスロット確保: {candidate.get('product_name', '')} を追加")
                        break
    
    # 風邪症状がある場合の特別なロジック: 1位=総合風邪薬、2位=内服薬（外用薬以外）、3位=外用薬（のど）
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if cold_symptom_count >= 2:
            # 総合風邪薬を1位に確保
            comprehensive_cold = None
            other_medicines = []
            external_throat_medicines = []
            
            for candidate in selected_sorted:
                if is_comprehensive_cold_medicine(candidate):
                    if comprehensive_cold is None:
                        comprehensive_cold = candidate
                elif '外用薬（のど）' in candidate.get('medicine_type', ''):
                    external_throat_medicines.append(candidate)
                else:
                    # 総合風邪薬以外の内服薬を追加（再確認）
                    if not is_comprehensive_cold_medicine(candidate):
                        other_medicines.append(candidate)
            
            # デバッグログ: other_medicinesの内容を確認
            logger.info(f"🔍 other_medicines: {len(other_medicines)}件 - {[c.get('product_name', '') for c in other_medicines[:5]]}")
            logger.info(f"🔍 comprehensive_cold: {comprehensive_cold.get('product_name', '') if comprehensive_cold else 'None'}")
            logger.info(f"🔍 external_throat_medicines: {len(external_throat_medicines)}件")
            
            # 1位: 総合風邪薬（なければスコア順の1位）
            top_2_candidates = []
            if comprehensive_cold:
                top_2_candidates.append(comprehensive_cold)
                comprehensive_cold['original_rank'] = 1  # 1位として明示的に設定
                logger.info(f"✅ 風邪症状: 総合風邪薬を1位に配置: {comprehensive_cold.get('product_name', '')}")
            elif selected_sorted:
                top_2_candidates.append(selected_sorted[0])
                selected_sorted[0]['original_rank'] = 1  # 1位として明示的に設定
            
            # 2位: 総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
            logger.info(f"🔍 2位選定開始: top_2_candidates={len(top_2_candidates)}, other_medicines={len(other_medicines)}")
            if len(top_2_candidates) < 2:
                # 2位も総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
                # まず総合風邪薬を探す（selected_sortedから優先的に探す）
                found_2nd_comprehensive_cold = False
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                        # 総合風邪薬を優先
                        if is_comprehensive_cold_medicine(candidate):
                            top_2_candidates.append(candidate)
                            candidate['original_rank'] = 2  # 2位として明示的に設定
                            logger.info(f"✅ 風邪症状: 総合風邪薬を2位に配置: {candidate.get('product_name', '')}")
                            found_2nd_comprehensive_cold = True
                            break
                
                # selected_sortedから見つからない場合、other_medicines + candidatesから探す
                if not found_2nd_comprehensive_cold and len(top_2_candidates) < 2:
                    for candidate in other_medicines + [c for c in candidates if c not in selected_sorted]:
                        if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                            # 総合風邪薬を優先
                            if is_comprehensive_cold_medicine(candidate):
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: 総合風邪薬を2位に配置（candidatesから）: {candidate.get('product_name', '')}")
                                found_2nd_comprehensive_cold = True
                                break
                
                # 総合風邪薬が見つからない場合、内服薬（外用薬以外、総合風邪薬以外）を選定
                if len(top_2_candidates) < 2:
                    for candidate in other_medicines:
                        if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                            # 総合風邪薬でないことを再確認
                            if not is_comprehensive_cold_medicine(candidate):
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: 内服薬を2位に配置: {candidate.get('product_name', '')}")
                                break
                
                # 内服薬が見つからない場合、selected_sortedから総合風邪薬以外の内服薬を探す
                if len(top_2_candidates) < 2:
                    logger.info(f"🔍 other_medicinesから見つからなかったため、selected_sortedから総合風邪薬以外を探します")
                    found_count = 0
                    for candidate in selected_sorted:
                        if (candidate not in top_2_candidates and 
                            '外用薬（のど）' not in candidate.get('medicine_type', '') and
                            not is_comprehensive_cold_medicine(candidate)):
                            top_2_candidates.append(candidate)
                            candidate['original_rank'] = 2  # 2位として明示的に設定
                            logger.info(f"✅ 風邪症状: スコア順で2位を選定（総合風邪薬以外）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                            found_count += 1
                            if len(top_2_candidates) >= 2:
                                break
                    if found_count == 0:
                        logger.warning(f"⚠️ selected_sortedから総合風邪薬以外の内服薬が見つかりませんでした。selected_sortedの上位10件: {[(c.get('product_name', ''), c.get('medicine_type', ''), is_comprehensive_cold_medicine(c)) for c in selected_sorted[:10]]}")
                        # filtered_candidates（candidates）から総合風邪薬以外の内服薬を探す
                        logger.info(f"🔍 candidatesから総合風邪薬以外の内服薬を探します（全{len(candidates)}件）")
                        for candidate in candidates:
                            if (candidate not in top_2_candidates and 
                                '外用薬（のど）' not in candidate.get('medicine_type', '') and
                                not is_comprehensive_cold_medicine(candidate) and
                                candidate.get('final_score', 0.0) >= 0.3):  # スコアが0.3以上の候補のみ
                                
                                # 効能が風邪症状に適していない医薬品を除外
                                efficacy = str(candidate.get('efficacy', '')).lower()
                                # 栄養補給・滋養強壮薬を除外
                                has_nutritional_efficacy = any(kw in efficacy for kw in ['栄養補給', '滋養強壮', '虚弱体質', '肉体疲労', '病中病後', '食欲不振', '栄養障害'])
                                has_cold_symptom_in_efficacy = any(kw in efficacy for kw in ['発熱', '熱', '解熱', '頭痛', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', 'のど', '咽頭', '喉', '感冒', 'かぜ', 'せき', 'たん', '鎮痛', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛', '咽頭痛', '打撲痛', '急性上気道炎'])
                                is_nutritional_only = has_nutritional_efficacy and not has_cold_symptom_in_efficacy
                                
                                if is_nutritional_only:
                                    logger.info(f"🚫 栄養補給・滋養強壮薬を除外（2位選定）: {candidate.get('product_name', '')} (効能: {efficacy[:80]}...)")
                                    continue
                                
                                # 効能特異性が低い医薬品を除外（_enforce_symptom_match_thresholdと同じ条件）
                                from src.core.scoring_utils import calculate_efficacy_specificity_score
                                efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)
                                symptom_specificity_penalty = calculate_symptom_specificity_penalty(candidate, nlu_result)
                                
                                # 効能特異性が0.0または非常に低い（0.1未満）かつ症状特異性ペナルティが-0.6以下の医薬品を除外
                                if efficacy_specificity < 0.1 and symptom_specificity_penalty <= -0.6:
                                    logger.info(f"🚫 効能特異性が低い医薬品を除外（2位選定）: {candidate.get('product_name', '')} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f})")
                                    continue
                                
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: candidatesから2位を選定（総合風邪薬以外）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')}, final_score: {candidate.get('final_score', 0.0):.3f})")
                                if len(top_2_candidates) >= 2:
                                    break
                        if len(top_2_candidates) < 2:
                            logger.warning(f"⚠️ candidatesからも総合風邪薬以外の内服薬が見つかりませんでした。上位10件: {[(c.get('product_name', ''), c.get('medicine_type', ''), is_comprehensive_cold_medicine(c), c.get('final_score', 0.0)) for c in sorted(candidates, key=lambda x: x.get('final_score', 0.0), reverse=True)[:10]]}")
            
            # 3位用の候補リスト（特化薬を優先：解熱鎮痛薬、外用喉薬、喉薬、鼻炎薬など）
            remaining_candidates = []
            # 3位は症状に特化した医薬品を優先（総合感冒薬以外）
            # 優先順位: 1. 外用薬（のど）、2. 解熱鎮痛薬、3. 鼻炎用薬、4. その他
            priority_types_for_3rd = ['外用薬（のど）', '解熱鎮痛薬', '鼻炎用薬']
            
            # まず特化薬を探す（総合感冒薬以外）
            for priority_type in priority_types_for_3rd:
                for candidate in other_medicines + selected_sorted:
                    if (candidate not in top_2_candidates and 
                        candidate.get('product_name', '') not in {c.get('product_name', '') for c in remaining_candidates} and
                        priority_type in candidate.get('medicine_type', '') and
                        not is_comprehensive_cold_medicine(candidate)):
                        remaining_candidates.append(candidate)
                        candidate['original_rank'] = 3  # 3位として明示的に設定
                        logger.info(f"✅ 風邪症状: 特化薬（{priority_type}）を3位候補に追加: {candidate.get('product_name', '')}")
                        break  # 各タイプから1つずつ選定
                if len(remaining_candidates) >= 3:  # 3つまで追加
                    break
            
            # 特化薬が見つからない場合、その他の候補を追加（重複を防止）
            if len(remaining_candidates) == 0:
                added_product_names = {c.get('product_name', '') for c in top_2_candidates + remaining_candidates}
                for candidate in other_medicines + [c for c in selected_sorted if c not in top_2_candidates]:
                    # 既に選定された候補や、同じ製品名の候補を除外
                    if (candidate not in top_2_candidates and 
                        candidate.get('product_name', '') not in added_product_names and
                        not is_comprehensive_cold_medicine(candidate)):  # 総合感冒薬は除外
                        remaining_candidates.append(candidate)
                        added_product_names.add(candidate.get('product_name', ''))
                        if len(remaining_candidates) >= 3:  # 3つまで追加
                            break
        else:
            # 風邪症状がない場合、従来のロジック
            top_2_candidates = selected_sorted[:2] if len(selected_sorted) >= 2 else selected_sorted
            # remaining_candidatesを生成する際、除外ロジックを適用
            if nlu_result and len(selected_sorted) > 2:
                temp_candidates = selected_sorted[2:]
                remaining_candidates = filter_by_efficacy_symptom_match(temp_candidates, nlu_result)
            else:
                remaining_candidates = selected_sorted[2:] if len(selected_sorted) > 2 else []
    else:
        # nlu_resultがない場合、従来のロジック
        top_2_candidates = selected_sorted[:2] if len(selected_sorted) >= 2 else selected_sorted
    # remaining_candidatesを生成する際、除外ロジックを適用
    if nlu_result and len(selected_sorted) > 2:
        temp_candidates = selected_sorted[2:]
        remaining_candidates = filter_by_efficacy_symptom_match(temp_candidates, nlu_result)
    else:
        remaining_candidates = selected_sorted[2:] if len(selected_sorted) > 2 else []
    
    # 上位2件の作用機序を確認
    top_2_mechanisms = set()
    for candidate in top_2_candidates:
        mechanism = classify_medicine_mechanism(candidate)
        top_2_mechanisms.add(mechanism)
    
    # 3件目を選定: 作用機序の多様性を考慮
    third_candidate = None
    # remaining_candidatesが空の場合、selected_sortedから3件目を選定
    if not remaining_candidates and len(top_2_candidates) < top_n:
        # selected_sortedから、top_2_candidatesに含まれていない候補を探す
        for candidate in selected_sorted:
            if candidate not in top_2_candidates:
                # 除外ロジックを事前に適用（不適切な候補を除外）
                if nlu_result:
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                remaining_candidates.append(candidate)
                if len(remaining_candidates) >= 3:  # 3件まで追加
                    break
    
    if len(top_2_candidates) < top_n and remaining_candidates:
        # 期待される医薬品を優先（月経不順関連の症状がある場合）
        if nlu_result:
            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
            has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
            
            if has_menstrual_symptom:
                # 期待される医薬品を優先
                priority_medicine_names = ["ラムールQ", "ラムールＱ", "加味逍遙散", "命の母ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸"]
                for candidate in remaining_candidates:
                    product_name = candidate.get('product_name', '')
                    if any(priority_name in product_name for priority_name in priority_medicine_names):
                        third_candidate = candidate
                        logger.info(f"⭐ 3件目に期待される医薬品を選定: {product_name}")
                        break
        
        # 期待される医薬品が見つからない場合、作用機序の多様性を考慮
        if not third_candidate:
            # 補血・調血系と理気・駆瘀血系の両方が含まれているか確認
            has_blood_tonifying = "補血・調血系" in top_2_mechanisms
            has_qi_regulating = "理気・駆瘀血系" in top_2_mechanisms
            
            # 両方が含まれていない場合、不足している方の作用機序を持つ候補を優先
            if not has_blood_tonifying:
                for candidate in remaining_candidates:
                    mechanism = classify_medicine_mechanism(candidate)
                    if mechanism == "補血・調血系":
                        third_candidate = candidate
                        logger.info(f"🔬 3件目に補血・調血系を選定（作用機序の多様性確保）: {candidate.get('product_name', '')}")
                        break
            elif not has_qi_regulating:
                for candidate in remaining_candidates:
                    mechanism = classify_medicine_mechanism(candidate)
                    if mechanism == "理気・駆瘀血系":
                        third_candidate = candidate
                        logger.info(f"🔬 3件目に理気・駆瘀血系を選定（作用機序の多様性確保）: {candidate.get('product_name', '')}")
                        break
        
        # 作用機序の多様性が確保されている場合、スコア順で3件目を選定
        if not third_candidate and remaining_candidates:
            # remaining_candidatesから適切な候補を選定（除外ロジックを適用済み）
            for candidate in remaining_candidates:
                # 除外ロジックを再度適用（念のため）
                if nlu_result:
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                third_candidate = candidate
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📊 3件目をスコア順で選定: {third_candidate.get('product_name', '')}")
                break
    
    # 最終選定リストを構築
    # 風邪症状がある場合、top_2_candidatesが2件未満の場合は2位を選定
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if len(top_2_candidates) < 2:
            if cold_symptom_count >= 2:
                # 2位: 総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
                for candidate in selected_sorted:
                    if (candidate not in top_2_candidates and 
                        is_comprehensive_cold_medicine(candidate)):
                        top_2_candidates.append(candidate)
                        logger.info(f"✅ 風邪症状: 最終チェックで2位を選定（総合風邪薬）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        if len(top_2_candidates) >= 2:
                            break
            else:
                # 単一症状の場合も2位、3位を選定（主要解熱鎮痛薬を優先）
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates:
                        # 主要解熱鎮痛薬を優先
                        is_major_analgesic = any(
                            major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                        )
                        if is_major_analgesic or len(top_2_candidates) < 2:
                            top_2_candidates.append(candidate)
                            logger.info(f"✅ 単一症状: {len(top_2_candidates)}位を選定: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                            if len(top_2_candidates) >= 2:
                                break
        
        # 単一症状の場合、3位も選定（主要解熱鎮痛薬を優先）
        if cold_symptom_count == 1 and len(top_2_candidates) >= 2 and not third_candidate:
            for candidate in selected_sorted:
                if candidate not in top_2_candidates:
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    
                    # 主要解熱鎮痛薬を優先
                    is_major_analgesic = any(
                        major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                    )
                    if is_major_analgesic:
                        third_candidate = candidate
                        logger.info(f"✅ 単一症状: 3位を選定（主要解熱鎮痛薬）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        break
            
            # 主要解熱鎮痛薬が見つからない場合、スコア順で3位を選定（除外ロジックを適用）
            if not third_candidate and selected_sorted:
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates:
                        # 除外ロジックを事前に適用（不適切な候補を除外）
                        if nlu_result:
                            temp_list = [candidate]
                            filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                            if len(filtered_temp) == 0:
                                continue  # 除外される場合はスキップ
                        
                        third_candidate = candidate
                        logger.info(f"✅ 単一症状: 3位を選定（スコア順）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        break
    
    final_selected = top_2_candidates.copy()
    if third_candidate and len(final_selected) < top_n:
        final_selected.append(third_candidate)
        logger.info(f"✅ 3位候補を追加: {third_candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
    
    # 残りの候補を追加（top_nに達するまで）
    # 重複を防止: 既に選定された医薬品と同じ製品名の候補を除外
    # 単一症状の場合も3つ選定する（主要解熱鎮痛薬を優先）
    if len(final_selected) < top_n:
        selected_product_names = {c.get('product_name', '') for c in final_selected}
        
        # まずremaining_candidatesから主要解熱鎮痛薬を優先的に追加
        for candidate in remaining_candidates:
            if candidate == third_candidate:
                continue
            if candidate.get('product_name', '') in selected_product_names:
                continue
            # 除外ロジックを事前に適用（不適切な候補を除外）
            if nlu_result:
                temp_list = [candidate]
                filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                if len(filtered_temp) == 0:
                    continue  # 除外される場合はスキップ
            # 主要解熱鎮痛薬を優先
            is_major_analgesic = any(
                major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic:
                final_selected.append(candidate)
                selected_product_names.add(candidate.get('product_name', ''))
                logger.info(f"✅ 単一症状: 主要解熱鎮痛薬を追加（remaining_candidates）: {candidate.get('product_name', '')}")
                if len(final_selected) >= top_n:
                    break
        
        # remaining_candidatesが空または不足している場合、selected_sortedから追加
        if len(final_selected) < top_n:
            # 単一症状の場合、主要解熱鎮痛薬を優先
            if nlu_result:
                symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
                cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
                
                if cold_symptom_count == 1:
                    # 主要解熱鎮痛薬を優先的に追加
                    for candidate in selected_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを事前に適用（不適切な候補を除外）
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                        is_major_analgesic = any(
                            major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                        )
                        if is_major_analgesic:
                            final_selected.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            logger.info(f"✅ 単一症状: 主要解熱鎮痛薬を追加（selected_sorted）: {candidate.get('product_name', '')}")
                            if len(final_selected) >= top_n:
                                break
            
            # 主要解熱鎮痛薬が不足している場合、remaining_candidatesから追加
            if len(final_selected) < top_n:
                for candidate in remaining_candidates:
                    if candidate == third_candidate:
                        continue
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    final_selected.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    logger.info(f"✅ 単一症状: 残りの候補を追加（remaining_candidates）: {candidate.get('product_name', '')}")
                    if len(final_selected) >= top_n:
                        break
            
            # まだ不足している場合、selected_sortedから追加（確実に3つ選定するため）
            if len(final_selected) < top_n:
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    final_selected.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    logger.info(f"✅ 単一症状: 残りの候補を追加（selected_sorted）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
                    if len(final_selected) >= top_n:
                        break
                
                # それでも不足している場合、candidatesから追加（確実に3つ選定するため）
                if len(final_selected) < top_n:
                    for candidate in candidates:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        if candidate.get('final_score', 0.0) >= 0.3:  # スコアが0.3以上の候補のみ
                            # 除外ロジックを事前に適用（不適切な候補を除外）
                            if nlu_result:
                                temp_list = [candidate]
                                filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                                if len(filtered_temp) == 0:
                                    continue  # 除外される場合はスキップ
                            final_selected.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            logger.info(f"✅ 単一症状: 残りの候補を追加（candidates）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
                            if len(final_selected) >= top_n:
                                break
    
    # カテゴリ多様性の確保と弱点補完ロジック（3症状以上の場合）
    if nlu_result and len(final_selected) >= top_n:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        symptom_count = len(symptom_names_list)
        
        if symptom_count >= 3:
            # 現在のカテゴリを確認
            medicine_types = [c.get('medicine_type', '') for c in final_selected[:top_n]]
            unique_types = set()
            for med_type in medicine_types:
                # カテゴリを抽出（"風邪薬"、"解熱鎮痛薬"、"外用薬（のど）"など）
                if '風邪薬' in med_type:
                    unique_types.add('風邪薬')
                elif '解熱鎮痛薬' in med_type:
                    unique_types.add('解熱鎮痛薬')
                elif '外用薬（のど）' in med_type:
                    unique_types.add('外用薬（のど）')
                elif '漢方薬' in med_type or any(kw in med_type for kw in ['葛根湯', '五苓散']):
                    unique_types.add('漢方薬')
            
            # 単一カテゴリのみの場合は、弱点補完ロジックを適用
            if len(unique_types) == 1:
                first_medicine_type = list(unique_types)[0]
                first_medicine = final_selected[0]
                
                # 1位の薬の弱点を補うカテゴリを決定（ルールベース + 症状ベース）
                complementary_category = None
                
                # ルールベース: 1位のカテゴリに応じた補完カテゴリ
                category_compensation_rules = {
                    "風邪薬": ["外用薬（のど）", "解熱鎮痛薬"],  # 総合感冒薬の弱点: 局所治療、強力な解熱
                    "解熱鎮痛薬": ["風邪薬", "外用薬（のど）"],  # 解熱鎮痛薬の弱点: 総合的な対応、局所治療
                    "外用薬（のど）": ["風邪薬", "解熱鎮痛薬"],  # 外用薬の弱点: 全身症状への対応
                }
                
                # 症状ベース: 症状に応じた優先順位
                has_throat_pain = any("のど" in name or "喉" in name for name in symptom_names_list)
                has_fever = "発熱" in symptom_names_list
                has_cough = "咳" in symptom_names_list
                
                if first_medicine_type == "風邪薬":
                    # のど痛みがあれば外用薬（のど）を優先、発熱が強ければ解熱鎮痛薬を優先
                    if has_throat_pain:
                        complementary_category = "外用薬（のど）"
                    elif has_fever:
                        complementary_category = "解熱鎮痛薬"
                    else:
                        complementary_category = category_compensation_rules.get(first_medicine_type, ["外用薬（のど）"])[0]
                elif first_medicine_type == "解熱鎮痛薬":
                    # のど痛みがあれば外用薬（のど）を優先、そうでなければ総合感冒薬を優先
                    if has_throat_pain:
                        complementary_category = "外用薬（のど）"
                    else:
                        complementary_category = "風邪薬"
                elif first_medicine_type == "外用薬（のど）":
                    # 発熱があれば解熱鎮痛薬を優先、そうでなければ総合感冒薬を優先
                    if has_fever:
                        complementary_category = "解熱鎮痛薬"
                    else:
                        complementary_category = "風邪薬"
                
                # 補完カテゴリの候補を探して追加
                if complementary_category:
                    # 既に選択されている候補以外から探す
                    remaining_for_compensation = [c for c in filtered_candidates if c not in final_selected[:top_n]]
                    for candidate in remaining_for_compensation:
                        candidate_type = candidate.get('medicine_type', '')
                        if complementary_category in candidate_type:
                            # 効能効果と症状のマッチングをチェック
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                            
                            # 効能効果に症状が含まれているかチェック
                            has_symptom_match = False
                            for symptom_name in symptom_names_list:
                                normalized_symptom = normalize_text(symptom_name)
                                # 効能効果に症状名または同義語が含まれているかチェック
                                symptom_dict_entry = load_symptom_dictionary().get(symptom_name, {})
                                synonyms = [normalized_symptom] + [normalize_text(s) for s in symptom_dict_entry.get("synonyms", [])]
                                
                                # 効能効果に症状が含まれているか確認
                                if any(synonym in efficacy for synonym in synonyms if synonym):
                                    has_symptom_match = True
                                    break
                                
                                # 風邪症状の特別チェック
                                cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ"]
                                if symptom_name in cold_symptoms:
                                    # 効能効果に風邪症状が含まれているか
                                    if any(kw in efficacy for kw in ['発熱', '熱', '解熱', '咳', '鎮咳', '鼻水', '鼻炎', 'のど', '咽頭', '喉', '頭痛', '悪寒', 'くしゃみ']):
                                        has_symptom_match = True
                                        break
                            
                            # 効能効果に症状が含まれていない場合はスキップ
                            if not has_symptom_match:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"弱点補完候補をスキップ（効能効果に症状が含まれていない）: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...)")
                                continue
                            
                            # 3位の候補と置き換え（または追加）
                            if len(final_selected) >= 3:
                                final_selected = final_selected[:2] + [candidate]
                                logger.info(f"🔬 弱点補完: {complementary_category} を追加 {candidate.get('product_name', '')}")
                            else:
                                final_selected.append(candidate)
                                logger.info(f"🔬 弱点補完: {complementary_category} を追加 {candidate.get('product_name', '')}")
                            break
    
    # 作用機序の多様性の強制: 補血・調血系と理気・駆瘀血系の両方を強制的に含める
    # 月経不順関連の症状がある場合のみ適用
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
        has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
        
        if has_menstrual_symptom:
            # 最終選定リストの作用機序を確認
            final_selected_mechanisms = {}
            for candidate in final_selected:
                mechanism = classify_medicine_mechanism(candidate)
                if mechanism not in final_selected_mechanisms:
                    final_selected_mechanisms[mechanism] = []
                final_selected_mechanisms[mechanism].append(candidate)
            
            # 補血・調血系と理気・駆瘀血系の両方が含まれているか確認
            has_blood_tonifying = "補血・調血系" in final_selected_mechanisms
            has_qi_regulating = "理気・駆瘀血系" in final_selected_mechanisms
            
            # 証との連動: 虚証なら「補血系」、実証なら「駆瘀血系」から必ず1つはピックアップ
            if user_info:
                user_message = user_info.get('user_message', '') or ''
                sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
                sho = sho_result.get('sho', '不明')
                confidence = sho_result.get('confidence', 0.0)
                
                # 確信度が高い場合（confidence >= 0.5）のみ証との連動を適用
                if confidence >= 0.5:
                    # 虚証の場合: 補血・調血系を優先的に含める
                    if sho == "虚証" and not has_blood_tonifying:
                        for candidate in filtered_candidates:
                            if candidate in final_selected:
                                continue
                            mechanism = classify_medicine_mechanism(candidate)
                            if mechanism == "補血・調血系":
                                # スコアが低くても、補血・調血系から最低1件は含める
                                if len(final_selected) < top_n:
                                    final_selected.append(candidate)
                                    logger.info(f"🔬 証との連動（虚証）: 補血・調血系を追加 {candidate.get('product_name', '')}")
                                    has_blood_tonifying = True
                                break
                    
                    # 実証の場合: 理気・駆瘀血系を優先的に含める
                    elif sho == "実証" and not has_qi_regulating:
                        for candidate in filtered_candidates:
                            if candidate in final_selected:
                                continue
                            mechanism = classify_medicine_mechanism(candidate)
                            if mechanism == "理気・駆瘀血系":
                                # スコアが低くても、理気・駆瘀血系から最低1件は含める
                                if len(final_selected) < top_n:
                                    final_selected.append(candidate)
                                    logger.info(f"🔬 証との連動（実証）: 理気・駆瘀血系を追加 {candidate.get('product_name', '')}")
                                    has_qi_regulating = True
                                break
            
            # 両方が含まれていない場合、追加する（証との連動で追加されなかった場合）
            if not has_blood_tonifying or not has_qi_regulating:
                # 補血・調血系がない場合、候補から補血・調血系を探す
                if not has_blood_tonifying:
                    for candidate in filtered_candidates:
                        if candidate in final_selected:
                            continue
                        mechanism = classify_medicine_mechanism(candidate)
                        if mechanism == "補血・調血系":
                            # スコアが低くても、補血・調血系から最低1件は含める
                            if len(final_selected) < top_n:
                                final_selected.append(candidate)
                                logger.info(f"🔬 作用機序の多様性確保: 補血・調血系を追加 {candidate.get('product_name', '')}")
                            break
                
                # 理気・駆瘀血系がない場合、候補から理気・駆瘀血系を探す
                if not has_qi_regulating:
                    for candidate in filtered_candidates:
                        if candidate in final_selected:
                            continue
                        mechanism = classify_medicine_mechanism(candidate)
                        if mechanism == "理気・駆瘀血系":
                            # スコアが低くても、理気・駆瘀血系から最低1件は含める
                            if len(final_selected) < top_n:
                                final_selected.append(candidate)
                                logger.info(f"🔬 作用機序の多様性確保: 理気・駆瘀血系を追加 {candidate.get('product_name', '')}")
                            break

    # original_rankに基づいて順序を復元（ランキング保護）
    # 風邪症状がある場合、総合風邪薬が含まれていない場合は強制的に追加
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if cold_symptom_count >= 2:
            # 現在の選定リストに総合風邪薬が含まれているかチェック
            has_comprehensive_cold = any(is_comprehensive_cold_medicine(c) for c in final_selected[:top_n])
            
            if not has_comprehensive_cold:
                # 総合風邪薬を候補から探す
                comprehensive_cold_candidates = [c for c in filtered_candidates if is_comprehensive_cold_medicine(c) and c not in final_selected]
                
                if comprehensive_cold_candidates:
                    # スコア順にソートして最上位の総合風邪薬を取得
                    comprehensive_cold_candidates_sorted = sorted(
                        comprehensive_cold_candidates,
                        key=lambda x: x.get('final_score', 0.0),
                        reverse=True
                    )
                    best_comprehensive_cold = comprehensive_cold_candidates_sorted[0]
                    
                    # 1位に配置（既存の1位を2位にずらす）
                    if len(final_selected) >= top_n:
                        # 既存の1位以降のoriginal_rankを1つずつずらす
                        for i, candidate in enumerate(final_selected[:top_n-1]):
                            candidate['original_rank'] = i + 2
                        final_selected = [best_comprehensive_cold] + final_selected[:top_n-1]
                    else:
                        # 既存の候補のoriginal_rankを1つずつずらす
                        for i, candidate in enumerate(final_selected):
                            candidate['original_rank'] = i + 2
                        final_selected = [best_comprehensive_cold] + final_selected
                    
                    # 総合風邪薬のoriginal_rankを1に設定（ランキング保護のため）
                    best_comprehensive_cold['original_rank'] = 1
                    
                    logger.info(f"✅ 総合風邪薬を強制配置（1位）: {best_comprehensive_cold.get('product_name', '')} (スコア: {best_comprehensive_cold.get('final_score', 0.0):.3f}, original_rank=1)")
    
    # 重複を除去: 同じ製品名の候補を除外（original_rankでソートする前に実行）
    seen_product_names = set()
    final_selected_deduplicated = []
    for candidate in final_selected[:top_n]:
        product_name = candidate.get('product_name', '')
        if product_name not in seen_product_names:
            final_selected_deduplicated.append(candidate)
            seen_product_names.add(product_name)
        else:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"重複を除去: {product_name} (original_rank={candidate.get('original_rank', 'N/A')})")
    
    # 最終チェック: 除外ロジックを再度適用（選定後に追加された候補を除外）
    if nlu_result:
        final_selected_filtered = filter_by_efficacy_symptom_match(final_selected_deduplicated, nlu_result)
        final_selected_deduplicated = final_selected_filtered
        
        # 除外後に3つ未満になった場合、再度候補を追加（確実に3つ選定するため）
        if len(final_selected_deduplicated) < top_n:
            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
            cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
            is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names_list
            is_single_symptom = cold_symptom_count == 1
            
            logger.info(f"🔍 除外後の再追加処理: final_selected_deduplicated={len(final_selected_deduplicated)}, top_n={top_n}, symptom_names_list={symptom_names_list}, cold_symptom_count={cold_symptom_count}, is_single_symptom={is_single_symptom}, is_fever_only={is_fever_only}")
            
            selected_product_names = {c.get('product_name', '') for c in final_selected_deduplicated}
            
            # 単一症状（発熱のみ）の場合、主要解熱鎮痛薬を優先的に追加
            if is_fever_only:
                # selected_sortedから主要解熱鎮痛薬を優先的に追加
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを再度適用（主要解熱鎮痛薬でも不適切なものは除外）
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                    
                    is_major_analgesic = any(
                        major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                    )
                    if is_major_analgesic:
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        logger.info(f"✅ 除外後: 主要解熱鎮痛薬を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
                
                # それでも不足している場合、selected_sortedから追加
                if len(final_selected_deduplicated) < top_n:
                    for candidate in selected_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを再度適用
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                        
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        logger.info(f"✅ 除外後: 残りの候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
            
            # 単一症状（発熱以外：咳、痰、鼻水など）の場合、適切な医薬品を追加
            elif is_single_symptom:
                logger.info(f"🔍 単一症状用の再追加処理開始: selected_sorted={len(selected_sorted)}件, selected_product_names={len(selected_product_names)}件")
                # selected_sortedから適切な候補を追加
                added_count = 0
                skipped_count = 0
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        skipped_count += 1
                        continue
                    # 除外ロジックを再度適用
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        skipped_count += 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                        continue  # 除外される場合はスキップ
                    
                    final_selected_deduplicated.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    added_count += 1
                    logger.info(f"✅ 除外後: 単一症状用の候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                    if len(final_selected_deduplicated) >= top_n:
                        break
                logger.info(f"🔍 単一症状用の再追加処理完了: 追加={added_count}件, スキップ={skipped_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                
                # selected_sortedから追加できなかった場合、candidatesから追加の候補を取得
                if len(final_selected_deduplicated) < top_n:
                    logger.info(f"🔍 selected_sortedから追加できなかったため、candidatesから追加の候補を取得: candidates={len(candidates)}件")
                    # 症状に応じた効能効果キーワードを取得
                    symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])] if nlu_result else []
                    # 効能効果に症状が含まれている候補を優先的に考慮
                    priority_keywords = []
                    for symptom_name in symptom_names_list:
                        if symptom_name in ["痰", "たん"]:
                            priority_keywords.extend(["たん", "痰", "去たん", "去痰"])
                        elif symptom_name in ["咳"]:
                            priority_keywords.extend(["咳", "せき", "咳嗽"])
                    
                    # candidatesを優先度順にソート（効能効果に症状が含まれている候補を優先、その後スコア順）
                    def get_priority_score(candidate):
                        efficacy = str(candidate.get('efficacy', '')).lower()
                        # 効能効果に症状が含まれている場合は優先度を高く
                        priority_score = 0
                        if priority_keywords:
                            for keyword in priority_keywords:
                                if keyword in efficacy:
                                    priority_score = 1
                                    break
                        # スコアを追加（優先度が同じ場合はスコア順）
                        return (priority_score, candidate.get('final_score', 0.0))
                    
                    candidates_sorted = sorted(candidates, key=get_priority_score, reverse=True)
                    
                    # 効能効果に症状が含まれている候補を優先的に追加
                    priority_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 1]
                    other_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 0]
                    
                    # 優先度の高い候補から追加
                    for candidate_list in [priority_candidates, other_candidates]:
                        for candidate in candidate_list:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 除外ロジックを再度適用
                            temp_list = [candidate]
                            filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                            if len(filtered_temp) == 0:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                                continue  # 除外される場合はスキップ
                            
                            final_selected_deduplicated.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            added_count += 1
                            logger.info(f"✅ 除外後: 単一症状用の候補を追加（candidatesから）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                            if len(final_selected_deduplicated) >= top_n:
                                break
                        if len(final_selected_deduplicated) >= top_n:
                            break
                    logger.info(f"🔍 candidatesからの追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
            
            # 複数症状の場合も、3つ未満の場合は追加
            elif len(final_selected_deduplicated) < top_n:
                logger.info(f"🔍 複数症状用の再追加処理開始: selected_sorted={len(selected_sorted)}件, selected_product_names={len(selected_product_names)}件")
                # selected_sortedから適切な候補を追加
                added_count = 0
                skipped_count = 0
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        skipped_count += 1
                        continue
                    # 除外ロジックを再度適用
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        skipped_count += 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                        continue  # 除外される場合はスキップ
                    
                    final_selected_deduplicated.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    added_count += 1
                    logger.info(f"✅ 除外後: 複数症状用の候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                    if len(final_selected_deduplicated) >= top_n:
                        break
                logger.info(f"🔍 複数症状用の再追加処理完了: 追加={added_count}件, スキップ={skipped_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                
                # selected_sortedから追加できなかった場合、candidatesから追加の候補を取得
                if len(final_selected_deduplicated) < top_n:
                    logger.info(f"🔍 selected_sortedから追加できなかったため、candidatesから追加の候補を取得: candidates={len(candidates)}件")
                    # 症状に応じた効能効果キーワードを取得
                    symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])] if nlu_result else []
                    # 効能効果に症状が含まれている候補を優先的に考慮
                    priority_keywords = []
                    for symptom_name in symptom_names_list:
                        if symptom_name in ["痰", "たん"]:
                            priority_keywords.extend(["たん", "痰", "去たん", "去痰"])
                        elif symptom_name in ["咳"]:
                            priority_keywords.extend(["咳", "せき", "咳嗽"])
                    
                    # candidatesを優先度順にソート（効能効果に症状が含まれている候補を優先、その後スコア順）
                    def get_priority_score(candidate):
                        efficacy = str(candidate.get('efficacy', '')).lower()
                        # 効能効果に症状が含まれている場合は優先度を高く
                        priority_score = 0
                        if priority_keywords:
                            for keyword in priority_keywords:
                                if keyword in efficacy:
                                    priority_score = 1
                                    break
                        # スコアを追加（優先度が同じ場合はスコア順）
                        return (priority_score, candidate.get('final_score', 0.0))
                    
                    candidates_sorted = sorted(candidates, key=get_priority_score, reverse=True)
                    for candidate in candidates_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを再度適用
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                            continue  # 除外される場合はスキップ
                        
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        added_count += 1
                        logger.info(f"✅ 除外後: 複数症状用の候補を追加（candidatesから）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
                    logger.info(f"🔍 candidatesからの追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        # 優先度の高い候補を取得
                        priority_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 1]
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
    
    final_selected_sorted = sorted(final_selected_deduplicated, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ensure_ingredient_diversity: original_rankに基づいて順序を復元: {len(final_selected_sorted)}件")
    
    return final_selected_sorted


def match_symptom_pattern(nlu_result: Dict) -> Optional[Dict]:
    """
    症状パターンをマッチングして、最適化情報を返す（キャッシュ対応）
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return None

    symptom_names = [s.get("name") for s in symptoms]
    normalized_symptom_names = []
    symptom_mapping = {
        "疲労感": "だるさ",
        "倦怠感": "だるさ",
        "疲れ": "だるさ",
        "だるい": "だるさ",
        "生理不順": "月経不順",
        "生理異常": "月経不順",
    }
    for name in symptom_names:
        normalized_name = symptom_mapping.get(name, name)
        if normalized_name != name:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状名を正規化: {name} → {normalized_name}")
        normalized_symptom_names.append(normalized_name)

    symptom_set = frozenset(normalized_symptom_names)
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"🔍 症状パターンマッチング: 元の症状={symptom_names}, 正規化後={list(symptom_set)}")

    cache_key = tuple(sorted(symptom_set))
    if cache_key in _symptom_pattern_cache:
        result = _symptom_pattern_cache[cache_key]
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            if result:
                logger.debug(f"✅ 症状パターンマッチング（キャッシュ）: {list(symptom_set)} → マッチ")
        return result

    if symptom_set in SYMPTOM_PATTERN_OPTIMIZATION:
        result = SYMPTOM_PATTERN_OPTIMIZATION[symptom_set]
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"✅ 症状パターンマッチング（完全一致）: {list(symptom_set)} → マッチ")
    else:
        result = None
        for pattern_symptoms, pattern_info in SYMPTOM_PATTERN_OPTIMIZATION.items():
            if symptom_set.issubset(pattern_symptoms):
                result = pattern_info
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"✅ 症状パターンマッチング（部分一致）: {list(symptom_set)} ⊆ {list(pattern_symptoms)} → マッチ")
                break
        if result is None and (DEBUG_MODE or logger.level <= logging.DEBUG):
            logger.debug(f"❌ 症状パターンマッチング: {list(symptom_set)} → マッチなし")

    if len(_symptom_pattern_cache) >= _max_symptom_pattern_cache_size:
        oldest_key = next(iter(_symptom_pattern_cache))
        del _symptom_pattern_cache[oldest_key]

    _symptom_pattern_cache[cache_key] = result
    return result


def calculate_final_score(candidate: Dict, nlu_result: Dict, user_info: Dict, user_text: str = "") -> Dict:
    """
    最終スコアを計算（全スコアを統合）
    
    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        user_text: ユーザー入力テキスト（成分ベースボーナス用）
    
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
    # 禁忌事項の優先ハードチェック（スコアリング計算の前）
    contraindication_check = is_contraindicated(candidate, user_info, nlu_result)
    if contraindication_check.get("is_contraindicated", False):
        # スコアリング計算をスキップし、即座に除外
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
            "contraindication_reason": contraindication_check.get("reason", ""),
            "contraindication_severity": contraindication_check.get("severity", "critical")
        }
    
    # --- 生理痛専用医薬品の完全除外チェック（早期チェック） ---
    # 生理痛専用の解熱鎮痛剤を、生理痛以外の場合に完全に除外
    # CSVの列名が'製品名'の場合と'product_name'の場合の両方に対応
    product_name_early = candidate.get('product_name', candidate.get('製品名', ''))
    efficacy_early = str(candidate.get('efficacy', candidate.get('効能効果', ''))).lower()
    
    # 生理痛専用医薬品のリスト（製品名ベースで判定）
    # これらの製品は、効能効果に「頭痛」などが含まれていても、生理痛専用として扱う
    menstrual_only_products = [
        "ノーシンピュア", "オトナノーシンピュア", "ノーシン", "ノーシンホワイト",
        "エルペインコーワ", "バファリンルナ", "バファリンルナi", "バファリンルナJ",
        "A錠EX", "イブA錠EX", "イントウェル", "ウラック", "メディペイン", "ユニトップファースト",
        "マルコミンEV", "ノーチカ", "クミアイ新頭痛錠"
    ]
    
    # 製品名で生理痛専用医薬品を判定（効能効果に関係なく、製品名で判定）
    is_menstrual_only_product = any(menstrual_product in product_name_early for menstrual_product in menstrual_only_products)
    
    # 効能効果が「生理痛」のみの医薬品を判定（他の効能効果がない場合）
    # 効能効果に「生理痛」が含まれ、かつ「頭痛」「発熱」「歯痛」などの一般的な効能効果が含まれていない場合
    has_menstrual_only_efficacy = (
        '生理痛' in efficacy_early and 
        not any(general_efficacy in efficacy_early for general_efficacy in ['頭痛', '発熱', '解熱', '歯痛', '咽喉痛', 'のどの痛み', '筋肉痛', '関節痛', '腰痛', '神経痛'])
    )
    
    # 小児用ノーシンピュアの例外処理（アセトアミノフェンのみの場合は除外しない）
    is_pediatric_noshin_early = "小中学生用ノーシンピュア" in product_name_early or "小中学生用" in product_name_early
    ingredients_check_early = str(candidate.get('ingredients', candidate.get('成分', ''))).lower()
    has_acetaminophen_only_early = 'アセトアミノフェン' in ingredients_check_early and 'イブプロフェン' not in ingredients_check_early
    is_pediatric_exception_early = is_pediatric_noshin_early and has_acetaminophen_only_early
    
    # 生理痛専用医薬品の判定（製品名ベースで判定、効能効果に関係なく除外）
    if (is_menstrual_only_product or has_menstrual_only_efficacy) and not is_pediatric_exception_early:
        # 生理痛関連キーワードのチェック
        menstrual_keywords_early = [
            "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理中",
            "月経不順", "生理不順", "生理", "月経"
        ]
        user_text_lower_early = user_text.lower() if user_text else ''
        has_menstrual_keyword_early = any(kw in user_text_lower_early for kw in menstrual_keywords_early)
        
        # 症状名からもチェック
        symptom_names_early = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_menstrual_symptom_early = any(
            any(kw in symptom_name.lower() for kw in menstrual_keywords_early)
            for symptom_name in symptom_names_early
        )
        
        # 生理痛が明示されていない場合は完全に除外
        if not (has_menstrual_keyword_early or has_menstrual_symptom_early):
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
                "contraindication_reason": f"{product_name_early}は生理痛専用の医薬品です。生理痛が明示されていない場合は使用できません。",
                "contraindication_severity": "critical"
            }
    
    # --- アスピリンとインフルエンザ・水痘の組み合わせの早期チェック（2.5で追加） ---
    # 15歳未満のインフルエンザ・水痘患者ではアスピリンを完全に除外
    # CSVの列名が'成分'の場合と'ingredients'の場合の両方に対応
    ingredients_str_early = str(candidate.get('ingredients', candidate.get('成分', ''))).lower()
    has_aspirin_early = 'アスピリン' in ingredients_str_early or 'アセチルサリチル酸' in ingredients_str_early
    
    if has_aspirin_early and user_info and user_info.get('age') and user_info.get('age') < 15:
        # インフルエンザ・水痘の疑いの検出
        influenza_risk_early = nlu_result.get('influenza_risk', False) or False
        
        # 水痘の疑いの検出（キーワードと症状の両方をチェック）
        chickenpox_keywords_early = [
            "水痘", "みずぼうそう", "水疱瘡", "帯状疱疹", "ヘルペス", 
            "発疹", "水ぶくれ", "水疱"
        ]
        user_text_lower_early = user_text.lower() if user_text else ''
        has_chickenpox_keyword_early = any(kw in user_text_lower_early for kw in chickenpox_keywords_early)
        
        # 水痘の症状の組み合わせ（発疹 + 水ぶくれ + かゆみ）
        symptom_names_early = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_rash_early = any("発疹" in name or "皮疹" in name for name in symptom_names_early)
        has_blister_early = any("水ぶくれ" in name or "水疱" in name for name in symptom_names_early)
        has_itch_early = any("かゆみ" in name or "痒み" in name for name in symptom_names_early)
        has_chickenpox_symptoms_early = (has_rash_early and has_blister_early) or (has_rash_early and has_itch_early) or (has_blister_early and has_itch_early)
        
        chickenpox_risk_early = has_chickenpox_keyword_early or has_chickenpox_symptoms_early
        
        if influenza_risk_early or chickenpox_risk_early:
            # 15歳未満かつインフルエンザ・水痘の疑いがある場合は完全に除外
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
                "contraindication_reason": "アスピリン含有医薬品は、15歳未満のインフルエンザ・水痘患者ではライ症候群のリスクがあるため使用できません。",
                "contraindication_severity": "critical"
            }
    
    # スコアリングユーティリティをインポート
    from src.core.scoring_utils import (
        calculate_efficacy_specificity_score,
        calculate_side_effect_risk_score,
        calculate_interaction_risk_score,
        calculate_usage_convenience_score,
        check_allergy_contraindication,
        check_drug_interactions,
        calculate_symptom_specific_boost
    )
    
    # 各スコアを計算
    symptom_score = calculate_symptom_match_score(candidate, nlu_result)
    efficacy_specificity_score = calculate_efficacy_specificity_score(candidate, nlu_result)
    age_score = calculate_age_fit_score(candidate, user_info)
    usage_score = calculate_usage_convenience_score(candidate)
    side_effect_score = calculate_side_effect_risk_score(candidate, user_info)
    interaction_score = calculate_interaction_risk_score(candidate, user_info)
    
    # --- 2.0 強力な医薬品・信頼性の高い医薬品の評価と特化型ボーナス ---
    import re
    
    product_name = candidate.get('product_name', '')
    medicine_classification = candidate.get('classification', '')
    manufacturer = candidate.get('manufacturer', '')
    ingredients_str = str(candidate.get('ingredients', ''))
    
    # 1. 信頼性の高いメーカーリスト（大幅拡充）
    trusted_manufacturers = [
        '第一三共', '第一三共ヘルスケア',  # ロキソニン, ルル
        '大正製薬',  # パブロン, ナロン
        'エスエス製薬',  # イブ, エスタック
        'ライオン',  # バファリン
        'シオノギ', 'シオノギヘルスケア',  # セデス
        '興和', 'Kowa',  # バンテリン, キャベジン
        'ロート製薬',  # 目薬, 漢方
        '小林製薬',  # 独自のニッチ薬
        '武田', 'タケダ', 'アリナミン製薬',  # ベンザブロック
        '佐藤製薬',  # リングル, ユンケル
        '久光製薬',  # フェイタス, サロンパス
        'グラクソ', 'GSK',  # ボルタレン, コンタック
        'ジョンソン', 'J&J'  # タイレノール
    ]
    
    # 2. 強力・著名な製品ブランドリスト（大幅拡充）
    strong_products = [
        # 解熱鎮痛
        'ロキソニン', 'カロナール', 'タイレノール', 
        'イブ', 'EVE', 'バファリン', 'セデス', 'ナロン', 'リングル',
        # 胃薬（H2ブロッカー等）
        'ガスター', 
        # 外用薬
        'ボルタレン', 'フェイタス', 'バンテリン', 'サロンパス',
        # アレルギー・鼻炎
        'アレグラ', 'アレジオン', 'クラリチン'
    ]
    
    # 3. 強力な成分リスト
    strong_ingredients = [
        'ロキソプロフェン', 'アセトアミノフェン', 'イブプロフェン', 
        'ジクロフェナク', 'フェルビナク', 'インドメタシン',  # 強力な鎮痛・抗炎症
        'ファモチジン',  # 強力な制酸
        'フェキソフェナジン', 'ロラタジン'  # 第2世代抗ヒスタミン
    ]
    
    # --- 判定ロジック ---
    
    is_strong_medicine = False
    strong_medicine_bonus = 0.0
    
    # A. 分類ボーナス（指定第1類、第1類は薬剤師の関与が必要な強力な薬が多い）
    if '指定第1類' in medicine_classification or '第1類' in medicine_classification:
        strong_medicine_bonus += 0.1
    
    # B. 成分ボーナス（大文字小文字を区別しない）
    ingredients_lower = ingredients_str.lower()
    if any(ingredient.lower() in ingredients_lower for ingredient in strong_ingredients):
        strong_medicine_bonus += 0.05
    
    # C. 製品ブランドボーナス（大文字小文字を区別しない、部分一致）
    product_name_lower = product_name.lower()
    if any(product.lower() in product_name_lower for product in strong_products):
        is_strong_medicine = True
        strong_medicine_bonus += 0.1
    
    # D. メーカー信頼度ボーナス（大文字小文字を区別しない、部分一致）
    manufacturer_lower = manufacturer.lower()
    if any(m.lower() in manufacturer_lower for m in trusted_manufacturers):
        strong_medicine_bonus += 0.05
    
    # --- 【重要】特化型（スペシャリスト）判定 ---
    # ロキソニンなどが風邪薬に負けないための最重要ロジック
    # 成分数が少ない（例：5つ以下）＝ 特定の症状に特化して効く「シャープな薬」
    
    # 成分文字列の正規化と解析
    # 1. 前後の空白を除去
    ingredients_normalized = ingredients_str.strip()
    # 2. 小文字に統一
    ingredients_normalized = ingredients_normalized.lower()
    # 3. 正規表現で分割（カンマ、スペース、改行などに対応）
    # カンマ、カンマ+スペース、改行などで分割
    ingredient_list = re.split(r'[,，\s\n]+', ingredients_normalized)
    # 4. 空文字列を除外
    ingredient_list = [ing for ing in ingredient_list if ing.strip()]
    
    # 成分数のカウント
    ingredient_count = len(ingredient_list)
    
    # 特化型（スペシャリスト）判定（成分数が5つ以下）
    is_focused_medicine = ingredient_count <= 5
    
    # 特化型ボーナス（強力な医薬品かつ特化型の場合のみ+0.15）
    if is_strong_medicine and is_focused_medicine:
        # ブランド力があり、かつ特化型の薬には追加ボーナス
        # これにより「頭痛」単一症状などの場合に、総合風邪薬（成分多）より優先される
        strong_medicine_bonus += 0.15
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"特化型ブランド薬ボーナス適用: {product_name} (成分数: {ingredient_count})")
    
    # ボーナスの適用（上限 +0.3 に設定）
    strong_medicine_bonus_final = min(strong_medicine_bonus, 0.3)
    
    if DEBUG_MODE or logger.level <= logging.DEBUG and strong_medicine_bonus > 0:
        logger.debug(f"強力な医薬品ボーナス合計: {product_name} = +{strong_medicine_bonus_final} (成分数: {ingredient_count}, 特化型: {is_focused_medicine})")
    
    # --- 成人判定（変更なし） ---
    # 成人（15歳以上）には年齢制限のペナルティを適用しない
    # （既存の年齢制限ペナルティロジックで、15歳未満の場合のみペナルティを適用するようにする）
    
    # 期待される医薬品の基本スコアを底上げ（最低0.50を保証）（計画要件: スコアリングシステムの調整）
    # ただし、月経不順関連の症状がない場合（頭痛のみなど）は底上げしない
    priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
    # 厳密マッチング + 部分一致も許可（CSVデータの表記の違いに対応）
    is_priority_medicine = any(is_exact_product_match(product_name, [name]) or name in product_name for name in priority_medicine_names)
    
    if is_priority_medicine:
        # 月経不順関連の症状があるかチェック
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
        has_menstrual_symptom = any(symptom in symptom_names for symptom in menstrual_symptoms)
        
        # 月経不順関連の症状がある場合のみ底上げを適用
        if has_menstrual_symptom:
            # 基本スコアを計算（症状マッチ、効能特異性、年齢適合性、用法簡便性の合計）
            base_score = (
                symptom_score * 0.30 +
                efficacy_specificity_score * 0.20 +
                age_score * 0.12 +
                usage_score * 0.03
            )
            
            # 基本スコアが0.50未満の場合は0.50に底上げ
            if base_score < 0.50:
                base_score_boost = 0.50 - base_score
                # 症状スコアに底上げ分を追加（症状マッチの重みが最も高いため）
                symptom_score += base_score_boost / 0.30
                logger.info(f"⭐ 期待される医薬品の基本スコアを底上げ: {product_name} = +{base_score_boost:.2f} (底上げ前: {base_score:.2f})")
        else:
            # 月経不順関連の症状がない場合（頭痛のみなど）は底上げしない
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"期待される医薬品の底上げをスキップ: {product_name} (月経不順関連の症状なし: {symptom_names})")
    
    # --- 2.1 ノーシンピュアの推奨条件の厳格化（小児用例外処理含む） ---
    # ノーシンピュア系医薬品の判定
    noshin_products = ["ノーシンピュア", "オトナノーシンピュア"]
    is_noshin_product = any(noshin_name in product_name for noshin_name in noshin_products)
    
    # 小児用ノーシンピュアの判定（例外処理用）
    is_pediatric_noshin = "小中学生用ノーシンピュア" in product_name or "小中学生用" in product_name
    ingredients_check = str(candidate.get('ingredients', '')).lower()
    has_acetaminophen_only = 'アセトアミノフェン' in ingredients_check and 'イブプロフェン' not in ingredients_check
    is_pediatric_exception = is_pediatric_noshin and has_acetaminophen_only
    
    noshin_penalty = 0.0
    has_menstrual_keyword = False
    has_menstrual_symptom = False
    
    if is_noshin_product and not is_pediatric_exception:
        # 生理痛関連キーワードのチェック（拡張版）
        menstrual_keywords = [
            "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理中",
            "月経不順", "生理不順", "生理", "月経"
        ]
        user_text_lower = user_text.lower() if user_text else ''
        has_menstrual_keyword = any(kw in user_text_lower for kw in menstrual_keywords)
        
        # 症状名からもチェック
        symptom_names_check = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_menstrual_symptom = any(
            any(kw in symptom_name.lower() for kw in menstrual_keywords)
            for symptom_name in symptom_names_check
        )
        
        if not (has_menstrual_keyword or has_menstrual_symptom):
            # 生理痛が明示されていない場合はペナルティを適用
            noshin_penalty = -0.5  # -0.3から-0.5に強化
            
            # 頭痛に対しては追加のペナルティを適用（ノーシンピュアは頭痛に不適切）
            symptom_names_check = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            has_headache = any("頭痛" in symptom_name for symptom_name in symptom_names_check)
            if has_headache or "頭痛" in (user_text_lower if user_text else ''):
                noshin_penalty -= 0.2  # 頭痛に対して追加で-0.2（合計-0.7）
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"ノーシンピュア頭痛追加ペナルティ: {product_name} = -0.2 (頭痛に対して不適切)")
            
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ノーシンピュアペナルティ: {product_name} = {noshin_penalty} (生理痛が明示されていない)")
    
    # 小児用ノーシンピュアの例外処理
    if is_pediatric_exception:
        # 小児用でアセトアミノフェンのみの場合は、生理痛キーワードがなくても軽減されたペナルティのみ
        # （通常の-0.3ではなく-0.1に軽減）
        if not (has_menstrual_keyword or has_menstrual_symptom):
            pediatric_noshin_penalty = -0.1  # 軽減されたペナルティ
            noshin_penalty = pediatric_noshin_penalty
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"小児用ノーシンピュア軽減ペナルティ: {product_name} = {pediatric_noshin_penalty}")
    
    # 部位マッチングスコアを計算
    user_body_part = nlu_result.get("user_body_part")
    body_part_score = calculate_body_part_match_score(candidate, user_body_part)
    
    # 症状特化型ブーストを計算
    symptom_boost = calculate_symptom_specific_boost(candidate, nlu_result, user_info)
    
    # ユーザー要望に基づくボーナス
    user_preference_bonus = 0.0
    if user_info and user_info.get('user_preferences'):
        from src.core.user_detection import extract_user_preferences
        user_preferences = user_info.get('user_preferences')
        user_preference_bonus = apply_user_preference_bonus(candidate, user_preferences, nlu_result)
        if user_preference_bonus > 0:
            logger.info(f"💊 ユーザー要望ボーナス: {candidate.get('product_name', '')} = +{user_preference_bonus:.2f}")
    
    # --- 2.4 痛みフラグボーナスの条件付き適用（既存コードの修正） ---
    # 痛みフラグボーナス（解熱鎮痛剤への独立したボーナス）
    pain_flag_bonus = 0.0
    medicine_type = candidate.get("medicine_type", "")
    if '解熱鎮痛薬' in medicine_type:
        # ユーザー発話に「痛い」「激痛」「生理痛」が含まれる場合
        user_message = user_text or user_info.get('user_message', '') or ''
        user_message_lower = user_message.lower() if user_message else ''
        pain_keywords = ['痛い', '激痛', '生理痛', '月経痛', '腹痛', 'お腹の痛み', '下腹部痛', '痛み', '痛む']
        
        if any(kw in user_message_lower for kw in pain_keywords):
            # 生理痛の場合はボーナスを維持
            menstrual_keywords = ['生理痛', '月経痛', '生理の痛み', '下腹部痛']
            is_menstrual_pain = any(kw in user_message_lower for kw in menstrual_keywords)
            
            # 症状名からもチェック
            symptom_names_pain = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            has_menstrual_symptom_pain = any(
                any(kw in symptom_name.lower() for kw in menstrual_keywords)
                for symptom_name in symptom_names_pain
            )
            
            if is_menstrual_pain or has_menstrual_symptom_pain:
                pain_flag_bonus = 0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"痛みフラグボーナス（生理痛）: {product_name} = +0.3")
            # それ以外の痛みは削除（アセトアミノフェンボーナスやNSAIDsボーナスに置き換える）
    
    # --- 2.2 アセトアミノフェン含有医薬品へのボーナス追加（炎症系除外） ---
    # アセトアミノフェン含有医薬品へのボーナス
    ingredients_acetaminophen = str(candidate.get('ingredients', '')).lower()
    has_acetaminophen = 'アセトアミノフェン' in ingredients_acetaminophen
    has_ibuprofen = 'イブプロフェン' in ingredients_acetaminophen
    
    acetaminophen_bonus = 0.0
    # アセトアミノフェンのみを含む医薬品（イブプロフェンを含まない）
    if has_acetaminophen and not has_ibuprofen:
        symptom_names_acetaminophen = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        user_text_lower_acetaminophen = user_text.lower() if user_text else ''
        
        # アセトアミノフェンが得意な領域（ボーナス大 +0.3）
        high_match_symptoms = ["頭痛", "発熱", "熱", "悪寒"]
        has_high_match = any(
            any(symptom in symptom_name for symptom in high_match_symptoms)
            for symptom_name in symptom_names_acetaminophen
        )
        
        # 炎症を伴う痛み（NSAIDsの方が適切）
        inflammatory_symptoms = ["筋肉痛", "関節痛", "腰痛", "打撲", "ねんざ", "腱鞘炎"]
        has_inflammatory_pain = any(
            any(symptom in symptom_name for symptom in inflammatory_symptoms)
            for symptom_name in symptom_names_acetaminophen
        )
        
        # 炎症キーワードのチェック
        inflammation_keywords = ["腫れている", "熱を持っている", "炎症"]
        has_inflammation_keyword = any(kw in user_text_lower_acetaminophen for kw in inflammation_keywords)
        
        # 生理痛は除外（ノーシンピュアが適切）
        menstrual_keywords_acetaminophen = ["生理痛", "月経痛", "生理の痛み", "下腹部痛"]
        has_menstrual_pain_acetaminophen = any(
            any(kw in symptom_name.lower() for kw in menstrual_keywords_acetaminophen)
            for symptom_name in symptom_names_acetaminophen
        ) or any(kw in user_text_lower_acetaminophen for kw in menstrual_keywords_acetaminophen)
        
        # 胃への配慮のチェック
        stomach_concern_keywords = [
            "胃が痛い", "胃もたれ", "胃潰瘍", "胃炎", "胃が弱い", 
            "胃が心配", "空腹時", "胃腸が弱い"
        ]
        has_stomach_concern = any(kw in user_text_lower_acetaminophen for kw in stomach_concern_keywords)
        
        # アセトアミノフェンボーナスの適用
        if has_high_match and not has_inflammatory_pain and not has_inflammation_keyword and not has_menstrual_pain_acetaminophen:
            acetaminophen_bonus = 0.4  # 0.3から0.4に強化（カロナールAなどをより推奨）
            # 胃への配慮が検出された場合は追加ボーナス
            if has_stomach_concern:
                acetaminophen_bonus += 0.1  # 合計+0.5
            # カロナールAなどの有名な製品には追加ボーナス
            if 'カロナール' in product_name or 'タイレノール' in product_name:
                acetaminophen_bonus += 0.1  # 合計+0.5または+0.6
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"カロナール/タイレノール追加ボーナス: {product_name} = +0.1")
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アセトアミノフェンボーナス: {product_name} = +{acetaminophen_bonus}")
    
    # --- 主要解熱鎮痛薬の追加ボーナス（強化版） ---
    # カロナールA、ロキソニンS、タイレノールを第一選択として推奨
    major_analgesic_bonus = 0.0
    is_major_analgesic = any(
        major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
    )
    
    if is_major_analgesic:
        # 風邪薬は主要解熱鎮痛薬ボーナスを受けない（総合感冒薬は除外）
        if is_comprehensive_cold_medicine(candidate):
            major_analgesic_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"風邪薬のため主要解熱鎮痛薬ボーナスを適用しない: {product_name}")
        else:
            symptom_names_major = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            
            # 主要解熱鎮痛薬は効能効果チェックをスキップしてボーナスを付与（第一選択として推奨）
            # 頭痛・発熱に対する第一選択として追加ボーナス
            has_headache_or_fever = any(
                any(symptom in symptom_name for symptom in ['頭痛', '発熱', '熱'])
                for symptom_name in symptom_names_major
            )
            
            # カロナールA、タイレノールの場合（頭痛・発熱の第一選択）
            if has_headache_or_fever and ('カロナール' in product_name or 'タイレノール' in product_name):
                major_analgesic_bonus = 0.8  # 0.6から0.8に強化（総合感冒薬のスコアを確実に上回るように）
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（カロナール/タイレノール）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（カロナール/タイレノール）: {product_name} = +{major_analgesic_bonus}")
            
            # 筋肉痛・関節痛・腰痛に対するロキソニンSのボーナス
            has_muscle_pain = any(
                any(symptom in symptom_name for symptom in ['筋肉痛', '関節痛', '腰痛'])
                for symptom_name in symptom_names_major
            )
            if has_muscle_pain and 'ロキソニン' in product_name:
                # 外用薬（テープ・ゲル・パップなど）の場合は追加ボーナス（筋肉痛には湿布が適切）
                is_topical = any(kw in product_name for kw in ['テープ', 'ゲル', 'パップ', 'ローション'])
                if is_topical:
                    major_analgesic_bonus = max(major_analgesic_bonus, 0.8)  # 外用薬は内服薬より優先（0.6 → 0.8に強化）
                    logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛・外用薬）: {product_name} = +{major_analgesic_bonus}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛・外用薬）: {product_name} = +{major_analgesic_bonus}")
                else:
                    major_analgesic_bonus = max(major_analgesic_bonus, 0.6)  # 内服薬も適切だが、外用薬を優先（0.5 → 0.6に強化）
                    logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛）: {product_name} = +{major_analgesic_bonus}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛）: {product_name} = +{major_analgesic_bonus}")
            
            # 頭痛・発熱に対するロキソニンSのボーナス（筋肉痛がない場合）
            elif has_headache_or_fever and 'ロキソニン' in product_name:
                major_analgesic_bonus = max(major_analgesic_bonus, 0.6)  # 頭痛・発熱に対するボーナス（0.4 → 0.6に強化）
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・頭痛/発熱）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・頭痛/発熱）: {product_name} = +{major_analgesic_bonus}")
            
            # イブ、ブファリンの場合（頭痛・発熱の第一選択）
            elif has_headache_or_fever and any(kw in product_name for kw in ['イブ', 'EVE', 'ブファリン', 'バファリン']):
                major_analgesic_bonus = max(major_analgesic_bonus, 0.7)  # カロナール/タイレノールに次ぐ優先度
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（イブ/ブファリン）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（イブ/ブファリン）: {product_name} = +{major_analgesic_bonus}")
    
    # --- 2.3 NSAIDs（イブプロフェン、ロキソプロフェンなど）へのボーナス追加 ---
    # NSAIDs含有医薬品へのボーナス
    nsaids_ingredients = ["イブプロフェン", "ロキソプロフェン", "アスピリン", "インドメタシン"]
    has_nsaids = any(nsaid.lower() in ingredients_acetaminophen for nsaid in nsaids_ingredients)
    
    nsaids_bonus = 0.0
    if has_nsaids:
        symptom_names_nsaids = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        user_text_lower_nsaids = user_text.lower() if user_text else ''
        
        # 炎症を伴う症状
        inflammatory_symptoms_nsaids = ["筋肉痛", "関節痛", "腰痛", "打撲", "ねんざ", "腱鞘炎"]
        has_inflammatory_symptom = any(
            any(symptom in symptom_name for symptom in inflammatory_symptoms_nsaids)
            for symptom_name in symptom_names_nsaids
        )
        
        # 炎症キーワードのチェック
        inflammation_keywords_nsaids = ["腫れている", "熱を持っている", "炎症"]
        has_inflammation_keyword_nsaids = any(kw in user_text_lower_nsaids for kw in inflammation_keywords_nsaids)
        
        # 痛みの強度キーワード（拡張版）
        pain_severity_keywords = [
            "激痛", "激しい痛み", "強い痛み", "ズキズキ", "脈打つような痛み",
            "割れそう", "耐えられない", "ひどい痛み"
        ]
        has_severe_pain = any(kw in user_text_lower_nsaids for kw in pain_severity_keywords)
        
        # 炎症が検出された場合
        if has_inflammatory_symptom or has_inflammation_keyword_nsaids:
            nsaids_bonus = 0.2
            # 強い痛みの場合は追加ボーナス
            if has_severe_pain:
                nsaids_bonus += 0.1  # 合計+0.3
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"NSAIDsボーナス: {product_name} = +{nsaids_bonus}")
    
    # 複数症状の組み合わせによるボーナス（MULTI_SYMPTOM_COMBINATIONSから）
    multi_symptom_bonus = 0.0
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    if len(symptom_names) >= 2:
        from itertools import combinations
        medicine_type = candidate.get("medicine_type", "")
        for combo in combinations(symptom_names, 2):
            combo_key = frozenset(combo)
            adjustments = MULTI_SYMPTOM_COMBINATIONS.get(combo_key)
            if adjustments and medicine_type in adjustments:
                adjustment = adjustments[medicine_type]
                # ボーナス（正の値）のみを適用
                if adjustment > 0.0:
                    multi_symptom_bonus += adjustment
                    symptom_boost += adjustment
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"複数症状ボーナス: {combo_key} × {medicine_type} = {adjustment:+.2f}"
                        )
    
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
    
    # --- 2.5 NSAIDs全般への条件付きペナルティ（15歳未満禁止成分の範囲拡大、胃薬成分考慮） ---
    # 15歳未満使用不可、または慎重投与のNSAIDs成分リスト（拡張版）
    adult_only_nsaids = [
        "イブプロフェン", "ロキソプロフェン", "アスピリン", "アセチルサリチル酸", 
        "インドメタシン", "メフェナム酸", "ジクロフェナク", "ナプロキセン", 
        "ケトプロフェン", "メロキシカム", "ピロキシカム"
    ]
    ingredients_str_nsaids = str(candidate.get('ingredients', '')).lower()
    has_adult_nsaid = any(nsaid.lower() in ingredients_str_nsaids for nsaid in adult_only_nsaids)
    
    nsaid_penalty = 0.0
    if has_adult_nsaid:
        total_penalty = 0.0  # 複数のNSAIDsが含まれている場合の合計ペナルティ
        
        # 各NSAIDs成分のペナルティ値を定義
        nsaid_penalty_values = {
            "イブプロフェン": -0.2,
            "ロキソプロフェン": -0.2,
            "アスピリン": -0.3,  # インフルエンザ・水痘がない場合
            "アセチルサリチル酸": -0.3,  # インフルエンザ・水痘がない場合
            "インドメタシン": -0.2,
            "メフェナム酸": -0.2,
            "ジクロフェナク": -0.2,
            "ナプロキセン": -0.2,
            "ケトプロフェン": -0.2,
            "メロキシカム": -0.2,
            "ピロキシカム": -0.2
        }
        
        # アスピリン含有のチェック
        has_aspirin = 'アスピリン' in ingredients_str_nsaids or 'アセチルサリチル酸' in ingredients_str_nsaids
        
        # インフルエンザ・水痘の疑いの検出（既存のロジックを拡張）
        # 既存のinfluenza_riskフラグを使用
        influenza_risk = nlu_result.get('influenza_risk', False) or False
        
        # 水痘の疑いの検出（キーワードと症状の両方をチェック）
        chickenpox_keywords = [
            "水痘", "みずぼうそう", "水疱瘡", "帯状疱疹", "ヘルペス", 
            "発疹", "水ぶくれ", "水疱"
        ]
        user_text_lower_nsaids = user_text.lower() if user_text else ''
        has_chickenpox_keyword = any(kw in user_text_lower_nsaids for kw in chickenpox_keywords)
        
        # 水痘の症状の組み合わせ（発疹 + 水ぶくれ + かゆみ）
        symptom_names_nsaids_penalty = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_rash = any("発疹" in name or "皮疹" in name for name in symptom_names_nsaids_penalty)
        has_blister = any("水ぶくれ" in name or "水疱" in name for name in symptom_names_nsaids_penalty)
        has_itch = any("かゆみ" in name or "痒み" in name for name in symptom_names_nsaids_penalty)
        has_chickenpox_symptoms = (has_rash and has_blister) or (has_rash and has_itch) or (has_blister and has_itch)
        
        chickenpox_risk = has_chickenpox_keyword or has_chickenpox_symptoms
        
        # アスピリンの特別処理（インフルエンザ・水痘の疑いがある場合は完全に除外）
        if has_aspirin:
            if (influenza_risk or chickenpox_risk) and user_info and user_info.get('age') and user_info.get('age') < 15:
                # 15歳未満かつインフルエンザ・水痘の疑いがある場合は完全に除外
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
                    "contraindication_reason": "アスピリン含有医薬品は、15歳未満のインフルエンザ・水痘患者ではライ症候群のリスクがあるため使用できません。",
                    "contraindication_severity": "critical"
                }
        
        # 胃を守る成分のチェック
        stomach_guard_ingredients = [
            "酸化マグネシウム", "乾燥水酸化アルミニウムゲル", 
            "合成ヒドロタルサイト", "メタケイ酸アルミン酸マグネシウム",
            "水酸化マグネシウム"
        ]
        has_stomach_guard = any(guard.lower() in ingredients_str_nsaids for guard in stomach_guard_ingredients)
        
        # 年齢ベースのペナルティ（15歳未満）
        if user_info and user_info.get('age'):
            age = user_info.get('age')
            if age < 15:
                # 各NSAIDs成分のペナルティを計算
                for nsaid, penalty_value in nsaid_penalty_values.items():
                    if nsaid.lower() in ingredients_str_nsaids:
                        # アスピリンの場合は特別処理（インフルエンザ・水痘がない場合のみペナルティ）
                        if nsaid in ["アスピリン", "アセチルサリチル酸"]:
                            if not (influenza_risk or chickenpox_risk):
                                total_penalty += penalty_value
                        else:
                            total_penalty += penalty_value
                
                # ペナルティの合計に上限を設定（-0.5を超える場合はスコアを0にする）
                if total_penalty < -0.5:
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
                        "contraindication_reason": "15歳未満で使用不可のNSAIDs成分が複数含まれています。",
                        "contraindication_severity": "critical"
                    }
                
                nsaid_penalty = total_penalty
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"NSAIDsペナルティ（年齢）: {product_name} = {nsaid_penalty} (年齢: {age}歳)")
        
        # ユーザー情報ベースのペナルティ（胃腸が弱い、胃潰瘍など）
        if user_info:
            stomach_conditions = [
                '胃腸が弱い', '胃潰瘍', '胃痛', '胃炎', '胃もたれ',
                '胃が弱い', '胃が心配', '空腹時'
            ]
            user_conditions = user_info.get('conditions', []) or []
            has_stomach_condition = any(
                condition in str(user_conditions).lower() or 
                condition in str(user_info).lower() or
                condition in user_text_lower_nsaids
                for condition in stomach_conditions
            )
            
            if has_stomach_condition:
                base_penalty = -0.4  # 胃が弱いのにNSAIDsは原則避けるべきなので強めに
                # 胃薬成分が配合されている場合、かつインフルエンザ・水痘がない場合はペナルティを軽減
                if has_stomach_guard and not (influenza_risk or chickenpox_risk):
                    base_penalty = -0.2  # 胃薬配合なら許容範囲内としてペナルティ軽減（-0.2軽減）
                nsaid_penalty = max(nsaid_penalty, base_penalty)  # より大きいペナルティを適用
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"NSAIDsペナルティ（胃腸）: {product_name} = {base_penalty} (胃薬成分: {has_stomach_guard}, インフルエンザ・水痘リスク: {influenza_risk or chickenpox_risk})")
    
    # --- 2.6 速効性要求への対応（液体カプセルボーナス） ---
    # 速効性要求の検出
    speed_keywords = [
        "速攻", "すぐ", "早く", "即効性", "すぐに効く", 
        "早く治したい", "急いでいる", "すぐ効く"
    ]
    user_text_lower_speed = user_text.lower() if user_text else ''
    has_speed_requirement = any(kw in user_text_lower_speed for kw in speed_keywords)
    
    speed_bonus = 0.0
    if has_speed_requirement:
        # 液体カプセルや溶解の早い製剤の判定
        product_name_lower_speed = product_name.lower()
        usage_speed = str(candidate.get('usage', '')).lower()
        medicine_type_speed = candidate.get('medicine_type', '').lower()
        
        # 液体カプセル、カプセル、顆粒などの判定
        is_fast_dissolving = any(
            form in product_name_lower_speed or form in usage_speed or form in medicine_type_speed
            for form in ['液体', 'カプセル', '顆粒', 'ドリンク', '液剤']
        )
        
        if is_fast_dissolving:
            speed_bonus = 0.1
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"速効性ボーナス: {product_name} = +{speed_bonus}")
    
    # リスク成分の減点（複数症状の場合は減点のみ、単一症状の場合は既に除外済み）
    risk_penalty = 0.0
    if candidate.get('risk_ingredient'):
        risk_penalty = candidate.get('risk_penalty', -0.3)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"リスク成分ペナルティ: {candidate.get('risk_ingredient')} = {risk_penalty}")
    
    # 症状パターンマッチングによる最適化ボーナス/ペナルティ
    pattern_bonus = 0.0
    # 単一症状の場合はpattern_bonusを適用しない（特化薬を優先するため）
    symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
    is_single_symptom_for_pattern = len(symptom_names) == 1
    pattern_info = None
    if not is_single_symptom_for_pattern:
        pattern_info = match_symptom_pattern(nlu_result)
    if pattern_info:
        bonuses = pattern_info.get("bonuses", {})
        penalties = pattern_info.get("penalties", {})
        product_name = candidate.get('product_name', '')
        efficacy = str(candidate.get('efficacy', ''))
        ingredients = str(candidate.get('ingredients', '')).lower()
        medicine_type = candidate.get('medicine_type', '')
        throat_specificity_level = candidate.get('throat_specificity_level', 'none')
        symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
        
        # 総合感冒薬（喉向き）のボーナス
        if "総合感冒薬（喉向き・成分あり）" in bonuses and throat_specificity_level == "component_and_efficacy":
            pattern_bonus += bonuses["総合感冒薬（喉向き・成分あり）"]
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状パターンボーナス（総合感冒薬・喉向き・成分あり）: {product_name} = +{bonuses['総合感冒薬（喉向き・成分あり）']}")
        elif "総合感冒薬（喉向き・効能のみ）" in bonuses and throat_specificity_level == "efficacy_only":
            pattern_bonus += bonuses["総合感冒薬（喉向き・効能のみ）"]
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状パターンボーナス（総合感冒薬・喉向き・効能のみ）: {product_name} = +{bonuses['総合感冒薬（喉向き・効能のみ）']}")
        
        # 五苓散の識別とボーナス
        if "五苓散" in bonuses:
            if "五苓散" in product_name or "五苓散" in ingredients:
                pattern_bonus += bonuses["五苓散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（五苓散）: {product_name} = +{bonuses['五苓散']}")
        
        # L-システイン含有医薬品の識別とボーナス
        if "L-システイン含有医薬品" in bonuses:
            if "l-システイン" in ingredients or "システイン" in ingredients:
                pattern_bonus += bonuses["L-システイン含有医薬品"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（L-システイン含有）: {product_name} = +{bonuses['L-システイン含有医薬品']}")
        
        # 生薬配合の胃腸薬の識別とボーナス
        if "生薬配合の胃腸薬" in bonuses:
            if '胃腸薬' in medicine_type:
                # 生薬成分のキーワード
                herbal_ingredients = ["ショウキョウ", "オウバク", "サンショウ", "カンゾウ", "ケイヒ", "ニンジン", "ブクリョウ"]
                has_herbal = any(herb.lower() in ingredients for herb in herbal_ingredients)
                if has_herbal:
                    pattern_bonus += bonuses["生薬配合の胃腸薬"]
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンボーナス（生薬配合の胃腸薬）: {product_name} = +{bonuses['生薬配合の胃腸薬']}")
        
        # 加味逍遙散の識別とボーナス（月経不順+イライラ）
        if "加味逍遙散" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            kamishoyosan_names = ["加味逍遙散", "カミショウヨウサン", "加味逍遙散エキス", "加味逍遙散エキス顆粒"]
            has_kamishoyosan_name = is_exact_product_match(product_name, kamishoyosan_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_kamishoyosan_name:
                for kamishoyosan_name in kamishoyosan_names:
                    if kamishoyosan_name in product_name:
                        has_kamishoyosan_name = True
                        logger.debug(f"加味逍遙散を部分一致で検出: {product_name} (検索名: {kamishoyosan_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_kamishoyosan_name:
                pattern_bonus += bonuses["加味逍遙散"]
                logger.info(f"⭐ 症状パターンボーナス（加味逍遙散）: {product_name} = +{bonuses['加味逍遙散']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（加味逍遙散）: {product_name} = +{bonuses['加味逍遙散']}")
        
        # 命の母ホワイトの識別とボーナス（月経不順+イライラ）
        if "命の母ホワイト" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            inochi_no_haha_white_names = ["命の母ホワイト", "命の母 ホワイト", "命の母ホワイト錠"]
            has_inochi_no_haha_white_name = is_exact_product_match(product_name, inochi_no_haha_white_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_inochi_no_haha_white_name:
                for inochi_name in inochi_no_haha_white_names:
                    if inochi_name in product_name:
                        has_inochi_no_haha_white_name = True
                        logger.debug(f"命の母ホワイトを部分一致で検出: {product_name} (検索名: {inochi_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_inochi_no_haha_white_name:
                pattern_bonus += bonuses["命の母ホワイト"]
                logger.info(f"⭐ 症状パターンボーナス（命の母ホワイト）: {product_name} = +{bonuses['命の母ホワイト']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（命の母ホワイト）: {product_name} = +{bonuses['命の母ホワイト']}")
        
        # 当帰芍薬散の識別とボーナス（月経不順+冷え症）
        if "当帰芍薬散" in bonuses:
            if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name.upper() or "当帰芍薬散" in efficacy:
                pattern_bonus += bonuses["当帰芍薬散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（当帰芍薬散）: {product_name} = +{bonuses['当帰芍薬散']}")
        
        # 桂枝茯苓丸の識別とボーナス（月経不順+ニキビ、または月経不順+イライラ）
        if "桂枝茯苓丸" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            keishibukuryogan_names = ["桂枝茯苓丸", "ケイシブクリョウガン", "桂枝茯苓丸エキス", "桂枝茯苓丸エキス顆粒"]
            has_keishibukuryogan_name = is_exact_product_match(product_name, keishibukuryogan_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_keishibukuryogan_name:
                for keishi_name in keishibukuryogan_names:
                    if keishi_name in product_name:
                        has_keishibukuryogan_name = True
                        logger.debug(f"桂枝茯苓丸を部分一致で検出: {product_name} (検索名: {keishi_name})")
                        break
            
            # 効能に「月経不順」「血の道症」が含まれる製品を優先（「打撲症」のみの製品は除外）
            has_menstrual_efficacy = "月経不順" in efficacy or "血の道症" in efficacy or "生理不順" in efficacy
            only_daposho = "打撲症" in efficacy and not has_menstrual_efficacy
            
            # 製品名がマッチし、かつ打撲症のみでない場合にボーナス適用
            if has_keishibukuryogan_name and not only_daposho:
                # 月経不順・血の道症が含まれる場合は追加ボーナス
                if has_menstrual_efficacy:
                    pattern_bonus += bonuses["桂枝茯苓丸"] + 0.05  # 追加ボーナス
                    logger.info(f"⭐ 症状パターンボーナス（桂枝茯苓丸・月経不順あり）: {product_name} = +{bonuses['桂枝茯苓丸'] + 0.05}")
                else:
                    pattern_bonus += bonuses["桂枝茯苓丸"]
                    logger.info(f"⭐ 症状パターンボーナス（桂枝茯苓丸）: {product_name} = +{bonuses['桂枝茯苓丸']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（桂枝茯苓丸）: {product_name} = +{bonuses['桂枝茯苓丸']} (効能: {efficacy[:100]}...)")
        
        # ラムールQの識別とボーナス（月経不順+イライラ）
        if "ラムールQ" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            ramuruq_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ"]
            has_ramuruq_name = is_exact_product_match(product_name, ramuruq_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す（CSVデータの表記の違いに対応）
            if not has_ramuruq_name:
                product_name_lower = product_name.lower()
                for ramuruq_name in ramuruq_names:
                    if ramuruq_name.lower() in product_name_lower:
                        has_ramuruq_name = True
                        logger.debug(f"ラムールQを部分一致で検出: {product_name} (検索名: {ramuruq_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_ramuruq_name:
                pattern_bonus += bonuses["ラムールQ"]
                logger.info(f"⭐ 症状パターンボーナス（ラムールQ）: {product_name} = +{bonuses['ラムールQ']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ラムールQ）: {product_name} = +{bonuses['ラムールQ']}")
        
        # ルナエールの識別とボーナス（月経不順+イライラ、錠剤タイプ）
        if "ルナエール" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            luna_elle_names = ["ルナエール", "ルナエール錠"]
            has_luna_elle_name = is_exact_product_match(product_name, luna_elle_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_luna_elle_name:
                for luna_name in luna_elle_names:
                    if luna_name in product_name:
                        has_luna_elle_name = True
                        logger.debug(f"ルナエールを部分一致で検出: {product_name} (検索名: {luna_name})")
                        break
            
            if has_luna_elle_name:
                pattern_bonus += bonuses["ルナエール"]
                logger.info(f"⭐ 症状パターンボーナス（ルナエール）: {product_name} = +{bonuses['ルナエール']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ルナエール）: {product_name} = +{bonuses['ルナエール']}")
        
        # ルナフェミンの識別とボーナス（月経不順+イライラ、錠剤タイプ）
        if "ルナフェミン" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            luna_femin_names = ["ルナフェミン", "ルナフェミン錠"]
            has_luna_femin_name = is_exact_product_match(product_name, luna_femin_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_luna_femin_name:
                for luna_name in luna_femin_names:
                    if luna_name in product_name:
                        has_luna_femin_name = True
                        logger.debug(f"ルナフェミンを部分一致で検出: {product_name} (検索名: {luna_name})")
                        break
            
            if has_luna_femin_name:
                pattern_bonus += bonuses["ルナフェミン"]
                logger.info(f"⭐ 症状パターンボーナス（ルナフェミン）: {product_name} = +{bonuses['ルナフェミン']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ルナフェミン）: {product_name} = +{bonuses['ルナフェミン']}")
        
        # 「イライラ」症状への対応強化：効能効果欄に「ヒステリー」「情緒不安定」「更年期神経症」などのキーワードが含まれる医薬品にボーナス
        if "月経不順" in symptom_names and "イライラ" in symptom_names:
            irritability_keywords = ["ヒステリー", "情緒不安定", "更年期神経症", "更年期障害", "神経症状"]
            efficacy_lower = efficacy.lower()
            has_irritability_keyword = any(keyword in efficacy_lower for keyword in irritability_keywords)
            if has_irritability_keyword:
                irritability_boost = 0.12  # イライラ症状への対応ボーナス
                pattern_bonus += irritability_boost
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"イライラ症状対応ボーナス: {product_name} = +{irritability_boost} (効能: {efficacy[:100]}...)")
        
        # 葛根湯の識別とペナルティ（「のどの痛み+発熱」の場合はペナルティを適用）
        if "葛根湯" in bonuses:
            from src.core.scoring_utils import _is_kampo_or_herbal_medicine
            # 葛根湯の判定：製品名または成分から判定
            is_kampo_check = _is_kampo_or_herbal_medicine(candidate)
            is_kakkonto_by_name = "葛根湯" in product_name
            # 成分から葛根湯を判定（カッコン、カンゾウ、ケイヒ、タイソウ、ショウキョウ、シャクヤク、マオウ）
            kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
            ingredients_normalized_check = normalize_text(ingredients)
            has_kakkonto_ingredients_check = sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized_check) >= 5  # 主要成分の5つ以上が含まれていれば葛根湯
            is_kakkonto_check = is_kakkonto_by_name or (is_kampo_check and has_kakkonto_ingredients_check)
            if is_kampo_check and is_kakkonto_check:
                # 「のどの痛み+発熱」の場合はペナルティを適用（総合感冒薬を優先）
                symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                has_throat = any("のど" in name or "喉" in name or "咽頭" in name for name in symptom_names_list)
                has_fever_symptom = "発熱" in symptom_names_list
                if has_throat and has_fever_symptom and len(symptom_names_list) >= 2:
                    # 「のどの痛み+発熱」の場合はペナルティを適用
                    pattern_bonus += bonuses["葛根湯"]  # bonuses["葛根湯"]は-0.1なので、ペナルティとして適用
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンペナルティ（葛根湯・のど痛み+発熱）: {product_name} = {bonuses['葛根湯']}")
                else:
                    # その他の症状パターンの場合は通常通り
                    pattern_bonus += bonuses["葛根湯"]
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンボーナス（葛根湯）: {product_name} = +{bonuses['葛根湯']}")
        
        # 医薬品種類ごとのボーナス
        for med_type, bonus_value in bonuses.items():
            if med_type in medicine_type:
                pattern_bonus += bonus_value
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（{med_type}）: {product_name} = +{bonus_value}")
        
        # 単一症状（発熱のみ）の場合、解熱鎮痛薬にボーナスを付与、総合感冒薬にペナルティ
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        is_single_symptom = len(symptom_names_list) == 1
        if is_single_symptom and "発熱" in symptom_names_list:
            if '解熱鎮痛薬' in medicine_type:
                pattern_bonus += 0.3  # 単一症状（発熱のみ）の場合、解熱鎮痛薬を優先
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"詳細スコアリング pattern_bonus適用（単一症状・発熱）: medicine_type=解熱鎮痛薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
            elif '風邪薬' in medicine_type:
                pattern_bonus -= 0.2  # 単一症状（発熱のみ）の場合、総合感冒薬にペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"詳細スコアリング pattern_bonus適用（単一症状・発熱）: medicine_type=風邪薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
        
        # リスク成分のペナルティ（便秘薬のセンナ、ヒマシ油など）
        if "リスク成分（センナ、ヒマシ油）" in penalties:
            if "センナ" in ingredients or "ヒマシ油" in ingredients or "カストル油" in ingredients:
                risk_penalty += penalties["リスク成分（センナ、ヒマシ油）"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンペナルティ（リスク成分）: {product_name} = {penalties['リスク成分（センナ、ヒマシ油）']}")
        
        # 二日酔いの場合、乗り物酔い薬へのペナルティ
        # 二日酔いの症状パターンがマッチした場合、乗り物酔い薬にペナルティを適用
        hangover_patterns = [
            frozenset({"頭痛", "むくみ", "だるさ"}),
            frozenset({"頭痛", "むくみ"}),
            frozenset({"頭痛", "だるさ"}),
            frozenset({"むくみ", "だるさ"}),
            frozenset({"頭痛", "吐き気"}),
            frozenset({"頭痛", "だるさ", "吐き気"})
        ]
        symptom_list = [s.get("name") for s in nlu_result.get("symptoms", [])]
        # 症状名の正規化（「疲労感」→「だるさ」など）
        symptom_mapping = {
            "疲労感": "だるさ",
            "倦怠感": "だるさ",
            "疲れ": "だるさ",
            "だるい": "だるさ",
        }
        # 各症状を正規化してからセットに変換（重複を除去）
        normalized_symptom_names = [symptom_mapping.get(name, name) for name in symptom_list]
        normalized_symptom_set = frozenset(normalized_symptom_names)
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"二日酔いパターンチェック: 元の症状={symptom_list}, 正規化後={list(normalized_symptom_set)}")
        
        # 二日酔いの症状パターンがマッチするかチェック
        # パターンの症状がすべて正規化後の症状セットに含まれているか確認
        is_hangover_pattern = False
        matched_pattern = None
        for pattern in hangover_patterns:
            # パターンのすべての症状が正規化後の症状セットに含まれているか
            if pattern.issubset(normalized_symptom_set):
                is_hangover_pattern = True
                matched_pattern = pattern
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い症状パターンマッチ: {pattern} ⊆ {normalized_symptom_set}")
                break
        
        if is_hangover_pattern:
            # 二日酔いの症状パターンがマッチした場合
            if _is_motion_sickness_medicine(candidate):
                # 乗り物酔い薬にペナルティを適用
                pattern_bonus -= 0.20  # 乗り物酔い薬へのペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い症状のため乗り物酔い薬にペナルティ: {product_name} = -0.20")
    
    throat_bonus = 0.0
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    # 症状名の正規化（スペースを削除してからチェック）
    has_throat_symptom = False
    for symptom in symptoms:
        symptom_name = symptom.get("name", "")
        # スペースを削除して正規化
        normalized_name = normalize_text(symptom_name.replace(" ", "").replace("　", ""))
        if normalized_name in THROAT_SYMPTOM_TOKENS:
            has_throat_symptom = True
            break
        # 症状名に「のど」「喉」が含まれている場合もチェック
        if "のど" in symptom_name or "喉" in symptom_name or "咽頭" in symptom_name:
            has_throat_symptom = True
            break
    has_fever = "発熱" in symptom_names
    medicine_type = candidate.get('medicine_type', '')
    throat_specificity_level = candidate.get('throat_specificity_level', 'none')
    
    # デバッグログ（has_throat_symptomとhas_feverの判定結果を確認）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"症状判定: has_throat_symptom={has_throat_symptom}, has_fever={has_fever}, symptom_names={symptom_names}, medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}")
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"症状判定: has_throat_symptom={has_throat_symptom}, has_fever={has_fever}, symptom_names={symptom_names}, throat_specificity_level={throat_specificity_level}, product_name={candidate.get('product_name', '')}")
    
    # 総合感冒薬（喉向き）の識別ログ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        if throat_specificity_level != "none":
            matched_ingredients = []
            if throat_specificity_level == "component_and_efficacy":
                ingredients_str = str(candidate.get('ingredients', '')).lower()
                ingredients_normalized_log = normalize_text(ingredients_str)
                matched_ingredients = [ing for ing in THROAT_SPECIFIC_INGREDIENTS if normalize_text(ing.lower()) in ingredients_normalized_log]
            logger.debug(f"総合感冒薬（喉向き）識別: {candidate.get('product_name', '')}, level={throat_specificity_level}, ingredients={matched_ingredients}")
    
    # 「のど痛み+発熱」の症状パターンでの特別なボーナス
    # 最初に葛根湯チェックを実行（すべてのthroat_bonus処理の前に）
    # 統一された判定関数を使用
    product_name = candidate.get('product_name', '')
    is_kakkonto_medicine = _is_kakkonto_medicine(candidate)
    
    # 葛根湯の条件付き推奨ロジック
    # 風邪の初期（軽度）の場合のみ推奨、それ以外は低優先度
    kakkonto_penalty = 0.0
    if is_kakkonto_medicine:
        # 効能効果に「かぜの初期」が含まれるか確認
        efficacy = candidate.get('efficacy', '')
        has_initial_cold_efficacy = 'かぜの初期' in efficacy or '感冒の初期' in efficacy or '風邪の初期' in efficacy
        
        # NLU結果のseverityが「軽度」か確認
        severity = nlu_result.get("severity", "中等度")
        is_mild_severity = severity == "軽度"
        
        if has_throat_symptom and has_fever:
            # 「のどの痛み+発熱」の場合
            if has_initial_cold_efficacy and is_mild_severity:
                # 風邪の初期（軽度）の場合、ペナルティを軽減（ただし-0.2に強化）
                kakkonto_penalty = -0.2  # -0.1から-0.2に強化（4位以降に配置するため）
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯（風邪の初期・軽度・のど痛み+発熱）: {candidate.get('product_name', '')} = ペナルティ -0.2（強化）")
            else:
                # 風邪の初期でない場合、大きなペナルティを課す
                kakkonto_penalty = -0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯（風邪の初期でない・のど痛み+発熱）: {candidate.get('product_name', '')} = ペナルティ -0.3（総合感冒薬優先）")
    
    # throat_bonusの計算前に、葛根湯の場合は0.0に設定（すべてのthroat_bonus処理の前に）
    if is_kakkonto_medicine:
        throat_bonus = 0.0
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"葛根湯のためthroat_bonusを0.0に設定（のど痛み+発熱）: {product_name}")
    
    # 総合風邪薬の優先推奨ボーナス（複数の風邪症状がある場合）
    comprehensive_cold_bonus = 0.0
    if is_comprehensive_cold_medicine(candidate):
        # 風邪の症状が複数ある場合、総合風邪薬にボーナスを付与
        # 単一症状の場合（ユーザー症状が1つの場合）はボーナスを付与しない（過剰処方を防ぐため）
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
        is_single_symptom = len(symptom_names) == 1
        
        if cold_symptom_count >= 2 and not is_single_symptom:
            # ボーナスをさらに強化（0.7 → 0.9）して、総合風邪薬のスコアを大幅に向上
            # ただし、単一症状の場合は適用しない
            comprehensive_cold_bonus = 0.9
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬優先推奨ボーナス: {candidate.get('product_name', '')} = +0.90 (風邪症状数: {cold_symptom_count})")
        elif cold_symptom_count >= 1 and not is_single_symptom:
            # 風邪症状が1つでもある場合、軽度のボーナスを付与
            # ただし、単一症状の場合は適用しない
            comprehensive_cold_bonus = 0.4
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬優先推奨ボーナス（軽度）: {candidate.get('product_name', '')} = +0.40 (風邪症状数: {cold_symptom_count})")
        elif is_single_symptom:
            # 単一症状の場合はペナルティを適用（過剰処方を防ぐため、-0.8のペナルティに強化）
            comprehensive_cold_bonus = -0.8
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬ペナルティ（単一症状）: {candidate.get('product_name', '')} = -0.8 (症状: {symptom_names})")
    
    # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
    multi_symptom_cold_bonus = 0.0
    if len(symptom_names) >= 3 and '風邪薬' in medicine_type:
        multi_symptom_cold_bonus = 0.15
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"複数症状（3症状以上）時の総合感冒薬への追加ボーナス: {candidate.get('product_name', '')} = +0.15")
    
    # 「のど痛み+発熱」パターンのボーナス適用条件をログ出力（DEBUGレベル）
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"「のど痛み+発熱」パターン検出: product_name={candidate.get('product_name', '')}, medicine_type={medicine_type}, is_kakkonto={is_kakkonto_medicine}")
    
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        # 葛根湯にはボーナスを適用しない（西洋薬を優先）
        # 葛根湯の場合はスキップ
        if not is_kakkonto_medicine:
            if '風邪薬' in medicine_type:
                if throat_specificity_level == "component_and_efficacy":
                    # 総合感冒薬（喉向き・成分あり）に+0.55のボーナス（強化：0.50から0.55に）
                    throat_bonus = 0.55
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・成分あり）ボーナス: {candidate.get('product_name', '')} = +0.55")
                elif throat_specificity_level == "efficacy_only":
                    # 総合感冒薬（喉向き・効能のみ）に+0.45のボーナス（強化：0.40から0.45に）
                    throat_bonus = 0.45
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・効能のみ）ボーナス: {candidate.get('product_name', '')} = +0.45")
                else:
                    # 一般の総合感冒薬にも+0.40のボーナス（強化：0.30から0.40に）
                    throat_bonus = 0.40
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"一般の総合感冒薬ボーナス: {candidate.get('product_name', '')} = +0.40")
            elif '解熱鎮痛薬' in medicine_type:
                # 解熱鎮痛薬に+0.45のボーナス（強化：2位優先のため、0.35から0.45に増加）
                throat_bonus = 0.45
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
            elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and has_throat_symptom):
                # 外用薬（喉スプレー・うがい薬）に+0.45のボーナス（強化：3位優先のため、0.35から0.45に増加）
                throat_bonus = 0.45
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
    
    if has_throat_symptom:
        # 葛根湯チェックは既に上で実行済み（is_kakkonto_medicineを使用）
        # 葛根湯の場合はthroat_bonusを0.0に設定（すべてのthroat_bonus処理の前に）
        if is_kakkonto_medicine:
            throat_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"葛根湯のためthroat_bonusを0.0に設定（のど症状）: {product_name}")
        
        # 単一のど症状の場合、剤形ごとの優先度を明確化
        if len(symptom_names) == 1 and "のどの痛み" in symptom_names:
            # 葛根湯の場合はスキップ
            if not is_kakkonto_medicine:
                if '外用薬（のど）' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.25)  # 局所治療薬を最優先
                elif '外用薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.20)
                elif '解熱鎮痛薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.08)
                elif '風邪薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.05)

        # 通常のthroat_bonus（複数症状や液剤検出時、上記の特別ボーナスがない場合）
        # ただし、葛根湯の場合はスキップ（西洋薬を優先）
        if throat_bonus == 0.0:
            # 葛根湯の場合はスキップ
            if not is_kakkonto_medicine:
                combined_text = candidate.get('product_name', '') + candidate.get('efficacy', '') + medicine_type + candidate.get('usage', '')
                normalized_combined = normalize_text(combined_text)
                detection_bonus = 0.0
                if any(token in normalized_combined for token in THROAT_LIQUID_TOKENS):
                    detection_bonus = 0.12  # 0.18から0.12に調整（液状への加点を適正化）
                elif any(token in normalized_combined for token in THROAT_KEYWORD_TOKENS):
                    detection_bonus = 0.08
                elif '外用薬' in medicine_type:
                    detection_bonus = 0.12

                throat_bonus = max(throat_bonus, detection_bonus)

    # アレルギーペナルティとブースト（アレルギー症状が検出された場合）
    allergy_penalty = candidate.get('allergy_penalty', 0.0)
    allergy_boost = candidate.get('allergy_boost', 0.0)
    
    # 二日酔いブースト（二日酔いが検出された場合）
    hangover_boost = candidate.get('hangover_boost', 0.0)
    
    # 複数症状（3症状以上）時の総合感冒薬への追加ボーナスの上限制限
    limited_multi_symptom_cold_bonus = max(0.0, min(0.15, multi_symptom_cold_bonus))
    
    # 総合風邪薬優先推奨ボーナスの上限制限
    # 総合風邪薬ボーナスの上限を0.9に引き上げ（0.7 → 0.9）
    # 単一症状時のペナルティ（-0.8）も適用するため、下限を-0.8に設定
    limited_comprehensive_cold_bonus = max(-0.8, min(0.9, comprehensive_cold_bonus))
    
    # ボーナス/ペナルティの影響を制限（スコアのばらつきを確保しつつ、特化医薬品の優位性を保つ）
    # 特化医薬品のボーナスは最大0.30まで許可（症状特化型ブースト、throat_bonus）- 総合感冒薬ボーナス強化のため上限を0.30に変更
    # 不適切な医薬品のペナルティは最大-0.30まで許可（症状特異性ペナルティ、リスク成分ペナルティ）
    # アレルギー関連は中程度の影響（-0.20から+0.20）
    # 解熱鎮痛薬と外用薬（のど）のボーナス上限を0.50に引き上げ（2位・3位優先のため強化）
    # 総合感冒薬の上限を0.70に引き上げ（throat_bonus 0.55 + multi_symptom_cold_bonus 0.15 = 0.70）
    if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        limited_throat_bonus = max(-0.20, min(0.50, throat_bonus))  # 解熱鎮痛薬と外用薬（のど）の上限を0.50に引き上げ
    elif '風邪薬' in medicine_type:
        # 総合感冒薬の場合、throat_bonus + multi_symptom_cold_bonusの合計が0.70を超えないように制限
        total_cold_bonus = throat_bonus + multi_symptom_cold_bonus
        if total_cold_bonus > 0.70:
            # 合計が0.70を超える場合は、throat_bonusを0.70 - multi_symptom_cold_bonusに制限
            limited_throat_bonus = max(-0.20, min(0.70 - limited_multi_symptom_cold_bonus, throat_bonus))
        else:
            limited_throat_bonus = max(-0.20, min(0.70, throat_bonus))  # 総合感冒薬の上限を0.70に引き上げ
    else:
        limited_throat_bonus = max(-0.20, min(0.40, throat_bonus))  # 特化医薬品の優位性を保つ（総合感冒薬ボーナス強化のため上限を0.40に変更）
    limited_symptom_boost = max(-0.20, min(0.25, symptom_boost))  # 特化医薬品の優位性を保つ
    
    # symptom_specific_boostとmulti_symptom_bonusが両方適用される場合、合計が0.30を超えないように制限
    # multi_symptom_bonusは既にsymptom_boostに含まれているため、重複を避ける
    # ただし、multi_symptom_bonusは表示用に保持する
    combined_boost = limited_symptom_boost  # symptom_boostには既にmulti_symptom_bonusが含まれている
    if combined_boost > 0.30:
        # 0.30を超える場合は、symptom_boostを0.30に制限
        limited_symptom_boost = 0.30
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"symptom_boostが0.30を超えるため制限: {combined_boost:.3f} → 0.30")
    
    limited_allergy_penalty = max(-0.20, min(0.0, allergy_penalty))  # 中程度のペナルティ
    limited_allergy_boost = max(0.0, min(0.20, allergy_boost))  # 中程度のボーナス
    limited_hangover_boost = max(0.0, min(0.55, hangover_boost))  # 二日酔い医薬品への非常に大幅なブースト（五苓散+頭痛優先）
    # symptom_specificity_penaltyがNoneの場合は0.0を使用
    symptom_specificity_penalty = symptom_specificity_penalty if symptom_specificity_penalty is not None else 0.0
    limited_symptom_specificity_penalty = max(-0.30, min(0.0, symptom_specificity_penalty))  # 不適切な医薬品を確実に下げる
    limited_risk_penalty = max(-0.30, min(0.0, risk_penalty))  # リスク成分のペナルティを強化
    
    # 基本スコア（重み付けによる基本スコア）
    base_score = (
        SCORING_WEIGHTS["症状適合度"] * symptom_score +
        SCORING_WEIGHTS["効能特異性"] * efficacy_specificity_score +
        SCORING_WEIGHTS["年齢適合性"] * age_score +
        SCORING_WEIGHTS["用法簡便性"] * usage_score +
        SCORING_WEIGHTS["副作用リスク"] * side_effect_score +
        SCORING_WEIGHTS["相互作用リスク"] * interaction_score
    )
    
    # 解熱鎮痛薬と外用薬（のど）のbase_scoreを底上げ（「のど痛み+発熱」パターンの場合）
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        if '解熱鎮痛薬' in medicine_type:
            # 解熱鎮痛薬のbase_scoreを底上げ（0.316 → 0.40程度に）
            if base_score < 0.40:
                base_score = 0.40
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬のbase_scoreを底上げ: {product_name} = 0.40")
        elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and has_throat_symptom):
            # 外用薬（のど）のbase_scoreを底上げ（0.316 → 0.40程度に）
            if base_score < 0.40:
                base_score = 0.40
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）のbase_scoreを底上げ: {product_name} = 0.40")
    
    # 部位マッチングスコアの制限（-0.5から+0.3の範囲に変更：1.0は大きすぎる）
    limited_body_part_score = max(-0.5, min(0.3, body_part_score))
    
    # 症状パターンボーナスの制限
    limited_pattern_bonus = max(-0.20, min(0.25, pattern_bonus))
    
    # --- 2.7 解熱鎮痛薬以外の医薬品タイプでの多様性向上 ---
    # 解熱鎮痛薬以外の医薬品タイプでの多様性向上
    medicine_type_diversity = candidate.get("medicine_type", "")
    symptom_names_diversity = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    user_text_lower_diversity = user_text.lower() if user_text else ''
    
    # 症状の重症度に応じた推奨
    severity_keywords = {
        "重度": ["激しい", "ひどい", "重い", "酷い", "深刻", "重症", "強烈", "耐えられない"],
        "軽度": ["少し", "軽い", "軽微", "ちょっと", "やや"],
        "中等度": ["中程度", "普通", "まあまあ"]
    }
    
    # 症状の重症度を判定
    detected_severity = None
    for severity, keywords in severity_keywords.items():
        if any(kw in user_text_lower_diversity for kw in keywords):
            detected_severity = severity
            break
    
    # 重症度に応じたボーナス（重度の症状には強力な医薬品を推奨）
    severity_bonus = 0.0
    if detected_severity == "重度" and is_strong_medicine:
        severity_bonus = 0.1
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"重症度ボーナス: {product_name} = +{severity_bonus}")
    
    # 症状の組み合わせに応じた推奨（複数症状の場合は異なる医薬品を推奨）
    combination_bonus = 0.0
    if len(symptom_names_diversity) >= 2:
        # 複数症状の場合は、より広範囲の効能効果を持つ医薬品にボーナス
        efficacy_diversity = str(candidate.get('efficacy', '')).lower()
        matched_symptoms = sum(1 for symptom in symptom_names_diversity if symptom.lower() in efficacy_diversity)
        if matched_symptoms >= 2:
            combination_bonus = 0.05
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"複数症状マッチボーナス: {product_name} = +{combination_bonus}")
    
    # ユーザーの年齢に応じた推奨（小児用、成人用など）
    age_match_bonus = 0.0
    if user_info and user_info.get('age'):
        age_diversity = user_info.get('age')
        # 小児用製剤の判定
        is_pediatric_form = any(kw in product_name.lower() for kw in ['小児', '子供', 'こども', '小中学生'])
        if age_diversity < 15 and is_pediatric_form:
            age_match_bonus = 0.1
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"年齢適合ボーナス: {product_name} = +{age_match_bonus}")
    
    # 剤形の優先順位調整（症状に応じた剤形ボーナス/ペナルティ）
    dosage_form_bonus = 0.0
    product_name = candidate.get('product_name', '')
    usage = candidate.get('usage', '')
    combined_dosage_text = (product_name + usage).lower()
    
    # のど痛みがある場合、液剤に+0.08、外用薬（のど）に+0.12のボーナス（既存ロジックを維持）
    if has_throat_symptom:
        if any(token in combined_dosage_text for token in ["液", "シロップ", "ドリンク", "内服液"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.08)
        if '外用薬（のど）' in medicine_type:
            dosage_form_bonus = max(dosage_form_bonus, 0.12)
    
    # 胃痛がある場合、錠剤・カプセルを優先（液剤は-0.05のペナルティ）
    if "胃痛" in symptom_names:
        if any(token in combined_dosage_text for token in ["錠", "カプセル", "錠剤"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.05)
        elif any(token in combined_dosage_text for token in ["液", "シロップ", "ドリンク", "内服液"]):
            dosage_form_bonus = min(dosage_form_bonus, -0.05)
    
    # 便秘の場合、錠剤・カプセルを優先
    if "便秘" in symptom_names:
        if any(token in combined_dosage_text for token in ["錠", "カプセル", "錠剤"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.05)
    
    # 筋肉痛の場合、外用薬（テープ・ゲル・パップなど）を優先（湿布が適切）
    if "筋肉痛" in symptom_names:
        is_topical_muscle = any(token in combined_dosage_text for token in ["テープ", "ゲル", "パップ", "ローション", "軟膏", "クリーム"]) or '外用薬（皮膚）' in medicine_type
        if is_topical_muscle:
            dosage_form_bonus = max(dosage_form_bonus, 0.25)  # 筋肉痛には外用薬を強く推奨
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"筋肉痛・外用薬ボーナス: {product_name} = +0.25")
    
    limited_dosage_form_bonus = max(-0.10, min(0.25, dosage_form_bonus))  # 上限を0.25に引き上げ（筋肉痛の外用薬ボーナスに対応）
    
    # 成分ベースのボーナス
    ingredient_boost = calculate_ingredient_based_boost(candidate, nlu_result, user_info, user_text)
    limited_ingredient_boost = max(0.0, min(0.25, ingredient_boost))  # 最大0.25まで
    if limited_ingredient_boost > 0:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"🔬 成分ベーススコア: {candidate.get('product_name', '')} = +{limited_ingredient_boost:.2f}")
    
    # 月経不順症状で漢方薬かつ食前・食間への微小な加点（新規追加）
    dosage_timing_boost = 0.0
    menstrual_symptoms_list = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom_list = any(symptom in symptom_names for symptom in menstrual_symptoms_list)
    
    # ライフステージ（年齢層）による補正
    life_stage_boost = 0.0
    if has_menstrual_symptom_list:
        life_stage = determine_life_stage(user_info, nlu_result)
        
        # 若年層（10-20代）: 「桂枝茯苓丸」や「鎮痛剤配合薬」をブースト
        if life_stage == "若年層":
            if "桂枝茯苓丸" in product_name or "ケイシブクリョウガン" in product_name.upper():
                life_stage_boost = max(life_stage_boost, 0.15)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（若年層）: 桂枝茯苓丸 = +0.15 ({candidate.get('product_name', '')})")
            # 鎮痛剤配合薬（解熱鎮痛薬）をブースト
            if '解熱鎮痛薬' in medicine_type:
                life_stage_boost = max(life_stage_boost, 0.10)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（若年層）: 鎮痛剤配合薬 = +0.10 ({candidate.get('product_name', '')})")
        
        # 中間層（30-40代）: 「加味逍遙散」や「命の母ホワイト」をブースト
        elif life_stage == "中間層":
            if is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
                life_stage_boost = max(life_stage_boost, 0.20)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（中間層）: 加味逍遙散 = +0.20 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
                life_stage_boost = max(life_stage_boost, 0.20)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（中間層）: 命の母ホワイト = +0.20 ({candidate.get('product_name', '')})")
        
        # 更年期前後（50代以上）: 「加味逍遙散」「命の母ホワイト」「ラムールQ」をブースト
        elif life_stage == "更年期前後":
            if is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: 加味逍遙散 = +0.25 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: 命の母ホワイト = +0.25 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["ラムールQ", "ラムールｑ", "ラムールq"]):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: ラムールQ = +0.25 ({candidate.get('product_name', '')})")
    
    if has_menstrual_symptom_list:
        # 漢方薬の判定
        from src.core.scoring_utils import _is_kampo_or_herbal_medicine
        is_kampo = _is_kampo_or_herbal_medicine(candidate)
        
        if is_kampo:
            # 用法用量テキストから「食前」「食間」「空腹時」のキーワードを抽出
            usage_text = str(candidate.get('usage', '')).lower()
            efficacy_text = str(candidate.get('efficacy', '')).lower()
            combined_usage = usage_text + efficacy_text
            
            if any(kw in combined_usage for kw in ["食前", "食間", "空腹時", "空腹"]):
                dosage_timing_boost = 0.02  # 微小な加点
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"月経不順症状+漢方薬+食前・食間のため加点: {candidate.get('product_name', '')} = +0.02")
        
        # ラムールQ、加味逍遙散、命の母ホワイト、ルナエール、ルナフェミンの優先ボーナス（製品名ベース、厳密なマッチング）
        if is_exact_product_match(product_name, ["ラムールQ", "ラムールｑ", "ラムールq"]):
            priority_boost = 0.15  # ラムールQ優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ラムールQ優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
            priority_boost = 0.15  # 加味逍遙散優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"加味逍遙散優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
            priority_boost = 0.15  # 命の母ホワイト優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"命の母ホワイト優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["ルナエール"]):
            priority_boost = 0.12  # ルナエール優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナエール優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["ルナフェミン"]):
            priority_boost = 0.12  # ルナフェミン優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナフェミン優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        
        # 錠剤タイプへの「飲みやすさ」ボーナス（月経不順症状がある場合）
        if any(token in combined_dosage_text for token in ["錠", "錠剤"]):
            tablet_convenience_boost = 0.08  # 飲みやすさボーナス
            dosage_timing_boost += tablet_convenience_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"月経不順症状+錠剤タイプのため飲みやすさボーナス: {candidate.get('product_name', '')} = +{tablet_convenience_boost}")
        
        # ビタミン配合へのボーナス（月経不順症状がある場合）
        ingredients = str(candidate.get('ingredients', '')).lower()
        vitamin_keywords = ["ビタミン", "vitamin", "ビタミンe", "ビタミンb", "トコフェロール", "酢酸トコフェロール"]
        has_vitamin = any(vitamin in ingredients for vitamin in vitamin_keywords)
        if has_vitamin:
            vitamin_boost = 0.08  # ビタミン配合ボーナス
            dosage_timing_boost += vitamin_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"月経不順症状+ビタミン配合のためボーナス: {candidate.get('product_name', '')} = +{vitamin_boost}")
    
    # タイブレーカー（成分重視型 vs 利便性重視型）
    tiebreaker_boost = 0.0
    nlu_severity = nlu_result.get("severity", None)
    if nlu_severity:
        if nlu_severity == "重度":
            # 症状が「強い」（重度）と判定された場合: 成分重視型
            # 効果的な成分が含まれている場合にボーナス（+0.15）
            # 成分含有の有無で判定（成分量は考慮しない）
            # 既にingredient_boostで評価されているため、追加のボーナスは不要
            tiebreaker_boost = 0.0  # ingredient_boostで既に評価済み
        elif nlu_severity == "軽度":
            # 症状が「軽い/仕事中」（軽度）と判定された場合: 利便性重視型
            # 用法の簡便性にボーナス（+0.10）
            # 服用回数（1日2回 < 1日3回）と剤形（カプセル > 錠剤 > 顆粒）の両方を考慮
            usage = str(candidate.get('usage', '')).lower()
            product_name = str(candidate.get('product_name', '')).lower()
            combined_usage = usage + product_name
            
            # 服用回数のチェック
            if any(kw in combined_usage for kw in ["1日1回", "1回", "1日1度"]):
                tiebreaker_boost = 0.10
            elif any(kw in combined_usage for kw in ["1日2回", "2回", "朝晩"]):
                tiebreaker_boost = 0.10
            elif any(kw in combined_usage for kw in ["1日3回", "3回", "食後"]):
                tiebreaker_boost = 0.05
            
            # 剤形のチェック（カプセル > 錠剤 > 顆粒）
            if "カプセル" in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.10)
            elif "錠" in combined_usage and "カプセル" not in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.05)
            elif "顆粒" in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.02)
    
    limited_tiebreaker_boost = max(0.0, min(0.10, tiebreaker_boost))  # 最大0.10まで
    
    # ライフステージボーナスをdosage_timing_boostに追加
    dosage_timing_boost += life_stage_boost
    
    # 月経不順症状がある場合、錠剤ボーナスとビタミン配合ボーナスが追加されるため、上限を引き上げ
    max_dosage_timing_boost = 0.20 if has_menstrual_symptom_list else 0.02
    limited_dosage_timing_boost = max(0.0, min(max_dosage_timing_boost, dosage_timing_boost))
    
    # 漢方薬・生薬製剤の優先度調整（症状パターンごとに異なる処理）
    # adjustment_scoreの計算前に実行する必要がある
    from src.core.scoring_utils import _is_kampo_or_herbal_medicine, _is_goreisan
    kampo_adjustment = 0.0
    
    # 証（Sho）判定によるボーナス/ペナルティ（月経不順症状がある場合）
    sho_bonus = 0.0
    if has_menstrual_symptom_list:
        # 証判定を実行
        user_message = user_text or user_info.get('user_message', '') or ''
        sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
        sho = sho_result.get('sho', '不明')
        confidence = sho_result.get('confidence', 0.0)
        
        # 確信度が低い場合（confidence < 0.5）: ペナルティを適用しない（フラット判定モード）
        if confidence >= 0.5:
            # 医薬品の作用機序を分類
            mechanism = classify_medicine_mechanism(candidate)
            
            # 虚証の場合: 補血・調血系にボーナス、理気・駆瘀血系にペナルティ
            if sho == "虚証":
                if mechanism == "補血・調血系":
                    sho_bonus = 0.15 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ボーナス（虚証→補血系）: {candidate.get('product_name', '')} = +{sho_bonus:.2f} (確信度: {confidence:.2f})")
                elif mechanism == "理気・駆瘀血系":
                    sho_bonus = -0.10 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ペナルティ（虚証→理気系）: {candidate.get('product_name', '')} = {sho_bonus:.2f} (確信度: {confidence:.2f})")
            
            # 実証の場合: 理気・駆瘀血系にボーナス、補血・調血系にペナルティ
            elif sho == "実証":
                if mechanism == "理気・駆瘀血系":
                    sho_bonus = 0.15 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ボーナス（実証→理気系）: {candidate.get('product_name', '')} = +{sho_bonus:.2f} (確信度: {confidence:.2f})")
                elif mechanism == "補血・調血系":
                    sho_bonus = -0.10 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ペナルティ（実証→補血系）: {candidate.get('product_name', '')} = {sho_bonus:.2f} (確信度: {confidence:.2f})")
            
            # 中間証・不明の場合: ペナルティを適用しない（フラット判定モード）
            else:
                sho_bonus = 0.0
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"🔍 証判定（{sho}）のため証ボーナス/ペナルティを適用しません: {candidate.get('product_name', '')}")
        else:
            # 確信度が低い場合: ペナルティを適用しない（フラット判定モード）
            sho_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔍 証判定の確信度が低い（{confidence:.2f}）ため証ボーナス/ペナルティを適用しません: {candidate.get('product_name', '')}")
    
    # 二日酔いの場合、漢方薬ペナルティを無効化
    is_hangover_case = candidate.get('is_hangover', False)
    hangover_boost = candidate.get('hangover_boost', 0.0)
    
    if _is_kampo_or_herbal_medicine(candidate):
        # 二日酔いが検出されている場合、漢方薬ペナルティを適用しない
        if is_hangover_case or hangover_boost > 0:
            kampo_adjustment = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"二日酔いのため漢方薬ペナルティを無効化: {candidate.get('product_name', '')}")
        else:
            # 症状パターンに基づく漢方薬ボーナス/ペナルティ
            pattern_info = match_symptom_pattern(nlu_result)
            product_name = candidate.get('product_name', '')
            is_goreisan = _is_goreisan(candidate)
            # 統一された判定関数を使用
            is_kakkonto_medicine_check = _is_kakkonto_medicine(candidate)
            
            # 症状パターンごとの特別な処理
            if pattern_info:
                # 「のど痛み+発熱」の場合、葛根湯には大きなペナルティを適用（西洋薬を優先）
                # has_throat_symptomとhas_feverの判定も使用（パターンマッチングが失敗した場合のフォールバック）
                symptoms_list = nlu_result.get("symptoms", [])
                symptom_names_list = [s.get("name", "") for s in symptoms_list]
                has_throat = any("のど" in name or "喉" in name or "咽頭" in name for name in symptom_names_list)
                has_fever_symptom = "発熱" in symptom_names_list
                
                if (frozenset({"のどの痛み", "発熱"}) in SYMPTOM_PATTERN_OPTIMIZATION) or (has_throat and has_fever_symptom and len(symptom_names_list) >= 2):
                    if is_kakkonto_medicine_check:
                        # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                        nlu_severity = nlu_result.get("severity", "中等度")
                        if nlu_severity is None or nlu_severity == "":
                            nlu_severity = "中等度"
                        
                        # 中等度以上の場合は大きなペナルティ（風邪の初期向けの医薬品を推奨しない）
                        if nlu_severity in ["中等度", "重度"]:
                            kampo_adjustment = -0.30  # 大きなペナルティ
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"のど痛み+発熱（強度: {nlu_severity}）のため葛根湯に大きなペナルティ: {product_name} = -0.30")
                        else:
                            # 軽度の場合は通常のペナルティ
                            kampo_adjustment = -0.15
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"のど痛み+発熱（強度: {nlu_severity}）のため葛根湯にペナルティ: {product_name} = -0.15")
                    else:
                        # その他の漢方薬は既にpattern_bonusで処理済み
                        kampo_adjustment = 0.0
                # 単一症状（発熱のみ、のど痛みのみ）の場合、漢方薬はペナルティ（症状強度に応じて調整）
                elif len(symptom_names) == 1:
                    # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                    nlu_severity = nlu_result.get("severity", "中等度")
                    if nlu_severity is None or nlu_severity == "":
                        nlu_severity = "中等度"
                    
                    # 縛り表現（必須条件）がある漢方薬の場合はさらに大きなペナルティ
                    efficacy = str(candidate.get('efficacy', '')).lower()
                    has_restrictive_expression = any(
                        kw in efficacy for kw in ['ものの次の諸症', 'ものの次の', 'ものの諸症', 'ものや', 'もの及び', 'もの並びに', 
                                                   '諸関節が腫れて痛む', '各処の筋肉が腫れて痛む', '下腹部に化膿性', '下腹部に凝結']
                    )
                    
                    if has_restrictive_expression:
                        # 縛り表現がある場合は非常に大きなペナルティ（発熱のみには不適切）
                        kampo_adjustment = -0.50
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"単一症状（強度: {nlu_severity}）+ 縛り表現ありのため漢方薬に大きなペナルティ: {product_name} = -0.50")
                    else:
                        # 中等度以上の場合は大きなペナルティ
                        if nlu_severity in ["中等度", "重度"]:
                            kampo_adjustment = -0.30
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.30")
                        else:
                            kampo_adjustment = -0.20
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.20")
                # 風邪の初期症状（悪寒+発熱）の場合、葛根湯にボーナス（ただし症状強度が中等度以上の場合はペナルティ）
                elif frozenset({"悪寒", "発熱"}) in SYMPTOM_PATTERN_OPTIMIZATION and is_kakkonto_medicine_check:
                    # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                    nlu_severity = nlu_result.get("severity", "中等度")
                    if nlu_severity is None or nlu_severity == "":
                        nlu_severity = "中等度"
                    
                    # 中等度以上の場合はペナルティ（風邪の初期向けの医薬品を推奨しない）
                    if nlu_severity in ["中等度", "重度"]:
                        kampo_adjustment = -0.20
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"悪寒+発熱（強度: {nlu_severity}）のため葛根湯にペナルティ: {product_name} = -0.20")
                    else:
                        # 軽度の場合は既にpattern_bonusで処理済み
                        kampo_adjustment = 0.0
                # 二日酔い（頭痛+むくみ+だるさなど）の場合、五苓散はpattern_bonusとhangover_boostで処理済み
                elif is_goreisan and any(
                    pattern_key in SYMPTOM_PATTERN_OPTIMIZATION 
                    for pattern_key in [
                        frozenset({"頭痛", "むくみ", "だるさ"}),
                        frozenset({"頭痛", "むくみ"}),
                        frozenset({"頭痛", "だるさ"}),
                        frozenset({"むくみ", "だるさ"}),
                        frozenset({"頭痛", "吐き気"}),
                        frozenset({"頭痛", "だるさ", "吐き気"})
                    ]
                ):
                    # 既にpattern_bonus（SYMPTOM_PATTERN_OPTIMIZATION）とhangover_boost（append_candidate内）で処理済み
                    kampo_adjustment = 0.0
                # 胃腸症状（胃もたれ+むかつき）の場合、生薬配合の胃腸薬に+0.15のボーナス
                elif frozenset({"吐き気", "胃もたれ", "むかつき"}) in SYMPTOM_PATTERN_OPTIMIZATION:
                    # 既にpattern_bonusで処理済み
                    kampo_adjustment = 0.0
                # その他の症状パターン: 西洋薬を優先（漢方薬は-0.05のペナルティ）
                else:
                    kampo_adjustment = -0.05
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"その他の症状パターンのため漢方薬にペナルティ: {product_name} = -0.05")
            else:
                # 症状パターンがマッチしない場合、ペナルティを適用（西洋薬を優先）
                kampo_adjustment = -0.2
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンがマッチしないため漢方薬にペナルティ: {product_name} = -0.2")
    else:
        kampo_adjustment = 0.0
    
    # 条件付き効能のペナルティ（filter_by_efficacy_symptom_matchで設定された警告）
    # 条件付き効能ペナルティは削除（フィルタリング段階で除外するため不要）
    
    # 調整スコア（ボーナス/ペナルティを制限付きで追加）
    # kampo_adjustmentをadjustment_scoreに含める
    # kakkonto_penalty（葛根湯の条件付き推奨ペナルティ）も追加
    # pain_flag_bonusは独立したボーナス（他のボーナスとは別枠）
    # strong_medicine_bonus_finalは強力な医薬品ボーナス（2.0で追加）
    # noshin_penaltyはノーシンピュアペナルティ（2.1で追加）
    # acetaminophen_bonusはアセトアミノフェンボーナス（2.2で追加）
    # nsaids_bonusはNSAIDsボーナス（2.3で追加）
    # conditional_efficacy_penaltyは条件付き効能ペナルティ（追加）
    adjustment_score = (
        limited_symptom_specificity_penalty +
        limited_risk_penalty +
        limited_throat_bonus +
        limited_multi_symptom_cold_bonus +  # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
        limited_comprehensive_cold_bonus +  # 総合風邪薬優先推奨ボーナス
        limited_symptom_boost +
        limited_allergy_penalty +
        limited_allergy_boost +
        limited_hangover_boost +  # 二日酔いブーストを追加
        limited_body_part_score +
        limited_pattern_bonus +
        limited_dosage_form_bonus +
        limited_ingredient_boost +  # 成分ベースのボーナスを追加
        limited_tiebreaker_boost +  # タイブレーカーボーナスを追加
        limited_dosage_timing_boost +  # 用法用量タイミングボーナス（月経不順+漢方薬+食前・食間）を追加
        kampo_adjustment +  # 漢方薬調整を追加
        sho_bonus +  # 証（Sho）判定によるボーナス/ペナルティを追加
        user_preference_bonus +  # ユーザー要望に基づくボーナスを追加
        kakkonto_penalty +  # 葛根湯の条件付き推奨ペナルティを追加
        pain_flag_bonus +  # 痛みフラグボーナス（独立したボーナス、他のボーナスとは別枠）
        strong_medicine_bonus_final +  # 強力な医薬品ボーナス（2.0で追加）
        noshin_penalty +  # ノーシンピュアペナルティ（2.1で追加）
        acetaminophen_bonus +  # アセトアミノフェンボーナス（2.2で追加）
        nsaids_bonus +  # NSAIDsボーナス（2.3で追加）
        nsaid_penalty +  # NSAIDsペナルティ（2.5で追加）
        speed_bonus +  # 速効性ボーナス（2.6で追加）
        severity_bonus +  # 重症度ボーナス（2.7で追加）
        combination_bonus +  # 複数症状マッチボーナス（2.7で追加）
        age_match_bonus +  # 年齢適合ボーナス（2.7で追加）
        major_analgesic_bonus  # 主要解熱鎮痛薬ボーナス（追加）
    )
    
    # ボーナス/ペナルティ適用のデバッグログ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ボーナス/ペナルティ適用: {candidate.get('product_name', '')}, throat_bonus={throat_bonus}, kakkonto_penalty={kakkonto_penalty}, kampo_adjustment={kampo_adjustment}, adjustment_score={adjustment_score:.3f}")
    
    # 最終スコア（基本スコア + 調整スコア）
    # スコアの分散を確保しつつ、最大スコアを0.98程度に設定
    # 調整スコアの影響を-0.3から+0.25の範囲に制限（より厳しく制限）
    # これにより、基本スコア0.73 + 調整スコア0.25 = 0.98が最大値となる
    # ただし、adjustment_scoreが異常に高い場合は、より厳しく制限
    # 解熱鎮痛薬と外用薬（のど）の場合、調整スコアの上限を0.30に引き上げ（2位・3位優先のため強化）
    # 総合風邪薬の場合、調整スコアの上限を0.40に引き上げ（1位優先のため強化）
    is_comprehensive_cold = is_comprehensive_cold_medicine(candidate)
    is_major_analgesic = any(
        major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
    )
    if is_major_analgesic:
        # 主要解熱鎮痛薬の場合、調整スコアの上限を0.80に引き上げ（major_analgesic_bonusを反映させるため、0.6 → 0.8に強化）
        if adjustment_score > 0.9:
            scaled_adjustment = 0.80
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.80")
        else:
            scaled_adjustment = max(-0.30, min(0.80, adjustment_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のscaled_adjustment: {scaled_adjustment:.3f} (adjustment_score: {adjustment_score:.3f})")
    elif '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        # 解熱鎮痛薬と外用薬（のど）の場合、調整スコアの上限を0.30に引き上げ
        if adjustment_score > 0.5:
            scaled_adjustment = 0.30
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"解熱鎮痛薬/外用薬（のど）のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.30")
        else:
            scaled_adjustment = max(-0.30, min(0.30, adjustment_score))
    elif is_comprehensive_cold:
        # 総合風邪薬の場合、調整スコアの上限を0.40に引き上げ（1位優先のため強化）
        if adjustment_score > 0.6:
            scaled_adjustment = 0.40
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.40")
        else:
            scaled_adjustment = max(-0.30, min(0.40, adjustment_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬のscaled_adjustment: {scaled_adjustment:.3f} (adjustment_score: {adjustment_score:.3f})")
    else:
        if adjustment_score > 0.5:
            # 異常に高い場合は0.25に制限
            scaled_adjustment = 0.25
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"adjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.25")
        else:
            scaled_adjustment = max(-0.30, min(0.25, adjustment_score))
    
    # 改善案1: 基本スコアの底上げ（推奨される医薬品の多くが0.7-0.98に収まるように）
    # 基本スコアが0.45未満の場合は、0.5に底上げしてから調整スコアを追加
    # これにより、推奨される医薬品の多くが0.7-0.98の範囲に収まる
    adjusted_base_score = base_score  # デフォルト値
    
    # 単一症状の場合、総合感冒薬の基本スコアを下げる
    is_single_symptom_for_base = len(symptom_names) == 1
    if is_comprehensive_cold and is_single_symptom_for_base:
        # 単一症状の場合、総合感冒薬の基本スコアを0.1下げる
        adjusted_base_score = max(0.3, base_score - 0.1)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"総合感冒薬の基本スコアを下げる（単一症状）: {product_name} = {adjusted_base_score:.3f} (元: {base_score:.3f})")
    
    # 主要解熱鎮痛薬の場合、基本スコアを底上げする
    if is_major_analgesic:
        if base_score < 0.55:
            # 主要解熱鎮痛薬の基本スコアを0.55に底上げ
            adjusted_base_score = 0.55
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のbase_scoreを底上げ: {product_name} = 0.55 (元: {base_score:.3f})")
        elif base_score < 0.60:
            # 0.55-0.60の範囲は、0.60に近づけるように補間
            adjusted_base_score = 0.55 + (base_score - 0.55) * 0.05 / 0.05
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のbase_scoreを補間: {product_name} = {adjusted_base_score:.3f} (元: {base_score:.3f})")
    elif base_score < 0.45:
        # 低スコア領域（0.45未満）は0.5に底上げ
        # ただし、調整スコアが負の場合は、その分を減算
        # これにより、不適切な医薬品は0.5 - 0.3 = 0.2程度まで下がる
        adjusted_base_score = 0.5
    elif base_score < 0.5:
        # 0.45-0.5の範囲は、0.5に近づけるように補間
        # これにより、より滑らかなスコア分布を実現
        adjusted_base_score = 0.5 + (base_score - 0.45) * 0.5 / 0.05
    
    # 改善案2: スコアの分散を確保するための非線形変換
    # 高スコア領域（0.5以上）では、より細かい差別化を行う
    if adjusted_base_score >= 0.5:
        # 0.5-0.73の範囲を0.5-0.73に拡大（より細かい差別化のため）
        # 平方根（0.85乗）を使用して、より細かい差別化を実現
        # 最大スコアが0.98以下になるように、拡大範囲を0.23に制限
        normalized_base = (adjusted_base_score - 0.5) / 0.23  # 0.5-0.73を0-1に正規化
        expanded_base = 0.5 + (normalized_base ** 0.85) * 0.23  # 0.5-0.73に拡大（非線形変換、最大0.98以下を保証）
        total_score = expanded_base + scaled_adjustment
    else:
        # 低スコア領域（0.5未満）はそのまま使用
        total_score = adjusted_base_score + scaled_adjustment
    
    # raw_scoreを保持（正規化は詳細スコアリング完了後に一括で行う）
    raw_score = total_score  # クリップ前の元のスコアを保持
    
    # 詳細ログの追加: Threshold Pass/Fail Detail、Sho Match Score、成分ベーススコア、証判定、ユーザー要望の反映
    threshold_pass_detail = {
        "passed": raw_score >= 0.35,
        "reason": "unknown",
        "base_score_boost": is_priority_medicine and base_score < 0.50,
        "ingredient_boost": limited_ingredient_boost > 0,
        "pattern_bonus": limited_pattern_bonus > 0,
        "user_preference_bonus": user_preference_bonus > 0,
        "life_stage_boost": life_stage_boost > 0,
        "sho_bonus": sho_bonus != 0.0
    }
    
    # スコアが0.35を超えた理由を判定
    if raw_score >= 0.35:
        if is_priority_medicine and base_score < 0.50:
            threshold_pass_detail["reason"] = "期待される医薬品の基本スコア底上げ"
        elif limited_ingredient_boost > 0:
            threshold_pass_detail["reason"] = "成分ブースト"
        elif limited_pattern_bonus > 0:
            threshold_pass_detail["reason"] = "症状パターンボーナス"
        elif user_preference_bonus > 0:
            threshold_pass_detail["reason"] = "ユーザー要望ボーナス"
        elif life_stage_boost > 0:
            threshold_pass_detail["reason"] = "ライフステージボーナス"
        elif sho_bonus > 0:
            threshold_pass_detail["reason"] = "証ボーナス"
        else:
            threshold_pass_detail["reason"] = "基本スコア"
    else:
        threshold_pass_detail["reason"] = "スコア不足"
    
    # Sho Match Score（証判定の詳細）
    sho_match_score = None
    if has_menstrual_symptom_list and user_info:
        user_message = user_text or user_info.get('user_message', '') or ''
        sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
        sho_match_score = {
            "sho": sho_result.get('sho', '不明'),
            "confidence": sho_result.get('confidence', 0.0),
            "reasons": sho_result.get('reasons', []),
            "kyo_indicators": sho_result.get('kyo_indicators', []),
            "jitsu_indicators": sho_result.get('jitsu_indicators', [])
        }
    
    result = {
        "total_score": raw_score,  # 一時的にraw_scoreを返す（後で正規化される）
        "raw_score": raw_score,  # 元のスコア（表示用）
        "threshold_pass_detail": threshold_pass_detail,  # Threshold Pass/Fail Detail
        "sho_match_score": sho_match_score,  # Sho Match Score
        "score_breakdown": {
            "symptom_match": symptom_score,
            "efficacy_specificity": efficacy_specificity_score,
            "body_part_match": limited_body_part_score,  # 制限後のbody_part_scoreを保存
            "age_fit": age_score,
            "usage_convenience": usage_score,
            "side_effect_risk": side_effect_score,
            "interaction_risk": interaction_score,
            "symptom_specificity_penalty": limited_symptom_specificity_penalty,  # 制限後の症状特異性ペナルティ
            "ingredient_boost": limited_ingredient_boost,  # 成分ベーススコア
            "user_preference_bonus": user_preference_bonus,  # ユーザー要望ボーナス
            "life_stage_boost": life_stage_boost,  # ライフステージボーナス
            "sho_bonus": sho_bonus,  # 証ボーナス
            "risk_ingredient_penalty": limited_risk_penalty,  # 制限後のリスク成分ペナルティ
            "throat_bonus": limited_throat_bonus,  # 制限後のthroat_bonus
            "symptom_specific_boost": limited_symptom_boost,  # 制限後の症状特化型ブースト
            "multi_symptom_bonus": multi_symptom_bonus,  # MULTI_SYMPTOM_COMBINATIONSのボーナス（表示用）
            "multi_symptom_cold_bonus": limited_multi_symptom_cold_bonus,  # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
            "comprehensive_cold_bonus": limited_comprehensive_cold_bonus,  # 総合風邪薬優先推奨ボーナス
            "pattern_bonus": limited_pattern_bonus,  # 制限後の症状パターンボーナス
            "allergy_penalty": limited_allergy_penalty,  # 制限後のアレルギーペナルティ
            "allergy_boost": limited_allergy_boost,  # 制限後のアレルギーブースト
            "hangover_boost": limited_hangover_boost,  # 制限後の二日酔いブースト
            "ingredient_boost": limited_ingredient_boost,  # 成分ベースのボーナス
            "tiebreaker_boost": limited_tiebreaker_boost,  # タイブレーカーボーナス
            "base_score": base_score,  # 基本スコア（デバッグ用）
            "adjusted_base_score": adjusted_base_score,  # 調整後の基本スコア（デバッグ用）
            "adjustment_score": adjustment_score,  # 調整スコア（デバッグ用）
            "kampo_adjustment": kampo_adjustment,  # 漢方薬優先度調整（西洋薬優先の場合-0.2）
            "kakkonto_penalty": kakkonto_penalty  # 葛根湯の条件付き推奨ペナルティ
        }
    }
    
    # 相互作用警告がある場合は追加
    if has_interaction:
        result["interaction_warnings"] = interaction_warnings
    
    # 詳細ログの出力
    if threshold_pass_detail and (DEBUG_MODE or logger.level <= logging.DEBUG):
        logger.debug(f"📊 Threshold Pass/Fail Detail: {candidate.get('product_name', '')} - passed={threshold_pass_detail.get('passed', False)}, reason={threshold_pass_detail.get('reason', 'unknown')}, base_score_boost={threshold_pass_detail.get('base_score_boost', False)}, ingredient_boost={threshold_pass_detail.get('ingredient_boost', False)}, pattern_bonus={threshold_pass_detail.get('pattern_bonus', False)}, user_preference_bonus={threshold_pass_detail.get('user_preference_bonus', False)}, life_stage_boost={threshold_pass_detail.get('life_stage_boost', False)}, sho_bonus={threshold_pass_detail.get('sho_bonus', False)}")
    
    if sho_match_score and (DEBUG_MODE or logger.level <= logging.DEBUG):
        logger.debug(f"🔍 Sho Match Score: {candidate.get('product_name', '')} - sho={sho_match_score.get('sho', '不明')}, confidence={sho_match_score.get('confidence', 0.0):.2f}, reasons={sho_match_score.get('reasons', [])}, kyo_indicators={sho_match_score.get('kyo_indicators', [])}, jitsu_indicators={sho_match_score.get('jitsu_indicators', [])}")
    
    if contraindication_check.get("is_contraindicated", False):
        logger.warning(f"🚫 禁忌事項の除外: {candidate.get('product_name', '')} - {contraindication_check.get('reason', '')}")
    
    return result

# calculate_medicine_score は calculate_final_score のエイリアス（テスト互換性のため）
def calculate_medicine_score(candidate: Dict, nlu_result: Dict, user_info: Dict = None, user_text: str = "") -> Dict:
    """
    calculate_final_score のエイリアス関数（テスト互換性のため）
    
    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報（デフォルト: None）
        user_text: ユーザー入力テキスト（デフォルト: ""）
    
    Returns:
        calculate_final_score と同じ形式のスコア結果辞書
    """
    if user_info is None:
        user_info = {}
    return calculate_final_score(candidate, nlu_result, user_info, user_text)

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
    try:
        symptoms = nlu_result.get("symptoms", [])
        if not symptoms:
            return 0.0
        
        symptom_names = [s.get("name") for s in symptoms]
        medicine_type = candidate.get("medicine_type", "")
        
        # 効能特異性スコアを計算（外部関数を使用）
        from src.core.scoring_utils import calculate_efficacy_specificity_score
        efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)
        
        # 浮動小数点比較用イプシロン
        EPSILON = 0.0001
        
        # 効能特異性が0.0（イプシロン比較）の場合（症状が効能に全く含まれていない場合）は強いペナルティを適用
        if efficacy_specificity < EPSILON:
            # 単一症状の場合、効能に症状が含まれていない場合は大幅減点
            if len(symptom_names) == 1:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状特異性ペナルティ: 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f})")
                return -0.5  # 効能に症状が含まれていない場合は強いペナルティ
        
        # 単一症状の場合
        if len(symptom_names) == 1:
            symptom_name = symptom_names[0]
            
            # 症状カテゴリ間優先表からペナルティを取得
            if symptom_name in SYMPTOM_CATEGORY_PENALTY:
                penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
                if medicine_type in penalty_table:
                    base_penalty = penalty_table[medicine_type]
                    # 単一症状の場合、総合感冒薬（風邪薬）には効能特異性に関係なくペナルティを適用
                    # 効能に症状が含まれていても、単一症状に対して複合薬は過剰処方となる
                    if base_penalty < 0 and medicine_type == '風邪薬':
                        # 総合感冒薬の場合は、効能特異性に関係なくフルペナルティを適用（単一症状時は過剰処方）
                        # 効能特異性が高い場合でも、単一症状に対して複合薬は不適切
                        penalty = base_penalty  # -0.5をそのまま適用（緩和しない）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"症状特異性ペナルティ（単一症状・総合感冒薬）: {symptom_name} + {medicine_type} = {penalty:.2f} (効能特異性{efficacy_specificity:.2f}, フルペナルティ適用)")
                        return penalty
                    
                    # その他の医薬品タイプの場合、従来のロジックを適用
                    # 効能に症状が明記されている場合（efficacy_specificity >= 0.5）は、ペナルティを適用しない
                    # 効能に症状が含まれているということは、その医薬品が症状に対して適切であることを示している
                    if efficacy_specificity >= 0.5:
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"症状特異性ペナルティ: 効能に症状が明記されているためペナルティを適用しない (効能特異性{efficacy_specificity:.2f})")
                        return 0.0  # ペナルティを適用しない
                    
                    # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                    if efficacy_specificity >= 0.95:
                        penalty = base_penalty * 0.25  # 0.17から0.25に変更（緩和を減らす）
                    elif efficacy_specificity >= 0.8:
                        penalty = base_penalty * 0.6   # 0.5から0.6に変更
                    elif efficacy_specificity >= EPSILON:  # イプシロン比較（0.5未満の場合）
                        penalty = base_penalty * 0.7  # 30%緩和
                    elif efficacy_specificity < EPSILON:  # イプシロン比較
                        # 効能特異性が0.0（イプシロン比較）の場合は、ベースペナルティを強化
                        penalty = base_penalty * 1.5  # ペナルティを1.5倍に強化
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
                    # 単一症状の場合、総合感冒薬（風邪薬）には効能特異性に関係なくペナルティを適用
                    # 効能に症状が含まれていても、単一症状に対して複合薬は過剰処方となる
                    if medicine_type == '風邪薬':
                        # 総合感冒薬の場合は、効能特異性に関係なくフルペナルティを適用（単一症状時は過剰処方）
                        # 効能特異性が高い場合でも、単一症状に対して複合薬は不適切
                        base_penalty = -0.5
                        penalty = base_penalty  # -0.5をそのまま適用（緩和しない）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"複合薬ペナルティ（単一症状・総合感冒薬）: {symptom_name} + {medicine_type} = {penalty:.2f} (効能特異性{efficacy_specificity:.2f}, フルペナルティ適用)")
                        return penalty
                    
                    # その他の複合薬の場合は従来のロジックを適用
                    # 効能に症状が明記されている場合（efficacy_specificity >= 0.5）は、複合薬ペナルティを適用しない
                    # 効能に症状が含まれているということは、その医薬品が症状に対して適切であることを示している
                    if efficacy_specificity >= 0.5:
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"複合薬ペナルティ: 効能に症状が明記されているためペナルティを適用しない (効能特異性{efficacy_specificity:.2f})")
                        return 0.0  # ペナルティを適用しない
                    
                    # デフォルトペナルティ（カテゴリ間優先表にない場合）
                    base_penalty = -0.3
                    # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                    if efficacy_specificity >= 0.95:
                        penalty = base_penalty * 0.25  # 0.17から0.25に変更
                    elif efficacy_specificity >= 0.8:
                        penalty = base_penalty * 0.6   # 0.5から0.6に変更
                    elif efficacy_specificity >= EPSILON:  # イプシロン比較（0.5未満の場合）
                        penalty = base_penalty * 0.7  # 30%緩和
                    elif efficacy_specificity < EPSILON:  # イプシロン比較
                        # 効能特異性が0.0（イプシロン比較）の場合は、ベースペナルティを強化
                        penalty = base_penalty * 1.5  # ペナルティを1.5倍に強化
                    else:
                        penalty = base_penalty
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"複合薬ペナルティ: 単一症状({symptom_name})に対して複合薬({medicine_type}) = {base_penalty} → {penalty:.2f} (効能特異性{efficacy_specificity:.2f})")
                    return penalty
        
        # 複数症状の場合
        elif len(symptom_names) >= 2:
            from itertools import combinations

            total_adjustment = 0.0

            # 効能特異性が非常に低い場合（症状が効能に全く含まれていない、またはほとんど含まれていない場合）は強いペナルティを適用
            # このペナルティは他のペナルティよりも優先される
            if efficacy_specificity < 0.1:  # 0.0だけでなく、0.1未満も対象とする
                # 複数症状の場合でも、効能に症状が全く含まれていない場合は大幅減点
                unrelated_penalty = -0.4  # 効能が全く関係ない場合のペナルティ
                total_adjustment += unrelated_penalty
                logger.info(f"症状特異性ペナルティ（複数症状・効能無関係）: {candidate.get('product_name', '')} - 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f}), penalty={unrelated_penalty:.2f}, total_adjustment={total_adjustment:.2f}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状特異性ペナルティ（複数症状・効能無関係）: 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f}), penalty={unrelated_penalty:.2f}")
            else:
                # 効能特異性が0.1以上の場合は、症状カテゴリ間優先表からペナルティを適用
                penalties = []
                for symptom_name in symptom_names:
                    if symptom_name in SYMPTOM_CATEGORY_PENALTY:
                        penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
                        if medicine_type in penalty_table:
                            if '風邪薬' in medicine_type:
                                continue
                            penalty_value = penalty_table[medicine_type]
                            penalties.append(penalty_value)
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"症状特異性ペナルティ（複数症状）: symptom={symptom_name}, medicine_type={medicine_type}, penalty={penalty_value}")

                if penalties:
                    base_penalty = max(penalties)
                    if base_penalty < 0:
                        if efficacy_specificity >= 0.95:
                            base_penalty *= 0.25  # 0.17から0.25に変更
                        elif efficacy_specificity >= 0.8:
                            base_penalty *= 0.6   # 0.5から0.6に変更
                        total_adjustment += base_penalty
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"症状特異性ペナルティ（複数症状・最終）: medicine_type={medicine_type}, penalties={penalties}, base_penalty={base_penalty:.2f}, total_adjustment={total_adjustment:.2f}, efficacy_specificity={efficacy_specificity:.2f}")
                            logger.debug(
                                f"症状特異性ペナルティ（複数症状）: {medicine_type} = {penalties} → {base_penalty:.2f} (効能特異性{efficacy_specificity:.2f})"
                            )

            # 複数症状の組み合わせによるペナルティのみを適用（ボーナスはcalculate_symptom_specific_boostで処理）
            for combo in combinations(symptom_names, 2):
                combo_key = frozenset(combo)
                adjustments = MULTI_SYMPTOM_COMBINATIONS.get(combo_key)
                if adjustments and medicine_type in adjustments:
                    adjustment = adjustments[medicine_type]
                    # ペナルティ（負の値）のみを適用
                    if adjustment < 0.0:
                        total_adjustment += adjustment
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"複数症状ペナルティ適用: combo={combo_key}, medicine_type={medicine_type}, adjustment={adjustment:.2f}, total_adjustment={total_adjustment:.2f}")
                            logger.debug(
                                f"複数症状ペナルティ: {combo_key} × {medicine_type} = {adjustment:.2f}"
                            )
                    # ボーナス（正の値）は無視（calculate_symptom_specific_boostで処理される）

            # 「生理痛」のみが効能の医薬品に対するペナルティ（月経不順が主訴の場合）
            # 効能効果欄に「生理痛」のみが含まれ、かつ「月経不順」「月経異常」「血の道症」が含まれない場合にペナルティ適用
            efficacy = str(candidate.get('efficacy', ''))
            has_menstrual_irregularity = any(symptom in ['月経不順', '生理不順', '月経異常', '生理異常', '血の道症'] for symptom in symptom_names)
            has_dysmenorrhea = any(symptom in ['生理痛', '月経痛'] for symptom in symptom_names)
            
            # 効能効果欄の確認（大文字小文字を区別しないチェック）
            efficacy_lower = efficacy.lower()
            has_dysmenorrhea_in_efficacy = '生理痛' in efficacy_lower or '月経痛' in efficacy_lower
            has_menstrual_irregularity_in_efficacy = ('月経不順' in efficacy_lower or '生理不順' in efficacy_lower or 
                                                       '月経異常' in efficacy_lower or '生理異常' in efficacy_lower or 
                                                       '血の道症' in efficacy_lower or '血の道' in efficacy_lower)
            
            # 「生理痛」のみが効能で、月経不順が主訴の場合
            # 効能特異性が0.1未満の場合でも、「生理痛」のみが効能の場合は追加でペナルティを適用
            if has_dysmenorrhea_in_efficacy and not has_menstrual_irregularity_in_efficacy and has_menstrual_irregularity:
                # 症状に「生理痛」が含まれていない場合のみペナルティを適用
                if not has_dysmenorrhea:
                    # 「生理痛」のみが効能で、主訴が「月経不順」の場合、追加ペナルティを適用
                    # 効能特異性が0.1未満の場合は既に-0.4のペナルティが適用されているため、追加で-0.3のペナルティを適用（合計-0.7）
                    # 効能特異性が0.1以上の場合は-0.25のペナルティを適用
                    if efficacy_specificity < 0.1:
                        dysmenorrhea_penalty = -0.3  # 効能特異性が0.1未満の場合は追加で-0.3のペナルティ
                    else:
                        dysmenorrhea_penalty = -0.25  # 効能特異性が0.1以上の場合は-0.25のペナルティ
                    total_adjustment += dysmenorrhea_penalty
                    logger.info(f"「生理痛」のみが効能のペナルティ適用: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...), penalty={dysmenorrhea_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}, total_adjustment={total_adjustment:.2f}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"「生理痛」のみが効能のペナルティ適用: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...), penalty={dysmenorrhea_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}")
            
            # ペナルティのみを返す（負の値または0）
            # この関数はペナルティのみを返し、ボーナスは別途calculate_symptom_specific_boostで処理される
            if total_adjustment != 0.0:
                final_penalty = min(0.0, total_adjustment)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"calculate_symptom_specificity_penalty最終結果: {candidate.get('product_name', '')} - total_adjustment={total_adjustment:.2f}, final_penalty={final_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}")
                # 負の値のみを返す（正の値が含まれている場合は0を返す）
                return final_penalty
            
            return 0.0
    except Exception as e:
        logger.warning(f"症状特異性ペナルティ計算エラー: {e}")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            import traceback
            logger.debug(f"詳細: {traceback.format_exc()}")
        return 0.0  # エラー時は安全側に倒す

# ================================================================================
# 4.6 推奨後の検証関数（_recheck_risk_ingredients, _check_influenza_compatibility, detect_influenza_risk は candidate_scoring から import）
# ================================================================================

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

    # 3. 下痢情報がない腹痛単独相談では止瀉薬候補を除外
    validated = _filter_antidiarrheal_without_diarrhea(validated, nlu_result)

    # 3.5. 効能効果と症状のマッチングに基づくフィルタリング（単一症状限定医薬品の除外）
    validated = filter_by_efficacy_symptom_match(validated, nlu_result)

    # 4. 症状適合度スコアの最低閾値を適用
    validated = _enforce_symptom_match_threshold(validated, nlu_result)
    
    # 4.5. 性器周辺症状の場合、刺激の強い外用薬を除外
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part == "delicate_area":
        filtered_candidates = []
        for candidate in validated:
            medicine_type = str(candidate.get('medicine_type', '')).lower()
            ingredients = str(candidate.get('ingredients', '')).lower()
            
            # 刺激の強い成分のキーワード
            strong_ingredients = ["メントール", "カンフル", "アンモニア", "サリチル酸", "メントール", "dl-カンフル", "l-メントール"]
            has_strong_ingredient = any(ing in ingredients for ing in strong_ingredients)
            
            # 性器専用の医薬品は優先
            candidate_body_part = _detect_body_part_specificity(candidate)
            if candidate_body_part == "delicate_area":
                filtered_candidates.append(candidate)
            # 刺激の強い外用薬は除外
            elif "外用薬（皮膚）" in medicine_type or "外用" in medicine_type:
                if has_strong_ingredient:
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"性器周辺症状: 刺激の強い外用薬を除外: {candidate.get('product_name', '')}"
                        )
                    continue  # この候補を除外
                else:
                    # 刺激の強い成分がない場合は残すが、警告を追加
                    candidate['delicate_area_warning'] = True
                    filtered_candidates.append(candidate)
            else:
                # 外用薬以外は残す
                filtered_candidates.append(candidate)
        
        validated = filtered_candidates
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"性器周辺症状: {len(validated)}件の候補をフィルタリング後")
    
    # 4.6. 効能特異性が非常に低い医薬品を除外（症状に合わない医薬品を除外）
    from src.core.scoring_utils import calculate_efficacy_specificity_score
    
    filtered_by_efficacy = []
    for candidate in validated:
        # 効能特異性スコアを計算
        efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)
        # 症状特異性ペナルティを計算
        symptom_specificity_penalty = calculate_symptom_specificity_penalty(candidate, nlu_result)
        
        # 浮動小数点比較用イプシロン
        EPSILON = 0.0001
        
        # 効能特異性が0.0（イプシロン比較）または非常に低い（0.1未満）かつ症状特異性ペナルティが-0.6以下の医薬品を除外
        # または、効能特異性が0.0（イプシロン比較）で症状特異性ペナルティが-0.4以下かつ効能に「生理痛」のみが含まれる場合も除外
        # または、大黄牡丹皮湯で便秘傾向がない場合も除外
        efficacy = str(candidate.get('efficacy', '')).lower()
        product_name_lower = str(candidate.get('product_name', '')).lower()
        has_only_dysmenorrhea = ('生理痛' in efficacy or '月経痛' in efficacy) and not any(kw in efficacy for kw in ['月経不順', '生理不順', '月経異常', '生理異常', '血の道症', '血の道'])
        
        # 大黄牡丹皮湯の判定（便秘傾向がない場合に除外）
        is_daioubotanpi = '大黄牡丹皮湯' in product_name_lower or 'だいおうぼたんぴとう' in product_name_lower or 'ダイオウボタンピトウ' in product_name_lower
        # 効能に「便秘の傾向」「便秘傾向」「便秘」が含まれているか確認
        has_constipation_efficacy = '便秘' in efficacy or '便通' in efficacy or '便秘の傾向' in efficacy or '便秘傾向' in efficacy
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_constipation_symptom = '便秘' in symptom_names_list
        
        if is_daioubotanpi:
            logger.info(f"🔍 大黄牡丹皮湯チェック: {candidate.get('product_name', '')}, 効能に便秘関連: {has_constipation_efficacy}, 症状に便秘: {has_constipation_symptom}, 効能: {efficacy[:150]}...")
        
        should_exclude = False
        if efficacy_specificity < 0.1 and symptom_specificity_penalty <= -0.6:
            should_exclude = True
        elif efficacy_specificity < EPSILON and symptom_specificity_penalty <= -0.4 and has_only_dysmenorrhea:
            # 「生理痛」のみが効能で、月経不順が主訴の場合も除外
            should_exclude = True
        elif is_daioubotanpi and not has_constipation_efficacy and not has_constipation_symptom:
            # 大黄牡丹皮湯で便秘傾向がない場合も除外（下腹部痛を伴う月経不順・月経困難症、便秘、痔疾などに用いられるため）
            should_exclude = True
            logger.info(f"⚠️ 大黄牡丹皮湯を除外: {candidate.get('product_name', '')} (便秘傾向がないため、効能: {efficacy[:150]}...)")
        
        if should_exclude:
            product_name = candidate.get('product_name', '')
            efficacy = candidate.get('efficacy', '')
            logger.info(f"⚠️ 効能特異性が低く症状に合わない医薬品を除外: {product_name} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f}, 効能: {efficacy[:100]}...)")
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"⚠️ 効能特異性が低く症状に合わない医薬品を除外: {product_name} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f})")
            continue
        
        filtered_by_efficacy.append(candidate)
    
    validated = filtered_by_efficacy
    
    # 5. スコアが0.0の候補を除外、0.3未満の候補を警告付きで残す
    # 期待される医薬品をスコアフィルタリングから保護（計画要件: 期待される医薬品の優先確保）
    priority_medicine_names_for_protection = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
    
    final_candidates = []
    protected_medicines = []
    for candidate in validated:
        score = candidate.get('final_score', 0.0)
        product_name = candidate.get('product_name', '')
        product_name_lower = product_name.lower()
        
        # 期待される医薬品かどうかをチェック（部分一致も許可）
        is_priority = False
        for priority_name in priority_medicine_names_for_protection:
            priority_name_lower = priority_name.lower()
            # 完全一致、部分一致、正規化後一致をチェック
            if (product_name_lower == priority_name_lower or 
                priority_name_lower in product_name_lower or 
                product_name_lower in priority_name_lower or
                is_exact_product_match(product_name, [priority_name])):
                is_priority = True
                protected_medicines.append(candidate)
                logger.info(f"🔒 期待される医薬品をスコアフィルタリングから保護: {product_name} (スコア: {score:.3f}, 検索名: {priority_name})")
                break
        
        # スコア0の候補を完全に除外（期待される医薬品は保護）
        if score <= 0.0:
            if is_priority:
                # 期待される医薬品はスコアが0でも保護
                final_candidates.append(candidate)
                logger.info(f"🔒 期待される医薬品をスコアフィルタリングから保護して追加: {product_name} (スコア: {score:.3f})")
            else:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"⚠️ スコア0の候補を除外: {product_name} (スコア: {score:.3f})")
                continue
        
        if score < 0.3:
            candidate['low_score_warning'] = True
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"⚠️ 低スコア警告: {product_name} (スコア: {score:.3f})")
        
        if not is_priority:  # 期待される医薬品は既に追加済み
            final_candidates.append(candidate)
    
    return final_candidates

# ================================================================================
# 5. 不足情報のチェックと質問生成（missing_info_service から import）
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
    
    # やけどの程度判定（ガードレール）- 早期チェック
    burn_severity, is_burn_doctor_referral = detect_burn_severity(user_text)
    if is_burn_doctor_referral:
        logger.info("やけどの重度判定により、医師受診を推奨します")
        return {
            "status": "doctor_referral",
            "is_doctor_referral": True,
            "reason": "重度のやけどの可能性があります",
            "recommended_medicines": [],
            "usage_notes": "",
            "doctor_consultation": "⚠️ 重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
            "error_message": "重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
            "severity": burn_severity
        }
    
    # 入力検証: 空入力・意味のない文字列のチェック
    if not user_text or not user_text.strip():
        logger.warning("空の入力が検出されました")
        return {
            "status": "error",
            "reason": "症状を入力してください",
            "recommended_medicines": [],
            "error_message": "症状を入力してください。具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください。",
            "technical_details": f"入力テキスト: '{user_text}', 空文字列または空白のみ"
        }
    
    # 意味のない文字列のチェック
    user_text_stripped = user_text.strip()
    
    # 極端に短い文字列（3文字未満）
    if len(user_text_stripped) < 3:
        logger.warning(f"極端に短い入力が検出されました: {user_text_stripped}")
        return {
            "status": "error",
            "reason": "症状を詳しく入力してください",
            "recommended_medicines": [],
            "error_message": "症状を詳しく入力してください（3文字以上）。具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）。",
            "technical_details": f"入力テキスト: '{user_text_stripped}', 文字数: {len(user_text_stripped)}（3文字未満）"
        }
    
    # 繰り返し文字のみのチェック（例: 「あああ」「テストテスト」）
    if len(set(user_text_stripped)) <= 2 and len(user_text_stripped) >= 3:
        # 同じ文字が3回以上繰り返されている場合
        char_counts = {}
        for char in user_text_stripped:
            char_counts[char] = char_counts.get(char, 0) + 1
        if max(char_counts.values()) >= 3:
            logger.warning(f"繰り返し文字のみの入力が検出されました: {user_text_stripped}")
            return {
                "status": "error",
                "reason": "症状を入力してください",
                "recommended_medicines": [],
                "error_message": "症状を入力してください。具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）。",
                "technical_details": f"入力テキスト: '{user_text_stripped}', 文字数: {len(user_text_stripped)}, 繰り返し文字パターン検出"
            }
    
    # 医療関連キーワードが一切含まれていない場合のチェック（簡易版）
    # 注: より厳密なチェックはNLU結果に依存するため、ここでは基本的なチェックのみ
    # 重要: load_symptom_dictionary()に登録されているすべての症状に対応するキーワードを網羅的に追加
    # これにより、考慮漏れによって推奨処理が停止することを防ぐ
    medical_keywords = [
        # 基本キーワード（必須）
        "痛", "熱", "咳", "鼻", "喉", "頭", "胃", "下痢", "便秘", "吐", "めまい",
        "かゆ", "発疹", "不眠", "疲労", "症状", "病気", "薬", "医", "病",
        
        # 風邪関連キーワード（「風邪を完治したい」などの表現に対応）
        "風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状",
        "風邪を完治", "風邪を治", "風邪を直", "完治", "治したい", "治す", "直したい", "直す",
        
        # 風邪関連症状（load_symptom_dictionary()から抽出）
        "発熱", "熱がある", "熱っぽい", "高熱", "微熱", "体温", "熱",
        "頭痛", "頭が痛い", "ズキズキ", "頭が重い", "偏頭痛",
        "のど", "喉", "咽頭", "声がれ", "のどの痛み", "喉の痛み", "喉の腫れ",
        "せき", "咳", "咳が出る", "咳込む", "空咳",
        "痰", "たん", "痰が絡む", "痰が出る",
        "鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい",
        "鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉",
        "くしゃみ", "クシャミ",
        "悪寒", "寒気", "さむけ", "ゾクゾク",
        "関節痛", "関節の痛み", "節々", "関節が痛い",
        "筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い",
        
        # 解熱鎮痛薬関連症状
        "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理", "月経",
        "歯痛", "歯が痛い", "歯の痛み", "歯",
        
        # 鼻炎用薬関連症状
        "鼻汁過多", "鼻水が多い", "鼻水がとまらない",
        "なみだ目", "涙目", "涙",
        
        # 胃腸薬関連症状
        "胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおち",
        "腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "お腹",
        "軟便", "水様便", "便がゆるい", "便",
        "便が出ない", "便通がない", "便が硬い",
        "吐き気", "むかつき", "気持ち悪い", "嘔吐感", "嘔吐",
        "胸やけ", "胸焼け", "胃もたれ", "胃の重い感じ", "消化が悪い", "胃の不快感",
        
        # 外用薬関連症状
        "かゆみ", "かゆい", "痒み", "痒い", "痒", "皮膚のかゆみ",
        "ブツブツ", "赤い斑点", "皮膚の異常",
        "湿疹", "皮膚炎", "かぶれ", "皮膚の炎症", "皮膚",
        "水虫", "白癬", "足の水虫", "指の間",
        "打撲", "打ち身", "青あざ", "内出血",
        "捻挫", "くじいた", "靭帯損傷",
        "肩こり", "肩の凝り", "肩の痛み", "首肩", "肩", "こり",
        "腰痛", "腰", "腰の痛み",
        
        # 目薬関連症状
        "目の充血", "目が赤い", "充血", "目の血走り", "目", "眼",
        "目の疲れ", "眼精疲労", "目が疲れる", "目の重い感じ", "疲れ",
        "目のかゆみ", "目がかゆい", "目の痒み",
        
        # 睡眠・精神関連症状
        "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠", "睡眠",
        "眩暈", "ふらつき", "立ちくらみ",
        "乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う", "乗物酔い",
        "疲労感", "疲れ", "だるい", "倦怠感", "倦怠",
        "イライラ", "いらいら", "焦燥感", "落ち着かない",
        "不安", "心配", "憂鬱", "落ち込み",
        "ストレス", "緊張", "プレッシャー",
        
        # 重症疑い症状（RED_FLAG_SYMPTOMS）
        "呼吸困難", "呼吸が苦しい", "息苦しい", "息ができない", "息切れ",
        "38.5度以上", "39度", "40度", "熱が下がらない",
        "胸痛", "胸が痛い", "胸の痛み", "胸部痛", "心臓が痛い", "胸が締め付けられる",
        "意識障害", "意識がもうろう", "意識がない", "気を失う", "意識不明", "ぼーっと",
        "激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛", "頭が割れる", "耐えられない頭痛",
        "血便", "便に血が混じる", "黒い便", "タール便",
        "喀血", "血を吐く", "吐血",
        "激しい腹痛", "お腹が痛くて動けない", "耐えられない腹痛",
        "顔面麻痺", "顔が動かない", "口が曲がる", "顔の半分が動かない",
        "手足の麻痺", "手足が動かない", "力が入らない", "しびれが続く", "しびれ",
        "持続する嘔吐", "何度も吐く", "止まらない嘔吐", "嘔吐が続く",
        
        # その他の一般的な医療関連キーワード
        "耳", "耳の痛み", "耳鳴り",
        "口内炎", "口", "口の中",
        "喉頭", "気管", "気管支",
        "消化", "食欲", "食欲不振",
        "血圧", "血圧が高い", "血圧が低い",
        "動悸", "心拍", "脈",
        "発汗", "汗", "多汗",
        "冷え", "冷え性", "冷える",
        "むくみ", "浮腫",
        "しこり", "腫れ", "腫れる",
        "炎症", "感染", "菌",
        "ウイルス", "細菌",
        "アレルギー", "アレルギー症状",
        "かぶれ", "接触性皮膚炎",
        "やけど", "火傷", "熱傷",
        "切り傷", "擦り傷", "傷",
        "骨折", "骨",
        "筋肉", "筋",
        "神経", "神経痛",
        "リウマチ", "関節リウマチ",
        "痛風",
        "貧血", "貧血気味",
        "低血糖", "高血糖", "血糖",
        "コレステロール",
        "脂質",
        "肝臓", "肝機能",
        "腎臓", "腎機能",
        "膀胱", "尿", "排尿",
        "月経", "生理", "月経不順",
        "更年期", "ホルモン",
        "妊娠", "妊婦",
        "授乳", "母乳",
        "小児", "子供", "こども", "幼児", "乳児",
        "高齢者", "老人",
        "処方", "処方箋",
        "副作用", "効能", "効果",
        "用法", "用量", "服用", "飲む", "飲み",
        "錠剤", "カプセル", "粉薬", "シロップ", "液剤",
        "軟膏", "クリーム", "ローション", "スプレー",
        "点眼", "点鼻", "点耳",
        # 風邪関連のキーワード
        "風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状",
        "風邪を完治", "風邪を治", "風邪を直", "治したい", "治す"
    ]
    has_medical_keyword = any(keyword in user_text_stripped for keyword in medical_keywords)
    
    # ステップ1: NLU（症状抽出）- キーワードチェックの前に実行して、症状が検出される場合はキーワードチェックをスキップ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1: NLU（症状抽出） ---")
    nlu_result = hybrid_nlu_extraction(user_text, user_info, client, session_id)
    
    # やけどの場合、NLU結果から強度を確認（ガードレールで検出されなかった場合）
    if burn_severity is not None and not is_burn_doctor_referral:
        # NLU結果からやけどの強度を確認
        nlu_severity = nlu_result.get("severity", "中等度")
        symptoms_list = nlu_result.get("symptoms", [])
        # やけどの症状がある場合、その強度を確認
        burn_symptoms = [s for s in symptoms_list if "やけど" in s.get("name", "")]
        if burn_symptoms:
            burn_symptom_severity = burn_symptoms[0].get("severity", "中等度")
            # 軽度・中等度は市販薬で対処可能、重度は受診勧奨
            if burn_symptom_severity == "重度" or nlu_severity == "重度":
                logger.info("やけどの重度判定（NLU）により、医師受診を推奨します")
                return {
                    "status": "doctor_referral",
                    "is_doctor_referral": True,
                    "reason": "重度のやけどの可能性があります",
                    "recommended_medicines": [],
                    "usage_notes": "",
                    "doctor_consultation": "⚠️ 重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
                    "error_message": "重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
                    "severity": "重度"
                }
    
    # NLU結果を確認し、症状が検出されている場合はキーワードチェックをスキップ
    symptoms_detected = nlu_result.get("symptoms", [])
    has_detected_symptoms = len(symptoms_detected) > 0
    
    # 症状が検出されていない場合、select_symptoms_via_gptで抽出を試みる
    if not has_detected_symptoms:
        try:
            from src.core.medicine_logic import select_symptoms_via_gpt
            logger.info(f"🔍 select_symptoms_via_gptで症状抽出を試みます: {user_text}")
            symptom_extraction_result = select_symptoms_via_gpt(user_text, client=client)
            logger.debug(f"🔍 select_symptoms_via_gptの結果: {symptom_extraction_result}")
            
            # select_symptoms_via_gptは直接 {'status': 'success', 'symptoms': [...], 'message': '...'} を返す
            if symptom_extraction_result and 'symptoms' in symptom_extraction_result:
                extracted_symptom_names = symptom_extraction_result['symptoms']
                logger.debug(f"🔍 extracted_symptom_names: {extracted_symptom_names}")
                
                if extracted_symptom_names:
                    # 抽出された症状をnlu_resultに統合
                    symptoms_list = []
                    for symptom_name in extracted_symptom_names:
                        symptoms_list.append({
                            "name": symptom_name,
                            "severity": "中等度",
                            "duration": "不明",
                            "body_part": None
                        })
                    nlu_result["symptoms"] = symptoms_list
                    has_detected_symptoms = True
                    # confidence_scoreも更新
                    nlu_result["confidence_score"] = 0.7  # フォールバック抽出のため中程度の信頼度
                    logger.info(f"✅ select_symptoms_via_gptで症状を抽出: {extracted_symptom_names}")
                else:
                    logger.warning(f"⚠️ select_symptoms_via_gptで症状が抽出されませんでした（空のリスト）")
            else:
                logger.warning(f"⚠️ select_symptoms_via_gptの結果に'symptoms'キーがありません: {symptom_extraction_result}")
        except Exception as e:
            logger.warning(f"⚠️ select_symptoms_via_gptでの症状抽出に失敗: {e}")
            import traceback
            traceback.print_exc()
    
    # 医療キーワードがなく、かつ短い文字列の場合、かつ症状も検出されていない場合のみエラー
    if not has_medical_keyword and len(user_text_stripped) < 10 and not has_detected_symptoms:
        logger.warning(f"医療関連キーワードが含まれていない入力が検出されました（症状も検出されませんでした）: {user_text_stripped}")
        return {
            "status": "error",
            "reason": "症状を入力してください",
            "recommended_medicines": [],
            "error_message": "症状を入力してください（例: 頭痛、発熱、のどの痛みなど）。より具体的な症状名を含めて記述してください。",
            "technical_details": f"入力テキスト: {user_text_stripped}, 文字数: {len(user_text_stripped)}, 医療キーワード検出: {has_medical_keyword}, 症状検出: {has_detected_symptoms}"
        }
    
    # 部位情報の抽出
    symptoms = nlu_result.get("symptoms", [])
    user_body_part = None
    if symptoms:
        # 最初の症状から部位情報を抽出
        first_symptom = symptoms[0]
        symptom_name = first_symptom.get("name", "")
        user_body_part = _extract_body_part_from_user_text(user_text, symptom_name)
        if user_body_part:
            nlu_result["user_body_part"] = user_body_part
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"部位情報を抽出: {user_body_part} (症状: {symptom_name})")
    
    # confidenceチェック（0.4未満の場合はGPTフォールバックを検討）
    confidence_score = nlu_result.get('confidence_score', 0.0)
    symptoms_count = len(nlu_result.get("symptoms", []))
    
    logger.info(f"NLU信頼度スコア: {confidence_score:.2f}, 検出症状数: {symptoms_count}")
    
    # ステップ1.5: 不足情報のチェック
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1.5: 不足情報のチェック ---")
    missing_info_result = check_missing_information(user_info, nlu_result, user_text, client)
    
    # 不足情報による減点を事前に計算（後で使用するため）
    from src.core.user_detection import calculate_completeness_penalty
    penalty_result = calculate_completeness_penalty(missing_info_result)
    completeness_penalty = penalty_result.get('completeness_penalty', 0.0)
    missing_fields_detail = penalty_result.get('missing_fields_detail', {})
    
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
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "missing_critical_info",
                "reason": "症状が検出されていません",
                "missing_fields": missing_info_result['missing_fields'],
                "questions": missing_info_result['questions'],
                "critical_questions": missing_info_result.get('critical_questions', []),
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": "入力されたテキストから症状を検出できませんでした。具体的な症状名（例：頭痛、発熱、のどの痛み、かゆみなど）を含めて記述してください。",
                "technical_details": f"入力テキスト: '{user_text}', 検出された症状: {symptom_names}, 信頼度スコア: {confidence_score:.2f}, 不足フィールド: {missing_fields}",
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
    
    scoring_user_info = dict(user_info)
    
    # 消化器症状と産後・授乳中の情報を追加
    try:
        from src.core.user_detection import detect_digestive_sensitivity, detect_postpartum_breastfeeding
        
        # 消化器症状の検出
        digestive_info = detect_digestive_sensitivity(user_text, nlu_result, user_info)
        if digestive_info.get("has_digestive_sensitivity", False):
            scoring_user_info['digestive_sensitivity'] = True
            logger.info(f"🔍 消化器症状検出: {digestive_info.get('reason', '')}")
        
        # 産後・授乳中の判定
        postpartum_info = detect_postpartum_breastfeeding(user_text, nlu_result, user_info)
        if postpartum_info.get("is_postpartum", False):
            scoring_user_info['postpartum'] = True
            logger.info(f"🔍 産後検出: {postpartum_info.get('reason', '')}")
        if postpartum_info.get("is_breastfeeding", False):
            scoring_user_info['breastfeeding'] = True
            logger.info(f"🔍 授乳中検出: {postpartum_info.get('reason', '')}")
    except Exception as e:
        logger.warning(f"消化器症状・産後・授乳中の検出でエラー: {e}")
    
    # user_messageを追加（痛みフラグボーナス用）
    scoring_user_info['user_message'] = user_text
    
    age_imputed = False
    if scoring_user_info.get('age') is None:
        scoring_user_info['age'] = DEFAULT_ADULT_AGE
        age_imputed = True
        # age_imputedフラグを追加（calculate_age_fit_scoreで使用）
        scoring_user_info['age_imputed'] = True

    # ステップ4: 候補医薬品取得（インフルエンザリスクを考慮）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ4: 候補医薬品取得 ---")
    candidates = get_candidate_medicines(nlu_result, medicine_df, user_text, influenza_risk)
    
    # 初期候補数を記録
    initial_candidate_count = len(candidates)
    
    # 睡眠改善薬専用の安全性チェック（候補医薬品取得後、スコアリング前）
    # 症状から医薬品種類を判定
    medicine_type = None
    symptoms = nlu_result.get("symptoms", [])
    for symptom in symptoms:
        symptom_name = symptom.get("name")
        if symptom_name in load_symptom_dictionary():
            types = load_symptom_dictionary()[symptom_name].get("medicine_types", [])
            if "睡眠障害" in types:
                medicine_type = "睡眠障害"
                break
    
    # 睡眠障害カテゴリの場合、専用の安全性チェックを実行
    if medicine_type == "睡眠障害":
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"\n--- ステップ3.5: 睡眠改善薬専用安全性チェック ---")
        sleep_safety_result = check_sleep_medicine_safety(user_text, user_info, nlu_result, medicine_type)
        
        if not sleep_safety_result["should_recommend"]:
            # 推奨を停止し、医師受診を促す
            logger.warning(f"睡眠改善薬の推奨を停止: {sleep_safety_result['escalation_reason']}")
            return {
                "status": "escalation_required",
                "reason": sleep_safety_result["escalation_reason"],
                "warnings": sleep_safety_result["warnings"],
                "recommended_medicines": [],
                "alternative_therapies": sleep_safety_result.get("alternative_therapies", []),
                "critical_questions": sleep_safety_result.get("critical_questions", []),
                "nlu_result": nlu_result,
                "influenza_risk": influenza_risk,
                "influenza_reason": influenza_reason,
                "timestamp": datetime.now().isoformat()
            }
        
        # 推奨は継続するが、警告と代替療法を保存
        if sleep_safety_result.get("warnings"):
            safety_result["warnings"].extend(sleep_safety_result["warnings"])
        # alternative_therapiesとcritical_questionsは後で使用するため、nlu_resultに保存
        nlu_result["sleep_alternative_therapies"] = sleep_safety_result.get("alternative_therapies", [])
        nlu_result["sleep_critical_questions"] = sleep_safety_result.get("critical_questions", [])
    
    if not candidates:
        logger.warning("該当する候補医薬品が見つかりませんでした")
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        return {
            "status": "no_candidates",
            "reason": "該当する医薬品が見つかりませんでした",
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "confidence_score": confidence_score,
            "error_message": f"検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して、適切な市販薬が見つかりませんでした。症状をより具体的に記述するか、医療機関を受診することをお勧めします。",
            "technical_details": f"検出症状: {symptom_names}, 医薬品の種類: {nlu_result.get('medicine_type', '不明')}, 信頼度スコア: {confidence_score:.2f}, インフルエンザリスク: {influenza_risk}",
            "timestamp": datetime.now().isoformat()
        }

    # 小児用医薬品フィルタリング（15歳以上のユーザー、または年齢不明の場合にも適用）
    user_age = scoring_user_info.get('age')
    # 年齢が15歳以上、または年齢不明の場合でも小児専用製品を除外
    # （効能に「小児の」が含まれている場合は年齢不明でも除外）
    if user_age is None or user_age >= 15:
        # 15歳以上のユーザー、または年齢不明の場合には小児専用製品を除外
        before_filter = len(candidates)
        candidates = [c for c in candidates if not _is_pediatric_specific(c)]
        after_filter = len(candidates)
        if after_filter == 0:
            logger.warning("15歳以上のユーザーのため、小児専用製品を除外した結果、候補がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "適切な医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"15歳以上のユーザーのため、小児専用製品を除外した結果、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。医療機関を受診することをお勧めします。",
                "technical_details": f"ユーザー年齢: {user_age}歳, 検出症状: {symptom_names}, フィルタ前候補数: {before_filter}, フィルタ後候補数: {after_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
        elif before_filter != after_filter:
            if user_age is None:
                logger.info(f"年齢不明のユーザーのため小児専用製品を{before_filter - after_filter}件除外しました")
            else:
                logger.info(f"15歳以上のユーザーのため小児専用製品を{before_filter - after_filter}件除外しました")
    elif age_imputed:
        # 年齢未入力の場合も従来通り除外
        before_filter = len(candidates)
        candidates = [c for c in candidates if not _is_pediatric_specific(c)]
        after_filter = len(candidates)
        if after_filter == 0:
            logger.warning("年齢未入力のため、小児専用製品を除外した結果、候補がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "年齢未入力のため適切な医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"年齢未入力のため、小児専用製品を除外した結果、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。年齢を入力するか、医療機関を受診することをお勧めします。",
                "technical_details": f"年齢: 未入力（デフォルト年齢{scoring_user_info.get('age')}歳で評価）, 検出症状: {symptom_names}, フィルタ前候補数: {before_filter}, フィルタ後候補数: {after_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
        elif before_filter != after_filter:
            logger.info(f"年齢未入力のため小児専用製品を{before_filter - after_filter}件除外しました")
    
    # 乗り物酔い薬のフィルタリング（乗り物酔いの症状がない場合は除外）
    if candidates:
        has_motion_sickness = _has_motion_sickness_symptom(nlu_result, user_text)
        before_motion_filter = len(candidates)
        
        # 二日酔いが検出されている場合は、乗り物酔い薬を強制的に除外
        user_text_lower = user_text.lower()
        hangover_keywords = ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ"]
        is_hangover_case = any(kw in user_text_lower for kw in hangover_keywords)
        
        if is_hangover_case or not has_motion_sickness:
            # 二日酔いの場合、または乗り物酔いの症状がない場合は、乗り物酔い薬を除外
            candidates = [c for c in candidates if not _is_motion_sickness_medicine(c)]
            after_motion_filter = len(candidates)
            if before_motion_filter != after_motion_filter:
                if is_hangover_case:
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔いが検出されたため、乗り物酔い薬を{before_motion_filter - after_motion_filter}件除外しました")
                else:
                    logger.info(f"乗り物酔い症状がないため、乗り物酔い薬を{before_motion_filter - after_motion_filter}件除外しました")
        else:
            logger.info("乗り物酔い症状が検出されたため、乗り物酔い薬も推奨対象に含めます")
        
        # フィルタリング後に候補がなくなった場合の処理
        if not candidates:
            logger.warning("フィルタリング後、候補医薬品がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "該当する医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"フィルタリング後、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。症状をより具体的に記述するか、医療機関を受診することをお勧めします。",
                "technical_details": f"検出症状: {symptom_names}, 乗り物酔い症状: {has_motion_sickness}, フィルタ前候補数: {before_motion_filter}, フィルタ後候補数: {after_motion_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
    
    # ステップ5: 二段階スコアリング（高速化）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5: スコアリング（二段階方式） ---")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("ステップ5: スコアリング開始")
    
    # ステップ5.1: 簡易スコアリング（高速）
    def calculate_quick_score(candidate: Dict, nlu_result: Dict, user_info: Dict) -> float:
        """簡易スコア（症状マッチ、効能特異性、年齢適合性、症状特異性ペナルティを含む）"""
        from src.core.scoring_utils import calculate_efficacy_specificity_score
        symptom_score = calculate_symptom_match_score(candidate, nlu_result)
        efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
        age_score = calculate_age_fit_score(candidate, user_info)
        
        # 主要解熱鎮痛薬のボーナス（発熱のみの場合）
        major_analgesic_bonus = 0.0
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
        is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
        
        if is_fever_only:
            product_name = candidate.get('product_name', '')
            is_major_analgesic = any(
                major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic and '解熱鎮痛薬' in candidate.get('medicine_type', ''):
                # 主要解熱鎮痛薬にボーナスを付与（quick_scoreで優先されるように）
                major_analgesic_bonus = 0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score 主要解熱鎮痛薬ボーナス: {product_name} = +{major_analgesic_bonus}")
        
        # 簡易版の症状特異性ペナルティ（複数症状時の薬効調整）
        symptom_penalty = 0.0
        symptoms = nlu_result.get("symptoms", [])
        symptom_names = [s.get("name") for s in symptoms]
        medicine_type = candidate.get("medicine_type", "")
        
        # 症状パターンマッチングによる最適化ボーナス
        pattern_bonus = 0.0
        # 単一症状の場合はpattern_bonusを適用しない（特化薬を優先するため）
        is_single_symptom_for_pattern = len(symptom_names) == 1
        if not is_single_symptom_for_pattern:
            pattern_info = match_symptom_pattern(nlu_result)
            if pattern_info:
                bonuses = pattern_info.get("bonuses", {})
                product_name = candidate.get('product_name', '')
                ingredients = str(candidate.get('ingredients', '')).lower()
                throat_specificity_level = candidate.get('throat_specificity_level', 'none')
                
                # 「のど痛み+発熱」の場合、総合感冒薬（喉向き）にボーナス
                if "のどの痛み" in symptom_names and "発熱" in symptom_names:
                    if '風邪薬' in medicine_type:
                        if throat_specificity_level == "component_and_efficacy":
                            pattern_bonus = 0.25
                        elif throat_specificity_level == "efficacy_only":
                            pattern_bonus = 0.15
                    elif '解熱鎮痛薬' in medicine_type:
                        pattern_bonus = 0.45  # 0.35から0.45に増加（2位優先のため強化）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"quick_score pattern_bonus適用: medicine_type=解熱鎮痛薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
                    elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and "のどの痛み" in symptom_names):
                        pattern_bonus = 0.45  # 0.35から0.45に増加（3位優先のため強化）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"quick_score pattern_bonus適用: medicine_type=外用薬（のど）, product_name={product_name}, pattern_bonus={pattern_bonus}")
        else:
            # pattern_infoがNoneの場合もログ出力（DEBUGレベル）
            if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_info=None: medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}, symptom_names={symptom_names}")
        
        # 単一症状（発熱のみ）の場合、解熱鎮痛薬にボーナスを付与、総合感冒薬にペナルティ
        if is_single_symptom_for_pattern and "発熱" in symptom_names:
            if '解熱鎮痛薬' in medicine_type:
                pattern_bonus = 0.3  # 単一症状（発熱のみ）の場合、解熱鎮痛薬を優先
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_bonus適用（単一症状・発熱）: medicine_type=解熱鎮痛薬, product_name={candidate.get('product_name', '')}, pattern_bonus={pattern_bonus}")
            elif '風邪薬' in medicine_type:
                pattern_bonus = -0.2  # 単一症状（発熱のみ）の場合、総合感冒薬にペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_bonus適用（単一症状・発熱）: medicine_type=風邪薬, product_name={candidate.get('product_name', '')}, pattern_bonus={pattern_bonus}")
        
        if len(symptom_names) >= 2:
            # のどの痛み + 発熱のパターン（既存ロジックは維持）
            if "のどの痛み" in symptom_names and "発熱" in symptom_names:
                if "解熱鎮痛薬" in medicine_type:
                    symptom_penalty = 0.0
                elif "風邪薬" in medicine_type:
                    symptom_penalty = 0.25
        
        # 二日酔いブーストを簡易スコアにも適用
        hangover_quick_boost = candidate.get('hangover_boost', 0.0)
        
        # 年齢適合性も含めて精度向上（重みは症状:効能:年齢 = 0.5:0.3:0.2）
        # 症状パターンボーナス、二日酔いブースト、主要解熱鎮痛薬ボーナスも追加
        quick_score_result = (symptom_score * 0.5 + efficacy_score * 0.3 + age_score * 0.2 + symptom_penalty + pattern_bonus + hangover_quick_boost + major_analgesic_bonus)
        
        # 解熱鎮痛薬と外用薬（のど）のquick_score計算の詳細をログ出力（DEBUGレベル）
        if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"quick_score計算詳細: medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}, symptom_score={symptom_score:.3f}, efficacy_score={efficacy_score:.3f}, age_score={age_score:.3f}, symptom_penalty={symptom_penalty:.3f}, pattern_bonus={pattern_bonus:.3f}, hangover_boost={hangover_quick_boost:.3f}, major_analgesic_bonus={major_analgesic_bonus:.3f}, quick_score={quick_score_result:.3f}")
        
        return quick_score_result
    
    # 簡易スコアで上位N×250件を選別（異なる薬効カテゴリの多様性確保）
    # 候補数が少ない場合は全件を詳細スコアリング（精度確保）
    selection_count = min(top_n * 250, len(candidates))
    quick_scores = [(calculate_quick_score(c, nlu_result, scoring_user_info), c) for c in candidates]
    
    # 解熱鎮痛薬と外用薬（のど）のquick_scoreをログ出力（DEBUGレベル）
    for score, candidate in quick_scores:
        medicine_type = candidate.get('medicine_type', '')
        product_name = candidate.get('product_name', '')
        if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"quick_score: {score:.3f}, medicine_type={medicine_type}, product_name={product_name}")
    
    quick_scores_sorted = sorted(quick_scores, key=lambda x: x[0], reverse=True)
    top_candidates_for_scoring = quick_scores_sorted[:selection_count]
    
    # 簡易スコアが0.3以上の場合も含める（閾値ベースの選別）
    threshold_candidates = [(score, c) for score, c in quick_scores if score >= 0.3]
    if len(threshold_candidates) > selection_count:
        # 閾値を超える候補が多い場合は、それらも含める
        top_candidates_for_scoring = sorted(threshold_candidates, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"閾値ベース選別: 簡易スコア0.3以上の候補 {len(top_candidates_for_scoring)}件を選別")
    
    # スコアリング後の候補数を記録（閾値ベース選別後）
    after_scoring_candidate_count = len(top_candidates_for_scoring)
    
    # 解熱鎮痛薬と外用薬（のど）を優先的に詳細スコアリングに含める
    # 「のど痛み+発熱」パターンの場合、解熱鎮痛薬と外用薬（のど）を確実に含める
    # 発熱のみの場合、主要解熱鎮痛薬を優先的に含める
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    has_throat_and_fever = "のどの痛み" in symptom_names and "発熱" in symptom_names
    cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
    cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
    is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
    
    # 発熱のみの場合、主要解熱鎮痛薬を優先的に含める
    if is_fever_only:
        logger.info(f"🔥 発熱のみを検出: symptom_names={symptom_names}, cold_symptom_count={cold_symptom_count}, is_fever_only={is_fever_only}")
        # 主要解熱鎮痛薬を抽出
        major_analgesic_candidates = []
        for score, candidate in quick_scores:
            product_name = candidate.get('product_name', '')
            is_major_analgesic = any(
                major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic and '解熱鎮痛薬' in candidate.get('medicine_type', ''):
                major_analgesic_candidates.append((score, candidate))
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬候補: {product_name} (score={score:.3f})")
        
        # 主要解熱鎮痛薬を優先的に含める（上位30件）
        top_major_analgesic = sorted(major_analgesic_candidates, key=lambda x: x[0], reverse=True)[:30]
        
        # 既存の候補に追加（重複を避ける）
        existing_products = {c.get('product_name', '') for _, c in top_candidates_for_scoring}
        added_count = 0
        for score, candidate in top_major_analgesic:
            if candidate.get('product_name', '') not in existing_products:
                # スコアが低くても強制的に追加（主要解熱鎮痛薬を優先）
                # スコアが0.2未満の場合は0.2に底上げして追加
                adjusted_score = max(score, 0.2)
                top_candidates_for_scoring.append((adjusted_score, candidate))
                existing_products.add(candidate.get('product_name', ''))
                added_count += 1
                logger.info(f"⭐ 主要解熱鎮痛薬を優先的に追加: {candidate.get('product_name', '')} (score={score:.3f} → {adjusted_score:.3f})")
        
        # スコア順に再ソート
        top_candidates_for_scoring = sorted(top_candidates_for_scoring, key=lambda x: x[0], reverse=True)
        logger.info(f"🔥 発熱のみの場合、主要解熱鎮痛薬を優先的に追加: {len(top_major_analgesic)}件中{added_count}件を追加")
        
        # 主要解熱鎮痛薬が既に含まれている場合もログ出力
        if added_count == 0 and len(top_major_analgesic) > 0:
            existing_major_analgesics = []
            for score, candidate in top_major_analgesic:
                if candidate.get('product_name', '') in existing_products:
                    existing_major_analgesics.append(candidate.get('product_name', ''))
            if existing_major_analgesics:
                logger.info(f"🔥 主要解熱鎮痛薬は既に候補に含まれています: {existing_major_analgesics[:5]}")
    
    if has_throat_and_fever:
        # 解熱鎮痛薬と外用薬（のど）を抽出
        analgesic_candidates = [(score, c) for score, c in quick_scores if '解熱鎮痛薬' in c.get('medicine_type', '')]
        throat_external_candidates = [(score, c) for score, c in quick_scores if '外用薬（のど）' in c.get('medicine_type', '')]
        
        # 解熱鎮痛薬と外用薬（のど）を優先的に含める（上位50件ずつ）
        top_analgesic = sorted(analgesic_candidates, key=lambda x: x[0], reverse=True)[:50]
        top_throat_external = sorted(throat_external_candidates, key=lambda x: x[0], reverse=True)[:50]
        
        # 既存の候補に追加（重複を避ける）
        existing_products = {c.get('product_name', '') for _, c in top_candidates_for_scoring}
        for score, candidate in top_analgesic + top_throat_external:
            if candidate.get('product_name', '') not in existing_products:
                top_candidates_for_scoring.append((score, candidate))
                existing_products.add(candidate.get('product_name', ''))
        
        # スコア順に再ソート
        top_candidates_for_scoring = sorted(top_candidates_for_scoring, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"解熱鎮痛薬と外用薬（のど）を優先的に追加: 解熱鎮痛薬={len(top_analgesic)}件, 外用薬（のど）={len(top_throat_external)}件")
    
    # 解熱鎮痛薬と外用薬（のど）が詳細スコアリングに進んでいるか確認（500件に絞り込む前）
    analgesic_count_before = 0
    throat_external_count_before = 0
    for score, candidate in top_candidates_for_scoring:
        medicine_type = candidate.get('medicine_type', '')
        if '解熱鎮痛薬' in medicine_type:
            analgesic_count_before += 1
        if '外用薬（のど）' in medicine_type:
            throat_external_count_before += 1
    
    # より積極的に候補を絞り込む（750件から500件に削減）
    # ただし、解熱鎮痛薬と外用薬（のど）は確実に含める
    if len(top_candidates_for_scoring) > 500:
        # 解熱鎮痛薬と外用薬（のど）を分離
        analgesic_candidates_in_top = [(score, c) for score, c in top_candidates_for_scoring if '解熱鎮痛薬' in c.get('medicine_type', '')]
        throat_external_candidates_in_top = [(score, c) for score, c in top_candidates_for_scoring if '外用薬（のど）' in c.get('medicine_type', '')]
        other_candidates = [(score, c) for score, c in top_candidates_for_scoring if '解熱鎮痛薬' not in c.get('medicine_type', '') and '外用薬（のど）' not in c.get('medicine_type', '')]
        
        # 解熱鎮痛薬と外用薬（のど）を優先的に含める（それぞれ最大50件）
        top_analgesic_included = sorted(analgesic_candidates_in_top, key=lambda x: x[0], reverse=True)[:50]
        top_throat_external_included = sorted(throat_external_candidates_in_top, key=lambda x: x[0], reverse=True)[:50]
        
        # 残りの枠を他の候補で埋める
        remaining_slots = 500 - len(top_analgesic_included) - len(top_throat_external_included)
        top_other_candidates = sorted(other_candidates, key=lambda x: x[0], reverse=True)[:remaining_slots]
        
        # 統合して再ソート
        top_candidates_for_scoring = sorted(top_analgesic_included + top_throat_external_included + top_other_candidates, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"簡易スコアリング完了: {len(candidates)}件 → 上位{len(top_candidates_for_scoring)}件を選別（500件に削減、解熱鎮痛薬={len(top_analgesic_included)}件、外用薬（のど）={len(top_throat_external_included)}件を優先的に含む）")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"簡易スコアリング完了: {len(candidates)}件 → 上位{len(top_candidates_for_scoring)}件を選別")
    
    # 解熱鎮痛薬と外用薬（のど）が詳細スコアリングに進んでいるか確認（500件に絞り込んだ後）
    analgesic_count = 0
    throat_external_count = 0
    for score, candidate in top_candidates_for_scoring:
        medicine_type = candidate.get('medicine_type', '')
        if '解熱鎮痛薬' in medicine_type:
            analgesic_count += 1
        if '外用薬（のど）' in medicine_type:
            throat_external_count += 1
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"詳細スコアリング対象: 解熱鎮痛薬={analgesic_count}件, 外用薬（のど）={throat_external_count}件（絞り込み前: 解熱鎮痛薬={analgesic_count_before}件, 外用薬（のど）={throat_external_count_before}件）")
    
    # ステップ5.2: 詳細スコアリング（選別された候補のみ）
    # サマリーログ用のデータ収集
    analgesic_scores = []
    throat_external_scores = []
    top_10_scores = []
    
    for idx, (score, candidate) in enumerate(top_candidates_for_scoring):
        score_result = calculate_final_score(candidate, nlu_result, scoring_user_info, user_text)
        candidate['final_score'] = score_result['total_score']
        candidate['raw_score'] = score_result.get('raw_score', score_result['total_score'])
        candidate['score_breakdown'] = score_result['score_breakdown']
        if 'allergy_warning' in score_result:
            candidate['allergy_warning'] = score_result['allergy_warning']
        if 'interaction_warnings' in score_result:
            candidate['interaction_warnings'] = score_result['interaction_warnings']
        
        # 上位10件のみ詳細ログ出力（本番環境ではDEBUGレベル）
        medicine_type = candidate.get('medicine_type', '')
        product_name = candidate.get('product_name', '')
        raw_score = candidate['raw_score']
        
        if idx < 10:
            score_breakdown = score_result.get('score_breakdown', {})
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"詳細スコアリング結果: medicine_type={medicine_type}, product_name={product_name}, raw_score={raw_score:.3f}, base_score={score_breakdown.get('base_score', 0.0):.3f}, adjusted_base_score={score_breakdown.get('adjusted_base_score', 0.0):.3f}, throat_bonus={score_breakdown.get('throat_bonus', 0.0):.3f}, symptom_specific_boost={score_breakdown.get('symptom_specific_boost', 0.0):.3f}, multi_symptom_bonus={score_breakdown.get('multi_symptom_bonus', 0.0):.3f}, pattern_bonus={score_breakdown.get('pattern_bonus', 0.0):.3f}, adjustment_score={score_result.get('adjustment_score', 0.0):.3f}")
        
        # サマリーログ用のデータ収集
        if '解熱鎮痛薬' in medicine_type:
            analgesic_scores.append((product_name, raw_score))
        if '外用薬（のど）' in medicine_type:
            throat_external_scores.append((product_name, raw_score))
        if idx < 10:
            top_10_scores.append((product_name, medicine_type, raw_score))
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"{product_name}: raw={raw_score:.3f}, final={candidate['final_score']:.3f}")
    
    # サマリーログ出力
    if analgesic_scores:
        max_analgesic = max(analgesic_scores, key=lambda x: x[1])
        avg_analgesic = sum(s[1] for s in analgesic_scores) / len(analgesic_scores)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"解熱鎮痛薬スコアリングサマリー: {len(analgesic_scores)}件, 最高スコア={max_analgesic[1]:.3f} ({max_analgesic[0]}), 平均スコア={avg_analgesic:.3f}")
    
    if throat_external_scores:
        max_throat = max(throat_external_scores, key=lambda x: x[1])
        avg_throat = sum(s[1] for s in throat_external_scores) / len(throat_external_scores)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"外用薬（のど）スコアリングサマリー: {len(throat_external_scores)}件, 最高スコア={max_throat[1]:.3f} ({max_throat[0]}), 平均スコア={avg_throat:.3f}")
    
    if top_10_scores:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"詳細スコアリング上位10件: {', '.join([f'{s[0]}({s[2]:.3f})' for s in top_10_scores[:5]])}...")
    
    # ステップ5.2.5: 閾値判定のセーフティガード（減点適用前のraw_scoreで判定）
    # raw_score < 0.3の候補を除外（現在の完璧な薬が除外されないよう保護）
    # ただし、主要解熱鎮痛薬は優先的に含める（発熱のみの場合）
    threshold = 0.3
    excluded_candidates = []
    valid_candidates_for_scoring = []
    
    # 発熱のみの場合、主要解熱鎮痛薬を優先的に含める
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
    cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
    is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
    
    for score, candidate in top_candidates_for_scoring:
        raw_score = candidate.get('raw_score', 0.0)
        product_name = candidate.get('product_name', '')
        
        # 発熱のみの場合、主要解熱鎮痛薬は優先的に含める（閾値を下回っていても）
        is_major_analgesic = any(
            major_name in product_name for major_name in MAJOR_ANALGESIC_MEDICINES
        )
        if is_fever_only and is_major_analgesic and raw_score >= 0.2:  # 閾値を0.2に緩和
            valid_candidates_for_scoring.append((score, candidate))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬を優先的に含める: {product_name} raw_score={raw_score:.3f} (閾値緩和)")
        elif raw_score < threshold:
            excluded_candidates.append(candidate)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"閾値以下で除外: {product_name} raw_score={raw_score:.3f} < {threshold}")
        else:
            valid_candidates_for_scoring.append((score, candidate))
    
    if excluded_candidates:
        logger.info(f"閾値判定: {len(excluded_candidates)}件の候補を除外（raw_score < {threshold}）、残り{len(valid_candidates_for_scoring)}件")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"除外された候補: {[c.get('product_name', '') for c in excluded_candidates[:5]]}...")
    
    # 有効な候補のみを使用
    top_candidates_for_scoring = valid_candidates_for_scoring
    
    # ステップ5.2.5.5: raw_scoreで順序を確定し、original_rankを保存（ランキング保護）
    # 正規化前のraw_scoreでソートし、順序を確定
    candidates_with_scores = [(c.get('raw_score', 0.0), c) for _, c in top_candidates_for_scoring]
    candidates_with_scores_sorted = sorted(candidates_with_scores, key=lambda x: x[0], reverse=True)
    
    # 各候補にoriginal_rankを保存（raw_scoreでの順位）
    for rank, (raw_score, candidate) in enumerate(candidates_with_scores_sorted, 1):
        candidate['original_rank'] = rank
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"original_rank保存: rank={rank}, product_name={candidate.get('product_name', '')}, raw_score={raw_score:.3f}")
    
    # 元の形式に戻す（タプルのリスト）
    top_candidates_for_scoring = [(score, candidate) for score, candidate in candidates_with_scores_sorted]
    
    # ステップ5.2.6: 正規化プロセスを簡素化（絶対評価ベースのため、raw_scoreをそのまま保持）
    # Min-Max正規化、重み付き線形変換、底上げロジックを削除
    # raw_scoreをそのままfinal_scoreとして使用（絶対評価ベース）
    for _, candidate in top_candidates_for_scoring:
        raw_score = candidate.get('raw_score', 0.0)
        score_breakdown = candidate.get('score_breakdown', {})
        hangover_boost = score_breakdown.get('hangover_boost', 0.0)
        is_hangover_medicine = candidate.get('is_hangover', False)
        
        # 二日酔い医薬品の場合、閾値を下げる
        min_threshold = 0.3 if (hangover_boost > 0 or is_hangover_medicine) else 0.5
        
        # 閾値以下のスコアは0.0にマッピング
        if raw_score <= min_threshold:
            # 二日酔い医薬品で0.2以上の場合は、最低限のスコアを与える
            if (hangover_boost > 0 or is_hangover_medicine) and raw_score >= 0.2:
                final_score = 0.4  # 最低限の推奨可能スコア
            else:
                final_score = 0.0
        else:
            # raw_scoreをそのままfinal_scoreとして使用（絶対評価ベース）
            final_score = raw_score
        
        candidate['final_score'] = final_score
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"正規化簡素化: product_name={candidate.get('product_name', '')}, raw_score={raw_score:.3f} → final_score={final_score:.3f}")
    
    # ステップ5.3: 詳細スコアリング（選別された候補のみ）
    # 正規化後、original_rankに基づいて順序を復元（ランキング保護）
    candidates_list = [c for _, c in top_candidates_for_scoring]
    candidates_sorted = sorted(candidates_list, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"正規化後、original_rankに基づいて順序を復元: {len(candidates_sorted)}件")
    
    # スコア差が僅差（0.1以内）の場合、指定第2類医薬品を優先するソートロジック（乗り物酔い薬の場合）
    symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
    if len(candidates_sorted) >= 2 and "乗り物酔い" in symptom_names:
        # 上位2件のスコア差を確認
        top_score = candidates_sorted[0].get('final_score', 0.0)
        second_score = candidates_sorted[1].get('final_score', 0.0)
        score_diff = top_score - second_score
        
        # スコア差が0.1以内の場合、指定第2類を優先
        if score_diff <= 0.1:
            top_classification = str(candidates_sorted[0].get('classification', '')).lower()
            second_classification = str(candidates_sorted[1].get('classification', '')).lower()
            
            # 2位が指定第2類で、1位が指定第2類でない場合、入れ替え
            if '指定第2類' in second_classification and '指定第2類' not in top_classification:
                candidates_sorted[0], candidates_sorted[1] = candidates_sorted[1], candidates_sorted[0]
                # original_rankを更新（ランキング保護のため）
                candidates_sorted[0]['original_rank'], candidates_sorted[1]['original_rank'] = candidates_sorted[1]['original_rank'], candidates_sorted[0]['original_rank']
                logger.info(f"スコア差が僅差（{score_diff:.3f}）のため、指定第2類医薬品を優先しました（original_rankを更新）")
    
    # 肩こり・筋肉痛の場合、最適解の外用薬（フェイタス、バンテリン、サロンパス）を優先するソートロジック
    has_musculoskeletal_symptom = any(s in symptom_names for s in ["肩こり", "筋肉痛", "関節痛", "腰痛"])
    if has_musculoskeletal_symptom and len(candidates_sorted) >= 2:
        optimal_keywords = ["フェイタス", "バンテリン", "サロンパス"]
        
        # 最適解の製品を探す
        optimal_indices = []
        for i, candidate in enumerate(candidates_sorted):
            product_name = str(candidate.get('product_name', '')).lower()
            if any(kw.lower() in product_name for kw in optimal_keywords):
                optimal_indices.append(i)
        
        # 最適解が見つかり、1位でない場合、優先的に上位に移動
        if optimal_indices:
            for idx in optimal_indices:
                if idx > 0:  # 1位でない場合
                    # スコア差が0.2以内の場合、最適解を優先
                    optimal_score = candidates_sorted[idx].get('final_score', 0.0)
                    top_score = candidates_sorted[0].get('final_score', 0.0)
                    score_diff = top_score - optimal_score
                    
                    if score_diff <= 0.2:
                        # 最適解を1位に移動
                        optimal_candidate = candidates_sorted.pop(idx)
                        candidates_sorted.insert(0, optimal_candidate)
                        # original_rankを更新（ランキング保護のため）
                        # 1位からidx位までのoriginal_rankをシフト
                        for i in range(idx):
                            candidates_sorted[i + 1]['original_rank'] = i + 2
                        candidates_sorted[0]['original_rank'] = 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"肩こり外用薬の最適解を優先しました: {optimal_candidate.get('product_name')} (スコア差: {score_diff:.3f}, original_rankを更新)")
                        break
    
    top_candidates = ensure_ingredient_diversity(candidates_sorted, top_n=top_n, nlu_result=nlu_result, user_info=user_info)
    
    # フィルタリング後の候補数を記録
    after_filtering_candidate_count = len(top_candidates)
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(
            f"詳細スコアリング完了: {len(top_candidates_for_scoring)}件 → 上位{len(top_candidates)}件を選択（成分多様性考慮）"
        )
    
    # 最終推奨結果をログ出力（解熱鎮痛薬と外用薬（のど）の確認用、DEBUGレベル）
    for i, candidate in enumerate(top_candidates, 1):
        medicine_type = candidate.get('medicine_type', '')
        product_name = candidate.get('product_name', '')
        final_score = candidate.get('final_score', 0.0)
        raw_score = candidate.get('raw_score', 0.0)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"最終推奨結果 rank{i}: medicine_type={medicine_type}, product_name={product_name}, final_score={final_score:.3f}, raw_score={raw_score:.3f}")
    
    # ステップ5.3.5: 不足情報による減点情報の保存（絶対評価ベースのため、final_scoreには適用しない）
    # 減点はdisplay_score計算時に適用されるため、ここでは情報のみを保存
    if completeness_penalty > 0:
        logger.info(f"不足情報による減点情報を保存: penalty={completeness_penalty:.3f}, missing_fields={list(missing_fields_detail.keys())}")
        
        # 減点適用前のraw_scoreをログ出力（INFOレベルで出力）
        for i, candidate in enumerate(top_candidates[:3], 1):
            logger.info(f"減点適用前 rank{i}: {candidate.get('product_name', '')} final_score={candidate.get('final_score', 0.0):.3f}, raw_score={candidate.get('raw_score', 0.0):.3f}")
        
        # score_breakdownに減点情報を追加（final_scoreには影響しない）
        for candidate in top_candidates:
            if 'score_breakdown' not in candidate:
                candidate['score_breakdown'] = {}
            candidate['score_breakdown']['completeness_penalty'] = -completeness_penalty
            candidate['score_breakdown']['missing_fields_detail'] = missing_fields_detail
            
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"減点情報を保存: {candidate.get('product_name', '')} penalty={completeness_penalty:.3f} (final_scoreには適用しない)")
    
    # ステップ5.3.6: MaxPossibleScore計算（絶対評価ベースのため、MaxPossibleScore情報のみ保存）
    # 絶対評価ベースのため、MaxPossibleScore正規化は不要
    MaxPossibleScore = 1.0 - completeness_penalty  # 最大-0.15でキャップ済み
    for candidate in top_candidates:
        candidate['max_possible_score'] = MaxPossibleScore
    
    # ステップ5.4: 相対スコア化（最高スコアを100%として正規化）
    # ensure_ingredient_diversity実行後、relative_scoreを再計算
    # 注意: ensure_ingredient_diversityが順序を変更する可能性があるため、
    # 実際の最高スコアを取得してから相対スコアを計算する
    if top_candidates:
        # 実際の最高スコアを取得（順序に関係なく）
        max_score = max(candidate.get('final_score', 0.0) for candidate in top_candidates)
        if max_score > 0:
            for candidate in top_candidates:
                final_score = candidate.get('final_score', 0.0)
                # final_scoreが0.0の場合はrelative_scoreも0.0に設定
                if final_score <= 0.0:
                    candidate['relative_score'] = 0.0
                    candidate['score_level'] = '低'
                else:
                    relative_score = final_score / max_score
                    # 1.0を超えないようにクリップ
                    relative_score = min(1.0, relative_score)
                    candidate['relative_score'] = relative_score
                    
                    # スコアレベルの再定義（情報網羅率を考慮）
                    # Criticalな不足情報があるかチェック
                    has_critical_missing = False
                    if missing_info_result.get("has_missing_info", False):
                        critical_fields = ["age", "allergies", "pregnancy_status"]
                        missing_fields = missing_info_result.get("missing_fields", [])
                        has_critical_missing = any(field in missing_fields for field in critical_fields)
                    
                    # 新しいスコアレベル判定（計画7.1に従う）
                    if relative_score >= 0.8 and not has_critical_missing:
                        candidate['score_level'] = '高'  # 高（S）: 80%以上 + Criticalな不足情報なし
                    elif relative_score >= 0.6:
                        candidate['score_level'] = '中'  # 中（A）: 60%以上
                    elif relative_score < 0.4:
                        candidate['score_level'] = '低'  # 低（B）: 40%未満 または 閾値ギリギリ
                    else:
                        # 0.4 <= relative_score < 0.6 の場合は中（A）として扱う
                        candidate['score_level'] = '中'
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"相対スコア: {candidate.get('product_name', '')} = {candidate.get('relative_score', 0.0):.3f} ({candidate.get('score_level', '')})")
        
        # 相対スコア計算後、original_rankに基づいて順序を復元（ランキング保護）
        top_candidates = sorted(top_candidates, key=lambda x: x.get('original_rank', 9999))
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"相対スコア計算後、original_rankに基づいて順序を復元: {len(top_candidates)}件")
        
        # ステップ5.4.5: 絶対評価ベースの表示用スコア計算
        if len(top_candidates) >= 1:
            # 各候補に対してdisplay_scoreを計算（絶対評価ベース）
            for rank, candidate in enumerate(top_candidates[:3], 1):
                raw_score = candidate.get('raw_score', 0.0)
                
                # 絶対評価ベースのdisplay_scoreを計算
                display_score = calculate_display_score_absolute(rank, raw_score, completeness_penalty)
                candidate['display_score'] = display_score
                
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"表示用スコア（絶対評価ベース）: rank={rank}, {candidate.get('product_name', '')} = {display_score:.1f}% (raw_score={raw_score:.3f}, penalty={completeness_penalty:.3f})")
    
    # ステップ5.5: 推奨後の検証処理
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5.5: 推奨後の検証処理 ---")
    
    # 減点適用後、final_scoreが0になった候補も保持（ランキング保護のため）
    # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
    validated_candidates = _finalize_recommendations(top_candidates, nlu_result, influenza_risk)
    
    # 減点適用後、final_scoreが0になった候補も保持（最低3件推奨するため）
    # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
    if len(validated_candidates) < top_n:
        # 減点適用後、final_scoreが0になった候補も追加
        excluded_by_validation = [c for c in top_candidates if c not in validated_candidates]
        # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
        for candidate in excluded_by_validation:
            if candidate.get('raw_score', 0.0) >= 0.3:  # 減点適用前のraw_scoreで閾値判定済み
                validated_candidates.append(candidate)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"減点適用後も候補を保持: {candidate.get('product_name', '')} (raw_score={candidate.get('raw_score', 0.0):.3f}, final_score={candidate.get('final_score', 0.0):.3f})")
    
    # 推奨医薬品が3件未満の場合、スコアが低い候補も含める（最低3件推奨するため）
    if len(validated_candidates) < top_n and len(top_candidates) > len(validated_candidates):
        # 除外された候補から、減点適用前のraw_score >= 0.3の候補を追加
        # 減点適用後、final_scoreが0になっても、減点適用前のraw_scoreで閾値判定済みのため保持
        excluded_candidates = [c for c in top_candidates if c not in validated_candidates]
        excluded_candidates = [c for c in excluded_candidates if c.get('raw_score', 0.0) >= 0.3]
        
        # original_rankに基づいてソート（ランキング保護）
        excluded_candidates = sorted(excluded_candidates, key=lambda x: x.get('original_rank', 9999))
        
        # 不足分を追加
        needed_count = top_n - len(validated_candidates)
        for candidate in excluded_candidates[:needed_count]:
            # 低スコア警告を追加
            candidate['low_score_warning'] = True
            validated_candidates.append(candidate)
            logger.info(f"⚠️ 推奨医薬品が{top_n}件未満のため、低スコア候補を追加: {candidate.get('product_name', '')} (スコア: {candidate.get('final_score', 0.0):.3f})")
        
        # original_rankに基づいて順序を復元（ランキング保護）
        validated_candidates = sorted(validated_candidates, key=lambda x: x.get('original_rank', 9999))
    
    # 最終的な順序復元（すべての処理後、original_rankに基づいて順序を復元）
    validated_candidates = sorted(validated_candidates, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"最終的な順序復元: original_rankに基づいて順序を復元: {len(validated_candidates)}件")
    
    # ステップ6: 説明生成
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ6: 説明生成 ---")
    recommendations = []
    for i, candidate in enumerate(validated_candidates, 1):
        explanation = generate_explanation(candidate, nlu_result, safety_result, scoring_user_info)
        
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
            "relative_score": candidate.get('relative_score', candidate['final_score']),  # 相対スコア（最高スコアを1.0として正規化）
            "display_score": candidate.get('display_score'),  # 表示用スコア（小数点第1位、絶対評価ベース）
            "score_level": candidate.get('score_level', '中'),  # スコア帯（高/中/低）
            "score_breakdown": candidate.get('score_breakdown', {}),
            "explanation": explanation,
            "reason": explanation,  # ChatGPTベース互換性のため追加
            "allergy_warning": candidate.get('allergy_warning', ''),
            "interaction_warnings": candidate.get('interaction_warnings', []),
            "completeness_penalty": completeness_penalty,  # 不足情報による減点
            "max_possible_score": candidate.get('max_possible_score', 1.0),  # MaxPossibleScore
            "raw_score": candidate.get('raw_score'),  # 管理者向け: raw_score（絶対評価ベースの計算元）
            "original_rank": candidate.get('original_rank', i)  # 管理者向け: original_rank（ランキング保護用）
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
        recommendations, nlu_result, scoring_user_info, client
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
    
    # 代替療法の取得（睡眠改善薬の場合）
    alternative_therapies = nlu_result.get("sleep_alternative_therapies", [])
    sleep_critical_questions = nlu_result.get("sleep_critical_questions", [])
    
    # critical_questionsに睡眠改善薬の質問を追加
    all_critical_questions = missing_info_result.get("critical_questions", [])
    if sleep_critical_questions:
        all_critical_questions.extend(sleep_critical_questions)
    
    return {
        "status": "success",
        "recommended_medicines": recommendations,
        "warnings": safety_result["warnings"],
        "usage_notes": usage_and_consultation.get('usage_notes', ''),
        "doctor_consultation": usage_and_consultation.get('doctor_consultation', ''),
        "additional_questions": additional_questions,
        "critical_questions": all_critical_questions,  # 睡眠改善薬の質問も含める
        "missing_priority": missing_priority,
        "alternative_therapies": alternative_therapies,  # 代替療法（睡眠改善薬の場合）
        "nlu_result": nlu_result,
        "influenza_risk": influenza_risk,  # 新規追加
        "influenza_reason": influenza_reason,  # 新規追加
        "confidence_score": confidence_score,  # confidence_scoreを追加
        "score_breakdown_json": score_breakdown_json,  # デバッグ用JSON出力
        "completeness_penalty": completeness_penalty,  # 不足情報による減点
        "max_possible_score": MaxPossibleScore,  # MaxPossibleScore
        "candidate_counts": {
            "initial": initial_candidate_count,
            "after_scoring": after_scoring_candidate_count,
            "after_filtering": after_filtering_candidate_count
        },
        "timestamp": datetime.now().isoformat()
    }

# generate_explanation は explanation_generator から import（SRP改善）

# ================================================================================
# 6. ChatGPTによる使用上の注意と医師相談アドバイス（explanation_generator から import）
# ================================================================================

# ================================================================================
# 7. ロギング（recommendation_logger からインポート）
# ================================================================================

from src.services.recommendation_logger import log_recommendation_session

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
    medicine_df = pd.read_csv(CSV_PATH)
    
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
