#!/usr/bin/env python3
"""
ログファイルから推奨医薬品を分析する統合スクリプト

複数のログ形式に対応し、以下のレポートを生成可能:
  summary       - 要約レポート + recommendation_analysis.csv
  pharmacist    - 薬剤師視点レポート（簡易）pharmacist_analysis_report.md
  detailed      - 薬剤師視点詳細レポート pharmacist_detailed_analysis_report.md
  comprehensive - ボーナススコア・優位性分析 pharmacist_comprehensive_analysis_report.md
  all           - 上記すべて

使用例:
  python analyze_recommendations.py --report all
  python analyze_recommendations.py --report summary --output-dir ./out
  python analyze_recommendations.py --log log/test.log --csv data/otc_medicine_data.csv --report pharmacist
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.analysis.log_parsers import (
    parse_log_unified,
    extract_medicine_names_from_log,
    extract_bonus_scores_from_log,
)
from src.analysis.report_generators import (
    generate_summary_report,
    generate_pharmacist_report,
    generate_detailed_report,
    generate_comprehensive_report,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RecommendationAnalyzer:
    """統合分析クラス（データ読み込みとオーケストレーション）"""

    def __init__(self, log_path: Path, csv_path: Path, output_dir: Path):
        self.log_path = log_path
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.medicine_df: Optional[pd.DataFrame] = None
        self.recommendations: List[Dict] = []
        self.bonus_scores: Dict[str, List[float]] = {}
        self.detailed_contexts: List[Dict] = []

    def load_medicine_data(self) -> None:
        """OTC医薬品データを読み込み"""
        logger.info("医薬品データを読み込み中...")
        self.medicine_df = pd.read_csv(self.csv_path, encoding='utf-8')
        logger.info(f"医薬品データ読み込み完了: {len(self.medicine_df)}件")

    def load_log(self) -> None:
        """ログを解析して推奨リストを取得"""
        logger.info("ログファイルを解析中...")
        self.recommendations = parse_log_unified(self.log_path)
        logger.info(f"解析完了: {len(self.recommendations)}件のテストケース")

    def load_bonus_scores(self) -> None:
        """ボーナススコアを抽出"""
        self.bonus_scores = extract_bonus_scores_from_log(self.log_path)
        logger.info(f"ボーナススコア: {len(self.bonus_scores)}種類の医薬品")

    def load_detailed_contexts(self) -> None:
        """詳細レポート用に医薬品名をログから抽出"""
        self.detailed_contexts, _ = extract_medicine_names_from_log(self.log_path)
        logger.info(f"詳細抽出: {len(self.detailed_contexts)}件")

    def run_report_summary(self) -> None:
        """要約レポート + CSV 出力"""
        generate_summary_report(
            self.output_dir,
            self.recommendations,
            self.medicine_df,
        )

    def run_report_pharmacist(self) -> None:
        """薬剤師視点レポート（簡易）"""
        generate_pharmacist_report(
            self.output_dir,
            self.recommendations,
            self.medicine_df,
        )

    def run_report_detailed(self) -> None:
        """薬剤師視点詳細レポート（医薬品名パターン抽出ベース）"""
        if not self.detailed_contexts:
            self.load_detailed_contexts()
        generate_detailed_report(
            self.output_dir,
            self.detailed_contexts,
            self.medicine_df,
            self.log_path,
        )

    def run_report_comprehensive(self) -> None:
        """包括レポート（ボーナススコア・優位性）"""
        if not self.bonus_scores:
            self.load_bonus_scores()
        generate_comprehensive_report(
            self.output_dir,
            self.bonus_scores,
            self.medicine_df,
            self.log_path,
        )


def main():
    parser = argparse.ArgumentParser(
        description='ログから推奨医薬品を分析し、要約・薬剤師・詳細・包括レポートを出力する'
    )
    parser.add_argument('--log', type=Path, default=Path('log/test.log'), help='テストログのパス')
    parser.add_argument('--csv', type=Path, default=Path('data/otc_medicine_data.csv'), help='OTC医薬品CSVのパス')
    parser.add_argument('--output-dir', '-o', type=Path, default=Path('.'), help='レポート出力ディレクトリ')
    parser.add_argument(
        '--report', '-r',
        choices=['summary', 'pharmacist', 'detailed', 'comprehensive', 'all'],
        default='all',
        help='出力するレポート種別 (default: all)'
    )
    args = parser.parse_args()

    if not args.log.exists():
        logger.error(f"ログファイルが見つかりません: {args.log}")
        return 1
    if not args.csv.exists():
        logger.error(f"CSVファイルが見つかりません: {args.csv}")
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = RecommendationAnalyzer(args.log, args.csv, args.output_dir)
    analyzer.load_medicine_data()
    analyzer.load_log()

    reports = args.report if args.report != 'all' else ['summary', 'pharmacist', 'detailed', 'comprehensive']
    if 'summary' in reports:
        analyzer.run_report_summary()
    if 'pharmacist' in reports:
        analyzer.run_report_pharmacist()
    if 'detailed' in reports:
        analyzer.run_report_detailed()
    if 'comprehensive' in reports:
        analyzer.run_report_comprehensive()

    logger.info("分析完了")
    return 0


if __name__ == '__main__':
    exit(main() or 0)
