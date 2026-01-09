import re
from typing import Dict, List, Optional, Tuple, Set, FrozenSet
from utils.text_utils import normalize_text
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# デバッグモード（デフォルト）
DEBUG_MODE = False

# キーワードリストのインポート
try:
    from config.keywords import URGENT_SYMPTOM_KEYWORDS
except ImportError:
    # フォールバック（開発環境などでconfig/keywords.pyが存在しない場合）
    URGENT_SYMPTOM_KEYWORDS = []
    logging.warning("config/keywords.pyが見つかりません。URGENT_SYMPTOM_KEYWORDSを使用できません。")


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
    },
    "茯苓": {
        "canonical_name": "茯苓",
        "synonyms": ["ブクリョウ", "茯苓", "ぶくりょう", "ブクリョウ末", "ブクリョウエキス", "茯苓末"],
        "effects": ["利水作用", "むくみ改善", "精神安定", "不安緩和"],
        "related_symptoms": ["月経不順", "むくみ", "イライラ", "不安"],
        "medicine_types": ["漢方薬"]
    },
    "牡丹皮": {
        "canonical_name": "牡丹皮",
        "synonyms": ["ボタンピ", "牡丹皮", "ぼたんぴ", "ボタンピ末", "ボタンピエキス", "牡丹皮末"],
        "effects": ["血行改善", "瘀血除去", "炎症緩和", "精神安定"],
        "related_symptoms": ["月経不順", "生理痛", "イライラ", "ニキビ"],
        "medicine_types": ["漢方薬"],
        "contraindications": ["妊娠中"]  # 妊娠中は禁忌
    },
    "桃仁": {
        "canonical_name": "桃仁",
        "synonyms": ["トウニン", "桃仁", "とうにん", "トウニン末", "トウニンエキス", "桃仁末"],
        "effects": ["血行改善", "瘀血除去", "便秘改善"],
        "related_symptoms": ["月経不順", "生理痛", "便秘"],
        "medicine_types": ["漢方薬"],
        "contraindications": ["妊娠中"]  # 妊娠中は禁忌（子宮収縮作用のリスク）
    },
    "桂枝": {
        "canonical_name": "桂枝",
        "synonyms": ["ケイヒ", "桂枝", "けいひ", "ケイヒ末", "ケイヒエキス", "桂枝末"],
        "effects": ["血行改善", "冷え性改善", "発汗作用"],
        "related_symptoms": ["月経不順", "冷え性", "生理痛"],
        "medicine_types": ["漢方薬"]
    },
    "柴胡": {
        "canonical_name": "柴胡",
        "synonyms": ["シャクヨウ", "柴胡", "しゃくよう", "シャクヨウ末", "シャクヨウエキス", "柴胡末"],
        "effects": ["精神安定", "イライラ緩和", "ストレス緩和", "気の流れ改善"],
        "related_symptoms": ["月経不順", "イライラ", "ストレス", "不安"],
        "medicine_types": ["漢方薬"]
    },
    "甘草": {
        "canonical_name": "甘草",
        "synonyms": ["カンゾウ", "甘草", "かんぞう", "カンゾウ末", "カンゾウエキス", "甘草末"],
        "effects": ["痛み緩和", "炎症緩和", "精神安定"],
        "related_symptoms": ["月経不順", "生理痛", "イライラ"],
        "medicine_types": ["漢方薬"]
    },
    "大黄": {
        "canonical_name": "大黄",
        "synonyms": ["ダイオウ", "大黄", "だいおう", "ダイオウ末", "ダイオウエキス", "大黄末"],
        "effects": ["便秘改善", "血行改善", "瘀血除去"],
        "related_symptoms": ["月経不順", "便秘"],
        "medicine_types": ["漢方薬"],
        "contraindications": ["お腹を壊しやすい", "産後", "授乳中"]  # 下剤作用があるため
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
        "synonyms": ["打撲", "打ち身", "青あざ", "あおたん", "内出血", "あざ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "打ち身": {
        "canonical_name": "打ち身",
        "synonyms": ["打ち身", "打撲", "青あざ", "あおたん", "内出血", "あざ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["外用薬（皮膚）"],
        "weight": 0.9
    },
    "炎症": {
        "canonical_name": "炎症",
        "synonyms": ["炎症", "炎症している", "炎症する", "にえる", "にえている"],
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
    "眠気": {
        "canonical_name": "眠気",
        "synonyms": [
            "眠い", "眠気", "だるい", "眠たい", "眠気が強い", "いつも眠い",
            "寝てしまう", "眠くて寝てしまう", "眠すぎて寝てしまう",
            "仕事中に寝てしまう", "居眠り", "眠くてたまらない",
            "眠気に襲われる", "眠くて仕方がない", "眠すぎる"
        ],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["睡眠障害"],  # データベース上では睡眠障害カテゴリに分類
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

# URGENT_SYMPTOM_KEYWORDSと統合（緊急症状の拡張）
if URGENT_SYMPTOM_KEYWORDS:
    # 既存のRED_FLAG_SYMPTOMSに緊急症状を追加
    if "緊急症状" not in RED_FLAG_SYMPTOMS:
        RED_FLAG_SYMPTOMS["緊急症状"] = []
    # URGENT_SYMPTOM_KEYWORDSの各キーワードを追加
    for keyword in URGENT_SYMPTOM_KEYWORDS:
        if keyword not in RED_FLAG_SYMPTOMS["緊急症状"]:
            RED_FLAG_SYMPTOMS["緊急症状"].append(keyword)

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

def is_comprehensive_cold_medicine(candidate: Dict) -> bool:
    """
    総合風邪薬（総合感冒薬）かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        総合風邪薬の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    
    # 外用薬は総合風邪薬として判定しない
    if medicine_type.startswith('外用薬'):
        return False
    
    # 製品名に外用薬を示すキーワードが含まれている場合は除外
    external_medicine_keywords = ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布', 'のど', '喉']
    if any(kw in product_name for kw in external_medicine_keywords):
        # ただし、「のど」や「喉」が含まれていても、内服薬の場合は総合風邪薬として判定
        # 外用薬のキーワード（スプレー、トローチなど）が含まれている場合は除外
        if any(kw in product_name for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布']):
            return False
    
    # 有名な総合風邪薬のブランド名をチェック（優先順位順）
    # より具体的なブランド名を先にチェック（例：「ルルエース」→「ルル」の順）
    famous_cold_medicine_brands = [
        # ルルシリーズ（「新ルルエース」→「ルルエース」でマッチ）
        "ルルアタック", "ルルエース", "ルルゴールド", "ルルカゼ", "ルル",
        # パブロンシリーズ（総合風邪薬としての「パブロン」は存在しない可能性があるが、念のため）
        "パブロンゴールド", "パブロンエース", "パブロンセレクト", "パブロンメディカル", "パブロン",
        # ベンザブロックシリーズ
        "ベンザブロックs", "ベンザブロックl", "ベンザブロックip", "ベンザブロック",
        # プレコールシリーズ（「新プレコール」→「プレコール」でマッチ）
        "プレコールエース", "プレコール持続性", "プレコール", "プレコー",
        # パイロンシリーズ（「パイロンＰＬ」→「パイロンpl」でマッチ）
        "パイロンpl", "パイロンＰＬ", "パイロンα", "パイロンmk", "パイロンam", "パイロン",
        # その他
        "カゼンエース", "カゼン", "カゼブロック"
    ]
    
    # 製品名に有名な総合風邪薬のブランド名が含まれている場合
    for brand in famous_cold_medicine_brands:
        # ブランド名が製品名に含まれているかチェック（大文字小文字、全角半角を区別しない）
        # 「新ルルエース」→「ルルエース」でマッチ、「パイロンＰＬ」→「パイロンpl」でマッチ
        brand_normalized = brand.lower().replace('ｐ', 'p').replace('ｌ', 'l').replace('ｓ', 's')
        product_name_normalized = product_name.lower().replace('ｐ', 'p').replace('ｌ', 'l').replace('ｓ', 's')
        
        if brand_normalized in product_name_normalized:
            # ブランド名が含まれていても、外用薬のキーワードが含まれている場合は除外
            if any(kw in product_name_normalized for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布', '点鼻']):
                continue
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（ブランド名）: {candidate.get('product_name', '')} (ブランド: {brand})")
            return True
    
    # 総合感冒薬のパターンをチェック
    patterns = COMPOUND_MEDICINE_INDICATORS.get("風邪薬", {}).get("patterns", [])
    for pattern in patterns:
        if pattern.search(product_name) or pattern.search(efficacy):
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（パターンマッチ）: {candidate.get('product_name', '')}")
            return True
    
    # 効能効果に複数の風邪症状が含まれているかチェック
    cold_symptoms = ["発熱", "熱", "解熱", "咳", "鎮咳", "去痰", "鼻水", "鼻炎", "のど", "咽頭", "喉", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "感冒", "かぜ", "せき", "たん"]
    symptom_count = sum(1 for symptom in cold_symptoms if symptom in efficacy)
    
    # 風邪薬の場合、効能効果に2つ以上の風邪症状が含まれていれば総合風邪薬と判定
    if "風邪薬" in medicine_type:
        if symptom_count >= 2:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（複数症状）: {candidate.get('product_name', '')} (症状数: {symptom_count}, 効能: {efficacy[:100]}...)")
            return True
        # 効能効果に「感冒」「かぜ」が含まれている場合も総合風邪薬と判定
        if "感冒" in efficacy or "かぜ" in efficacy:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（感冒キーワード）: {candidate.get('product_name', '')}")
            return True
    
    return False

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

# 成分重複チェック用リスク成分マスター（過剰摂取のリスクが高い成分）
RISK_INGREDIENTS_OVERLAP = {
    # 鎮痛成分
    "アセトアミノフェン": {
        "canonical_name": "アセトアミノフェン",
        "synonyms": ["アセトアミノフェン", "アセトアミノフェン水和物", "パラセタモール"],
        "overlap_warning": True,
        "category": "analgesic",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "アセトアミノフェン",
        "side_effects": ["肝機能障害", "過剰摂取"],
        "max_daily_dose": 4000  # mg（参考値）
    },
    "エテンザミド": {
        "canonical_name": "エテンザミド",
        "synonyms": ["エテンザミド"],
        "overlap_warning": True,
        "category": "analgesic",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "エテンザミド",
        "side_effects": ["過剰摂取"]
    },
    "イブプロフェン": {
        "canonical_name": "イブプロフェン",
        "synonyms": ["イブプロフェン", "イブプロフェン錠"],
        "overlap_warning": True,
        "category": "nsaid",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "イブプロフェン（NSAIDs）",
        "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"],
        "note": "ロキソプロフェン等、他のNSAIDsとの併用は避けてください"
    },
    # 抗ヒスタミン薬（第一世代のみ：眠気の副作用が強いもの）
    "クロルフェニラミン": {
        "canonical_name": "クロルフェニラミン",
        "synonyms": [
            "クロルフェニラミン", "クロルフェニラミンマレイン酸塩",
            "クロルフェニラミン塩酸塩", "d-クロルフェニラミンマレイン酸塩"
        ],
        "overlap_warning": True,
        "category": "antihistamine",
        "severity": "yellow",  # 注意レベル（副作用が強まるが致命的ではない）
        "warning_message": "クロルフェニラミン",
        "side_effects": ["眠気", "口渇", "閉尿"],
        "focus_side_effect": "眠気"
    },
    "ジフェンヒドラミン": {
        "canonical_name": "ジフェンヒドラミン",
        "synonyms": [
            "ジフェンヒドラミン", "ジフェンヒドラミン塩酸塩",
            "ジフェンヒドラミンサリチル酸塩"
        ],
        "overlap_warning": True,
        "category": "antihistamine",
        "severity": "yellow",  # 注意レベル（副作用が強まるが致命的ではない）
        "warning_message": "ジフェンヒドラミン",
        "side_effects": ["眠気", "口渇", "閉尿"],
        "focus_side_effect": "眠気"
    },
    "クレマスチン": {
        "canonical_name": "クレマスチン",
        "synonyms": ["クレマスチン", "クレマスチンフマル酸塩"],
        "overlap_warning": True,
        "category": "antihistamine",
        "severity": "yellow",  # 注意レベル（副作用が強まるが致命的ではない）
        "warning_message": "クレマスチン",
        "side_effects": ["眠気", "口渇", "閉尿"],
        "focus_side_effect": "眠気"
    },
    "プロメタジン": {
        "canonical_name": "プロメタジン",
        "synonyms": [
            "プロメタジン", "プロメタジン塩酸塩",
            "プロメタジンマレイン酸塩"
        ],
        "overlap_warning": True,
        "category": "antihistamine",
        "severity": "yellow",  # 注意レベル（副作用が強まるが致命的ではない）
        "warning_message": "プロメタジン",
        "side_effects": ["眠気", "口渇", "閉尿"],
        "focus_side_effect": "眠気"
    },
    # その他の鎮痛・解熱成分
    "アスピリン": {
        "canonical_name": "アスピリン",
        "synonyms": [
            "アスピリン", "アセチルサリチル酸", "アセチルサリチル酸アルミニウム",
            "アセチルサリチル酸カルシウム", "アセチルサリチル酸リジン"
        ],
        "overlap_warning": True,
        "category": "nsaid",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "アスピリン（サリチル酸系）",
        "side_effects": ["胃腸障害", "出血傾向", "過剰摂取", "ライ症候群（小児）"],
        "max_daily_dose": 4000,  # mg（参考値）
        "note": "他の解熱鎮痛薬との併用不可"
    },
    "ロキソプロフェン": {
        "canonical_name": "ロキソプロフェン",
        "synonyms": [
            "ロキソプロフェン", "ロキソプロフェンナトリウム",
            "ロキソプロフェンナトリウム水和物"
        ],
        "overlap_warning": True,
        "category": "nsaid",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "ロキソプロフェン（NSAIDs）",
        "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"],
        "max_daily_dose": 180,  # mg（参考値）
        "note": "イブプロフェン等、他のNSAIDsとの併用は避けてください"
    },
    "イソプロピルアンチピリン": {
        "canonical_name": "イソプロピルアンチピリン",
        "synonyms": [
            "イソプロピルアンチピリン", "イソプロピルアンチピリン錠"
        ],
        "overlap_warning": True,
        "category": "pyralozone",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "イソプロピルアンチピリン（ピリン系）",
        "side_effects": ["過剰摂取", "アレルギー反応", "顆粒球減少症", "ピリン疹（薬疹）", "ショック"],
        "note": "ピリン系アレルギーの既往がある場合は厳禁"
    },
    "メフェナム酸": {
        "canonical_name": "メフェナム酸",
        "synonyms": [
            "メフェナム酸", "メフェナム酸錠"
        ],
        "overlap_warning": True,
        "category": "nsaid",
        "severity": "red",  # 重複禁止レベル（1日最大摂取量を超える可能性）
        "warning_message": "メフェナム酸（NSAIDs）",
        "side_effects": ["胃腸障害", "過剰摂取", "腎機能障害", "喘息誘発"],
        "note": "ロキソプロフェン、イブプロフェン等、他のNSAIDsとの併用は避けてください"
    },
    # カフェイン（過剰摂取のリスク）
    "カフェイン": {
        "canonical_name": "カフェイン",
        "synonyms": [
            "カフェイン", "無水カフェイン", "カフェイン水和物",
            "クエン酸カフェイン", "安息香酸ナトリウムカフェイン"
        ],
        "overlap_warning": True,
        "category": "xanthine",
        "severity": "yellow",  # 注意レベル（過剰摂取で不眠、動悸など）
        "warning_message": "カフェイン",
        "side_effects": ["不眠", "動悸", "頭痛", "過剰摂取", "振戦", "胃荒れ"],
        "max_daily_dose": 400,  # mg（参考値）
        "note": "風邪薬、鎮痛薬、眠気防止薬、栄養ドリンクでの重複が非常に起きやすい"
    },
    # 鎮咳成分
    "デキストロメトルファン": {
        "canonical_name": "デキストロメトルファン",
        "synonyms": [
            "デキストロメトルファン", "デキストロメトルファン臭化水素酸塩",
            "デキストロメトルファン臭化水素酸塩水和物"
        ],
        "overlap_warning": True,
        "category": "antitussive_non_narcotic",
        "severity": "yellow",  # 注意レベル（過剰摂取で副作用が強まる）
        "warning_message": "デキストロメトルファン",
        "side_effects": ["眠気", "めまい", "過剰摂取", "消化器症状"],
        "note": "非麻薬性だが、重複すると副作用が強く出る"
    },
    "ジヒドロコデイン": {
        "canonical_name": "ジヒドロコデイン",
        "synonyms": [
            "ジヒドロコデイン", "ジヒドロコデインリン酸塩",
            "ジヒドロコデインリン酸塩水和物"
        ],
        "overlap_warning": True,
        "category": "antitussive_narcotic",
        "severity": "red",  # 重複禁止レベル（依存性のリスク）
        "warning_message": "ジヒドロコデイン（麻薬性鎮咳成分）",
        "side_effects": ["依存性", "眠気", "便秘", "過剰摂取", "呼吸抑制"],
        "note": "12歳未満は使用禁止。風邪薬と咳止めで重複しやすい"
    },
    "コデイン": {
        "canonical_name": "コデイン",
        "synonyms": [
            "コデイン", "コデインリン酸塩水和物", "リン酸コデイン"
        ],
        "overlap_warning": True,
        "category": "antitussive_narcotic",
        "severity": "red",  # 重複禁止レベル（依存性のリスク）
        "warning_message": "コデイン類（麻薬性鎮咳成分）",
        "side_effects": ["呼吸抑制", "便秘", "眠気", "依存性"],
        "note": "12歳未満は使用禁止。重複により呼吸抑制リスク増大"
    },
    # 鼻づまり改善成分（交感神経興奮成分）
    "プソイドエフェドリン": {
        "canonical_name": "プソイドエフェドリン",
        "synonyms": [
            "プソイドエフェドリン", "プソイドエフェドリン塩酸塩",
            "dl-プソイドエフェドリン塩酸塩"
        ],
        "overlap_warning": True,
        "category": "sympathomimetic",
        "severity": "red",  # 重複禁止レベル（高血圧・心臓病の人は要注意）
        "warning_message": "プソイドエフェドリン",
        "side_effects": ["不眠", "動悸", "血圧上昇", "過剰摂取", "排尿困難"],
        "note": "鼻炎薬と風邪薬での重複が非常に多い。高血圧・心臓病の人は要注意"
    },
    "メチルエフェドリン": {
        "canonical_name": "メチルエフェドリン",
        "synonyms": [
            "メチルエフェドリン", "dl-メチルエフェドリン塩酸塩",
            "メチルエフェドリンサッカリン塩"
        ],
        "overlap_warning": True,
        "category": "sympathomimetic",
        "severity": "yellow",  # 注意レベル（副作用が強まる）
        "warning_message": "メチルエフェドリン",
        "side_effects": ["動悸", "血圧上昇", "震え"],
        "note": "咳止めや風邪薬に含まれる。交感神経刺激作用の重複に注意"
    },
    # 止血成分
    "トラネキサム酸": {
        "canonical_name": "トラネキサム酸",
        "synonyms": [
            "トラネキサム酸", "トラネキサム酸錠"
        ],
        "overlap_warning": True,
        "category": "hemostatic",
        "severity": "yellow",  # 注意レベル（血栓症のリスク）
        "warning_message": "トラネキサム酸",
        "side_effects": ["血栓症", "過剰摂取"]
    },
    # 脂溶性ビタミン（過剰摂取のリスク）
    "ビタミンA": {
        "canonical_name": "ビタミンA",
        "synonyms": [
            "ビタミンA", "レチノール", "レチノールパルミチン酸エステル",
            "レチノール酢酸エステル", "β-カロテン"
        ],
        "overlap_warning": True,
        "category": "vitamin",
        "severity": "yellow",  # 注意レベル（過剰摂取で肝機能障害など）
        "warning_message": "ビタミンA",
        "side_effects": ["肝機能障害", "頭痛", "過剰摂取"],
        "max_daily_dose": 5000  # IU（参考値）
    },
    "ビタミンD": {
        "canonical_name": "ビタミンD",
        "synonyms": [
            "ビタミンD", "ビタミンD2", "ビタミンD3",
            "エルゴカルシフェロール", "コレカルシフェロール"
        ],
        "overlap_warning": True,
        "category": "vitamin",
        "severity": "yellow",  # 注意レベル（過剰摂取で高カルシウム血症など）
        "warning_message": "ビタミンD",
        "side_effects": ["高カルシウム血症", "腎機能障害", "過剰摂取"],
        "max_daily_dose": 4000  # IU（参考値）
    },
    # 制酸剤（長期併用のリスク）
    "アルミニウム": {
        "canonical_name": "アルミニウム",
        "synonyms": [
            "アルミニウム", "水酸化アルミニウム", "アルミニウムゲル",
            "合成ケイ酸アルミニウム", "ケイ酸アルミニウムマグネシウム",
            "炭酸アルミニウム", "リン酸アルミニウムゲル"
        ],
        "overlap_warning": True,
        "category": "antacid",
        "severity": "yellow",  # 注意レベル（長期併用で便秘、リン吸着など）
        "warning_message": "アルミニウム含有製剤",
        "side_effects": ["便秘", "リン吸着", "長期使用によるリスク"]
    },
    "マグネシウム": {
        "canonical_name": "マグネシウム",
        "synonyms": [
            "マグネシウム", "酸化マグネシウム", "水酸化マグネシウム",
            "炭酸マグネシウム", "ケイ酸アルミニウムマグネシウム"
        ],
        "overlap_warning": True,
        "category": "antacid",
        "severity": "yellow",  # 注意レベル（下痢のリスク）
        "warning_message": "マグネシウム含有製剤",
        "side_effects": ["下痢", "長期使用によるリスク"]
    },
    # その他のリスク成分
    "グアヤコールスルホン酸カリウム": {
        "canonical_name": "グアヤコールスルホン酸カリウム",
        "synonyms": [
            "グアヤコールスルホン酸カリウム", "グアイフェネシン"
        ],
        "overlap_warning": True,
        "category": "expectorant",
        "severity": "yellow",  # 注意レベル（過剰摂取で副作用が強まる）
        "warning_message": "グアヤコールスルホン酸カリウム",
        "side_effects": ["胃腸障害", "過剰摂取"]
    },
    "ブロムヘキシン": {
        "canonical_name": "ブロムヘキシン",
        "synonyms": [
            "ブロムヘキシン", "ブロムヘキシン塩酸塩"
        ],
        "overlap_warning": True,
        "category": "expectorant",
        "severity": "yellow",  # 注意レベル（過剰摂取で副作用が強まる）
        "warning_message": "ブロムヘキシン",
        "side_effects": ["胃腸障害", "過剰摂取"]
    },
    "カルボシステイン": {
        "canonical_name": "カルボシステイン",
        "synonyms": [
            "カルボシステイン", "L-カルボシステイン"
        ],
        "overlap_warning": True,
        "category": "expectorant",
        "severity": "yellow",  # 注意レベル（過剰摂取で副作用が強まる）
        "warning_message": "カルボシステイン",
        "side_effects": ["胃腸障害", "過剰摂取"]
    },
    # 抗コリン成分（鼻水止め・胃痛止め：カテゴリーが違う薬での重複事故が多い）
    "ベラドンナ総アルカロイド": {
        "canonical_name": "ベラドンナ総アルカロイド",
        "synonyms": [
            "ベラドンナ総アルカロイド", "ベラドンナエキス"
        ],
        "overlap_warning": True,
        "category": "anticholinergic",
        "severity": "red",  # 重複禁止レベル（緑内障・前立腺肥大の人はリスク大）
        "warning_message": "ベラドンナ総アルカロイド（抗コリン成分）",
        "side_effects": ["口渇", "便秘", "眼圧上昇", "排尿困難"],
        "note": "鼻炎薬と胃腸鎮痛鎮痙薬での重複が多い。緑内障・前立腺肥大の人はリスク大"
    },
    "ヨウ化イソプロパミド": {
        "canonical_name": "ヨウ化イソプロパミド",
        "synonyms": [
            "ヨウ化イソプロパミド"
        ],
        "overlap_warning": True,
        "category": "anticholinergic",
        "severity": "yellow",  # 注意レベル（副作用が強まる）
        "warning_message": "ヨウ化イソプロパミド（抗コリン成分）",
        "side_effects": ["口渇", "便秘", "眼圧上昇"],
        "note": "鼻炎薬によく含まれる。作用時間が長い"
    },
    "スコポラミン": {
        "canonical_name": "スコポラミン",
        "synonyms": [
            "スコポラミン", "スコポラミン臭化水素酸塩水和物", "ロートエキス"
        ],
        "overlap_warning": True,
        "category": "anticholinergic",
        "severity": "yellow",  # 注意レベル（副作用が強まる）
        "warning_message": "スコポラミン・ロートエキス（抗コリン成分）",
        "side_effects": ["眠気", "口渇", "目のかすみ"],
        "note": "乗り物酔い止め、胃薬、風邪薬での重複に注意"
    },
    # 鎮静成分（依存性や過剰摂取のリスク）
    "ブロモバレリル尿素": {
        "canonical_name": "ブロモバレリル尿素",
        "synonyms": [
            "ブロモバレリル尿素", "ブロムワレリル尿素"
        ],
        "overlap_warning": True,
        "category": "sedative",
        "severity": "red",  # 重複禁止レベル（依存性のリスク）
        "warning_message": "ブロモバレリル尿素（鎮静成分）",
        "side_effects": ["強い眠気", "依存性", "ふらつき"],
        "note": "「アリルイソプロピルアセチル尿素」との重複も鎮静作用増強のため注意"
    },
    "アリルイソプロピルアセチル尿素": {
        "canonical_name": "アリルイソプロピルアセチル尿素",
        "synonyms": [
            "アリルイソプロピルアセチル尿素"
        ],
        "overlap_warning": True,
        "category": "sedative",
        "severity": "yellow",  # 注意レベル（副作用が強まる）
        "warning_message": "アリルイソプロピルアセチル尿素",
        "side_effects": ["眠気", "だるさ"],
        "note": "解熱鎮痛薬によく配合されている。乗り物酔い薬等との重複で眠気が増強"
    }
}
