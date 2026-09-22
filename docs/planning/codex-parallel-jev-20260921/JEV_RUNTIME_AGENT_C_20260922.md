# Agent C: Runtime Reliability — Round 0→1（2026-09-22）

- Agent: C (Runtime Reliability)
- Owner files: `jev_client.py` / `jev_router.py` / `llm_flags.py` / `routing_config.py`
- Tests: `tests/services/test_jev_client.py`, `tests/dialogue/routing/test_jev_router.py`
- Gate context: Phase1 local shadow = Passed; Gate A-accuracy = Not Passed; Gate B = Hard No-Go（Supervisor 固定）

---

## Round 0 要約（監査）

| 項目 | Round0 状態 | 判定 |
| --- | --- | --- |
| client 再利用（process-level `httpx.Client`） | 実装済 + atexit close | OK |
| timeout / connect split（read=budget, connect≤1s） | 実装済 | OK |
| retry（429/5xx 最大1、timeout/4xx/network は無） | 実装済 | OK |
| APIキー欠落 fail-open（`JEV_API_KEY` のみ、TYPESAFE 不使用） | 実装済 | OK |
| secret 非出力（`exc_info` 禁止・結果 dataclass にキー無し） | 実装済 | OK |
| bounded executor（workers=2）+ pending cap（8） | 実装済 | OK |
| queue saturation → `not_eligible`/`queue_full` | 実装済 | OK |
| process shutdown（client/executor atexit） | 実装済 | OK（executor TypeError 耐性不足） |
| flags default OFF / PRIMARY 本線不関与 | 実装済 | OK |
| submit 失敗時メトリクス | **欠落**（pending 戻しのみ、観測イベント無し） | GAP |
| 障害注入テスト網羅 | 一部のみ（DNS/拒否/500/usage/queue/submit/log/enum 不足） | GAP |
| `jev_http_max_retries` getter | 未（retry は client 定数） | GAP（軽微） |
| correlation lifecycle | router/dispatcher 側（Supervisor 所有）。adapter は `False` 返却で stash 抑止に協調 | OK（文書化不足） |

---

## Round 1 変更ファイル / 理由

| ファイル | 理由 |
| --- | --- |
| `src/services/jev_client.py` | `_max_attempts()` を `jev_http_max_retries()` に接続。DNS/接続拒否コメント明確化 |
| `src/dialogue/routing/jev_router.py` | submit 失敗時 `submit_failed` メトリクス。`_record_schedule_skip` DRY。shutdown 耐性。`exc_info` 除去。`_reset_runtime_for_tests` |
| `config/routing_config.py` | `jev_http_max_retries()`（固定 1、env 不可変） |
| `config/llm_flags.py` | PRIMARY docstring 強化（Phase1 で実行に効かせない契約の明示） |
| `tests/services/test_jev_client.py` | 障害注入 + flags default OFF + retry getter |
| `tests/dialogue/routing/test_jev_router.py` | queue / submit / log write / unknown enum / corr=None / shutdown / missing key |
| `docs/planning/.../JEV_RUNTIME_AGENT_C_20260922.md` | 本報告 |

---

## テスト

```text
.venv\Scripts\python.exe -m pytest tests/services/test_jev_client.py tests/dialogue/routing/test_jev_router.py -q
→ 58 passed
```

障害注入（mock）カバー:

| 注入 | 期待 | テスト |
| --- | --- | --- |
| timeout | `timeout`, retry=0 | `test_timeout_no_retry` |
| DNS failure | `network_error`, retry=0 | `test_dns_failure_no_retry` |
| connection refusal | `network_error`, retry=0 | `test_connection_refused_no_retry` |
| 429 exhausted | `http_429_exhausted`, retry=1 | `test_429_exhausted` |
| 500 exhausted | `http_5xx_exhausted`, retry=1 | `test_500_exhausted` |
| 503 then OK | ok, retry=1 | `test_503_then_success` |
| malformed JSON | `invalid_json` | `test_invalid_json` / `test_malformed_json_non_object` |
| unknown enum | shadow `invalid_schema` + `unknown_choice` | `test_unknown_enum_answers_recorded_as_invalid_schema` |
| usage missing | `usage={}` | `test_usage_missing_returns_empty_dict` |
| worker scheduling failure | `submit_failed`, return False | `test_worker_scheduling_failure_records_submit_failed` |
| log write failure | 例外非伝播 | `test_log_write_failure_does_not_raise_on_sync_path` |
| missing API key | `missing_api_key` fail-open | client + `test_missing_api_key_fail_open_through_shadow_worker` |
| queue saturation | `queue_full` | `test_queue_saturation_records_not_eligible_and_returns_false` |
| process shutdown | idempotent close | `test_close_shared_client_idempotent` / `test_shutdown_executor_idempotent` |

---

## 未解決

1. **Session correlation clear**（`_jev_shadow_correlation_id` stash / notify 後 clear）は `router.py` / `dispatcher.py`（Supervisor 所有）。本 Agent は `schedule_jev_shadow→False` で stash 抑止に協調するのみ。
2. **`resolved_version` の metrics 永続化**は Agent D（Observability）所有。client は返却済み。
3. **Gate A-accuracy / Gate B** は Runtime 外。本変更でゲート語は変えない。
4. **executor `wait=True` drain on SIGTERM** は未実装（atexit + `wait=False`）。Cloud Run グレースフル停止での in-flight shadow 欠損は許容（fail-open）だが、必要なら Supervisor と運用契約を決める。

---

## 危険 / リスク

| リスク | 深刻度 | 緩和 |
| --- | --- | --- |
| shadow queue drop 増で観測欠損 | Low | `queue_full` / `submit_failed` イベントで可視化 |
| PRIMARY を誤って router 本線に配線 | High（契約違反） | Phase1 では `jev_router` / `jev_client` が PRIMARY を参照しないことをテストで固定 |
| secret が他モジュールの `exc_info` 経由で漏洩 | Med | client は非例外経路。router 側 `exc_info` を除去済 |
| flags を default ON にする PR | High | `_flag(..., False)` 維持 + 所有テストで default OFF 断言 |

---

## Supervisor への共有ファイル変更提案（編集せず提案のみ）

### `src/dialogue/routing/router.py`（任意・低優先）

- `_maybe_schedule_jev_shadow` が `scheduled=False`（queue_full / submit_failed）のとき既に `None` を返し corr stash しない — **現行で正しい**。
- 提案: debug ログに `schedule_skipped` 理由を渡せるよう、`schedule_jev_shadow` が `(bool, reason)` を返す API 拡張は **不要**（metrics 側で十分）。変更しないことを推奨。

### `src/dialogue/dispatcher.py`

- `notify_executed_decision` 後の corr clear は現状どおり維持。
- 提案なし（Agent C 範囲で不足なし）。

### `src/services/jev_metrics.py`（Agent D）

- `error_class=submit_failed` / `queue_full` を schema 文書・集計ダッシュボードの known enum に追加してほしい。
- `resolved_version` を shadow JSONL に載せるなら client 結果から転送（D 所有）。

---

## 自己評価

| 観点 | 評価 |
| --- | --- |
| Round0 ギャップ埋め | **完了**（submit メトリクス + retry getter + テスト網羅） |
| Phase1 本線不変 | **維持**（PRIMARY 非参照・fail-open・session 非 mutate） |
| secret 取り扱い | **維持・強化**（router `exc_info` 除去） |
| テスト green | **58 passed** |
| Gate 語への影響 | **なし**（Runtime は A-accuracy を動かさない） |

**総合:** Round1 Runtime Reliability は提出可能。共有ファイルの必須変更なし。

---

## 提出チェックリスト

- [x] flags default OFF 維持
- [x] PRIMARY を Phase1 実行に効かせない
- [x] decisions / metrics / eval / fixture 非編集
- [x] router / dispatcher / pipeline 非編集
- [x] git commit/push なし
- [x] secret 非記載
