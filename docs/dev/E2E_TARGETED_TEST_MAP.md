# E2E 変更領域 → 最小テストマップ

PR / ローカル検証では **フル GPT 30 ペルソナ（120t）を毎回走らせない**。
変更ファイルに応じて下表の **最小ペルソナセット** のみ実行する。

## 実行コマンド例

```powershell
# 固定 YAML のみ（GPT sim なし・低コスト）
python scripts/local_v2_chat_test_runner.py --limit 10 --report-suffix smoke

# 変更関連 GPT ペルソナのみ
python scripts/local_v2_chat_test_runner.py --skip-yaml --use-gpt-user `
  --personas-path tests/fixtures/v2_gpt_retry_failures_3.yaml --sessions 3 --turns-per-session 4
```

## 変更領域マップ

| 変更パス（glob） | 最小 GPT ペルソナ | ターン | 固定 YAML 追加 |
|------------------|-------------------|--------|----------------|
| `medicine_response_builder.py`, `medicine_qa_routing.py` | sports-prep, allergy-check, travel-medicine | 12 | comparison / interaction |
| `reco_followup_signals.py`, `reco_dedup.py` | correction-user, implicit-short | 8 | pivot-fix |
| `conversation_followup_resolver.py` | medicine-anaphora, returning-thread | 8 | — |
| `medicine_discovery_routing.py`, `chat_post_pipeline.py` (triage) | vague-to-specific, allergy-check | 8 | cold-start |
| `e2e_gpt_user_sim.py` | teen-slang | 4 | — |
| `llm_triage.py`, `chat_triage.py` | vague-to-specific, emotional-distress | 8 | triage smoke |
| CI / workflow のみ | — | 0 | `pytest` unit only |

## コスト目安

| スコープ | LLM 呼出（概算） | 時間 |
|----------|------------------|------|
| unit pytest | 0 | <2min |
| YAML smoke 10 | ~30 | ~5min |
| targeted GPT 2〜3 ペルソナ | ~40 | ~8min |
| GPT 30 フル | ~500 | ~29min |

## ベースライン

- **月次**: `v2_gpt_expanded_personas_30.yaml` フル（精度 KPI）
- **PR**: 上表 targeted + golden PR 20（YAML）
- **latency**: `--limit 10` GPT sim なし、`report-suffix latency-*`
