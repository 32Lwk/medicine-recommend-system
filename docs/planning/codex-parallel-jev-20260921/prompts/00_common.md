# 共通制約（全エージェント）

リポジトリ: `D:/Programing/medicine-recommend`
作業日: 2026-09-21
目的: Jev（TypeSafe System One）導入の仮説検証・評価分析・計画策定。**本番接続の実装コード変更はしない**（解析・評価・計画・評価スクリプト拡張案まで可）。

## 必読
- `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`（§2, §4–8）
- `docs/planning/JEV_INTRODUCTION_ANALYSIS_2026-09-20.md`
- `scripts/eval_jev_intent_router_10.py`
- `tests/fixtures/jev_intent_router_eval_10.yaml`
- `log/analysis/jev_intent_router_eval_10_20260921_013619.{json,md}`
- `log/analysis/jev_intent_router_eval_10_20260921_013452.{json,md}`

## 確定方針（変更禁止）
- 精度優先。速度・コストは精度を落とさない範囲のみ。
- adapter mode は `jev:minimal` 一本化。`with_baseline_triage` は破棄。
- 環境変数は `JEV_API_KEY`。現状 local のみ。精度検証後に dev から。
- state: channel + user_input + 直近5 turn + 短い構造化メタ。baseline_triage_hint / 識別子 / 不要PII / RAG全文は送らない。
- timeout 3.5s。retry は 429/5xx のみ最大1回。timeout/4xx はリトライしない。
- Emergency/Security/medical_examination FN=0。Jev単独確定禁止。二重ゲート必須。
- token-cost 目標: IntentRouter primary 後 `dialogue.intent_router_llm` の OpenAI cost ≥70% 削減。
- SessionOps は最初の primary 対象外。
- 回答生成・推薦ランキング本体は Jev 対象外。

## 作業ルール
- 仮説は「主張 / 根拠 / 検証方法 / 合格条件 / 失敗時の次手」で書く。
- 数値は既存ログ・再評価・コードから根拠付き。推測は推測と明示。
- 成果物は Markdown。指定パスに書く。
- `.env` の秘密値を出力・コミットしない。キー有無だけ述べる。
- git commit / push / 本番設定変更はしない。
- 担当スコープ外は触れず、他エージェント向け「依頼メモ」に回す。
- 日本語で成果物を書く。
