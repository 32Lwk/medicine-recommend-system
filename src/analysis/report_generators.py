"""
レポート生成モジュール

推奨医薬品分析の各レポート（要約、薬剤師、詳細、包括）を生成する。
"""
import logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


def _find_medicine_in_data(medicine_df: Optional[pd.DataFrame], medicine_name: str) -> pd.DataFrame:
    """医薬品データから該当製品を検索"""
    if medicine_df is None:
        return pd.DataFrame()
    base = medicine_name.split('（')[0].split('[')[0]
    return medicine_df[
        medicine_df['製品名'].str.contains(base, na=False, regex=False)
    ]


def generate_summary_report(
    output_dir: Path,
    recommendations: List[Dict],
    medicine_df: Optional[pd.DataFrame],
) -> None:
    """要約レポート + CSV 出力"""
    medicine_frequency = Counter()
    symptom_to_medicines = defaultdict(list)
    medicine_details = {}

    for rec in recommendations:
        medicines = rec.get('medicines') or []
        if not medicines:
            continue
        for medicine in medicines:
            medicine_frequency[medicine] += 1
            for symptom in rec.get('symptoms') or []:
                symptom_to_medicines[symptom].append(medicine)

    if medicine_df is not None:
        for medicine_name, count in medicine_frequency.most_common(50):
            rows = medicine_df[medicine_df['製品名'] == medicine_name]
            if not rows.empty:
                row = rows.iloc[0]
                medicine_details[medicine_name] = {
                    'frequency': count,
                    'manufacturer': row.get('メーカー名', ''),
                    'category': row.get('分類', ''),
                    'medicine_type': row.get('医薬品の種類', ''),
                    'efficacy': row.get('効能効果', ''),
                    'ingredients': row.get('成分', ''),
                }

    top_medicines = medicine_frequency.most_common(30)
    total_tests = len(recommendations)
    tests_with_recommendations = sum(1 for r in recommendations if r.get('medicines'))

    report = []
    report.append("=" * 80)
    report.append("推奨医薬品分析レポート")
    report.append("=" * 80)
    report.append(f"\n総テストケース数: {total_tests}")
    report.append(f"推奨医薬品が生成されたケース: {tests_with_recommendations}")
    report.append("\n最も頻繁に推奨される医薬品 TOP 30")
    report.append("=" * 80)
    for i, (medicine, count) in enumerate(top_medicines, 1):
        report.append(f"{i}. {medicine}: {count}回")
        if medicine in medicine_details:
            d = medicine_details[medicine]
            report.append(f"   メーカー: {d['manufacturer']} 分類: {d['category']}")
    report.append("\n症状別推奨医薬品パターン")
    report.append("=" * 80)
    for symptom, medicines in sorted(symptom_to_medicines.items(), key=lambda x: -len(x[1]))[:20]:
        cnt = Counter(medicines)
        report.append(f"\n【{symptom}】")
        for med, c in cnt.most_common(5):
            report.append(f"  - {med}: {c}回")

    text = "\n".join(report)
    out_path = output_dir / "recommendation_summary.txt"
    out_path.write_text(text, encoding='utf-8')
    logger.info(f"要約レポート保存: {out_path}")

    detailed_data = []
    for rec in recommendations:
        for i, medicine in enumerate(rec.get('medicines') or [], 1):
            detailed_data.append({
                'test_number': rec.get('test_number', ''),
                'input': rec.get('input', ''),
                'symptoms': ', '.join(rec.get('symptoms') or []),
                'rank': i,
                'medicine_name': medicine,
            })
    if detailed_data:
        df = pd.DataFrame(detailed_data)
        csv_path = output_dir / "recommendation_analysis.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSV保存: {csv_path}")
    print("\n" + text)


def generate_pharmacist_report(
    output_dir: Path,
    recommendations: List[Dict],
    medicine_df: Optional[pd.DataFrame],
) -> None:
    """薬剤師視点レポート（簡易）"""
    medicine_counts = Counter()
    for r in recommendations:
        for m in r.get('medicines') or []:
            medicine_counts[m] += 1

    report = []
    report.append("=" * 80)
    report.append("薬剤師視点からの推奨医薬品分析レポート")
    report.append("=" * 80)
    report.append("\n## 1. 推奨頻度の高い医薬品トップ20\n")
    for i, (name, count) in enumerate(medicine_counts.most_common(20), 1):
        report.append(f"{i}. {name}: {count}回推奨")

    type_counts = Counter()
    for medicine_name, count in medicine_counts.items():
        matches = _find_medicine_in_data(medicine_df, medicine_name)
        if len(matches) > 0:
            mtype = matches.iloc[0].get('医薬品の種類', '不明')
            type_counts[mtype] += count
        else:
            type_counts['不明'] += count
    report.append("\n## 2. 医薬品の種類別推奨状況\n")
    for t, c in type_counts.most_common():
        report.append(f"- {t}: {c}回")

    report.append("\n## 3. 主要推奨医薬品の詳細\n")
    for name, count in medicine_counts.most_common(10):
        report.append(f"### {name} (推奨回数: {count})")
        matches = _find_medicine_in_data(medicine_df, name)
        if len(matches) > 0:
            m = matches.iloc[0]
            report.append(f"- メーカー: {m.get('メーカー名', '不明')}")
            report.append(f"- 分類: {m.get('分類', '不明')}")
            report.append(f"- 効能効果: {(m.get('効能効果') or '')[:100]}...")
        report.append("")

    path = output_dir / "pharmacist_analysis_report.md"
    path.write_text("\n".join(report), encoding='utf-8')
    logger.info(f"薬剤師レポート保存: {path}")


def generate_detailed_report(
    output_dir: Path,
    detailed_contexts: List[Dict],
    medicine_df: Optional[pd.DataFrame],
    log_path: Path,
) -> None:
    """薬剤師視点詳細レポート（医薬品名パターン抽出ベース）"""
    medicine_counts = Counter(c['medicine'] for c in detailed_contexts)

    report = []
    report.append("=" * 100)
    report.append("薬剤師視点からの推奨医薬品詳細分析レポート")
    report.append("=" * 100)
    report.append(f"\n分析日時: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    report.append(f"分析対象ログ: {log_path.name}\n")
    report.append("## 1. 推奨頻度の高い医薬品ランキング\n")
    report.append("| 順位 | 医薬品名 | 推奨回数 | メーカー | 分類 | 種類 |")
    report.append("|------|---------|---------|---------|------|------|")
    for i, (name, count) in enumerate(medicine_counts.most_common(30), 1):
        matches = _find_medicine_in_data(medicine_df, name)
        if len(matches) > 0:
            m = matches.iloc[0]
            report.append(f"| {i} | {name} | {count} | {m.get('メーカー名', '')} | {m.get('分類', '')} | {m.get('医薬品の種類', '')} |")
        else:
            report.append(f"| {i} | {name} | {count} | - | - | - |")
    report.append("\n## 2. 主要推奨医薬品の詳細分析（薬剤師視点）\n")
    for name, count in medicine_counts.most_common(20):
        report.append(f"### {name} (推奨回数: {count})\n")
        matches = _find_medicine_in_data(medicine_df, name)
        if len(matches) > 0:
            m = matches.iloc[0]
            report.append(f"**基本情報**\n- メーカー: {m.get('メーカー名', '不明')}\n- 分類: {m.get('分類', '不明')}\n")
            eff = m.get('効能効果', '') or ''
            report.append(f"**効能効果**\n{eff[:500]}{'...' if len(eff) > 500 else ''}\n")
            ing = m.get('成分', '') or ''
            for line in (ing.split('\n') or [ing])[:10]:
                if line.strip():
                    report.append(f"- {line.strip()}")
            report.append("")
        report.append("---\n")

    path = output_dir / "pharmacist_detailed_analysis_report.md"
    path.write_text("\n".join(report), encoding='utf-8')
    logger.info(f"詳細レポート保存: {path}")


def generate_comprehensive_report(
    output_dir: Path,
    bonus_scores: Dict[str, List[float]],
    medicine_df: Optional[pd.DataFrame],
    log_path: Path,
) -> None:
    """包括レポート（ボーナススコア・優位性）"""
    report = []
    report.append("=" * 100)
    report.append("薬剤師視点からの推奨医薬品包括的分析レポート")
    report.append("=" * 100)
    report.append(f"\n分析日時: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    report.append(f"分析対象ログ: {log_path.name}\n")
    report.append("## 1. 主要解熱鎮痛薬の推奨理由分析\n")
    major = ['カロナールＡ', 'タイレノール', 'ロキソニンＳ', 'ロキソニンＳプレミアム', 'ロキソニンＳクイック']
    for medicine_name in major:
        if medicine_name not in bonus_scores:
            continue
        matches = _find_medicine_in_data(medicine_df, medicine_name)
        if len(matches) == 0:
            continue
        med_info = matches.iloc[0]
        scores = bonus_scores[medicine_name]
        bonus = scores[0] if scores else 0
        report.append(f"### {medicine_name} (ボーナススコア: +{bonus})\n")
        report.append(f"**基本情報**\n- メーカー: {med_info.get('メーカー名', '不明')}\n- 分類: {med_info.get('分類', '不明')}\n")
        ingredients = str(med_info.get('成分', ''))
        if 'アセトアミノフェン' in ingredients:
            report.append("- アセトアミノフェン含有により、胃への負担が少なく安全性が高い\n")
        if 'イブプロフェ' in ingredients or 'ロキソプロフェン' in ingredients:
            report.append("- NSAIDs含有により、抗炎症作用があり痛みや熱に効果的\n")
        eff = str(med_info.get('効能効果', ''))
        if eff and eff != 'nan':
            report.append(f"**効能効果**\n{eff[:300]}{'...' if len(eff) > 300 else ''}\n")
        report.append("---\n")
    report.append("## 2. ボーナススコアによる優先順位付け\n")
    for name, scores in sorted(bonus_scores.items(), key=lambda x: -(x[1][0] if x[1] else 0)):
        avg = sum(scores) / len(scores) if scores else 0
        report.append(f"- **{name}**: +{avg:.1f} (推奨回数: {len(scores)}回)")
    report.append("")

    path = output_dir / "pharmacist_comprehensive_analysis_report.md"
    path.write_text("\n".join(report), encoding='utf-8')
    logger.info(f"包括レポート保存: {path}")
