"""診断名のユーザー向け表示（略称に正式名称をかっこ書きで付与）。"""
from __future__ import annotations

import re

# 検出リストに含まれる英字略称 → ユーザー向けの正式名称
DIAGNOSIS_ABBREVIATION_LABELS: dict[str, str] = {
    "ADHD": "注意欠如・多動性障害",
    "AIDS": "後天性免疫不全症候群",
    "AIH": "自己免疫性肝炎",
    "ALS": "筋萎縮性側索硬化症",
    "AMD": "加齢黄斑変性",
    "AN": "神経性無食欲症",
    "ASD": "自閉症スペクトラム",
    "BED": "過食性障害",
    "BN": "神経性過食症",
    "BPD": "境界性パーソナリティ障害",
    "BPH": "良性前立腺肥大症",
    "BPPV": "良性発作性頭位めまい症",
    "CIDP": "慢性炎症性脱髄性多発根神経炎",
    "CKD": "慢性腎臓病",
    "COPD": "慢性閉塞性肺疾患",
    "CPTSD": "複雑性PTSD",
    "DVT": "深部静脈血栓症",
    "FD": "機能性ディスペプシア",
    "GAD": "全般性不安障害",
    "GERD": "胃食道逆流症",
    "HIV": "ヒト免疫不全ウイルス感染症",
    "IBD": "炎症性腸疾患",
    "IBS": "過敏性腸症候群",
    "IC": "間質性膀胱炎",
    "IPF": "特発性肺線維症",
    "ITP": "免疫性血小板減少症",
    "LD": "学習障害",
    "MCI": "軽度認知障害",
    "MCTD": "混合性結合組織病",
    "MS": "多発性硬化症",
    "NAFLD": "非アルコール性脂肪性肝疾患",
    "NASH": "非アルコール性脂肪性肝炎",
    "OCD": "強迫性障害",
    "OSAS": "閉塞性睡眠時無呼吸症候群",
    "PCOS": "多嚢胞性卵巣症候群",
    "PE": "肺血栓塞栓症",
    "PBC": "原発性胆汁性胆管炎",
    "PTSD": "心的外傷後ストレス障害",
    "RA": "関節リウマチ",
    "RLS": "レストレスレッグス症候群",
    "SAD": "社交不安障害",
    "SAS": "睡眠時無呼吸症候群",
    "SLE": "全身性エリテマトーデス",
    "TTP": "血栓性血小板減少性紫斑病",
    "UC": "潰瘍性大腸炎",
}

_ABBREV_PATTERN = re.compile(r"^[A-Z0-9]{2,6}$")


def format_diagnosis_user_label(name: str) -> str:
    """略称なら「略称（正式名称）」、それ以外はそのまま返す。"""
    text = (name or "").strip()
    if not text:
        return text
    expanded = DIAGNOSIS_ABBREVIATION_LABELS.get(text)
    if expanded:
        return f"{text}（{expanded}）"
    if _ABBREV_PATTERN.match(text):
        return text
    return text


def format_diagnosis_user_label_quoted(name: str) -> str:
    return f"「{format_diagnosis_user_label(name)}」"


def join_diagnosis_user_labels(names: list[str]) -> str:
    """複数診断名を読点区切りで連結（各要素に略称展開を適用）。"""
    labels = [format_diagnosis_user_label(n) for n in names if (n or "").strip()]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return "、".join(labels[:-1]) + "、" + labels[-1]
