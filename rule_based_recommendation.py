"""
ルールベース医薬品推奨システム

ChatGPT APIはNLU（症状抽出）のみに使用し、
医薬品推奨は登録販売者の判断を再現するルールベース/スコアリング型アルゴリズムで実装
"""

import pandas as pd
import os
import json
import re
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from scoring_utils import normalize_text

# ロガー設定
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

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

# ================================================================================
# 1. データ構造と定数定義
# ================================================================================

# 成分辞書（月経不順に効く成分）
INGREDIENT_DICTIONARY = {
    "当帰": {
        "canonical_name": "当帰",
        "synonyms": ["トウキ", "当帰", "とうき", "トウキ末", "トウキ流エキス", "トウキエキス", "トウキ乾燥エキス", "トウキ流エキスＳ", "トウキエキスＳ", "当帰末"],
        "effects": ["血行改善", "冷え性改善", "生理痛緩和", "体力回復"],
        "related_symptoms": ["月経不順", "生理痛", "冷え性"],
        "medicine_types": ["解熱鎮痛薬", "漢方薬"]
    },
    "芍薬": {
        "canonical_name": "芍薬",
        "synonyms": ["シャクヤク", "芍薬", "しゃくやく", "シャクヤク末", "シャクヤクエキス", "シャクヤク乾燥エキス", "芍薬エキス"],
        "effects": ["痛み緩和", "筋肉緊張緩和", "不安緩和"],
        "related_symptoms": ["月経不順", "生理痛", "イライラ"],
        "medicine_types": ["解熱鎮痛薬", "漢方薬"]
    },
    "当帰芍薬散": {
        "canonical_name": "当帰芍薬散",
        "synonyms": ["トウキシャクヤクサン", "当帰芍薬散", "とうきしゃくやくさん"],
        "effects": ["血行改善", "生理痛緩和", "月経不順改善", "冷え性改善"],
        "related_symptoms": ["月経不順", "生理痛", "冷え性"],
        "medicine_types": ["漢方薬"]
    }
}

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
    "月経不順": {
        "canonical_name": "月経不順",
        "synonyms": ["月経不順", "生理不順", "月経異常", "生理周期が乱れている", "生理が遅れている", "月経が遅れている", "生理が来ていない", "月経が来ない", "生理が来ない", "血の道症", "生理異常"],
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
    "つわり": {
        "canonical_name": "つわり",
        "synonyms": ["つわり", "悪阻", "吐き気", "嘔吐", "匂いに敏感", "匂いが気になる"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.9
    },
    "胸の張り": {
        "canonical_name": "胸の張り",
        "synonyms": ["胸が張る", "胸の張り", "乳房の張り", "胸が痛い", "胸が敏感", "乳房が痛い"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],
        "weight": 0.8
    },
    "頻尿": {
        "canonical_name": "頻尿",
        "synonyms": ["頻尿", "トイレが近い", "おしっこが近い", "尿が近い", "トイレに行く回数が多い"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["胃腸薬"],
        "weight": 0.8
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
    "乗り物酔い": {
        "canonical_name": "乗り物酔い",
        "synonyms": ["乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う", "車に乗ると気持ち悪い", "船に乗ると気持ち悪い", "乗物酔い", "乗物に酔う"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],  # データベース上では解熱鎮痛薬カテゴリに分類されている
        "weight": 0.95
    },
    "疲労感": {
        "canonical_name": "疲労感",
        "synonyms": ["疲労感", "疲れ", "だるい", "倦怠感"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状"],
        "weight": 0.7
    },
    "だるさ": {
        "canonical_name": "だるさ",
        "synonyms": ["だるさ", "だるい", "体がだるい", "全身倦怠感", "倦怠感"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["精神症状", "胃腸薬", "抗アレルギー薬"],
        "weight": 0.7
    },
    "むくみ": {
        "canonical_name": "むくみ",
        "synonyms": ["むくみ", "浮腫", "腫れぼったい", "パンパン", "顔のむくみ", "足のむくみ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["抗アレルギー薬", "胃腸薬"],
        "weight": 0.75
    },
    "二日酔い": {
        "canonical_name": "二日酔い",
        "synonyms": ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["抗アレルギー薬", "胃腸薬", "解熱鎮痛薬"],
        "weight": 0.95
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
    "胸痛": ["胸が痛い", "胸の痛み", "胸部痛", "胸が締め付けられる"],
    # 新規追加: 心臓関連の緊急症状（安全弁強化版）
    "心臓の痛み": [
        "心臓が痛い", "心臓部分が痛い", "心臓が痛む", 
        "心臓部が痛い", "心臓のあたりが痛い", "心臓付近が痛い"
    ],
    # 新規追加: 動悸・不整脈関連の緊急症状
    "動悸・不整脈": [
        "動悸", "動悸が止まらない", "ドキドキが止まらない",
        "脈が飛ぶ", "不整脈", "脈が速い", "脈が遅い", "脈が不規則"
    ],
    # 注意: 「心が痛い」は含めない（心理的症状の可能性があるため）
    # 注意: 「胸が苦しい」「胸の圧迫感」は循環器系の可能性もあるが、
    #       精神的な場合も多いため、LLMトリアージに任せる
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
# 妊娠の可能性を示す症状辞書
PREGNANCY_SYMPTOMS = {
    "生理の遅れ": {
        "weight": 3.0,  # 最高重み
        "synonyms": [
            "生理が遅れている", "月経が来ない", "生理が来ない", 
            "予定日を過ぎた", "いつもより遅い", "生理が遅い",
            "月経遅延", "生理が来ていない",
            "月経が遅れている", "生理予定日を過ぎた"
            # 注意: "生理不順", "月経不順"は除外（妊娠以外の原因も多いため）
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
        "weight": 0.5,  # 他の症状と組み合わせて判定
        "synonyms": ["便秘", "便が出ない", "便通がない"]
    },
    "微熱": {
        "weight": 0.5,  # 他の症状と組み合わせて判定
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

# 特殊用途医薬品の除外キーワード（一般的な症状には不適切な特殊用途医薬品）
SPECIFIC_USE_EXCLUSION_KEYWORDS = {
    "ホルモン": ["ホルモン", "テストステロン", "エストロゲン", "プロゲステロン", "メチルテストステロン"],
    "男性器": ["男性器", "ペニス", "陰茎", "性器", "オットピン", "内股"],
    "女性器": ["女性器", "膣", "おりもの", "デリケートゾーン"],
    "特殊用途": ["勃起", "性機能", "更年期障害", "ホルモン補充", "記憶力減退"]
}

def is_specific_use_medicine(candidate: Dict) -> bool:
    """
    特殊用途医薬品かどうかを判定
    ホルモン剤、男性器塗布剤などの特殊用途医薬品を検出
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        特殊用途医薬品の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    
    combined_text = product_name + efficacy + usage + ingredients
    
    for category, keywords in SPECIFIC_USE_EXCLUSION_KEYWORDS.items():
        if any(kw in combined_text for kw in keywords):
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"特殊用途医薬品を検出: {candidate.get('product_name', '')} (カテゴリ: {category})")
            return True
    
    return False

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
        "風邪薬": -0.3,  # 単一症状の場合は複合薬にペナルティ
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
        "priority_order": ["加味逍遙散", "命の母ホワイト", "ラムールQ"],
        "bonuses": {
            "加味逍遙散": 0.20,  # 0.15から0.20に増加
            "命の母ホワイト": 0.20,  # 0.15から0.20に増加
            "ラムールQ": 0.18,  # 新規追加
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
        "priority_order": ["桂枝茯苓丸"],
        "bonuses": {
            "桂枝茯苓丸": 0.15,
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

# NLUキャッシュ（セッション間でも共有可能なキャッシュ）
_nlu_cache = {}
_max_cache_size = 100  # 50から100に拡張（セッション間共有のため）

# 医薬品タイプ判定キャッシュ
_medicine_type_cache = {}
_max_medicine_type_cache_size = 50

# 翻訳キャッシュ
_translation_cache = {}
_max_translation_cache_size = 200

# 症状パターンマッチングキャッシュ
_symptom_pattern_cache = {}
_max_symptom_pattern_cache_size = 200

# 成分抽出キャッシュ
_ingredient_extraction_cache = {}
_max_ingredient_extraction_cache_size = 500

def get_cached_nlu_result(user_text: str, session_id: str = None) -> Optional[Dict]:
    """
    NLUキャッシュから結果を取得（セッション間でも共有可能）
    
    Args:
        user_text: ユーザーの症状入力
        session_id: セッションID（オプション、セッション間共有のため必須ではない）
    
    Returns:
        キャッシュされたNLU結果、またはNone
    """
    # セッションIDがなくても、テキストのハッシュで検索可能
    text_hash = hash(user_text)
    
    # セッションIDがある場合はセッション固有のキーを優先
    if session_id:
        cache_key = f"{session_id}:{text_hash}"
        if cache_key in _nlu_cache:
            return _nlu_cache[cache_key]
    
    # セッション間共有キャッシュを検索（テキストハッシュのみで検索）
    for key, value in _nlu_cache.items():
        if key.endswith(f":{text_hash}"):
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"NLUキャッシュヒット（セッション間共有）: {key}")
            return value
    
    return None

def set_cached_nlu_result(user_text: str, nlu_result: Dict, session_id: str = None):
    """
    NLUキャッシュに結果を保存（セッション間でも共有可能）
    
    Args:
        user_text: ユーザーの症状入力
        nlu_result: NLU結果
        session_id: セッションID（オプション）
    """
    text_hash = hash(user_text)
    
    # キャッシュサイズ制限
    if len(_nlu_cache) >= _max_cache_size:
        # 古いエントリを削除（FIFO）
        oldest_key = next(iter(_nlu_cache))
        del _nlu_cache[oldest_key]
    
    # セッションIDがある場合はセッション固有のキーを使用
    if session_id:
        cache_key = f"{session_id}:{text_hash}"
    else:
        # セッションIDがない場合はテキストハッシュのみを使用（セッション間共有）
        cache_key = f"shared:{text_hash}"
    
    _nlu_cache[cache_key] = nlu_result
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"NLUキャッシュに保存: {cache_key}")

def clear_nlu_cache():
    """NLUキャッシュをクリア"""
    global _nlu_cache
    _nlu_cache.clear()
    logger.info("NLUキャッシュをクリアしました")

def get_cached_medicine_type(user_text: str) -> Optional[str]:
    """
    医薬品タイプ判定キャッシュから結果を取得
    
    Args:
        user_text: ユーザーの症状入力
    
    Returns:
        キャッシュされた医薬品タイプ、またはNone
    """
    text_hash = hash(user_text)
    return _medicine_type_cache.get(text_hash)

def set_cached_medicine_type(user_text: str, medicine_type: str):
    """
    医薬品タイプ判定キャッシュに結果を保存
    
    Args:
        user_text: ユーザーの症状入力
        medicine_type: 医薬品タイプ
    """
    global _medicine_type_cache
    
    # キャッシュサイズ制限
    if len(_medicine_type_cache) >= _max_medicine_type_cache_size:
        # 古いエントリを削除（FIFO）
        oldest_key = next(iter(_medicine_type_cache))
        del _medicine_type_cache[oldest_key]
    
    text_hash = hash(user_text)
    _medicine_type_cache[text_hash] = medicine_type
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"医薬品タイプキャッシュに保存: {medicine_type}")

def get_cached_translation(text: str, target_language: str) -> Optional[str]:
    """
    翻訳キャッシュから結果を取得
    
    Args:
        text: 翻訳対象テキスト
        target_language: 翻訳先言語
    
    Returns:
        キャッシュされた翻訳結果、またはNone
    """
    cache_key = f"{target_language}:{hash(text)}"
    return _translation_cache.get(cache_key)

def set_cached_translation(text: str, target_language: str, translated_text: str):
    """
    翻訳キャッシュに結果を保存
    
    Args:
        text: 翻訳対象テキスト
        target_language: 翻訳先言語
        translated_text: 翻訳結果
    """
    global _translation_cache
    
    # キャッシュサイズ制限
    if len(_translation_cache) >= _max_translation_cache_size:
        # 古いエントリを削除（FIFO）
        oldest_key = next(iter(_translation_cache))
        del _translation_cache[oldest_key]
    
    cache_key = f"{target_language}:{hash(text)}"
    _translation_cache[cache_key] = translated_text
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"翻訳キャッシュに保存: {cache_key[:50]}...")

def simple_pattern_matching_nlu(user_text: str, user_info: Dict) -> Dict:
    """
    強化されたルールベースNLU（正規表現、重症度推定、期間抽出）
    """
    import re
    
    text_lower = user_text.lower()
    detected_symptoms = []
    red_flags = []
    
    # 重症度修飾語のパターン（拡張版・改善）
    severity_patterns = {
        "重度": [
            r"激しい", r"ひどい", r"重い", r"酷い", r"深刻", r"重症", r"強烈", r"猛烈",
            r"耐えられない", r"我慢できない", r"今までにない", r"異常に", r"非常に",
            r"緊急", r"救急", r"命に関わる", r"危険", r"危篤", r"重症化"
        ],
        "軽度": [
            r"少し", r"軽い", r"軽微", r"微か", r"弱い", r"軽度", r"軽い",
            r"ちょっと", r"やや", r"わずか", r"軽く", r"微か", r"軽微",
            r"始まったばかり", r"初期", r"初期の", r"初期段階", r"初期症状",
            r"軽く", r"軽め", r"軽症", r"軽い症状", r"軽い痛み", r"軽い熱"
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
    
    # 症状辞書から同義語でマッチング（強化版・活用形対応）
    for symptom_name, symptom_data in SYMPTOM_DICTIONARY.items():
        matched = False
        
        # 正規化名でチェック
        canonical = symptom_data["canonical_name"]
        if canonical in user_text:
            matched = True
        
        # 同義語でチェック（完全一致）
        if not matched:
            for synonym in symptom_data["synonyms"]:
                if synonym in user_text:
                    matched = True
                    break
        
        # 部分一致チェック（活用形対応）
        if not matched:
            # canonical_nameの語幹でチェック（例: "のどの痛み" → "のど", "痛"）
            if "痛み" in canonical or "痛い" in canonical:
                # "痛" を含むか確認（"痛い", "痛く", "痛む" などに対応）
                base_symptom = canonical.replace("の痛み", "").replace("痛み", "").replace("が痛い", "")
                if base_symptom and base_symptom in user_text and "痛" in user_text:
                    matched = True
            
            # 同義語も活用形チェック
            if not matched:
                for synonym in symptom_data["synonyms"]:
                    if "痛い" in synonym:
                        # "○○が痛い" → "○○が痛" で部分一致チェック
                        base_syn = synonym.replace("が痛い", "").replace("痛い", "")
                        if base_syn and base_syn in user_text and "痛" in user_text:
                            matched = True
                            break
        
        if matched:
            detected_symptoms.append({
                "name": symptom_name,
                "severity": "中等度",  # デフォルト
                "duration_days": None
            })
    
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
    
    # 症状の信頼度を計算（最適化版）
    confidence_score = 0.0
    if detected_symptoms:
        # 1. 症状数による信頼度（基本スコア）
        confidence_score += min(len(detected_symptoms) * 0.3, 0.6)
        
        # 2. 重症度の明確性による信頼度（改善：中等度でも軽微な加点）
        severity_specificity = sum(1 for s in detected_symptoms if s["severity"] != "中等度")
        confidence_score += severity_specificity * 0.1
        # 中等度でも症状が検出されたこと自体に軽微な加点
        if severity_specificity == 0 and len(detected_symptoms) > 0:
            confidence_score += 0.05
        
        # 3. 期間の明確性による信頼度
        if duration_days is not None:
            confidence_score += 0.2
        
        # 4. 症状組み合わせによる信頼度向上
        confidence_score += combination_boost
        
        # 5. 部位情報の明確性による信頼度向上（新規追加）
        # 部位情報を抽出（症状名を使用）
        first_symptom_name = detected_symptoms[0].get("name", "") if detected_symptoms else ""
        body_part = _extract_body_part_from_user_text(user_text, first_symptom_name)
        if body_part:
            confidence_score += 0.1
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"部位情報検出による信頼度向上: {body_part}")
        
        # 6. 症状名の明確性による信頼度向上（新規追加）
        # SYMPTOM_DICTIONARYに完全一致する症状がある場合
        symptom_dict_matches = 0
        for symptom in detected_symptoms:
            symptom_name = symptom.get("name", "")
            if symptom_name in SYMPTOM_DICTIONARY:
                symptom_dict_matches += 1
        if symptom_dict_matches > 0:
            # 完全一致する症状がある場合、1つにつき0.05加点（最大0.15）
            confidence_score += min(symptom_dict_matches * 0.05, 0.15)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状名の明確性による信頼度向上: {symptom_dict_matches}個の症状がSYMPTOM_DICTIONARYに完全一致")
        
        # 7. 入力テキストの詳細度による信頼度向上（新規追加）
        # より詳細な記述がある場合（文字数や情報量で判断）
        text_length = len(user_text.strip())
        if text_length > 15:  # 最低限の詳細度
            confidence_score += 0.05
        if text_length > 30:  # より詳細な記述
            confidence_score += 0.05
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"入力テキストの詳細度: {text_length}文字")
        
        # 8. 症状の記述方法の明確性（新規追加）
        # 「○○が△△」のような明確な記述パターンがある場合
        explicit_patterns = [
            r'[がは]かゆ',  # 「腕がかゆい」「頭はかゆい」
            r'[がは]痛',    # 「頭が痛い」「お腹は痛い」
            r'[がは]熱',    # 「熱がある」「熱が高い」
            r'[がは]咳',    # 「咳が出る」「咳が止まらない」
        ]
        explicit_count = sum(1 for pattern in explicit_patterns if re.search(pattern, user_text))
        if explicit_count > 0:
            confidence_score += min(explicit_count * 0.03, 0.1)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"明確な記述パターン検出: {explicit_count}個")
        
        # 信頼度スコアを0.0-1.0の範囲に制限
        confidence_score = min(confidence_score, 1.0)
    else:
        # 症状が検出されていない場合、body_partはNone
        body_part = None
    
    needs_escalation = len(red_flags) > 0
    escalation_reason = f"重症疑い症状が検出されました: {', '.join(red_flags)}" if needs_escalation else ""
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"=== 強化NLU結果 ===")
        logger.debug(f"検出された症状: {[s['name'] for s in detected_symptoms]}")
        logger.debug(f"重症疑い: {red_flags}")
        logger.debug(f"エスカレーション必要: {needs_escalation}")
        logger.debug(f"部位情報: {body_part if body_part else 'なし'}")
        logger.debug(f"信頼度スコア: {confidence_score:.2f}")
    
    # トップレベルのseverityフィールドを追加（各症状の強度から最も高いものを選択）
    if detected_symptoms:
        severity_levels = {"軽度": 1, "中等度": 2, "重度": 3}
        max_severity = max(
            (severity_levels.get(s.get("severity", "中等度"), 2) for s in detected_symptoms),
            default=2
        )
        # 数値から文字列に変換
        severity_map = {1: "軽度", 2: "中等度", 3: "重度"}
        overall_severity = severity_map.get(max_severity, "中等度")
    else:
        overall_severity = "中等度"  # デフォルト
    
    # 女性特有の症状から性別を自動判定
    gender_detected_symptoms = []
    gender_detected = None
    current_gender = user_info.get('gender', '').strip() if user_info.get('gender') else ''
    
    # 既存の性別が「男性」の場合は警告のみで上書きしない
    if current_gender == '男性':
        gender_detected = {
            "detected": False,
            "gender": None,
            "confidence": None,
            "symptoms": [],
            "reason": "既存の性別が男性のため、症状からの自動判定をスキップ",
            "warning": "女性特有の症状が検出されましたが、既に性別が男性として登録されているため、性別は変更しませんでした。"
        }
    else:
        # 女性特有の症状辞書から症状を検出
        for symptom_name, symptom_data in FEMALE_SPECIFIC_SYMPTOMS.items():
            confidence = symptom_data["confidence"]
            synonyms = symptom_data["synonyms"]
            
            # 高信頼度の症状のみを対象
            if confidence == "high":
                # 同義語でマッチング（部分一致を確実にする）
                matched = False
                user_text_lower = user_text.lower()
                for synonym in synonyms:
                    synonym_lower = synonym.lower()
                    # 部分一致を確認（より柔軟なマッチング）
                    if synonym_lower in user_text_lower or user_text_lower in synonym_lower:
                        matched = True
                        break
                    # 正規表現による柔軟なマッチングも試行
                    import re
                    # 「最近生理が遅れています」のようなパターンも検出
                    pattern = re.escape(synonym_lower).replace(r'\ ', r'\s*')
                    if re.search(pattern, user_text_lower):
                        matched = True
                        break
                
                if matched:
                    gender_detected_symptoms.append(symptom_name)
        
        # 高信頼度の症状が1つでも検出された場合、性別を「女性」として自動判定
        if len(gender_detected_symptoms) > 0:
            gender_detected = {
                "detected": True,
                "gender": "female",
                "confidence": "high",
                "symptoms": gender_detected_symptoms,
                "reason": f"{', '.join(gender_detected_symptoms)}の症状から女性と判定"
            }
            logger.info(f"👤 性別自動判定: {gender_detected['reason']}")
        else:
            gender_detected = {
                "detected": False,
                "gender": None,
                "confidence": None,
                "symptoms": [],
                "reason": "女性特有の症状が検出されませんでした"
            }
    
    # 妊娠の可能性を示す症状の検出
    pregnancy_detected_symptoms = []
    pregnancy_score = 0.0
    # 性別自動判定の結果を優先（検出された場合はそれを使用、そうでなければ既存の性別を使用）
    # gender_detectedのgenderは'female'/'male'/'unknown'なので、日本語に変換
    if gender_detected and gender_detected.get('detected'):
        detected_gender_en = gender_detected.get('gender')
        if detected_gender_en == 'female':
            gender = '女性'
        elif detected_gender_en == 'male':
            gender = '男性'
        else:
            gender = current_gender
    else:
        gender = current_gender
    
    # 男性の場合は検出しない
    if gender == '男性':
        pregnancy_possible = {
            "detected": False,
            "score": 0.0,
            "symptoms": [],
            "confidence": None,
            "gender": "male"
        }
    else:
        # 妊娠症状辞書から症状を検出
        for symptom_name, symptom_data in PREGNANCY_SYMPTOMS.items():
            weight = symptom_data["weight"]
            synonyms = symptom_data["synonyms"]
            
            # 同義語でマッチング
            matched = False
            for synonym in synonyms:
                if synonym in user_text:
                    matched = True
                    break
            
            if matched:
                pregnancy_detected_symptoms.append(symptom_name)
                pregnancy_score += weight
        
        # 性別に応じた閾値設定
        # 「生理不順」だけで妊娠可能性を判定するのは早計のため、閾値を上げる
        if gender == '女性':
            threshold = 4.0  # 女性: 閾値を上げる（複数の明確な妊娠症状が必要）
        else:
            threshold = 4.5  # 性別不明: 閾値を高く設定
        
        # 性別不明の場合の誤検出防止：複数の症状（3個以上）が必要
        # ただし「生理の遅れ」は単独でも警告を出す（重み3.0で閾値4.5を超えるため）
        # また、「つわり」などの重要な症状が検出された場合も警告を出す（推奨は継続）
        if gender != '女性' and pregnancy_score >= threshold:
            # 閾値を超えている場合
            pregnancy_possible = {
                "detected": True,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": "low",  # 性別不明の場合は低信頼度
                "gender": "unknown"
            }
        elif gender != '女性' and pregnancy_score > 0.0:
            # 性別不明でスコアが0より大きいが閾値未満の場合
            # 「つわり」「生理の遅れ」などの重要な症状が検出された場合は警告を出す（推奨は継続）
            important_symptoms = ["つわり", "生理の遅れ", "着床出血", "胸の張り"]
            has_important_symptom = any(symptom in important_symptoms for symptom in pregnancy_detected_symptoms)
            
            if has_important_symptom:
                # 重要な症状が検出された場合は警告を出す（推奨は継続）
                pregnancy_possible = {
                    "detected": True,
                    "score": pregnancy_score,
                    "symptoms": pregnancy_detected_symptoms,
                    "confidence": "low",  # 性別不明の場合は低信頼度
                    "gender": "unknown"
                }
            else:
                # 重要な症状がない場合は検出しない
                pregnancy_possible = {
                    "detected": False,
                    "score": pregnancy_score,
                    "symptoms": pregnancy_detected_symptoms,
                    "confidence": None,
                    "gender": "unknown"
                }
        elif gender == '女性' and pregnancy_score >= threshold:
            # 女性で閾値を超えている場合
            pregnancy_possible = {
                "detected": True,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": "high",  # 女性の場合は高信頼度
                "gender": "female"
            }
        else:
            # 閾値を超えていない場合
            pregnancy_possible = {
                "detected": False,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": None,
                "gender": gender if gender else "unknown"
            }
    
    # 妊娠可能性検出のログ（検出された場合のみINFOレベルで出力、それ以外はDEBUG）
    if pregnancy_possible.get('detected', False):
        logger.info(f"🤰 妊娠の可能性検出: detected={pregnancy_possible['detected']}, score={pregnancy_possible['score']:.2f}, confidence={pregnancy_possible['confidence']}, symptoms={pregnancy_possible['symptoms']}, gender={pregnancy_possible.get('gender', 'unknown')}")
    else:
        # 検出されなかった場合でも、スコアが0より大きい場合はINFOレベルでログ出力（デバッグ用）
        if pregnancy_possible.get('score', 0.0) > 0.0:
            threshold = 2.0 if gender == '女性' else 4.5
            logger.info(f"🤰 妊娠可能性検出（閾値未満）: score={pregnancy_possible['score']:.2f}, threshold={threshold}, symptoms={pregnancy_possible['symptoms']}, gender={pregnancy_possible.get('gender', 'unknown')}")
        elif DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"妊娠可能性検出: detected={pregnancy_possible['detected']}, score={pregnancy_possible['score']:.2f}, confidence={pregnancy_possible['confidence']}, symptoms={pregnancy_possible['symptoms']}")
    
    return {
        "symptoms": detected_symptoms,
        "red_flags": red_flags,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason,
        "confidence_score": confidence_score,
        "user_body_part": body_part,  # 部位情報を返り値に含める
        "severity": overall_severity,  # トップレベルの強度
        "pregnancy_possible": pregnancy_possible,  # 妊娠の可能性検出結果
        "gender_detected": gender_detected  # 性別自動判定結果
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
        
        # rule_based_resultからgender_detectedとpregnancy_possibleを取得してgpt_resultに追加
        if 'gender_detected' in rule_based_result:
            gpt_result['gender_detected'] = rule_based_result['gender_detected']
        if 'pregnancy_possible' in rule_based_result:
            gpt_result['pregnancy_possible'] = rule_based_result['pregnancy_possible']
        
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

【重要な注意事項】
- 症状名は必ず上記のリストから選択してください
- 「目がかゆい」「目もかゆい」「目の痒み」などは必ず「目のかゆみ」として抽出してください（「かゆみ」ではありません）
- 「かゆみ」は皮膚のかゆみを指し、「目のかゆみ」とは区別してください
- 「のどが痛い」「喉が痛い」は「のどの痛み」として抽出してください
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

【最重要ルール - 症状名の正確な抽出】
1. 「目がかゆい」「目もかゆい」「目の痒み」「目かゆい」「目が痒い」→必ず「目のかゆみ」として抽出（「かゆみ」ではない）
2. 「かゆみ」は皮膚のかゆみを指し、「目のかゆみ」とは区別してください
3. 「鼻水+くしゃみ+目のかゆみ」の組み合わせはアレルギー性鼻炎の可能性が高い
4. 「のどが痛い」「喉が痛い」→「のどの痛み」として抽出

【その他の重要な注意事項】
- 高熱（38.5度以上）と複数の風邪症状がある場合は、red_flagsに「インフルエンザ疑い」を追加してください
- 体温情報を正確に抽出し、38.5度以上の場合は「高熱」として扱ってください
- 症状名は必ずSYMPTOM_DICTIONARYに定義されている症状名から選択してください
- 重症疑い症状がある場合は必ずneeds_escalationをtrueにしてください"""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
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
        
        # トップレベルのseverityフィールドを追加（各症状の強度から最も高いものを選択）
        symptoms_list = parsed_result.get('symptoms', [])
        if symptoms_list:
            severity_levels = {"軽度": 1, "中等度": 2, "重度": 3}
            max_severity = max(
                (severity_levels.get(s.get("severity", "中等度"), 2) for s in symptoms_list),
                default=2
            )
            # 数値から文字列に変換
            severity_map = {1: "軽度", 2: "中等度", 3: "重度"}
            parsed_result["severity"] = severity_map.get(max_severity, "中等度")
        else:
            parsed_result["severity"] = "中等度"  # デフォルト
        
        # gender_detectedとpregnancy_possibleを追加（simple_pattern_matching_nluから取得）
        try:
            rule_based_result = simple_pattern_matching_nlu(user_text, user_info)
            if 'gender_detected' in rule_based_result:
                parsed_result['gender_detected'] = rule_based_result['gender_detected']
            if 'pregnancy_possible' in rule_based_result:
                parsed_result['pregnancy_possible'] = rule_based_result['pregnancy_possible']
        except Exception as e:
            logger.warning(f"性別・妊娠可能性検出の追加でエラー: {e}")
        
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
    
    # 2.5. 性器周辺症状のチェック（医師受診強く推奨）
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part == "delicate_area":
        # 性器周辺の症状は性感染症や皮膚疾患の可能性があるため、医師受診を強く推奨
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。"
        safety_result["warnings"].append("性器周辺の症状は、性感染症や皮膚疾患の可能性があります。医師の診察を受けることを強く推奨します。")
        safety_result["referral_reasons"].append({
            "description": "性器周辺の症状",
            "message": "性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。",
            "priority": "high"
        })
        # 注意: 推奨は続行するが、医師受診を強く推奨する
    
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
    
    # 3.5. 妊娠の可能性チェック（信頼度に応じた処理）
    # user_infoから取得、なければnlu_resultから取得
    pregnancy_possible = user_info.get('pregnancy_possible')
    if not pregnancy_possible:
        # nlu_resultからpregnancy_possibleを取得
        nlu_pregnancy_possible = nlu_result.get('pregnancy_possible', {})
        if nlu_pregnancy_possible.get('detected', False):
            confidence = nlu_pregnancy_possible.get('confidence')
            if confidence == 'high':
                pregnancy_possible = 'high'
            elif confidence == 'low':
                pregnancy_possible = 'low'
    
    if pregnancy_possible == 'high':
        # 高信頼度（女性+スコア4.0以上）: 推奨を停止し、医師受診のみを促す
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["doctor_referral_required"] = True
        safety_result["escalation_reason"] = "妊娠の可能性があります。医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        safety_result["referral_reasons"].append(DOCTOR_REFERRAL_CONDITIONS["pregnancy_possible"])
        return safety_result
    elif pregnancy_possible == 'low':
        # 低信頼度（性別不明+スコア4.5以上）: 推奨は続行するが、一般的な警告メッセージを表示
        safety_result["warnings"].append("一部の症状は妊娠の可能性を示す場合がありますが、性別情報がないため確定できません。医師にご相談ください。")
        # 推奨は継続するため、is_safeはTrueのまま
    
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


def _has_antidiarrheal_signal(candidate: Dict) -> bool:
    """
    止瀉薬系の成分やテキストシグナルが含まれているかを判定
    """
    ingredients = candidate.get('ingredients', '') or ''
    combined_text_parts = [
        candidate.get('product_name', ''),
        candidate.get('efficacy', ''),
        candidate.get('usage', ''),
        candidate.get('classification', ''),
        candidate.get('medicine_type', '')
    ]
    combined_text = ''.join(part for part in combined_text_parts if part)
    
    for token in ANTIDIARRHEAL_INGREDIENTS:
        if token and token in ingredients:
            return True
    for keyword in ANTIDIARRHEAL_KEYWORDS:
        if keyword and keyword in combined_text:
            return True
    
    return False


def _filter_antidiarrheal_without_diarrhea(
    candidates: List[Dict],
    nlu_result: Dict
) -> List[Dict]:
    """
    下痢症状が確認できない腹痛単独相談で止瀉薬系候補を除外
    """
    if not candidates:
        return candidates
    
    symptoms = nlu_result.get("symptoms", []) or []
    symptom_names = {s.get("name") for s in symptoms if s.get("name")}
    
    if not symptom_names:
        return candidates
    
    # 下痢・軟便などが確認できる場合は除外しない
    diarrhea_related = {"下痢", "軟便", "水様便"}
    if symptom_names & diarrhea_related:
        return candidates
    
    # 腹痛のみの場合に限定
    abdominal_only = symptom_names == {"腹痛"}
    if not abdominal_only:
        return candidates
    
    filtered: List[Dict] = []
    for candidate in candidates:
        if _has_antidiarrheal_signal(candidate):
            if logger.level <= logging.INFO:
                logger.info(
                    f"🚫 下痢症状が未確認の腹痛相談のため止瀉薬候補を除外: {candidate.get('product_name', '')}"
                )
            continue
        filtered.append(candidate)
    
    return filtered


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
    is_single_symptom = len(symptom_names) == 1
    threshold = MIN_SYMPTOM_MATCH_SINGLE if is_single_symptom else MIN_SYMPTOM_MATCH_MULTI
    
    filtered: List[Dict] = []
    for candidate in candidates:
        score_breakdown = candidate.get('score_breakdown', {}) or {}
        symptom_match = score_breakdown.get('symptom_match')
        
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
        
        if symptom_match is not None and symptom_match < adjusted_threshold:
            if logger.level <= logging.INFO:
                logger.info(
                    f"🚫 症状適合度が閾値未満のため候補を除外 (score={symptom_match:.2f}, threshold={adjusted_threshold:.2f}): "
                    f"{candidate.get('product_name', '')}"
                )
            continue
        filtered.append(candidate)
    
    return filtered


def extract_main_ingredients(ingredients: str, max_count: int = 3) -> List[str]:
    """成分表から主要成分を抽出し、比較用に正規化する（キャッシュ対応）"""
    if not ingredients or not isinstance(ingredients, str):
        return []

    # キャッシュキーを作成
    cache_key = (ingredients, max_count)
    
    # キャッシュをチェック
    if cache_key in _ingredient_extraction_cache:
        return _ingredient_extraction_cache[cache_key]

    parts = re.split(r"[\n、,/，／・]+", ingredients)
    normalized = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        normalized.append(token.lower())
        if len(normalized) >= max_count:
            break
    
    # キャッシュに保存
    if len(_ingredient_extraction_cache) >= _max_ingredient_extraction_cache_size:
        # 最も古いエントリを削除（FIFO方式）
        oldest_key = next(iter(_ingredient_extraction_cache))
        del _ingredient_extraction_cache[oldest_key]
    
    _ingredient_extraction_cache[cache_key] = normalized
    
    return normalized


def ensure_ingredient_diversity(candidates: List[Dict], top_n: int = 3, similarity_threshold: float = 0.2, nlu_result: Dict = None) -> List[Dict]:
    """主要成分が重複しすぎないように候補を再選別する（剤形多様性も考慮）
    
    改善点：
    - similarity_thresholdを0.3から0.2に下げる（より厳格に重複を避ける）
    - 異なる成分の医薬品にボーナスを付与
    """
    if len(candidates) <= top_n:
        return candidates

    # スコアフィルタリング: スコア0の候補を除外
    filtered_candidates = [c for c in candidates if c.get('final_score', 0.0) > 0.0]
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
    
    # 液剤を最初に1件確保（剤形多様性）
    liquid_candidate = None
    for candidate in filtered_candidates:
        if candidate == reserved_goreisan or candidate == reserved_cysteine:
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
    # 1. 五苓散（最優先）
    if reserved_goreisan and len(selected) < top_n:
        selected.insert(0, reserved_goreisan)  # 1位に挿入
        selected_sets.insert(0, set(extract_main_ingredients(reserved_goreisan.get("ingredients", ""))))
    
    # 2. L-システイン含有医薬品（2番目の優先度）
    if reserved_cysteine and len(selected) < top_n:
        # 2位または3位に挿入（五苓散が既にある場合は2位）
        insert_pos = min(1, len(selected))
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

    return selected[:top_n]


def _detect_body_part_specificity(candidate: Dict) -> Optional[str]:
    """
    候補医薬品の部位特異性を検出
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        部位名（"delicate_area", "scalp", "throat"など）、またはNone
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    
    # 各部位についてキーワードをチェック
    for body_part, keywords_dict in BODY_PART_SPECIFIC_KEYWORDS.items():
        # 製品名のキーワードをチェック
        if any(kw.lower() in product_name for kw in keywords_dict.get("product_name_keywords", [])):
            return body_part
        
        # 効能効果のキーワードをチェック
        if any(kw.lower() in efficacy for kw in keywords_dict.get("efficacy_keywords", [])):
            return body_part
        
        # 用法のキーワードをチェック
        if any(kw.lower() in usage for kw in keywords_dict.get("usage_keywords", [])):
            return body_part
    
    return None


def _extract_body_part_from_user_text(user_text: str, symptom_name: str) -> Optional[str]:
    """
    ユーザー入力テキストから部位情報を抽出（拡張版）
    
    Args:
        user_text: ユーザーの入力テキスト
        symptom_name: 検出された症状名
    
    Returns:
        部位名（"scalp", "throat", "arm", "leg", "hand", "eye", "nose", "chest", "stomach", "back", "delicate_area"など）、またはNone
    """
    if not user_text:
        return None
    
    user_text_lower = user_text.lower()
    
    # 優先度の高い特殊部位（症状名との組み合わせを考慮）
    # 頭皮関連のキーワード
    scalp_keywords = ["頭", "頭皮", "頭部", "フケ", "頭頂部", "後頭部"]
    if any(kw in user_text_lower for kw in scalp_keywords):
        if symptom_name in ["かゆみ", "発疹", "湿疹"] or "かゆ" in user_text_lower or "フケ" in user_text_lower:
            return "scalp"
    
    # デリケート部位関連のキーワード（多言語対応）
    # 日本語
    delicate_keywords_jp = ["デリケート", "おりもの", "ナプキン", "蒸れ", "おむつ", "陰部", "股間", 
                            "ペニス", "性器", "生殖器", "局部", "私部", "陰茎", "陰嚢", "亀頭"]
    # 中国語（繁体字・簡体字）
    delicate_keywords_zh = ["陰莖", "陰茎", "生殖器", "性器", "私處", "私处", "私部", "局部", 
                            "陰部", "股間", "股间", "陰囊", "陰囊", "龜頭", "龟头", "阴茎"]
    # 英語
    delicate_keywords_en = ["penis", "genital", "private area", "genitalia", "genitals", 
                           "private parts", "intimate area", "groin", "pubic", "scrotum", 
                           "glans", "foreskin"]
    
    # すべてのキーワードを統合
    delicate_keywords = delicate_keywords_jp + delicate_keywords_zh + delicate_keywords_en
    
    # ユーザー入力テキストを正規化（大文字小文字、空白を除去）
    normalized_text = user_text_lower.replace(" ", "").replace("\t", "").replace("\n", "")
    
    # キーワードマッチング（部分一致も含む）
    for kw in delicate_keywords:
        kw_lower = kw.lower()
        # 完全一致または部分一致をチェック
        if kw_lower in user_text_lower or kw_lower in normalized_text:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"デリケート部位を検出: キーワード='{kw}', 入力テキスト='{user_text[:50]}...'")
            return "delicate_area"
    
    # のど関連のキーワード
    throat_keywords = ["のど", "喉", "咽頭", "喉頭", "声帯"]
    if any(kw in user_text_lower for kw in throat_keywords):
        if symptom_name in ["のどの痛み", "かゆみ", "咳"] or "痛" in user_text_lower or "かゆ" in user_text_lower:
            return "throat"
    
    # 一般的な部位の検出（優先度順）
    general_body_parts = {
        'arm': ['腕', 'うで', '上腕', '前腕', '二の腕', 'ひじ', '肘'],
        'leg': ['足', '脚', 'あし', '下肢', '太もも', 'ふともも', 'もも', 'すね', '脛', 'ふくらはぎ', '膝', 'ひざ'],
        'hand': ['手', 'て', '手首', '手のひら', '手の甲', '指', '親指', '人差し指', '中指', '薬指', '小指'],
        'foot': ['足首', 'くるぶし', '足の裏', '足の甲', 'つま先', 'かかと'],
        'eye': ['目', '眼', 'まぶた', '眼球', '白目', '黒目', '瞳', '目頭', '目尻'],
        'nose': ['鼻', 'はな', '鼻腔', '鼻の穴', '鼻先', '鼻筋'],
        'ear': ['耳', 'みみ', '耳たぶ', '耳の穴', '耳の奥'],
        'mouth': ['口', 'くち', '口腔', '唇', 'くちびる', '歯茎', '歯', '舌', 'した'],
        'chest': ['胸', '胸部', '乳房', 'おっぱい', '乳首'],
        'stomach': ['お腹', '腹部', '胃', 'みぞおち', 'へそ', 'おへそ', '下腹部', 'わき腹', '脇腹'],
        'back': ['背中', '腰', '腰部', '腰椎', '背骨', '脊椎'],
        'shoulder': ['肩', 'かた', '肩甲骨', '肩こり'],
        'neck': ['首', 'くび', '首筋', 'うなじ'],
        'face': ['顔', 'かお', '頬', 'ほほ', 'ほっぺ', 'あご', '顎', '額', 'ひたい', 'こめかみ'],
        'skin': ['皮膚', '肌', 'はだ', '表皮']
    }
    
    # 部位を優先度順にチェック（より具体的な部位を優先）
    for part_name, keywords in general_body_parts.items():
        if any(kw in user_text_lower for kw in keywords):
            return part_name
    
    return None


def _extract_min_age_value(age_restriction) -> Optional[int]:
    """年齢制限から最小年齢を抽出"""
    if age_restriction is None:
        return None

    if isinstance(age_restriction, (int, float)):
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            return None
        try:
            return int(age_restriction)
        except (ValueError, OverflowError):
            return None

    if isinstance(age_restriction, str) and age_restriction.strip():
        match = re.search(r'(\d+)', age_restriction)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    return None


def _is_kakkonto_by_ingredients(candidate: Dict) -> bool:
    """
    成分ベースで葛根湯を判定
    
    Args:
        candidate: 候補医薬品情報
    
    Returns:
        葛根湯の主要成分（カッコン、カンゾウ、ケイヒ、タイソウ、ショウキョウ、シャクヤク、マオウ）のうち
        5つ以上が含まれていればTrue
    """
    ingredients = str(candidate.get('ingredients', '')).lower()
    if not ingredients:
        return False
    
    kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
    ingredients_normalized = normalize_text(ingredients)
    count = sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized)
    return count >= 5


def _is_kakkonto_medicine(candidate: Dict) -> bool:
    """
    統一された葛根湯判定関数
    
    Args:
        candidate: 候補医薬品情報
    
    Returns:
        葛根湯の場合True
    """
    product_name = candidate.get('product_name', '')
    is_kakkonto_by_name = "葛根湯" in product_name
    
    # 成分ベースで葛根湯を判定（漢方薬判定をスキップして、直接成分をチェック）
    ingredients = str(candidate.get('ingredients', '')).lower()
    kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
    ingredients_normalized = normalize_text(ingredients)
    has_kakkonto_ingredients = sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized) >= 5
    
    # 製品名に「葛根湯」が含まれているか、または成分から判定（漢方薬判定をスキップ）
    is_kakkonto = is_kakkonto_by_name or has_kakkonto_ingredients
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"葛根湯判定（統一関数）: {product_name}, is_kakkonto_by_name={is_kakkonto_by_name}, has_kakkonto_ingredients={has_kakkonto_ingredients} (成分数: {sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized)}), is_kakkonto={is_kakkonto}")
    
    return is_kakkonto


def _candidate_has_throat_liquid_signature(candidate: Dict) -> bool:
    """候補が喉向け液剤かどうかを判定"""
    combined_text = normalize_text(
        ''.join(
            filter(
                None,
                [
                    candidate.get('product_name', ''),
                    candidate.get('efficacy', ''),
                    candidate.get('usage', ''),
                    candidate.get('medicine_type', '')
                ]
            )
        )
    )

    if not combined_text:
        return False

    return any(token in combined_text for token in THROAT_LIQUID_TOKENS)


def _is_pediatric_specific(candidate: Dict) -> bool:
    """小児専用製品を判定（年齢不明時の除外用）"""
    # NaN処理を安全にするため、str()でキャスト
    def safe_str(value) -> str:
        if value is None:
            return ''
        if isinstance(value, float) and math.isnan(value):
            return ''
        return str(value)
    
    p_name = safe_str(candidate.get('product_name', ''))
    efficacy = safe_str(candidate.get('efficacy', ''))
    m_type = safe_str(candidate.get('medicine_type', ''))
    usage_text = safe_str(candidate.get('usage', ''))
    
    # 製品名・タイプに小児専用キーワードがある場合は小児専用と判定
    target_text = p_name + m_type
    has_pediatric_keyword = any(k in target_text for k in PEDIATRIC_KEYWORDS)
    
    # 用法チェック（補助的）
    has_pediatric_usage = False
    if any(k in usage_text for k in PEDIATRIC_KEYWORDS) and \
       any(f in usage_text for f in PEDIATRIC_USAGE_KEYWORDS):
        has_pediatric_usage = True
    
    # キーワードで判定できた場合は、年齢制限に関係なく小児専用と判定
    if has_pediatric_keyword or has_pediatric_usage:
        return True
    
    # 年齢制限のチェック（キーワードがない場合のみ）
    raw_age = candidate.get('age_restriction')
    min_age_allowed = _extract_min_age_value(raw_age)
    
    if min_age_allowed is None:
        return False  # 年齢不明、かつキーワードもなし → 大人用とみなしてFalse
    
    if min_age_allowed >= 13:
        return False
    
    
    return False


def _is_motion_sickness_medicine(candidate: Dict) -> bool:
    """
    乗り物酔い薬（鎮暈薬）かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        乗り物酔い薬の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    target_text = product_name + efficacy + medicine_type
    
    # 乗り物酔い薬のキーワード（アネロン「ニスキャップ」を追加）
    motion_sickness_keywords = ["酔い", "めまい", "乗り物", "船酔い", "車酔い", "鎮暈", "トラベルミン", "トリブラ", "アネロン", "ニスキャップ", "ソラシドン", "センパア"]
    return any(kw in target_text for kw in motion_sickness_keywords)

def _has_motion_sickness_symptom(nlu_result: Dict, user_text: str) -> bool:
    """
    ユーザーの症状に乗り物酔い関連の症状があるか判定
    
    Args:
        nlu_result: NLU解析結果
        user_text: ユーザーの入力テキスト
    
    Returns:
        乗り物酔い関連の症状がある場合True
    """
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    
    # ユーザー入力テキストの小文字化
    user_text_lower = user_text.lower()
    
    # 二日酔い関連のキーワードがある場合は乗り物酔いではない
    hangover_keywords = ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ", "酒", "アルコール", "お酒"]
    if any(kw in user_text_lower for kw in hangover_keywords):
        return False
    
    # 乗り物酔い関連の症状キーワード（二日酔いは除外）
    motion_sickness_symptoms = ["乗り物酔い", "車酔い", "船酔い"]
    
    # 症状名でチェック
    if any(s in symptom_names for s in motion_sickness_symptoms):
        return True
    
    # ユーザー入力テキストでチェック（より具体的なキーワードのみ）
    # 注意：「酔い」単独は除外（二日酔いと誤認識されるため）
    motion_sickness_text_keywords = [
        "乗り物酔い", "車酔い", "船酔い", "バス酔い", "電車酔い",
        "車に乗ると", "船に乗ると", "バスに乗ると", "電車に乗ると",
        "乗り物で", "移動中", "旅行で", "ドライブで"
    ]
    if any(kw in user_text_lower for kw in motion_sickness_text_keywords):
        return True
    
    return False

def _expand_search_categories(symptom_names: List[str], medicine_types: set) -> set:
    """
    症状に基づいて検索対象カテゴリを拡張する
    例: "肩こり"なら "解熱鎮痛薬" に加えて "外用薬（皮膚）" も検索対象にする
    
    Args:
        symptom_names: 検出された症状名のリスト
        medicine_types: 既に決定された医薬品種類のセット
    
    Returns:
        拡張された医薬品種類のセット
    """
    expanded_types = set(medicine_types)  # 既存の種類をコピー
    
    # アレルギー症状の検出（目のかゆみ + くしゃみ/鼻水）
    allergy_symptoms = ["目のかゆみ"]
    allergy_indicators = ["くしゃみ", "鼻水", "鼻づまり"]
    
    has_eye_itch = any(s in symptom_names for s in allergy_symptoms)
    has_allergy_indicator = any(s in symptom_names for s in allergy_indicators)
    
    if has_eye_itch and has_allergy_indicator:
        # アレルギー性鼻炎の可能性が高い
        if "鼻炎用薬" not in expanded_types:
            expanded_types.add("鼻炎用薬")
        # アレルギー症状が検出された場合、鼻炎用薬を優先的に検索するため、フラグを設定
        logger.info("アレルギー症状（目のかゆみ + くしゃみ/鼻水）を検出。鼻炎用薬カテゴリを追加しました")
    
    # 整形外科的症状のキーワード
    musculoskeletal_symptoms = ["肩こり", "筋肉痛", "関節痛", "腰痛", "打撲", "捻挫"]
    
    # 症状リストのいずれかが上記に該当する場合
    if any(s in symptom_names for s in musculoskeletal_symptoms):
        # データベース上の正確なカテゴリ名: "外用薬（皮膚）"
        topical_category = "外用薬（皮膚）"
        oral_category = "解熱鎮痛薬"
        
        # 外用薬を追加
        expanded_types.add(topical_category)
        
        # もし元々の判定が「筋肉痛」のような曖昧なカテゴリだった場合、内服薬も明示的に追加
        if "筋肉痛" in expanded_types and oral_category not in expanded_types:
            expanded_types.add(oral_category)
    
    return expanded_types


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
    
    # アレルギー症状フラグの設定（後続のスコアリングで使用）
    # NLU結果とユーザー入力テキストの両方から検出（より確実に）
    allergy_symptoms = ["目のかゆみ", "かゆみ"]  # 「かゆみ」も含める（NLUが「目のかゆみ」を「かゆみ」として抽出する場合がある）
    allergy_indicators = ["くしゃみ", "鼻水", "鼻づまり"]
    has_eye_itch = any(s in symptom_names for s in allergy_symptoms)
    has_allergy_indicator = any(s in symptom_names for s in allergy_indicators)
    
    # ユーザー入力テキストからも直接検出（NLUが抽出し損ねた場合のフォールバック）
    user_text_lower = user_text.lower() if user_text else ""
    if not has_eye_itch:
        # 「目のかゆみ」「目がかゆい」「目の痒み」「目かゆ」「目痒」などを直接検出
        eye_itch_keywords = ["目のかゆみ", "目がかゆい", "目の痒み", "目かゆ", "目痒", "目もかゆ", "目も痒"]
        has_eye_itch = any(kw in user_text_lower for kw in eye_itch_keywords)
    
    if not has_allergy_indicator:
        # くしゃみ、鼻水、鼻づまりを直接検出
        allergy_indicator_keywords = ["くしゃみ", "鼻水", "鼻づまり", "鼻詰まり", "鼻が詰まる"]
        has_allergy_indicator = any(kw in user_text_lower for kw in allergy_indicator_keywords)
    
    # 「かゆみ」が検出された場合、ユーザー入力テキストで「目」が含まれているか確認
    if "かゆみ" in symptom_names and not has_eye_itch:
        # 「目」が含まれているか、または「目もかゆい」などの表現があるか確認
        if "目" in user_text_lower or "眼" in user_text_lower:
            has_eye_itch = True
            logger.info("「かゆみ」+「目」の組み合わせから目のかゆみを検出しました")
        # 「目もかゆい」などの表現を直接チェック
        elif any(kw in user_text_lower for kw in ["目もかゆ", "目も痒", "目がかゆ", "目が痒"]):
            has_eye_itch = True
            logger.info("「目もかゆい」などの表現から目のかゆみを検出しました")
    
    is_allergy_case = has_eye_itch and has_allergy_indicator
    
    # アレルギー症状が検出された場合の詳細ログ
    if is_allergy_case:
        logger.info(f"アレルギー症状を検出: 目のかゆみ={has_eye_itch}, アレルギー指標={has_allergy_indicator}, ユーザー入力={user_text[:100]}")
    
    # 拡張ロジックを適用（肩こり・筋肉痛の場合に外用薬を追加、アレルギー症状の場合は鼻炎用薬を追加）
    medicine_types = _expand_search_categories(symptom_names, medicine_types)
    
    # アレルギー症状が検出された場合、鼻炎用薬カテゴリを強制的に追加
    if is_allergy_case:
        if "鼻炎用薬" not in medicine_types:
            medicine_types.add("鼻炎用薬")
            logger.info("アレルギー症状が検出されました（ユーザー入力テキストからも検出）。鼻炎用薬カテゴリを追加しました")
        # 風邪薬カテゴリを削除または優先度を下げる（アレルギー症状の場合は風邪薬は不適切）
        if "風邪薬" in medicine_types and len(medicine_types) > 1:
            # 風邪薬は残すが、優先度は下がる（ペナルティで対応）
            logger.info("アレルギー症状が検出されたため、風邪薬へのペナルティを適用します")
    
    # 二日酔い検出（ユーザー入力テキストから）
    hangover_keywords = ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ", "酒", "アルコール"]
    is_hangover = any(kw in user_text_lower for kw in hangover_keywords)
    
    # 二日酔いの症状パターンからも検出
    hangover_symptom_patterns = [
        frozenset({"頭痛", "むくみ", "だるさ"}),
        frozenset({"頭痛", "むくみ"}),
        frozenset({"頭痛", "だるさ"}),
        frozenset({"むくみ", "だるさ"}),
        frozenset({"頭痛", "吐き気"}),
        frozenset({"頭痛", "だるさ", "吐き気"}),
        frozenset({"吐き気", "むくみ"}),
        frozenset({"吐き気", "だるさ"}),
    ]
    
    # 症状名の正規化（「疲労感」→「だるさ」など）
    symptom_mapping_for_hangover = {
        "疲労感": "だるさ",
        "倦怠感": "だるさ",
        "疲れ": "だるさ",
        "だるい": "だるさ",
    }
    normalized_symptom_names_for_hangover = [symptom_mapping_for_hangover.get(name, name) for name in symptom_names]
    normalized_symptom_set_for_hangover = frozenset(normalized_symptom_names_for_hangover)
    
    # 症状パターンマッチング
    if not is_hangover:
        for pattern in hangover_symptom_patterns:
            if pattern.issubset(normalized_symptom_set_for_hangover):
                is_hangover = True
                logger.info(f"二日酔い症状パターンを検出: {pattern} ⊆ {normalized_symptom_set_for_hangover}")
                break
    
    # 二日酔いが検出された場合、「抗アレルギー薬」カテゴリを追加（五苓散用）
    if is_hangover:
        if "抗アレルギー薬" not in medicine_types:
            medicine_types.add("抗アレルギー薬")
            logger.info("二日酔いが検出されました。抗アレルギー薬カテゴリを追加（五苓散対応）")
    
    logger.info(f"推定された医薬品の種類（拡張後）: {medicine_types}")
    if is_allergy_case:
        logger.info(f"アレルギー症状が検出されました（目のかゆみ: {has_eye_itch}, アレルギー指標: {has_allergy_indicator}）。鼻炎用薬を優先します")
    if is_hangover:
        logger.info(f"二日酔いが検出されました（キーワードまたは症状パターン）。二日酔い向け医薬品を優先します")

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

        # 特殊用途医薬品の除外チェック（ホルモン剤、男性器塗布剤など）
        candidate_dict = {
            'product_name': product_name,
            'efficacy': efficacy,
            'usage': row.get('用法用量', ''),
            'ingredients': ingredients
        }
        if is_specific_use_medicine(candidate_dict):
            # ユーザーの症状が特殊用途に該当するかチェック
            user_symptoms_str = " ".join(symptom_names).lower()
            specific_symptom_keywords = ["性器", "ホルモン", "勃起", "更年期", "記憶力", "男性器", "女性器", "ペニス", "陰茎"]
            is_specific_symptom = any(kw in user_symptoms_str for kw in specific_symptom_keywords)
            
            if not is_specific_symptom:
                # 特殊用途の症状がない場合は除外
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"特殊用途医薬品を除外: {product_name} (症状: {symptom_names})")
                return

        # 年齢制限の整形
        age_restriction = row.get('年齢制限', '')
        if not age_restriction and hasattr(row, 'iloc') and len(row) > 6:
            age_restriction = row.iloc[6]
        # 数値（float/int）の場合は文字列に変換
        if isinstance(age_restriction, (int, float)):
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            else:
                age_restriction = f"{int(age_restriction)}歳以上"
        elif age_restriction and isinstance(age_restriction, str):
            age_match = re.search(r'(\d+)歳', age_restriction)
            if age_match:
                age_restriction = f"{age_match.group(1)}歳以上"

        usage_full = row.get('用法用量', '') or ''
        usage_notes = ''
        if '注意' in usage_full or '＜' in usage_full:
            parts = usage_full.split('\n')
            note_parts = [p for p in parts if '注意' in p or '＜' in p or '用法' in p]
            usage_notes = '\n'.join(note_parts[:3])

        # 医薬品種類の補正（のど向け外用薬が「皮膚」に分類されている場合）
        medicine_type = _sanitize_text(row.get('医薬品の種類', ''))
        if medicine_type == '外用薬（皮膚）':
            # 効能にのど関連キーワードがあれば「外用薬（のど）」に補正
            if efficacy and any(keyword in efficacy for keyword in ['のどの痛み', 'のどの', 'のど', '喉', '咽頭', '声がれ']):
                medicine_type = '外用薬（のど）'
        
        candidate = {
            'medicine_id': len(candidates),
            'product_name': product_name,
            'manufacturer': manufacturer,
            'medicine_type': medicine_type,
            'classification': _sanitize_text(row.get('分類', '')),
            'efficacy': efficacy,
            'usage': row.get('用法用量', ''),
            'age_restriction': age_restriction,
            'ingredients': ingredients,
            'doping_prohibited': _sanitize_text(row.get('禁止物質あり', '')),
            'competition_category': _sanitize_text(row.get('競技会区分', '')),
            'conditions': _sanitize_text(row.get('条件', '')),
            'usage_notes': usage_notes if usage_notes else '用法用量を守ってご使用ください。',
            'base_score': 0.0,
            'is_allergy_case': is_allergy_case,  # アレルギー症状フラグ
            'is_hangover': is_hangover  # 二日酔いフラグ
        }

        # アレルギー症状が検出された場合、風邪薬カテゴリにペナルティを適用
        if is_allergy_case and '風邪薬' in medicine_type:
            candidate['allergy_penalty'] = -0.35  # 風邪薬へのペナルティ（さらに強化）
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アレルギー症状検出: 風邪薬 {product_name} にペナルティ -0.35 を適用")
        
        # アレルギー症状が検出された場合、鼻炎用薬カテゴリに大幅ブーストを適用
        if is_allergy_case and '鼻炎用薬' in medicine_type:
            candidate['allergy_boost'] = 0.40  # 鼻炎用薬への大幅ブースト（さらに強化）
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アレルギー症状検出: 鼻炎用薬 {product_name} にブースト +0.40 を適用")
        
        # 二日酔いが検出された場合、二日酔い関連医薬品にブーストを適用
        if is_hangover:
            # 症状に頭痛が含まれているか確認
            has_headache = any("頭痛" in str(s.get("name", "")) for s in symptoms)
            
            # 五苓散系の医薬品（最優先）
            if "五苓散" in product_name or "五苓散" in efficacy:
                # 頭痛がある場合はさらにブースト強化
                if has_headache:
                    candidate['hangover_boost'] = 0.55  # 頭痛+二日酔いで五苓散を最優先
                else:
                    candidate['hangover_boost'] = 0.50  # 五苓散への非常に大幅なブースト（最優先）
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い検出: 五苓散 {product_name} にブースト +{candidate['hangover_boost']:.2f} を適用")
            # 効能効果に「二日酔い」が明記されている医薬品（次優先）
            elif any(kw in efficacy.lower() for kw in ["二日酔", "宿酔", "悪酔"]):
                # L-システイン含有で主効能が美容用途（しみ・そばかす）の場合はブースト減少
                is_cysteine = "l-システイン" in ingredients.lower() or "システイン" in ingredients.lower()
                is_beauty_primary = any(kw in efficacy.lower()[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])
                
                if is_cysteine and is_beauty_primary:
                    candidate['hangover_boost'] = 0.00  # 美容用途主体のL-システイン製品はブースト大幅減少
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: L-システイン（美容主体） {product_name} にブースト +0.00 を適用（大幅減少）")
                else:
                    candidate['hangover_boost'] = 0.38  # 二日酔い効能明記医薬品へのブースト
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 二日酔い効能明記 {product_name} にブースト +0.38 を適用")
            # L-システイン含有医薬品（二日酔い関連効能がある場合のみ）
            elif ("l-システイン" in ingredients.lower() or "システイン" in ingredients.lower()) and \
                 any(kw in efficacy.lower() for kw in ["倦怠", "疲労", "肝", "解毒"]):
                candidate['hangover_boost'] = 0.32  # L-システイン含有医薬品へのブースト
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い検出: L-システイン含有（二日酔い関連効能） {product_name} にブースト +0.32 を適用")
            # 生薬配合の胃腸薬（吐き気・胃もたれ対応）- ブースト強化
            elif '胃腸薬' in medicine_type and any(kw in efficacy.lower() for kw in ["生薬", "健胃", "消化"]):
                # 効能に「二日酔のむかつき」「悪酔のむかつき」が含まれる場合はさらにブースト
                if any(kw in efficacy.lower() for kw in ["二日酔のむかつき", "悪酔のむかつき"]):
                    candidate['hangover_boost'] = 0.40  # 二日酔い専用胃腸薬へのブースト（強化）
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 二日酔い専用胃腸薬 {product_name} にブースト +0.40 を適用")
                else:
                    candidate['hangover_boost'] = 0.28  # 生薬配合胃腸薬へのブースト
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 生薬配合胃腸薬 {product_name} にブースト +0.28 を適用")

        # 総合感冒薬（喉向き）の識別
        # 葛根湯は漢方薬なので、総合感冒薬（喉向き）として識別しない
        throat_specificity_level = "none"
        # 成分ベースで葛根湯を判定（製品名だけでなく成分もチェック）
        is_kakkonto_product = "葛根湯" in product_name
        is_kakkonto_by_ingredients = _is_kakkonto_by_ingredients(candidate)
        is_kakkonto_any = is_kakkonto_product or is_kakkonto_by_ingredients
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"葛根湯判定（識別段階）: {product_name}, is_kakkonto_product={is_kakkonto_product}, is_kakkonto_by_ingredients={is_kakkonto_by_ingredients}, is_kakkonto_any={is_kakkonto_any}")
        
        if '風邪薬' in medicine_type and not is_kakkonto_any:
            has_throat_efficacy = efficacy and any(keyword in efficacy for keyword in ['のどの痛み', 'のどの', 'のど', '喉', '咽頭'])
            if has_throat_efficacy:
                # 成分をチェック（表記ゆれに対応）
                ingredients_lower = str(ingredients).lower() if ingredients else ""
                ingredients_normalized = normalize_text(ingredients_lower)
                # 成分名の表記ゆれに対応（例：「グリチルリチン酸」と「グリチルリチン」）
                has_throat_ingredient = False
                for ing in THROAT_SPECIFIC_INGREDIENTS:
                    ing_normalized = normalize_text(ing.lower())
                    # 完全一致または部分一致をチェック
                    if ing_normalized in ingredients_normalized:
                        has_throat_ingredient = True
                        break
                    # 成分名の一部が含まれている場合もチェック（例：「グリチルリチン」が「グリチルリチン酸」に含まれる）
                    ing_parts = ing_normalized.split()
                    if any(part in ingredients_normalized for part in ing_parts if len(part) > 3):
                        has_throat_ingredient = True
                        break
                if has_throat_ingredient:
                    throat_specificity_level = "component_and_efficacy"
                    matched_ingredients = [ing for ing in THROAT_SPECIFIC_INGREDIENTS if normalize_text(ing.lower()) in ingredients_normalized]
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・成分あり）を識別: {product_name}, level={throat_specificity_level}, ingredients={matched_ingredients}")
                else:
                    # 効能に「のど」が含まれている場合は「効能のみ」として識別
                    throat_specificity_level = "efficacy_only"
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・効能のみ）を識別: {product_name}, level={throat_specificity_level} (成分なし)")
            else:
                # 効能にのど関連がない場合でも、製品名や成分から判断
                product_name_lower = str(product_name).lower()
                has_throat_keyword = any(keyword in product_name_lower for keyword in ['のど', '喉', '咽頭', 'トローチ', 'スプレー', 'うがい'])
                if has_throat_keyword:
                    ingredients_normalized = normalize_text(str(ingredients).lower() if ingredients else "")
                    # 成分名の表記ゆれに対応
                    has_throat_ingredient = False
                    for ing in THROAT_SPECIFIC_INGREDIENTS:
                        ing_normalized = normalize_text(ing.lower())
                        # 完全一致または部分一致をチェック
                        if ing_normalized in ingredients_normalized:
                            has_throat_ingredient = True
                            break
                        # 成分名の一部が含まれている場合もチェック
                        ing_parts = ing_normalized.split()
                        if any(part in ingredients_normalized for part in ing_parts if len(part) > 3):
                            has_throat_ingredient = True
                            break
                    if has_throat_ingredient:
                        throat_specificity_level = "component_and_efficacy"
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"総合感冒薬（喉向き・成分あり）を識別（製品名から）: {product_name}")
                    else:
                        throat_specificity_level = "efficacy_only"
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"総合感冒薬（喉向き・効能のみ）を識別（製品名から）: {product_name}")
        candidate['throat_specificity_level'] = throat_specificity_level

        if contains_risk and risk_info:
            candidate['risk_ingredient'] = risk_name
            candidate['risk_warning'] = risk_info.get("warning", "")
            candidate['risk_penalty'] = risk_info.get("penalty_score", -0.3)

        candidates.append(candidate)
        existing_keys.add(key)

    for medicine_type in medicine_types:
        matched = medicine_df[medicine_df['医薬品の種類'] == medicine_type]
        matched_count = len(matched)
        logger.info(f"候補抽出: medicine_type={medicine_type}, 抽出数={matched_count}")
        for _, row in matched.iterrows():
            append_candidate(row)
        if matched_count > 0:
            logger.info(f"候補抽出完了: medicine_type={medicine_type}, 追加候補数={matched_count}")

    # のどの痛みがある場合は局所治療薬も候補に追加
    has_throat_pain = "のどの痛み" in symptom_names
    if has_throat_pain:
        logger.info(f"のどの痛み検出: 局所治療薬（外用薬（のど））を候補に追加します")
        throat_keyword_pattern = r"(?:のど|喉|咽頭)"
        product_keyword_pattern = r"(?:のど|喉|咽|トローチ|スプレー|うがい|キャンディ|飴)"
        
        # 喉の痛み特化医薬品を明示的に検索（ベンザブロック、ルルアタックなど）
        throat_specific_keywords = ["ベンザブロック", "ルルアタック", "トラネキサム"]
        throat_specific_mask = medicine_df['製品名'].astype(str).str.contains(
            '|'.join(throat_specific_keywords), na=False, case=False, regex=True
        )

        throat_mask = (
            medicine_df['効能効果'].astype(str).str.contains(throat_keyword_pattern, na=False) |
            medicine_df['製品名'].astype(str).str.contains(product_keyword_pattern, na=False) |
            medicine_df['医薬品の種類'].astype(str).str.contains(throat_keyword_pattern, na=False) |
            throat_specific_mask  # 喉の痛み特化医薬品も含める
        )

        throat_candidates = medicine_df[throat_mask]
        throat_count = 0
        for _, row in throat_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            if key not in existing_keys:
                append_candidate(row)
                throat_count += 1
        
        logger.info(f"のどの痛み関連候補追加: {throat_count}件（重複除外後）")
        if throat_specific_mask.any():
            logger.info(f"喉の痛み特化医薬品を検出しました: {throat_specific_mask.sum()}件")

    # VIP成分枠：肩こり・筋肉痛の場合、第2世代鎮痛成分を含む製品を強制的に候補に追加
    has_musculoskeletal_symptom = any(s in symptom_names for s in ["肩こり", "筋肉痛", "関節痛", "腰痛"])
    if has_musculoskeletal_symptom:
        # 第2世代鎮痛成分のキーワード
        vip_ingredients = [
            "フェルビナク", "フェルビナクナトリウム", "フェルビナクナトリウム水和物",
            "インドメタシン", "インダシン", "インドメタシン水和物",
            "ジクロフェナク", "ジクロフェナクナトリウム", "ボルタレン", "ジクロフェナクナトリウム水和物"
        ]
        
        # VIP成分を含む製品を検索（外用薬に限定）
        vip_mask = (
            medicine_df['医薬品の種類'].astype(str).str.contains('外用', na=False) &
            medicine_df['成分'].astype(str).str.contains('|'.join(vip_ingredients), na=False, case=False, regex=True)
        )
        
        vip_candidates = medicine_df[vip_mask]
        vip_count = 0
        for _, row in vip_candidates.iterrows():
            # 既に候補に含まれているかチェック
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            
            if key not in existing_keys:
                append_candidate(row)
                vip_count += 1
        
        if vip_count > 0:
            logger.info(f"VIP成分枠: 第2世代鎮痛成分含有の外用薬を{vip_count}件追加しました")
        
        # 最適解の製品名も強制的に追加（フェイタス、バンテリン、サロンパス）
        optimal_product_keywords = ["フェイタス", "バンテリン", "サロンパス"]
        optimal_mask = (
            medicine_df['医薬品の種類'].astype(str).str.contains('外用', na=False) &
            medicine_df['製品名'].astype(str).str.contains('|'.join(optimal_product_keywords), na=False, case=False, regex=True)
        )
        
        optimal_candidates = medicine_df[optimal_mask]
        optimal_count = 0
        for _, row in optimal_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            
            if key not in existing_keys:
                append_candidate(row)
                optimal_count += 1
        
        if optimal_count > 0:
            logger.info(f"VIP製品名枠: 最適解の外用薬を{optimal_count}件追加しました（フェイタス、バンテリン、サロンパス）")

    # 二日酔い特化医薬品の追加（効能効果から直接検索）
    # 注意: append_candidate内で二日酔いブーストが設定されるため、
    # 二日酔い特化医薬品を追加する前に is_hangover フラグが必要
    if is_hangover:
        # 二日酔い関連のキーワードで効能効果を検索
        hangover_efficacy_keywords = ["二日酔", "宿酔", "悪酔", "五苓散", "茵ちん五苓散"]
        hangover_mask = medicine_df['効能効果'].astype(str).str.contains(
            '|'.join(hangover_efficacy_keywords), na=False, case=False, regex=True
        )
        
        hangover_candidates = medicine_df[hangover_mask]
        hangover_count = 0
        for _, row in hangover_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            
            if key not in existing_keys:
                append_candidate(row)
                hangover_count += 1
        
        if hangover_count > 0:
            logger.info(f"二日酔い特化医薬品を効能効果から{hangover_count}件追加しました")
        
        # L-システイン含有医薬品も追加検索
        cysteine_keywords = ["l-システイン", "lシステイン", "システイン"]
        cysteine_mask = medicine_df['成分'].astype(str).str.contains(
            '|'.join(cysteine_keywords), na=False, case=False, regex=True
        )
        
        cysteine_candidates = medicine_df[cysteine_mask]
        cysteine_count = 0
        for _, row in cysteine_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            
            # 効能効果に「二日酔い」「肝臓」「解毒」などが含まれるか確認
            efficacy = str(row.get('効能効果', '')).lower()
            is_hangover_related = any(kw in efficacy for kw in ["二日酔", "宿酔", "悪酔", "肝", "解毒", "倦怠", "疲労"])
            
            if key not in existing_keys and is_hangover_related:
                append_candidate(row)
                cysteine_count += 1
        
        if cysteine_count > 0:
            logger.info(f"L-システイン含有医薬品（二日酔い関連）を{cysteine_count}件追加しました")
        
        # 二日酔いブーストを後から適用（append_candidate内で設定されなかった場合のフォールバック）
        for candidate in candidates:
            if not candidate.get('hangover_boost'):  # まだ設定されていない場合
                product_name = candidate.get('product_name', '')
                efficacy = candidate.get('efficacy', '')
                ingredients = str(candidate.get('ingredients', '')).lower()
                medicine_type = candidate.get('medicine_type', '')
                
                # 五苓散系の医薬品（最優先）
                if "五苓散" in product_name or "五苓散" in efficacy:
                    candidate['hangover_boost'] = 0.50
                # 効能効果に「二日酔い」が明記されている医薬品（次優先）
                elif any(kw in efficacy.lower() for kw in ["二日酔", "宿酔", "悪酔"]):
                    # L-システイン含有で主効能が美容用途の場合はブースト減少
                    is_cysteine = "l-システイン" in ingredients or "システイン" in ingredients
                    is_beauty_primary = any(kw in efficacy.lower()[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])
                    
                    if is_cysteine and is_beauty_primary:
                        candidate['hangover_boost'] = 0.10  # 美容主体は大幅減少
                    else:
                        candidate['hangover_boost'] = 0.38
                # L-システイン含有医薬品（二日酔い関連効能がある場合）
                elif ("l-システイン" in ingredients or "システイン" in ingredients) and \
                     any(kw in efficacy.lower() for kw in ["倦怠", "疲労", "肝", "解毒"]):
                    candidate['hangover_boost'] = 0.38
                # 生薬配合の胃腸薬（吐き気・胃もたれ対応）- ブースト強化
                elif '胃腸薬' in medicine_type and any(kw in efficacy.lower() for kw in ["生薬", "健胃", "消化"]):
                    # 効能に「二日酔のむかつき」「悪酔のむかつき」が含まれる場合はさらにブースト
                    if any(kw in efficacy.lower() for kw in ["二日酔のむかつき", "悪酔のむかつき"]):
                        candidate['hangover_boost'] = 0.40
                    else:
                        candidate['hangover_boost'] = 0.28

    # 候補の医薬品の種類を集計してログ出力
    medicine_type_counts = {}
    for candidate in candidates:
        medicine_type = candidate.get('medicine_type', '不明')
        medicine_type_counts[medicine_type] = medicine_type_counts.get(medicine_type, 0) + 1
    
    logger.info(f"候補医薬品数: {len(candidates)} (フィルタリング後)")
    logger.info(f"候補医薬品の種類別内訳: {medicine_type_counts}")
    return candidates

def calculate_symptom_match_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状適合度スコアを計算
    """
    import re
    
    def is_word_match(token: str, text: str) -> bool:
        """
        単語境界を考慮したマッチング
        日本語の単語境界を考慮（症状名が独立した単語として存在するかチェック）
        """
        if not token or not text:
            return False
        
        # 症状名が効能テキスト内に存在するかチェック
        if token not in text:
            return False
        
        # 日本語文字の判定関数（助詞・記号を除く）
        def is_japanese_word_char(c: str) -> bool:
            if not c:
                return False
            # 漢字、カタカナのみを単語文字とみなす（ひらがな助詞は境界）
            return ('\u30A0' <= c <= '\u30FF' or  # カタカナ
                    '\u4E00' <= c <= '\u9FFF')    # 漢字
        
        # 症状名の出現位置をすべて取得
        start_positions = []
        start = 0
        while True:
            pos = text.find(token, start)
            if pos == -1:
                break
            start_positions.append(pos)
            start = pos + 1
        
        # 各出現位置で、前後が日本語文字でないことを確認
        for pos in start_positions:
            # 前の文字（存在する場合）
            prev_char = text[pos - 1] if pos > 0 else ''
            # 後の文字（存在する場合）
            next_pos = pos + len(token)
            next_char = text[next_pos] if next_pos < len(text) else ''
            
            # 前後が日本語単語文字でないことを確認
            # （前が文の始まりまたは非単語文字）AND（後が文の終わりまたは非単語文字）
            # ひらがな助詞（の、が、を、に、は、など）や記号（、。）は境界とみなす
            is_valid_start = (pos == 0) or not is_japanese_word_char(prev_char)
            is_valid_end = (next_pos >= len(text)) or not is_japanese_word_char(next_char)
            
            if is_valid_start and is_valid_end:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"✅ 単語境界マッチ: '{token}' found at position {pos} in '{text}'")
                return True
            else:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"❌ 単語境界除外: '{token}' at position {pos} (前:'{prev_char}', 後:'{next_char}')")
        
        return False
    
    症状スコア = 0.0
    症状数 = len(nlu_result.get("symptoms", []))
    
    if 症状数 == 0:
        return 0.0
    
    # 効能テキストを取得
    efficacy_text_raw = candidate.get('efficacy', '')
    if not efficacy_text_raw:
        return 0.0
    
    # 二日酔い特別処理：効能効果に「二日酔」「宿酔」「悪酔」が含まれている場合
    efficacy_lower = efficacy_text_raw.lower()
    hangover_keywords_in_efficacy = ["二日酔", "宿酔", "悪酔"]
    has_hangover_efficacy = any(kw in efficacy_lower for kw in hangover_keywords_in_efficacy)
    
    # NLU結果に「二日酔い」症状が含まれているか確認
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    has_hangover_symptom = any("二日酔" in str(name) for name in symptom_names)
    
    # 二日酔い症状と二日酔い効能が一致する場合、高スコアを付与
    if has_hangover_symptom and has_hangover_efficacy:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"✅ 二日酔い直接マッチ: {candidate.get('product_name', '')} (効能: {efficacy_text_raw[:100]}...)")
        return 0.95  # 二日酔い特化医薬品には高スコア
    
    # 効能テキストを句読点で分割してから正規化
    # 「激しい咳、咽頭痛の緩解」→ 「激しい咳」「咽頭痛の緩解」
    import re
    efficacy_parts_raw = re.split(r'[、。，．,.]', efficacy_text_raw)
    efficacy_parts = [normalize_text(p) for p in efficacy_parts_raw if p.strip()]
    efficacy_parts = [p for p in efficacy_parts if p]
    
    for symptom in nlu_result.get("symptoms", []):
        symptom_name = symptom.get("name")
        if not symptom_name:
            continue
        normalized_symptom = normalize_text(symptom_name)
        if not normalized_symptom:
            continue
        synonym_set = {normalized_symptom}
        dictionary_entry = SYMPTOM_DICTIONARY.get(symptom_name, {})
        for synonym in dictionary_entry.get("synonyms", []):
            normalized_synonym = normalize_text(synonym)
            if normalized_synonym:
                synonym_set.add(normalized_synonym)
        
        # 血の道症・月経異常の双方向マッピング（効能効果テキスト内の専門用語も認識）
        if symptom_name == "月経不順" or "月経不順" in dictionary_entry.get("canonical_name", ""):
            # 効能効果テキスト内の「血の道症」「月経異常」も「月経不順」として認識
            synonym_set.add(normalize_text("血の道症"))
            synonym_set.add(normalize_text("血の道"))
            synonym_set.add(normalize_text("月経異常"))
            synonym_set.add(normalize_text("生理異常"))
        
        # イライラ症状への対応強化（効能効果欄に「ヒステリー」「情緒不安定」「更年期神経症」などが含まれる場合）
        if symptom_name == "イライラ" or "イライラ" in dictionary_entry.get("canonical_name", ""):
            # 効能効果テキスト内の「ヒステリー」「情緒不安定」「更年期神経症」も「イライラ」として認識
            synonym_set.add(normalize_text("ヒステリー"))
            synonym_set.add(normalize_text("情緒不安定"))
            synonym_set.add(normalize_text("更年期神経症"))
            synonym_set.add(normalize_text("神経症状"))
        
        # 各効能パート内でマッチングを試行
        matched = False
        for part in efficacy_parts:
            # 効能効果テキスト内の「血の道症」「月経異常」もチェック（大文字小文字を区別しない）
            part_lower = part.lower()
            if symptom_name == "月経不順" or "月経不順" in dictionary_entry.get("canonical_name", ""):
                if "血の道症" in part_lower or "血の道" in part_lower or "月経異常" in part_lower or "生理異常" in part_lower:
                    matched = True
                    break
            # 効能効果テキスト内の「ヒステリー」「情緒不安定」などもチェック（大文字小文字を区別しない）
            if symptom_name == "イライラ" or "イライラ" in dictionary_entry.get("canonical_name", ""):
                if "ヒステリー" in part_lower or "情緒不安定" in part_lower or "更年期神経症" in part_lower or "神経症状" in part_lower:
                    matched = True
                    break
            if any(is_word_match(token, part) for token in synonym_set):
                matched = True
                break
        
        if matched:
            weight = dictionary_entry.get("weight", 0.5)
            症状スコア += weight
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 症状マッチ: {symptom_name} が効能に含まれています (効能: {efficacy_text_raw})")
        elif DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"❌ 症状マッチなし: {symptom_name} は効能に含まれていません (効能: {efficacy_text_raw})")
    
    # 症状が効能に含まれていない場合の処理
    if 症状スコア == 0.0:
        # 解熱鎮痛薬の場合、発熱やのどの痛みなどの症状に対して一定のスコアを付与
        medicine_type = candidate.get("medicine_type", "")
        if "解熱鎮痛薬" in medicine_type:
            # 解熱鎮痛薬は発熱、頭痛、のどの痛みなどに効果がある
            fever_symptoms = ["発熱", "熱", "高熱", "微熱"]
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            headache_symptoms = ["頭痛"]
            
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            matched_symptom_count = 0
            
            # 月経不順・生理痛関連症状の定義
            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "月経異常", "生理異常", "血の道症"]
            menstrual_keywords = ["生理", "月経", "周期", "遅れ", "来ない", "来ていない", "乱れ", "不順", "異常"]
            
            for symptom_name in symptom_names:
                normalized_symptom = normalize_text(symptom_name)
                # 発熱関連症状
                if any(fever in normalized_symptom or fever in symptom_name for fever in fever_symptoms):
                    matched_symptom_count += 1
                # のど痛み関連症状
                elif any(throat in normalized_symptom or throat in symptom_name for throat in throat_symptoms):
                    matched_symptom_count += 1
                # 頭痛関連症状
                elif any(headache in normalized_symptom or headache in symptom_name for headache in headache_symptoms):
                    matched_symptom_count += 1
                # 月経不順・生理痛関連症状（新規追加）
                elif any(menstrual in normalized_symptom or menstrual in symptom_name for menstrual in menstrual_symptoms):
                    matched_symptom_count += 1
                # 月経不順・生理痛のキーワードマッチ（「生理が遅れている」など）
                elif any(keyword in normalized_symptom or keyword in symptom_name for keyword in menstrual_keywords):
                    matched_symptom_count += 1
            
            if matched_symptom_count > 0:
                # 解熱鎮痛薬は発熱、のどの痛み、頭痛、月経不順・生理痛に効果があるため、一定のスコアを付与
                base_score = 0.45  # 解熱鎮痛薬の基本スコア
                return base_score * (matched_symptom_count / len(symptom_names))
        
        # 外用薬（のど）の場合、のどの痛みに対して一定のスコアを付与
        if "外用薬（のど）" in medicine_type or ("外用薬" in medicine_type and "のど" in medicine_type):
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            
            for symptom_name in symptom_names:
                normalized_symptom = normalize_text(symptom_name)
                if any(throat in normalized_symptom or throat in symptom_name for throat in throat_symptoms):
                    # 外用薬（のど）はのどの痛みに効果があるため、一定のスコアを付与
                    return 0.45
        
        return 0.0
    
    return 症状スコア / 症状数

def calculate_age_fit_score(candidate: Dict, user_info: Dict) -> float:
    """
    年齢適合性スコアを計算
    
    年齢がNoneの場合の処理を修正：
    - 年齢制限がない場合：0.6（年齢不明でも使用可能と判断）
    - 年齢制限が6歳以下：0.65（小児向け、年齢不明でも比較的安全）
    - 年齢制限が12歳以下：0.58（小児向け、年齢不明でも比較的安全）
    - 年齢制限が15歳以上：0.45（成人向け、年齢不明の場合は慎重に）
    """
    age = user_info.get('age')
    age_restriction = candidate.get('age_restriction', '')
    
    # age_imputedフラグがTrueの場合、ageをNoneとして扱う（年齢が不明な場合の処理を適用）
    age_imputed = user_info.get('age_imputed', False)
    if age_imputed:
        age = None
    
    # ageが空文字列や0の場合もNoneとして扱う
    if age == '' or age == 0:
        age = None
    
    # age_restrictionが数値（float/int）の場合も処理
    if isinstance(age_restriction, (int, float)):
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            age_restriction = ''
        else:
            # 数値の場合は文字列に変換して処理
            age_restriction = f"{int(age_restriction)}歳以上"

    min_age_allowed = _extract_min_age_value(age_restriction)
    
    # デバッグログ（INFOレベルでも出力）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"年齢適合性スコア計算: age={age} (type={type(age)}), age_restriction={age_restriction}, min_age_allowed={min_age_allowed}, age is None={age is None}, product_name={candidate.get('product_name', '')}")

    if age is None:
        # 年齢が不明な場合の処理を修正
        # ログと実装の不一致を解消：年齢制限に応じた適切なスコアを返す
        base_score = 0.5
        if min_age_allowed is None:
            # 年齢制限がない場合：年齢不明でも使用可能と判断
            base_score += 0.1  # 0.6
        elif min_age_allowed <= 6:
            # 小児向け（6歳以下）：年齢不明でも比較的安全
            base_score += 0.15  # 0.65
        elif min_age_allowed <= 12:
            # 小児向け（12歳以下）：年齢不明でも比較的安全
            base_score += 0.08  # 0.58
        elif min_age_allowed >= 15:
            # 成人向け（15歳以上）：年齢不明の場合は慎重に
            base_score -= 0.05  # 0.45
        result_score = max(0.0, min(1.0, base_score))
        # INFOレベルでも出力（デバッグログが出力されない問題を解決）
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"年齢適合性スコア（年齢不明）: min_age_allowed={min_age_allowed}, base_score={base_score}, result={result_score}, product_name={candidate.get('product_name', '')}")
        return result_score

    if min_age_allowed is not None and age < min_age_allowed:
        return 0.0

    if age < 15:
        return 0.8 if min_age_allowed and min_age_allowed <= age else 0.6

    # 年齢が15歳以上の場合、年齢制限が15歳以上なら1.0、それ以外は0.9
    if min_age_allowed is not None and min_age_allowed >= 15:
        return 1.0
    elif min_age_allowed is None:
        # 年齢制限がない場合は1.0
        return 1.0
    else:
        # 年齢制限が15歳未満の場合は0.9（成人向けではない）
        return 0.9

def calculate_body_part_match_score(candidate: Dict, user_body_part: Optional[str]) -> float:
    """
    部位マッチングスコアを計算
    
    Args:
        candidate: 候補医薬品の情報
        user_body_part: ユーザーの症状部位（"delicate_area", "scalp", "throat"など）
    
    Returns:
        部位マッチングスコア
        - 部位が一致する場合: 1.0
        - 部位が不一致の場合: -0.5（大幅減点）
        - 部位情報がない場合: 0.0（ペナルティなし、ただし性器周辺の場合は軽いペナルティ）
    """
    if not user_body_part:
        return 0.0
    
    candidate_body_part = _detect_body_part_specificity(candidate)
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    
    # 性器周辺（delicate_area）の症状に対する特別な処理
    if user_body_part == "delicate_area":
        if candidate_body_part == "delicate_area":
            # 性器専用の医薬品は最優先
            return 1.0
        elif candidate_body_part:
            # 他の部位専用の医薬品は大幅減点
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"性器周辺症状に不適切な部位専用医薬品: 候補={candidate_body_part}, "
                    f"製品={candidate.get('product_name', '')}"
                )
            return -0.7  # 通常の-0.5より強いペナルティ
        else:
            # 部位情報がない場合でも、一般的な外用薬（皮膚）には軽いペナルティ
            # 性器周辺は特別な注意が必要なため
            if "外用薬（皮膚）" in medicine_type or "外用" in medicine_type:
                # 刺激の強い成分が含まれている可能性があるため、軽いペナルティ
                ingredients = str(candidate.get('ingredients', '')).lower()
                # 刺激の強い成分のキーワード
                strong_ingredients = ["メントール", "カンフル", "アンモニア", "サリチル酸"]
                has_strong_ingredient = any(ing in ingredients for ing in strong_ingredients)
                
                if has_strong_ingredient:
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"性器周辺症状に刺激の強い外用薬: 製品={candidate.get('product_name', '')}"
                        )
                    return -0.3  # 刺激の強い成分がある場合はペナルティ
                else:
                    return -0.1  # 一般的な外用薬には軽いペナルティ
            else:
                # 外用薬以外の場合はペナルティなし（内服薬など）
                return 0.0
    
    # その他の部位の処理（既存のロジック）
    if not candidate_body_part:
        # 候補に部位情報がない場合はペナルティなし
        return 0.0
    
    if candidate_body_part == user_body_part:
        # 部位が一致する場合
        return 1.0
    else:
        # 部位が不一致の場合、大幅減点
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(
                f"部位不一致: 候補={candidate_body_part}, ユーザー={user_body_part}, "
                f"製品={candidate.get('product_name', '')}"
            )
        return -0.5

def match_symptom_pattern(nlu_result: Dict) -> Optional[Dict]:
    """
    症状パターンをマッチングして、最適化情報を返す（キャッシュ対応）
    
    Args:
        nlu_result: NLU解析結果
    
    Returns:
        マッチしたパターンの最適化情報、またはNone
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return None
    
    symptom_names = [s.get("name") for s in symptoms]
    
    # 症状名の正規化（「疲労感」→「だるさ」など）
    normalized_symptom_names = []
    symptom_mapping = {
        "疲労感": "だるさ",
        "倦怠感": "だるさ",
        "疲れ": "だるさ",
        "だるい": "だるさ",
    }
    for name in symptom_names:
        normalized_name = symptom_mapping.get(name, name)
        if normalized_name != name:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状名を正規化: {name} → {normalized_name}")
        normalized_symptom_names.append(normalized_name)
    
    symptom_set = frozenset(normalized_symptom_names)
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"症状パターンマッチング: 元の症状={symptom_names}, 正規化後={list(symptom_set)}")
    
    # キャッシュキーを作成（正規化後の症状セットを使用）
    cache_key = tuple(sorted(symptom_set))
    
    # キャッシュをチェック
    if cache_key in _symptom_pattern_cache:
        return _symptom_pattern_cache[cache_key]
    
    # 完全一致をチェック
    if symptom_set in SYMPTOM_PATTERN_OPTIMIZATION:
        result = SYMPTOM_PATTERN_OPTIMIZATION[symptom_set]
    else:
        # 部分一致をチェック（症状がパターンのサブセットの場合）
        result = None
        for pattern_symptoms, pattern_info in SYMPTOM_PATTERN_OPTIMIZATION.items():
            if symptom_set.issubset(pattern_symptoms):
                result = pattern_info
                break
    
    # キャッシュに保存
    if len(_symptom_pattern_cache) >= _max_symptom_pattern_cache_size:
        # 最も古いエントリを削除（FIFO方式）
        oldest_key = next(iter(_symptom_pattern_cache))
        del _symptom_pattern_cache[oldest_key]
    
    _symptom_pattern_cache[cache_key] = result
    
    return result

def calculate_ingredient_based_boost(candidate: Dict, nlu_result: Dict, user_info: Dict, user_text: str = "") -> float:
    """
    成分ベースのスコアリング関数
    症状に応じた優先成分が含まれている場合にボーナスを付与
    
    Args:
        candidate: 候補医薬品の情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        user_text: ユーザー入力テキスト（食事との関連性判定用）
    
    Returns:
        成分ベースのボーナススコア（0.0-1.0）
    """
    ingredients = str(candidate.get('ingredients', '')).lower()
    product_name = str(candidate.get('product_name', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    
    if not symptoms:
        return 0.0
    
    boost = 0.0
    user_text_lower = user_text.lower() if user_text else ""
    
    # 胃薬・胃腸薬の症状別成分優先順位
    if '胃腸薬' in medicine_type or '胃薬' in medicine_type:
        # 胃痛の場合
        if "胃痛" in symptom_names:
            # 空腹時痛の判定（キーワード検出と症状ベースの両方）
            is_fasting_pain = any(kw in user_text_lower for kw in ["空腹時", "食前", "食事の前", "お腹が空いた時", "空腹"])
            # キーワードがない場合は症状から推測（胃痛のみの場合は空腹時痛の可能性）
            if not is_fasting_pain and len(symptom_names) == 1 and "胃痛" in symptom_names:
                is_fasting_pain = True  # デフォルトで空腹時痛と推測
            
            if is_fasting_pain:
                # 胃粘膜保護成分を優先（製品名と成分列の両方をチェック）
                for ingredient in STOMACH_MUCOSAL_PROTECTANTS:
                    if ingredient.lower() in ingredients or ingredient.lower() in product_name:
                        boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃痛"]["胃粘膜保護"]["boost"])
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"胃粘膜保護成分ボーナス（空腹時痛）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃痛']['胃粘膜保護']['boost']}")
                        break
            else:
                # 食後痛の場合は制酸薬を優先
                for ingredient in STOMACH_MEDICINE_PRIORITY["胃痛"]["制酸薬"]["ingredients"]:
                    if ingredient.lower() in ingredients:
                        boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃痛"]["制酸薬"]["boost"])
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"制酸薬ボーナス（食後痛）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃痛']['制酸薬']['boost']}")
                        break
        
        # 胸やけの場合
        if "胸やけ" in symptom_names:
            for ingredient in STOMACH_MEDICINE_PRIORITY["胸やけ"]["H2ブロッカー"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, STOMACH_MEDICINE_PRIORITY["胸やけ"]["H2ブロッカー"]["boost"])
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"H2ブロッカーボーナス（胸やけ）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胸やけ']['H2ブロッカー']['boost']}")
                    break
        
        # 胃もたれの場合
        if "胃もたれ" in symptom_names:
            # 健胃消化薬のキーワードを効能効果から検出
            if any(kw in efficacy for kw in STOMACH_MEDICINE_PRIORITY["胃もたれ"]["健胃消化薬"]["ingredients"]):
                boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃もたれ"]["健胃消化薬"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"健胃消化薬ボーナス（胃もたれ）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃もたれ']['健胃消化薬']['boost']}")
        
        # 吐き気の場合
        if "吐き気" in symptom_names:
            for ingredient in STOMACH_MEDICINE_PRIORITY["吐き気"]["制吐薬"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, STOMACH_MEDICINE_PRIORITY["吐き気"]["制吐薬"]["boost"])
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"制吐薬ボーナス（吐き気）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['吐き気']['制吐薬']['boost']}")
                    break
    
    # 便秘薬の成分優先順位
    if "便秘" in symptom_names:
        # 高優先度（安全性重視）
        for ingredient in CONSTIPATION_MEDICINE_PRIORITY["高優先度（安全性重視）"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, CONSTIPATION_MEDICINE_PRIORITY["高優先度（安全性重視）"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"安全性重視便秘薬ボーナス: {candidate.get('product_name', '')} = +{CONSTIPATION_MEDICINE_PRIORITY['高優先度（安全性重視）']['boost']}")
                break
        
        # 中優先度（効果重視だがリスクあり）は既にboostが0.0の場合のみ適用
        if boost == 0.0:
            for ingredient in CONSTIPATION_MEDICINE_PRIORITY["中優先度（効果重視だがリスクあり）"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, CONSTIPATION_MEDICINE_PRIORITY["中優先度（効果重視だがリスクあり）"]["boost"])
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"効果重視便秘薬ボーナス: {candidate.get('product_name', '')} = +{CONSTIPATION_MEDICINE_PRIORITY['中優先度（効果重視だがリスクあり）']['boost']}")
                    break
    
    # 解熱鎮痛薬の成分優先順位
    if '解熱鎮痛薬' in medicine_type:
        # 高優先度（胃に優しい）
        for ingredient in ANALGESIC_PRIORITY["高優先度（胃に優しい）"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, ANALGESIC_PRIORITY["高優先度（胃に優しい）"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"胃に優しい解熱鎮痛薬ボーナス: {candidate.get('product_name', '')} = +{ANALGESIC_PRIORITY['高優先度（胃に優しい）']['boost']}")
                break
        
        # 中優先度（バランス型）
        if boost == 0.0:
            for ingredient in ANALGESIC_PRIORITY["中優先度（バランス型）"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, ANALGESIC_PRIORITY["中優先度（バランス型）"]["boost"])
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"バランス型解熱鎮痛薬ボーナス: {candidate.get('product_name', '')} = +{ANALGESIC_PRIORITY['中優先度（バランス型）']['boost']}")
                    break
    
    # 外用薬（喉）の成分優先順位
    if '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and "のどの痛み" in symptom_names):
        # 高優先度
        for ingredient in THROAT_TOPICAL_PRIORITY["高優先度"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, THROAT_TOPICAL_PRIORITY["高優先度"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（喉）高優先度成分ボーナス: {candidate.get('product_name', '')} = +{THROAT_TOPICAL_PRIORITY['高優先度']['boost']}")
                break
        
        # 中優先度
        if boost == 0.0:
            for ingredient in THROAT_TOPICAL_PRIORITY["中優先度"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, THROAT_TOPICAL_PRIORITY["中優先度"]["boost"])
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"外用薬（喉）中優先度成分ボーナス: {candidate.get('product_name', '')} = +{THROAT_TOPICAL_PRIORITY['中優先度']['boost']}")
                    break
    
    # 切り傷・擦り傷の成分・剤形ベース判定
    if "切り傷" in symptom_names or "擦り傷" in symptom_names:
        # 成分ベース
        for ingredient in WOUND_MEDICINE_PRIORITY["成分"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, WOUND_MEDICINE_PRIORITY["成分"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"切り傷成分ボーナス: {candidate.get('product_name', '')} = +{WOUND_MEDICINE_PRIORITY['成分']['boost']}")
                break
        
        # 剤形ベース
        for form in WOUND_MEDICINE_PRIORITY["剤形"]["forms"]:
            if form in product_name or form in medicine_type:
                boost = max(boost, WOUND_MEDICINE_PRIORITY["剤形"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"切り傷剤形ボーナス: {candidate.get('product_name', '')} = +{WOUND_MEDICINE_PRIORITY['剤形']['boost']}")
                break
    
    # 月経不順・生理痛向けの成分優先順位（新規追加）
    menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom = any(symptom in symptom_names for symptom in menstrual_symptoms)
    
    if has_menstrual_symptom and '解熱鎮痛薬' in medicine_type:
        # ラムールQ、加味逍遙散、命の母ホワイトの製品名ベース識別（最高優先度）
        product_name_lower = product_name.lower()
        efficacy_lower = efficacy.lower()
        
        # ラムールQの識別
        if "ラムールq" in product_name_lower or "ラムールｑ" in product_name_lower:
            boost = max(boost, 0.25)  # ラムールQ専用ボーナス
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ラムールQ製品名ボーナス: {candidate.get('product_name', '')} = +0.25")
        
        # 加味逍遙散の識別
        if "加味逍遙散" in product_name or "カミショウヨウサン" in product_name.upper():
            boost = max(boost, 0.25)  # 加味逍遙散専用ボーナス
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"加味逍遙散製品名ボーナス: {candidate.get('product_name', '')} = +0.25")
        
        # 命の母ホワイトの識別
        if "命の母ホワイト" in product_name or ("命の母" in product_name and "ホワイト" in product_name):
            boost = max(boost, 0.25)  # 命の母ホワイト専用ボーナス
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"命の母ホワイト製品名ボーナス: {candidate.get('product_name', '')} = +0.25")
        
        # 当帰芍薬散を含む医薬品（最高優先度）
        product_name_upper = product_name.upper()
        efficacy_upper = efficacy.upper()
        if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name_upper or "当帰芍薬散" in efficacy:
            boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["高優先度（当帰芍薬散）"]["boost"])
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"当帰芍薬散ボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['高優先度（当帰芍薬散）']['boost']}")
        else:
            # 当帰と芍薬の両方が含まれる場合（高優先度）
            toki_keywords = ["トウキ", "当帰", "とうき", "トウキ末", "トウキ流エキス", "トウキエキス", "トウキ乾燥エキス", "トウキ流エキスＳ", "トウキエキスＳ", "当帰末"]
            shakuyaku_keywords = ["シャクヤク", "芍薬", "しゃくやく", "シャクヤク末", "シャクヤクエキス", "シャクヤク乾燥エキス", "芍薬エキス"]
            
            has_toki = any(kw.lower() in ingredients for kw in toki_keywords)
            has_shakuyaku = any(kw.lower() in ingredients for kw in shakuyaku_keywords)
            
            if has_toki and has_shakuyaku:
                boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["高優先度（当帰+芍薬の組み合わせ）"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"当帰+芍薬組み合わせボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['高優先度（当帰+芍薬の組み合わせ）']['boost']}")
            # 当帰または芍薬単独（中優先度）
            elif has_toki or has_shakuyaku:
                boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["中優先度（当帰または芍薬単独）"]["boost"])
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"当帰または芍薬単独ボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['中優先度（当帰または芍薬単独）']['boost']}")
    
    return boost

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
    # スコアリングユーティリティをインポート
    from scoring_utils import (
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
    
    # 部位マッチングスコアを計算
    user_body_part = nlu_result.get("user_body_part")
    body_part_score = calculate_body_part_match_score(candidate, user_body_part)
    
    # 症状特化型ブーストを計算
    symptom_boost = calculate_symptom_specific_boost(candidate, nlu_result, user_info)
    
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
    
    # リスク成分の減点（複数症状の場合は減点のみ、単一症状の場合は既に除外済み）
    risk_penalty = 0.0
    if candidate.get('risk_ingredient'):
        risk_penalty = candidate.get('risk_penalty', -0.3)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"リスク成分ペナルティ: {candidate.get('risk_ingredient')} = {risk_penalty}")
    
    # 症状パターンマッチングによる最適化ボーナス/ペナルティ
    pattern_bonus = 0.0
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
            product_name_upper = product_name.upper()
            efficacy_lower = efficacy.lower()
            if "加味逍遙散" in product_name or "カミショウヨウサン" in product_name_upper or "加味逍遙散" in efficacy_lower:
                pattern_bonus += bonuses["加味逍遙散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（加味逍遙散）: {product_name} = +{bonuses['加味逍遙散']}")
        
        # 命の母ホワイトの識別とボーナス（月経不順+イライラ）
        if "命の母ホワイト" in bonuses:
            # 製品名または効能効果欄に「命の母ホワイト」「命の母」が含まれる場合にボーナス適用
            efficacy_lower = efficacy.lower()
            if "命の母ホワイト" in product_name or "命の母" in product_name or "命の母" in efficacy_lower:
                pattern_bonus += bonuses["命の母ホワイト"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（命の母ホワイト）: {product_name} = +{bonuses['命の母ホワイト']}")
        
        # 当帰芍薬散の識別とボーナス（月経不順+冷え症）
        if "当帰芍薬散" in bonuses:
            if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name.upper() or "当帰芍薬散" in efficacy:
                pattern_bonus += bonuses["当帰芍薬散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（当帰芍薬散）: {product_name} = +{bonuses['当帰芍薬散']}")
        
        # 桂枝茯苓丸の識別とボーナス（月経不順+ニキビ）
        if "桂枝茯苓丸" in bonuses:
            # 製品名または効能効果欄に「桂枝茯苓丸」が含まれる場合
            has_keishibukuryogan_name = "桂枝茯苓丸" in product_name or "ケイシブクリョウガン" in product_name.upper()
            has_keishibukuryogan_efficacy = "桂枝茯苓丸" in efficacy
            # 効能に「月経不順」「血の道症」が含まれる製品を優先（「打撲症」のみの製品は除外）
            has_menstrual_efficacy = "月経不順" in efficacy or "血の道症" in efficacy or "生理不順" in efficacy
            only_daposho = "打撲症" in efficacy and not has_menstrual_efficacy
            
            if (has_keishibukuryogan_name or has_keishibukuryogan_efficacy) and not only_daposho:
                # 月経不順・血の道症が含まれる場合は追加ボーナス
                if has_menstrual_efficacy:
                    pattern_bonus += bonuses["桂枝茯苓丸"] + 0.05  # 追加ボーナス
                else:
                    pattern_bonus += bonuses["桂枝茯苓丸"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（桂枝茯苓丸）: {product_name} = +{bonuses['桂枝茯苓丸']} (効能: {efficacy[:100]}...)")
        
        # ラムールQの識別とボーナス（月経不順+イライラ）
        if "ラムールQ" in bonuses:
            # 製品名に「ラムールQ」「ラムールＱ」が含まれる場合、または効能効果欄に「血の道症」「月経不順」「更年期障害」が含まれる場合にボーナス適用
            has_ramuruq_name = "ラムールQ" in product_name or "ラムールＱ" in product_name or "ラムールq" in product_name.lower()
            efficacy_lower = efficacy.lower()
            has_ramuruq_efficacy = ("血の道症" in efficacy_lower or "血の道" in efficacy_lower) and ("月経不順" in efficacy_lower or "更年期障害" in efficacy_lower)
            if has_ramuruq_name or has_ramuruq_efficacy:
                pattern_bonus += bonuses["ラムールQ"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ラムールQ）: {product_name} = +{bonuses['ラムールQ']}")
        
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
            from scoring_utils import _is_kampo_or_herbal_medicine
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
                    # 総合感冒薬（喉向き・成分あり）に+0.50のボーナス（強化）
                    throat_bonus = 0.50
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・成分あり）ボーナス: {candidate.get('product_name', '')} = +0.50")
                elif throat_specificity_level == "efficacy_only":
                    # 総合感冒薬（喉向き・効能のみ）に+0.40のボーナス（強化）
                    throat_bonus = 0.40
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・効能のみ）ボーナス: {candidate.get('product_name', '')} = +0.40")
                else:
                    # 一般の総合感冒薬にも+0.30のボーナス（強化：葛根湯より優先するため）
                    throat_bonus = 0.30
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"一般の総合感冒薬ボーナス: {candidate.get('product_name', '')} = +0.30")
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
    
    # ボーナス/ペナルティの影響を制限（スコアのばらつきを確保しつつ、特化医薬品の優位性を保つ）
    # 特化医薬品のボーナスは最大0.30まで許可（症状特化型ブースト、throat_bonus）- 総合感冒薬ボーナス強化のため上限を0.30に変更
    # 不適切な医薬品のペナルティは最大-0.30まで許可（症状特異性ペナルティ、リスク成分ペナルティ）
    # アレルギー関連は中程度の影響（-0.20から+0.20）
    # 解熱鎮痛薬と外用薬（のど）のボーナス上限を0.50に引き上げ（2位・3位優先のため強化）
    if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        limited_throat_bonus = max(-0.20, min(0.50, throat_bonus))  # 解熱鎮痛薬と外用薬（のど）の上限を0.50に引き上げ
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
    
    limited_dosage_form_bonus = max(-0.10, min(0.12, dosage_form_bonus))
    
    # 成分ベースのボーナス
    ingredient_boost = calculate_ingredient_based_boost(candidate, nlu_result, user_info, user_text)
    limited_ingredient_boost = max(0.0, min(0.25, ingredient_boost))  # 最大0.25まで
    
    # 月経不順症状で漢方薬かつ食前・食間への微小な加点（新規追加）
    dosage_timing_boost = 0.0
    menstrual_symptoms_list = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom_list = any(symptom in symptom_names for symptom in menstrual_symptoms_list)
    
    if has_menstrual_symptom_list:
        # 漢方薬の判定
        from scoring_utils import _is_kampo_or_herbal_medicine
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
        
        # ラムールQ、加味逍遙散、命の母ホワイトの優先ボーナス（製品名ベース）
        product_name_lower = product_name.lower()
        if "ラムールq" in product_name_lower or "ラムールｑ" in product_name_lower:
            priority_boost = 0.10  # ラムールQ優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ラムールQ優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif "加味逍遙散" in product_name or "カミショウヨウサン" in product_name.upper():
            priority_boost = 0.10  # 加味逍遙散優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"加味逍遙散優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif "命の母ホワイト" in product_name or ("命の母" in product_name and "ホワイト" in product_name):
            priority_boost = 0.10  # 命の母ホワイト優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"命の母ホワイト優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        
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
    # 月経不順症状がある場合、錠剤ボーナスとビタミン配合ボーナスが追加されるため、上限を引き上げ
    max_dosage_timing_boost = 0.20 if has_menstrual_symptom_list else 0.02
    limited_dosage_timing_boost = max(0.0, min(max_dosage_timing_boost, dosage_timing_boost))
    
    # 漢方薬・生薬製剤の優先度調整（症状パターンごとに異なる処理）
    # adjustment_scoreの計算前に実行する必要がある
    from scoring_utils import _is_kampo_or_herbal_medicine, _is_goreisan
    kampo_adjustment = 0.0
    
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
                    
                    # 中等度以上の場合は大きなペナルティ
                    if nlu_severity in ["中等度", "重度"]:
                        kampo_adjustment = -0.20
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.20")
                    else:
                        kampo_adjustment = -0.10
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.10")
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
                # 二日酔い（頭痛+むくみ+だるさ）の場合、五苓散に+0.20のボーナス
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
                    # 既にpattern_bonusで処理済み
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
    
    # 調整スコア（ボーナス/ペナルティを制限付きで追加）
    # kampo_adjustmentをadjustment_scoreに含める
    # kakkonto_penalty（葛根湯の条件付き推奨ペナルティ）も追加
    adjustment_score = (
        limited_symptom_specificity_penalty +
        limited_risk_penalty +
        limited_throat_bonus +
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
        kakkonto_penalty  # 葛根湯の条件付き推奨ペナルティを追加
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
    if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        # 解熱鎮痛薬と外用薬（のど）の場合、調整スコアの上限を0.30に引き上げ
        if adjustment_score > 0.5:
            scaled_adjustment = 0.30
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"解熱鎮痛薬/外用薬（のど）のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.30")
        else:
            scaled_adjustment = max(-0.30, min(0.30, adjustment_score))
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
    if base_score < 0.45:
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
    
    result = {
        "total_score": raw_score,  # 一時的にraw_scoreを返す（後で正規化される）
        "raw_score": raw_score,  # 元のスコア（表示用）
        "score_breakdown": {
            "symptom_match": symptom_score,
            "efficacy_specificity": efficacy_specificity_score,
            "body_part_match": limited_body_part_score,  # 制限後のbody_part_scoreを保存
            "age_fit": age_score,
            "usage_convenience": usage_score,
            "side_effect_risk": side_effect_score,
            "interaction_risk": interaction_score,
            "symptom_specificity_penalty": limited_symptom_specificity_penalty,  # 制限後の症状特異性ペナルティ
            "risk_ingredient_penalty": limited_risk_penalty,  # 制限後のリスク成分ペナルティ
            "throat_bonus": limited_throat_bonus,  # 制限後のthroat_bonus
            "symptom_specific_boost": limited_symptom_boost,  # 制限後の症状特化型ブースト
            "multi_symptom_bonus": multi_symptom_bonus,  # MULTI_SYMPTOM_COMBINATIONSのボーナス（表示用）
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
    
    # 効能特異性が0.0の場合（症状が効能に全く含まれていない場合）は強いペナルティを適用
    if efficacy_specificity == 0.0:
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
                # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                if efficacy_specificity >= 0.95:
                    penalty = base_penalty * 0.25  # 0.17から0.25に変更（緩和を減らす）
                elif efficacy_specificity >= 0.8:
                    penalty = base_penalty * 0.6   # 0.5から0.6に変更
                elif efficacy_specificity == 0.0:
                    # 効能特異性が0.0の場合は、ベースペナルティを強化
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
                # デフォルトペナルティ（カテゴリ間優先表にない場合）
                base_penalty = -0.3
                # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                if efficacy_specificity >= 0.95:
                    penalty = base_penalty * 0.25  # 0.17から0.25に変更
                elif efficacy_specificity >= 0.8:
                    penalty = base_penalty * 0.6   # 0.5から0.6に変更
                elif efficacy_specificity == 0.0:
                    # 効能特異性が0.0の場合は、ベースペナルティを強化
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
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
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
                    logger.info(f"複数症状ペナルティ適用: combo={combo_key}, medicine_type={medicine_type}, adjustment={adjustment:.2f}, total_adjustment={total_adjustment:.2f}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
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
            logger.info(f"calculate_symptom_specificity_penalty最終結果: {candidate.get('product_name', '')} - total_adjustment={total_adjustment:.2f}, final_penalty={final_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}")
            # 負の値のみを返す（正の値が含まれている場合は0を返す）
            return final_penalty

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

    # 3. 下痢情報がない腹痛単独相談では止瀉薬候補を除外
    validated = _filter_antidiarrheal_without_diarrhea(validated, nlu_result)

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
    
    # 5. スコアが0.0の候補を除外、0.3未満の候補を警告付きで残す
    final_candidates = []
    for candidate in validated:
        score = candidate.get('final_score', 0.0)
        # スコア0の候補を完全に除外
        if score <= 0.0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"⚠️ スコア0の候補を除外: {candidate.get('product_name', '')} (スコア: {score:.3f})")
            continue
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

def generate_symptom_detail_questions_with_gpt(
    user_text: str,
    nlu_result: Dict,
    user_info: Dict,
    client: OpenAI
) -> List[Dict[str, str]]:
    """
    ChatGPTを使用して症状詳細に関する追加質問を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        client: OpenAI client
    
    Returns:
        質問リスト（各質問は{"question": str, "priority": str}の形式）
    """
    if not client:
        return []
    
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return []
    
    symptom_names = [s.get("name", "") for s in symptoms if s.get("name")]
    if not symptom_names:
        return []
    
    # 基本情報の質問を除外するための情報
    basic_info_covered = {
        "age": user_info.get('age') is not None,
        "gender": user_info.get('gender') is not None,
        "pregnant": user_info.get('pregnant') is not None or user_info.get('breastfeeding') is not None,
        "allergies": user_info.get('allergies') is not None and len(user_info.get('allergies', [])) > 0,
        "medications": user_info.get('current_medications') is not None and len(user_info.get('current_medications', [])) > 0,
        "duration": any(s.get('duration_days') is not None for s in symptoms) or user_info.get('symptom_duration_days') is not None
    }
    
    # プロンプトの構築
    prompt = f"""ユーザーの症状に関する追加質問を生成してください。

【ユーザーの入力】
{user_text}

【検出された症状】
{', '.join(symptom_names)}

【既に回答済みの基本情報】
- 年齢: {'回答済み' if basic_info_covered['age'] else '未回答'}
- 性別: {'回答済み' if basic_info_covered['gender'] else '未回答'}
- 妊娠・授乳状態: {'回答済み' if basic_info_covered['pregnant'] else '未回答'}
- アレルギー: {'回答済み' if basic_info_covered['allergies'] else '未回答'}
- 服用中薬: {'回答済み' if basic_info_covered['medications'] else '未回答'}
- 症状の期間: {'回答済み' if basic_info_covered['duration'] else '未回答'}

【指示】
1. 症状の詳細（部位、原因、程度、経過など）に関する質問を生成してください
2. 基本情報（年齢、性別、妊娠状態、アレルギー、服用中薬、期間）に関する質問は生成しないでください
3. 各質問に優先度（critical, important, optional）を付与してください
4. 質問数は適切な数（3-5問程度）にしてください
5. JSON形式で返してください

【出力形式】
[
    {{"question": "質問文", "priority": "critical|important|optional"}},
    ...
]
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは医薬品推奨システムの質問生成アシスタントです。症状の詳細を把握するための適切な質問を生成してください。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300  # 300トークンに削減（処理時間短縮）
        )
        
        result = response.choices[0].message.content.strip()
        
        # JSONブロックを除去
        if result.startswith('```json'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]
        result = result.strip()
        
        # JSONをパース
        import json
        questions = json.loads(result)
        
        # 形式を検証
        validated_questions = []
        for q in questions:
            if isinstance(q, dict) and "question" in q and "priority" in q:
                priority = q.get("priority", "optional")
                if priority not in ["critical", "important", "optional"]:
                    priority = "optional"
                validated_questions.append({
                    "question": q.get("question", ""),
                    "priority": priority
                })
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ChatGPTで生成された症状詳細質問: {len(validated_questions)}件")
        
        return validated_questions
        
    except Exception as e:
        logger.warning(f"ChatGPTによる質問生成でエラーが発生しました: {e}")
        return []


def check_missing_information(user_info: Dict, nlu_result: Dict, user_text: str = "", client: Optional[OpenAI] = None) -> Dict:
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
    
    # ChatGPTによる症状詳細質問の生成（簡略化版：必須情報のみ）
    # 症状が検出され、かつ必須情報（年齢、性別）が不足している場合のみGPT呼び出し
    if client and user_text and symptoms:
        # 必須情報の不足をチェック
        has_critical_missing = (
            user_info.get('age') is None or 
            user_info.get('gender') is None or
            (user_info.get('gender') == '女性' and user_info.get('pregnant') is None)
        )
        
        # 必須情報が不足している場合のみGPT呼び出し（処理時間短縮）
        if has_critical_missing:
            try:
                symptom_detail_questions = generate_symptom_detail_questions_with_gpt(
                    user_text, nlu_result, user_info, client
                )
                
                # 質問を優先度に応じて分類
                for q_dict in symptom_detail_questions:
                    question = q_dict.get("question", "")
                    priority = q_dict.get("priority", "optional")
                    
                    if question:
                        missing_info["has_missing_info"] = True
                        missing_info["missing_fields"].append("symptom_detail")
                        
                        if priority == "critical":
                            missing_info["critical_questions"].append(question)
                            if missing_info["priority"] != "critical":
                                missing_info["priority"] = "critical"
                        elif priority == "important":
                            missing_info["questions"].append(question)
                            if missing_info["priority"] not in ["critical", "important"]:
                                missing_info["priority"] = "important"
                        else:
                            missing_info["questions"].append(question)
                            if missing_info["priority"] == "optional":
                                missing_info["priority"] = "optional"
            except Exception as e:
                logger.warning(f"症状詳細質問生成でエラーが発生しました: {e}")
    
    return missing_info

# ================================================================================
# 5.5 やけどの程度判定関数
# ================================================================================

def detect_burn_severity(user_text: str) -> Tuple[Optional[str], bool]:
    """
    やけどの程度を判定
    
    Args:
        user_text: ユーザー入力テキスト
    
    Returns:
        (severity: "軽度"/"中等度"/"重度"/None, is_doctor_referral: bool)
        severityがNoneの場合はやけどではない
        is_doctor_referralがTrueの場合は医師受診を推奨
    """
    user_text_lower = user_text.lower()
    
    # やけど関連キーワードのチェック
    burn_keywords = ["やけど", "火傷", "熱傷", "やけ", "火傷", "熱傷"]
    has_burn_keyword = any(kw in user_text_lower for kw in burn_keywords)
    
    if not has_burn_keyword:
        return None, False
    
    # 重度判定キーワード（ガードレール）- 即座に受診勧奨
    severe_keywords = BURN_SEVERITY_KEYWORDS["severe"]
    for keyword in severe_keywords:
        if keyword in user_text_lower:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"やけどの重度キーワード検出（ガードレール）: {keyword}")
            return "重度", True
    
    # 軽度・中等度はNLUで判定されるため、ここではデフォルトで軽度として扱う
    # 実際の判定はNLUフェーズで行われる
    return "軽度", False

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
    # 重要: SYMPTOM_DICTIONARYに登録されているすべての症状に対応するキーワードを網羅的に追加
    # これにより、考慮漏れによって推奨処理が停止することを防ぐ
    medical_keywords = [
        # 基本キーワード（必須）
        "痛", "熱", "咳", "鼻", "喉", "頭", "胃", "下痢", "便秘", "吐", "めまい",
        "かゆ", "発疹", "不眠", "疲労", "症状", "病気", "薬", "医", "病",
        
        # 風邪関連症状（SYMPTOM_DICTIONARYから抽出）
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
        "点眼", "点鼻", "点耳"
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

    # 小児用医薬品フィルタリング（15歳以上のユーザーにも適用）
    user_age = scoring_user_info.get('age')
    if user_age is not None and user_age >= 15:
        # 15歳以上のユーザーには小児専用製品を除外
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
                    logger.info(f"二日酔いが検出されたため、乗り物酔い薬を{before_motion_filter - after_motion_filter}件除外しました")
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
        from scoring_utils import calculate_efficacy_specificity_score
        symptom_score = calculate_symptom_match_score(candidate, nlu_result)
        efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
        age_score = calculate_age_fit_score(candidate, user_info)
        
        # 簡易版の症状特異性ペナルティ（複数症状時の薬効調整）
        symptom_penalty = 0.0
        symptoms = nlu_result.get("symptoms", [])
        symptom_names = [s.get("name") for s in symptoms]
        medicine_type = candidate.get("medicine_type", "")
        
        # 症状パターンマッチングによる最適化ボーナス
        pattern_bonus = 0.0
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
        # 症状パターンボーナスと二日酔いブーストも追加
        quick_score_result = (symptom_score * 0.5 + efficacy_score * 0.3 + age_score * 0.2 + symptom_penalty + pattern_bonus + hangover_quick_boost)
        
        # 解熱鎮痛薬と外用薬（のど）のquick_score計算の詳細をログ出力（DEBUGレベル）
        if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"quick_score計算詳細: medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}, symptom_score={symptom_score:.3f}, efficacy_score={efficacy_score:.3f}, age_score={age_score:.3f}, symptom_penalty={symptom_penalty:.3f}, pattern_bonus={pattern_bonus:.3f}, hangover_boost={hangover_quick_boost:.3f}, quick_score={quick_score_result:.3f}")
        
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
    
    # 解熱鎮痛薬と外用薬（のど）を優先的に詳細スコアリングに含める
    # 「のど痛み+発熱」パターンの場合、解熱鎮痛薬と外用薬（のど）を確実に含める
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    has_throat_and_fever = "のどの痛み" in symptom_names and "発熱" in symptom_names
    
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
    
    # ステップ5.2.5: Min-Max正規化のための最大値・最小値を計算
    raw_scores = [c.get('raw_score', 0.0) for c in [c for _, c in top_candidates_for_scoring]]
    if raw_scores:
        min_raw_score = min(raw_scores)
        max_raw_score = max(raw_scores)
        score_range = max_raw_score - min_raw_score
        
        # 各候補に対してMin-Max正規化を適用
        import math
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
                    normalized_score = 0.4  # 最低限の推奨可能スコア
                else:
                    normalized_score = 0.0
            else:
                # Min-Max正規化: (raw_score - min) / (max - min)
                if score_range > 0:
                    min_max_normalized = (raw_score - min_raw_score) / score_range
                else:
                    # 全て同じスコアの場合、1.0に設定
                    min_max_normalized = 1.0 if raw_score > min_threshold else 0.0
                
                # 非線形変換（平方根）で差を拡大
                normalized_score = math.sqrt(min_max_normalized) if min_max_normalized >= 0.0 else 0.0
                # 0.0-1.0の範囲にクリップ
                normalized_score = min(1.0, max(0.0, normalized_score))
            
            candidate['final_score'] = normalized_score
            candidate['normalization_info'] = {
                'min_raw_score': min_raw_score,
                'max_raw_score': max_raw_score,
                'score_range': score_range
            }
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"Min-Max正規化適用: raw_score範囲 [{min_raw_score:.3f}, {max_raw_score:.3f}], 範囲幅: {score_range:.3f}")
    
    # ステップ5.3: 詳細スコアリング（選別された候補のみ）
    candidates_sorted = sorted([c for _, c in top_candidates_for_scoring], 
                              key=lambda x: x['final_score'], reverse=True)
    
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
                logger.info(f"スコア差が僅差（{score_diff:.3f}）のため、指定第2類医薬品を優先しました")
    
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
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"肩こり外用薬の最適解を優先しました: {optimal_candidate.get('product_name')} (スコア差: {score_diff:.3f})")
                        break
    
    top_candidates = ensure_ingredient_diversity(candidates_sorted, top_n=top_n, nlu_result=nlu_result)
    
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
                    # スコア帯の判定（高/中/低）
                    if relative_score >= 0.9:
                        candidate['score_level'] = '高'
                    elif relative_score >= 0.7:
                        candidate['score_level'] = '中'
                    else:
                        candidate['score_level'] = '低'
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"相対スコア: {candidate.get('product_name', '')} = {candidate.get('relative_score', 0.0):.3f} ({candidate.get('score_level', '')})")
        
        # 相対スコア計算後、スコアの降順で再ソート（順位を最適度の降順に統一）
        top_candidates = sorted(top_candidates, key=lambda x: x.get('final_score', 0.0), reverse=True)
    
    # ステップ5.5: 推奨後の検証処理
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5.5: 推奨後の検証処理 ---")
    validated_candidates = _finalize_recommendations(top_candidates, nlu_result, influenza_risk)
    
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
            "score_level": candidate.get('score_level', '中'),  # スコア帯（高/中/低）
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
   - 年齢制限が複雑な表現（「1歳以下は1／12量以下」「15歳以下8歳まで：1／2量」など）を含む場合は、「年齢制限: 用法用量を参照してください」と記載してください
   - 単純な表現（「15歳以上」「7歳以上」など）の場合は、そのまま記載してください
4. ドーピング: I列に「禁止物質あり」がある場合のみ記載

【出力形式】
効能: [全文]

用法用量の注意:
・[この医薬品特有の注意1]
・[この医薬品特有の注意2]

年齢制限: [ある場合のみ、複雑な表現の場合は「年齢制限: 用法用量を参照してください」]

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
            max_tokens=300  # 400から300に削減（処理時間短縮）
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
    
    # バッチ処理用のプロンプト（簡潔化で処理時間短縮）
    prompt = "医薬品情報:\n\n"
    
    for med_info in medicines_info:
        prompt += f"{med_info['number']}. {med_info['product_name']}\n"
        prompt += f"効能: {med_info['efficacy']}\n"
        prompt += f"用法: {med_info['usage'][:200]}\n"  # 用法は200文字まで（処理時間短縮）
        if med_info['age_restriction']:
            prompt += f"年齢制限: {med_info['age_restriction']}\n"
        if med_info['doping_prohibited']:
            prompt += f"禁止物質: {med_info['doping_prohibited']}\n"
        prompt += "\n"
    
    prompt += """JSON形式で出力:
{
  "medicines": [
    {
      "number": 1,
      "product_name": "製品名",
      "usage_notes": "効能: [全文]\\n\\n用法用量の注意:\\n・[重要な注意2項目以内]\\n\\n[年齢制限・ドーピング情報]"
    }
  ]
}

ルール: 効能は全文、用法用量注意は2項目以内、重要情報のみ記載。
年齢制限が複雑な表現（「1歳以下は1／12量以下」「15歳以下8歳まで：1／2量」など）を含む場合は、「年齢制限: 用法用量を参照してください」と記載してください。"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "登録販売者として、効能は全文、用法用量注意は2項目以内で簡潔に。年齢制限が複雑な場合は「年齢制限: 用法用量を参照してください」と記載。JSON形式で出力。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 0.2から0.1に削減（より決定論的で高速）
            max_tokens=600,  # 800から600に削減（処理時間短縮）
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # 個別の使用上の注意を整形
        individual_notes = []
        medicines_dict = {m['number']: m for m in result_json.get('medicines', [])}
        
        for i, med in enumerate(recommended_medicines, 1):
            med_result = medicines_dict.get(i)
            
            # 刺激性下剤の警告を動的に追加
            ingredients = str(med.get('ingredients', '')).lower()
            usage_notes = med_result.get('usage_notes', '') if med_result else ''
            
            # 刺激性下剤が含まれているかチェック
            has_irritant_laxative = any(
                ingredient.lower() in ingredients 
                for ingredient in IRRITANT_LAXATIVE_INGREDIENTS
            )
            
            if has_irritant_laxative:
                # 既存のusage_notesに警告が含まれていない場合のみ追加（重複チェック）
                warning_text = "刺激性下剤が含まれています"
                if warning_text not in usage_notes and "連用" not in usage_notes:
                    warning_html = '<strong>⚠️ 重要：</strong>本品には刺激性下剤が含まれています。連用により耐性が生じる可能性があるため、3日以上の連用は避けてください。症状が続く場合は医師にご相談ください。'
                    # 既存のusage_notesの後に追加
                    if usage_notes:
                        usage_notes = usage_notes + '\n\n' + warning_html
                    else:
                        usage_notes = warning_html
                    
                    if med_result:
                        med_result['usage_notes'] = usage_notes
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"刺激性下剤の警告を追加: {med.get('product_name', '')}")
            if med_result:
                individual_note = med_result.get('usage_notes', '')
            else:
                # フォールバック: 個別生成関数を使用
                individual_note = generate_individual_usage_notes_with_gpt(med, client)
            
            # 年齢制限の表示（G列から）
            # ChatGPTが生成した年齢制限情報を優先し、コード側で生成した年齢制限表示は複雑な表現の場合のみスキップ
            age_restriction = med.get('age_restriction', '')
            age_restriction_display = ''
            
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            
            # 複雑な表現かどうかを判定（分数表現、複数の年齢制限が含まれる場合など）
            is_complex_age_restriction = False
            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                # 分数表現（1／12量、1/12量など）が含まれる場合は複雑と判定
                import re
                if re.search(r'\d+[／/]\d+量', age_restriction):
                    is_complex_age_restriction = True
                # 「歳以下」と「量」が同時に含まれている場合（「1歳以下は1／12量」など）
                elif '歳以下' in age_restriction and '量' in age_restriction:
                    is_complex_age_restriction = True
                # 複数の年齢制限が含まれる場合（「15歳以下8歳まで：1／2量」など）
                elif len(re.findall(r'\d+歳', age_restriction)) >= 2:
                    is_complex_age_restriction = True
            
            # 複雑な表現でない場合のみ、コード側で年齢制限表示を生成
            if not is_complex_age_restriction:
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
            # ChatGPTが生成した年齢制限情報が含まれていない場合のみ、コード側で生成した年齢制限表示を追加
            # 複雑な表現の場合は、ChatGPTが生成した情報を優先（コード側の表示はスキップ）
            if age_restriction_display and age_restriction_display not in individual_note and not is_complex_age_restriction:
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
            
            # 刺激性下剤の警告を動的に追加（フォールバック処理）
            ingredients = str(med.get('ingredients', '')).lower()
            has_irritant_laxative = any(
                ingredient.lower() in ingredients 
                for ingredient in IRRITANT_LAXATIVE_INGREDIENTS
            )
            
            if has_irritant_laxative:
                # 既存のusage_notesに警告が含まれていない場合のみ追加（重複チェック）
                warning_text = "刺激性下剤が含まれています"
                if warning_text not in individual_note and "連用" not in individual_note:
                    warning_html = '<strong>⚠️ 重要：</strong>本品には刺激性下剤が含まれています。連用により耐性が生じる可能性があるため、3日以上の連用は避けてください。症状が続く場合は医師にご相談ください。'
                    # 既存のusage_notesの後に追加
                    if individual_note:
                        individual_note = individual_note + '\n\n' + warning_html
                    else:
                        individual_note = warning_html
                    
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"刺激性下剤の警告を追加（フォールバック）: {med.get('product_name', '')}")
            
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
    # user_infoにuser_body_partを追加（性器周辺症状の特別な注意書きのため）
    enhanced_user_info = user_info.copy()
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part:
        enhanced_user_info['user_body_part'] = user_body_part
    
    general_notes = generate_default_usage_notes_and_consultation(recommended_medicines, enhanced_user_info)
    
    # 性器周辺症状の場合、特別な注意書きを追加
    if user_body_part == "delicate_area":
        delicate_area_note = "\n\n【性器周辺の症状について】\n性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。特に、以下の場合はすぐに医師にご相談ください：\n・症状が3日以上続く場合\n・症状が悪化する場合\n・発疹、水ぶくれ、ただれなどの症状がある場合\n・性行為のパートナーにも症状がある場合"
        doctor_consultation = general_notes['doctor_consultation'] + delicate_area_note
    else:
        doctor_consultation = general_notes['doctor_consultation']
    
    # 個別の注意 + 共通の注意を結合
    usage_notes_combined = usage_notes_individual + '\n\n' + general_notes['usage_notes']
    
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
    
    # 性器周辺症状の特別な注意書き（user_infoから取得可能な場合）
    if user_info.get('user_body_part') == "delicate_area":
        doctor_consultation_parts.insert(1, "・性器周辺の症状は、性感染症や皮膚疾患の可能性があります。市販薬の使用前に医師の診察を受けることを強く推奨します。")
        doctor_consultation_parts.insert(2, "・性器周辺のかゆみ、発疹、痛みなどの症状が続く場合は、早めに医師にご相談ください。")
    
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
