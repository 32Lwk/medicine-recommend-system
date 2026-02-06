"""
ログファイルの解析モジュール

複数のログ形式に対応し、推奨医薬品・ボーナススコア等を抽出する。
"""
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# 医薬品名抽出用パターン（詳細レポート用）
MEDICINE_PATTERNS = [
    r'カロナール[ＡA]?', r'ロキソニン[ＳS]?[^テパゲロ]', r'ロキソニン[ＳS]?テープ',
    r'ロキソニン[ＳS]?パップ', r'ロキソニン[ＳS]?ゲル', r'ロキソニン[ＳS]?ローション',
    r'タイレノール', r'ノーシン[^ピ]', r'ノーシンピュア', r'バファリン', r'イブ[^A]', r'イブA錠',
    r'エキセドリン', r'セデス', r'ナロン', r'ラックル', r'リングルアイビー', r'リングル',
    r'パブロン', r'ルル', r'コンタック', r'ストナ', r'新ルル', r'ベンザブロック',
    r'プレコール', r'トランサミン', r'トラネキサム酸',
]

# ボーナススコア抽出用パターン（包括レポート用）: (pattern, medicine_name)
BONUS_PATTERNS = [
    (r'主要解熱鎮痛薬ボーナス.*?カロナール[ＡA]\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'カロナールＡ'),
    (r'主要解熱鎮痛薬ボーナス.*?タイレノール\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'タイレノール'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳ'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]プレミアム\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳプレミアム'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]クイック\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳクイック'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]テープ\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳテープ'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]パップ\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳパップ'),
    (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]ゲル\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳゲル'),
]


def parse_log_format_a(log_path: Path) -> List[Dict]:
    """形式A: test_N|input|, 症状検出完了:, 推奨医薬品:"""
    recommendations = []
    current_test, current_input = None, None
    current_symptoms, current_medicines = None, None

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            test_match = re.search(r'test_(\d+)\|(.+?)\|', line)
            if test_match:
                current_test = test_match.group(1)
                current_input = test_match.group(2)
                current_symptoms = None
                current_medicines = None
                continue

            symptom_match = re.search(r'症状検出完了: (.+?)(?: \(処理時間|$)', line)
            if symptom_match:
                s = symptom_match.group(1)
                current_symptoms = [x.strip() for x in s.split(',')] if s != "該当なし" else []
                continue

            medicine_match = re.search(r'推奨医薬品: (.+?)(?:$|処理時間)', line)
            if medicine_match:
                m = medicine_match.group(1)
                current_medicines = [x.strip() for x in m.split(',')] if m != "該当なし" else []
                if current_test and current_input:
                    recommendations.append({
                        'test_number': current_test,
                        'input': current_input,
                        'symptoms': current_symptoms or [],
                        'medicines': current_medicines or [],
                    })
    return recommendations


def parse_log_format_b(log_path: Path) -> List[Dict]:
    """形式B: test_xxx, 推奨医薬品:, 症状: など"""
    recommendations = []
    current_test, current_input = None, None
    current_symptoms = []

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('test_'):
                match = re.search(r'test_(\w+)', line)
                if match:
                    current_test = match.group(1)
            if '推奨医薬品:' in line or 'recommendations' in line.lower():
                medicine_match = re.search(r'推奨医薬品:\s*(.+)', line)
                if medicine_match:
                    medicines = [x.strip() for x in medicine_match.group(1).strip().split(',')]
                    recommendations.append({
                        'test_number': current_test or '',
                        'input': current_input or '',
                        'symptoms': current_symptoms.copy(),
                        'medicines': medicines,
                    })
            if '症状:' in line or 'symptom:' in line.lower():
                symptom_match = re.search(r'症状[：:]\s*(.+)', line)
                if symptom_match:
                    current_symptoms.append(symptom_match.group(1).strip())
    return recommendations


def parse_log_unified(log_path: Path) -> List[Dict]:
    """複数形式を試し、得られた結果をマージ（重複は test_number+input で簡易除外）"""
    ra = parse_log_format_a(log_path)
    rb = parse_log_format_b(log_path)
    seen = set()
    out = []
    for r in ra + rb:
        key = (r.get('test_number'), (r.get('input') or '')[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    if not out and rb:
        out = rb
    elif not out:
        out = ra
    return out


def extract_medicine_names_from_log(log_path: Path) -> Tuple[List[Dict], List[str]]:
    """ログから医薬品名を正規表現で抽出（詳細レポート用）"""
    test_contexts = []
    names = set()
    current_test = None

    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'test_' in line and '(' in line:
            m = re.search(r'test_(\w+)', line)
            if m:
                current_test = m.group(1)
        for pattern in MEDICINE_PATTERNS:
            for m in re.finditer(pattern, line):
                name = m.group(0)
                names.add(name)
                test_contexts.append({'test_case': current_test, 'medicine': name, 'line': i + 1})
    return test_contexts, list(names)


def extract_bonus_scores_from_log(log_path: Path) -> Dict[str, List[float]]:
    """ログからボーナススコアを抽出（包括レポート用）"""
    bonus_scores = defaultdict(list)
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            for pattern, medicine_name in BONUS_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    bonus_scores[medicine_name].append(float(match.group(1)))
    return dict(bonus_scores)
