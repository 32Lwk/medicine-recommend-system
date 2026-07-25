# AWS CloudWatch ログ分析（medicine-recommend staging）

GCP Cloud Logging 解析（`gcp-log-analysis` スキル）の AWS 版。ECS ステージング（`/ecs/medicine-recommend`・`aws.medicine.yutok.dev`）の CloudWatch エクスポート JSON を解析する。

## クイックスタート

```bash
# 差分取得 + 解析準備（任意）
.venv/bin/python scripts/prepare_aws_log_analysis.py

# エクスポート JSON からセクション抽出
.venv/bin/python scripts/analyze_aws_logs.py log/raw/downloaded-aws-logs-*.json

# 統合レポート（multitask エージェント併用時）
# → log/analysis/YYYY-MM-DD_downloaded-aws-logs-*.md
```

## 主要パス

| 種別 | パス |
|------|------|
| エクスポート | `scripts/export_aws_logs.py` |
| 解析 CLI | `scripts/analyze_aws_logs.py` |
| 差分 prepare | `scripts/prepare_aws_log_analysis.py` |
| パーサ | `src/analysis/aws_cloudwatch_log_parser.py` |
| セッション分析 | `src/analysis/session_conversation_analysis.py`（`side_effect_qa_mishandled` 等） |
| スキル | `.cursor/skills/aws-log-analysis/SKILL.md` |
| 成果物 | `log/analysis/downloaded-aws-logs-*/` |

## NLU/ルーティング改善との連携

2026-07-25 の AWS ログ深掘りで特定したゴールデン 6 セッションは、ローカル再検証用 YAML に移植済み:

- `tests/fixtures/v2_golden_aws_6_sessions.yaml`
- `python scripts/local_v2_chat_test_runner.py --scenarios-path tests/fixtures/v2_golden_aws_6_sessions.yaml`

関連 CHANGELOG: **NLU/ルーティング統合（Unified Pipeline）** セクション。
