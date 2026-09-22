# JEV Shadow JSONL Integration Result（Phase1 / Local isolation）

- Agent: **D Observability and Privacy**
- 日付: 2026-09-22
- 対象: Phase1 shadow 観測（**dev / staging / production には一切 enable しない**）
- Owner: `src/services/jev_metrics.py`, `tests/services/test_jev_metrics.py`
- Read-only 確認: `jev_router.py`, `llm_flags`（defaults は OFF のまま。本作業で flip していない）
- Gate A-accuracy: **Not Passed**（本証跡は観測・プライバシーのみ。Passed 主張なし）

---

## 判定サマリ

| 領域 | 結果 | 根拠 |
| --- | --- | --- |
| legacy route / response 不変 | **PASS（unit）** | `test_jev_shadow_integration` — shadow ON / PRIMARY true でも `resolve_route` は同一 legacy 参照を返す |
| JSONL path / schema v2 | **PASS（unit）** | 書込先 `log/jev_intent_router_shadow.jsonl`、`schema_version=2`、必須フィールド + `event_completeness` |
| correlation bind / notify / clear | **PASS（unit）** | router stash → dispatcher `notify_executed_decision` → session pop；metrics registry join |
| queue_full / submit_failed 記録 | **PASS（unit・修正後）** | router 側 `error_class` 記録済み；`failure_reason` が `not_eligible` で潰れていた点を metrics 正規化で是正 |
| restartability | **PASS（設計＋unit）** | JSONL は append（再起動後もファイル存続）；in-memory registry は揮発（想定内） |
| PII / secret denylist | **PASS（unit・修正後） / 残留リスクあり** | 検証時に denylist 欠落を Critical として検出→所有範囲で是正。値ヒューリスティックは完全ではない |
| フルアプリ smoke（有料 API） | **未検証** | 意図的に未実施（ローカル isolation・課金回避） |
| Gate A-accuracy | **Not Passed** | 別レポート正本。本ドキュメントは Passed を主張しない |

---

## Pass / Fail チェックリスト

### A. Legacy route / response unchanged

| # | 項目 | 結果 | 検証方法 |
| --- | --- | --- | --- |
| A1 | shadow OFF → legacy identity | **PASS** | `test_resolve_route_default_off_returns_legacy_identity` |
| A2 | shadow ON → 同一 legacy オブジェクト | **PASS** | `test_resolve_route_shadow_on_still_returns_same_legacy` |
| A3 | PRIMARY=true でも実行 route は legacy | **PASS** | `test_resolve_route_primary_flag_true_still_returns_legacy` |
| A4 | shadow 成功時も dispatch key を書かない | **PASS** | `test_shadow_sync_success_does_not_write_dispatch_keys` |
| A5 | shadow 失敗が session / response を壊さない | **PASS** | `test_shadow_sync_failure_does_not_mutate_session_or_raise` |
| A6 | 実 HTTP 応答の E2E 差分なし | **未検証** | フル app smoke 未実施 |

### B. JSONL generation path / schema

| # | 項目 | 結果 | 検証方法 |
| --- | --- | --- | --- |
| B1 | log file 名 | **PASS** | `LOG_FILE = "jev_intent_router_shadow.jsonl"` → `structured_logger._write_to_jsonl` → `log/` 配下 append |
| B2 | `log_type` / `schema_version` | **PASS** | `jev_intent_router_shadow` / `2` |
| B3 | REQUIRED_SHADOW_FIELDS 完備 | **PASS** | `assess_event_completeness` + unit |
| B4 | cost 推定/実測分離 | **PASS** | `jev_cost_usd_estimate` 正本、`jev_cost_usd` は DEPRECATED エイリアス（estimated） |
| B5 | 書き込み失敗が本線例外にならない | **PASS** | `test_record_shadow_event_write_failure_does_not_raise` / router sync logfail |
| B6 | 実ファイルがローカルに数行生成されたこと | **未検証** | 本検証は `_write_to_jsonl` を mock。生成 JSONL は commit しない方針のため実ファイル未採取 |

### C. Correlation bind / executed notify / clear

| # | 項目 | 結果 | 検証方法 |
| --- | --- | --- | --- |
| C1 | schedule 成功時 `_jev_shadow_correlation_id` stash | **PASS** | router + shadow integration |
| C2 | schedule 失敗 / OFF 時 clear（stash しない） | **PASS** | `schedule→False` で correlation 返さず pop |
| C3 | dispatcher `notify_executed_decision(corr, decision)` | **PASS** | `test_dispatcher_notifies_executed_without_reading_jev` |
| C4 | notify 後 session key clear | **PASS** | `dispatcher.py` で `pop("_jev_shadow_correlation_id")`（コードレビュー + 間接 unit） |
| C5 | metrics registry join（executed ≠ legacy の場合） | **PASS** | `test_record_uses_notified_executed_decision` |
| C6 | notify 失敗の非伝播 | **PASS** | `test_notify_failure_non_propagating` |

### D. queue_full / submit_failed

| # | 項目 | 結果 | 検証方法 |
| --- | --- | --- | --- |
| D1 | queue 飽和で `attempted=False` + `error_class=queue_full` | **PASS** | `test_queue_saturation_records_not_eligible_and_returns_false` |
| D2 | submit 失敗で `error_class=submit_failed` | **PASS** | `test_worker_scheduling_failure_records_submit_failed` |
| D3 | `failure_reason` が enum として `queue_full` / `submit_failed` | **PASS（修正後）** | 旧: `fallback_reason=not_eligible` が先に解釈され `failure_reason=other`。`normalize_failure_reason` が未知ラベルをスキップするよう修正 |
| D4 | 本線ブロックしない（False 返却のみ） | **PASS** | schedule 戻り値 False；例外なし |

### E. Restartability

| # | 項目 | 結果 | 備考 |
| --- | --- | --- | --- |
| E1 | JSONL append でプロセス再起動後も追記可能 | **PASS（設計）** | `open(..., 'a')`。専用ローテーション契約は本フェーズ外 |
| E2 | in-memory `_executed_by_correlation` は再起動で消える | **PASS（想定内）** | 最大 256・LRU。再起動跨ぎ join は保証しない |
| E3 | executor は lazy 再生成 + atexit shutdown | **PASS（コード）** | `jev_router._get_executor` / `_shutdown_executor` |
| E4 | flag 既定 OFF → 再起動しても勝手に ON にならない | **PASS** | `JEV_*` すべて `_flag(..., False)`。本作業で未変更 |
| E5 | 再起動後の実 JSONL 追記 smoke | **未検証** | 有料 API / フル app 未実施 |

### F. PII / secret denylist

| # | 項目 | 結果 | 備考 |
| --- | --- | --- | --- |
| F1 | API key / Authorization / Bearer / sk- 値 | **PASS** | キー禁止 + `_SECRET_VALUE_RE` redact |
| F2 | Cookie | **PASS（修正後）** | 検証時欠落 → `cookie`/`Cookie` を `FORBIDDEN_LOG_KEYS` に追加 |
| F3 | raw session id / user id | **PASS** | キー禁止；SID は `trace_hash`（SHA256 先頭 32）のみ |
| F4 | email / phone / address | **PASS（修正後）** | 検証時 `extra` 経由で漏出可能だった → キー禁止追加 |
| F5 | system / RAG / generation prompts | **PASS（修正後）** | `rag`/`rag_text` 既存；`system_prompt`/`generation_prompt`/`prompt` 追加 |
| F6 | `baseline_triage_hint` | **PASS** | state builder 禁止 + metrics 禁止キー |
| F7 | history >5 turns | **PASS（unit）** | `_MAX_RECENT_TURNS=5`；JSONL には本文ではなく `state_shape.recent_turn_count` |
| F8 | non-allowlist session fields | **PASS（unit）** | `_ALLOWED_TOP_LEVEL_KEYS` + forbidden scrub（router 側・読取確認） |
| F9 | assert 非依存（`-O` 耐性） | **PASS** | scrub + `ast` で Assert 0 |
| F10 | 未知形式の秘密・自由文 PII の値検査 | **残留** | キー/正規表現ヒューリスティック。メール文字列が別キー名に入ると取りこぼし得る |

---

## Critical privacy findings

### 検出（検証時点）→ 是正済み

1. **Critical — denylist 欠落（是正済）**  
   `FORBIDDEN_LOG_KEYS` に `Cookie` / `email` / `phone` / `address` / `system_prompt` / `generation_prompt` / `prompt` が無く、`record_shadow_event(..., extra=...)` 経由で JSONL に入り得た。  
   **対応:** `jev_metrics.py` に追加し、`test_record_scrubs_poisoned_extra` を拡張。

2. **High（観測）— `failure_reason` が queue skip で `other` 化（是正済）**  
   `fallback_reason=not_eligible` が未知のため先に `other` へ落ち、`error_class=queue_full|submit_failed` が `failure_reason` に反映されなかった。  
   **対応:** `normalize_failure_reason` が未知候補をスキップし後続の既知 enum を採用。

### 残留（Critical 未達・許容）

- メイン shadow worker path は allowlist 構築のため、通常は email 等を載せない。今回の穴は主に `extra` / 将来呼び出し。
- 値ベース redact は `sk-` / `Bearer` / `api_key=` 中心。任意メール・電話・住所の自由文は **キー名依存**。
- 実 `log/jev_intent_router_shadow.jsonl` の人手目視は **未検証**（mock のみ・生成物は commit しない）。

---

## 実行したテスト（有料 API なし）

```text
.venv\Scripts\python.exe -m pytest \
  tests/services/test_jev_metrics.py \
  tests/dialogue/routing/test_jev_shadow_integration.py \
  tests/dialogue/routing/test_jev_router.py -q
```

結果: **54 passed**（約 1s）

環境フラグ（参考・本 pytest は flag mock / force 経路中心）:

```text
JEV_ENABLED=true
JEV_INTENT_ROUTER_SHADOW=true
JEV_INTENT_ROUTER_PRIMARY=false
```

リポジトリ既定はすべて **false**（変更なし）。

---

## unit 検証 vs 未検証

| 検証済み（unit / コード） | 未検証 |
| --- | --- |
| schema v2 payload 形状・completeness | 実 JSONL ファイルの目視サンプリング |
| legacy 不変（resolve_route） | フル app HTTP smoke / 実応答 diff |
| corr bind / notify / clear | プロセス再起動跨ぎの join 実測 |
| queue_full / submit_failed 記録 | 負荷下での実 queue 飽和 |
| PII scrub（キー + sk-/Bearer） | 未知秘密形式・自由文 PII |
| cost estimate 命名 | OpenAI actual 本番配線（他 owner） |
| flag 既定 OFF | Cloud Run / staging 設定監査（本スコープ外・enable 禁止） |

---

## 変更ファイル（本 Worker）

| ファイル | 内容 |
| --- | --- |
| `src/services/jev_metrics.py` | denylist 拡張；`normalize_failure_reason` が未知ラベルをスキップ |
| `tests/services/test_jev_metrics.py` | queue_full/submit_failed 正規化・拡張 PII extra テスト |
| 本ドキュメント | Phase1 local-isolation 統合検証結果 |

`jev_router.py` / `llm_flags.py` は **未変更**。

---

## Gate 語（厳守）

- **Gate A-accuracy: Not Passed**（変更なし・本証跡で Passed と書かない）
- Phase1 shadow の観測・プライバシー準備はローカル unit 上で前進。**製品 Go / 環境 enable の根拠にはならない**
- 生成 JSONL は **commit / `git add log/` 自動追加しない**（本検証でも実ファイル未生成）
