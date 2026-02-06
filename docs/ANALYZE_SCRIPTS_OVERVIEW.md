# 推奨医薬品分析スクリプト

## 統合スクリプト: `analyze_recommendations.py`

従来の4本のスクリプト（analyze_recommendations, _detailed, _comprehensive, analyze_test_recommendations）を1本に統合しました。

### 使い方

```bash
# すべてのレポートを出力（要約・薬剤師・詳細・包括）
python analyze_recommendations.py --report all

# 要約のみ（要約テキスト + recommendation_analysis.csv）
python analyze_recommendations.py --report summary

# 薬剤師レポート（簡易）のみ
python analyze_recommendations.py --report pharmacist

# 詳細レポートのみ
python analyze_recommendations.py --report detailed

# 包括レポート（ボーナススコア・優位性）のみ
python analyze_recommendations.py --report comprehensive

# ログ・CSV・出力先を指定
python analyze_recommendations.py --log log/test.log --csv data/otc_medicine_data.csv -o ./out --report all
```

### 出力ファイル

| --report      | 出力ファイル |
|---------------|--------------|
| summary       | recommendation_summary.txt, recommendation_analysis.csv |
| pharmacist    | pharmacist_analysis_report.md |
| detailed      | pharmacist_detailed_analysis_report.md |
| comprehensive | pharmacist_comprehensive_analysis_report.md |

### ログ形式

複数のログ形式に対応しています。

- **形式A**: `test_N|入力テキスト|`, `症状検出完了: ...`, `推奨医薬品: ...`
- **形式B**: `test_xxx`, `推奨医薬品: ...`, `症状: ...`

その他、`analyze_test_log_recommendations.py` は役割が重複しているため廃止済みです。必要なら上記の `--report summary` で同様の集計が得られます。
