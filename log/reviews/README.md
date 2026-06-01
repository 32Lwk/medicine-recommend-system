# 推奨評価レポート（medicine-recommendation-advisor）

本ディレクトリは **エージェントによる推奨品質評価** の保存先です。`log/` 全体は `.gitignore` 対象のため、ローカル・CI 成果物として残します。

## ファイル命名

```
log/reviews/YYYY-MM-DD_<slug>_<sessionId-or-caseId>.md
```

例: `log/reviews/2026-06-02_cold-productive-cough_GC-COLD-004.md`

## 必須セクション（テンプレート）

評価完了後、以下を含む Markdown を **必ず** 1 ファイル保存する:

1. メタデータ（日時, case ID, session_id, 入力, user_info）
2. 判定（適切 / 要改善 / 受診優先）
3. データ照合表（上位3品 × CSV × PMDA × CureBell Tier1.5）
4. スコア・NLU 所見
5. 学会ガイドライン参照（該当時）
6. 分類（algorithm bug / data inconsistency / clinical edge）
7. 推奨アクション

テンプレート本体: [../../.cursor/skills/medicine-recommendation-advisor/references/evaluation-report-template.md](../../.cursor/skills/medicine-recommendation-advisor/references/evaluation-report-template.md)
