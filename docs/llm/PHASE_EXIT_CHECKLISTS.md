# Phase 出口チェックリスト（薬剤師レビュー用）

## Phase 0（P0-13）

- [ ] `scripts/baseline_llm_metrics.py` で P50/P95/セッションコストを記録
- [ ] `LLM_GPT_RECOMMEND_FALLBACK=false`（本番）
- [ ] ゴールデン 40 件（P16/E10/A6/Em4/O4）が `tests/fixtures/golden/sample_cases.jsonl` に存在
- [ ] `/admin/llm_settings` で文案・アラートメールを設定済み
- [ ] 月額 5 万円 hard_stop 動作確認

## Phase 1（P1-11）

- [ ] `LLM_MODEL_PROFILE=gpt5` またはカナリアで triage/NLU が動作
- [ ] `pytest tests/llm/test_llm_phase1.py` パス
- [ ] ゴールデン triage カテゴリ一致率がベースライン ±2pt 以内（手動または CI）

## Phase 2（P2-14）

- [ ] `chat.completions` 直呼びゼロ（`llm_client` のみ）
- [ ] `docs/llm/LLM_ROLLBACK.md` 手順で切り戻し可能
- [ ] match@3（推奨3件）ゴールデンで 100%（薬剤師監修分）

## Phase 3（P3-12）

- [ ] `LLM_AGENT_ENABLED` + `LLM_AGENT_CANARY_PERCENT` で段階ロールアウト
- [ ] `tests/integration/test_safety_regression.py` 50 件パス
- [ ] rule_based のみがランキングを返すこと（PhysicalOrchestrator）
- [ ] KPI: レイテンシ・コスト・安全性の月次レビュー
