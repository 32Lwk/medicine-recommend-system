# Jev 進捗確認と今後の実行計画

作成日: 2026-09-21  
対象: `medicine-recommend` / Chat Pipeline v2 / IntentRouter Jev 導入  
位置づけ: 並列Codex成果物 A-F の進捗確認と、次に実装へ進むための実行計画

## 1. 現在の進捗

並列Codexの成果物はすべて生成済み。実装コード、dev設定、本番設定、commit / push はまだ行っていない。

| Agent | 成果物 | 状態 | 要点 |
| --- | --- | --- | --- |
| A | `JEV_HYPOTHESIS_ROUTING_20260921.md` | 完了 | `jev:minimal` 限定採用、`with_baseline_triage` 棄却、高リスク二重ゲート必須 |
| B | `jev_intent_router_eval_cost_latency_20260921.md` | 完了 | `013619` を最新有効値に採用。再計測は接続拒否で不採用 |
| C | `JEV_PHASE1_INSERTION_DESIGN_20260921.md` | 完了 | `resolve_route()` 後置 shadow、legacy decision 不変、bounded worker 方針 |
| D | `JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md` | 完了 | Phase 1 後は Focus -> Eligibility -> triage stage2 -> triage stage1 -> Store |
| E | `JEV_EXECUTION_PLAN_PHASE0-2_20260921.md` | 完了 | Phase 0-2 の依存、ゲート、rollback、監視、未解決質問を整理 |
| F | `JEV_PARALLEL_SYNTHESIS_20260921.md` | 完了 | 精度優先で最終統合。Phase 1 local shadow は Go、dev shadow 以降は No-Go |

補足:

- `logs/*_last_message.md` は A-F すべて完了メッセージあり。
- `logs/*_pid.txt` のプロセスは現時点で稼働していない。
- Git 上は `docs/planning/codex-parallel-jev-20260921/` 全体と `JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`、Jev評価レポートが未追跡。

## 2. 現時点の判定

| 項目 | 判定 | 理由 |
| --- | --- | --- |
| `jev:minimal` adapter 方針 | Go | 10ケース x 3回で 30/30、latency も条件達成 |
| `with_baseline_triage` | No-Go / 廃止 | 10ケース中1件で medicine comparison の sub-route を落とした |
| Phase 1 local shadow 実装 | Go | 本線非干渉の設計が固まった。default OFF で実装できる |
| dev shadow 有効化 | No-Go | expanded safety fixture、live再評価、dev secret/log/rollback準備が未完 |
| primary canary | No-Go | dev shadow 150 eligible decisions、disagreement、FN、fallback監査が未完 |
| staging / production | No-Go | dev primary 未完。別途明示承認が必要 |
| OpenAI token-cost 70%削減 | 未判定 | primary運用ログと `legacy_saved_calls` 実測がまだない |

数値:

- current: 30/30, avg 1456.28ms, P50 1112.62ms, P95 3216.91ms
- `jev:minimal`: 30/30, avg 536.78ms, P50 532.54ms, P95 594.15ms
- 短縮: avg 919.50ms、P95 2622.76ms
- Jev usage: 平均 input 1358.5 tokens / output 367.7 tokens
- Jev概算コスト: 約 $0.000057/call、参考換算で約 0.00896円/call

## 3. 次の全体方針

次は「devに出す」ではなく、「ローカル実装とテストの土台を作る」段階。

最重要方針:

1. Phase 1 は絶対に実行 route を変えない。
2. Jev は `resolve_route()` で legacy decision を確定した後に shadow として呼ぶ。
3. `JEV_INTENT_ROUTER_PRIMARY=true` が誤設定されても Phase 1 コードでは primary 化しない。
4. Emergency / Security / medical_examination は Jev 単独確定禁止。
5. SessionOps は現行 fast-path を維持し、Jev primary 対象にしない。
6. token-cost は OpenAI cost 削減と Jev込み総分類費を分けて測る。

## 4. 実行計画

### Phase 0A: 設計凍結と仕様の最終確定

目的: 実装前にブレやすい契約を固定する。

完了条件:

- `JEV_API_KEY` を唯一の正規 secret 名にする。
- `TYPESAFE_API_KEY` fallback を Phase 1 に入れない方針を確定する。
- adapter mode は `jev:minimal` のみ。
- state allowlist と禁止payloadを固定する。
- `baseline_triage_hint` 非送信を contract test にする。
- timeout 3.5s、retry は 429/5xx のみ最大1回。
- shadow log schema と failure reason enum を固定する。

### Phase 0B: 拡張 fixture の器を作る

目的: 10ケースだけでは不足する高リスク・境界・会話文脈を評価できるようにする。

作成候補:

- `tests/fixtures/jev_intent_router_safety_expanded.yaml`
- `tests/services/test_jev_decisions.py`
- `tests/dialogue/routing/test_jev_router.py`

最低収録:

- Emergency positive / negative / hypothetical / quoted
- Security prompt injection / hard negative
- medical_examination request
- prescription / illegal / controlled drug
- Store + symptom
- SessionOps + high-risk mixed input
- follow-up state none / correct / stale / conflicting

完了条件:

- label owner が期待値をレビューできる形になっている。
- primary と required sub-route の joint accuracy を評価できる。
- high-risk FN を独立集計できる。

### Phase 1A: local shadow adapter 実装

目的: 本線を変えずに Jev decision を観測できるようにする。

変更候補:

- `src/services/jev_client.py`
- `src/services/jev_decisions.py`
- `src/services/jev_metrics.py`
- `src/dialogue/routing/jev_router.py`
- `src/dialogue/routing/router.py`
- `config/llm_flags.py`
- `config/routing_config.py`
- 必要なら `src/dialogue/dispatcher.py`

完了条件:

- default OFF。
- `resolve_route()` は常に legacy decision を返す。
- Jev失敗、timeout、schema不正、log失敗が本線へ伝播しない。
- worker は bounded executor。
- session proxy や生IDではなく immutable snapshot だけを渡す。
- Jev は `_routing_decision`、`_intent_router_shadow`、`last_triage_result` を更新しない。

### Phase 1B: unit / mock integration

目的: API接続なしでも契約を保証する。

必須テスト:

- Choice / Noul / confidence / unknown enum / malformed response
- emergency/security override の shadow DTO 化
- high-risk を低リスクへ降格しない
- state allowlist と禁止field検出
- secret/header/raw response 非出力
- 429/5xx だけ retry、4xx/timeout は retry しない
- flag 全組み合わせで executed route 不変
- shadow ON/OFF で response 差分 0

完了条件:

- unit と mock integration が green。
- legacy routing regression が増えない。
- expanded fixture で joint accuracy 100%、high-risk combined FN=0。

### Phase 1C: live再評価

目的: `013619` の有効値を再現し、接続失敗を除外して精度・速度を再確認する。

実行条件:

- local API接続が安定している。
- `JEV_API_KEY` は値を表示せず、存在のみ確認。
- current と Jev の API接続失敗を accuracy 分母から分離する。

推奨:

- `jev:minimal` のみ。
- 各ケース最低10回。
- current/Jev を交互またはランダム順で実行。
- avg / P50 / P95 / P99 と bootstrap 95% CI を出す。

完了条件:

- 95% CI の保守側でも avg 900ms または P95 2500ms 短縮。
- API error と eval failure が別集計。
- `jev_usage` と cost estimate が出る。

### Phase 1D: dev shadow 準備

目的: dev に出す前の運用準備だけを完了する。まだ有効化しない。

確認項目:

- dev `JEV_API_KEY` の配備方法。
- dev log sink、閲覧権限、保持期間。
- flag 反映方式と最大反映時間。
- rollback 担当と手順。
- shadow log に raw text / secret / 不要PII が残らないこと。

完了条件:

- 明示承認があれば `JEV_ENABLED=true`, `JEV_INTENT_ROUTER_SHADOW=true` にできる状態。
- ただし本書時点では dev shadow 有効化は No-Go のまま。

## 5. dev shadow に進む条件

次をすべて満たしたら、dev shadow 開始を再判定する。

- Phase 1 local 実装が green。
- default OFF で挙動差 0。
- shadow ON でも executed route / response 差分 0。
- expanded fixture 100%。
- high-risk FN=0。
- live再評価が完走。
- `JEV_API_KEY`、log sink、rollback が準備済み。
- 禁止データの state/log 混入 0。

dev shadow 開始後の合格条件:

- eligible decision 最低150件。
- 全体 disagreement <= 0.5%。
- high-risk disagreement は全件レビュー、未解決 0。
- FN=0。
- fallback / usage / latency / log completeness が欠損なく集計可能。

## 6. primary canary に進む条件

Phase 2 は別変更として設計する。Phase 1 完了までは着手しない。

primary canary の最低条件:

- 低リスク route のみ。
- SessionOps 除外。
- Emergency / Security / medical_examination は既存 gate 必須。
- primary confidence だけでなく required sub-route confidence も見る。
- disagreement または low confidence では legacy。
- OpenAI `dialogue.intent_router_llm` cost が基準比70%以上削減。
- Jev込み総分類費も別指標で悪化していないか報告する。

## 7. 未解決質問

実装前に確認したいこと:

1. Phase 1 local shadow 実装に進めてよいか。
2. dev shadow は、local実装とlive再評価が完了するまで明示的に禁止でよいか。
3. `JEV_API_KEY` を唯一の正規名にし、`TYPESAFE_API_KEY` fallback は入れない方針でよいか。
4. expanded fixture の label owner は誰にするか。医療安全系の期待値レビュー担当が必要。
5. shadow log の保存先は既存 JSONL でよいか。それとも専用 `log/jev_intent_router_shadow.jsonl` にするか。
6. Jev に送る直近履歴は「5 turn」で確定してよいか。
7. 商品名メタは最大3件でよいか。stale判定に turn index を持たせるか。
8. dev secret、log閲覧権限、rollback担当は誰が持つか。
9. live再評価は外部API接続が安定する環境で再実行してよいか。
10. `JEV_MODEL=jev-latest` のまま shadow を始めるか、primary 前に version pin を必須にするだけでよいか。

## 8. 直近の推奨タスク順

1. この計画を承認し、Phase 1 local shadow のみ実装許可を出す。
2. `jev_intent_router_safety_expanded.yaml` の初版を作る。
3. `jev_decisions` の pure mapping unit test を先に作る。
4. `jev_client` の retry / timeout / secret非出力 test を作る。
5. `jev_router` の state allowlist / bounded scheduler test を作る。
6. `router.resolve_route()` に default OFF shadow hook を入れる。
7. shadow ON/OFF で executed route 不変の integration を作る。
8. local live再評価を、接続が安定している環境で再実行する。

現在地: **Phase 1 local shadow 実装は計画上 Go。ただし dev shadow、primary canary、staging、production はまだ No-Go。**

## 9. Phase 0 契約凍結ステータス（2026-09-21）

Phase 0 の契約は文書上凍結済み。

- 凍結サマリ: `JEV_PHASE0_CONTRACT_FREEZE_20260921.md`
- Test Plan 同期: `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` §8–§9（joint accuracy、`JEV_API_KEY` のみ、10 シナリオは pilot、`jev:minimal` のみ、PRIMARY 無視、高リスク二重ゲート、SessionOps 除外、cost 分離、shadow log パス、timeout/retry）
- 次: Phase 1 local shadow 実装（Gate A）。dev shadow は Gate B（expanded fixture 医療安全レビュー含む）まで No-Go
- §7 未解決のうち secret / 5 turn / 商品名最大3 / shadow log 専用パスは凍結値で確定。label owner・dev 権限は Gate B 前に別途確定
