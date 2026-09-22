# test_jev_router.py 差分分類 — 境界 candidate 除外判定

- Date: 2026-09-22
- commit / push / live: **禁止**
- 結論: **`tests/dialogue/routing/test_jev_router.py` を境界 commit candidate から EXCLUDE**

## A. 差分分類（WT vs HEAD）

| 区分 | 内容 | 判定 |
| --- | --- | --- |
| **boundary-essential** | `test_eligibility_exception_fail_closed_skips_jev_api`（+末尾） | **名目のみ**。`is_jev_intent_router_eligible` を patch するが、現行 `schedule_jev_shadow` は `collect_pre_route_signals` + `decide_jev_intent_eligibility` を直接呼ぶため **配線テストとして陳腐化**（confirmed） |
| **pre-existing Phase1 runtime** | queue / submit / log-fail / unknown-enum / correlation-none / shutdown / no-primary-flag / missing-api-key、および既存 schedule/sync/scrub 系 | 境界契約外の runtime 信頼性 |
| **test-mock hygiene** | `patch.dict(sys.modules, {jev_client, jev_decisions})` + `patch(jev_metrics.record_shadow_event)` を併用する複数テスト；**current fail 2 件**（sync / queue_saturation）の根 | 別 candidate |
| **unrelated** | `import inspect` / `sys` / `jr` のモジュール先頭寄せ | 境界必須ではない |

### current failures（measured）

```text
test_sync_path_mocked_client_no_session_change
test_queue_saturation_records_not_eligible_and_returns_false
→ 2 failed, 21 passed（ファイル全体）
```

HEAD 版テストファイルを WT `jev_router.py` に当てた場合も  
`test_sync_path_mocked_client_no_session_change` が **1 failed**（queue テストは HEAD に無し）。

→ **本ファイルを含む candidate を green として提示してはならない。**

## B. boundary-essential hunk の安全分離

| 方式 | 結果 |
| --- | --- |
| 非対話で eligibility テストだけ stage | 当該テストは **誤った patch 先**のため境界証明に使えない |
| ファイル丸ごと stage | Phase1 runtime + 失敗テスト混入 → **禁止** |
| 新ファイルに正しい配線テストを追加 | 境界強化には有効だが **本サイクルでは未作成**（mock hygiene と混同しない） |

**分離不能 → ファイル全体を境界 candidate から除外。**

## C. 他テストによる境界契約の十分性（measured）

除外後に実行した境界関連 suite:

```text
tests/dialogue/routing/test_pre_route_signals.py
tests/services/test_jev_eligibility.py
tests/services/test_jev_eligibility_sessionops_matrix.py
tests/dialogue/routing/test_gate.py
tests/line/test_session_agent.py
tests/core/test_crisis_detection.py
tests/docs/test_jev_pdca_state_integrity.py
tests/services/test_jev_metrics_physical_jsonl.py

129 passed
```

| 境界契約 | 証明の所在 | 十分? |
| --- | --- | --- |
| PreRouteSignals / fail-closed decide | `test_pre_route_signals` | yes |
| eligibility pure / SessionOps 行列 | `test_jev_eligibility*` | yes |
| Safety ≻ SessionOps（gate） | `test_gate` | yes |
| session_agent probe 抑止・循環切断 | `test_session_agent` / `test_pre_route_signals` | yes |
| Option A（否定 soft 非導入） | `test_crisis_detection`（crisis_detection.py は EXCLUDE） | yes |
| `jev_router.schedule` ↔ collect+decide 配線 | **専用 green テスト欠落** | **gap（Open）** |

`jev_router.py` 実装を INCLUDE する場合、配線回帰は **別の新テストファイル**で後続追加する（本 polluted ファイルには載せない）。  
現状 gap は「eligibility 契約自体は専用テストで証明済み；router 結線の回帰だけ薄い」。

## D. test-mock hygiene candidate（別単位・未実装）

要件（Supervisor）:

- `patch.dict(sys.modules)` による package 属性汚染を除去
- 実モジュール import のうえ `patch.object`
- production code 変更なし
- 単独 / ファイル全体 / suite 内順序入れ替えで order-dependent failure 消滅を証明

**境界 candidate に混入させない。**

## E. manifest 表現

「fail 中ファイルを含むが commit 可能」と読める INCLUDE を削除済み（改訂 manifest 参照）。
